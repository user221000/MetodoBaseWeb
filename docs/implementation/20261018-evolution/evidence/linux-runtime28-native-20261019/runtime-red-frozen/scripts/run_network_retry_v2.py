from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, io, json, shlex, subprocess, tarfile

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = LAB / 'evidence/runtime28-native-20261019'
OUT = BASE / 'network-retry-v2'
OUT.mkdir(exist_ok=False)
initial = BASE / 'network-executed/owned-state.json'
config = {'initial_state_sha256': hashlib.sha256(initial.read_bytes()).hexdigest(),
          'canary_sha256': hashlib.sha256((BASE / 'scripts/network_canary.py').read_bytes()).hexdigest()}
code = (BASE / 'scripts/retry_guest_network_v2.py').read_bytes()
compile(code, 'retry-guest-network-v2', 'exec')
items = {'retry_guest_network_v2.py': code, 'retry-v2-inputs.json': (json.dumps(config, indent=2) + '\n').encode()}
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode='w') as archive:
    for name, data in items.items():
        member = tarfile.TarInfo(name);member.size=len(data);member.mode=0o600
        archive.addfile(member, io.BytesIO(data))
payload = buffer.getvalue();sha = hashlib.sha256(payload).hexdigest()
source = OUT / 'retry-inputs.tar';source.write_bytes(payload)
spec = importlib.util.spec_from_file_location('access', LAB / 'scripts/guest_access.py')
access = importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
prepare = r'''from pathlib import Path
import hashlib,io,sys,tarfile
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==SHA
root=Path('/home/lab/metodobase-runtime28-network-20261019')
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
 assert {m.name for m in archive.getmembers()}=={'retry_guest_network_v2.py','retry-v2-inputs.json'}
 assert all(m.isfile() and not (root/m.name).exists() for m in archive.getmembers())
 archive.extractall(root,filter='data')
'''.replace('SHA', repr(sha))
with source.open('rb') as stdin:
    transfer = access.run('/opt/metodobase-lab/python/bin/python3.12 -c ' + shlex.quote(prepare), stdin=stdin, timeout=60)
(OUT / 'transfer.log').write_bytes(transfer.stdout + transfer.stderr)
assert transfer.returncode == 0
with (OUT / 'run.log').open('xb') as stdout, (OUT / 'run.stderr.log').open('xb') as stderr:
    result = access.run('sudo -n /opt/metodobase-lab/python/bin/python3.12 /home/lab/metodobase-runtime28-network-20261019/retry_guest_network_v2.py',
                        stdout=stdout, stderr=stderr, timeout=420)
names = ['state.json', 'namespace-routes.json', 'canary.json', 'canary.log', 'counters-and-output-probes.json',
         'iptables.before.txt', 'ip6tables.before.txt', 'iptables.after.txt', 'ip6tables.after.txt']
for name in names:
    response = access.run('sudo -n cat ' + shlex.quote('/home/lab/metodobase-runtime28-network-20261019/retry-v2/' + name), timeout=30)
    if response.returncode == 0:
        (OUT / name).write_bytes(response.stdout)
    elif result.returncode == 0:
        raise AssertionError('Missing gate evidence ' + name)
summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'exit': result.returncode,
           'inputs': config, 'input_archive_sha256': sha,
           'guest_controller_sha256': hashlib.sha256(code).hexdigest(),
           'scope': 'Owned namespace route removal before stdin and full credential-free OS network canary. Original contract and initial red run preserved.'}
if result.returncode == 0:
    actual = json.loads((OUT / 'state.json').read_text())
    assert actual['gate_passed'] and actual['container_removed']
    summary.update(gate_passed=True, product_started=False, secret_consumption=False,
                   namespace_identity_and_routes_recorded=True, restrictive_gates_and_registered_proxies_active=True)
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
raise SystemExit(result.returncode)
