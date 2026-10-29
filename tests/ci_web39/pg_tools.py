"""PG39 native libpq attribution; derived99f HANDLE/normalwait, no SQL on import."""
from __future__ import annotations

import ctypes
from ctypes import wintypes as W
from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit
import uuid
from contextlib import contextmanager
from unittest.mock import patch
from types import SimpleNamespace


def require(ok, message):
    if not ok:
        raise ValueError(message)


def native(process):
    """Use Popen's retained process handle, including after normal exit."""
    if sys.platform == 'linux':
        from tests.ci_web39.pg_tools_linux import native as linux_native
        return linux_native(process)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [ctypes.POINTER(W.FILETIME)] * 4
    kernel.GetProcessTimes.restype = W.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [
        W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = W.BOOL
    times = [W.FILETIME() for _ in range(4)]
    size, name = W.DWORD(32768), ctypes.create_unicode_buffer(32768)
    handle = W.HANDLE(int(process._handle))  # Original Popen handle, never reopen a PID.
    if (not kernel.GetProcessTimes(handle, *[ctypes.byref(row) for row in times])
            or not kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size))):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'pid': process.pid,
        'birth_filetime': (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime,
        'executable': str(Path(name.value).resolve(strict=True))}


def confirm_closed(process, identity):
    """Corroborate normal closure on the original HANDLE; image was attested live.

    Never reopen a PID, query an exited image, poll, wait again or signal. The
    executable string in the proof is explicitly the earlier live attestation.
    """
    if sys.platform == 'linux':
        from tests.ci_web39.pg_tools_linux import confirm_closed as linux_closed
        return linux_closed(process, identity)
    require(type(identity) is dict and set(identity) == {'pid', 'birth_filetime', 'executable'}
            and type(identity['pid']) is int and identity['pid'] > 0
            and type(identity['birth_filetime']) is int and identity['birth_filetime'] > 0
            and type(identity['executable']) is str and bool(identity['executable'])
            and type(process.pid) is int and process.pid == identity['pid'],
            'Exact original live Popen identity required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    kernel.WaitForSingleObject.restype = W.DWORD
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [ctypes.POINTER(W.FILETIME)] * 4
    kernel.GetProcessTimes.restype = W.BOOL
    kernel.GetProcessId.argtypes = [W.HANDLE]
    kernel.GetProcessId.restype = W.DWORD
    kernel.GetExitCodeProcess.argtypes = [W.HANDLE, ctypes.POINTER(W.DWORD)]
    kernel.GetExitCodeProcess.restype = W.BOOL
    handle = W.HANDLE(int(process._handle))  # SAME retained Popen HANDLE, no OpenProcess.
    status = kernel.WaitForSingleObject(handle, 0)
    if status == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    require(status == 0, 'Original Popen HANDLE is not signalled closed')
    times = [W.FILETIME() for _ in range(4)]
    exit_code = W.DWORD()
    if (not kernel.GetProcessTimes(handle, *[ctypes.byref(row) for row in times])
            or not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))):
        raise ctypes.WinError(ctypes.get_last_error())
    pid = kernel.GetProcessId(handle)
    if pid == 0:
        raise ctypes.WinError(ctypes.get_last_error())
    birth = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    require(pid == process.pid == identity['pid'], 'Original closed Popen PID differs')
    require(birth == identity['birth_filetime'], 'Original closed Popen birth differs')
    require(type(process.returncode) is int and exit_code.value == process.returncode,
            'Original closed Popen exit code differs from normal wait')
    return {'schema': 'owned-Popen-original-HANDLE-closure-v1', 'pid': pid,
            'birth_filetime': birth, 'exit_code': exit_code.value,
            'original_HANDLE_signalled': True,
            'executable_attested_while_alive': identity['executable'],
            'post_exit_image_query_performed': False}


def current_native():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = W.HANDLE
    import os
    return native(SimpleNamespace(pid=os.getpid(), _handle=kernel.GetCurrentProcess()))


