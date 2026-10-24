"""Finite39 source companion: original owned603f and commonclose e905 intact."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from tests.ci_web39 import pg_contract as contract


def record(name,value):
    from web.services.legacy_object_apply_boundary import verify
    root=Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR']).resolve(strict=True)
    verify(root,directory=True)
    with (root/name).open('x',encoding='utf8') as output:
        json.dump(value,output,indent=2,sort_keys=True);output.write('\n');output.flush();os.fsync(output.fileno())


@pytest.fixture(scope='session')
def database_schema():yield


@pytest.fixture(autouse=True)
def isolated_database():yield


class Runtime:
    def __init__(self,name,value,profile):
        self.name,self.contract,self.profile=name,value,profile
        self.created=self.closed=self.active=0
        self.failed=False

    @contextmanager
    def database(self,directory):
        from tests.ci_web37.pg_close import owned_database
        if self.failed or self.active or self.created>=self.contract['phase']['UUIDs']:
            raise ValueError('Finite PG39 sequential UUID budget unavailable')
        self.active=1
        try:
            with owned_database('postgresql',directory) as value:yield value
            self.closed+=1
        except BaseException:
            self.failed=True
            raise
        finally:self.active=0


@pytest.fixture(scope='module')
def pg39_runtime(request):
    from tests.ci_web39.pg_control import check_control_generation
    name=os.environ['PG39_PHASE']
    value,profile=contract.checked_runtime(name)
    assert Path(request.module.__file__).resolve()==contract.ROOT/value['phase']['module']
    os.environ.update(profile)
    check_control_generation(value,profile)
    runtime=Runtime(name,value,profile)
    with contract.creation_generation_guard(runtime):yield runtime
    current,config=contract.checked_runtime(name)
    assert current==value and config==profile and not runtime.failed
    assert runtime.active==0 and runtime.created==runtime.closed==value['phase']['UUIDs']
    record('pg39-'+name+'-runtime.json',{'phase':name,'contract_sha256':contract.digest(value),
        'FileSetDigest':value['FileSetDigest'],'created_UUIDs':runtime.created,
        'normally_closed_UUIDs':runtime.closed,'max_concurrent_UUIDs':1})


@pytest.fixture(scope='module')
def pg39_database(pg39_runtime,tmp_path_factory):
    from tests.integration_provider_subjects import application_engine
    from tests.integration_schema_migrations import run_migration
    from tests.ci_web39.pg_physical import physical_contract
    with pg39_runtime.database(tmp_path_factory.mktemp('privacy39')) as (url,admin):
        run_migration(url,'db_bootstrap.py','--revision','20261023_privacy_disposition')
        app=application_engine(url,admin)
        try:
            record('pg39-'+pg39_runtime.name+'-physical.json',physical_contract(app))
            yield SimpleNamespace(url=url,admin=admin,app=app,runtime=pg39_runtime)
        finally:
            assert app.pool.checkedout()==admin.pool.checkedout()==0
            # The original e905 validates every lifetime/OID/generation before
            # disposal and normal DROP. No FORCE, terminate or retry fallback.


@pytest.fixture(autouse=True)
def released(pg39_database):
    yield
    from web.database.tenant_context import current_tenant
    from tests.ci_web39.pg_physical import blank_pool
    assert current_tenant.get()==''
    blank_pool(pg39_database.app)
    assert pg39_database.admin.pool.checkedout()==0
