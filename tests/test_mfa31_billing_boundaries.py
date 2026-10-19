"""Secondary authentication never makes an unsafe external capability safe."""
from types import SimpleNamespace
from urllib.parse import urlsplit
import pytest

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


def test_portal_service_rejects_relative_authority_before_stripe_port(mfa_client, monkeypatch):
    import stripe
    from web.settings import get_settings
    from web.database.engine import get_engine
    from web.database.models import Subscription
    from web.services import stripe_service
    _, actor, _ = mfa_client
    monkeypatch.setattr(get_settings(), "BASE_URL", "https://app.example.invalid")
    monkeypatch.setattr(stripe_service, "_init_stripe", lambda: True)
    calls = []
    monkeypatch.setattr(stripe.billing_portal.Session, "create", lambda **kw: calls.append(kw) or SimpleNamespace(url="https://provider.example.invalid/portal"))
    with Session(get_engine()) as db:
        db.add(Subscription(gym_id=actor["id"], plan="standard", status="active", provider="stripe", stripe_customer_id="cus_synthetic_mfa"))
        db.commit()
        try:
            stripe_service.create_portal_session(db, actor["id"], "@outside.example.invalid/path")
        except ValueError:
            assert calls == []
        else:
            # Before witness: the actual captured SDK argument changes host.
            assert urlsplit(calls[0]["return_url"]).hostname == "app.example.invalid"
            pytest.fail("Invalid relative path must be rejected, not sanitized")


@pytest.mark.parametrize("path", ["/usuario", "/usuario?billing=return#plan", "/dashboard?x=1", "/suscripciones", "/configuracion#billing"])
def test_existing_individual_and_professional_relative_paths_preserved(path):
    from web.services.return_paths import private_return_path
    assert private_return_path(path) == path


@pytest.mark.parametrize("path", ["@outside.example.invalid/path", "//outside.example.invalid", "https://outside.example.invalid", "javascript:alert(1)", "/\\outside", "/usuario\n", "/usuario\x7f", " /usuario"])
def test_origin_backslash_controls_and_scheme_rejected_whole(path):
    from web.services.return_paths import private_return_path
    with pytest.raises(ValueError): private_return_path(path)
