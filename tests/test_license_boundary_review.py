"""Independent SEC01 checks through real persisted JWT authorization."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def issued_owner(test_gym_user):
    from web.database.engine import get_engine
    from web.database.models import GymLicense

    with Session(get_engine()) as db:
        issued = GymLicense(gym_id=test_gym_user["id"], license_key="synthetic-review-issued-key",
                            plan_tier="standard", max_clients=23, is_active=True,
                            expires_at=datetime.now(timezone.utc) + timedelta(days=7))
        db.add(issued)
        db.commit()
    return test_gym_user


def activate(client, **changes):
    payload = {"clave": "synthetic-review-issued-key", "hardware_id": "review-device-123",
               "email": "synthetic-contact@example.invalid"}
    return client.post("/api/licencias/activar", json={**payload, **changes})


def test_real_owner_token_uses_issued_rights_without_creating_subscriptions(auth_client, issued_owner):
    from web.database.engine import get_engine
    from web.database.models import LicenseActivation, Subscription, UserSubscription

    result = activate(auth_client)
    assert result.status_code == 200, result.text
    assert result.json()["plan"] == "standard" and result.json()["max_clientes"] == 23
    assert auth_client.get("/api/licencias/estado/review-device-123").json()["activa"] is True
    with Session(get_engine()) as db:
        activation = db.execute(select(LicenseActivation)).scalar_one()
        assert activation.gym_id == issued_owner["id"]
        assert db.execute(select(Subscription)).first() is None
        assert db.execute(select(UserSubscription)).first() is None


@pytest.mark.parametrize("change,expected", [("role", 403), ("inactive", 401), ("version", 401), ("team", 401)])
def test_old_signed_token_cannot_override_current_owner_authority(auth_client, issued_owner, change, expected):
    from web.database.engine import get_engine
    from web.database.models import LicenseActivation, Usuario, UserRole

    with Session(get_engine()) as db:
        user = db.get(Usuario, issued_owner["id"])
        if change == "role":
            user.role = UserRole.VIEWER
        elif change == "inactive":
            user.activo = False
        elif change == "version":
            user.session_version += 1
        else:
            other = Usuario(id="review-other-gym", email="other-license@example.invalid", nombre="Other",
                            password_hash="synthetic-unused", tipo="gym", role=UserRole.OWNER)
            db.add(other)
            db.flush()
            user.team_gym_id = other.id
            user.role = UserRole.ADMIN
        db.commit()
    assert activate(auth_client).status_code == expected
    assert auth_client.get("/api/licencias/estado/review-device-123").status_code == expected
    with Session(get_engine()) as db:
        assert db.execute(select(LicenseActivation)).first() is None


def test_current_professional_token_is_authenticated_but_not_an_owner(auth_client, issued_owner):
    from web.auth import crear_access_token, identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole

    with Session(get_engine()) as db:
        member = Usuario(id="review-license-member", email="license-member@example.invalid", nombre="Member",
                         password_hash="synthetic-unused", tipo="usuario", role=UserRole.ADMIN,
                         team_gym_id=issued_owner["id"], activo=True)
        db.add(member)
        db.commit()
        token = crear_access_token(identity_from_user(member, db))
    auth_client.headers["Authorization"] = "Bearer " + token
    assert activate(auth_client).status_code == 403
    assert auth_client.get("/api/licencias/estado/review-device-123").status_code == 403


def test_existing_expiry_cannot_be_extended_by_editing_issuer_or_repeat(auth_client, issued_owner):
    from web.database.engine import get_engine
    from web.database.models import GymLicense, LicenseActivation

    assert activate(auth_client).status_code == 200
    with Session(get_engine()) as db:
        activation = db.execute(select(LicenseActivation)).scalar_one()
        original = activation.expira
        db.execute(select(GymLicense)).scalar_one().expires_at = None
        db.commit()
    assert activate(auth_client).status_code == 200
    with Session(get_engine()) as db:
        assert db.execute(select(LicenseActivation)).scalar_one().expira == original


def test_status_rechecks_issuer_revocation_and_shorter_expiry(auth_client, issued_owner):
    from web.database.engine import get_engine
    from web.database.models import GymLicense

    assert activate(auth_client).status_code == 200
    with Session(get_engine()) as db:
        db.execute(select(GymLicense)).scalar_one().expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert auth_client.get("/api/licencias/estado/review-device-123").json()["activa"] is False
    with Session(get_engine()) as db:
        db.execute(select(GymLicense)).scalar_one().revoked_at = datetime.now(timezone.utc)
        db.commit()
    state = auth_client.get("/api/licencias/estado/review-device-123").json()
    assert state["activa"] is False and state["revocada"] is True


def test_unassociated_legacy_hardware_cannot_be_claimed_by_email(auth_client, issued_owner):
    from web.database.engine import get_engine
    from web.database.models import LicenseActivation

    with Session(get_engine()) as db:
        db.add(LicenseActivation(hardware_id="review-device-123", clave_hash="synthetic-unknown-legacy-hash",
                                email=issued_owner["email"], plan="clinica", activa=True, revocada=False))
        db.commit()
    assert activate(auth_client, email=issued_owner["email"]).status_code == 409
    assert auth_client.get("/api/licencias/estado/review-device-123").status_code == 404
    with Session(get_engine()) as db:
        activation = db.execute(select(LicenseActivation)).scalar_one()
        assert activation.gym_id is None and activation.issued_license_id is None


@pytest.mark.parametrize("untrusted_key", ["\u00f1-invalid-license", "\uff11\uff12-invalid-license"])
def test_unicode_key_is_rejected_without_exception_or_remote_request(tmp_path, monkeypatch, untrusted_key):
    from core.licencia import GestorLicencias

    monkeypatch.setattr(GestorLicencias, "ARCHIVO_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setattr(GestorLicencias, "ARCHIVO_LICENCIA", str(tmp_path / "license.json"))
    monkeypatch.setattr(GestorLicencias, "_CACHE_DB", str(tmp_path / "cache.sqlite"))
    manager = GestorLicencias()
    manager.SALT_MASTER = "synthetic-independent-license-test"
    issued = manager.generar_key_activacion(manager.obtener_id_instalacion(), 6)
    assert manager.activar_licencia_con_key("Synthetic License Gym", issued, 6)[0]

    def unexpected_request(*args, **kwargs):
        pytest.fail("An invalid license key must not contact a remote service")

    monkeypatch.setattr("urllib.request.urlopen", unexpected_request)
    assert manager.validar_licencia_online(untrusted_key)[0] is False
