"""Portal return destinations keep the configured origin before SDK dispatch."""
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from sqlalchemy.orm import Session


@pytest.mark.parametrize("path,valid", [("@outside.example.invalid/path",False),
    ("//outside.example.invalid",False),("https://outside.example.invalid",False),
    ("javascript:alert(1)",False),("/\\outside",False),("/usuario\n",False),
    ("/usuario\x7f",False),(" /usuario",False),("/usuario",True),
    ("/usuario?billing=return#plan",True),("/dashboard?x=1",True),
    ("/suscripciones",True),("/configuracion#billing",True)])
def test_portal_rejects_invalid_destinations_before_external_port_and_preserves_valid_private_paths(test_gym_user, monkeypatch, path, valid):
    import stripe
    from web.database.engine import get_engine
    from web.database.models import Subscription
    from web.services import stripe_service
    from web.services.return_paths import private_return_path
    from web.settings import get_settings
    calls = []
    monkeypatch.setattr(get_settings(),"BASE_URL","https://app.example.invalid")
    monkeypatch.setattr(stripe_service,"_init_stripe",lambda:True)
    monkeypatch.setattr(stripe.billing_portal.Session,"create",lambda **kwargs:calls.append(kwargs) or SimpleNamespace(url="https://provider.example.invalid/portal"))
    with Session(get_engine()) as db:
        db.add(Subscription(gym_id=test_gym_user["id"],plan="standard",status="active",provider="stripe",stripe_customer_id="cus_synthetic_return_review"))
        db.commit()
        if not valid:
            with pytest.raises(ValueError):
                private_return_path(path)
            with pytest.raises(ValueError):
                stripe_service.create_portal_session(db,test_gym_user["id"],path)
            assert calls == []
        else:
            assert private_return_path(path) == path
            assert stripe_service.create_portal_session(db,test_gym_user["id"],path) == {"url":"https://provider.example.invalid/portal"}
            assert calls == [{"customer":"cus_synthetic_return_review","return_url":"https://app.example.invalid"+path}]
            assert urlsplit(calls[0]["return_url"]).hostname == "app.example.invalid"
