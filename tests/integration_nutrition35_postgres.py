"""Explicit nutrition35 PostgreSQL gate on exclusive synthetic databases.

The original SQLite HTTP assertions run unchanged through password and MFA in
both factories. Publication locking additionally uses two restricted pool1
engines and observes a real PostgreSQL lock wait, rather than pool contention.
Historical fixtures, targets and expected results are never retargeted.
"""
import importlib
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from tests import followup34_http as http34
from tests import test_nutrition35_http as http35
from tests.followup34_fixtures import owned_database
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import ROOT, run_migration
from tests.integration_stored_objects_migrations import snapshot
from tests.test_nutrition35_http import (
    test_declared_profile_is_rejected_before_any_quota_CPU_or_object as _prequota,
)
from tests.test_nutrition35_http import (
    test_gym_declaration_survives_omitted_and_null_edits_and_reads_are_private as _edits,
)
from tests.test_nutrition35_http import (
    test_independent_personal_profile_preserves_declaration_without_consuming_quota as _personal,
)
from tests.test_nutrition35_http import (
    test_invalid_declaration_is_not_echoed_or_saved as _invalid,
)
from tests.test_nutrition35_http import (
    test_real_PDF_cannot_become_ready_after_restrictions_change as _pdf,
)
from tests.test_nutrition35_http import (
    test_worker_rechecks_a_new_declaration_and_compensates_the_reservation as _worker,
)
from tests.test_nutrition35_migrations import (
    test_drift_or_interrupted_DDL_cannot_advance_the_revision as _drift,
)
from tests.test_nutrition35_migrations import (
    test_nonnull_declaration_refuses_data_loss_on_downgrade as _downgrade,
)
from tests.test_nutrition35_profile_contract import declaration
from web.database.models import Cliente, PlanGenerado, UserRole, Usuario
from web.database.schema_control import verify_runtime_schema
from web.database.tenant_context import tenant_scope
from web.services.nutrition_profiles import (
    capture_profile,
    encode_declaration,
    lock_current_restrictions,
)

PREVIOUS = "20261019_followup_tasks"
REVISION = "20261020_nutrition_profile"
followup_http = http34.followup_http
personal35_http = http35.personal35_http


def _require_profile():
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.fail("This explicit integration gate requires its own PostgreSQL lease profile")


def blank_pool(engine):
    """Verify released checkout and transaction-local identity after each case."""
    assert engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),"
            "current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one()) == ("", "", "")


@pytest.fixture
def database35(tmp_path):
    _require_profile()
    with owned_database("postgresql", tmp_path) as value:
        yield value


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    _require_profile()
    with owned_database("postgresql", tmp_path_factory.mktemp("nutrition35-http-pg")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        application = application_engine(url, admin)
        try:
            with application.connect() as db:
                assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,"
                    "pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') "
                    "FROM pg_roles WHERE rolname=current_user")).one()) == (False, False, False, False, False)
                assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace "
                    "AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 28
                assert len(inspect(db).get_table_names()) == 38
            yield admin, application
        finally:
            application.dispose()


@pytest.mark.parametrize("populated", [False, True])
def test_previous_rows_upgrade_repeat_and_null_only_downgrade(database35, populated):
    url, engine = database35
    run_migration(url, "db_bootstrap.py", "--revision", PREVIOUS)
    if populated:
        with Session(engine) as db:
            db.add(Usuario(id="nutrition35-old", email="nutrition35-old@example.invalid", nombre="Synthetic",
                password_hash="synthetic", tipo="gym", role=UserRole.OWNER))
            db.flush()
            # Seed the actual34 shape, without ORM35's not-yet-added column.
            db.execute(text("INSERT INTO clientes(id_cliente,gym_id,nombre,activo) "
                "VALUES('NUTRITION35-OLD','nutrition35-old','Synthetic legacy',true)"))
            db.commit()
    columns, rows = snapshot(engine)
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
    with engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM clientes WHERE nutrition_restrictions_json IS NOT NULL")) == 0
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    run_migration(url, "-m", "alembic", "downgrade", PREVIOUS)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows


def test_declared_data_prevents_destructive_downgrade(database35):
    _downgrade(database35)


