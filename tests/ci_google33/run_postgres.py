"""Sequential versioned PG gates with private RAW and exclusive UUID ownership.

This runner never provisions roles or changes HBA/default privileges. A fresh
CI service is bootstrapped in a preceding workflow step; local execution needs
an explicitly coordinated lease of the existing synthetic profile.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shlex
import subprocess
import sys
import traceback
import uuid
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.ci_google33.workflow import (
    CURRENT_REPORT_COMMANDS,
    HISTORICAL32_REPORT_COMMANDS,
)
from tests.run_reviewed_ci30 import new_directory, regular_directory


def write(path, value):
    with path.open('x', encoding='utf8') as out:
        json.dump(value, out, indent=2)
        out.write('\n')


def private_directory(path):
    path = new_directory(path)
    if os.name == 'nt':
        sid = next(csv.reader(io.StringIO(subprocess.check_output(
            ['whoami', '/user', '/fo', 'csv', '/nh'], text=True))))[1]
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
            '*' + sid + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], check=True, capture_output=True)
    else:
        path.chmod(0o700)
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def photo(source, pg_bin):
    names = set()
    for options in ([], ['--others', '--exclude-standard']):
        names.update(subprocess.check_output(['git', '--no-replace-objects', 'ls-files',
            '-z', *options], cwd=source).decode().split('\0'))
    sources = {name: digest(source / name) for name in sorted(names)
               if name and not name.startswith('docs/') and (source / name).is_file()}
    suffix = '.exe' if os.name == 'nt' else ''
    binaries = {name: digest(pg_bin / (name + suffix))
                for name in ('postgres', 'pg_ctl', 'pg_dump', 'pg_restore', 'psql')}
    from tests.ci_google33.environment_photo import interpreter, packages
    return {'sources': sources, 'packages': packages(), 'Python': interpreter(),
            'PostgreSQL_binaries': binaries}


def role_catalog(environment):
    import psycopg2

    from tests.isolation import validate_postgres_test_url
    urls = [validate_postgres_test_url(environment[key])
            for key in ('METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL')]
    parts = [urlsplit(url) for url in urls]
    assert all(p.hostname in {'127.0.0.1', 'localhost'} and p.port == 55483 for p in parts)
    assert parts[0].username != parts[1].username
    with psycopg2.connect(urls[0].replace('postgresql+psycopg2://', 'postgresql://', 1), connect_timeout=5) as db, db.cursor() as c:
        c.execute('SELECT rolname,oid,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname IN (%s,%s) ORDER BY rolname',
                  (parts[0].username, parts[1].username))
        rows = c.fetchall()
    assert len(rows) == 2
    assert next(row[2:] for row in rows if row[0] == parts[1].username) == (False,) * 4
    return rows


def execute(argv, source, environment, path, timeout=1800):
    with path.open('xb') as raw:
        result = subprocess.run(argv, cwd=source, env=environment, stdout=raw,
                                stderr=subprocess.STDOUT, timeout=timeout, check=False)
    return result.returncode


def lease_audit(directory, environment):
    import psycopg2
    rows = []
    for path in sorted(directory.glob('*.json')):
        lease = json.loads(path.read_bytes())
        assert lease['state'] == 'closed_fresh_absent' and lease['created'] is True
        assert lease['sessions_before_drop'] == 0 and lease['executed_FORCE'] is False
        assert lease['backend_termination'] is False
        events = [json.loads(line) for line in path.with_suffix('.events.jsonl').read_text().splitlines()]
        assert [event['state'] for event in events] == ['exclusive_before_CREATE', 'created_exact_OID',
            'zero_sessions_before_ordinary_DROP', 'closed_fresh_absent']
        assert events[0]['oid'] is None and all(event['oid'] == lease['oid'] for event in events[1:])
        assert len({event['run_nonce'] for event in events}) == 1
        rows.append(lease['database'])
    assert rows, 'A PostgreSQL acceptance phase created no attributable UUID'
    # A new control connection after every child exited, not a cached absence.
    url = environment['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://', 'postgresql://', 1)
    with psycopg2.connect(url, connect_timeout=5) as db, db.cursor() as c:
        c.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)', (rows,))
        assert c.fetchall() == []
        c.execute('SELECT datname,pid FROM pg_stat_activity WHERE datname=ANY(%s)', (rows,))
        assert c.fetchall() == []
    return len(rows)


def run(args, private):
    source = args.source.resolve(strict=True)
    regular_directory(source)
    schema = args.schema
    label = 'current33' if schema == '33' else 'historical32'
    if schema == '32':
        from tests.ci_google33.history import specifications
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source).decode().strip()
        assert actual == specifications()['32']['commit']
    pg_bin = Path(os.environ['METODOBASE_TEST_PG_BIN']).resolve(strict=True)
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
    for key in list(environment):
        upper = key.upper()
        if upper == 'DATABASE_URL' or upper.endswith('_DATABASE_URL') or upper.startswith(('AWS_', 'S3_')) or any(
                item in upper for item in ('STRIPE', 'MERCADOPAGO', 'SMTP', 'RESEND', 'SENTRY', 'GOOGLE_CLIENT', 'OPENAI_API')):
            environment.pop(key, None)
    nonce = uuid.uuid4().hex
    leases = private / 'guard-leases'
    leases.mkdir()
    google = private / ('metodobase-google33-author-ci33-' + nonce) / 'leases'
    google.mkdir(parents=True)
    evidence = private / 'restore-evidence'
    evidence.mkdir()
    r24 = private / 'r24'
    r24.mkdir()
    sec_receipts = private / 'sec-canonical-receipts'
    sec_receipts.mkdir()
    environment.pop('_METODOBASE_TEST_ROOT', None)
    environment.update(CI33_LEASE_DIRECTORY=str(leases), CI33_RUN_NONCE=nonce,
        GOOGLE33_PRIVATE_LEASES=str(google), CI33_SCHEMA=schema, CI33_SOURCE=str(source),
        METODOBASE_TEST_EVIDENCE_DIR=str(evidence), R24_PG_OUTPUT=str(r24),
        SEC_GOOGLE_PRIVATE_RECEIPTS=str(sec_receipts),
        R25_EVIDENCE_DIR=str(private / 'historical32-receipts'),
        TMP=str(private), TEMP=str(private), TMPDIR=str(private),
        PYTHONPATH=os.pathsep.join([str(ROOT / 'tests/ci_google33/boot'), str(ROOT / 'tests/ci_google33')]))
    before = photo(source, pg_bin)
    write(private / 'before.json', before)
    roles = role_catalog(environment)
    write(private / 'roles-before.json', roles)
    assert execute([sys.executable, '-m', 'pip', 'check'], source, environment, private / 'pip-before.raw.log') == 0
    commands = CURRENT_REPORT_COMMANDS if schema == '33' else HISTORICAL32_REPORT_COMMANDS
    names = []
    failures = []
    try:
        for group, modules, selection in commands:
            name = 'pytest-' + label + '-' + group + '.xml'
            witness = name.replace('.xml', '.witnesses.json')
            environment['CI33_WITNESSES'] = str(private / witness)
            argv = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py', *modules,
                *shlex.split(selection), '-p', 'pg_observer', '-q', '--tb=short',
                '--basetemp=' + str(private / (group + '-pytest')),
                '--junitxml=' + str(private / name)]
            code = execute(argv, source, environment, private / (group + '.raw.log'))
            names.extend([name, witness])
            if code:
                failures.append({'group': group, 'exit': code})
                break
    finally:
        after = photo(source, pg_bin)
        write(private / 'after.json', after)
        write(private / 'roles-after.json', role_catalog(environment))
        pip = execute([sys.executable, '-m', 'pip', 'check'], source, environment, private / 'pip-after.raw.log')
        write(private / 'run-status.json', {'failures': failures, 'sources_packages_binaries_quiet': before == after,
              'roles_quiet': role_catalog(environment) == roles, 'pip_after': pip})
    count = lease_audit(leases, environment)
    assert before == after and role_catalog(environment) == roles and pip == 0 and not failures
    from tests.check_google33_reports import validate
    passed = validate(private, schema)
    summary = {'schema': schema, 'reports': len(commands), 'passed_nodes': passed,
        'sources_packages_binaries_quiet': True, 'pip_before': 0, 'pip_after': 0,
        'closed_leases': count, 'postdrop_absence_fresh': True, 'executed_FORCE': False,
        'backend_termination': False, 'private_raw_uploaded': False}
    write(private / 'runtime-summary.json', summary)
    from tests.ci_google33.publish import publish
    publish(private, args.output.absolute(), [*names, 'runtime-summary.json'])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', choices=('32', '33'), required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    private = private_directory(args.private.absolute())
    try:
        result = run(args, private)
    except Exception:
        (private / 'runner-error.raw.log').write_text(traceback.format_exc(), encoding='utf8')
        parser.exit(1, 'Versioned PostgreSQL gate failed; private diagnostics and attributed UUID leases retained\n')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
