"""Contradictory monetary observations never become a reminder authority."""
from dataclasses import replace

import pytest

from tests.test_notifications36_domain import NOW, fact, source
from web.services.notification_domain import qualifies


@pytest.mark.parametrize("paid,remaining", [(20000, 10000), (6000, 6000), (0, 10001), (10000, 1), (1, 10000)])
def test_stripe_contradictory_balances_are_not_verified(paid, remaining):
    with pytest.raises(ValueError):
        replace(source(), amount_paid=paid, amount_remaining=remaining).validate()


@pytest.mark.parametrize("paid,remaining", [(0, 10000), (4000, 6000)])
def test_stripe_partial_or_unpaid_consistent_balance_still_qualifies(paid, remaining):
    snapshot = replace(source(), amount_paid=paid, amount_remaining=remaining).validate()
    assert snapshot.amount_paid == paid
    assert qualifies(fact(amount_paid=paid, amount_remaining=remaining), "confirmed_payment_issue", NOW)


def test_paid_status_with_false_paid_flag_is_not_verified():
    with pytest.raises(ValueError):
        replace(source(), invoice_status="paid", amount_paid=10000, amount_remaining=0).validate()


@pytest.mark.parametrize("paid,remaining", [(20000, 10000), (6000, 6000), (0, True), (False, 10000)])
@pytest.mark.parametrize("purpose", ["confirmed_payment_issue", "account_period_end"])
def test_persisted_untyped_or_contradictory_amounts_never_qualify(paid, remaining, purpose):
    changes = {"amount_paid": paid, "amount_remaining": remaining}
    if purpose == "account_period_end":
        changes.update(subscription_status="active", invoice_status="paid", paid=True)
    assert not qualifies(fact(**changes), purpose, NOW)
