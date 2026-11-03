"""Independent current41 refund policy and authenticated history boundaries."""
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.test_partial_refund_facts_author import billing_case  # noqa: F401 -- domain's owned database
from tests.test_stripe_refund_ledger_author import refund_case, _deliver, _paid, _refund  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    # Domain cases own their SQLAlchemy database. HTTP cases below additionally
    # run the complete Alembic41 chain and verify the real product schema gate.
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def test_same_paid_invoice_partial_cannot_create_extra_time_by_shifting_its_start(refund_case):
    from web.database.models import Subscription

    factory, _, state = refund_case
    _paid(factory, state)
    with factory() as db:
        paid_end = db.query(Subscription).one().current_period_end
    state["subscription"]["current_period_start"] += 86400
    state["subscription"]["current_period_end"] += 86400
    assert _deliver(factory, _refund(state, 1)) == "refund:reconciled"
    with factory() as db:
        end = db.query(Subscription).one().current_period_end
        assert end <= paid_end, "A partial refund of this already paid invoice must never add access time"


@pytest.fixture
def actual41(monkeypatch):
    """A genuine migrated41 memory database; no create_all, stamp or schema mock."""
    from alembic import command
    from alembic.config import Config
    from web.database import engine as engine_module
    from web.database.models import Payment, Usuario, UserRole
    from web.database.schema_control import verify_runtime_schema
    from web.auth import crear_access_token, init_auth

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(engine_module, "_engine", engine)
    monkeypatch.setattr(engine_module, "_SessionLocal", factory)
    config = Config()
    config.set_main_option("script_location", str(ROOT / "web/database/alembic"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    verify_runtime_schema(engine, expected_revision="20261102_payment_refund_facts")
    actors = {
        "personal-a": {"id": "qa41-personal-a", "tipo": "usuario", "team_gym_id": None, "role": "owner"},
        "personal-b": {"id": "qa41-personal-b", "tipo": "usuario", "team_gym_id": None, "role": "owner"},
        "gym": {"id": "qa41-gym", "tipo": "gym", "team_gym_id": None, "role": "owner"},
        "member": {"id": "qa41-member", "tipo": "gym", "team_gym_id": "qa41-gym", "role": "viewer"},
    }
    with factory() as db:
        for key, actor in actors.items():
            actor.update(email=key + "@example.invalid", nombre="Synthetic", apellido="QA", session_version=0)
            db.add(Usuario(id=actor["id"], email=actor["email"], password_hash="unused-offline",
                nombre=actor["nombre"], tipo=actor["tipo"], role=UserRole(actor["role"]),
                team_gym_id=actor["team_gym_id"], activo=True, session_version=0))
        db.flush()
        for index, actor in enumerate(actors.values(), 1):
            db.add(Payment(id=index, gym_id=actor["id"], amount_cents=7900, currency="mxn",
                status="succeeded", plan="pro_usuario", stripe_payment_intent_id="pi_qa41_" + str(index),
                stripe_invoice_id="in_qa41_" + str(index)))
        db.commit()
    init_auth(run_startup_writes=False)
    tokens = {key: crear_access_token(actor) for key, actor in actors.items()}
    try:
        yield engine, factory, actors, tokens
    finally:
        assert engine.pool.checkedout() == 0 if hasattr(engine.pool, "checkedout") else True
        engine.dispose()


@pytest.mark.parametrize("factory_name", ["api", "web"])
def test_real_factories_personal_team_and_cross_account_payment_history(actual41, factory_name):
    from fastapi.testclient import TestClient
    from fastapi.routing import iter_route_contexts
    from web.database.models import Payment
    if factory_name == "api":
        from api.app import create_app
    else:
        from web.main_web import create_app

    _, factory, actors, tokens = actual41
    app = create_app()
    registrations = [route for route in iter_route_contexts(app.routes) if getattr(route, "path", None) == "/api/usuario/payments"
                     and "GET" in getattr(route, "methods", set())]
    assert len(registrations) == 1
    operation = app.openapi()["paths"]["/api/usuario/payments"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
    with TestClient(app, raise_server_exceptions=False) as client:
        for key, expected in (("personal-a", 1), ("personal-b", 2), ("member", 4)):
            reply = client.get("/api/usuario/payments", params={"gym_id": actors["gym"]["id"], "user_id": actors["personal-a"]["id"]},
                headers={"Authorization": "Bearer " + tokens[key]})
            assert reply.status_code == 200, (key, reply.status_code, reply.text)
            rows = reply.json()["payments"]
            assert [row["id"] for row in rows] == [expected]
            assert rows[0]["refund_amount_cents"] is None and rows[0]["net_amount_cents"] is None
            assert rows[0]["stripe_invoice_id"] == "in_qa41_" + str(expected)
            assert datetime.fromisoformat(rows[0]["created_at"]).tzinfo is not None
            assert not any(name in rows[0] for name in ("stripe_charge_id", "stripe_payment_intent_id", "gym_id"))
        assert client.get("/api/usuario/payments", headers={"Authorization": "Bearer " + tokens["gym"]}).status_code == 403
        assert client.get("/api/usuario/payments").status_code == 401
        assert client.get("/api/usuario/payments", headers={"Authorization": "Bearer malformed"}).status_code == 401
        for limit in (0, -1, 101, "x"):
            assert client.get("/api/usuario/payments", params={"limit": limit},
                headers={"Authorization": "Bearer " + tokens["personal-a"]}).status_code == 422
    with factory() as db:
        assert [(row.id, row.gym_id, row.status) for row in db.scalars(select(Payment).order_by(Payment.id))] == [
            (index, actor["id"], "succeeded") for index, actor in enumerate(actors.values(), 1)]
