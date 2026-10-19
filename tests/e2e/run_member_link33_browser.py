"""Run the accepted R12 browser against an owned real PostgreSQL fixture.

This is a host-checkout fixture. The separate image gate tests the container.
Private files remain under an owned temporary directory; only a fixed, checked
allowlist is copied to the requested public output directory.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import uuid

ROOT = Path(__file__).resolve().parents[2]
REVISION = '20261019_google_subjects'
PUBLIC_FILES = (
    'startup.json', 'browser-result.json', 'database-closure.json',
    'http-trace.jsonl', 'final-identities.json', 'report.json',
    '01-explicit-acceptance.png', '02-real-recipient-publication.png',
    '03-owner-own-external-contexts.png', '04-account-switch-cleared.png',
)
TOKEN = re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])')


def validate_startup(marker: dict, head: str, port: int) -> None:
    assert marker['fixture'] == 'r12-real-postgres33'
    assert marker['head'] == head and type(marker['pid']) is int and marker['pid'] > 0
    assert type(marker['port']) is int and marker['port'] == port
    assert marker['database_kind'] == 'postgresql'
    assert marker['executed_revision'] == marker['model_target_revision'] == REVISION
    assert marker['business_contract_revision'] == '20261019_client_account_links'
    from web.database.alembic.history_index_contract_v1 import expected_history_index
    validate_history_index(marker['history_order_index'], expected_history_index('postgresql'))
    assert type(marker['model_tables']) is int and marker['model_tables'] == 35
    assert type(marker['actual_tables']) is int and marker['actual_tables'] == 36
    assert marker['application_role_restricted_nonowner'] is True
    assert marker['runtime_pool_size'] == 20 and marker['runtime_max_overflow'] == 10
    assert marker['R12_API_doubles'] is False
    assert marker['first_party_origin'] == 'http://127.0.0.1:' + str(port)


def validate_history_index(actual, expected) -> None:
    """Require the complete closed JSON witness, including exact scalar types."""
    assert type(actual) is type(expected)
    if type(expected) is dict:
        assert set(actual) == set(expected)
        for key in expected:
            validate_history_index(actual[key], expected[key])
    elif type(expected) is list:
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected):
            validate_history_index(left, right)
    else:
        assert actual == expected


def listener_closed(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(.5)
        return probe.connect_ex(('127.0.0.1', port)) != 0


def validate_closure(value: dict) -> None:
    names = value['exact_owned_names']
    assert type(value['count']) is int
    assert isinstance(names, list) and len(names) == value['count'] == 1
    assert all(re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}', name) for name in names)
    assert value['all_owned_absent'] is True and value['remaining'] == []
    assert value['fixture_error_class'] is None


def publish(phase: Path, output: Path) -> list[str]:
    """Never recurse over a private directory or publish partial browser output."""
    from tests.ci_google33.publish import scan
    invitations = [row['token'].encode() for row in json.loads((phase / 'mail.private.json').read_bytes())]
    assert len(invitations) == 3 and all(re.fullmatch(rb'[A-Za-z0-9_-]{43}', item) for item in invitations)
    checked = []
    for name in PUBLIC_FILES:
        source = phase / name
        assert source.is_file() and not source.is_symlink()
        raw = source.read_bytes()
        assert raw and not TOKEN.search(raw), 'Credential pattern in public artifact'
        scan(raw)
        assert all(item not in raw for item in invitations), 'Invitation proof in public artifact'
        if name.endswith('.png'):
            assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        checked.append((name, raw))
    for name, raw in checked:
        with (output / name).open('xb') as stream:
            stream.write(raw)
    return [name for name, _ in checked]


def run(output: Path, port: int) -> None:
    sys.path.insert(0, str(ROOT))
    from tests.isolation import validate_postgres_test_url
    assert 1024 < port < 65536 and listener_closed(port), 'A free loopback port is required'
    configuration = {name: os.environ[name] for name in (
        'METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_PG_BIN')}
    for name in ('METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL'):
        validate_postgres_test_url(configuration[name])
    assert Path(configuration['METODOBASE_TEST_PG_BIN']).is_dir()
    node = shutil.which('node')
    assert node and Path(os.environ['QA_CHROME']).is_file()
    modules = Path(os.environ['QA_NODE_MODULES']).resolve(strict=True)
    assert (modules / 'playwright-core/package.json').is_file() and (modules / 'axe-core/axe.min.js').is_file()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert re.fullmatch(r'[0-9a-f]{40}', head)
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT).strip()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    phase = Path(tempfile.mkdtemp(prefix='metodobase-member31-browser-'))
    configuration_path = phase / 'config.private.json'
    with configuration_path.open('x', encoding='utf8') as stream:
        json.dump(configuration, stream)
    if os.name != 'nt':
        configuration_path.chmod(0o600)
    origin = 'http://127.0.0.1:' + str(port)
    receipt = {'scope': 'Host checkout / actual HTTP / owned migrated PostgreSQL; separate from candidate image',
               'head': head, 'origin': origin, 'executed_revision': REVISION, 'completed': False, 'public_files': [],
               'private_files_uploaded': False, 'API_doubles': False}
    process = None
    failure = None
    fixture_log = (phase / 'fixture.private.log').open('xb')
    try:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', '-B',
            str(ROOT / 'tests/e2e/member_link33_postgres_server.py'), '--root', str(ROOT),
            '--out', str(phase), '--config', str(configuration_path), '--head', head, '--port', str(port)],
            cwd=ROOT, stdout=fixture_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            assert process.poll() is None, 'Owned fixture stopped before readiness'
            marker_path = phase / 'startup.json'
            if marker_path.is_file():
                try:
                    marker = json.loads(marker_path.read_bytes())
                except json.JSONDecodeError:
                    pass  # A writer may still be completing this small marker.
                else:
                    validate_startup(marker, head, port)
                    try:
                        with urlopen(origin + '/health/ready', timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        pass
            time.sleep(.1)
        else:
            raise TimeoutError('Owned PostgreSQL fixture did not become ready')
        environment = dict(os.environ, QA_BROWSER_PHASE=str(phase), QA_NODE_MODULES=str(modules))
        browser = subprocess.run([node, str(ROOT / 'tests/e2e/member_link33_browser.cjs')],
            cwd=ROOT, env=environment, capture_output=True, timeout=300)
        (phase / 'driver.private.log').write_bytes(browser.stdout + browser.stderr)
        assert browser.returncode == 0, 'Real member browser did not complete all required criteria'
        normalize = subprocess.run([sys.executable, '-X', 'utf8', '-B',
            str(ROOT / 'tests/e2e/normalize_member_link33_report.py'),
            '--input', str(phase / 'browser-result.json'), '--output', str(phase / 'report.json'),
            '--expected-head', head, '--expected-origin', origin, '--expected-revision', REVISION], capture_output=True, cwd=ROOT, timeout=10)
        (phase / 'normalizer.private.log').write_bytes(normalize.stdout + normalize.stderr)
        assert normalize.returncode == 0, 'Real browser report was incomplete or inconsistent'
        checked = subprocess.run([sys.executable, str(ROOT / 'scripts/check_frontend_report.py'),
            str(phase / 'report.json'), '--format', 'counts', '--minimum', '16'],
            capture_output=True, cwd=ROOT, timeout=10)
        (phase / 'parser.private.log').write_bytes(checked.stdout + checked.stderr)
        assert checked.returncode == 0
    except BaseException as error:
        failure = error
        receipt['failure_class'] = type(error).__name__
    finally:
        if process is not None:
            if process.poll() is None:
                pending = phase / 'control-stop.pending.private.json'
                pending.write_text(json.dumps({'id': str(uuid.uuid4()), 'action': 'stop'}), encoding='utf8')
                pending.replace(phase / 'control.private.json')
            try:
                process.wait(timeout=45)
                receipt['fixture_exit'] = process.returncode
                assert process.returncode == 0
                validate_closure(json.loads((phase / 'database-closure.json').read_bytes()))
                assert listener_closed(port), 'Owned listener did not close'
                receipt['database_absent'] = receipt['listener_closed'] = True
            except BaseException as error:
                if failure is None:
                    failure = error
                    receipt['failure_class'] = type(error).__name__
        fixture_log.close()
        if failure is None:
            try:
                receipt['public_files'] = publish(phase, output)
                receipt['completed'] = True
                receipt['required_criteria'] = 16
            except BaseException as error:
                failure = error
                receipt['failure_class'] = type(error).__name__
        with (output / 'receipt.json').open('x', encoding='utf8', newline='\n') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
    if failure is not None:
        # Keep full diagnostics private, without printing provider URLs or proofs.
        raise RuntimeError('Member browser gate failed; private diagnostics retained in owned temp storage') from None
    print(json.dumps({'head': head, 'passed': 16, 'total': 16, 'database_absent': True,
                      'listener_closed': True, 'public_files': len(receipt['public_files'])}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8796)
    args = parser.parse_args()
    run(args.output, args.port)


if __name__ == '__main__':
    main()
