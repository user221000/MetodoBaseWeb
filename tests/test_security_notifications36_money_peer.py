"""Independent provider contradiction boundary through both real factories."""
from tests.notifications36_http import followup_db as followup_db, notification_http as notification_http
from tests.test_notifications36_http import billing, candidate, observe


def test_provider_paid_above_total_never_becomes_confirmed_arrears(notification_http, monkeypatch):
    case = notification_http
    _subscription, invoice = billing(case, monkeypatch)
    invoice["amount_paid"] = invoice["amount_due"] * 2
    assert invoice["amount_remaining"] > 0 and invoice["paid"] is False
    response = observe(case)
    assert response.status_code in {200, 503}
    current = candidate(case)
    assert current["eligible"] is False
