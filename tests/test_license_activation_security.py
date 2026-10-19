"""SEC01: issued authority, authenticated ownership and offline containment."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def license_case():
    from api.routes.licencias import router
    from web.auth_deps import get_usuario_actual
    from web.database.engine import get_db
    from web.database.models import Base, GymLicense, Usuario, UserRole

    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    actor = {"id": "license-owner-a", "tipo": "gym", "role": "owner", "team_gym_id": None}
    with factory() as db:
        for suffix in ("a", "b"):
            db.add(Usuario(id="license-owner-" + suffix, email=suffix + "@example.invalid",
                           nombre=suffix, password_hash="not-a-password-hash", tipo="gym",
                           role=UserRole.OWNER, activo=True))
        db.flush()
        db.add(GymLicense(gym_id=actor["id"], license_key="PRO-issued-synthetic-only",
                          plan_tier="gym_comercial", max_clients=73, is_active=True,
                          expires_at=datetime.now(timezone.utc) + timedelta(days=17)))
        db.commit()

    def session():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_usuario_actual] = lambda: dict(actor)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, factory, actor, app
    engine.dispose()


def activate(case, key="PRO-issued-synthetic-only", hardware="synthetic-device-a"):
    return case[0].post("/api/licencias/activar", json={
        "clave": key, "hardware_id": hardware, "email": "contact@example.invalid"})


def test_both_routes_require_authentication(license_case):
    from web.auth_deps import get_usuario_actual
    client, _, _, app = license_case
    app.dependency_overrides.pop(get_usuario_actual)
    assert activate(license_case).status_code == 401
    assert client.get("/api/licencias/estado/synthetic-device-a").status_code == 401


@pytest.mark.parametrize("key", ["STR-not-issued-anywhere", "PRO-not-issued-anywhere", "CLN-not-issued-anywhere"])
def test_prefix_never_grants_a_license(license_case, key):
    from web.database.models import LicenseActivation
    assert activate(license_case, key).status_code == 400
    with license_case[1]() as db:
        assert db.execute(select(LicenseActivation)).first() is None


def test_issued_expiry_and_custom_cap_are_authoritative_and_repeat_does_not_extend(license_case):
    from web.database.models import GymLicense, LicenseActivation
    first = activate(license_case)
    assert first.status_code == 200, first.text
    assert first.json()["max_clientes"] == 73
    with license_case[1]() as db:
        issued = db.execute(select(GymLicense)).scalar_one()
        row = db.execute(select(LicenseActivation)).scalar_one()
        assert row.gym_id == license_case[2]["id"]
        assert row.issued_license_id == issued.id
        assert row.expira == issued.expires_at
        original = row.expira
    second = activate(license_case)
    assert second.status_code == 200
    with license_case[1]() as db:
        assert db.execute(select(LicenseActivation)).scalar_one().expira == original


def test_other_owner_cannot_activate_issued_key_or_read_hardware(license_case):
    assert activate(license_case).status_code == 200
    license_case[2]["id"] = "license-owner-b"
    assert activate(license_case).status_code == 400
    assert license_case[0].get("/api/licencias/estado/synthetic-device-a").status_code == 404


def test_hardware_binding_cannot_be_overwritten_by_another_owner(license_case):
    from web.database.models import GymLicense, LicenseActivation
    assert activate(license_case).status_code == 200
    with license_case[1]() as db:
        db.add(GymLicense(gym_id="license-owner-b", license_key="CLN-second-issued-only",
                          plan_tier="clinica", max_clients=0, is_active=True))
        db.commit()
    license_case[2]["id"] = "license-owner-b"
    response = activate(license_case, "CLN-second-issued-only")
    assert response.status_code == 409
    assert "UNIQUE" not in response.text
    with license_case[1]() as db:
        row = db.execute(select(LicenseActivation)).scalar_one()
        assert row.gym_id == "license-owner-a" and row.plan == "gym_comercial"


@pytest.mark.parametrize("state", ["expired", "revoked", "inactive", "unknown_plan"])
def test_unusable_issued_license_never_activates(license_case, state):
    from web.database.models import GymLicense
    with license_case[1]() as db:
        row = db.execute(select(GymLicense)).scalar_one()
        if state == "expired":
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        elif state == "revoked":
            row.revoked_at = datetime.now(timezone.utc)
        elif state == "inactive":
            row.is_active = False
        else:
            row.plan_tier = "unexpected"
        db.commit()
    assert activate(license_case).status_code == 400


def test_revoked_activation_cannot_be_reactivated_by_repeat(license_case):
    from web.database.models import LicenseActivation
    assert activate(license_case).status_code == 200
    with license_case[1]() as db:
        row = db.execute(select(LicenseActivation)).scalar_one()
        row.revocada = True
        db.commit()
    assert activate(license_case).status_code == 409
    status = license_case[0].get("/api/licencias/estado/synthetic-device-a")
    assert status.status_code == 200
    assert status.json()["revocada"] is True and status.json()["activa"] is False


def test_perpetual_authority_and_less_than_one_day_are_not_invented_years(license_case):
    from web.database.models import GymLicense
    with license_case[1]() as db:
        db.execute(select(GymLicense)).scalar_one().expires_at = None
        db.commit()
    response = activate(license_case)
    assert response.status_code == 200 and response.json()["expira"] is None
    status = license_case[0].get("/api/licencias/estado/synthetic-device-a")
    assert status.status_code == 200 and status.json()["dias_restantes"] is None
    assert status.json()["activa"] is True
    with license_case[1]() as db:
        db.execute(select(GymLicense)).scalar_one().expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
    status = license_case[0].get("/api/licencias/estado/synthetic-device-a")
    assert status.status_code == 200 and status.json()["activa"] is True
    assert status.json()["dias_restantes"] == 0


def test_team_member_cannot_issue_activation(license_case):
    license_case[2].update(role="admin", team_gym_id="license-owner-a")
    assert activate(license_case).status_code == 403
