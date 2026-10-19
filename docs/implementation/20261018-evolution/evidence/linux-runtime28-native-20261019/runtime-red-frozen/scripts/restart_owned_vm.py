from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, subprocess, time

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
SEALED = Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\linux-tcg-20261019')
OUT = LAB / 'evidence/runtime28-native-20261019/restart'
OUT.mkdir(exist_ok=False)

def info(p, algorithm='sha256'):
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, algorithm).hexdigest()
    return {'bytes': p.stat().st_size, algorithm: digest}

manifest_file = SEALED / 'linux-tcg-evidence-manifest.json'
assert info(manifest_file)['sha256'] == '00484dfdc605f08f37e9616902204edab2f769cf4ec68c0d9a9356e1fbe52e00'
records = {r['file']: r for r in json.loads(manifest_file.read_text())['files']}
for rel in ['scripts/lab_control.py', 'scripts/guest_access.py', 'linux-tcg-qemu-verified.json', 'linux-tcg-boot-start.json']:
    expected = records[rel]
    assert info(SEALED / rel) == {k: expected[k] for k in ['bytes', 'sha256']}
for name in ['lab_control.py', 'guest_access.py']:
    assert (LAB / 'scripts' / name).read_bytes() == (SEALED / 'scripts' / name).read_bytes()
verified = json.loads((SEALED / 'linux-tcg-qemu-verified.json').read_text())
tools = LAB / 'tools/qemu'
for rel, expected in verified['files'].items():
    p = tools / rel
    assert p.resolve().is_relative_to(tools.resolve())
    for a in (p, *p.parents):
        assert not a.is_symlink() and not (getattr(a.lstat(), 'st_file_attributes', 0) & 0x400)
    assert info(p) == expected, rel
state = json.loads((LAB / 'instance/state.json').read_text())
initial = json.loads((SEALED / 'linux-tcg-boot-start.json').read_text())
assert state['command'] == initial['command']
for key in ['source_image', 'source_sha512', 'overlay', 'seed_iso', 'seed_iso_sha256', 'ports', 'resources']:
    assert state[key] == initial[key], key
assert info(Path(state['seed_iso']))['sha256'] == initial['seed_iso_sha256']
assert info(Path(state['source_image']), 'sha512')['sha512'] == initial['source_sha512']

def module(name):
    spec = importlib.util.spec_from_file_location(name, LAB / 'scripts' / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

control = module('lab_control')
assert control.process_identity(state) is None
before = {'captured_utc': datetime.now(timezone.utc).isoformat(),
          'prior_manifest_sha256': info(manifest_file)['sha256'],
          'portable_files_verified': len(verified['files']),
          'controller': info(LAB / 'scripts/lab_control.py'),
          'guest_access': info(LAB / 'scripts/guest_access.py'),
          'seed_iso_sha256': initial['seed_iso_sha256'], 'source_sha512': initial['source_sha512'],
          'previous_pid_absent': state['pid'], 'command_matches_sealed_initial_boot': True,
          'resources': state['resources'], 'ports': state['ports']}
(OUT / 'before.json').write_text(json.dumps(before, indent=2) + '\n', encoding='utf-8')
started = control.start(state)
(OUT / 'start.json').write_text(json.dumps(started, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'stage': 'qemu-started', **started}), flush=True)
access = module('guest_access')
deadline = time.monotonic() + 240
attempts = []
while time.monotonic() < deadline:
    try:
        result = access.run("uname -a && test \"$(id -un)\" = lab && printf '\\nOWNED_SSH_READY\\n'", timeout=12)
        attempts.append({'exit': result.returncode, 'stdout_bytes': len(result.stdout), 'stderr_bytes': len(result.stderr)})
        if result.returncode == 0 and b'OWNED_SSH_READY' in result.stdout:
            (OUT / 'ssh-ready.log').write_bytes(result.stdout + result.stderr)
            break
    except subprocess.TimeoutExpired:
        attempts.append({'timeout': True})
    print(json.dumps({'stage': 'waiting-owned-ssh', 'attempt': len(attempts)}), flush=True)
    time.sleep(2)
else:
    raise RuntimeError('Owned SSH did not become healthy; no automatic stop of any other process')
qmp = control.qmp(control.state(), ['query-status', 'query-memory-size-summary'])
assert qmp['query-status']['return']['status'] == 'running'
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(),
           'qemu_pid': started['pid'], 'qmp': qmp, 'ssh_attempts': attempts,
           'owned_strict_ssh_ready': True, 'resources': state['resources'],
           'scope': 'Owned software TCG guest restarted from preserved overlay. No application or provider traffic.'}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'qemu_pid': started['pid'], 'owned_strict_ssh_ready': True}), flush=True)
