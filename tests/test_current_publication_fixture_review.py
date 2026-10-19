"""Real current31 fixture adoption must keep the privileged action barrier."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.current_google33_publication_fixtures import case, http, link_db  # noqa: F401


@pytest.mark.parametrize("link_db", ["sqlite"], indirect=True)
def test_actual_factor_login_does_not_grant_a_privileged_mutation(http, monkeypatch):
    from web.database.models import MfaCredential, MfaRecoveryCode, Usuario
    from web.services import stripe_service

    identities = [http[key] for key in ("gym", "othergym", "person", "other")]
    with Session(http["admin"]) as db:
        for identity in identities:
            factor = db.get(MfaCredential, identity)
            assert factor.enabled_at is not None and factor.generation == 1
            assert factor.secret_ciphertext is not None and factor.pending_ciphertext is None
            codes = db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == identity)).all()
            assert len(codes) == 8 and sum(code.used_at is not None for code in codes) == 1
        before = db.scalar(select(func.count()).select_from(Usuario))
    path = "/api/billing/portal"
    assert path in http["client_http"].app.openapi()["paths"]
    ports = []
    monkeypatch.setattr(stripe_service, "create_portal_session", lambda *args, **kwargs: ports.append(True))
    response = http["client_http"].post(path, headers=http["headers"]["gym"],
        json={"return_url": "/dashboard"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "mfa_step_up_required"
    assert http["mail"] == [] and ports == []
    with Session(http["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(Usuario)) == before
