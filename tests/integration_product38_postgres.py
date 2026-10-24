"""Separate current38 PG facts/origin/security plus original four new races.

One owned UUID, app1/0 and explicit admin observer2/0; race workers each own
another app1/0. Imports do no SQL. No providers, SQLite fallback or skips.
"""
from datetime import datetime, timezone
import json
import uuid
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from tests import integration_client_link_services as actors
from tests import integration_product38_concurrency as races
from tests.ci_web38.pg_fixtures import (database_schema, isolated_database, link_db,
    pg38_database, pg38_runtime, released)  # noqa: F401 -- explicit fixture composition
from tests.ci_web38.pg_physical import physical_contract
from web.database.models import PlanGenerado, ProductAnalyticsFact as Fact, Usuario, UserRole
from web.database.repository import registrar_plan
from web.database.tenant_context import tenant_scope
from web.services import product_facts
from web.services.product_analytics_v2 import origin, read_report

case = actors.case


def claims(value, who='gym'):
    with Session(value['admin']) as db:
        row = db.get(Usuario, value[who])
        return {'id': row.id, 'tipo': row.tipo, 'role': row.role.value,
                'team_gym_id': row.team_gym_id, 'session_version': row.session_version}


def declare(value, label, version, *, who='gym', context='gym', client=None):
    with Session(value['app']) as db:
        return origin(db, claims(value, who), context,
            (client or value['client']) if context == 'gym' else None,
            value=label, expected_version=version)


def save_plan(value, *, commit=True):
    raw = json.dumps({meal: {'kcal_objetivo': 100, 'kcal_real': 100, 'alimentos': {'synthetic': 50}}
                     for meal in ('desayuno', 'almuerzo', 'comida', 'cena')})
    with tenant_scope(value['gym']), Session(value['app']) as db:
        identity = registrar_plan(db, value['gym'], value['client'], {'plan_json': raw}, return_id=True)
        assert type(identity) is int
        if commit:
            db.commit()
        else:
            db.rollback()
        return identity


def test_real38_role_force_no_context_and_cross_tenant_are_enforced(case):
    observed = physical_contract(case['app'])
    assert observed['role_five_flags'] == [False] * 5 and observed['new_table_FORCE_RLS'] is True
    declare(case, 'demo', 0)
    with Session(case['app']) as db:
        assert db.scalars(select(Fact.id)).all() == []
    with Session(case['app']) as db, pytest.raises(DBAPIError):
        product_facts.append(db, case['gym'], 'gym', case['client'], 'origin_declared',
                             case['client'], 2, 'customer')
        db.commit()
    with tenant_scope(case['othergym']), Session(case['app']) as db:
        assert db.scalars(select(Fact.id).where(Fact.owner_id == case['gym'])).all() == []
    with tenant_scope(case['othergym']), Session(case['app']) as db, pytest.raises(DBAPIError):
        product_facts.append(db, case['gym'], 'gym', case['client'], 'origin_declared',
                             case['client'], 2, 'customer')
        db.commit()
    with Session(case['admin']) as db:
        assert db.query(Fact).filter_by(owner_id=case['gym']).count() == 1


def test_owner_personal_admin_viewer_and_foreign_client_authority(case):
    declare(case, 'demo', 0)
    for label, role in (('admin_member', UserRole.ADMIN), ('viewer', UserRole.VIEWER)):
        identity = str(uuid.uuid4())
        case[label] = identity
        with Session(case['admin']) as db:
            db.add(Usuario(id=identity, email=identity + '@example.invalid', password_hash='not-a-login',
                nombre='Synthetic38', tipo='usuario', role=role, team_gym_id=case['gym']))
            db.commit()
        with Session(case['app']) as db:
            assert origin(db, claims(case, label), 'gym', case['client'])['origin'] == 'demo'
        with pytest.raises(HTTPException) as denied:
            declare(case, 'customer', 1, who=label)
        assert denied.value.status_code == 403
        assert declare(case, 'demo', 0, who=label, context='personal')['origin'] == 'demo'
    assert declare(case, 'unknown', 0, who='person', context='personal')['version'] == 1
    with pytest.raises(HTTPException) as foreign:
        declare(case, 'customer', 1, client=case['otherclient'])
    assert foreign.value.status_code == 404
    # Existing aggregate analytics permission stays owner/admin; viewer client
    # origin reads do not imply a new global analytics permission or any write.
    report = read_report(claims(case, 'admin_member'), 'gym', session_factory=sessionmaker(bind=case['app']))
    assert report['baseline']['targets'] is None
    with pytest.raises(HTTPException) as denied:
        read_report(claims(case, 'viewer'), 'gym', session_factory=sessionmaker(bind=case['app']))
    assert denied.value.status_code == 403


