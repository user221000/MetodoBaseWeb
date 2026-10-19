"""Secondary authentication never makes an unsafe external capability safe."""
from types import SimpleNamespace

from sqlalchemy.orm import Session

from tests.test_mfa31_http import mfa_client, enroll, authenticate


def test_privileged_portal_rejects_authority_component_in_return_path(mfa_client, monkeypatch):
    import stripe
    from web.settings import get_settings
    from web.database.engine import get_engine
    from web.database.models import Subscription
    from web.services import stripe_service
    client, actor, clock = mfa_client
    monkeypatch.setattr(get_settings(), "BASE_URL", "https://app.example.invalid")
    monkeypatch.setattr(stripe_service, "_init_stripe", lambda: True)
    calls = []
    monkeypatch.setattr(stripe.billing_portal.Session, "create", lambda **kw: calls.append(kw) or SimpleNamespace(url="https://provider.example.invalid/portal"))
    with Session(get_engine()) as db:
        db.add(Subscription(gym_id=actor["id"], plan="standard", status="active",
            provider="stripe", stripe_customer_id="cus_synthetic_mfa"))
        db.commit()
    _, enabled = enroll(client, clock)
    authenticate(client, actor, clock, recovery=enabled["recovery_codes"][0])
    body = {"return_url":"@outside.example.invalid/path"}
    grant = client.post("/api/auth/mfa/step-up", json={"method":"POST","path":"/api/billing/portal","body":body})
    assert grant.status_code == 400
    assert calls == []