def normal_wait_owned(process, *, waiter=None):
    """One ordinary wait. On uncertainty keep this stack/handle/FD owners alive.

    No process restart, signal or Popen.wait retry. Native waiting on the SAME
    retained original handle prevents unwinding a log/monitor context while a
    child can still write. A Python wait error is raised only AFTER the native
    object is signalled. If that cannot be established, this frame stays alive
    for Root review; it never manufactures normal closure.
    """
    try:
        return (waiter or process.wait)()
    except BaseException as first:
        try:
            print('Owned child wait uncertain; handles and private writers retained; no signals.',
                  file=sys.stderr, flush=True)
        except BaseException:
            pass
        while True:
            status = None
            try:
                if sys.platform == 'linux':
                    from tests.ci_web39.pg_tools_linux import signalled
                    status = 0 if signalled(process, 1000) else None
                else:
                    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
                    kernel.WaitForSingleObject.restype = W.DWORD
                    status = kernel.WaitForSingleObject(W.HANDLE(int(process._handle)), 1000)
            except BaseException:
                pass
            if status == 0:  # Native HANDLE signalled, not a PID-name absence.
                raise first
            try:
                time.sleep(0.1)
            except BaseException:
                pass


@contextmanager
def observe_tools(contract, config, database, phase, fresh, admit, write, before_tools):
    """Actual Popen, finite catalogue observations and natural attributed drain.

    fresh() rechecks authority and the approved server generation. No connection
    is called observed merely because the child existed. This seam never
    terminates a backend or process and does not change _pg_run's timeout policy.
    """
    import psycopg2
    original = subprocess.Popen
    suffix = '.exe' if os.name == 'nt' else ''
    expected_order = ['pg_dump' + suffix, 'pg_restore' + suffix] if phase == 'source' else ['pg_restore' + suffix]
    tools = []
    current = None
    owner = unquote(urlsplit(config['METODOBASE_TEST_MIGRATOR_URL']).username)
    pg_bin = Path(config['METODOBASE_TEST_PG_BIN'])
    connection = psycopg2.connect(
        config['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://', 'postgresql://', 1),
        connect_timeout=5, options='-c statement_timeout=250ms -c lock_timeout=250ms')
    try:
        connection.autocommit = True
    except BaseException:
        connection.close()
        raise

    def catalogue(row, *, permit_new):
        # This control connection is in the separate profile database.
        with connection.cursor() as cursor:
            fresh(cursor)  # Same monitor connection, no fourth connection while a tool runs.
            cursor.execute('SELECT pid,usename,client_addr::text,backend_start,application_name '
                           'FROM pg_stat_activity WHERE datname=%s ORDER BY pid', (database,))
            values = cursor.fetchall()
        seen = {item['pid']: item for item in row['backends']}
        require(len(values) <= 1, 'The single PG tool connection budget was exceeded')
        for pid, role, address, started, label in values:
            require(type(pid) is int and pid > 0 and role == owner
                    and address in {'127.0.0.1', '127.0.0.1/32'} and label == row['application_name']
                    and started.tzinfo is not None
                    and datetime.fromisoformat(row['window_started_UTC']) <= started <= datetime.now(UTC),
                    'Unattributed or foreign owned-DB client')
            identity = {'pid': pid, 'role': role, 'client_addr': address,
                        'backend_start': started.isoformat()}
            if pid in seen:
                require(seen[pid] == identity, 'Attributed backend identity changed')
            else:
                require(permit_new, 'A new backend appeared after the tool exited')
                # Statement is observed during this exact Popen window, not inferred.
                row['backends'].append(identity)
        return values

    class Tracked(original):
        def __init__(self, args, **kwargs):
            nonlocal current
            admit()  # Expiry gates a NEW tool, never replaces its owned close.
            require(current is None and len(tools) < len(expected_order), 'Unexpected concurrent PG tool')
            require(isinstance(args, list) and all(isinstance(item, str) for item in args),
                    'Exact PG tool argv required')
            executable = Path(args[0])
            expected_name = expected_order[len(tools)]
            require(executable == pg_bin / expected_name
                    and hashlib.sha256(executable.read_bytes()).hexdigest()
                    == contract['PG_tools'][expected_name], 'Unreviewed PG tool executable')
            expected_prefix = ['--format=custom', '--no-owner', '--no-acl', '--file'] if expected_name == 'pg_dump' + suffix else (
                ['--list'] if phase == 'source' else ['--exit-on-error', '--single-transaction', '--no-owner', '--no-acl', '--dbname'])
            require(args[1:1 + len(expected_prefix)] == expected_prefix,
                    'The actual product PG argv changed')
            require(len(args) == len(expected_prefix) + (3 if phase == 'target' else 2)
                    and Path(args[-1]).is_absolute()
                    and Path(args[-1]).is_relative_to(Path(contract['scratch_root']))
                    and (phase != 'target' or args[-2] == database),
                    'Exact PG arguments and private plaintext path required')
            env = dict(kwargs['env'])
            require(env['PGDATABASE'] == database and env['PGPORT'] == '55483'
                    and env['PGHOST'] in {'127.0.0.1', 'localhost'} and env['PGUSER'] == owner,
                    'PG child connection binding differs')
            require(not any('://' in item for item in args), 'A URL must never enter PG argv')
            if os.name == 'nt':
                require(kwargs.get('creationflags', 0) & subprocess.CREATE_NO_WINDOW,
                        'Actual PG child must be explicitly hidden')
            else:
                from tests.ci_web39.pg_tools_linux import require_direct_spawn
                require_direct_spawn(kwargs)
            require(all(kwargs.get(name) == subprocess.DEVNULL for name in ('stdin', 'stdout', 'stderr')),
                    'Product PG subprocess streams must remain DEVNULL')
            row = {'application_name': 'mbbackup_' + uuid.uuid4().hex, 'argv': args,
                   'window_started_UTC': datetime.now(UTC).isoformat(),
                   'backends': [], 'normally_waited': False, 'fresh_absent_after_wait': False}
            # Before launch the entire owned DB must have no clients.
            require(not catalogue(row, permit_new=False), 'Owned DB is not empty before PG tool')
            env['PGAPPNAME'] = row['application_name']
            kwargs['env'] = env
            super().__init__(args, **kwargs)
            self.row = row
            row['created_pid'] = self.pid
            tools.append(self)
            current = self
            try:
                row['process'] = native(self)
                require(Path(row['process']['executable']) == executable, 'Spawned PG image differs')
                row['executable_sha256'] = contract['PG_tools'][expected_name]
            except BaseException as first:
                row['post_launch_error_type'] = type(first).__name__
                try:
                    row['post_launch_exit_code'] = normal_wait_owned(
                        self, waiter=lambda: original.wait(self, timeout=300))
                except BaseException as wait_error:
                    # normal_wait_owned unwinds only after native closure.
                    row['post_launch_wait_error_type'] = type(wait_error).__name__
                row['post_launch_closed_after_error'] = True
                current = None
                raise first

        def __exit__(self, *error):
            first = None
            try:
                return super().__exit__(*error)
            except BaseException as failure:
                first = failure
                self.row['context_exit_error_type'] = type(failure).__name__
                raise
            finally:
                # A catalogue/identity failure in overridden wait must not let
                # subprocess.run unwind while this exact created tool is alive.
                try:
                    normal_wait_owned(self, waiter=lambda: original.wait(self, timeout=300))
                except BaseException as close_error:
                    self.row['context_close_error_type'] = type(close_error).__name__
                    if first is None:
                        raise

        def wait(self, timeout=None):
            nonlocal current
            if self.row['normally_waited']:
                return super().wait(timeout=timeout)
            if self.row.get('timeout_seconds') is not None:
                # subprocess.run's EXISTING timeout path may kill and then call
                # communicate/wait again. Preserve that first timeout, do not
                # replace it with an observer exit-code error or claim normal.
                result = super().wait(timeout=timeout)
                self.row['exit_code_after_product_timeout'] = result
                return result
            started = time.monotonic()
            while self.poll() is None:
                catalogue(self.row, permit_new=True)
                if timeout is not None and time.monotonic() - started >= timeout:
                    self.row['timeout_seconds'] = timeout
                    raise subprocess.TimeoutExpired(self.args, timeout)
                time.sleep(0.025)
            remaining = None if timeout is None else max(0, timeout - (time.monotonic() - started))
            result = super().wait(timeout=remaining)  # Actual Popen wait; no signal.
            self.row['exit_code'] = result
            self.row['closed_process'] = confirm_closed(self, self.row['process'])
            self.row['normally_waited'] = True
            self.row['normal_wait_UTC'] = datetime.now(UTC).isoformat()
            deadline = time.monotonic() + 2.0
            while True:
                require(time.monotonic() < deadline, 'Attributed PG drain deadline expired before query')
                active = catalogue(self.row, permit_new=False)
                require(time.monotonic() < deadline, 'Attributed PG drain deadline expired after query')
                if not active:
                    self.row['fresh_absent_after_wait'] = True
                    break
                time.sleep(0.025)
            self.row['connection_observed'] = bool(self.row['backends'])
            current = None
            return result

    def popen(args, *positional, **kwargs):
        # The PG39 window has no Git/source subprocess; only the exact PG tools.
        require(not positional, 'Unexpected positional PG launch parameters')
        return Tracked(args, **kwargs)

    try:
        # One native-first monitor, same-cursor generation/OID/owner BEFORE
        # the adapter may dispose any of its own idle Pools.
        with connection.cursor() as cursor:
            fresh(cursor)
            before_tools()
        with patch.object(subprocess, 'Popen', popen):
            yield
        require(current is None and len(tools) == len(expected_order)
                and all(item.row['normally_waited'] and item.row['exit_code'] == 0
                        and item.row['fresh_absent_after_wait'] for item in tools),
                'PG tools did not finish with exact normal closure')
    finally:
        # Private diagnostic survives failure; no claim of success from its existence.
        try:
            write({'phase': phase, 'tools': [item.row for item in tools],
                   'no_process_or_backend_termination_by_observer': True})
        finally:
            try:
                connection.close()
            finally:
                if sys.platform == 'linux':
                    from tests.ci_web39.pg_tools_linux import release
                    for tool in tools:
                        release(tool)

