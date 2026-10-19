"""Cooperatively stop the attributed idle lab VM while retaining its owned disk."""
from pathlib import Path
import hashlib
import json
import socket
import subprocess
import sys
import time

lab = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
proof = lab / 'evidence/qa-runtime31-c538-acl-independent-public-20261019'
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-vm-memory-handoff-20261019')
assert not out.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest_raw = (proof / 'manifest.json').read_bytes()
assert sha(manifest_raw) == 'c52e2b217dc0bb2736f57df2439bb1eeda47905d971033207970199072d793c2'
handoff_raw = (proof / 'vm-lease-handoff.json').read_bytes()
metadata = json.loads(manifest_raw)['vm-lease-handoff.json']
assert sha(handoff_raw) == metadata['sha256'] and len(handoff_raw) == metadata['bytes']
handoff = json.loads(handoff_raw)
assert handoff['pid'] == 29768 and handoff['lease_returned_to'] == 'ROOT'
assert handoff['guest']['running_containers'] == [] and handoff['pg55486_port_free']

def powershell(command):
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
        capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0
    return json.loads(result.stdout) if result.stdout.strip() else None

def process():
    return powershell('Get-CimInstance Win32_Process -Filter "ProcessId=29768" | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine,ParentProcessId | ConvertTo-Json -Compress')

def available():
    return int(powershell('(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory | ConvertTo-Json')) * 1024

before = process()
assert before['CreationDate'] == handoff['birth']
assert before['ParentProcessId'] == handoff['parent']
assert Path(before['ExecutablePath']).resolve() == Path(handoff['exe']).resolve()
assert sha(Path(before['ExecutablePath']).read_bytes()) == handoff['exe_sha256']
assert sha(before['CommandLine'].encode('utf-8')) == handoff['argv_sha256']
parent = powershell('Get-CimInstance Win32_Process -Filter "ProcessId=' + str(handoff['parent']) + '" | Select-Object ProcessId,CreationDate,ExecutablePath | ConvertTo-Json -Compress')
state = json.loads((lab / 'instance/state.json').read_bytes())
assert state['pid'] == handoff['pid'] and state['ports'] == handoff['ports']
assert state['resources'] == handoff['resources']
for key in ['overlay', 'source_image', 'seed_iso']:
    path = Path(state[key]).resolve()
    assert path.is_relative_to(lab.resolve()) and path.is_file() and not path.is_symlink()
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
(out / 'before.private.json').write_bytes((json.dumps({'process': before, 'observed_parent': parent,
    'parent_generation_not_used_as_authority': True, 'free_memory_bytes': available(),
    'authenticated_handoff_sha256': sha(handoff_raw)}, indent=2) + '\n').encode())
control = lab / 'scripts/lab_control.py'
control_sha = sha(control.read_bytes())
result = subprocess.run([sys.executable, '-B', str(control), 'shutdown'], cwd=lab, capture_output=True, timeout=30)
(out / 'shutdown.stdout.raw.log').write_bytes(result.stdout)
(out / 'shutdown.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode == 0
deadline = time.monotonic() + 40
after = process()
while after is not None and time.monotonic() < deadline:
    assert after['CreationDate'] == handoff['birth'] and sha(after['CommandLine'].encode()) == handoff['argv_sha256']
    time.sleep(1)
    after = process()
ports_free = {}
for name, port in handoff['ports'].items():
    with socket.socket() as connection:
        connection.settimeout(1)
        ports_free[name] = connection.connect_ex(('127.0.0.1', port)) != 0
receipt = {'owned_pid': 29768, 'birth': handoff['birth'], 'process_exited': after is None,
    'ports_closed': ports_free, 'method': 'Existing owned controller QMP system_powerdown only; no terminate/kill/Windows shutdown.',
    'control_sha256': control_sha, 'control_unchanged': control_sha == sha(control.read_bytes()),
    'retained_files': {key: str(Path(state[key]).resolve()) for key in ['overlay', 'source_image', 'seed_iso']},
    'retained_files_exist': all(Path(state[key]).is_file() for key in ['overlay', 'source_image', 'seed_iso']),
    'free_memory_after_bytes': available(), 'disk_byte_identity_claim': False,
    'purpose': 'Temporary RAM handoff to one current32 Chrome; restart the same retained overlay/controller later.'}
(out / 'receipt.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
print(json.dumps(receipt))
assert after is None and all(ports_free.values()) and receipt['retained_files_exist'] and receipt['control_unchanged']
