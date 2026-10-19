"""Opt-in pytest observations on own UUIDs; no business body is replaced."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

HERE = Path(__file__).resolve().parent
CASES = []


def load(name):
    spec = importlib.util.spec_from_file_location('ci33_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pytest_configure(config):
    import resource_guard
    assert resource_guard.INSTALLED
    if os.environ['CI33_SCHEMA'] == '32':
        import tests.retirement32_owned as legacy
        legacy.owned_database = load('owned_portable').owned_database
    import tests
    from web.database import models
    source = Path(os.environ['CI33_SOURCE']).resolve()
    assert Path(tests.__file__).resolve().is_relative_to(source)
    assert Path(models.__file__).resolve().is_relative_to(source)


def engines(value, seen=None):
    from sqlalchemy.engine import Engine
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, Engine):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from engines(child, seen)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from engines(child, seen)


def transition(engine):
    from sqlalchemy import inspect, text

    from web.database.alembic.schema_contract_v1 import schema_signature
    with engine.connect() as db:
        flags = list(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one())
        gucs = tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.client_invitation_digest',true),current_setting('app.mfa_actor',true)")).one())
        return {'database_kind': 'postgresql',
            'runtime_revision': db.scalar(text('SELECT version_num FROM alembic_version')),
            'actual_tables': len(inspect(db).get_table_names()), 'role_flags4': flags,
            'database_nonowner': db.scalar(text('SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()')),
            'owned_tables': db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)")),
            'application_pool_size': engine.pool.size(), 'blank_GUCs': gucs == ('', '', ''),
            'schema_sha256': hashlib.sha256(json.dumps(schema_signature(db), sort_keys=True, default=list).encode()).hexdigest()}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    if outcome.excinfo is not None:
        return
    import resource_guard
    from sqlalchemy import create_engine

    from tests.integration_provider_subjects import application_engine
    schema = os.environ['CI33_SCHEMA']
    path, name = item.nodeid.split('::', 1)
    identity = [path.removesuffix('.py').replace('/', '.').replace('\\', '.'), name]
    assert resource_guard.OWNED, 'No process-owned database remains before teardown'
    candidates = list(engines(item.funcargs))
    measurements, origins = [], []
    for database, (lease, _raw) in sorted(resource_guard.OWNED.items()):
        assert resource_guard.state(database)[0] == (lease['oid'], lease['owner'])
        app_user = urlsplit(os.environ['METODOBASE_TEST_POSTGRES_URL']).username
        matches = [engine for engine in candidates if engine.dialect.name == 'postgresql'
                   and engine.url.database == database and engine.url.username == app_user]
        admin = None
        if matches:
            app = matches[0]
            origin = 'business_fixture_engine'
        else:
            parts = urlsplit(os.environ['METODOBASE_TEST_MIGRATOR_URL'])
            url = urlunsplit(parts._replace(path='/' + database))
            admin = create_engine(url, pool_size=1, max_overflow=0)
            # Same table/sequence grants as the unchanged original fixtures;
            # only this attributed UUID is touched, never default ACLs/roles.
            app = application_engine(url, admin)
            origin = 'postcase_restricted_probe'
        try:
            migration = '_migrations' in identity[0]
            value = transition(app) if migration else load('physical').physical_contract(
                app, schema=schema, expected_pool=6 if identity[0] == 'tests.integration_current33_r24_race' else 1)
            load('witness').validate(value, schema=schema,
                pool=6 if identity[0] == 'tests.integration_current33_r24_race' else 1, transition=migration)
            measurements.append(value)
            origins.append(origin)
        finally:
            if admin is not None:
                app.dispose()
                admin.dispose()
    CASES.append({'identity': identity, 'phase': 'after_business_before_teardown',
                  'measurements': measurements, 'measurement_sources': origins})


def pytest_sessionfinish(session, exitstatus):
    if exitstatus == 0:
        path = Path(os.environ['CI33_WITNESSES'])
        with path.open('x', encoding='utf8') as out:
            json.dump({'schema': os.environ['CI33_SCHEMA'], 'cases': CASES}, out, indent=2)
            out.write('\n')