# Reviewed against the CLOSED restore38 environment-before snapshot, not autopins.
PG_TOOLS = {
    'pg_dump.exe': 'e856d19e6b73f351069d2d3d9f442e8c0371bebfc53c7e55b455adfc0b8ee14b',
    'pg_restore.exe': 'c85a472c22c4eb657f76e70a87b55e2070474cd0042bcb87b50a787d085d950c',
}


@contextmanager
def observe_restore_tools(runtime, url, admin, app, phase, scratch):
    """Before common-close: idle own Pools, actual libpq attribution and drain.

    No backup implementation is patched. Only its real subprocess.Popen is
    observed for this exact window. No PID is invented/adopted, no signal.
    """
    import json
    import os
    from tests.ci_web39 import pg_contract
    from tests.ci_web39.pg_fixtures import record
    from tests.billing13_legacy_apply37_pg_contract import (
        check_generation, windows_process_identity, pg_binary_directory)
    require(sys.platform in {'win32', 'linux'} and phase in {'source', 'target'}
            and runtime.name == 'restore', 'This finite native PG39 tool window requires Windows or Linux')
    current_contract, config = pg_contract.checked_runtime('restore')
    require(current_contract == runtime.contract and config == runtime.profile,
            'PG39 tool source/profile/Root authority differs')
    selected = runtime.contract['phase']
    require(selected['UUIDs'] == 2 and selected['concurrent_UUIDs'] == 1
            and selected['application_pool'] == selected['admin_observer_pool'] == 1
            and selected['max_overflow'] == 0, 'PG39 restore resource budget differs')
    parsed = urlsplit(url)
    database = parsed.path.lstrip('/')
    namespace = Path(os.environ['ACCOUNT37_PRIVATE_LEASES']).resolve(strict=True)
    plan_id = database.removeprefix('metodobase_test_account37_')
    require(len(plan_id) == 32 and all(c in '0123456789abcdef' for c in plan_id)
            and database == 'metodobase_test_account37_' + plan_id,
            'An exact existing owned UUID is required')
    lease_path = namespace / ('lease-' + plan_id + '.json')
    lease_raw = lease_path.read_bytes()
    lease = json.loads(lease_raw)
    owner = unquote(urlsplit(config['METODOBASE_TEST_MIGRATOR_URL']).username)
    require(lease['plan_id'] == plan_id and lease['database'] == database
            and lease['state'] == 'created' and type(lease['oid']) is int and lease['oid'] > 0
            and lease['expected_owner'] == owner, 'The original created lease differs')
    scratch = Path(scratch).resolve(strict=True)
    task = Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR']).resolve(strict=True).parent
    require(scratch.is_relative_to(task) and scratch.is_absolute(),
            'PG plaintext scratch must stay under this isolated private Task')
    engines = [admin] + ([app] if app is not None else [])
    require(len({id(engine) for engine in engines}) == len(engines), 'A pool was duplicated')
    pools_before = []
    for engine in engines:
        require(engine.url.database == database and engine.url.host in {'localhost', '127.0.0.1'}
                and engine.url.port == 55483, 'A PG tool window cannot dispose a foreign engine')
        out = engine.pool.checkedout()
        require(type(out) is int and out == 0 and engine.pool.size() == 1
                and engine.pool._max_overflow == 0, 'Only the idle own 1/0 Pools may be disposed')
        pools_before.append({'checked_out': out, 'size': engine.pool.size(), 'max_overflow': engine.pool._max_overflow})
    # Use the ACTUAL admitted e905 ledger; do not infer returned loans from a
    # reset current Pool counter, and do not duplicate its lifecycle algorithm.
    from tests.ci_web37 import pg_close
    observer = pg_close._OBSERVER
    current_lease = None if observer is None else observer.leases.get(database)
    require(current_lease is not None and current_lease.verified
            and current_lease.receipt == lease_path and current_lease.initial_raw == lease_raw,
            'The exact active common-close lease/ledger is required')
    ledger = current_lease.ledger
    def dispose_idle():
        # Invoked only after fresh() on the one monitor's own cursor.
        ledger.no_loans()
        for engine in engines:
            require(ledger.pools.get(id(engine.pool)) is engine.pool, 'Own current Pool is not in the lease ledger')
            ledger.no_loans()
            engine.dispose()  # Original e905 hook records this idle disposal.
        ledger.no_loans()
        ledger.no_open_dbapi()

    def process():
        expected = runtime.contract['generation']
        if sys.platform == 'linux':
            from tests.billing13_legacy_apply37_pg_contract import linux_process_identity
            pg_binary_directory(config)
            linux_process_identity(expected)
        else:
            created, executable = windows_process_identity(expected['postmaster_pid'])
            require(created == expected['master_creation_filetime_100ns']
                    and executable == pg_binary_directory(config) / 'postgres.exe',
                    'The approved PG39 PID/birth/executable changed')

    def fresh(cursor):
        check_generation(runtime.contract, config, cursor=cursor)  # Same monitor connection.
        require(lease_path.read_bytes() == lease_raw, 'Original lease changed during PG tool')
        cursor.execute('SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', (database,))
        require(cursor.fetchone() == (lease['oid'], owner), 'Owned PG tool OID/owner changed')

    def admit():
        value, profile = pg_contract.checked_runtime('restore')
        require(value == runtime.contract and profile == config, 'Root/source authority changed before PG tool')
        process()

    def write(value):
        record('pg39-restore-' + phase + '-tools.json',
               dict(value, schema='pg39-native-tools-observation-v1', plan_id=plan_id,
                    original_lease_SHA256=hashlib.sha256(lease_raw).hexdigest(),
                    original_oid=lease['oid'], own_idle_pools_before=pools_before,
                    FileSetDigest=runtime.contract['FileSetDigest']))

    process()  # Native-first before creating the explicit monitor connection.
    tools = PG_TOOLS
    if sys.platform == 'linux':
        from tests.ci_web39.pg_tools_linux import tool_hashes
        tools = runtime.contract['Linux_PG_tools']
        require(tool_hashes(pg_binary_directory(config)) == tools,
                'Linux39 client package/binary binding changed after admission')
    tool_contract = {'PG_tools': tools, 'scratch_root': str(scratch)}
    with observe_tools(tool_contract, config, database, phase, fresh, admit, write, dispose_idle):
        yield
    value, profile = pg_contract.checked_runtime('restore')
    require(value == runtime.contract and profile == config, 'PG39 source changed during tool window')
