"""SEC01 multiprocess HTTP activation under the migrated restricted PG role.

Each module owns a freshly created UUID database through the R04 fixture.
Workers use real JWT validation, routers and commits; no auth/API transport mock.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import multiprocessing
import os

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.integration_postgres import owned_postgres_database, TENANT_A, TENANT_B


def _activation_worker(url, subject, key, hardware, barrier, output, timezone_name):
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url

    validate_postgres_test_url(url)
    os.environ.pop("_METODOBASE_TEST_ROOT", None)
    os.environ["METODOBASE_TEST_DATABASE_URL"] = url
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from fastapi.testclient import TestClient
    from api.app import create_app
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario

    try:
        if timezone_name is not None:
            assert timezone_name in {"UTC", "America/Mexico_City"}
            from sqlalchemy import event

            @event.listens_for(get_engine(), "connect")
            def set_synthetic_timezone(connection, record):
                previous = connection.autocommit
                connection.autocommit = True
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SET TIME ZONE %s", (timezone_name,))
                finally:
                    connection.autocommit = previous
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            # Startup initializes the signing key before a real identity token
            # is issued; signing before init_auth would exercise only a 401.
            with Session(get_engine()) as db:
                identity = identity_from_user(db.get(Usuario, subject), db)
                token = crear_access_token(identity)
            barrier.wait(25)
            response = client.post("/api/licencias/activar", headers={"Authorization": "Bearer " + token},
                json={"clave": key, "hardware_id": hardware, "email": subject + "@example.test"})
            output.put({"subject": subject, "status": response.status_code, "body": response.json()})
    except Exception as error:
        output.put({"subject": subject, "error": type(error).__name__})
    finally:
        get_engine().dispose()


def _parallel(url, requests, *, timezone_name=None):
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    barrier = context.Barrier(len(requests))
    workers = [context.Process(target=_activation_worker, args=(url, *request, barrier, output, timezone_name))
               for request in requests]
    for worker in workers:
        worker.start()
    try:
        for worker in workers:
            worker.join(40)
            assert not worker.is_alive(), "Owned synthetic activation worker exceeded deadline"
            assert worker.exitcode == 0
        outcomes = [output.get(timeout=5) for _ in workers]
        assert all("error" not in item for item in outcomes), outcomes
        return outcomes
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(5)
        output.close()


def _issued(engine):
    from web.database.models import GymLicense

    with Session(engine) as db:
        licenses = {row.gym_id: row for row in db.scalars(select(GymLicense)).all()}
        for row in licenses.values():
            row.plan_tier = "standard"
            row.max_clients = 25
            row.expires_at = datetime.now(timezone.utc) + timedelta(days=14)
        db.commit()
        return {subject: (row.id, row.license_key, row.expires_at) for subject, row in licenses.items()}


def test_different_owners_racing_for_one_hardware_keep_exactly_one_binding(owned_postgres_database):
    from web.database.models import LicenseActivation

    admin, url = owned_postgres_database
    issued = _issued(admin)
    hardware = "synthetic-concurrent-cross-owner-hardware"
    outcomes = _parallel(url, [(subject, issued[subject][1], hardware) for subject in (TENANT_A, TENANT_B)])
    assert sorted(item["status"] for item in outcomes) == [200, 409], outcomes
    loser = next(item for item in outcomes if item["status"] == 409)
    assert loser["body"]["detail"]["code"] == "device_binding_unavailable"
    assert "UNIQUE" not in str(loser["body"]) and "INSERT" not in str(loser["body"])
    winner = next(item for item in outcomes if item["status"] == 200)
    with Session(admin) as db:
        activation = db.scalars(select(LicenseActivation).where(LicenseActivation.hardware_id == hardware)).one()
        assert activation.gym_id == winner["subject"]
        assert activation.issued_license_id == issued[winner["subject"]][0]
        assert activation.clave_hash == hashlib.sha256(issued[winner["subject"]][1].encode()).hexdigest()


@pytest.mark.parametrize("timezone_name", ["UTC", "America/Mexico_City"])
def test_same_owner_parallel_repeats_preserve_shorter_original_expiry(owned_postgres_database, timezone_name):
    from web.database.models import LicenseActivation

    admin, url = owned_postgres_database
    issued = _issued(admin)
    license_id, key, _ = issued[TENANT_A]
    hardware = "synthetic-owner-repeat-" + timezone_name.replace("/", "-")
    original_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5)
    with Session(admin) as db:
        db.add(LicenseActivation(gym_id=TENANT_A, issued_license_id=license_id, hardware_id=hardware,
            clave_hash=hashlib.sha256(key.encode()).hexdigest(), email="repeat@example.test", plan="standard",
            activa=True, revocada=False, expira=original_expiry))
        db.commit()
    outcomes = _parallel(url, [(TENANT_A, key, hardware)] * 2, timezone_name=timezone_name)
    assert [item["status"] for item in outcomes] == [200, 200], outcomes
    actual_expiries = [item["body"]["expira"] for item in outcomes]
    assert all(datetime.fromisoformat(value).replace(tzinfo=None) == original_expiry for value in actual_expiries), {
        "expected_original_expiry": original_expiry.isoformat(), "actual_expiries": actual_expiries}
    with Session(admin) as db:
        activation = db.scalars(select(LicenseActivation).where(LicenseActivation.hardware_id == hardware)).one()
        assert activation.expira == original_expiry and activation.issued_license_id == license_id
