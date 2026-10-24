"""Observe genuine39 target and restricted PG role; never assume observed counts."""
from sqlalchemy import inspect, text

REVISION = '20261023_privacy_disposition'


def blank_pool(engine):
    from tests.ci_web37.physical import blank_pool as original
    original(engine)


def physical_contract(engine):
    from web.database.models import Base
    from web.database.schema_control import expected_head, verify_runtime_schema
    assert engine.dialect.name == 'postgresql' and expected_head() == REVISION
    assert engine.pool.size() == 1 and engine.pool._max_overflow == 0
    verify_runtime_schema(engine, expected_revision=REVISION)
    with engine.connect() as db:
        tables = set(inspect(db).get_table_names())
        assert tables == set(Base.metadata.tables) | {'alembic_version'}
        flags = tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,"
            "pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') "
            "FROM pg_roles WHERE rolname=current_user")).one())
        assert flags == (False,) * 5
        assert db.scalar(text("SELECT datdba<>(SELECT oid FROM pg_roles WHERE rolname=current_user) "
                              "FROM pg_database WHERE datname=current_database()")) is True
        assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
                              "AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)")) == 0
        protected = ('product_analytics_facts', 'privacy_requests', 'privacy_disposition_items')
        for table in protected:
            assert tuple(db.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE oid=to_regclass(:table)"), {'table':'public.'+table}).one()) == (True, True)
        force = db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
            "AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
    blank_pool(engine)
    return {'revision': REVISION, 'physical_tables_observed': len(tables),
        'ORM_tables_observed': len(Base.metadata.tables), 'FORCE_RLS_observed': force,
        'role_five_flags': list(flags), 'protected_tables_FORCE_RLS': list(protected), 'application_pool': 1, 'overflow': 0}
