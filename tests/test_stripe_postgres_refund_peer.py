"""Current migrated restricted-role refund, RLS and untouched foreign quota."""
from copy import deepcopy

import pytest
import stripe
from sqlalchemy.orm import Session

from tests.test_stripe_postgres_authority_peer import migration_database, pg_invoice
from tests.test_stripe_invoice_authority_peer import SURFACES, deliver
from tests.test_stripe_refund_ledger_peer import make_paid, set_refunded, refund_event


@pytest.mark.parametrize('surface', SURFACES)
def test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota(pg_invoice, monkeypatch, surface):
    case, app, admin = pg_invoice
    factory, actor, state = case
    from web.database.models import Payment, UserSubscription
    from web.database.tenant_context import tenant_scope
    from web.services.stripe_service import get_payment_history
    client = make_paid(case, surface)
    actual = set_refunded(state)
    monkeypatch.setattr(stripe.Charge, 'retrieve', lambda *a, **kw: deepcopy(actual))
    event = refund_event(actual)
    response = deliver(client, surface[1], event)
    assert response.status_code == 200, response.text
    replay = deliver(client, surface[1], event)
    assert replay.status_code == 200 and replay.json()['result'] == 'duplicate:charge.refunded'
    with Session(admin) as db:
        payment = db.query(Payment).one()
        assert (payment.gym_id,payment.amount_cents,payment.currency,payment.status) == (actor['id'],7900,'mxn','refunded')
        assert db.query(UserSubscription).filter_by(user_id=actor['id']).one().plan == 'starter'
        other = db.query(UserSubscription).filter_by(user_id='pg-peer-b').one()
        assert (other.plan,other.max_planes_mes,other.planes_usados_mes) == ('starter',1,1)
    with tenant_scope('pg-peer-b'), factory() as db:
        assert get_payment_history(db, 'pg-peer-b') == []
        assert db.query(Payment).count() == 0
    with tenant_scope(actor['id']), factory() as db:
        assert get_payment_history(db, actor['id'])[0]['status'] == 'refunded'
