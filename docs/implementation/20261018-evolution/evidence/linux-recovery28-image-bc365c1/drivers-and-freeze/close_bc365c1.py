from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, shlex, subprocess

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
REPO = Path(r'F:\MetodoBaseWeb-image-security-20261019')
BUILD = LAB / 'evidence/recovery28-image-bc365c1'
OUT = LAB / 'evidence/closure-bc365c1'
HEAD = 'bc365c13b9af9e24129a56b4068059a67bb3afa0'
IMAGE = 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c'
OUT.mkdir(exist_ok=False)

def info(p):
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': p.stat().st_size, 'sha256': digest}

env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
           GIT_ATTR_NOSYSTEM='1', GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
gitcmd = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
          '-c', 'core.hooksPath=' + os.devnull, '-c', 'core.attributesFile=' + os.devnull,
          '-c', 'core.excludesFile=' + os.devnull, '-C', str(REPO)]
def git(*args):
    return subprocess.check_output(gitcmd + list(args), env=env)

assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('status', '--porcelain=v1', '--untracked-files=all') == b''
files = {}
for rel in git('ls-files', '-z').decode().rstrip('\0').split('\0'):
    p = REPO / rel
    assert p.is_file() and not p.is_symlink() and not (getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)
    files[rel] = info(p)
gitdir = Path(git('rev-parse', '--absolute-git-dir').decode().strip())
common = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
controls = [gitdir / 'index', common / 'config', gitdir / 'config.worktree',
            Path.home() / '.gitconfig', Path.home() / '.config/git/config']
snapshot = {'tracked_sources': files,
            'git_controls': {str(p): info(p) if p.is_file() else None for p in controls}}
assert snapshot == json.loads((BUILD / 'before.json').read_text())
(OUT / 'source-after-os.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
build = json.loads((BUILD / 'build-summary.json').read_text())
assert info(BUILD / 'build-context.tar') == build['archive']

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

access = load_module('owned_guest_access', LAB / 'scripts/guest_access.py')
remote = r'''import json, pathlib, subprocess
expected = [9242, 9250, 10244, 10272, 10273]
processes = {}
for pid in expected:
    p = pathlib.Path('/proc') / str(pid)
    processes[str(pid)] = {'present': p.exists()}
    if p.exists():
        processes[str(pid)]['cmdline'] = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
assert not any(p['present'] for p in processes.values()), processes
containers = subprocess.check_output(['sudo', '-n', 'docker', 'ps', '-a', '--no-trunc', '--format', '{{json .}}'], text=True)
running = subprocess.check_output(['sudo', '-n', 'docker', 'ps', '-q'], text=True)
assert not running.strip(), 'Unexpected running container; stop nothing automatically'
image = json.loads(subprocess.check_output(['sudo', '-n', 'docker', 'image', 'inspect', 'metodobase-lab:recovery28-bc365c1']))[0]
assert image['Id'] == 'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c'
print(json.dumps({'uname': subprocess.check_output(['uname', '-a'], text=True).strip(),
 'targeted_completed_processes': processes, 'docker_ps_all': containers.splitlines(),
 'running_container_count': 0, 'image_id': image['Id'],
 'image_revision_label': image['Config']['Labels']['org.opencontainers.image.revision'],
 'disk': subprocess.check_output(['df', '-B1', '/'], text=True),
 'memory': subprocess.check_output(['free', '-b'], text=True),
 'scope': 'Read-only lifecycle inventory. No app command or VM shutdown.'}, indent=2))
'''
result = access.run('/opt/metodobase-lab/python/bin/python3.12 -c ' + shlex.quote(remote), timeout=90)
(OUT / 'guest-lifecycle.log').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0, result.stderr.decode(errors='replace')
guest = json.loads(result.stdout)
assert guest['image_revision_label'] == HEAD
(OUT / 'guest-lifecycle.json').write_text(json.dumps(guest, indent=2) + '\n', encoding='utf-8')

control = load_module('owned_lab_control', LAB / 'scripts/lab_control.py')
state = control.state()
assert state['pid'] == 29456
qmp = control.qmp(state, ['query-status', 'query-memory-size-summary'])
assert qmp['query-status']['return']['status'] == 'running'
ps = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
    'Get-NetTCPConnection -OwningProcess 29456 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress'],
    capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
assert ps.returncode == 0, ps.stderr.decode(errors='replace')
listeners = json.loads(ps.stdout)
assert isinstance(listeners, list) and len(listeners) == 2
assert {(p['LocalAddress'], p['LocalPort']) for p in listeners} == {('127.0.0.1', 53105), ('127.0.0.1', 53106)}
host = {'qemu_pid': 29456, 'qmp': qmp, 'listeners': listeners,
        'action': 'read-only status; VM left running for root-coordinated shutdown',
        'resources': state['resources']}
(OUT / 'host-lifecycle.json').write_text(json.dumps(host, indent=2) + '\n', encoding='utf-8')
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(),
           'source_head': HEAD, 'tracked_files': len(files), 'source_and_git_controls_stable': True,
           'source_snapshot_sha256': info(OUT / 'source-after-os.json')['sha256'],
           'archive_stable': True, 'archive': build['archive'], 'image_id': IMAGE,
           'targeted_build_and_scan_processes_closed': True, 'running_container_count': 0,
           'vm_pid': 29456, 'vm_running': True, 'owned_loopback_listeners_only': True,
           'vm_shutdown_performed': False,
           'scope': 'Closes this image build/audit lifecycle. Application, PostgreSQL/Redis integration and deployment acceptance remain pending.'}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
