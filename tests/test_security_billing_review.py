"""Independent regression for stale events crossing payment providers."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.test_billing_integrity import billing_case, _paid_snapshot  # noqa: F401


def test_old_stripe_cancellation_cannot_revoke_current_mercadopago_purchase(billing_case):
    from web.database.models import Subscription, UserSubscription
    from web.services.stripe_service import reconcile_subscription, _on_subscription_deleted
    from web.services.subscription_service import activate_subscription

    _, factory, principal = billing_case
    snapshot = _paid_snapshot(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
            now = datetime.now(timezone.utc)
            current = activate_subscription(db, principal["id"], "pro_usuario", provider="mercadopago",
                current_period_start=now, current_period_end=now + timedelta(days=30))
            current.provider_payment_id = "synthetic-current-mp-payment"
            db.commit()

        # The old provider reports cancellation after the other purchase funded
        # access. Every record and provider response is synthetic and isolated.
        snapshot["status"] = "canceled"
        with factory() as db:
            _on_subscription_deleted(db, {"id": "sub_person"})
            db.commit()
            current = db.query(Subscription).filter_by(gym_id=principal["id"]).one()
            assert current.provider == "mercadopago"
            assert current.provider_payment_id == "synthetic-current-mp-payment"
            assert current.status == "active"
            assert db.query(UserSubscription).filter_by(user_id=principal["id"]).one().plan == "pro"
