"""Durable individual publication and conservative compensation, no providers."""
from fastapi import HTTPException
import pytest
from sqlalchemy import text

from tests.test_billing_integrity import billing_case  # noqa: F401


def reserved(factory, user, key='publication'):
    from web.services.generation_quota import reserve_generation
    with factory() as db:
        return reserve_generation(db, user, key).id


def publish(db, user, reservation):
    from web.database.repository import registrar_plan
    return registrar_plan(db, user, 'billing-profile', {'plan_json': '{}'},
        return_id=True, individual_reservation_id=reservation)


def observed(factory, reservation):
    from web.database.models import GenerationReservation, UserSubscription
    with factory() as db:
        row = db.get(GenerationReservation, reservation)
        return row.status, row.plan_id, row.persisted_at, db.query(UserSubscription).one().planes_usados_mes


def test_atomic_completion_is_verified_and_never_refunded(billing_case):
    from web.services.generation_quota import finish_generation
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        plan = publish(db, user['id'], identity)
        db.commit()
    status, linked, stamp, used = observed(factory, identity)
    assert (status, linked, used) == ('completed', plan, 1)
    assert stamp is not None
    with factory() as db:
        finish_generation(db, identity, user['id'], plan, success=True)
        finish_generation(db, identity, user['id'], None, success=False)
    assert observed(factory, identity) == (status, linked, stamp, used)


def test_success_cannot_adopt_an_unlinked_owned_plan(billing_case):
    from web.database.models import PlanGenerado
    from web.services.generation_quota import finish_generation
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        unrelated = PlanGenerado(gym_id=user['id'], id_cliente='billing-profile')
        db.add(unrelated)
        db.commit()
        with pytest.raises(HTTPException) as failure:
            finish_generation(db, identity, user['id'], unrelated.id, success=True)
        assert failure.value.status_code == 503
    assert observed(factory, identity) == ('reserved', None, None, 1)


@pytest.mark.parametrize('invalid', ['foreign', 'missing', 'legacy', 'released', 'completed'])
def test_repository_rejects_unavailable_individual_reservation(billing_case, invalid):
    from web.database.models import GenerationReservation, PlanGenerado
    from web.services.generation_quota import finish_generation
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    if invalid == 'released':
        with factory() as db:
            finish_generation(db, identity, user['id'], None, success=False)
    elif invalid == 'completed':
        with factory() as db:
            publish(db, user['id'], identity)
            db.commit()
    elif invalid == 'legacy':
        with factory() as db:
            db.get(GenerationReservation, identity).publication_protocol = 0
            db.commit()
    with factory() as db:
        count = db.query(PlanGenerado).count()
        with pytest.raises((ValueError, HTTPException)):
            publish(db, 'different-subject' if invalid == 'foreign' else user['id'],
                'missing' if invalid == 'missing' else identity)
        db.rollback()
        assert db.query(PlanGenerado).count() == count


def test_protocol_parameters_are_distinct_and_mutually_exclusive(billing_case):
    from web.database.repository import registrar_plan
    from web.services.plan_generation import generate_plan, build_plan
    _, factory, user = billing_case
    with factory() as db, pytest.raises(ValueError, match='mutually exclusive'):
        registrar_plan(db, user['id'], 'billing-profile', {}, reservation_id='gym', individual_reservation_id='person')
    for worker in (generate_plan, build_plan):
        with pytest.raises(ValueError, match='mutually exclusive'):
            worker('billing-profile', 1, user['id'], reservation_id='gym', individual_reservation_id='person')


def test_rollback_before_publication_returns_credit_exactly_once(billing_case):
    from web.database.models import PlanGenerado
    from web.services.generation_quota import compensate_individual_generation_failure
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        publish(db, user['id'], identity)
        db.rollback()
        compensate_individual_generation_failure(db, identity, user['id'])
        compensate_individual_generation_failure(db, identity, user['id'])
        assert db.query(PlanGenerado).count() == 0
    assert observed(factory, identity) == ('released', None, None, 0)


