"""Independent accounting-period boundary tests against real persisted state."""
from tests.test_billing_integrity import billing_case  # noqa: F401


def reserve_across_month_boundary(factory, subject, monkeypatch):
    from web.database.models import UserSubscription
    from web.services import billing_integrity, generation_quota
    with factory() as db:
        db.add(UserSubscription(user_id=subject, plan='starter', max_planes_mes=1,
            planes_usados_mes=0, mes_actual='2032-10', status='active'))
        db.commit()
    periods = iter(['2032-10', '2032-10', '2032-11'])
    def clock():
        return next(periods, '2032-11')
    monkeypatch.setattr(billing_integrity, 'current_quota_period', clock)
    monkeypatch.setattr(generation_quota, 'current_quota_period', clock)
    with factory() as db:
        return generation_quota.reserve_generation(db, subject, 'boundary-old').id


def test_reserved_period_is_the_month_actually_debited(billing_case, monkeypatch):
    from web.database.models import GenerationReservation, UserSubscription
    _, factory, principal = billing_case
    identity = reserve_across_month_boundary(factory, principal['id'], monkeypatch)
    with factory() as db:
        reservation = db.get(GenerationReservation, identity)
        projection = db.query(UserSubscription).one()
        assert projection.planes_usados_mes == 1
        assert reservation.period == projection.mes_actual == '2032-10'


def test_late_refund_does_not_return_the_next_months_other_credit(billing_case, monkeypatch):
    from web.database.models import UserSubscription
    from web.services import billing_integrity, generation_quota
    _, factory, principal = billing_case
    identity = reserve_across_month_boundary(factory, principal['id'], monkeypatch)
    monkeypatch.setattr(billing_integrity, 'current_quota_period', lambda: '2032-11')
    monkeypatch.setattr(generation_quota, 'current_quota_period', lambda: '2032-11')
    with factory() as db:
        generation_quota.reserve_generation(db, principal['id'], 'boundary-new')
    with factory() as db:
        generation_quota.finish_generation(db, identity, principal['id'], None, success=False)
    with factory() as db:
        projection = db.query(UserSubscription).one()
        assert projection.mes_actual == '2032-11'
        assert projection.planes_usados_mes == 1
