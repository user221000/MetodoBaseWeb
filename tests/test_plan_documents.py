"""Exact PDF identity and authorization through both real application factories."""
import importlib
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.fixture(params=["web.main_web", "api.app"])
def documents(request, test_gym_user, tmp_path, monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import Cliente, PlanGenerado, Usuario, UserRole
    from web.services import plan_documents

    monkeypatch.setattr(plan_documents, "CARPETA_PLANES", str(tmp_path / "private"))
    root = Path(plan_documents.CARPETA_PLANES)
    root.mkdir()
    first, latest = b"%PDF-synthetic-first", b"%PDF-synthetic-latest"
    (root / "first.pdf").write_bytes(first)
    (root / "latest.pdf").write_bytes(latest)
    foreign = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Usuario(id=foreign, email=foreign + "@example.invalid", nombre="Synthetic Other",
            password_hash="synthetic-unused", role=UserRole.OWNER, tipo="gym", activo=True))
        db.flush()
        own_client, foreign_client = str(uuid.uuid4()), str(uuid.uuid4())
        db.add_all([Cliente(gym_id=test_gym_user["id"], id_cliente=own_client, nombre="Synthetic Own", activo=False),
            Cliente(gym_id=foreign, id_cliente=foreign_client, nombre="Synthetic Other")])
        db.flush()
        plans = [PlanGenerado(gym_id=test_gym_user["id"], id_cliente=own_client, ruta_pdf=str(root / "first.pdf")),
            PlanGenerado(gym_id=test_gym_user["id"], id_cliente=own_client, ruta_pdf=str(root / "latest.pdf")),
            PlanGenerado(gym_id=foreign, id_cliente=foreign_client, ruta_pdf=str(root / "first.pdf")),
            PlanGenerado(gym_id=test_gym_user["id"], id_cliente=foreign_client, ruta_pdf=str(root / "first.pdf"))]
        db.add_all(plans)
        db.flush()
        ids = [row.id for row in plans]
        db.commit()
    app = importlib.import_module(request.param).create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, test_gym_user["auth_headers"], ids, root, first, latest, own_client


def get_pdf(case, index=0, *, authenticated=True):
    return case[0].get("/api/planes/" + str(case[2][index]) + "/pdf",
        headers=case[1] if authenticated else {})


def test_exact_historical_plan_is_returned_even_when_newer_exists_and_client_inactive(documents):
    assert get_pdf(documents).content == documents[4]
    assert get_pdf(documents, 1).content == documents[5]
    response = get_pdf(documents)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="plan.pdf"'
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_authentication_and_both_owner_predicates_are_required(documents):
    assert get_pdf(documents, authenticated=False).status_code == 401
    for index in (2, 3):
        response = get_pdf(documents, index)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "plan_pdf_unavailable"
        assert str(documents[3]) not in response.text


@pytest.mark.parametrize("change", ["deleted_plan", "deleted_client", "missing", "outside", "corrupt", "oversized"])
def test_unavailable_file_never_falls_back_to_latest_or_exposes_paths(documents, change, monkeypatch):
    from datetime import datetime, timezone
    from web.database.engine import get_engine
    from web.database.models import Cliente, PlanGenerado
    from web.services import plan_documents

    with Session(get_engine()) as db:
        plan = db.get(PlanGenerado, documents[2][0])
        if change == "deleted_plan":
            plan.deleted_at = datetime.now(timezone.utc)
        elif change == "deleted_client":
            db.query(Cliente).filter_by(id_cliente=documents[6]).one().deleted_at = datetime.now(timezone.utc)
        elif change == "outside":
            outside = documents[3].parent / "outside.pdf"
            outside.write_bytes(documents[4])
            plan.ruta_pdf = str(outside)
        elif change == "missing":
            (documents[3] / "first.pdf").unlink()
        elif change == "corrupt":
            (documents[3] / "first.pdf").write_bytes(b"private-non-PDF-content")
        else:
            monkeypatch.setattr(plan_documents, "MAX_OBJECT_BYTES", 8)
        db.commit()
    response = get_pdf(documents)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "plan_pdf_unavailable"
    assert str(documents[3]) not in response.text and "private-non-PDF-content" not in response.text


def test_download_get_does_not_commit_or_write_database(documents):
    from web.database.engine import get_engine

    writes, commits = [], []
    def executed(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)
    def committed(session):
        commits.append(True)
    engine = get_engine()
    event.listen(engine, "before_cursor_execute", executed)
    event.listen(Session, "after_commit", committed)
    try:
        assert get_pdf(documents).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", executed)
        event.remove(Session, "after_commit", committed)
    assert not writes and not commits


@pytest.mark.parametrize("value", [0, -1, 2147483648])
def test_plan_identifier_respects_database_integer_bounds(documents, value):
    response = documents[0].get("/api/planes/" + str(value) + "/pdf", headers=documents[1])
    assert response.status_code == 422