def test_interruption_and_predecessor_drift_are_atomic(database35):
    _drift(database35)


def test_actual_database_declaration_bounds(database35):
    # Preserve the SQLite test's business assertions, with a PostgreSQL boolean
    # seed. The original SQLite helper deliberately retains its own SQL shape.
    from sqlalchemy.exc import IntegrityError

    url, engine = database35
    run_migration(url, "db_bootstrap.py", "--revision", REVISION)
    with Session(engine) as db:
        db.add(Usuario(id="bound35", email="bound35@example.invalid", nombre="Synthetic", password_hash="synthetic",
                       tipo="gym", role=UserRole.OWNER))
        db.flush()
        db.add(Cliente(gym_id="bound35", id_cliente="BOUND35", nombre="Synthetic", activo=True))
        db.commit()
    for invalid in ("", "{", "x"*16385):
        with pytest.raises(IntegrityError), engine.begin() as c:
            c.execute(text("UPDATE clientes SET nutrition_restrictions_json=:v WHERE id_cliente=:i"),
                      {"v": invalid, "i": "BOUND35"})
    with engine.connect() as c:
        assert c.scalar(text("SELECT nutrition_restrictions_json FROM clientes WHERE id_cliente='BOUND35'")) is None


def test_target_adds_only_bounded_nullable_declaration_to_unchanged_security():
    folder = ROOT/"web/database/alembic/schema_targets"
    old = json.loads((folder/(PREVIOUS+"_postgresql.json")).read_bytes())
    current = json.loads((folder/(REVISION+"_postgresql.json")).read_bytes())
    table = current["signature"]["tables"]["clientes"]
    column = next(value for value in table["columns"] if value["name"] == "nutrition_restrictions_json")
    assert column["nullable"] is True and column["type"] == "TEXT" and column["default"] is None
    table["columns"].remove(column)
    check = next(value for value in table["checks"] if value["name"] == "ck_cliente_nutrition_declaration_bound")
    assert "nutrition_restrictions_json" in check["sql"] and "16384" in check["sql"]
    table["checks"].remove(check)
    assert current == old
    assert importlib.import_module("web.database.alembic.versions."+REVISION).down_revision == PREVIOUS


def test_private_edit_preserves_original_declared_facts(followup_http):
    _edits(followup_http)
    blank_pool(followup_http["engine"])


@pytest.mark.parametrize("declared", ["allergy", "review"])
def test_restriction_precedes_quota_CPU_and_objects(followup_http, declared, monkeypatch):
    _prequota(followup_http, declared, monkeypatch)
    blank_pool(followup_http["engine"])


def test_worker_rechecks_and_compensates(followup_http, monkeypatch):
    _worker(followup_http, monkeypatch)
    blank_pool(followup_http["engine"])


def test_PDF_pending_cannot_publish_a_stale_profile(followup_http, monkeypatch):
    _pdf(followup_http, monkeypatch)
    blank_pool(followup_http["engine"])


def test_invalid_health_input_is_not_echoed_or_saved(followup_http):
    _invalid(followup_http)
    blank_pool(followup_http["engine"])


def test_personal_declared_profile_stays_personal_and_unconsumed(personal35_http):
    _personal(personal35_http)
    blank_pool(personal35_http["engine"])


def test_declared_facts_remain_hidden_without_the_owning_tenant(followup_http):
    case = followup_http
    payload = declaration(reported=True)
    result = case["raw"].put("/api/clientes/"+case["profile"], json={"restricciones_nutricionales": payload})
    assert result.status_code == 200
    query = select(Cliente.nutrition_restrictions_json).where(Cliente.id_cliente == case["profile"])
    with Session(case["engine"]) as db:
        assert db.scalar(query) is None
    with tenant_scope(str(uuid.uuid4())), Session(case["engine"]) as db:
        assert db.scalar(query) is None
    with tenant_scope(case["user"]), Session(case["engine"]) as db:
        assert db.scalar(query) == encode_declaration(payload)
    blank_pool(case["engine"])


