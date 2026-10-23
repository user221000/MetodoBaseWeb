"""Current57 metadata gate; never start, upload, build or clean a guest.

The Root lease producer is separate. Host RAM pre4.4GiB/post2GiB, C/F free2GiB
and a fresh E budget remain external prerequisites; this runner does not claim
to measure them. Structural offline doubles are not authentic context or guest
acceptance. The original LAB helper does not itself attest birth/generation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from types import ModuleType

from . import authority, context

ROOT=Path(__file__).resolve().parents[2]
E_HOME=Path('E:/MetodoBaseWorkspace')
HISTORICAL_TEMP=E_HOME/'temp'
LAB = Path("F:/MetodoBaseWeb-linux-lab-20261019")
CACHE_TAG = "metodobase-lab:expat-sec10-m2-72c44a1"
CACHE_ID = "sha256:a2b7e06ec1971f6519395aa1cd08c54f6d18c2bf26749abf3d65513f86337e7f"
LAB_HELPERS = {
    "lab_control": "b5729b9ad3746bc9d18fc50f8ed14ad5acb2015326a8b9f856aadb745d1cf7d0",
    "guest_access": "616b66b791140966dac837fbd58808291b165d4ae06011a1395279462f43b7a7",
}


def load(name):
    path = LAB / "scripts" / (name + ".py")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LAB_HELPERS[name]:
        raise ValueError("The reviewed owned lab access helper differs")
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)  # noqa: S102
    return module


def validate_guest(value):
    if (value["system"] != "Linux" or value["machine"] != "x86_64"
            or type(value["free_bytes"]) is not int or value["free_bytes"] < 2500 * 1024 * 1024
            or type(value["mem_available_KiB"]) is not int or value["mem_available_KiB"] < 1024 * 1024
            or value["running_containers"] != [] or value["cached_native_image_id"] != CACHE_ID):
        raise ValueError("The fresh guest resource/cache contract differs; no build is authorized")
    return {key: value[key] for key in ("system", "machine", "free_bytes", "mem_available_KiB",
                                      "running_containers", "cached_native_image_id")}


REMOTE = """import json,os,platform,subprocess
from pathlib import Path
def capture(argv):
    result=subprocess.run(argv,capture_output=True,text=True,check=True)
    return result.stdout
stats=os.statvfs('/var/lib/docker')
memory=dict((key,int(value.strip().split()[0])) for key,value in
    (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()))
images=json.loads(capture(['sudo','-n','docker','image','inspect','CACHE_TAG']))
assert len(images)==1
value={'system':platform.system(),'machine':platform.machine(),
    'free_bytes':stats.f_bavail*stats.f_frsize,'mem_available_KiB':memory['MemAvailable'],
    'running_containers':capture(['sudo','-n','docker','ps','-q']).splitlines(),
    'cached_native_image_id':images[0]['Id'],
    'docker_version':capture(['sudo','-n','docker','version','--format','{{.Server.Version}}']).strip(),
    'docker_space':capture(['sudo','-n','docker','system','df']),
    'lab_nonce':Path('/var/tmp/metodobase-lab-nonce').read_text().strip(),
    'source_transferred':False,'image_built':False}
