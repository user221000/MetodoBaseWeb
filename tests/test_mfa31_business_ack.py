"""The grant's durable transaction owns the ACK, including uncertainty."""
import pytest
from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate


@pytest.mark.parametrize("after_real_commit", [False, True])
def test_business_commit_failure_is_visible_without_returning_external_capability(mfa_client, monkeypatch, caplog, after_real_commit):
    client, actor, clock = mfa_client
    from web.services import stripe_service
    from web.database.engine import get_engine
    from web.database.models import MfaAuthorization
    from web.services.mfa_crypto import opaque_digest
    calls = []
    monkeypatch.setattr(stripe_service,"create_portal_session",lambda **kwargs:calls.append(kwargs) or {"url":"https://provider.example.invalid/portal"})
    _, done = enroll(client,clock)
    authenticate(client,actor,clock,recovery=done["recovery_codes"][0])
    body = {"return_url":"/dashboard"}
    issued = client.post("/api/auth/mfa/step-up",json={"method":"POST","path":"/api/billing/portal","body":body})
    assert issued.status_code == 200
    token = issued.json()["grant"]
    actual_commit = Session.commit
    def uncertain(db):
        if after_real_commit:
            actual_commit(db)
        raise RuntimeError("synthetic-sensitive-driver-message")
    with monkeypatch.context() as patch:
        patch.setattr(Session,"commit",uncertain)
        response = client.post("/api/billing/portal",json=body,headers={"X-MFA-Grant":token})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "mfa_unconfirmed"
    assert calls == []
    assert "synthetic-sensitive-driver-message" not in response.text + caplog.text
    assert token not in caplog.text
    with Session(get_engine()) as db:
        proof = db.get(MfaAuthorization,opaque_digest("action",token))
        assert (proof.consumed_at is not None) is after_real_commit
    retry = client.post("/api/billing/portal",json=body,headers={"X-MFA-Grant":token})
    assert retry.status_code == (400 if after_real_commit else 200)
    assert len(calls) == (0 if after_real_commit else 1)
