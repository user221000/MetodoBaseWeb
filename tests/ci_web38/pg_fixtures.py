"""Finite new38 leases; original owned603f/commonclose e905 remain unchanged."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web38 import pg_contract as contract


def record(name, value):
    from web.services.legacy_object_apply_boundary import verify
    root = Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR']).resolve(strict=True)
    verify(root, directory=True)
    with (root / name).open('x', encoding='utf8') as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())


@pytest.fixture(scope='session')
def database_schema():
    """No unrelated root SQLite bootstrap in this explicitly leased PG phase."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    """Each business case seeds UUID actors; never clear an unrelated default DB."""
    yield


class Runtime:
    def __init__(self, name, value, profile):
        self.name, self.contract, self.profile = name, value, profile
        self.created = self.closed = self.active = 0
        self.failed = False

    @contextmanager
    def database(self, directory):
        from tests.ci_web37.pg_close import owned_database
        if self.failed or self.active or self.created >= self.contract['phase']['UUIDs']:
            raise ValueError('The finite PG38 sequential UUID budget is unavailable')
        self.active = 1
        try:
            with owned_database('postgresql', directory) as value:
                yield value
            self.closed += 1  # commonclose/owner already demanded strict zero/normal DROP/fresh absence.
        except BaseException:
            self.failed = True
            raise
        finally:
            self.active = 0


@pytest.fixture(scope='module')
def pg38_runtime(request):
    name = os.environ['PG38_PHASE']
    value, profile = contract.checked_runtime(name)
    assert Path(request.module.__file__).resolve() == contract.ROOT / value['phase']['module']
    os.environ.update(profile)
    from tests.ci_web38.pg_contract import check_generation_closed as check_generation
    check_generation(value, profile)  # First SQL follows the new Root38 ACK.
    runtime = Runtime(name, value, profile)
    with contract.creation_generation_guard(runtime):
        yield runtime
    current, config = contract.checked_runtime(name)
    assert current == value and config == profile and not runtime.failed
    assert runtime.active == 0 and runtime.created == runtime.closed == value['phase']['UUIDs']
    record('pg38-' + name + '-runtime.json', {'phase': name, 'contract_sha256': contract.digest(value),
        'FileSetDigest': value['FileSetDigest'], 'created_UUIDs': runtime.created,
        'normally_closed_UUIDs': runtime.closed, 'max_concurrent_UUIDs': 1})


@pytest.fixture(scope='module')
def pg38_database(pg38_runtime, tmp_path_factory):
    from sqlalchemy import create_engine
    from tests.integration_provider_subjects import application_engine
    from tests.integration_schema_migrations import run_migration
    from tests.ci_web38.pg_physical import physical_contract
    with pg38_runtime.database(tmp_path_factory.mktemp('product38')) as (url, lease_admin):
        run_migration(url, 'db_bootstrap.py', '--revision', '20261023_product_facts')
        # The SV canary holds one admin row lock while another admin connection
        # observes its worker. The original owned603f engine/pool is untouched.
        admin = (create_engine(url, pool_size=2, max_overflow=0)
                 if pg38_runtime.contract['phase']['admin_observer_pool'] == 2 else lease_admin)
        app = None
        try:
            app = application_engine(url, lease_admin)
            record('pg38-' + pg38_runtime.name + '-physical.json', physical_contract(app))
            yield SimpleNamespace(url=url, admin=admin, app=app, runtime=pg38_runtime)
        finally:
            if app is not None:
                assert app.pool.checkedout() == 0
            if admin is not lease_admin:
                assert admin.pool.checkedout() == 0
            # e905 owns final disposal: validate generation/OID/owner and all
            # original Pools/loans before touching them, not just current pool.


@pytest.fixture(scope='module')
def link_db(pg38_database):
    return pg38_database.admin, pg38_database.app


@pytest.fixture(autouse=True)
def released(pg38_database):
    yield
    from web.database.tenant_context import current_tenant
    from tests.ci_web38.pg_physical import blank_pool
    assert current_tenant.get() == ''
    blank_pool(pg38_database.app)
    assert pg38_database.admin.pool.checkedout() == 0