print(json.dumps(value))
""".replace("CACHE_TAG", CACHE_TAG).encode()

LEASE_KEYS=frozenset(('schema','source','input_contract_sha256','manifest_sha256','context_sha256',
    'state_sha256','lab_helpers','generation','issued_utc','expires_utc','pid','birth_filetime',
    'executable','exe_sha256','argv','nonce','overlay'))
EXTERNAL_PREREQUISITES={'host_RAM_pre_GiB':4.4,'host_RAM_post_GiB':2,
    'host_C_free_GiB':2,'host_F_free_GiB':2,'fresh_E_budget':'Root lease phase',
    'measured_by_this_runner':False}


def check(condition,message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(value,pattern='[0-9a-f]{64}'):
    check(type(value) is str and re.fullmatch(pattern,value) is not None,'Explicit lowercase source/pin required')
    return value


def absent(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    return False


def e_path(path,*,file=False):
    path=Path(path)
    check(path.is_absolute() and '..' not in path.parts,'Absolute E path required')
    base=authority.regular_directory(E_HOME)
    check(path.is_relative_to(base) and not path.is_relative_to(HISTORICAL_TEMP),'Current E workspace outside historical temp required')
    if file:
        authority.regular_file(path)
        check(path.lstat().st_nlink==1,'Input file alias refused')
    else:
        authority.regular_directory(path.parent)
    check(not path.is_relative_to(ROOT.resolve()),'Evidence/input inside checkout refused')
    return path


def file_snapshot(path,*,limit):
    path=authority.regular_file(path)
    value=path.lstat()
    check(value.st_nlink==1 and 0<=value.st_size<=limit,'Unsafe input alias or size')
    raw=path.read_bytes()
    after=path.lstat()
    fields=lambda item:(item.st_dev,item.st_ino,item.st_size,item.st_mtime_ns,item.st_ctime_ns)
    check(fields(value)==fields(after),'Input metadata changed during readback')
    return raw,{'sha256':hashlib.sha256(raw).hexdigest(),'metadata':fields(after)}


def validate_inputs(args):
    pin(args.source,'[0-9a-f]{40}')
    for value in (args.contract_sha256,args.manifest_sha256,args.context_sha256,args.lease_sha256):
        pin(value)
    contract_path=e_path(args.input_contract,file=True)
    manifest_path=e_path(args.context_manifest,file=True)
    check(contract_path.name=='runtime-input-contract.json' and manifest_path.name=='source-manifest.json'
        and contract_path.parent==manifest_path.parent,'One explicit closed context parent required')
    paths=[contract_path,manifest_path,contract_path.parent/'source-context.tar',contract_path.parent/'source-objects.zip']
    snapshots={};raws={}
    for path in paths:
        e_path(path,file=True)
        raw,snapshot=file_snapshot(path,limit=context.MAX_CONTEXT if path.suffix=='.tar' else 8*1024**2)
        snapshots[path]=snapshot;raws[path]=raw
    check(snapshots[contract_path]['sha256']==args.contract_sha256
        and snapshots[manifest_path]['sha256']==args.manifest_sha256
        and snapshots[paths[2]]['sha256']==args.context_sha256,'Root context pins differ')
    contract=context.json_object(raws[contract_path])
    check(contract['source']==args.source and contract['context_sha256']==args.context_sha256,'Current source/context binding differs')
    manifest,records=context.validate_contract(contract_path.parent,contract)
    check(manifest['source_commit']==args.source and manifest['archive_sha256']==args.context_sha256,
        'Validated source manifest differs')
    for path,snapshot in snapshots.items():
        check(file_snapshot(path,limit=context.MAX_CONTEXT)[1]==snapshot,'Context changed during validation')
    return contract,manifest,records,snapshots


def timestamp(value):
    check(type(value) is str,'Aware UTC lease timestamp required')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    check(parsed.tzinfo is not None and parsed.utcoffset() is not None,'Aware lease timestamp required')
    return parsed


def validate_lease(value,args,state_raw,state,*,now=None):
    check(type(value) is dict and set(value)==LEASE_KEYS,'Exactly seventeen lease fields required')
    check(value['schema']=='current57-readonly-lease-v1','Lease schema differs')
    pin(value['source'],'[0-9a-f]{40}')
    for key in ('input_contract_sha256','manifest_sha256','context_sha256','state_sha256','exe_sha256'):
        pin(value[key])
    pin(value['generation'],'[0-9a-f]{32}')
    pin(value['nonce'],'[0-9a-f]{40}')
    check(value['source']==args.source and value['input_contract_sha256']==args.contract_sha256
        and value['manifest_sha256']==args.manifest_sha256 and value['context_sha256']==args.context_sha256
        and value['state_sha256']==hashlib.sha256(state_raw).hexdigest(),'Lease source/state pins differ')
    check(type(value['lab_helpers']) is dict and value['lab_helpers']==LAB_HELPERS,'Lease helper pins differ')
    issued=timestamp(value['issued_utc']);expires=timestamp(value['expires_utc'])
    now=now or datetime.now(timezone.utc)
    check(issued<=now<expires and 0<(expires-issued).total_seconds()<=4*60*60,'Root lease expired or exceeds four hours')
    for key in ('pid','birth_filetime'):
        check(type(value[key]) is int and value[key]>0,'Strict positive process identity required')
    check(type(state['pid']) is int and value['pid']==state['pid'] and value['nonce']==state['nonce'],
        'Lease PID/nonce differs from state')
    check(type(value['argv']) is list and value['argv'] and all(type(item) is str and item and '\0' not in item for item in value['argv'])
        and value['argv']==state['command'],'Lease argv differs from state')
    check(type(value['executable']) is str and Path(value['executable']).is_absolute()
        and value['executable']==state['command'][0],'Lease executable differs')
    overlay=value['overlay']
    check(type(overlay) is dict and set(overlay)=={'path','volume','inode'}
        and type(overlay['path']) is str and Path(overlay['path']).is_absolute() and overlay['path']==state['overlay'],
        'Lease overlay path differs')
    for key in ('volume','inode'):
        check(type(overlay[key]) is int and overlay[key]>0,'Strict positive overlay identity required')
    check(state['resources']=={'vcpus':2,'memory_mib':2048,'acceleration':'tcg,thread=multi'}
        and type(state['resources']['vcpus']) is int and type(state['resources']['memory_mib']) is int,
        'The leased VM resource definition differs')
    return value


class WindowsIdentity:
    """Retain process HANDLE and overlay FileID; never hash a live overlay."""
    def __init__(self,lease):
        if os.name!='nt':
            raise ValueError('Actual LAB identity requires reviewed Windows transport')
        import ctypes
        from ctypes import wintypes as W
        self.ctypes=ctypes;self.W=W;self.lease=lease
        self.K=ctypes.WinDLL('kernel32',use_last_error=True)
        self.S=ctypes.WinDLL('shell32',use_last_error=True)
        self.process=None;self.overlay=None
        self.K.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];self.K.OpenProcess.restype=W.HANDLE
        self.K.CloseHandle.argtypes=[W.HANDLE];self.K.CloseHandle.restype=W.BOOL
        self.K.GetProcessId.argtypes=[W.HANDLE];self.K.GetProcessId.restype=W.DWORD
        self.K.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];self.K.WaitForSingleObject.restype=W.DWORD
        self.K.GetProcessTimes.argtypes=[W.HANDLE,*([ctypes.POINTER(W.FILETIME)]*4)]
        self.K.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
        self.K.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE]
        self.K.CreateFileW.restype=W.HANDLE
        self.S.CommandLineToArgvW.argtypes=[W.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
        self.S.CommandLineToArgvW.restype=ctypes.POINTER(W.LPWSTR)
        self.K.LocalFree.argtypes=[ctypes.c_void_p]
        class Info(ctypes.Structure):
            _fields_=[('attrs',W.DWORD),('created',W.FILETIME),('accessed',W.FILETIME),('modified',W.FILETIME),
                ('volume',W.DWORD),('size_hi',W.DWORD),('size_lo',W.DWORD),('links',W.DWORD),('index_hi',W.DWORD),('index_lo',W.DWORD)]
        self.Info=Info
        self.K.GetFileInformationByHandle.argtypes=[W.HANDLE,ctypes.POINTER(Info)]
        try:
            self.process=self.K.OpenProcess(0x1000|0x100000,False,lease['pid'])
            self.ok(self.process)
            overlay=authority.regular_file(Path(lease['overlay']['path']))
            self.overlay=self.K.CreateFileW(str(overlay),0x80,3,None,3,0x00200000,None)
            check(self.overlay not in (None,ctypes.c_void_p(-1).value),'Cannot retain owned overlay metadata handle')
            self.verify()
        except BaseException:
            self.close();raise

    def ok(self,value):
        if not value:
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        return value

    def argv(self,commandline):
        count=self.ctypes.c_int()
        values=self.S.CommandLineToArgvW(commandline,self.ctypes.byref(count))
        self.ok(values)
        try:
            return [values[index] for index in range(count.value)]
        finally:
            self.K.LocalFree(values)

    def verify(self,process=None):
        check(self.K.WaitForSingleObject(self.process,0)==0x102,'Retained owned process exited')
        check(self.K.GetProcessId(self.process)==self.lease['pid'],'Retained process PID differs')
        times=[self.W.FILETIME() for _ in range(4)]
        self.ok(self.K.GetProcessTimes(self.process,*(self.ctypes.byref(value) for value in times)))
        birth=times[0].dwLowDateTime|(times[0].dwHighDateTime<<32)
        check(birth==self.lease['birth_filetime'],'Owned process birth differs')
        buffer=self.ctypes.create_unicode_buffer(32768);size=self.W.DWORD(len(buffer))
        self.ok(self.K.QueryFullProcessImageNameW(self.process,0,buffer,self.ctypes.byref(size)))
        executable=authority.regular_file(Path(buffer.value))
        check(executable==Path(self.lease['executable']) and digest(executable)==self.lease['exe_sha256'],
            'Retained process executable identity differs')
        row=self.Info();self.ok(self.K.GetFileInformationByHandle(self.overlay,self.ctypes.byref(row)))
        check(not row.attrs&(0x400|0x10) and row.links==1 and row.volume==self.lease['overlay']['volume']
            and (row.index_lo|(row.index_hi<<32))==self.lease['overlay']['inode'],'Retained overlay FileID differs')
        if process is not None:
            check(type(process) is dict and type(process['ProcessId']) is int and process['ProcessId']==self.lease['pid']
                and Path(process['ExecutablePath'])==executable and self.argv(process['CommandLine'])==self.lease['argv'],
                'Actual process argv/executable differs from Root lease')

    def close(self):
        errors=[]
        for name in ('overlay','process'):
            value=getattr(self,name,None)
            if value not in (None,self.ctypes.c_void_p(-1).value):
                try:
                    self.ok(self.K.CloseHandle(value))
                except OSError as error:
                    errors.append(error)
                finally:
                    setattr(self,name,None)
        if errors:
            raise errors[0]

    def __enter__(self):
        return self

    def __exit__(self,*_):
        self.close()


def write_raw(path,raw):
    with path.open('xb') as output:
        output.write(raw);output.flush();os.fsync(output.fileno())


def roots(args,input_parent,lease_path):
    private=e_path(args.private);public=e_path(args.output)
    check(absent(private) and absent(public),'Fresh output roots required')
    check(all(not one.is_relative_to(two) and not two.is_relative_to(one)
        for one,two in ((private,public),(private,input_parent),(public,input_parent))),
        'Evidence roots overlap input/private/public')
    check(not lease_path.is_relative_to(private) and not lease_path.is_relative_to(public),'Lease overlaps fresh evidence')
    return private,public


def execute(args):
    check(args.authorized_read_only_preflight is True,'Explicit Root read-only preflight authority required')
    contract,manifest,records,snapshots=validate_inputs(args)
    lease_path=e_path(args.lease,file=True)
    lease_raw,lease_snapshot=file_snapshot(lease_path,limit=1024*1024)
    check(lease_snapshot['sha256']==args.lease_sha256,'Root lease SHA differs')
    state_path=authority.regular_file(LAB/'instance/state.json')
    state_raw,state_snapshot=file_snapshot(state_path,limit=1024*1024)
    state=context.json_object(state_raw)
    lease=validate_lease(context.json_object(lease_raw),args,state_raw,state)
    helper_snapshots={}
    for name,expected in LAB_HELPERS.items():
        path=LAB/'scripts'/(name+'.py')
        _,snapshot=file_snapshot(path,limit=1024*1024)
        check(snapshot['sha256']==expected,'Reviewed LAB helper differs')
        helper_snapshots[path]=snapshot
    private,public=roots(args,Path(args.input_contract).parent,lease_path)
    private=authority.private_directory(private,ROOT)
    evidence=authority.evidence();acl=evidence['boundary_before_payload'](private)
    write_raw(private/'lease.private.json',lease_raw)
    write_raw(private/'state.private.json',state_raw)
    with WindowsIdentity(lease) as identity:
        lifecycle=load('lab_control')
        process=lifecycle.process_identity(state)
        check(process is not None,'The owned guest must already be started under a separate Root lease')
        identity.verify(process)
        guest_access=load('guest_access')
        write_raw(private/'remote-readonly.py',REMOTE)
        with (private/'remote-readonly.py').open('rb') as payload:
            response=guest_access.run('python3 -',stdin=payload,timeout=45)
        write_raw(private/'guest.stdout.private.json',response.stdout)
        write_raw(private/'guest.stderr.private.log',response.stderr)
        # Same HANDLE stays live while all closed authority is rechecked.
        process=lifecycle.process_identity(state)
        check(process is not None,'Owned process identity disappeared after SSH')
        identity.verify(process)
        check(file_snapshot(state_path,limit=1024*1024)[1]==state_snapshot,'Owned state changed during preflight')
        check(file_snapshot(lease_path,limit=1024*1024)[1]==lease_snapshot,'Root lease changed during preflight')
        validate_lease(lease,args,state_raw,state)
        for path,snapshot in helper_snapshots.items():
            check(file_snapshot(path,limit=1024*1024)[1]==snapshot,'Reviewed LAB helper changed during preflight')
        for path,snapshot in snapshots.items():
            check(file_snapshot(path,limit=context.MAX_CONTEXT)[1]==snapshot,'Closed context changed during preflight')
        check(response.returncode==0,'The owned guest read-only preflight failed; originals retained')
        value=context.json_object(response.stdout)
        check(value['lab_nonce']==state['nonce'],'The SSH guest is not the owned leased instance')
        checked=validate_guest(value)
    result={'scope':'current57 read-only owned guest preflight; no build authorized',
        'source_commit':args.source,'input_contract_sha256':args.contract_sha256,
        'manifest_sha256':args.manifest_sha256,'source_context_sha256':args.context_sha256,
        'lease_sha256':args.lease_sha256,'context_files':len(records),'app_files':len(context.app_records(records)),
        'runtime_distributions_expected':57,'native_inputs':12,'native_merkle_objects':21,
        'VM_resources':state['resources'],'owned_PID':lease['pid'],'birth_filetime':lease['birth_filetime'],
        'Root_lease_generation':lease['generation'],'native_QEMU_generation_claimed':False,
        'overlay_native_identity':{key:lease['overlay'][key] for key in ('volume','inode')},
        'executable_sha256':lease['exe_sha256'],'lab_helpers':LAB_HELPERS,'guest':checked,
        'external_host_prerequisites':EXTERNAL_PREREQUISITES,
        'VM_started_by_this_runner':False,'source_transferred':False,'image_built':False,
        'SQL_Redis_Chrome_started':False,'build_authorized':False,'SBOM_SCA_complete':False}
    return evidence['seal'](private,public,result,acl)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--source',required=True)
    parser.add_argument('--input-contract',type=Path,required=True)
    parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--context-manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--context-sha256',required=True)
    parser.add_argument('--lease',type=Path,required=True)
    parser.add_argument('--lease-sha256',required=True)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--authorized-read-only-preflight',action='store_true',required=True)
    args=parser.parse_args(argv)
    print(json.dumps(execute(args)))
    return 0
