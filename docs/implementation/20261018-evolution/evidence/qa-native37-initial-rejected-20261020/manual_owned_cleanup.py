"""Explicit ROOT-authorized recovery of exact owned native37 process generation."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

TASK = Path(__file__).resolve().parents[1]
P = TASK / 'private'
ROOT = Path('F:/mb-qa-native37-20261020')
PROFILE = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
EXPECTED = {27404: 134369530643760054, 27324: 134369530643879639}
sha = lambda data: hashlib.sha256(data).hexdigest()
def put(name, value):
    with (P / name).open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode())

assert sha(PROFILE.read_bytes()) == '1526482e15f5e31a4248868e77a609af536f6dfbbf2b04959e7b14d521519f02'
lease_paths = list((TASK / 'leases').glob('lease-*.json'))
assert len(lease_paths) == 1
lease_raw = lease_paths[0].read_bytes()
lease = json.loads(lease_raw)
assert lease['state'] == 'created' and lease['launcher_pid'] == 27324
assert lease['launcher_birth'] == EXPECTED[27324]
assert lease['launcher_birth_after_create'] == EXPECTED[27324]
assert lease['server_port'] == 55483
startup = json.loads((P / 'startup.json').read_bytes())
assert startup['pid'] == 27324 and startup['process_birth'] == EXPECTED[27324]
assert (P / 'server-stop-timeout.json').is_file() and (P / 'stop').is_file()

api = ctypes.WinDLL('kernel32', use_last_error=True)
api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
api.OpenProcess.restype = wintypes.HANDLE
api.CloseHandle.argtypes = [wintypes.HANDLE]
api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
api.GetProcessTimes.restype = wintypes.BOOL
api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
api.GetExitCodeProcess.restype = wintypes.BOOL
api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
api.WaitForSingleObject.restype = wintypes.DWORD
api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
api.QueryFullProcessImageNameW.restype = wintypes.BOOL
api.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
api.TerminateProcess.restype = wintypes.BOOL

def observe_handle(pid, handle):
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    assert api.GetProcessTimes(handle, *[ctypes.byref(x) for x in (created, exited, kernel, user)])
    birth = (created.dwHighDateTime << 32) | created.dwLowDateTime
    assert birth == EXPECTED[pid], 'PID generation mismatch; no cleanup permitted'
    buffer = ctypes.create_unicode_buffer(32768)
    length = wintypes.DWORD(len(buffer))
    assert api.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length))
    expected_image = Path(sys.executable if pid == 27404 else sys._base_executable).resolve()
    assert Path(buffer.value).resolve() == expected_image
    code = wintypes.DWORD()
    assert api.GetExitCodeProcess(handle, ctypes.byref(code))
    return {'pid': pid, 'birth': birth, 'image': buffer.value, 'exit_code': code.value,
            'wait_zero': api.WaitForSingleObject(handle, 0)}

script = "$r=@(Get-CimInstance Win32_Process -Filter \"ProcessId=27404 OR ProcessId=27324\" | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $r -Depth 4 -Compress"
cim_raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', script])
with (P / 'manual-cleanup-cim-before.raw').open('xb') as stream: stream.write(cim_raw)
cim = json.loads(cim_raw.decode('utf-8-sig'))
cim = {row['ProcessId']: row for row in cim}
handles = {}
observations = []
try:
    for pid in (27404, 27324):
        handle = api.OpenProcess(0x1000 | 0x100000 | 0x0001, False, pid)
        if not handle:
            assert ctypes.get_last_error() in (87, 1168)
            observations.append({'pid': pid, 'birth': EXPECTED[pid], 'state': 'absent_before_recovery'})
            continue
        handles[pid] = handle
        row = observe_handle(pid, handle)
        if row['wait_zero'] == 258:
            command = cim[pid]['CommandLine'].replace('\\', '/').lower()
            assert 'tests/e2e/native37_postgres_server_qa.py' in command
            assert str(P).replace('\\', '/').lower() in command
            assert str(PROFILE).replace('\\', '/').lower() in command
            assert '--port' in command and '8802' in command
            if pid == 27324:
                assert cim[pid]['ParentProcessId'] == 27404
                assert EXPECTED[pid] >= EXPECTED[27404]
        observations.append(row)
    put('manual-cleanup-authorized-plan.json', {'utc': datetime.now(UTC).isoformat(),
        'authorization': 'ROOT exact handle/executable/arguments/birth and parent-generation verified; only own server',
        'original_lease_sha256': sha(lease_raw), 'original_lease_state': lease['state'],
        'observations': observations, 'normal_server_exit': False, 'timeout_before_manual_action': True})

    actions = []
    worker = handles.get(27324)
    if worker and api.WaitForSingleObject(worker, 0) == 258:
        row = observe_handle(27324, worker)
        assert row['exit_code'] == 259
        assert api.TerminateProcess(worker, 125)
        assert api.WaitForSingleObject(worker, 10000) == 0
        actions.append({'pid': 27324, 'birth': EXPECTED[27324], 'action': 'TerminateProcess exact verified handle', 'exit_code_requested': 125})
    parent = handles.get(27404)
    if parent:
        wait = api.WaitForSingleObject(parent, 10000)
        if wait == 258:
            row = observe_handle(27404, parent)
            assert row['exit_code'] == 259
            assert api.TerminateProcess(parent, 125)
            assert api.WaitForSingleObject(parent, 10000) == 0
            actions.append({'pid': 27404, 'birth': EXPECTED[27404], 'action': 'TerminateProcess exact verified redirector handle after child wait', 'exit_code_requested': 125})
        else:
            assert wait == 0
            actions.append({'pid': 27404, 'birth': EXPECTED[27404], 'action': 'redirector exited after own worker termination'})
    after = [observe_handle(pid, handle) for pid, handle in handles.items()]
    assert all(row['wait_zero'] == 0 for row in after)
    put('manual-server-process-closure.json', {'actions': actions, 'after': after,
        'normal_server_exit': False, 'classification': 'manual authorized recovery after server TimeoutExpired'})
finally:
    for handle in handles.values(): api.CloseHandle(handle)

import psycopg2
from psycopg2 import sql
config = json.loads(PROFILE.read_bytes())
source = config.get('METODOBASE_TEST_MIGRATOR_URL', config.get('migrator_url'))
parsed = urlsplit(source)
assert parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port == 55483
url = source.replace('postgresql+psycopg2://', 'postgresql://', 1)
control = psycopg2.connect(url)
control.autocommit = True
session_counts = []
try:
    with control.cursor() as cursor:
        cursor.execute('SELECT current_user,pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')
        owner, postmaster, host, port = cursor.fetchone()
        assert owner == lease['expected_owner'] and postmaster.isoformat() == lease['postmaster_start']
        assert host in ('127.0.0.1', '127.0.0.1/32') and port == 55483
        cursor.execute('SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', (lease['database'],))
        assert cursor.fetchone() == (lease['oid'], lease['expected_owner'])
        deadline = time.monotonic() + 20
        while True:
            cursor.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s', (lease['database'],))
            count = cursor.fetchone()[0]
            session_counts.append(count)
            if count == 0: break
            assert time.monotonic() < deadline, 'Own sessions retained; no cancellation or DROP permitted'
            time.sleep(.25)
        put('manual-drop-planned.json', {'database': lease['database'], 'oid': lease['oid'],
            'owner': lease['expected_owner'], 'original_lease_sha256': sha(lease_raw),
            'sessions_before_normal_DROP': 0, 'session_count_observations': session_counts,
            'no_FORCEDROP_no_backend_cancellation': True})
        cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(lease['database'])))
finally: control.close()

with psycopg2.connect(url) as fresh, fresh.cursor() as cursor:
    cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s', (lease['database'],))
    databases = cursor.fetchone()[0]
    cursor.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=%s', (lease['database'],))
    sessions = cursor.fetchone()[0]
    assert databases == sessions == 0
assert lease_paths[0].read_bytes() == lease_raw, 'Original created lease retained unchanged'
put('manual-owned-close.json', {'utc': datetime.now(UTC).isoformat(), 'database': lease['database'],
    'oid': lease['oid'], 'expected_owner': lease['expected_owner'], 'original_lease_sha256': sha(lease_raw),
    'original_created_lease_preserved': True, 'manual_server_termination_after_timeout': True,
    'normal_server_exit': False, 'ordinary_DROP_after_zero_sessions': True,
    'fresh_connection_database_absence': databases == 0, 'fresh_connection_sessions': sessions,
    'no_FORCEDROP_no_foreign_cancel_no_global_changes': True})
print(json.dumps({'manual_owned_server_closed': True, 'normal_server_exit': False,
    'ordinary_DROP_after_zero_sessions': True, 'fresh_database_absence': databases == 0, 'fresh_sessions': sessions}))
