"""Own current31 image and real MFA/PG browser fixtures, with private raw logs.

Invoked only by its explicit CI image job or a coordinated local test window.
No fixture process or database is claimed as executed by static verification.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hashlib
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
from urllib.request import build_opener, ProxyHandler
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.ci_mfa31.publish import publish
from tests.isolation import validate_postgres_test_url
from tests.run_reviewed_ci30 import trusted_baseline


def source_hashes() -> dict:
    result = {}
    names = subprocess.check_output(['git', '--no-replace-objects', 'ls-files', '-z'], cwd=ROOT).split(b'\0')
    for raw in names:
        if not raw:
            continue
        name = raw.decode('utf8')
        if not name.startswith('docs/'):
            path = ROOT / name
            assert path.is_file() and not path.is_symlink()
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def execute(argv: list[str], phase: Path, name: str, environment: dict, timeout=400, *, stdin=None) -> bytes:
    with (phase / (name + '.private.stdout')).open('xb') as stdout, (phase / (name + '.private.stderr')).open('xb') as stderr:
        result = subprocess.run(argv, cwd=ROOT, env=environment, input=stdin, stdout=stdout, stderr=stderr,
                                timeout=timeout, check=False)
    assert result.returncode == 0, 'Current31 child gate failed; diagnostics retained privately: ' + name
    return (phase / (name + '.private.stdout')).read_bytes()


def free_port(port: int) -> None:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))


def wait_ready(process, port: int, marker, validate, timeout=120) -> dict:
    deadline = time.monotonic() + timeout
    opener = build_opener(ProxyHandler({}))
    while time.monotonic() < deadline:
        assert process.poll() is None, 'Owned fixture stopped before readiness'
        try:
            value = marker()
            validate(value, process.pid)
            with opener.open('http://127.0.0.1:' + str(port) + '/health/ready', timeout=1) as response:
                if response.status == 200:
                    return value
        except (OSError, ValueError, KeyError, AssertionError, json.JSONDecodeError):
            time.sleep(.2)
    raise TimeoutError('Current31 owned fixture did not satisfy real readiness/marker')


@contextmanager
def fixture(argv: list[str], phase: Path, name: str, environment: dict, stop_file: Path | None):
    stdout = (phase / (name + '.private.log')).open('xb')
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=subprocess.STDOUT)
    control_failed = False
    try:
        yield process
    finally:
        if process.poll() is None:
            if stop_file is not None:
                try:
                    assert not stop_file.is_symlink()
                    stop_file.touch(exist_ok=True)
                except BaseException:
                    # Still close the exact owned child if the private control
                    # channel cannot be written; never leave a process behind.
                    process.terminate()
                    control_failed = True
            else:
                process.terminate()  # exact Popen child, never a listener/PID discovered by port
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            raise RuntimeError('Owned fixture required forced shutdown') from None
        finally:
            stdout.close()
        assert process.returncode == 0 or (stop_file is None and process.returncode == -15), 'Owned fixture finalizer failed'
        assert not control_failed, 'Owned fixture private control failed'


def validate_pg_marker(value, pid):
    assert value['pid'] == pid and value['runtime_revision'] == '20261019_mfa'
    assert value['model_tables'] == 32 and value['actual_tables'] == 33
    if 'application_role_restricted_nonowner' in value:
        assert value['application_role_restricted_nonowner'] is True


def require_browser_report(path: Path, count: int, *, list_name='checks', completed=None) -> None:
    value = json.loads(path.read_bytes())
    assert len(value[list_name]) == count
    assert value.get('pageErrors', value.get('page_errors', [])) == []
    if list_name == 'results':
        assert all(item['passed'] is True for item in value[list_name])
    if completed:
        assert value[completed] is True


def image(tag: str, phase: Path, environment: dict) -> None:
    expected = subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', expected)
    private = phase / 'image'
    private.mkdir(mode=0o700)
    runtime = dict(METODOBASE_ENV='testing', DATABASE_URL=environment['METODOBASE_TEST_POSTGRES_URL'],
        WEB_SECRET_KEY=base64.urlsafe_b64encode(os.urandom(48)).decode(),
        MFA_ENCRYPTION_KEY=base64.urlsafe_b64encode(os.urandom(32)).decode(),
        METODOBASE_DATA_DIR='/data', OBJECT_STORAGE_BACKEND='local', OBJECT_STORAGE_LOCAL_ROOT='/tmp/image31-objects',
        METODOBASE_SEED_DEMO='0', PORT='8765', BASE_URL='http://127.0.0.1:8765',
        CORS_ORIGINS='http://127.0.0.1:8765', RATE_LIMIT_ENABLED='true', WEB_WORKERS='1')
    for filename, values in [('runtime.env', runtime), ('bootstrap.env', dict(runtime,
            MIGRATOR_DATABASE_URL=environment['METODOBASE_TEST_MIGRATOR_URL']))]:
        path = private / filename
        path.write_text(''.join(key + '=' + value + '\n' for key, value in values.items()), encoding='utf8')
        path.chmod(0o600)
    execute([sys.executable, '-X', 'utf8', 'tests/ci_mfa31/image_roles.py', 'before'], phase, 'image-role-before', environment)
    execute(['docker', 'run', '--rm', '--network', 'host', '--entrypoint', 'python', '--env-file',
             str(private / 'bootstrap.env'), tag, '/app/db_bootstrap.py'], phase, 'image-bootstrap', environment)
    execute([sys.executable, '-X', 'utf8', 'tests/ci_mfa31/image_roles.py', 'after'], phase, 'image-role-after', environment)
    free_port(8765)
    owner = uuid.uuid4().hex
    container = None
    cidfile = private / 'container-id.private.txt'
    def identity():
        value = subprocess.check_output(['docker', 'inspect', container, '--format',
            '{{.Id}}|{{.Image}}|{{index .Config.Labels "metodobase.ci31.owner"}}'], text=True).strip()
        assert value == container + '|' + expected + '|' + owner
    try:
        raw = execute(['docker', 'run', '--detach', '--name', 'metodobase-current31-' + owner,
            '--cidfile', str(cidfile),
            '--label', 'metodobase.ci31.owner=' + owner, '--network', 'host', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--read-only', '--tmpfs', '/data:rw,nosuid,nodev,mode=1777',
            '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777', '--env-file', str(private / 'runtime.env'), tag],
            phase, 'image-start', environment)
        candidate = raw.decode().strip()
        assert re.fullmatch(r'[0-9a-f]{64}', candidate)
        container = candidate
        identity()
        opener = build_opener(ProxyHandler({}))
        for _ in range(120):
            try:
                with opener.open('http://127.0.0.1:8765/health/ready', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.5)
        else:
            raise TimeoutError('Current image real entrypoint was not ready')
        raw = execute(['docker', 'exec', '-i', container, 'python', '-'], phase, 'image-inventory', environment,
                      stdin=(ROOT / 'tests/ci_mfa31/image_inventory.py').read_bytes())
        inventory = json.loads(raw)
        assert inventory['complete'] is True
        for name, digest in inventory['sources_sha256'].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        (phase / 'image-inventory.json').write_bytes(raw)
        execute([environment['CI31_NODE'], 'tests/e2e/mfa31_image.cjs', str(phase / 'image-browser.json')],
                phase, 'image-browser', dict(environment, METODOBASE_E2E_URL='http://127.0.0.1:8765'))
        require_browser_report(phase / 'image-browser.json', 6, completed='complete')
        (phase / 'image-identity.json').write_bytes((json.dumps({'complete': True, 'image_id': expected,
            'actual_entrypoint': 'Docker CMD /app/entrypoint.sh -> python web/main_web.py --no-browser',
            'flags_scope': 'LAB execution flags, not Dockerfile defaults', 'test_settings': True}) + '\n').encode())
    finally:
        if container is None and cidfile.exists():
            assert cidfile.is_file() and not cidfile.is_symlink()
            container = cidfile.read_text().strip()
            assert re.fullmatch(r'[0-9a-f]{64}', container)
        if container is not None:
            identity()
            execute(['docker', 'stop', '--time', '15', container], phase, 'image-stop', environment, timeout=40)
            execute(['docker', 'rm', container], phase, 'image-remove', environment, timeout=20)


def run(output: Path, tag: str) -> None:
    assert os.name == 'posix', 'This Docker/browser CI orchestration requires a coordinated Linux runner'
    trusted_baseline()
    before = source_hashes()
    phase = Path(tempfile.mkdtemp(prefix='metodobase-ci31-private-'))
    phase.chmod(0o700)
    environment = dict(os.environ, CI31_NODE=shutil.which('node') or '')
    assert environment['CI31_NODE'] and Path(environment['CHROME_PATH']).is_file()
    configuration = {key: environment[key] for key in
                     ('METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL', 'METODOBASE_TEST_PG_BIN')}
    for key in ('METODOBASE_TEST_MIGRATOR_URL', 'METODOBASE_TEST_POSTGRES_URL'):
        validate_postgres_test_url(configuration[key])
    config = phase / 'config.private.json'
    config.write_bytes((json.dumps(configuration) + '\n').encode())
    config.chmod(0o600)
    modules = ROOT / 'tests/e2e/node_modules'
    environment.update(QA_NODE_MODULES=str(modules), QA_CHROME=environment['CHROME_PATH'],
        FOLLOWUP_NODE_MODULES=str(modules), METODOBASE_E2E_DEPENDENCIES=str(modules),
        NODE_PATH=str(modules), TEMP=tempfile.gettempdir(), TMPDIR=tempfile.gettempdir())
    image(tag, phase, environment)
    execute([sys.executable, '-X', 'utf8', '-B', 'tests/e2e/run_member_link31_browser.py',
             '--output', str(phase / 'member'), '--port', '8794'], phase, 'member', environment)
    shutil.copyfile(phase / 'member/report.json', phase / 'member-report.json')
    followup = phase / 'followup'
    followup.mkdir()
    free_port(8795)
    command = [sys.executable, '-X', 'utf8', '-B', 'tests/e2e/followup31_server.py', '--pg-config', str(config),
               '--report', str(followup / 'startup.json'), '--stop-file', str(followup / 'stop'), '--port', '8795']
    with fixture(command, phase, 'followup', environment, followup / 'stop') as process:
        wait_ready(process, 8795, lambda: json.loads((followup / 'startup.json').read_bytes()), validate_pg_marker)
        execute([environment['CI31_NODE'], 'tests/e2e/dashboard_followup31_browser.cjs', str(followup)],
                phase, 'followup-browser', dict(environment, FOLLOWUP_STARTUP_REPORT=str(followup / 'startup.json'),
                                               METODOBASE_E2E_URL='http://127.0.0.1:8795'))
        require_browser_report(followup / 'report.json', 8, list_name='results')
    shutil.copyfile(followup / 'report.json', phase / 'followup-report.json')
    daily = phase / 'daily'
    daily.mkdir(mode=0o700)
    free_port(8800)
    with fixture([sys.executable, '-X', 'utf8', '-B', 'tests/e2e/daily_plan31_server.py', '--private', str(daily),
                  '--config', str(config)], phase, 'daily', environment, daily / 'stop') as process:
        wait_ready(process, 8800, lambda: json.loads((daily / 'startup.json').read_bytes()), validate_pg_marker)
        execute([environment['CI31_NODE'], 'tests/e2e/daily_plan31_browser.cjs'], phase, 'daily-browser',
                dict(environment, R24_PRIVATE=str(daily), R24_BROWSER_OUTPUT=str(daily / 'browser')))
        require_browser_report(daily / 'browser/report.json', 11)
    assert json.loads((daily / 'resource.json').read_bytes())['owned_database_absent_after'] is True
    assert json.loads((daily / 'close.json').read_bytes())['sources_stable'] is True
    shutil.copyfile(daily / 'browser/report.json', phase / 'daily-report.json')
    batch = 'ci-' + uuid.uuid4().hex
    free_port(8802)
    with fixture([sys.executable, '-X', 'utf8', '-B', 'tests/e2e/mfa_ui_server.py'], phase, 'mfa-ui',
                 environment, None) as process:
        def marker():
            return json.loads((phase / 'mfa-ui.private.log').read_bytes().splitlines()[0])
        def validate(value, pid):
            assert value['pid'] == pid and value['actual_alembic_revision'] == '20261019_mfa'
            assert value['expected_runtime_revision'] == '20261019_mfa'
            assert value['metadata_table_count'] == 32 and value['physical_table_count'] == 33
        wait_ready(process, 8802, marker, validate)
        for driver in ('mfa_ui_browser', 'mfa_personal_browser'):
            execute([environment['CI31_NODE'], 'tests/e2e/' + driver + '.cjs'], phase, driver,
                    dict(environment, METODOBASE_EVIDENCE_BATCH=batch, METODOBASE_E2E_URL='http://127.0.0.1:8802'))
        reports = ROOT / 'docs/implementation/20261018-evolution/evidence/mfa-ui31'
        for kind, name, minimum in [('browser', 'mfa-ui-report.json', 11), ('personal', 'mfa-personal-report.json', 4)]:
            original = reports / (kind + '-' + batch) / 'report.json'
            require_browser_report(original, minimum, completed='complete')
            shutil.copyfile(original, phase / name)
    assert source_hashes() == before, 'Current source changed while image/browser gates ran'
    names = ['image-inventory.json', 'image-identity.json', 'image-browser.json', 'member-report.json',
             'followup-report.json', 'daily-report.json', 'mfa-ui-report.json', 'mfa-personal-report.json']
    publish(phase, output, names)
    print(json.dumps({'current31_components': 6, 'published_reports': len(names),
                      'raw_logs_and_factors_uploaded': False, 'sources_quiet': True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--image-tag', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'metodobase-current31:[0-9a-f]{40}', args.image_tag)
    run(args.output.absolute(), args.image_tag)


if __name__ == '__main__':
    main()