def test_append_atomic_rollback_immutable_server_clock_and_source_binding(case):
    declare(case, 'demo', 0)
    rolled = save_plan(case, commit=False)
    with Session(case['admin']) as db:
        assert db.get(PlanGenerado, rolled) is None
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='plan_saved').count() == 0
    identity = save_plan(case)
    with Session(case['admin']) as db:
        saved = db.scalar(select(Fact).where(Fact.owner_id == case['gym'], Fact.event_type == 'plan_saved'))
        snapshot = (saved.id, saved.origin, saved.occurred_at, saved.source_id)
    def complete_fact_snapshot():
        with Session(case['admin']) as db:
            rows = db.scalars(select(Fact).where(Fact.owner_id == case['gym']).order_by(Fact.id)).all()
            return tuple(tuple(getattr(row, column.key) for column in Fact.__table__.columns) for row in rows)

    immutable_before = complete_fact_snapshot()
    for sql in ("UPDATE product_analytics_facts SET origin='customer' WHERE owner_id=:owner",
                "DELETE FROM product_analytics_facts WHERE owner_id=:owner"):
        # With no app UPDATE/DELETE policy, RLS default-deny filters all rows.
        # The privileged same-SQL probe separately proves the append-only trigger.
        with tenant_scope(case['gym']), Session(case['app']) as db:
            result = db.execute(text(sql), {'owner': case['gym']})
            assert result.rowcount == 0
            db.rollback()
        assert complete_fact_snapshot() == immutable_before
        with Session(case['admin']) as db, pytest.raises(DBAPIError):
            db.execute(text(sql), {'owner': case['gym']})
            db.commit()
        assert complete_fact_snapshot() == immutable_before
    with tenant_scope(case['gym']), Session(case['app']) as db, pytest.raises(DBAPIError):
        product_facts.append(db, case['gym'], 'gym', case['client'], 'plan_saved', '999999999999', 1, 'demo')
        db.commit()
    with tenant_scope(case['gym']), Session(case['app']) as db:
        before = db.scalar(text("SELECT clock_timestamp() AT TIME ZONE 'UTC'"))
        db.add(Fact(owner_id=case['gym'], context='gym', client_id=case['client'],
            event_type='origin_declared', source_id=case['client'], source_version=2,
            origin='customer', occurred_at=datetime(2000, 1, 1, tzinfo=timezone.utc)))
        db.commit()
    with Session(case['admin']) as db:
        latest = db.scalar(select(Fact).where(Fact.owner_id == case['gym'], Fact.event_type == 'origin_declared', Fact.source_version == 2))
        assert latest.occurred_at.replace(tzinfo=None) >= before.replace(tzinfo=None)
        original = db.scalar(select(Fact).where(Fact.owner_id == case['gym'], Fact.event_type == 'plan_saved'))
        assert (original.id, original.origin, original.occurred_at, original.source_id) == snapshot
        assert original.source_id == str(identity)


# Literal original function objects and assertions; their own globals/helpers
# remain in races. The only transport is this module's actual38 link_db fixture.
test_revoked_session_while_origin_waits_on_owner_cannot_commit = races.test_revoked_session_while_origin_waits_on_owner_cannot_commit
test_acceptance_first_preserves_prior_origin_then_declaration_applies_to_future = races.test_acceptance_first_preserves_prior_origin_then_declaration_applies_to_future
test_declaration_first_retains_R12_nowait_then_explicit_accept_retry_snapshots_demo = races.test_declaration_first_retains_R12_nowait_then_explicit_accept_retry_snapshots_demo
test_plan_fact_replay_after_new_classification_preserves_original_snapshot = races.test_plan_fact_replay_after_new_classification_preserves_original_snapshot