@pytest.mark.parametrize('legacy', [False, True])
def test_completed_consumption_survives_result_fk_set_null(billing_case, legacy):
    from web.database.models import GenerationReservation
    from web.services.generation_quota import finish_generation
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        plan = publish(db, user['id'], identity)
        db.commit()
        # This owned fixture enables the real FK action on its connection.
        db.execute(text('PRAGMA foreign_keys=ON'))
        db.execute(text('DELETE FROM planes_generados WHERE id=:id'), {'id': plan})
        db.commit()
        assert db.get(GenerationReservation, identity).plan_id is None
        if legacy:
            row = db.get(GenerationReservation, identity)
            row.publication_protocol, row.persisted_at = 0, None
            db.commit()
        finish_generation(db, identity, user['id'], None, success=False)
    status, plan, _, used = observed(factory, identity)
    assert (status, plan, used) == ('completed', None, 1)


def test_legacy_reserved_is_retained_without_guessing_a_result(billing_case):
    from web.database.models import GenerationReservation
    from web.services.generation_quota import finish_generation
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        db.get(GenerationReservation, identity).publication_protocol = 0
        db.commit()
        with pytest.raises(HTTPException) as failure:
            finish_generation(db, identity, user['id'], None, success=False)
        assert failure.value.detail['code'] == 'generation_reconciliation_required'
    assert observed(factory, identity) == ('reserved', None, None, 1)


def test_old_period_compensation_does_not_debit_the_new_month(billing_case):
    from web.database.models import GenerationReservation, UserSubscription
    from web.services.generation_quota import finish_generation
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        db.get(GenerationReservation, identity).period = '2000-01'
        db.query(UserSubscription).one().planes_usados_mes = 1
        db.commit()
        finish_generation(db, identity, user['id'], None, success=False)
    assert observed(factory, identity) == ('released', None, None, 1)


@pytest.mark.parametrize('failure', ['rollback', 'read', 'release_commit'])
def test_uncertain_compensation_is_sanitized_and_idempotent(billing_case, monkeypatch, caplog, failure):
    from sqlalchemy.exc import StatementError
    from web.services import generation_quota
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    marker = 'synthetic-private-sql-parameter'
    error = StatementError('Synthetic failure', 'UPDATE synthetic SET private=:value', {'value': marker}, RuntimeError(marker))
    with factory() as db:
        if failure == 'rollback':
            monkeypatch.setattr(db, 'rollback', lambda: (_ for _ in ()).throw(error))
        elif failure == 'read':
            monkeypatch.setattr(generation_quota, '_lock_account', lambda *args: (_ for _ in ()).throw(error))
        else:
            original = db.commit
            def committed_then_failed():
                original()
                raise error
            monkeypatch.setattr(db, 'commit', committed_then_failed)
        with pytest.raises(HTTPException) as uncertain:
            generation_quota.compensate_individual_generation_failure(db, identity, user['id'])
        assert uncertain.value.status_code == 503
        assert marker not in str(uncertain.value.detail) + caplog.text
    monkeypatch.undo()
    if failure == 'release_commit':
        assert observed(factory, identity) == ('released', None, None, 0)
        with factory() as db:
            generation_quota.compensate_individual_generation_failure(db, identity, user['id'])
        assert observed(factory, identity) == ('released', None, None, 0)
    else:
        assert observed(factory, identity) == ('reserved', None, None, 1)


def test_committed_but_unacknowledged_publication_is_not_compensated(billing_case):
    from web.services.generation_quota import compensate_individual_generation_failure
    _, factory, user = billing_case
    identity = reserved(factory, user['id'])
    with factory() as db:
        publish(db, user['id'], identity)
        db.commit()
        try:
            raise RuntimeError('Synthetic lost COMMIT acknowledgement')
        except RuntimeError:
            compensate_individual_generation_failure(db, identity, user['id'])
    assert observed(factory, identity)[0] == 'completed'
    assert observed(factory, identity)[3] == 1
