"""Actual revision38 SQLite business transactions; not PostgreSQL/RLS evidence."""
from datetime import UTC, datetime
import json
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from tests import product38_fixtures as f
from web.database.models import Cliente, PlanGenerado, ProductAnalyticsFact as Fact, UserRole, Usuario
from web.database.repository import eliminar_cliente, registrar_plan, listar_clientes
from web.services import product_facts
from web.services.product_analytics_v2 import origin, read_report

origin38_engine = f.origin38_engine
link_db = f.link_db
case = f.case


def claims(case, who='gym'):
    with Session(case['admin']) as db:
        u = db.get(Usuario, case[who])
        return {'id': u.id, 'session_version': u.session_version, 'tipo': u.tipo,
                'role': u.role.value, 'team_gym_id': u.team_gym_id}


def declare(case, value, expected, who='gym', context='gym', client=None):
    with Session(case['app']) as db:
        return origin(db, claims(case, who), context, (client or case['client']) if context == 'gym' else None,
                      value=value, expected_version=expected)


def saved(case, *, commit=True):
    raw = json.dumps({meal: {'kcal_objetivo': 100, 'kcal_real': 100, 'alimentos': {'synthetic': 50}}
                      for meal in ('desayuno', 'almuerzo', 'comida', 'cena')})
    with Session(case['app']) as db:
        identity = registrar_plan(db, case['gym'], case['client'], {'plan_json': raw}, return_id=True)
        if commit: db.commit()
        else: db.rollback()
    return identity


def test_existing_unknown_then_future_only_declarations_and_cas(case):
    with Session(case['app']) as db:
        assert origin(db, claims(case), 'gym', case['client'])['origin'] == 'unknown'
    first = saved(case)
    assert declare(case, 'demo', 0)['version'] == 1
    second = saved(case)
    assert declare(case, 'customer', 1)['version'] == 2
    with pytest.raises(HTTPException) as conflict: declare(case, 'unknown', 0)
    assert conflict.value.status_code == 409
    with Session(case['admin']) as db:
        facts = dict(db.execute(select(Fact.source_id, Fact.origin).where(Fact.owner_id == case['gym'], Fact.event_type == 'plan_saved')).all())
        assert facts[str(first)] == 'unknown' and facts[str(second)] == 'demo'
        assert db.scalar(select(Fact.source_version).where(Fact.owner_id == case['gym'], Fact.event_type == 'origin_declared').order_by(Fact.source_version.desc()).limit(1)) == 2


def test_plan_and_fact_rollback_and_exact_replay(case):
    declare(case, 'demo', 0)
    rolled = saved(case, commit=False)
    with Session(case['admin']) as db:
        assert db.get(PlanGenerado, rolled) is None
        assert db.scalar(select(Fact.id).where(Fact.owner_id == case['gym'], Fact.event_type == 'plan_saved')) is None
    identity = saved(case)
    with Session(case['app']) as db:
        product_facts.plan_saved(db, db.get(PlanGenerado, identity))
        db.commit()
    with Session(case['admin']) as db:
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='plan_saved').count() == 1


def test_owner_only_write_foreign_client_and_personal_scope(case):
    with pytest.raises(HTTPException) as foreign:
        declare(case, 'demo', 0, client=case['otherclient'])
    assert foreign.value.status_code == 404
    identity = str(uuid.uuid4())
    with Session(case['admin']) as db:
        db.add(Usuario(id=identity, email=identity+'@example.invalid', password_hash='not-a-login', nombre='Synthetic',
                       tipo='usuario', role=UserRole.ADMIN, team_gym_id=case['gym']))
        db.commit()
    case['team'] = identity
    with pytest.raises(HTTPException) as denied: declare(case, 'demo', 0, who='team')
    assert denied.value.status_code == 403
    assert declare(case, 'demo', 0, who='team', context='personal')['origin'] == 'demo'
    with Session(case['app']) as db:
        assert origin(db, claims(case), 'gym', case['client'])['origin'] == 'unknown'


def test_sql_history_update_delete_backdate_and_foreign_source_rejected(case):
    declare(case, 'demo', 0)
    for sql in ("UPDATE product_analytics_facts SET origin='customer' WHERE owner_id=:owner",
                "DELETE FROM product_analytics_facts WHERE owner_id=:owner"):
        with Session(case['admin']) as db, pytest.raises(IntegrityError):
            db.execute(text(sql), {'owner': case['gym']})
    with Session(case['admin']) as db, pytest.raises(IntegrityError):
        db.add(Fact(owner_id=case['gym'], context='gym', client_id=case['client'], event_type='origin_declared',
                    source_id=case['client'], source_version=2, origin='customer', occurred_at=datetime(2000, 1, 1, tzinfo=UTC)))
        db.flush()
    with Session(case['admin']) as db, pytest.raises(IntegrityError):
        product_facts.append(db, case['gym'], 'gym', case['client'], 'plan_saved', '99999999', 1, 'demo')


def test_filtered_clients_and_aggregate_no_ids_health_or_payment(case):
    declare(case, 'demo', 0)
    saved(case)
    with Session(case['app']) as db:
        result, count = listar_clientes(db, case['gym'], data_origin='demo')
        assert count == 1 and result[0]['data_origin'] == 'demo'
        assert listar_clientes(db, case['gym'], data_origin='customer')[1] == 0
    report = read_report(claims(case), 'gym', session_factory=sessionmaker(bind=case['app']))
    assert report['baseline']['event_counts_by_origin']['demo']['plan_saved'] == 1
    assert all(value not in str(report) for value in (case['gym'], case['client'], case['email']))
    assert report['baseline']['targets'] is None and report['baseline']['retention_D30'] is None


def test_existing_soft_delete_survives_without_reclassifying_retained_facts(case):
    declare(case, 'demo', 0)
    saved(case)
    with Session(case['app']) as db:
        assert eliminar_cliente(db, case['gym'], case['client']) is True
        db.commit()
    with Session(case['app']) as db:
        assert listar_clientes(db, case['gym'], data_origin='demo')[1] == 0
        assert db.query(Fact).filter_by(owner_id=case['gym'], event_type='plan_saved', origin='demo').count() == 1
