"""Both fresh import orders preserve fixtures, original16 IDs and current crypto setup."""
import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('pair',[
    ['tests.test_identity_security','tests.google33_identity_contract'],
    ['tests.google33_identity_contract','tests.test_identity_security'],
    ['tests.test_mfa31_google_reauth','tests.google33_mfa_reauth_contract'],
    ['tests.google33_mfa_reauth_contract','tests.test_mfa31_google_reauth'],
])
def test_fresh_import_orders_have_no_cycle_and_share_exact_test_objects(pair):
    program="""import importlib,json
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
a,b=[importlib.import_module(n) for n in json.loads(__import__('sys').argv[1])]
names={n for n in vars(a) if n.startswith('test_')} & {n for n in vars(b) if n.startswith('test_')}
assert len(names)==(2 if 'identity' in a.__name__ else 4)
assert all(getattr(a,n) is getattr(b,n) for n in names)
if 'identity' in a.__name__:
 assert a.identity_db is b.identity_db and a.principal is b.principal and a.auth_client is b.auth_client
else:
 assert a.mfa_client is b.mfa_client and a.google_http is b.google_http and a.google_db is b.google_db
print('import-order-and-object-identity-ok')
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',program,json.dumps(pair)],cwd=ROOT,capture_output=True,timeout=30,check=False)
    assert result.returncode==0,'Fresh import order or object/fixture identity failed; diagnostics remain private'
    assert result.stdout.strip()==b'import-order-and-object-identity-ok'


def test_original_identity_nonGoogle_functions_and_fixtures_remain_exact():
    mapping=json.loads((ROOT/'tests/ci_google33/autodiscovery-map.json').read_bytes())
    raw=subprocess.check_output(['git','--no-replace-objects','show',mapping['base']+':tests/test_identity_security.py'],cwd=ROOT)
    current=(ROOT/'tests/test_identity_security.py').read_bytes()
    functions=lambda source:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    old=functions(raw);new=functions(current);fixtures=functions((ROOT/'tests/ci_google33/identity_fixtures.py').read_bytes())
    assert all(old[n]==new[n] for n in mapping['identity_nonGoogle_function_AST_exact'])
    assert all(old[n]==fixtures[n] for n in mapping['identity_fixture_AST_exact'])


def test_new_owner_keeps_function_lifetime_for_diary_and_MFA():
    from tests.ci_google33.owned import migration_database
    from tests.integration_schema_migrations import migration_database as old_owner
    from tests.mfa31_fixtures import mfa_database
    assert migration_database._fixture_function_marker.scope==mfa_database._fixture_function_marker.scope==old_owner._fixture_function_marker.scope=='function'
    assert inspect.signature(migration_database.__wrapped__)==inspect.signature(old_owner.__wrapped__)
