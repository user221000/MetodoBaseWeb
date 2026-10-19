from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from ctypes import wintypes
import ctypes, hashlib, importlib.util, io, json, re, subprocess, tarfile, time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE=LAB/'evidence/runtime28-native-20261019'
OUT=BASE/'closure'
assert (OUT/'guest-teardown.stdout.json').is_file()
assert json.loads((OUT/'guest-teardown.stdout.json').read_text())['owned_network_removed']
def module(name):
    p=LAB/'scripts'/(name+'.py')
    expected={'guest_access':'616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7',
              'lab_control':'b5729b9ad3746bc9d18fc50f8ed14ad5acb2015326a8b9f856aadb745d1cf7d0'}[name]
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
access=module('guest_access');control=module('lab_control')
remote="""from pathlib import Path
import sys,tarfile
roots=[Path('/home/lab/metodobase-runtime28-network-20261019'),Path('/home/lab/metodobase-runtime28-product-a781deb39fd74441baa6a37c1a0cab40')]
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for root in roots:
  for p in sorted(root.rglob('*')):
   rel=p.relative_to(root)
   if 'private' in rel.parts:continue
   assert not p.is_symlink()
   if p.is_file():t.add(p,arcname=root.name+'/'+rel.as_posix(),recursive=False)
"""
fetch=OUT/'fetch-public-guest-input.py'
with fetch.open('x',encoding='ascii') as f:f.write(remote)
with fetch.open('rb') as stdin:r=access.run('sudo -n /opt/metodobase-lab/python/bin/python3.12 -B -',stdin=stdin,timeout=60)
assert r.returncode==0 and not r.stderr
dest=OUT/'guest-frozen';dest.mkdir()
members=[]
with tarfile.open(fileobj=io.BytesIO(r.stdout),mode='r:') as archive:
    for member in archive:
        rel=PurePosixPath(member.name)
        assert member.isfile() and not rel.is_absolute() and '..' not in rel.parts and 'private' not in rel.parts
        p=dest/Path(*rel.parts)
        assert p.resolve().is_relative_to(dest.resolve())
        p.parent.mkdir(parents=True,exist_ok=True)
        raw=archive.extractfile(member).read()
        with p.open('xb') as f:f.write(raw)
        members.append({'file':rel.as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
(OUT/'guest-fetch-receipt.json').write_text(json.dumps({'files':members,'archive_sha256':hashlib.sha256(r.stdout).hexdigest(),'private_directory_excluded':True},indent=2)+'\n')
def cim(pid):
    c='Get-CimInstance Win32_Process -Filter "ProcessId='+str(pid)+'" | Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress'
    return json.loads(subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',c],creationflags=subprocess.CREATE_NO_WINDOW))
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
k.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
k.CloseHandle.argtypes=[wintypes.HANDLE]
def held_process(identity,terminate=False):
    h=k.OpenProcess(0x1000|0x00100000|(1 if terminate else 0),False,identity['ProcessId']);assert h
    try:
        b=ctypes.create_unicode_buffer(32768);n=wintypes.DWORD(len(b))
        assert k.QueryFullProcessImageNameW(h,0,b,ctypes.byref(n))
        assert Path(b.value).resolve()==Path(identity['ExecutablePath']).resolve()
        ts=[wintypes.FILETIME() for _ in range(4)]
        assert k.GetProcessTimes(h,*[ctypes.byref(t) for t in ts])
        birth=((ts[0].dwHighDateTime<<32)+ts[0].dwLowDateTime)//10000-11644473600000
        assert abs(birth-int(re.search(r'/Date\((\d+)\)/',identity['CreationDate']).group(1)))<=1
        return h,birth
    except BaseException:k.CloseHandle(h);raise
ssh=json.loads((BASE/'network-target55484/host-state.json').read_text())
identity=cim(ssh['ssh_forward_pid'])
assert identity['ProcessId']==3956 and identity['CreationDate']==ssh['ssh_creation_date']
assert Path(identity['ExecutablePath']).resolve()==Path(ssh['ssh_executable']).resolve()
assert hashlib.sha256(Path(identity['ExecutablePath']).read_bytes()).hexdigest()==ssh['ssh_executable_sha256']
assert '127.0.0.1:55483:127.0.0.1:55484' in identity['CommandLine']
h,birth=held_process(identity,terminate=True)
try:
    assert k.TerminateProcess(h,0)
    assert k.WaitForSingleObject(h,10000)==0
finally:k.CloseHandle(h)
state=control.state();assert state['pid']==18028
assert control.process_identity(state)
qi=cim(18028);h,qbirth=held_process(qi)
try:
    restarted=datetime.fromisoformat(state['restarted_utc']).timestamp()*1000
    assert abs(qbirth-restarted)<5000
    reply=control.qmp(state,['system_powerdown'])
    (OUT/'qmp-powerdown.json').write_text(json.dumps(reply,indent=2)+'\n')
    started=time.monotonic()
    while k.WaitForSingleObject(h,1000)!=0:
        assert time.monotonic()-started<120,'ACPI shutdown pending; no hard kill'
    elapsed=time.monotonic()-started
finally:k.CloseHandle(h)
assert control.process_identity(state) is None
receipt={'finished_utc':datetime.now(timezone.utc).isoformat(),'owned_ssh_pid_stopped':3956,'ssh_birth_verified_ms':birth,
         'owned_qemu_pid_stopped':18028,'qemu_birth_verified_ms':qbirth,'shutdown':'QMP system_powerdown; process exited',
         'shutdown_wait_seconds':elapsed,'guest_memory_mib_released':2048,'overlay_and_images_preserved':True,
         'pg55484_left_running_for_authorized_backend_handoff':True,'windows_shutdown_or_global_config_change':False}
(OUT/'host-vm-closure.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
