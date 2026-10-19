"""Own-fixture browser review for R29/R34; only ports/output directories adapt."""
import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
import zipfile

MAIN = Path(r'F:\MetodoBaseWeb-execution-20261018')
EVIDENCE = MAIN / 'docs/implementation/20261018-evolution/evidence'
OLD_GUARD = EVIDENCE / 'ux/diary-ui-bf46-independent-20261019-qa/browser_network_guard.cjs'
BASE_PYTHON = Path(r'C:\Users\Consu\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(out, name, value):
    with (out / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def ps(code):
    result = subprocess.run(['powershell', '-NoProfile', '-Command', code], capture_output=True,
                            encoding='utf8', errors='replace', timeout=20)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def process(pid):
    text = ps("Get-CimInstance Win32_Process -Filter 'ProcessId = " + str(pid) + "' | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress")
    return json.loads(text) if text else None


def public_process(identity):
    if not identity:
        return None
    return {key: value for key, value in identity.items() if key != 'CommandLine'} | {'command_sha256': sha(identity['CommandLine'].encode())}


def listeners(port):
    text = ps('Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq ' + str(port) + ' | Select-Object -ExpandProperty OwningProcess | ConvertTo-Json -Compress')
    values = json.loads(text) if text else []
    return sorted(set(values if isinstance(values, list) else [values]))


def foreign():
    return {str(port): [public_process(process(pid)) for pid in listeners(port)] for port in [8776, 8777, 8780, 8781, 8784]}


def photo(root, head, prefix):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True)
    assert git('rev-parse', 'HEAD').strip() == head
    assert git('status', '--porcelain') == ''
    paths = [path for path in git('ls-files', '-z').split('\0') if path and
             (not path.startswith('docs/') or '/evidence/' + prefix + '/' in path or
              '/evidence/history-headers-followup/' in path)]
    node = [path for name in ['playwright-core', 'axe-core']
            for path in (MAIN / 'tests/e2e/node_modules' / name).rglob('*') if path.is_file()]
    return {'head': head, 'sources': {path: sha((root / path).read_bytes()) for path in paths},
            'packages': sorted([dist.metadata['Name'], dist.version] for dist in importlib.metadata.distributions()),
            'readonly_node_dependencies': {path.relative_to(MAIN).as_posix(): sha(path.read_bytes()) for path in sorted(node)}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['history', 'landing'])
    parser.add_argument('--head', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--own-driver', type=Path)
    parser.add_argument('--own-only', action='store_true')
    parser.add_argument('--own-checks', type=int, default=3)
    args = parser.parse_args()
    root = Path(r'F:\MetodoBaseWeb-history-ci-20261019')
    prefix = 'history-pagination' if args.kind == 'history' else 'landing'
    stem = 'personal_history' if args.kind == 'history' else 'landing'
    original_port = 8780 if args.kind == 'history' else 8781
    fixture_name = 'personal-history-ui' if args.kind == 'history' else 'public-landing'
    expected_checks = 10 if args.kind == 'history' else 8
    out = args.output.resolve(); assert out.is_relative_to(EVIDENCE)
    out.mkdir(exist_ok=False)
    base = 'http://127.0.0.1:' + str(args.port)
    before = photo(root, args.head, prefix); save(out, 'before.json', before)
    assert len(before['packages']) == 89 and len(before['readonly_node_dependencies']) == 146
    prior = foreign(); save(out, 'foreign-before.json', prior)
    assert not listeners(args.port)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, encoding='utf8', timeout=30)
    (out / 'pip-before.log').write_text(pip.stdout + pip.stderr, encoding='utf8'); assert pip.returncode == 0
    snapshot = root / ('docs/implementation/20261018-evolution/evidence/' + prefix + '/source-freeze.json')
    manifest = json.loads(snapshot.read_text(encoding='utf8'))
    archive_path = root / manifest['raw_source_archive']['path']
    assert sha(archive_path.read_bytes()) == manifest['raw_source_archive']['sha256']
    fixture_path = 'tests/e2e/' + stem + '_server.py'
    driver_path = 'tests/e2e/' + stem + ('_browser.cjs' if args.kind == 'history' else '.cjs')
    with zipfile.ZipFile(archive_path) as archive:
        fixture_raw = archive.read(fixture_path); driver_raw = archive.read(driver_path)
    historical_fixture_raw = fixture_raw
    for path, data in [(fixture_path, historical_fixture_raw), (driver_path, driver_raw)]:
        assert sha(data) == manifest['sources'][path]['raw_sha256']
    fixture_raw = (root / fixture_path).read_bytes()
    fixture_git = subprocess.check_output(['git', 'show', args.head + ':' + fixture_path], cwd=root)
    driver_git = subprocess.check_output(['git', 'show', args.head + ':' + driver_path], cwd=root)
    assert fixture_raw.replace(b'\r\n', b'\n') == fixture_git
    assert driver_raw.replace(b'\r\n', b'\n') == driver_git
    assert driver_git == (root / driver_path).read_bytes().replace(b'\r\n', b'\n')
    old_tree = ast.parse(historical_fixture_raw)
    current_tree = ast.parse(fixture_raw)
    target_change = 'No AST change from authenticated author fixture'
    if ast.dump(old_tree) != ast.dump(current_tree):
        class RestoreHistoricalTarget(ast.NodeTransformer):
            imports = 0
            calls = 0
            def visit_ImportFrom(self, node):
                if node.module == 'web.database.schema_control':
                    assert [(entry.name, entry.asname) for entry in node.names] == [('expected_head', None)]
                    self.imports += 1
                    return None
                return node
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id == 'expected_head':
                    assert not node.args and not node.keywords
                    self.calls += 1
                    return ast.Constant('20261019_personal_diary')
                return self.generic_visit(node)
        transform = RestoreHistoricalTarget()
        restored = transform.visit(current_tree)
        assert transform.imports == transform.calls == 1
        assert ast.dump(restored) == ast.dump(old_tree), 'Fixture behavior changed beyond dynamic target marker'
        target_change = 'Only expected_head import and marker call replace historical revision27 literal'
    save(out, 'fixture-target28-review.json', {
        'head': args.head, 'historical_fixture_raw_sha256': sha(historical_fixture_raw),
        'current_fixture_raw_sha256': sha(fixture_raw), 'current_fixture_git_sha256': sha(fixture_git),
        'current_driver_git_sha256': sha(driver_git), 'driver_raw_sha256': sha(driver_raw),
        'fixture_review': target_change, 'driver_assertions_unchanged': True,
        'scope': 'New composed target28 fixture authenticated against current HEAD; original author snapshot and its target27 acceptance remain intact.'})
    server_text = fixture_raw.decode('utf8').replace(str(original_port), str(args.port))
    assert server_text.replace(str(args.port), str(original_port)).encode() == fixture_raw
    (out / 'server-adapted.py').write_bytes(server_text.encode())
    launcher = out / 'run_server.py'
    launcher.write_text('from pathlib import Path\nsource=Path(' + repr(str(out / 'server-adapted.py')) + ").read_bytes().decode('utf8')\nexec(compile(source," + repr(str(root / fixture_path)) + ",'exec'),{'__file__':" + repr(str(root / fixture_path)) + ",'__name__':'__main__'})\n", encoding='utf8')
    if args.kind == 'history':
        old_output = "path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/history-pagination/browser-'+(process.env.METODOBASE_EVIDENCE_BATCH||Date.now()))"
    else:
        old_output = "path.join(root,'docs/implementation/20261018-evolution/evidence/landing/browser-'+(process.env.METODOBASE_EVIDENCE_BATCH||Date.now()))"
    original_driver = driver_raw.decode('utf8')
    assert original_driver.count(old_output) == 1
    new_output = json.dumps(str(out / 'author-browser'))
    adapted_driver = original_driver.replace(str(original_port), str(args.port)).replace(old_output, new_output)
    assert adapted_driver.replace(new_output, old_output).replace(str(args.port), str(original_port)) == original_driver
    (out / 'author-adapted.cjs').write_bytes(adapted_driver.encode())
    guard_source = OLD_GUARD.read_bytes().decode('utf8')
    old_literal = "const base='http://127.0.0.1:8789',output="
    assert guard_source.count(old_literal) == 1
    guard_source = guard_source.replace(old_literal, 'const base=process.env.METODOBASE_E2E_URL,output=')
    (out / 'network-guard.cjs').write_bytes(guard_source.encode())
    save(out, 'adaptations.json', {'raw_archive_sha256': sha(archive_path.read_bytes()),
        'fixture_original_sha256': sha(fixture_raw), 'fixture_adapted_sha256': sha(server_text.encode()),
        'driver_original_sha256': sha(driver_raw), 'driver_adapted_sha256': sha(adapted_driver.encode()),
        'driver_and_fixture_exact_reversal_proven': True, 'allowed_changes': ['fixture/driver own port', 'driver output directory'],
        'network_guard_original_sha256': sha(OLD_GUARD.read_bytes()),
        'network_guard': 'Previously accepted exact-origin/maxRedirects0 wrapper; only own origin is supplied through environment.',
        'own_driver_sha256': sha(args.own_driver.read_bytes()) if args.own_driver else None})
    env = dict(os.environ, NODE_PATH=str(MAIN / 'tests/e2e/node_modules'), METODOBASE_E2E_URL=base,
               CHROME_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe', METODOBASE_TEST_PYTHON=sys.executable)
    server = None; owned = None; startup = None; results = []; failure = None
    log = (out / 'server.log').open('xb')
    try:
        server = subprocess.Popen([sys.executable, '-X', 'utf8', str(launcher)], cwd=root, env=env,
                                  stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        parent = process(server.pid)
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, message, headers, newurl):
                raise HTTPError(request.full_url, code, 'Own fixture redirects rejected', headers, fp)
        opener = build_opener(ProxyHandler({}), NoRedirect())
        for attempt in range(200):
            assert server.poll() is None, 'Own fixture stopped before readiness'
            for line in (out / 'server.log').read_text(encoding='utf8').splitlines():
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict) and value.get('fixture') == fixture_name:
                    startup = value
            if startup:
                try:
                    with opener.open(base + '/health/ready', timeout=1) as response:
                        assert response.status == 200
                    break
                except URLError:
                    pass
            time.sleep(.1)
        assert startup and startup['tables'] == 26 and startup['model_target_revision'] == '20261019_account_recovery'
        pids = listeners(args.port); assert len(pids) == 1
        owned = process(pids[0]); assert owned
        assert owned['ProcessId'] == server.pid or owned['ParentProcessId'] == server.pid
        assert str(launcher).lower() in owned['CommandLine'].lower()
        assert Path(owned['ExecutablePath']).resolve() in {Path(sys.executable).resolve(), BASE_PYTHON.resolve()}
        save(out, 'owned-process-start.json', {'launcher': public_process(parent), 'listener': public_process(owned)})
        save(out, 'startup.json', startup)
        print('Own ' + args.kind + ' fixture ready at port ' + str(args.port), flush=True)
        if args.own_only:
            assert args.own_driver
        if args.own_only and args.kind == 'history':
            assert args.kind == 'history' and args.own_driver
            from urllib.request import Request
            from uuid import uuid4
            def call(path, payload=None, token=None):
                headers = {'Content-Type': 'application/json'}
                if token:
                    headers.update({'Authorization': 'Bearer ' + token, 'Idempotency-Key': str(uuid4())})
                request = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None,
                                  headers=headers, method='POST' if payload is not None else 'GET')
                with opener.open(request, timeout=30) as response:
                    assert response.status == 200
                    return json.load(response)
            pair = call('/api/auth/login', {'email': 'diary-history@example.invalid', 'password': 'Synthetic-Diary-Password-2026!'})
            me = call('/api/auth/me', token=pair['token']); assert me['role'] == 'viewer' and me['tipo'] == 'usuario'
            generated = [call('/api/usuario/generar-plan', {}, pair['token']) for _ in range(2)]
            assert all(plan['plan_id'] > 0 and plan['tiene_pdf'] for plan in generated)
            assert generated[1]['plan_id'] > generated[0]['plan_id']
            save(out, 'own-fixture-preparation.json', {'role': 'viewer', 'tipo': 'usuario',
                'actual_worker_plans': [{'plan_id': plan['plan_id'], 'tiene_pdf': plan['tiene_pdf']} for plan in generated],
                'scope': 'Same real two-worker-plan prerequisite as original author driver; no browser10 replay or fake rows added.'})
        drivers = [] if args.own_only else [('author', out / 'author-adapted.cjs', root / driver_path, expected_checks)]
        if args.own_driver:
            drivers.append(('own', args.own_driver.resolve(), args.own_driver.resolve(), args.own_checks))
        for label, source, filename, checks in drivers:
            target = out / (label + '-browser')
            runtime_env = dict(env, QA_BROWSER_OUTPUT=str(target), QA_DRIVER_SOURCE=str(source),
                               QA_DRIVER_FILENAME=str(filename), METODOBASE_QA_OWN_OUTPUT=str(target))
            started = time.monotonic()
            result = subprocess.run(['node', str(out / 'network-guard.cjs')], cwd=root, env=runtime_env,
                                    capture_output=True, text=True, encoding='utf8', timeout=240)
            (out / (label + '.log')).write_text(result.stdout + result.stderr, encoding='utf8')
            report = json.loads((target / 'report.json').read_text(encoding='utf8'))
            results.append({'label': label, 'exit': result.returncode, 'checks': len(report['checks']),
                            'screens': len(report.get('screens', [])), 'pageErrors': report['pageErrors'],
                            'passed': report.get('passed'), 'seconds': round(time.monotonic() - started, 3)})
            save(out, label + '-result.json', results[-1])
            assert result.returncode == 0 and report.get('passed') is True, report.get('error')
            assert len(report['checks']) == checks and report['pageErrors'] == []
            guard = json.loads((target / 'network-guard.json').read_text())
            assert guard['exactOrigin'] == base and guard['maxRedirects'] == 0
            assert type(guard['blockedOtherOrigins']) is int and guard['blockedOtherOrigins'] >= 0
            print(label + ': ' + str(checks) + ' passed', flush=True)
    except BaseException as error:
        failure = {'class': type(error).__name__, 'detail': str(error)}
    finally:
        if owned:
            current = process(owned['ProcessId']); assert current == owned
            ps('Stop-Process -Id ' + str(owned['ProcessId']) + ' -ErrorAction Stop')
        if server:
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                current_parent = process(server.pid); assert current_parent == parent
                server.terminate(); server.wait(timeout=10)
        log.close()
    assert not listeners(args.port)
    if owned:
        assert process(owned['ProcessId']) is None
    after_foreign = foreign(); save(out, 'foreign-after.json', after_foreign); assert prior == after_foreign
    save(out, 'owned-process-close.json', {'listener_gone': True, 'launcher_exit': server.returncode if server else None,
        'owned_port_free': True, 'foreign_ports_fingerprints_unchanged': True,
        'start_fingerprint': public_process(owned), 'failure': failure})
    after = photo(root, args.head, prefix); save(out, 'after.json', after); assert before == after
    pip_after = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, encoding='utf8', timeout=30)
    (out / 'pip-after.log').write_text(pip_after.stdout + pip_after.stderr, encoding='utf8'); assert pip_after.returncode == 0
    summary = {'head': args.head, 'kind': args.kind, 'port': args.port, 'results': results, 'failure': failure,
               'sources': len(before['sources']), 'sources_stable': True, 'packages': len(before['packages']),
               'packages_stable': True, 'readonly_node_dependency_files': len(before['readonly_node_dependencies']),
               'readonly_node_dependencies_stable': True, 'pip_check_before_after': [0, 0],
               'own_pid_closed_and_foreign_listeners_untouched': True,
               'scope': 'Real loopback HTTP + metadata-only SQLite, exact-origin/maxRedirects0 and blocked external sockets. No provider, migration, PG, load, publication or Actions claim.'}
    save(out, 'summary.json', summary)
    files = {path.relative_to(out).as_posix(): sha(path.read_bytes()) for path in sorted(out.rglob('*')) if path.is_file()}
    save(out, 'manifest.json', {'files': files, 'count': len(files)})
    print(json.dumps({'summary_sha256': sha((out / 'summary.json').read_bytes()),
                      'manifest_sha256': sha((out / 'manifest.json').read_bytes()), **summary}))
    assert failure is None


if __name__ == '__main__':
    main()
