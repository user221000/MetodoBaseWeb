from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, io, json, os, shlex, subprocess, tarfile, time

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = LAB / 'evidence/runtime28-native-20261019'
OUT = BASE / 'network-executed'
OUT.mkdir(exist_ok=False)
REVIEWED = Path(r'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\linux-runtime28-native-20261019\network-prepared')
PINS = {'network-contract.json': '9d0122561e9e506b23dfa2d090beadc2a498c50eba60d5a3e9c3795c6b3ea85d',
        'firewall-rules.proposed.json': '74c12487861887e9d0daff862af1a5efd314ce0bb3bf07b63323e84d077b279d',
        'scripts/bounded_tcp_proxy.py': '37337f6387f1fb5ce38204bcaa992f63df7c764725696708046d330d96fb557f'}
members = {}
for rel, sha in PINS.items():
    data = (REVIEWED / rel).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha
    assert (BASE / rel).read_bytes() == data
    members[Path(rel).name] = data
for name in ['apply_guest_network.py', 'network_canary.py']:
    data = (BASE / 'scripts' / name).read_bytes();compile(data, name, 'exec')
    members[name] = data
files = {name: hashlib.sha256(data).hexdigest() for name, data in members.items()}
members['inputs.json'] = (json.dumps({'files': files, 'reviewed_artifacts_sha256': PINS}, indent=2) + '\n').encode()
archive = io.BytesIO()
with tarfile.open(fileobj=archive, mode='w', format=tarfile.PAX_FORMAT) as output:
    for name, data in sorted(members.items()):
        item = tarfile.TarInfo(name);item.size=len(data);item.mode=0o600;item.mtime=0
        output.addfile(item, io.BytesIO(data))
payload = archive.getvalue();payload_sha = hashlib.sha256(payload).hexdigest()
payload_file = OUT / 'network-inputs.tar'
payload_file.write_bytes(payload)
spec = importlib.util.spec_from_file_location('access', LAB / 'scripts/guest_access.py')
assert hashlib.sha256((LAB / 'scripts/guest_access.py').read_bytes()).hexdigest() == '616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7'
access = importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
remote = r'''import hashlib,io,pathlib,sys,tarfile
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==EXPECTED
root=pathlib.Path('/home/lab/metodobase-runtime28-network-20261019');assert not root.exists()
with tarfile.open(fileobj=io.BytesIO(data)) as source:
 names=[]
 for m in source.getmembers():
  names.append(m.name);assert m.isfile() and pathlib.PurePosixPath(m.name).name==m.name and ':' not in m.name and '\\' not in m.name
 assert len(names)==len(set(names))==len({p.casefold() for p in names})==6
 root.mkdir(mode=0o700)
 source.extractall(root,filter='data')
print('OWNED_NETWORK_INPUTS_VERIFIED')
'''.replace('EXPECTED', repr(payload_sha))
with payload_file.open('rb') as stream:
    prepared = access.run('/opt/metodobase-lab/python/bin/python3.12 -c ' + shlex.quote(remote), stdin=stream, timeout=90)
(OUT / 'transfer.log').write_bytes(prepared.stdout + prepared.stderr)
assert prepared.returncode == 0
command, environment = access.configuration()
command = command[:-1] + ['-N', '-T', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=15',
                         '-o', 'ServerAliveCountMax=3', '-R', '127.0.0.1:55483:127.0.0.1:55483', command[-1]]
ssh = Path(command[0])
ssh_sha = hashlib.sha256(ssh.read_bytes()).hexdigest()
with (OUT / 'ssh-forward.stdout.log').open('xb') as stdout, (OUT / 'ssh-forward.stderr.log').open('xb') as stderr:
    process = subprocess.Popen(command, cwd=LAB / 'instance', env=environment, stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
state = {'started_utc': datetime.now(timezone.utc).isoformat(), 'ssh_forward_pid': process.pid,
         'ssh_executable': str(ssh), 'ssh_executable_sha256': ssh_sha,
         'guest_bind': '127.0.0.1:55483', 'fixed_windows_destination': '127.0.0.1:55483',
         'ssh_endpoint': '127.0.0.1:53105', 'strict_host_key_checking': True, 'dynamic_forwarding': False,
         'input_archive_sha256': payload_sha, 'source_and_reviewed_inputs': files,
         'scope': 'Credential-free network gate. Owned forwarding process remains registered for later exact teardown.'}
(OUT / 'host-state.json').write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
time.sleep(2)
assert process.poll() is None, 'Owned SSH reverse forward failed; inspect private stderr'
print(json.dumps({'stage': 'fixed-reverse-forward-started', 'pid': process.pid}), flush=True)
with (OUT / 'apply.log').open('xb') as stdout, (OUT / 'apply.stderr.log').open('xb') as stderr:
    result = access.run('sudo -n /opt/metodobase-lab/python/bin/python3.12 /home/lab/metodobase-runtime28-network-20261019/apply_guest_network.py',
                        stdout=stdout, stderr=stderr, timeout=420)
# Explicit allowlist exports evidence only, never a broad folder or future private inputs.
names = ['owned-state.json', 'preflight.json', 'network.json', 'listeners.json', 'input-counters.json',
         'guest-output-probes.json', 'iptables.before.txt', 'ip6tables.before.txt',
         'iptables.after.txt', 'ip6tables.after.txt', 'canary.json', 'canary.log', 'pg-proxy.log', 'redis-proxy.log']
for name in names:
    fetch = access.run('sudo -n cat ' + shlex.quote('/home/lab/metodobase-runtime28-network-20261019/' + name), timeout=30)
    if fetch.returncode == 0:
        (OUT / name).write_bytes(fetch.stdout)
    elif result.returncode == 0:
        raise AssertionError('Missing required network evidence ' + name)
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'exit': result.returncode,
           'host_forward_pid': process.pid, 'host_forward_running': process.poll() is None,
           'reviewed_contract_sha256': PINS['network-contract.json'],
           'product_started': False, 'secret_consumption': False,
           'scope': 'Actual guest OS/Docker network gate without credentials. Restrictive rules and owned proxies remain for root-reviewed runtime.'}
if result.returncode == 0:
    summary['guest_state'] = json.loads((OUT / 'owned-state.json').read_text())
    assert summary['guest_state']['gate_passed'] is True
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
raise SystemExit(result.returncode)
