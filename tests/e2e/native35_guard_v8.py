"""Finite current-web v8 admission. No SQL/process/application import on module load."""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('F:/MetodoBaseWeb-execution-20261018')
HOME = Path('E:/MetodoBaseWorkspace')
PG_BIN = HOME / 'tools/postgresql17/bin'
ROOTS = ['web', 'api', 'core', 'config', 'utils', 'src', 'static', 'fonts']
GENERATION = re.compile(r'[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
HEAD = re.compile(r'[0-9a-f]{40}\Z')
TRANSITIVE_SHA = 'c41726235eb296c149fe9c88eb90d2a9f9e1d51057752b551a2534a4aabbfa56'
PG_CONTRACT_SHA = '520cbd9f74d13bfb053fd557e5607281f97b5a5b07400d83f1c8f04b591a1e8f'

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode('utf8')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate private control key")
        value[key] = item
    return value


def private_json(path, limit=65536):
    path = Path(path)
    if (not path.is_file() or path.is_symlink()
            or getattr(path.lstat(), "st_file_attributes", 0) & 0x400
            or path.stat().st_size > limit):
        raise ValueError("Private control is not a bounded regular file")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Private control exceeded its bound")
    return json.loads(raw, object_pairs_hook=unique)


def validate_ack(value, expected, now=None):
    """Pure typed finite contract; cleanup deliberately does not call this."""
    if set(value) != set(expected) | {"granted", "expires_at_UTC"}:
        raise ValueError("Unexpected Root ACK fields")
    if value["granted"] is not True:
        raise ValueError("Root ACK not granted")
    if type(value.get("UUIDs")) is not int or value["UUIDs"] != 1:
        raise ValueError("Root UUID budget differs")
    if (type(value.get("expected_groups")) is not list
            or any(type(item) is not int for item in value["expected_groups"])):
        raise ValueError("Root group contract is not typed")
    for key, item in expected.items():
        if canonical(value[key]) != canonical(item):
            raise ValueError("Root ACK binding differs")
    if not isinstance(value["expires_at_UTC"], str):
        raise TypeError("Root ACK expiry is not explicit")
    expiry = datetime.fromisoformat(value["expires_at_UTC"])
    instant = datetime.now(UTC) if now is None else now
    if expiry.tzinfo is None or instant.tzinfo is None:
        raise ValueError("Root ACK expiry must be timezone aware")
    if not 0 < (expiry - instant).total_seconds() <= 4 * 3600:
        raise ValueError("Root ACK expired or exceeds four hours")
    return value


def _check(value, message):
    if not value:
        raise ValueError(message)


def e_path(value):
    _check(type(value) is str, 'Explicit E path required')
    path=Path(value)
    _check(path.is_absolute() and path.is_relative_to(HOME) and '..' not in path.parts,
           'Private inputs must stay in reviewed E workspace')
    return path


def validate_manifest(value, observed_head, observed_files):
    _check(type(value) is dict and set(value)=={'schema','repository','HEAD','roots','files'},
           'Exact current-source manifest required')
    _check(value['schema']=='native35-v8-source-v1' and value['repository']==ROOT.as_posix()
           and type(value['HEAD']) is str and HEAD.fullmatch(value['HEAD']) is not None
           and type(value['roots']) is list and canonical(value['roots'])==canonical(ROOTS),
           'Root manifest repository/HEAD/eight-root binding differs')
    files=value['files']
    _check(type(files) is dict and files, 'Full RAW source map required')
    folded=set()
    for name,pin in files.items():
        _check(type(name) is str and '\\' not in name and not name.startswith('/')
               and name.split('/')[0] in ROOTS and not any(part in {'','.', '..','__pycache__'} for part in name.split('/'))
               and not name.endswith(('.pyc','.pyo')) and name.casefold() not in folded
               and type(pin) is str and SHA.fullmatch(pin) is not None, 'Manifest file binding invalid')
        folded.add(name.casefold())
    _check(type(observed_head) is str and observed_head==value['HEAD']
           and canonical(observed_files)==canonical(files), 'Frozen HEAD or complete eight-root RAW source changed')
    return value


def validate_profile(value):
    keys={'METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN'}
    _check(type(value) is dict and set(value)==keys and all(type(v) is str and v for v in value.values()),
           'Exact three-key native PG profile required')
    _check(Path(value['METODOBASE_TEST_PG_BIN'])==PG_BIN, 'Only pinned portable E PostgreSQL17 directory admitted')
    users=[]
    for key in ('METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL'):
        parsed=urlsplit(value[key])
        _check(parsed.scheme in {'postgresql','postgresql+psycopg2','postgres'}
               and parsed.hostname in {'127.0.0.1','localhost'} and parsed.port==55483
               and unquote(parsed.path.lstrip('/')).startswith('metodobase_test')
               and unquote(parsed.username or '').startswith('metodobase_test')
               and not parsed.query and not parsed.fragment, 'Native PG profile must remain dedicated loopback55483')
        users.append(unquote(parsed.username))
    _check(users[0]!=users[1], 'Migrator and application roles must remain distinct')
    return value


def validate_generation(value, *, observed_identity=None, observed_sql=None):
    _check(type(value) is dict and set(value)=={'postmaster_pid','master_creation_filetime_100ns','postmaster_start_UTC'},
           'Exact Windows PG generation required')
    _check(all(type(value[k]) is int and value[k]>0 for k in ('postmaster_pid','master_creation_filetime_100ns'))
           and type(value['postmaster_start_UTC']) is str, 'Typed positive PostgreSQL PID/birth required')
    instant=datetime.fromisoformat(value['postmaster_start_UTC'])
    _check(instant.tzinfo is not None,'PG generation timestamp must be timezone aware')
    if observed_identity is not None:
        created,exe=observed_identity
        _check(type(created) is int and created==value['master_creation_filetime_100ns']
               and Path(exe)==PG_BIN/'postgres.exe','Approved PostgreSQL PID/birth/executable changed')
    if observed_sql is not None:
        _check(observed_sql[0]==instant and observed_sql[1] in {'127.0.0.1','127.0.0.1/32'}
               and type(observed_sql[2]) is int and observed_sql[2]==55483,'Approved PostgreSQL start/address/port changed')
    return value


def validate_context(preflight, manifest, profile, generation, *, observed_head, observed_files,
                     manifest_sha256, profile_sha256, generation_sha256):
    _check(preflight['schema']=='native35-v8' and preflight['selection']=='current35'
           and canonical(preflight['expected_groups'])==canonical([15,18,2]),'Native35 v8 selection differs')
    validate_manifest(manifest,observed_head,observed_files);validate_profile(profile);validate_generation(generation)
    _check(preflight['source_head']==preflight['product_source']==manifest['HEAD']
           and preflight['source_manifest_sha256']==manifest_sha256
           and preflight['profile_sha256']==profile_sha256
           and preflight['generation_sha256']==generation_sha256,'Source/profile/generation reference binding changed')
    for key in ('source_manifest_path','profile_path','generation_path'):
        e_path(preflight[key])
    _check(type(preflight['postgres_executable_sha256']) is str
           and SHA.fullmatch(preflight['postgres_executable_sha256']) is not None,'PG17 executable digest required')
    return preflight


def validate_helpers(bindings,observed):
    _check(type(bindings) is dict and len(bindings)==22 and type(observed) is dict
           and set(bindings)==set(observed),'Exact immutable22 helper inventory required')
    for name,row in bindings.items():
        _check(type(row) is dict and set(row)=={'raw_sha256','bytes','historical_raw_sha256','historical_bytes','framing'}
               and type(row['bytes']) is int and row['bytes']>=0
               and type(row['historical_bytes']) is int and row['historical_bytes']>=0
               and type(row['raw_sha256']) is str and SHA.fullmatch(row['raw_sha256']) is not None
               and type(row['historical_raw_sha256']) is str and SHA.fullmatch(row['historical_raw_sha256']) is not None,
               'Typed finite helper22 binding required')
        actual=observed[name]
        _check(type(actual) is dict and set(actual)=={'sha256','bytes'} and type(actual['bytes']) is int
               and actual['sha256']==row['raw_sha256'] and actual['bytes']==row['bytes'],
               'Immutable helper22 RAW changed')
    return bindings


def source_context():
    head=subprocess.check_output(['git','--no-replace-objects','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    observed={}
    def failed(error):raise error
    for name in ROOTS:
        parent=ROOT/name
        meta=os.lstat(parent)
        _check(stat.S_ISDIR(meta.st_mode) and not getattr(meta,'st_file_attributes',0)&0x400,'Runtime root is not a real directory')
        for directory,dirs,files in os.walk(parent,followlinks=False,onerror=failed):
            for child in dirs:
                entry=Path(directory)/child;item=os.lstat(entry)
                _check(not stat.S_ISLNK(item.st_mode) and not getattr(item,'st_file_attributes',0)&0x400,'Reparse runtime directory refused')
            dirs[:]=[child for child in dirs if child!='__pycache__']
            for child in files:
                if child.endswith(('.pyc','.pyo')):continue
                entry=Path(directory)/child;before=os.lstat(entry)
                _check(stat.S_ISREG(before.st_mode) and not getattr(before,'st_file_attributes',0)&0x400,'Nonregular runtime source refused')
                raw=entry.read_bytes();after=os.lstat(entry)
                _check(all(getattr(before,k)==getattr(after,k) for k in ('st_ino','st_size','st_mtime_ns')),'Runtime file changed while hashing')
                observed[entry.relative_to(ROOT).as_posix()]=digest(raw)
    return head,observed


def _admission(task,phase,now=None):
    _check(phase in {'sql','chrome'} and os.name=='nt','Windows Native phase required')
    task=e_path(str(task))
    _check(task.name.startswith('metodobase-account37-author-pg-'),'Fresh native37 task namespace required')
    _check(Path(__file__).resolve()==ROOT/'tests/e2e/native35_guard_v8.py','V8 must execute from the frozen canonical source')
    path=task/'native-preflight.json';preflight=private_json(path,8*1024*1024);raw=path.read_bytes()
    source=e_path(preflight['source_manifest_path']);profile_path=e_path(preflight['profile_path']);generation_path=e_path(preflight['generation_path'])
    manifest=private_json(source,8*1024*1024);profile=private_json(profile_path);generation=private_json(generation_path)
    source_raw=source.read_bytes();profile_raw=profile_path.read_bytes();generation_raw=generation_path.read_bytes()
    head,files=source_context()
    validate_context(preflight,manifest,profile,generation,observed_head=head,observed_files=files,
                     manifest_sha256=digest(source_raw),profile_sha256=digest(profile_raw),generation_sha256=digest(generation_raw))
    transitive_raw=(ROOT/'tests/e2e/native35_transitive_v8.json').read_bytes()
    _check(digest(transitive_raw)==TRANSITIVE_SHA,'Finite22 binding manifest changed')
    bindings=json.loads(transitive_raw)['helper_bindings']
    observed={}
    for name in bindings:
        helper_raw=(ROOT/name).read_bytes();observed[name]={'sha256':digest(helper_raw),'bytes':len(helper_raw)}
    validate_helpers(bindings,observed)
    _check(digest((ROOT/'tests/billing13_legacy_apply37_pg_contract.py').read_bytes())==PG_CONTRACT_SHA,'Approved generation helpers changed')
    # These approved helpers are stdlib-only on import and make no SQL connection here.
    from tests.billing13_legacy_apply37_pg_contract import validated_generation, windows_process_identity
    validated_generation(generation)
    validate_generation(generation,observed_identity=windows_process_identity(generation['postmaster_pid']))
    _check(digest((PG_BIN/'postgres.exe').read_bytes())==preflight['postgres_executable_sha256'],'PG17 executable source changed')
    expected={'scope':'native35-v8-'+phase,'source_head':head,'product_source':head,'selection':'current35',
              'expected_groups':[15,18,2],'UUIDs':1,'preflight_sha256':digest(raw),
              'profile_sha256':digest(profile_raw),'source_manifest_sha256':digest(source_raw),'generation_sha256':digest(generation_raw),
              'launcher_sha256':digest((ROOT/'tests/e2e/run_native35_qa_v8.py').read_bytes()),
              'fixture_sha256':digest((ROOT/'tests/e2e/native35_postgres_server_v8.py').read_bytes()),
              'guard_sha256':digest(Path(__file__).read_bytes()),
              'generation_guard_sha256':digest((ROOT/'tests/e2e/native35_generation_v8.py').read_bytes())}
    if phase=='chrome':expected['startup_sha256']=digest((task/'private/startup.json').read_bytes())
    ack_path=task/('native-'+phase+'-ack.json');validate_ack(private_json(ack_path),expected,now)
    context={'preflight_sha256':digest(raw),'source_manifest_sha256':digest(source_raw),'profile_sha256':digest(profile_raw),
             'generation_sha256':digest(generation_raw),'source_head':head,'generation':generation}
    return context,profile,digest(ack_path.read_bytes())


def require_ack(task,phase,now=None):
    return _admission(task,phase,now)[2]


def checked_native_runtime(task):
    current,profile,_ack=_admission(task,'sql')
    return current,profile


def admitted_phase(check, launch):
    """Readmission occurs immediately before each new child; no finally guard."""
    check()
    return launch()


def require_chrome_phase(task):
    # The new browser may cause real SQL through HTTP, so both leases must hold.
    return {phase: require_ack(task, phase) for phase in ("sql", "chrome")}


class PrivateStop:
    """Exactly four instance-bound keys, with own process birth checked locally."""

    def __init__(self, private, pid, generation, source_commit, birth, identity):
        if (type(pid) is not int or pid <= 0 or not GENERATION.fullmatch(generation)
                or not re.fullmatch(r"[0-9a-f]{40}", source_commit)):
            raise ValueError("Invalid own stop identity")
        self.path = Path(private) / "stop-request.private.json"
        self.pid, self.generation, self.source = pid, generation, source_commit
        self.birth, self.identity = birth, identity
        self.accepted = False
        self.refusals = 0
        self.last_error_class = None

    def inspect(self):
        if not self.path.exists():
            return False
        try:
            value = private_json(self.path, 4096)
            if (type(value) is not dict or set(value) != {"action", "pid", "generation", "source_commit"}
                    or value["action"] != "stop" or type(value["pid"]) is not int
                    or value["pid"] != self.pid or value["generation"] != self.generation
                    or value["source_commit"] != self.source
                    or self.identity() != (self.pid, self.birth)):
                raise ValueError("Private stop identity mismatch")
            self.accepted = True
            return True
        except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
            self.refusals = min(1000, self.refusals + 1)
            self.last_error_class = type(error).__name__
            return False


def stop_receipt(closed, started, returned, joined, guard, error_class):
    accepted = guard is not None and guard.accepted is True
    return {"server_started": started is True, "normal_return": returned is True,
            "watcher_stopped_joined": joined is True, "stop_request_accepted": accepted,
            "stop_refusals": guard.refusals if guard is not None else 0,
            "error_class": error_class,
            "normal_shutdown_accepted": all(item is True for item in (closed, started, returned, joined, accepted)) and error_class is None}


def _api():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    api.OpenProcess.restype = ctypes.c_void_p
    api.CloseHandle.argtypes = [ctypes.c_void_p]
    api.GetProcessTimes.argtypes = [ctypes.c_void_p, *([ctypes.c_void_p] * 4)]
    return api


def _birth(handle):
    times = [ctypes.c_ulonglong() for _ in range(4)]
    if not _api().GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
        raise ValueError("Owned process birth unavailable")
    return times[0].value


def _fact(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("Owned PID invalid")
    code = "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(pid) + "';if($null -eq $p){throw 'Owned process absent'};$p|Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate|ConvertTo-Json -Compress"
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
                            capture_output=True, check=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.stderr.strip():
        raise ValueError("Owned process observation failed")
    value = json.loads(result.stdout.decode("utf-8-sig"))
    value["executable_sha256"] = digest(Path(value["ExecutablePath"]).read_bytes())
    return value


def _argv(command):
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not pointer:
        raise ValueError("Owned argument vector unavailable")
    try:
        return [pointer[index] for index in range(count.value)]
    finally:
        api = _api()
        api.LocalFree.argtypes = [ctypes.c_void_p]
        api.LocalFree(ctypes.cast(pointer, ctypes.c_void_p))


def verify_listener(pid):
    code = "[pscustomobject]@{rows=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object {$_.LocalPort -eq 8802}|Select-Object LocalAddress,LocalPort,OwningProcess)}|ConvertTo-Json -Depth 5 -Compress"
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
                            capture_output=True, check=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    value = json.loads(result.stdout.decode("utf-8-sig"))["rows"]
    if (result.stderr.strip() or not value
            or any(row != {"LocalAddress": "127.0.0.1", "LocalPort": 8802, "OwningProcess": pid} for row in value)):
        raise ValueError("Actual listener is not the owned fixture worker")
    return value


class OwnedWorker:
    """Retain the worker kernel object, then revalidate birth/argv before stop."""

    def __init__(self, startup, expected_args, wrapper_pid, base_executable):
        self.startup = startup
        self.handle = _api().OpenProcess(0x00100000 | 0x1000, False, startup["pid"])
        if not self.handle:
            raise ValueError("Cannot retain own worker HANDLE")
        try:
            self.fact = _fact(startup["pid"])
            if (_birth(self.handle) != startup["process_birth"]
                    or Path(self.fact["ExecutablePath"]).resolve() not in {Path(expected_args[0]).resolve(), Path(base_executable).resolve()}
                    or _argv(self.fact["CommandLine"])[1:] != expected_args[1:]
                    or (self.fact["ProcessId"] != wrapper_pid and self.fact["ParentProcessId"] != wrapper_pid)):
                raise ValueError("Own worker generation/executable/argv/parent differs")
        except BaseException:
            self.close()
            raise

    def request_stop(self, private):
        # No start-lease/expiry check: closing this exact owned instance is allowed.
        private = Path(private)
        if _birth(self.handle) != self.startup["process_birth"] or _fact(self.startup["pid"]) != self.fact:
            raise ValueError("Owned worker identity changed before cleanup")
        identity = private_json(private / "native35-instance.private.json")
        for key in ("pid", "process_birth", "generation", "source_commit"):
            if identity[key] != self.startup[key]:
                raise ValueError("Owned metadata generation changed")
        packet = {"action": "stop", "pid": identity["pid"], "generation": identity["generation"],
                  "source_commit": identity["source_commit"]}
        pending, target = private / "stop-request.pending.private.json", private / "stop-request.private.json"
        if target.exists():
            raise ValueError("Own stop request already exists")
        with pending.open("xb") as stream:
            stream.write((json.dumps(packet) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        pending.rename(target)

    def close(self):
        if self.handle:
            _api().CloseHandle(self.handle)
            self.handle = None