def test_exact_plan_source_replay_keeps_first_snapshot_and_outer_transaction_commits(case, monkeypatch):
    declare(case, 'demo', 0)
    original_plan = save_plan(case)
    with Session(case['admin']) as db:
        row = db.scalar(select(Fact).where(Fact.owner_id == case['gym'],
            Fact.event_type == 'plan_saved', Fact.source_id == str(original_plan), Fact.source_version == 1))
        first = tuple(getattr(row, column.key) for column in Fact.__table__.columns)
        original_fact_id = row.id
        payload = db.get(PlanGenerado, original_plan).plan_json
    declare(case, 'customer', 1)
    replay_id = uuid.uuid4().hex
    assert replay_id != original_fact_id
    with tenant_scope(case['gym']), Session(case['app']) as db:
        # The replay has a fresh identity and the now-current legitimate origin.
        # Neither may replace the original source's persisted snapshot.
        with monkeypatch.context() as selected_identity:
            selected_identity.setattr(product_facts.uuid, 'uuid4', lambda: SimpleNamespace(hex=replay_id))
            product_facts.append(db, case['gym'], 'gym', case['client'],
                                 'plan_saved', original_plan, 1, 'customer')
        later_plan = registrar_plan(db, case['gym'], case['client'], {'plan_json': payload}, return_id=True)
        assert type(later_plan) is int and later_plan != original_plan
        db.commit()
    with Session(case['admin']) as db:
        rows = db.scalars(select(Fact).where(Fact.owner_id == case['gym'],
            Fact.event_type == 'plan_saved', Fact.source_id == str(original_plan), Fact.source_version == 1)).all()
        assert len(rows) == 1
        assert tuple(getattr(rows[0], column.key) for column in Fact.__table__.columns) == first
        assert rows[0].id == original_fact_id and rows[0].origin == 'demo'
        assert db.get(Fact, replay_id) is None
        assert db.get(PlanGenerado, later_plan) is not None
        later = db.scalars(select(Fact).where(Fact.owner_id == case['gym'],
            Fact.event_type == 'plan_saved', Fact.source_id == str(later_plan), Fact.source_version == 1)).all()
        assert len(later) == 1 and later[0].origin == 'customer'


def test_unrelated_fact_primary_key_collision_propagates_and_rolls_back_business_plan(case, monkeypatch):
    declare(case, 'demo', 0)
    original_plan = save_plan(case)
    with Session(case['admin']) as db:
        original_fact = db.scalar(select(Fact).where(Fact.owner_id == case['gym'],
            Fact.event_type == 'plan_saved', Fact.source_id == str(original_plan), Fact.source_version == 1))
        collision_id = original_fact.id
        payload = db.get(PlanGenerado, original_plan).plan_json
        before = tuple(tuple(getattr(row, column.key) for column in Fact.__table__.columns)
                       for row in db.scalars(select(Fact).where(Fact.owner_id == case['gym']).order_by(Fact.id)))
        primary_key = db.scalar(text("SELECT conname FROM pg_constraint "
            "WHERE conrelid='product_analytics_facts'::regclass AND contype='p'"))
        assert type(primary_key) is str and primary_key
    new_plan = None
    with pytest.raises(IntegrityError) as collision:
        with tenant_scope(case['gym']), Session(case['app']) as db:
            # A valid new business source in this outer transaction, not a missing/FK-invalid source.
            plan = PlanGenerado(gym_id=case['gym'], id_cliente=case['client'],
                fecha_generacion=datetime.now(timezone.utc), plan_json=payload, kcal_objetivo=100)
            db.add(plan)
            db.flush()
            new_plan = plan.id
            assert type(new_plan) is int and new_plan != original_plan
            assert db.scalar(select(Fact).where(Fact.owner_id == case['gym'],
                Fact.event_type == 'plan_saved', Fact.source_id == str(new_plan), Fact.source_version == 1)) is None
            with monkeypatch.context() as selected_identity:
                selected_identity.setattr(product_facts.uuid, 'uuid4', lambda: SimpleNamespace(hex=collision_id))
                product_facts.append(db, case['gym'], 'gym', case['client'], 'plan_saved', new_plan, 1, 'demo')
            db.commit()  # A swallowed unrelated PK would wrongly commit the business plan.
    assert collision.value.orig.pgcode == '23505'
    assert collision.value.orig.diag.constraint_name == primary_key
    with Session(case['admin']) as db:
        assert db.get(PlanGenerado, new_plan) is None
        after = tuple(tuple(getattr(row, column.key) for column in Fact.__table__.columns)
                      for row in db.scalars(select(Fact).where(Fact.owner_id == case['gym']).order_by(Fact.id)))
        assert after == before
        assert db.get(Fact, collision_id).source_id == str(original_plan)
