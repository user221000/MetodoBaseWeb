"""Actual summary SQL preserves keyset order and ownership on both dialects.

The PostgreSQL plan gate counts visited plan rows, not wall-clock latency. It
uses a real restricted role and synthetic mixed dated/NULL/tied histories.
"""
from datetime import datetime, timedelta

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import run_migration
from tests.history_index_fixtures import history_migration_database as migration_database
from tests.integration_provider_subjects import application_engine
from web.database.models import Cliente, PlanGenerado, Usuario, UserRole
from web.database.tenant_context import tenant_scope
from web.services.generation_quota import individual_plan_results_query
from web.services.personal_history_query import history_summary_rows

SUBJECT = 'ordered-history-person'
PROFILE = 'ordered-history-self'


def seed(engine):
    with Session(engine) as db:
        for subject in (SUBJECT, 'ordered-history-other'):
            db.add(Usuario(id=subject, email=subject+'@example.invalid', password_hash='synthetic-unused',
                nombre='Synthetic', tipo='usuario', role=UserRole.VIEWER, activo=True))
        db.flush()
        for identity, owner in ((PROFILE, SUBJECT), ('ordered-history-extra', SUBJECT),
                                ('ordered-history-foreign', 'ordered-history-other')):
            db.add(Cliente(id_cliente=identity, gym_id=owner, nombre='Synthetic', activo=True))
        db.flush()
        stamp = datetime(2026, 10, 1)
        for number in range(1000):
            db.add(PlanGenerado(gym_id=SUBJECT, id_cliente=PROFILE,
                fecha_generacion=stamp-timedelta(minutes=max(number-19, 0)),
                kcal_objetivo=number+1000, plan_json='{"synthetic_large_plan":"'+('x'*8192)+'"}'))
        db.flush()
        ids = db.query(PlanGenerado.id).filter_by(gym_id=SUBJECT, id_cliente=PROFILE).order_by(PlanGenerado.id).all()
        db.query(PlanGenerado).filter(PlanGenerado.id.in_([row.id for row in ids[700:]])).update(
            {PlanGenerado.fecha_generacion: None}, synchronize_session=False)
        for owner, profile in ((SUBJECT, 'ordered-history-extra'),
                               ('ordered-history-other', 'ordered-history-foreign'),
                               (SUBJECT, 'ordered-history-foreign'),
                               ('ordered-history-other', PROFILE)):
            db.add(PlanGenerado(gym_id=owner, id_cliente=profile, fecha_generacion=stamp,
                kcal_objetivo=99999, plan_json='{"foreign":true}'))
        removed = PlanGenerado(gym_id=SUBJECT, id_cliente=PROFILE, fecha_generacion=stamp,
            deleted_at=stamp, kcal_objetivo=99999)
        db.add(removed)
        db.commit()
    if engine.dialect.name == 'postgresql':
        with engine.begin() as db:
            db.exec_driver_sql('ANALYZE planes_generados')
            db.exec_driver_sql('ANALYZE clientes')


def walk(node):
    yield node
    for child in node.get('Plans', []):
        yield from walk(child)


def test_mixed_history_order_ownership_complete_pages_and_pg_work_budget(migration_database):
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', '20261019_personal_history_index')
    seed(admin)
    app = application_engine(url, admin)
    observations = []
    try:
        with tenant_scope(SUBJECT), Session(app) as db:
            if app.dialect.name == 'postgresql':
                assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()) == (False, False, False, False)
                assert not db.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND pg_has_role(current_user,relowner,'MEMBER'))"))
            oracle = individual_plan_results_query(db, SUBJECT).filter(PlanGenerado.id_cliente == PROFILE).with_entities(
                PlanGenerado.id, PlanGenerado.fecha_generacion, PlanGenerado.kcal_objetivo,
            ).order_by(PlanGenerado.fecha_generacion.desc().nulls_last(), PlanGenerado.id.desc()).all()
            assert len(oracle) == 1000
            assert [row.id for row in oracle[:20]] == list(range(20, 0, -1))
            assert sum(row.fecha_generacion is None for row in oracle) == 300
            assert all(row.kcal_objetivo != 99999 for row in oracle)

            cases = [('first', None, 0), ('tie', oracle[9], 10),
                     ('late_dated', oracle[649], 650), ('date_to_null', oracle[689], 690),
                     ('null_cursor', oracle[749], 750)]
            for label, anchor, offset in cases:
                captured = []

                def capture(connection, cursor, statement, parameters, context, many):
                    if 'planes_generados' in statement:
                        captured.append((statement, parameters))

                event.listen(app, 'before_cursor_execute', capture)
                try:
                    position = None if anchor is None else (anchor.fecha_generacion, anchor.id)
                    rows = history_summary_rows(db, SUBJECT, PROFILE, 50, position)
                finally:
                    event.remove(app, 'before_cursor_execute', capture)
                assert [(r.id, r.fecha_generacion, r.kcal_objetivo) for r in rows] == [tuple(r) for r in oracle[offset:offset+51]]
                assert len(captured) == 1
                statement, parameters = captured[0]
                assert 'count(' not in statement.lower() and 'plan_json' not in statement
                observation = {'case': label, 'returned_candidates': len(rows)}
                if app.dialect.name == 'postgresql':
                    plan = db.connection().exec_driver_sql('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+statement, parameters).scalar_one()
                    nodes = list(walk(plan[0]['Plan']))
                    scans = [n for n in nodes if n.get('Relation Name') == 'planes_generados']
                    work = sum((n.get('Actual Rows', 0)+n.get('Rows Removed by Filter', 0)+n.get('Rows Removed by Index Recheck', 0))*n.get('Actual Loops', 1) for n in scans)
                    budget = 102 if position and position[0] is not None else 51
                    import json
                    import os
                    from pathlib import Path
                    diagnostic = os.environ.get('METODOBASE_HISTORY_ORDERED_PROOF_DIR')
                    if diagnostic:
                        path = Path(diagnostic)/('case-'+label+'-postgresql.json')
                        assert not path.exists()
                        path.write_text(json.dumps({'sql': statement, 'parameters': parameters,
                            'plan': plan, 'work': work, 'budget': budget}, indent=2, default=str)+'\n', encoding='utf-8')
                    assert work <= budget, (label, work, budget, plan)
                    assert all(n.get('Index Name') == 'ix_planes_gym_cliente_history' for n in scans)
                    observation.update(plan_rows_visited=work, max_candidates=budget, plan=plan,
                                       sql=statement, parameters=parameters)
                observations.append(observation)

            # Exhaust real pages through the shared reader; the oracle is test
            # only. Every next position comes from the last delivered result.
            seen, position = [], None
            for _ in range(30):
                candidates = history_summary_rows(db, SUBJECT, PROFILE, 37, position)
                page = candidates[:37]
                seen.extend(row.id for row in page)
                if len(candidates) <= 37:
                    break
                position = (page[-1].fecha_generacion, page[-1].id)
            assert seen == [row.id for row in oracle]
            assert len(seen) == len(set(seen)) == 1000
            assert history_summary_rows(db, SUBJECT, 'ordered-history-foreign', 50, None) == []
            db.rollback()
        import json
        import os
        from pathlib import Path
        output = os.environ.get('METODOBASE_HISTORY_ORDERED_PROOF_DIR')
        if output:
            path = Path(output)/('ordered-query-'+app.dialect.name+'.json')
            assert not path.exists()
            path.write_text(json.dumps(observations, indent=2, default=str)+'\n', encoding='utf-8')
    finally:
        if app is not admin:
            app.dispose()
