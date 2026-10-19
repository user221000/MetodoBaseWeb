from pathlib import Path
from datetime import datetime, timezone
from ctypes import wintypes
import ctypes, hashlib, importlib.util, json, re, subprocess, time

LAB = Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE = LAB / 'evidence/runtime28-native-20261019'
OUT = BASE / 'network-target55484'
OUT.mkdir(exist_ok=False)
old = json.loads((BASE / 'network-executed/host-state.json').read_text())
assert old['ssh_forward_pid'] == 28200 and old['fixed_windows_destination'] == '127.0.0.1:55483'
def cim(pid):
    command = 'Get-CimInstance Win32_Process -Filter "ProcessId=' + str(pid) + '" | Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress'
    return json.loads(subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',command], creationflags=subprocess.CREATE_NO_WINDOW))
identity = cim(28200)
assert Path(identity['ExecutablePath']).resolve() == Path(old['ssh_executable']).resolve()
assert '127.0.0.1:55483:127.0.0.1:55483' in identity['CommandLine']
assert hashlib.sha256(Path(identity['ExecutablePath']).read_bytes()).hexdigest() == old['ssh_executable_sha256']
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
k.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
k.CloseHandle.argtypes=[wintypes.HANDLE]
handle=k.OpenProcess(0x1000|0x0001|0x00100000,False,28200)
assert handle
try:
    buffer=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(buffer))
    assert k.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length))
    assert Path(buffer.value).resolve()==Path(identity['ExecutablePath']).resolve()
    times=[wintypes.FILETIME() for _ in range(4)]
    assert k.GetProcessTimes(handle,*[ctypes.byref(t) for t in times])
    birth=((times[0].dwHighDateTime<<32)+times[0].dwLowDateTime)//10000-11644473600000
    expected=int(re.search(r'/Date\((\d+)\)/',identity['CreationDate']).group(1))
    assert abs(birth-expected)<=1
    assert k.TerminateProcess(handle,0)
    assert k.WaitForSingleObject(handle,10000)==0
finally:
    k.CloseHandle(handle)
spec=importlib.util.spec_from_file_location('access',LAB/'scripts/guest_access.py')
access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
deadline=time.monotonic()+15
while time.monotonic()<deadline:
    test=access.run('ss -H -lnt "sport = :55483"',timeout=10)
    assert test.returncode==0
    if not test.stdout.strip():break
    time.sleep(.5)
else:raise AssertionError('Old owned reverse-forward listener did not close')
command,environment=access.configuration()
command=command[:-1]+['-N','-T','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3',
                     '-R','127.0.0.1:55483:127.0.0.1:55484',command[-1]]
with (OUT/'ssh.stdout.log').open('xb') as stdout,(OUT/'ssh.stderr.log').open('xb') as stderr:
    process=subprocess.Popen(command,cwd=LAB/'instance',env=environment,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                             creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
time.sleep(1)
assert process.poll() is None
current=cim(process.pid)
assert '127.0.0.1:55483:127.0.0.1:55484' in current['CommandLine']
assert Path(current['ExecutablePath']).resolve()==Path(old['ssh_executable']).resolve()
record={'finished_utc':datetime.now(timezone.utc).isoformat(),'original_contract_sha256':'9d0122561e9e506b23dfa2d090beadc2a498c50eba60d5a3e9c3795c6b3ea85d',
        'old_owned_forward_pid_stopped':28200,'old_birth_verified_ms':birth,
        'ssh_forward_pid':process.pid,'ssh_creation_date':current['CreationDate'],
        'ssh_executable':old['ssh_executable'],'ssh_executable_sha256':old['ssh_executable_sha256'],
        'guest_bind':'127.0.0.1:55483','fixed_windows_destination':'127.0.0.1:55484',
        'proxy_bind_and_destinations_unchanged':True,'dynamic_forwarding':False,
        'secret_consumption':False,'product_started':False,
        'scope':'Root-authorized contract annex: fixed reverse-SSH target points only to the new owned SCRAM instance; old QA55483 unchanged.'}
(OUT/'host-state.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,indent=2))
