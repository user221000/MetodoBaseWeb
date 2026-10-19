"""Seal closed checkpoint125 evidence. No tests, database, source edits or Git mutations."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import importlib.metadata
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

T = Path(r'C:/Users/Consu/AppData/Local/Temp')
M = Path(r'F:/MetodoBaseWeb-execution-20261018')
E = M / 'docs/implementation/20261018-evolution/evidence'
HERE = Path(__file__).parent
PRIVATE = T / 'metodobase-checkpoint125-originals-private-20261019'
sha = lambda b: hashlib.sha256(b).hexdigest()
encode = lambda d: (json.dumps(d, ensure_ascii=True, indent=2) + '\n').encode()
read = lambda p: json.loads(p.read_bytes())

def exclusive(path, blob):
    with path.open('xb') as handle:
        handle.write(blob)
    assert path.read_bytes() == blob

def git_blob(ref, path):
    return subprocess.check_output(['git', '--no-replace-objects', 'show', ref + ':' + path], cwd=M)

def package_state():
    result = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata['Name'].lower().replace('_', '-')
        result[name] = {'version': dist.version, 'metadata_sha256': sha((dist.read_text('METADATA') or '').encode())}
    assert len(result) == 89
    return {'packages': result, 'executable_sha256': sha(Path(sys.executable).read_bytes()),
            'base_executable_sha256': sha(Path(sys._base_executable).read_bytes())}

def pip_check():
    run = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, timeout=60)
    assert run.returncode == 0
    return run

def rows(path):
    cases = ET.fromstring(path.read_bytes()).findall('.//testcase')
    out = [{'case': c.get('classname', '') + '::' + c.get('name', ''),
            'outcome': next((k for k in ('failure', 'error', 'skipped') if c.find(k) is not None), 'passed')}
           for c in cases]
    assert len({r['case'] for r in out}) == len(out)
    return out

def counts(cases):
    return {'cases': len(cases), **{k: sum(c['outcome'] == k for c in cases) for k in ('passed', 'failure', 'error', 'skipped')}}

scanner_file = T / 'metodobase-checkpoint119-prepare.py'
scanner_raw = scanner_file.read_bytes()
definition = next(n for n in ast.parse(scanner_raw).body if isinstance(n, ast.FunctionDef) and n.name == 'scan')
scanner_exact = ast.get_source_segment(scanner_raw.decode(), definition).encode() + b'\n'
exec(compile(ast.Module(body=[definition], type_ignores=[]), 'checkpoint119-preserved-scan', 'exec'))

groups = {
    'terminal': ['metodobase-mfa31-composed-serial-terminal-sv-20261019'],
    'logging': ['metodobase-bootstrap-log-' + s + '-20261019' for s in ('source', 'before', 'after', 'integration', 'integration-lint')],
    'clock': ['metodobase-mfa31-fixture-clock-' + s + '-20261019' for s in ('source', 'before', 'after', 'integration', 'ci-preflight')],
}
prefixes = {
    'terminal': 'root-mfa31-terminal-sv-serial-diagnostic-20261019',
    'logging': 'root-bootstrap-outcome-logging-author-20261019',
    'clock': 'root-mfa31-fixture-clock-author-20261019',
}
archives = {'terminal': 'terminal-sv-originals.zip', 'logging': 'logging-originals.zip', 'clock': 'fixture-clock-originals.zip'}
assert all(not (E / name).exists() for name in prefixes.values())
assert not PRIVATE.exists()
original = {}
excluded = {}
for key, directories in groups.items():
    original[key] = {}
    excluded[key] = []
    for directory in directories:
        for file in sorted((T / directory).iterdir()):
            member = directory + '/' + file.name
            if file.is_dir() or file.name == '.coverage':
                excluded[key].append({'member': member, 'reason': 'Temporary directories and binary coverage database are excluded; no database or environment files are archived.'})
                continue
            assert file.is_file() and not file.is_symlink()
            assert file.suffix.lower() not in ('.db', '.sqlite', '.sqlite3', '.env')
            original[key][member] = file.read_bytes()
original_meta = {key: {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in files.items()} for key, files in original.items()}
state_before = package_state()
pip_before = pip_check()

# Authenticate prior case sets against their committed manifests before using them.
old2598 = E / 'main-r23-r24-regression-20261019'
old3039 = E / 'root-mfa31-composed-serial-diagnostic-20261019'
baseline_proof = {}
for name, directory, artifact in [('2598', old2598, 'serial.xml'), ('3039', old3039, 'all-cases.STRUCTURAL.json')]:
    manifest_raw = (directory / 'manifest.json').read_bytes()
    relative = (directory / 'manifest.json').relative_to(M).as_posix()
    assert git_blob('HEAD', relative) == manifest_raw
    manifest = json.loads(manifest_raw)
    info = manifest.get('files', manifest)[artifact]
    blob = (directory / artifact).read_bytes()
    assert info['sha256'] == sha(blob) and info['bytes'] == len(blob)
    baseline_proof[name] = {'manifest_path': relative, 'manifest_sha256': sha(manifest_raw), 'artifact': artifact,
                            'artifact_sha256': sha(blob), 'manifest_matches_committed_HEAD': True}
base2598 = {r['case'] for r in rows(old2598 / 'serial.xml')}
base3039 = {r['case'] for r in read(old3039 / 'all-cases.STRUCTURAL.json')}
assert len(base2598) == 2598 and len(base3039) == 3039 and base2598 <= base3039

terminal = T / groups['terminal'][0]
report = read(terminal / 'summary.private.json')
current = rows(terminal / 'results.xml')
assert report['head'] == '6a75d096ea3d63d9e78c76d33b7e243160b23364'
assert report['exit'] == 1 and not report['timed_out']
assert counts(current) == {'cases': 3047, 'passed': 3045, 'failure': 0, 'error': 1, 'skipped': 1}
assert base3039 <= {r['case'] for r in current}
assert report['sources_packages_python_exact'] and report['pip_before'] == report['pip_after'] == 0
assert report['known_windows_skip_exact']
assert (terminal / 'before.json').read_bytes() == (terminal / 'after.json').read_bytes()
coverage_script = M / 'tests/check_coverage.py'
assert coverage_script.read_bytes().replace(b'\r\n', b'\n') == git_blob(report['head'], 'tests/check_coverage.py')
coverage = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(coverage_script), str(terminal / 'coverage.json')], cwd=M, capture_output=True, timeout=30)
assert coverage.returncode == 0

public = {key: {} for key in groups}
for key in groups:
    public[key]['seal-driver.py'] = Path(__file__).read_bytes()
    public[key]['archive-acl.ps1'] = (HERE / 'archive-acl.ps1').read_bytes()
    public[key]['checkpoint119-scanner.py'] = scanner_exact
    public[key]['original-files.json'] = encode({'files': original_meta[key], 'excluded': excluded[key], 'originals_unchanged': True})
    public[key]['checkpoint119-scanner-source.json'] = encode({'source': str(scanner_file), 'sha256': sha(scanner_raw), 'function_sha256': sha(scanner_exact), 'function_AST_unmodified': True})

public['terminal'].update({
    'before.json': (terminal / 'before.json').read_bytes(), 'after.json': (terminal / 'after.json').read_bytes(),
    'run-driver.py': (terminal / 'driver.py').read_bytes(),
    'pip-before.raw.log': (terminal / 'pip-before.raw.log').read_bytes(),
    'pip-after.raw.log': (terminal / 'pip-after.raw.log').read_bytes(),
    'all-cases.STRUCTURAL.json': encode(current),
    'coverage-gate.py': coverage_script.read_bytes(),
    'coverage-gate.stdout.raw.log': coverage.stdout, 'coverage-gate.stderr.raw.log': coverage.stderr,
    'baseline-preservation.json': encode({'baselines': baseline_proof, 'baseline2598_subset': True, 'baseline3039_subset': True,
                                        'added_since2598': 449, 'added_since3039': 8}),
    'summary.STRUCTURAL.json': encode({
        **{k: report[k] for k in ('head', 'mode', 'exit', 'timed_out', 'seconds', 'sources', 'packages', 'sources_packages_python_exact', 'pip_before', 'pip_after')},
        **counts(current), 'known_windows_skip_exact': True, 'coverage_gate_exit': 0,
        'coverage_gate_source_matches_commit': True, 'result': 'REJECTED_FULL_SERIAL_DIAGNOSTIC',
        'causality': 'No retrospective cause is assigned to the setup error. Later focal logger/clock evidence is separate and does not make this run pass.',
        'original_xml_sha256': sha((terminal / 'results.xml').read_bytes()),
    }),
})

for key in ('logging', 'clock'):
    phases = ('before', 'after', 'integration', 'integration-lint') if key == 'logging' else ('before', 'after', 'integration')
    case_sets = {}
    phase_summaries = []
    stem = 'metodobase-bootstrap-log-' if key == 'logging' else 'metodobase-mfa31-fixture-clock-'
    for phase in phases:
        directory = T / (stem + phase + '-20261019')
        summary = read(directory / 'summary.json')
        cases = rows(directory / 'results.xml')
        observed = counts(cases)
        assert summary['source_environment_exact'] and summary['packages'] == 89
        assert summary['cases'] == observed['cases']
        assert (directory / 'before.json').read_bytes() == (directory / 'after.json').read_bytes()
        if phase == 'before':
            assert observed['cases'] == 2 and summary['exit'] == 1
            assert observed['failure' if key == 'logging' else 'error'] == 2
        else:
            assert summary['exit'] == 0 and observed['passed'] == observed['cases']
        case_sets[phase] = {c['case'] for c in cases}
        safe = {k: v for k, v in summary.items() if k not in ('failures', 'scope')}
        safe.update(observed)
        phase_summaries.append(safe)
        for name in ('before.json', 'after.json', 'driver.py', 'pip-before.raw.log', 'pip-after.raw.log'):
            public[key][phase + '/' + name] = (directory / name).read_bytes()
        public[key][phase + '/summary.STRUCTURAL.json'] = encode(safe)
        public[key][phase + '/cases.STRUCTURAL.json'] = encode(cases)
    assert case_sets['before'] == case_sets['after'] and case_sets['after'] <= case_sets['integration']
    assert len(case_sets['integration']) == (36 if key == 'logging' else 31)
    if key == 'logging':
        assert case_sets['integration'] == case_sets['integration-lint']
    source = T / (stem + 'source-20261019')
    for file in sorted(source.iterdir()):
        if file.is_file() and not file.name.endswith('private.raw.log'):
            public[key]['source/' + file.name] = file.read_bytes()
    source_commit = read(source / 'source-commit.json')
    for path in source_commit['paths']:
        blob = git_blob(source_commit['head'], path)
        public[key]['source/committed-' + path.replace('/', '__')] = blob
    if key == 'clock':
        review = T / 'metodobase-mfa31-fixture-clock-ci-preflight-20261019/review.json'
        public[key]['ci-preflight-review.json'] = review.read_bytes()
    public[key]['summary.STRUCTURAL.json'] = encode({
        'head': source_commit['head'], 'phases': phase_summaries,
        'before_after_case_ids_exact': True, 'integration_contains_causal_case_ids': True,
        'unique_integration_cases': len(case_sets['integration']),
        'repeated_phase_counts_are_not_unique_cases': True, 'independent_acceptance': False,
        'scope': 'Author focal evidence only. No retrospective attribution of the full serial setup error; no fresh test, database, browser or coverage execution during sealing.',
    })

# Validate every public candidate before private archive creation or public payload writes.
for key, files in public.items():
    for name, blob in files.items():
        scan(blob, name)

def acl(mode):
    run = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(HERE / 'archive-acl.ps1'), '-Mode', mode, '-PrivateRoot', str(PRIVATE)], capture_output=True, timeout=30)
    exclusive(HERE / ('acl-' + mode + '.stdout.raw.log'), run.stdout)
    exclusive(HERE / ('acl-' + mode + '.stderr.raw.log'), run.stderr)
    assert run.returncode == 0, 'Private archive ACL verification failed; raw logs retained in own Temp.'
    result = json.loads(run.stdout.decode('utf-8-sig'))
    assert result['allow_only'] == ['CURRENT_USER', 'SYSTEM'] and result['explicit_aces'] == 2
    return result

acl_create = acl('create')
acl_verify = acl('verify')
archive_proofs = {}
for key, filename in archives.items():
    destination = PRIVATE / filename
    before_stat = destination.stat()
    assert before_stat.st_size == 0 and not destination.is_symlink()
    # The placeholder was created with FileMode.CreateNew and verified private before any ZIP bytes.
    with destination.open('r+b') as stream:
        opened = os.fstat(stream.fileno())
        assert (opened.st_dev, opened.st_ino, opened.st_size) == (before_stat.st_dev, before_stat.st_ino, 0)
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, blob in sorted(original[key].items()):
                path = PurePosixPath(name)
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
                archive.writestr(name, blob)
    with zipfile.ZipFile(destination) as archive:
        assert len(archive.namelist()) == len(original[key]) and set(archive.namelist()) == set(original[key])
        for name, blob in original[key].items():
            assert archive.read(name) == blob
    archive_proofs[key] = {'path': str(destination), 'bytes': destination.stat().st_size, 'sha256': sha(destination.read_bytes()),
                           'members': original_meta[key], 'create_exclusive_empty_placeholder': True,
                           'DACL_verified_before_first_payload_write': True, 'ACL_create': acl_create, 'ACL_verify': acl_verify}
acl_final = acl('final')
pip_after = pip_check()
state_after = package_state()
assert state_before == state_after
for key, files in original.items():
    for name, blob in files.items():
        assert (T / name).read_bytes() == blob
for key in groups:
    public[key]['private-originals.json'] = encode({**archive_proofs[key], 'ACL_final': acl_final,
        'policy': 'Only current user and SYSTEM may access the private ZIP. Error payload and original XML remain private; directory data and binary database files were not archived.'})
    public[key]['seal-environment.json'] = encode({'before': state_before, 'after': state_after, 'exact': True,
        'pip_before_exit': 0, 'pip_after_exit': 0, 'closed_original_files_byte_exact': True,
        'no_tests_or_database_connections_during_seal': True})
    public[key]['seal-pip-before.stdout.raw.log'] = pip_before.stdout
    public[key]['seal-pip-before.stderr.raw.log'] = pip_before.stderr
    public[key]['seal-pip-after.stdout.raw.log'] = pip_after.stdout
    public[key]['seal-pip-after.stderr.raw.log'] = pip_after.stderr
    public[key]['review.md'] = (
        '# Checkpoint125 evidence seal\n\n'
        'Original bytes remain intact. Private archives were created as exclusive empty files, assigned protected DACLs for the current user and SYSTEM, and verified before payload writes. Public files passed the unmodified checkpoint119 scanner.\n\n'
        'The full serial run remains rejected: 3047 cases, 3045 passed, one setup error, one known skip. Later focal author replays do not establish the cause of that historical error or turn it into an accepted run. Repeated integration phases are not counted as additional unique criteria.\n\n'
        'No tests, browser, database or provider were run while sealing. The closed coverage JSON was checked by the actual coverage gate only. RAW proof files use * -text; this prefix has not been staged or committed by the sealing agent.\n'
    ).encode()
    manifest = {'.gitattributes': {'bytes': 8, 'sha256': sha(b'* -text\n')},
                **{name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in public[key].items()}}
    public[key]['manifest.json'] = encode({'files': manifest, 'checkpoint119_scan': 'PASS', 'RAW_readback': True})
    for name, blob in public[key].items():
        scan(blob, name)
    out = E / prefixes[key]
    out.mkdir()
    exclusive(out / '.gitattributes', b'* -text\n')
    for name, blob in public[key].items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        exclusive(path, blob)
    for path in out.rglob('*'):
        if path.is_file():
            scan(path.read_bytes(), path.relative_to(out).as_posix())
    assert len([p for p in out.rglob('*') if p.is_file()]) == len(public[key]) + 1
result = {key: {'path': str(E / prefixes[key]), 'public_files': len(public[key]) + 1,
                'manifest_sha256': sha((E / prefixes[key] / 'manifest.json').read_bytes()),
                'private_archive_sha256': archive_proofs[key]['sha256'], 'private_original_files': len(original[key])} for key in groups}
exclusive(HERE / 'result.json', encode(result))
print(json.dumps(result))