@pytest.mark.parametrize("expire", [True, False], ids=["expiring-session", "production-session"])
def test_request_handoff_does_not_retain_a_checkout_before_worker(followup_http, monkeypatch, record_property, expire):
    """Observe an actual HTTP/worker handoff under both session configurations."""
    case = followup_http
    from tests.test_nutrition35_http import VALID, _new_plan

    assert case["raw"].put("/api/clientes/"+case["profile"], json=VALID).status_code == 200
    case["factory"].configure(expire_on_commit=expire)
    module = importlib.import_module("api.routes.planes" if case["factory_name"] == "api.app" else "web.routes.planes")
    original = module._generar_plan_sync
    checkouts = []

    def observed(*args, **kwargs):
        checkouts.append(case["engine"].pool.checkedout())
        return original(*args, **kwargs)

    # Bound only this fixture's own QueuePool wait; this does not alter its
    # size, SQL locks, role, business assertions or original worker behavior.
    monkeypatch.setattr(case["engine"].pool, "_timeout", 0.3)
    monkeypatch.setattr(module, "_generar_plan_sync", observed)
    result = _new_plan(case)
    record_property("expire_on_commit", expire)
    record_property("request_checkouts_at_worker_entry", json.dumps(checkouts))
    assert checkouts == [0]
    assert result.status_code == 200
    with Session(case["admin"]) as db:
        assert db.scalar(select(PlanGenerado.id).where(PlanGenerado.gym_id == case["user"])) == result.json()["plan_id"]
    blank_pool(case["engine"])


def test_publication_lock_serializes_owner_profile_update(followup_db):
    """Observe the second backend waiting on our row, then its committed update.

    The test owns both connections and only its UUID database. Its deadline is
    below PostgreSQL's local lock_timeout; no foreign session is cancelled.
    """
    admin, first = followup_db
    second = application_engine(str(admin.url), admin)
    gym, client_id = str(uuid.uuid4()), str(uuid.uuid4())
    with Session(admin) as db:
        db.add(Usuario(id=gym, email=uuid.uuid4().hex+"@example.invalid", nombre="Synthetic",
            password_hash="synthetic", tipo="gym", role=UserRole.OWNER))
        db.flush()
        db.add(Cliente(id_cliente=client_id, gym_id=gym, nombre="Synthetic", alimentos_excluidos="[]"))
        db.commit()
    with Session(admin) as db:
        expected = capture_profile(db.scalar(select(Cliente).where(Cliente.id_cliente == client_id)))
    started = Event()
    completed = Event()
    pids = []

    def edit_profile():
        with tenant_scope(gym), Session(second) as db:
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            pids.append(db.scalar(text("SELECT pg_backend_pid()")))
            started.set()
            profile = db.scalar(select(Cliente).where(Cliente.gym_id == gym, Cliente.id_cliente == client_id))
            profile.nutrition_restrictions_json = encode_declaration(declaration(review=True))
            db.commit()
            completed.set()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            with tenant_scope(gym), Session(first) as publishing:
                lock_current_restrictions(publishing, gym, client_id, expected)
                future = executor.submit(edit_profile)
                assert started.wait(2), "Own profile editor did not begin"
                deadline = time.monotonic()+3
                waiting = False
                while time.monotonic() < deadline and not completed.is_set():
                    with admin.connect() as observer:
                        row = observer.execute(text("SELECT wait_event_type,datname FROM pg_stat_activity WHERE pid=:pid"),
                            {"pid": pids[0]}).one()
                    assert row.datname == admin.url.database
                    if row.wait_event_type == "Lock":
                        waiting = True
                        break
                    completed.wait(0.02)
                assert waiting and not completed.is_set(), "Expected a PostgreSQL row-lock wait, not a completed stale update"
                publishing.add(PlanGenerado(gym_id=gym, id_cliente=client_id, plan_json='{"synthetic":true}'))
                publishing.commit()
            future.result(timeout=5)
        assert completed.is_set()
        with Session(admin) as db:
            persisted = db.scalar(select(Cliente).where(Cliente.id_cliente == client_id))
            assert capture_profile(persisted).declaration_payload() == declaration(review=True)
            assert db.scalar(select(PlanGenerado.id).where(PlanGenerado.gym_id == gym)) is not None
        blank_pool(first)
        blank_pool(second)
    finally:
        second.dispose()
