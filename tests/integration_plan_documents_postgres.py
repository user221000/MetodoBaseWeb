"""Exact PDF identity using real JWT, factories, viewer scope and PostgreSQL.

Only the fixture's UUID database and temporary private PDF directory are used.
No auth/tenant/dependency or filesystem read implementation is replaced.
"""
import importlib
import multiprocessing
import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from tests.integration_postgres import owned_postgres_database, TENANT_A, TENANT_B, PERSONAL, CLIENT_IDS


def _download_worker(url, factory_module, data_dir, ids, output):
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url

    validate_postgres_test_url(url)
    destination = Path(data_dir).resolve(strict=True)
    import tempfile
    assert destination.is_relative_to(Path(tempfile.gettempdir()).resolve())
    os.environ.pop("_METODOBASE_TEST_ROOT", None)
    os.environ["METODOBASE_TEST_DATABASE_URL"] = url
    prepare_environment(discard_inherited=True)
    os.environ["METODOBASE_DATA_DIR"] = str(destination)
    os.environ["DB_POOL_SIZE"], os.environ["DB_MAX_OVERFLOW"] = "1", "0"
    block_external_sockets()
    from fastapi.testclient import TestClient
    from sqlalchemy import event, select
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import PlanGenerado, Usuario

    engine = get_engine()
    try:
        app = importlib.import_module(factory_module).create_app()
        assert not app.dependency_overrides
        with TestClient(app, raise_server_exceptions=False) as client:
            with Session(engine) as db:
                tokens = {subject: crear_access_token(identity_from_user(db.get(Usuario, subject), db))
                          for subject in (TENANT_A, TENANT_B, PERSONAL)}
            writes, commits = [], []

            def executed(conn, cursor, statement, parameters, context, many):
                if statement.lstrip().split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "ALTER", "CREATE"}:
                    writes.append(True)

            def committed(session):
                commits.append(True)

            def download(plan_id, token=None):
                return client.get("/api/planes/" + str(plan_id) + "/pdf",
                    headers={"Authorization": "Bearer " + token} if token else {})

            event.listen(engine, "before_cursor_execute", executed)
            event.listen(Session, "after_commit", committed)
            try:
                assert download(ids["first"]).status_code == 401
                first = download(ids["first"], tokens[TENANT_A])
                latest = download(ids["latest"], tokens[TENANT_A])
                assert first.status_code == latest.status_code == 200
                assert first.content == b"%PDF-synthetic-owned-first" and latest.content == b"%PDF-synthetic-owned-latest"
                assert first.headers["cache-control"] == "no-store"
                assert first.headers["content-disposition"] == 'attachment; filename="plan.pdf"'
                assert first.headers["referrer-policy"] == "no-referrer"
                for name in ("foreign", "mixed"):
                    denied = download(ids[name], tokens[TENANT_A])
                    assert denied.status_code == 404 and denied.json()["detail"]["code"] == "plan_pdf_unavailable"
                    assert str(destination) not in denied.text
                # VIEWER may read their current team's plan, never foreign or
                # independent personal rows through the professional context.
                assert download(ids["first"], tokens[PERSONAL]).content == first.content
                assert download(ids["foreign"], tokens[PERSONAL]).status_code == 404
                assert download(ids["personal"], tokens[PERSONAL]).status_code == 404
                assert download(ids["first"], tokens[TENANT_B]).status_code == 404
                assert not writes and not commits
            finally:
                event.remove(engine, "before_cursor_execute", executed)
                event.remove(Session, "after_commit", committed)
            with Session(engine) as db:
                assert db.scalars(select(PlanGenerado)).all() == []
                # Persisted revocation is fixture setup, outside the observed
                # read-only GET boundary; no auth function is patched.
                member = db.get(Usuario, PERSONAL)
                member.team_gym_id = None
                member.session_version += 1
                db.commit()
                detached_token = crear_access_token(identity_from_user(member, db))
            assert download(ids["first"], tokens[PERSONAL]).status_code == 401
            assert download(ids["first"], detached_token).status_code == 404
            personal = download(ids["personal"], detached_token)
            assert personal.status_code == 200 and personal.content == b"%PDF-synthetic-personal"
            with Session(engine) as db:
                assert db.scalars(select(PlanGenerado)).all() == []
            output.put({"passed": True, "factory": factory_module, "pool_size": engine.pool.size()})
    except Exception:
        import traceback
        output.put({"passed": False, "traceback": traceback.format_exc()})
    finally:
        engine.dispose()


@pytest.mark.parametrize("factory_module", ["web.main_web", "api.app"])
def test_exact_download_with_viewer_revocation_and_pool_reuse(owned_postgres_database, tmp_path, factory_module):
    from web.database.models import Cliente, PlanGenerado, Usuario, UserRole

    admin, url = owned_postgres_database
    data_dir = tmp_path / "private-data"
    private = data_dir / "planes"
    private.mkdir(parents=True)
    ids = {}
    with Session(admin) as db:
        member = db.get(Usuario, PERSONAL)
        member.role, member.team_gym_id = UserRole.VIEWER, TENANT_A
        member.session_version = 0
        db.query(Cliente).filter_by(gym_id=TENANT_A).one().activo = False
        for name, gym, client in (("first", TENANT_A, TENANT_A), ("latest", TENANT_A, TENANT_A),
                                  ("foreign", TENANT_B, TENANT_B), ("mixed", TENANT_A, TENANT_B),
                                  ("personal", PERSONAL, PERSONAL)):
            content = b"%PDF-synthetic-personal" if name == "personal" else ("%PDF-synthetic-owned-" + name).encode()
            path = private / (name + ".pdf")
            path.write_bytes(content)
            plan = PlanGenerado(gym_id=gym, id_cliente=CLIENT_IDS[client], ruta_pdf=str(path))
            db.add(plan)
            db.flush()
            ids[name] = plan.id
        db.commit()
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    child = context.Process(target=_download_worker, args=(url, factory_module, str(data_dir), ids, output))
    child.start()
    try:
        child.join(60)
        assert not child.is_alive(), "Owned exact-document worker exceeded deadline"
        assert child.exitcode == 0
        result = output.get(timeout=5)
        assert result["passed"], result
        assert result["pool_size"] == 1
    finally:
        if child.is_alive():
            child.terminate()
            child.join(5)
        output.close()
