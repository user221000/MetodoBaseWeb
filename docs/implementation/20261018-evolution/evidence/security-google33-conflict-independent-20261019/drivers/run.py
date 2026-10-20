"""Focal replay; PG requires an explicit root handoff before invocation."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

R = Path(r'F:/mb-security-google33-conflict-peer-20261019')
T = Path(r'C:/Users/Consu/AppData/Local/Temp')
P = T / 'metodobase-sec-google33-conflict-peer-private-20261019'
O = R / 'docs/implementation/20261018-evolution/evidence/security-google33-conflict-independent-20261019'
WEB = T / 'metodobase-candidate-web-20261018/Scripts/python.exe'
sys.path.insert(0, str(R))
sys.dont_write_bytecode = True
sha = lambda b: hashlib.sha256(b).hexdigest()
save = lambda n, x: (O / n).write_bytes((json.dumps(x, indent=2) + '\n').encode())
phase = sys.argv[1]
assert phase in {'sqlite', 'pg'}
binding = json.loads((O / 'frozen-source-binding.json').read_bytes())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R).decode().strip() == binding['reviewed_commit']
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=R)

def photo():
    names = subprocess.check_output(['git', 'ls-files', '-z', '--', 'web', 'api', 'core', 'config', 'tests', 'scripts', 'requirements*', 'Dockerfile', 'db_bootstrap.py', 'pyproject.toml'], cwd=R).decode().split('\0')
    names += ['tests/' + name for name in binding['peer_canaries']]
    code = "from pathlib import Path;import hashlib,importlib.metadata,json,sys;h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();print(json.dumps({'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':h(sys.executable),'base_python':h(sys._base_executable)}))"
    return {'source': {n: sha((R / n).read_bytes()) for n in names if n and (R / n).is_file()},
        'author92': {'packages': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
            'python': sha(Path(sys.executable).read_bytes()), 'base_python': sha(Path(sys._base_executable).read_bytes())},
        'web89': json.loads(subprocess.check_output([str(WEB), '-B', '-c', code]))}

before = photo()
assert len(before['author92']['packages']) == 92 and len(before['web89']['packages']) == 89
save(phase + '-before.json', before)
environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
receipts = P / (phase + '-association-receipts')
receipts.mkdir()
environment['SEC_GOOGLE_PRIVATE_RECEIPTS'] = str(receipts)
profile_raw = None
if phase == 'pg':
    # Caller must already have the explicit exclusive PG55483 handoff.
    PROFILE = T / 'metodobase-qa-pg55483-private-ok6hrpyq/env.json'
    profile_raw = PROFILE.read_bytes()
    profile = json.loads(profile_raw)
    assert set(profile) == {'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_PG_BIN'}
    from tests.isolation import validate_postgres_test_url
    for key in ['METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL']:
        parsed = urlsplit(validate_postgres_test_url(profile[key]))
        assert parsed.hostname in {'127.0.0.1', 'localhost'} and parsed.port == 55483
    import psycopg2
    with psycopg2.connect(profile['METODOBASE_TEST_POSTGRES_URL'].replace('postgresql+psycopg2://', 'postgresql://', 1)) as db, db.cursor() as cursor:
        cursor.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,inet_server_port() FROM pg_roles WHERE rolname=current_user')
        assert cursor.fetchone() == (False, False, False, False, 55483)
    environment.update(profile)
    leases = P / 'metodobase-google33-author-helper-independent-conflict-peer-20261019/leases'
    leases.mkdir(parents=True)
    environment['GOOGLE33_PRIVATE_LEASES'] = str(leases)
    save('pg-profile-binding.json', {'profile_SHA256': sha(profile_raw), 'loopback_port': 55483,
        'app_four_flags_false': True, 'profile_values_published': False, 'global_roles_HBA_services_altered': False})
    modules = [
        'tests/test_security_google33_postgres_peer.py::test_actual33_contract_is_restricted_and_adds_only_trigger_functions',
        'tests/test_security_google33_postgres_peer.py::test_one_real_intent_has_one_winner_under_two_pool1_workers',
        'tests/test_security_google33_postgres_peer.py::test_distinct_real_actors_cannot_acquire_one_subject_in_two_pool1_workers',
        'tests/test_security_google33_postgres_true_peer.py::test_one_real_intent_has_one_winner_under_two_pool1_workers',
        'tests/test_security_google33_postgres_true_peer.py::test_distinct_real_actors_cannot_acquire_one_subject_in_two_pool1_workers',
        'tests/test_security_google33_canonical_race_peer.py',
    ]
else:
    modules = ['tests/test_google33_conflict_window.py', 'tests/test_security_google33_conflict_peer.py',
        'tests/test_security_google33_peer.py::test_exact_ssr_get_and_api_error_boundaries_keep_distinct_private_policies']
command = [sys.executable, '-B', '-X', 'utf8', 'tests/run_isolated.py', *modules, '-q', '--tb=short',
    '--basetemp=' + str(P / ('pytest-' + phase)), '--junitxml=' + str(P / (phase + '.xml'))]
run = subprocess.run(command, cwd=R, env=environment, capture_output=True, timeout=480)
(P / (phase + '-stdout.RAW.log')).write_bytes(run.stdout)
(P / (phase + '-stderr.RAW.log')).write_bytes(run.stderr)
cases = ET.parse(P / (phase + '.xml')).findall('.//testcase')
rows = [{'case': c.get('classname') + '::' + c.get('name'), 'outcome': next(
    (kind for kind in ['failure', 'error', 'skipped'] if c.find(kind) is not None), 'passed')} for c in cases]
save(phase + '-cases.STRUCTURAL.json', rows)
after = photo()
save(phase + '-after.json', after)
assert before == after
summary = {'cases': len(rows), 'exit': run.returncode,
    'outcomes': {kind: sum(row['outcome'] == kind for row in rows) for kind in ['passed', 'failure', 'error', 'skipped']},
    'source_author92_WEB89_bothPython_quiet': True}
if profile_raw is not None:
    assert PROFILE.read_bytes() == profile_raw
    states = [json.loads(path.read_bytes()) for path in leases.glob('lease-*.json')]
    assert len(states) == 3
    closed = all(s['state'] == 'closed_absent' and s['sessions_before_drop'] == 0 and s['absence_verified'] == 'fresh_control_connection' for s in states)
    save('pg-closures.STRUCTURAL.json', {'scope': 'Only own UUIDs. Initial exclusive xb before CREATE; OID/birth; zero sessions; DROP without FORCE; fresh absence. No foreign DB actions.',
        'all_closed_absent': closed, 'leases': [{key: s.get(key) for key in ['plan_id', 'database', 'oid', 'state',
            'sessions_before_drop', 'absence_verified', 'initial_creation', 'launcher_pid', 'launcher_birth',
            'launcher_birth_after_create', 'created_at', 'closed_at']} for s in states]})
    assert closed
    summary.update({'owned_UUIDs': len(states), 'all_closed_absent': True, 'private_profile_bytes_quiet': True})
save(phase + '-summary.json', summary)
print(json.dumps(summary))
