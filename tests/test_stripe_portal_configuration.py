"""Portal configuration is operator-owned and cannot change the account scope."""
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session


@pytest.mark.parametrize("configuration", ["", "bpc_operator_selected"])
def test_portal_uses_operator_configuration_with_the_authenticated_customer(
    test_gym_user, monkeypatch, configuration,
):
    import stripe
    from web.database.engine import get_engine
    from web.database.models import Subscription
    from web.services import stripe_service
    from web.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "BASE_URL", "https://app.example.invalid")
    monkeypatch.setattr(settings, "STRIPE_PORTAL_CONFIGURATION_ID", configuration)
    monkeypatch.setattr(stripe_service, "_init_stripe", lambda: True)
    calls = []
    monkeypatch.setattr(
        stripe.billing_portal.Session,
        "create",
        lambda **params: calls.append(params) or SimpleNamespace(
            url="https://billing.stripe.com/synthetic-portal",
        ),
    )
    with Session(get_engine()) as db:
        db.add(Subscription(
            gym_id=test_gym_user["id"], plan="standard", status="active",
            provider="stripe", stripe_customer_id="cus_authenticated_owner",
        ))
        db.commit()
        assert stripe_service.create_portal_session(
            db, test_gym_user["id"], "/suscripciones",
        ) == {"url": "https://billing.stripe.com/synthetic-portal"}
    expected = {
        "customer": "cus_authenticated_owner",
        "return_url": "https://app.example.invalid/suscripciones",
    }
    if configuration:
        expected["configuration"] = configuration
    assert calls == [expected]
