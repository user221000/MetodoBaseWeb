"""Mounted privacy route through real factories, JWT and restricted PG role.

Each child configures the production database adapter before imports. No auth,
tenant middleware, service or dependency is replaced. All data is synthetic in
the UUID database owned by the imported fixture.
"""
import importlib
import multiprocessing
import os

import pytest
from sqlalchemy.orm import Session

from tests.integration_postgres import owned_postgres_database, CLIENT_IDS, PERSONAL, TENANT_A, TENANT_B

LEGACY_OWNER = "privacy-owner-individual-type"


def _composition_worker(url, factory_module, output):
    from tests.isolation import block_external_sockets, prepare_environment, validate_postgres_test_url

    validate_postgres_test_url(url)
    os.environ.pop("_METODOBASE_TEST_ROOT", None)
    os.environ["METODOBASE_TEST_DATABASE_URL"] = url
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from fastapi.testclient import TestClient
    from sqlalchemy import event, select, text
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Cliente, Usuario

    engine = get_engine()
    try:
        app = importlib.import_module(factory_module).create_app()
        assert not app.dependency_overrides
        with TestClient(app, raise_server_exceptions=False) as client:
            with Session(engine) as db:
                assert db.scalars(select(Cliente)).all() == []
                assert db.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one() == (False, False)
                tokens = {identity: crear_access_token(identity_from_user(db.get(Usuario, identity), db))
                          for identity in (TENANT_A, TENANT_B, PERSONAL, LEGACY_OWNER)}
            statements, commits = [], []

            def sql_observed(conn, cursor, statement, parameters, context, executemany):
                statements.append(statement.lstrip().split(None, 1)[0].upper())

            def committed(session):
                commits.append(True)

            event.listen(engine, "before_cursor_execute", sql_observed)
            event.listen(Session, "after_commit", committed)
            try:
                path = "/api/usuario/privacidad/exportar"
                assert client.get(path).status_code == 401
                assert client.get(path, headers={"Authorization": "Bearer invalid-synthetic-token"}).status_code == 401
                for identity in (TENANT_A, TENANT_B, LEGACY_OWNER):
                    response = client.get(path, headers={"Authorization": "Bearer " + tokens[identity]})
                    assert response.status_code == 200, response.text
                    data = response.json()
                    assert data["account"]["id"] == identity
                    assert data["scope"]["personal_space"] is False
                    for section in ("profiles", "plans", "measurements", "purchases", "generation_requests"):
                        assert data[section]["records"] == []
                    assert "professional-portfolio-marker" not in response.text
                response = client.get(path, params={"gym_id": TENANT_A, "user_id": TENANT_B},
                    headers={"Authorization": "Bearer " + tokens[PERSONAL]})
                assert response.status_code == 200, response.text
                data = response.json()
                assert data["account"]["id"] == PERSONAL
                assert data["scope"]["personal_space"] and data["scope"]["professional_membership"]
                assert [record["id_cliente"] for record in data["profiles"]["records"]] == [CLIENT_IDS[PERSONAL]]
                assert len(data["plans"]["records"]) == len(data["measurements"]["records"]) == 1
                assert all(record["id_cliente"] == CLIENT_IDS[PERSONAL]
                           for section in ("plans", "measurements") for record in data[section]["records"])
                assert "personal-profile-marker" in response.text
                assert "professional-portfolio-marker" not in response.text
                assert "private-object-path-marker" not in response.text
                assert response.headers["cache-control"] == "no-store"
                assert response.headers["content-disposition"] == 'attachment; filename="metodobase-datos-personales.json"'
                assert commits == []
                assert not set(statements).intersection({"INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP"})
            finally:
                event.remove(engine, "before_cursor_execute", sql_observed)
                event.remove(Session, "after_commit", committed)
            # The connection returned by the authenticated export cannot grant
            # a following direct session the member's scope.
            with Session(engine) as db:
                assert db.scalars(select(Cliente)).all() == []
            output.put({"passed": True, "factory": factory_module, "commits": len(commits)})
    except Exception:
        import traceback
        output.put({"passed": False, "traceback": traceback.format_exc()})
    finally:
        engine.dispose()


@pytest.mark.parametrize("factory_module", ["web.main_web", "api.app"])
def test_mounted_privacy_route_preserves_personal_boundary_without_overrides(owned_postgres_database, factory_module):
    from web.database.models import Cliente, PlanGenerado, Usuario, UserRole

    admin, url = owned_postgres_database
    with Session(admin) as db:
        if db.get(Usuario, LEGACY_OWNER) is None:
            db.add(Usuario(id=LEGACY_OWNER, email="privacy-owner-legacy@example.invalid", nombre="Synthetic owner",
                password_hash="unused-synthetic", tipo="usuario", role=UserRole.OWNER, activo=True, session_version=0))
            db.flush()
            db.add(Cliente(id_cliente="privacy-professional-legacy", gym_id=LEGACY_OWNER,
                nombre="professional-portfolio-marker", edad=30))
            db.flush()
            db.add(PlanGenerado(gym_id=LEGACY_OWNER, id_cliente="privacy-professional-legacy",
                ruta_pdf="private-object-path-marker.pdf"))
        for identity in (TENANT_A, TENANT_B, PERSONAL):
            db.query(Cliente).filter_by(gym_id=identity).one().notas = (
                "personal-profile-marker" if identity == PERSONAL else "professional-portfolio-marker")
            db.query(PlanGenerado).filter_by(gym_id=identity).one().ruta_pdf = "private-object-path-marker.pdf"
        db.commit()
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    child = context.Process(target=_composition_worker, args=(url, factory_module, output))
    child.start()
    try:
        child.join(60)
        assert not child.is_alive(), "Owned synthetic privacy worker exceeded deadline"
        assert child.exitcode == 0
        result = output.get(timeout=5)
        assert result["passed"], result
    finally:
        if child.is_alive():
            child.terminate()
            child.join(5)
        output.close()
