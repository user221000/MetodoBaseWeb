"""Finite27-case PG contract. Plan/ACK validation is pure and never connects."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path('E:/MetodoBaseWorkspace')
MODULE = 'tests/integration_billing13_legacy_apply37_postgres.py'
SCOPE = 'actual37-pg-b13-r07-27-exclusive-v1'
PLAN = 'tests/billing13_legacy_apply37_pg_plan.json'
NEW_PATHS = (MODULE, 'tests/billing13_legacy_apply37_pg_fixtures.py',
    'tests/billing13_legacy_apply37_pg_contract.py', 'tests/billing13_legacy_apply37_pg_offline.py',
    'tests/billing13_legacy_apply37_pg_generation.py', 'tests/billing13_legacy_apply37_ci_offline.py',
    PLAN, 'tests/ci_web37/run_postgres_b13_r07.py')
BOUND_PATHS = (
    '.github/workflows/ci.yml',
    'conftest.py', 'db_bootstrap.py', 'tests/run_isolated.py', 'tests/isolation.py',
    'tests/account_security37_owned.py', 'tests/account37_qa_pg_fixtures.py',
    'tests/integration_provider_subjects.py', 'tests/integration_schema_migrations.py',
    'tests/test_billing_reconciliation13.py', 'tests/test_billing_reconciliation13_cli.py',
    'tests/test_billing_reconciliation13_selection_peer.py', 'tests/test_billing_reconciliation13_session_peer.py',
    'tests/test_security_b13_cli_privacy_peer.py', 'tests/test_security_b13_boundaries_peer.py',
    'tests/test_legacy_object_apply.py', 'tests/test_legacy_object_apply_source.py', 'tests/test_legacy_object_apply_peer.py',
    'tests/ci_web37/pg_close.py',
    'tests/ci_web37/pg_lease.py', 'tests/ci_web37/pg53.py', 'tests/ci_web37/run_postgres.py',
    'tests/ci_web37/reports.py', 'tests/ci_web37/scope.py', 'tests/ci_web37/evidence.py',
    'tests/ci_web37/pg_plan.py', 'tests/ci_web37/pg-legacy37.json', 'tests/ci_web37/pg-current37-nodeids.json',
    'tests/ci_web37/pg-r30-ppl53.json', 'tests/integration_r30_ppl37_postgres.py',
    'tests/ci_web37/run_web.py', 'tests/ci_google33/publish.py', 'scripts/scan_secrets.py',
    'web/billing_reconciliation_cli.py', 'web/services/billing_reconciliation.py',
    'web/services/billing_reconciliation_providers.py', 'web/services/stripe_service.py',
    'web/services/mercadopago_service.py', 'web/services/billing_integrity.py',
    'web/services/subscription_service.py', 'web/services/provider_subjects.py',
    'web/services/resilience.py', 'web/constants.py', 'web/settings.py', 'core/plan_catalog.py',
    'tests/account_security37_fixtures.py', 'web/services/legacy_object_apply.py',
    'web/services/legacy_object_apply_boundary.py', 'web/services/legacy_object_inventory.py',
    'web/services/gym_logos.py', 'web/database/models.py', 'web/database/tenant_context.py',
    'web/database/tenant_policy.py', 'web/database/schema_control.py',
    'web/storage/objects.py', 'web/storage/local.py', 'web/storage/s3.py', 'web/storage/configuration.py',
    'scripts/apply_legacy_objects.py', 'scripts/inventory_legacy_objects.py',
)


def private_workspace():
    """Local E, or the exact existing non-root Actions checkout's private TEMP."""
    if os.name == 'nt':
        return WORKSPACE
    if (os.name != 'posix' or os.environ.get('GITHUB_ACTIONS') != 'true' or os.geteuid() == 0
            or Path(os.environ['GITHUB_WORKSPACE']).resolve(strict=True) != ROOT):
        raise ValueError('PG27 Linux requires the exact non-root Actions checkout')
    raw = Path(os.environ['RUNNER_TEMP'])
    temporary = raw.resolve(strict=True)
    if (not raw.is_absolute() or raw != temporary or any(part.is_symlink() for part in (raw, *raw.parents))
            or temporary == ROOT or temporary.is_relative_to(ROOT) or ROOT.is_relative_to(temporary)
            or any(Path(os.environ[key]).resolve(strict=True) != temporary for key in ('TEMP', 'TMP', 'TMPDIR'))
            or Path(tempfile.gettempdir()).resolve(strict=True) != temporary):
        raise ValueError('PG27 Linux TEMP boundary differs from RUNNER_TEMP')
    return temporary


def temporary_root():
    root = private_workspace()
    return root / 'tmp' if os.name == 'nt' else root


def pg_binary_directory(config):
    observed = Path(config['METODOBASE_TEST_PG_BIN']).resolve(strict=True)
    if os.name == 'nt':
        if not observed.is_relative_to(private_workspace() / 'tools'):
            raise ValueError('Use reviewed portable E PostgreSQL binaries')
    elif observed != Path('/usr/lib/postgresql/17/bin'):
        raise ValueError('Use only the existing CI PG17 binary directory')
    return observed


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def ast_nodeids(root=ROOT):
    """Explicit functions/parameter labels only; imports and pytest never run."""
    rows = []
    for node in ast.parse((root / MODULE).read_bytes()).body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith('test_'):
            continue
        labels = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == 'parametrize':
                if labels is not None:
                    raise ValueError('This finite plan supports one explicit parametrize per case')
                labels = ast.literal_eval(next(item.value for item in decorator.keywords if item.arg == 'ids'))
        rows.extend([MODULE + '::' + node.name + ('[' + label + ']' if label is not None else '')
                     for label in (labels if labels is not None else [None])])
    if len(rows) != 27 or len(set(rows)) != 27:
        raise ValueError('The finite new PG27 identities differ')
    return rows


def phase(root=ROOT):
    value = json.loads((root / PLAN).read_bytes())
    numeric = ('cases', 'UUIDs', 'concurrent_UUIDs', 'restricted_application_pool_size', 'max_overflow',
               'historical429_UUID_budget_unchanged', 'historical53_UUID_budget_unchanged')
    if (any(type(value[key]) is not int for key in numeric)
            or value['schema'] != SCOPE or value['module'] != MODULE or value['cases'] != 27
            or value['UUIDs'] != 1 or value['concurrent_UUIDs'] != 1 or value['restricted_application_pool_size'] != 1
            or value['max_overflow'] != 0 or value['historical429_UUID_budget_unchanged'] != 69
            or value['historical53_UUID_budget_unchanged'] != 1 or value['nodeids'] != ast_nodeids(root)):
        raise ValueError('The separate PG27 case/source/UUID contract differs')
    return value


def source_pins(root=ROOT):
    paths = {*NEW_PATHS, *BOUND_PATHS}
    # Pin the authentic migration/target closure; do not retarget historical targets.
    for path in (root / 'web/database/alembic').rglob('*'):
        if path.is_file() and path.suffix in {'.py', '.json', '.sql'}:
            paths.add(path.relative_to(root).as_posix())
    paths.update(path.relative_to(root).as_posix() for path in (root / 'web/database').glob('*.py'))
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sorted(paths)}


def require_executed_summary(value):
    if (value.get('accepted') is not True or value.get('PostgreSQL_executed') is not True
            or value.get('scope') != 'separate_current37_PG27' or value.get('selected_sources_quiet') is not True
            or value.get('source_packages_binaries_quiet') is not True or value.get('PG_binaries_sources_packages_roles_quiet') is not True
            or type(value.get('case_count')) is not int or value['case_count'] != 27
            or type(value.get('normally_closed_UUIDs_fresh_absent')) is not int or value['normally_closed_UUIDs_fresh_absent'] != 1
            or type(value.get('pytest_exit')) is not int or value['pytest_exit'] != 0
            or type(value.get('pip_before')) is not int or value['pip_before'] != 0
            or type(value.get('pip_after')) is not int or value['pip_after'] != 0):
        raise ValueError('A real successful PG27 phase with its one normally closed UUID is required')


def generation(path):
    return validated_generation(json.loads(Path(path).read_bytes()))


def validated_generation(value):
    if (type(value.get('postmaster_pid')) is not int or value['postmaster_pid'] <= 0
            or datetime.fromisoformat(value['postmaster_start_UTC']).tzinfo is None):
        raise ValueError('A fresh exact PG generation is required')
    if os.name == 'nt':
        if (set(value) != {'postmaster_pid', 'master_creation_filetime_100ns', 'postmaster_start_UTC'}
                or type(value['master_creation_filetime_100ns']) is not int or value['master_creation_filetime_100ns'] <= 0):
            raise ValueError('A fresh exact Windows PG generation is required')
    elif (set(value) != {'schema', 'postmaster_pid', 'start_ticks', 'boot_id', 'postmaster_start_UTC', 'postmaster_pidfile_sha256', 'data'}
            or value['schema'] != 'linux-ci-v1' or type(value['start_ticks']) is not int or value['start_ticks'] <= 0
            or not re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value['boot_id'])
            or not re.fullmatch('[0-9a-f]{64}', value['postmaster_pidfile_sha256'])
            or Path(value['data']) != private_workspace() / 'ci37-pg-cluster-private/data'):
        raise ValueError('A fresh exact Linux CI PG generation is required')
    return value


def ci_generation(identity, postmaster_start_UTC):
    private_workspace()
    if os.name != 'posix' or identity['source_commit'] != os.environ['GITHUB_SHA'] or identity['port'] != 55483:
        raise ValueError('Existing CI-only source/cluster identity required')
    value = {'schema': 'linux-ci-v1', 'postmaster_pid': identity['pid'], 'start_ticks': identity['start_ticks'],
        'boot_id': identity['boot_id'], 'postmaster_start_UTC': postmaster_start_UTC,
        'postmaster_pidfile_sha256': identity['postmaster_pidfile_sha256'], 'data': identity['data']}
    validated_generation(value)
    linux_process_identity(value)
    return value


def build_contract(profile_path, generation_path, *, root=ROOT):
    from scripts.apply_legacy_objects import source_check
    from tests.ci_web37.pg_lease import profile
    from web.services.legacy_object_apply_boundary import verify
    paths = [Path(item).resolve(strict=True) for item in (profile_path, generation_path)]
    for path in paths:
        if not path.is_relative_to(private_workspace()):
            raise ValueError('New profile/generation must stay in the exact private execution workspace')
        verify(path)
    config = profile(paths[0])
    pg_binary_directory(config)
    value = phase(root)
    head = source_check()['commit']  # Existing bounded Git authority neutralizes inherited GIT_*.
    return {'schema': SCOPE, 'source_commit': head, 'source_files': source_pins(root),
        'profile_path': str(paths[0]), 'profile_sha256': hashlib.sha256(paths[0].read_bytes()).hexdigest(),
        'generation_path': str(paths[1]), 'generation_sha256': hashlib.sha256(paths[1].read_bytes()).hexdigest(),
        'generation': generation(paths[1]), 'phase': value, 'server_port': 55483,
        'closure': 'planned_before_CREATE_exact_OID_normal_DROP_zero_sessions_fresh_absence'}


def require_ack(path, contract, *, now=None):
    path = Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(private_workspace()):
        raise ValueError('A new source/profile/generation-bound private Root/CI ACK is required')
    raw = path.read_bytes()
    ack = json.loads(raw)
    if (set(ack) != {'approved', 'scope', 'contract_sha256', 'expires_at_UTC'} or ack['approved'] is not True
            or ack['scope'] != SCOPE or contract.get('schema') != SCOPE or ack['contract_sha256'] != digest(contract)):
        raise ValueError('The new PG27 Root ACK binding differs')
    expiry = datetime.fromisoformat(ack['expires_at_UTC'])
    if expiry.tzinfo is None or not 0 < (expiry - (now or datetime.now(UTC))).total_seconds() <= 8 * 3600:
        raise ValueError('The new PG27 Root ACK is expired or exceeds eight hours')
    return hashlib.sha256(raw).hexdigest()


def checked_runtime():
    from tests.ci_web37.pg_lease import profile
    from web.services.legacy_object_apply_boundary import verify
    value = build_contract(os.environ['B13_R07_PG_PROFILE'], os.environ['B13_R07_PG_GENERATION'])
    ack = Path(os.environ['B13_R07_PG_ACK'])
    verify(ack)
    require_ack(ack, value)
    return value, profile(value['profile_path'], expected_sha256=value['profile_sha256'])


def windows_process_identity(pid):
    """PID plus creation and canonical executable, before any SQL; metadata only."""
    import ctypes
    from ctypes import wintypes
    if os.name != 'nt':
        raise ValueError('This prepared generation guard is Windows-only')
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    api.GetProcessTimes.restype = wintypes.BOOL
    api.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.QueryFullProcessImageNameW.restype = wintypes.BOOL
    handle = api.OpenProcess(0x1000, False, pid)
    if not handle:
        raise ValueError('The approved PostgreSQL process is absent or inaccessible')
    try:
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        size = wintypes.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        if not api.GetProcessTimes(handle, created, exited, kernel, user) or not api.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            raise ValueError('The approved PostgreSQL process cannot be verified')
        return ((created.dwHighDateTime << 32) | created.dwLowDateTime), Path(name.value).resolve(strict=True)
    finally:
        api.CloseHandle(handle)


def linux_process_identity(expected):
    """Read only metadata of the already-owned CI cluster; never discover a PID."""
    root = private_workspace()
    if (os.name != 'posix' or expected.get('schema') != 'linux-ci-v1'
            or type(expected.get('postmaster_pid')) is not int or expected['postmaster_pid'] <= 0
            or type(expected.get('start_ticks')) is not int or expected['start_ticks'] <= 0
            or Path(expected['data']) != root / 'ci37-pg-cluster-private/data'):
        raise ValueError('The approved Linux cluster namespace differs')
    pid = expected['postmaster_pid']
    rawstat = Path('/proc/' + str(pid) + '/stat').read_text(encoding='ascii')
    if (int(rawstat.split(' ', 1)[0]) != pid or int(rawstat[rawstat.rindex(')') + 2:].split()[19]) != expected['start_ticks']
            or Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip() != expected['boot_id']
            or Path('/proc/' + str(pid) + '/exe').resolve(strict=True) != Path('/usr/lib/postgresql/17/bin/postgres')):
        raise ValueError('The approved Linux PID/birth/boot/executable changed')
    data = Path(expected['data'])
    if any(part.is_symlink() for part in (data, *data.parents)):
        raise ValueError('The approved CI data path became an alias')
    pidfile = data / 'postmaster.pid'
    if pidfile.is_symlink() or not pidfile.is_file():
        raise ValueError('The approved CI pidfile is not a regular owned entry')
    raw = pidfile.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected['postmaster_pidfile_sha256'] or int(raw.splitlines()[0]) != pid:
        raise ValueError('The approved CI pidfile identity changed')


def check_generation(contract, config, *, engine=None, cursor=None):
    expected = contract['generation']
    def process():
        if os.name == 'nt':
            created, executable = windows_process_identity(expected['postmaster_pid'])
            if created != expected['master_creation_filetime_100ns'] or executable != pg_binary_directory(config) / 'postgres.exe':
                raise ValueError('The approved PostgreSQL PID/birth/executable changed')
        else:
            pg_binary_directory(config)
            linux_process_identity(expected)
    process()
    if cursor is not None:
        cursor.execute('SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')
        observed = cursor.fetchone()
    elif engine is None:
        import psycopg2
        with psycopg2.connect(config['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://', 'postgresql://', 1), connect_timeout=5) as db, db.cursor() as control:
            control.execute('SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')
            observed = control.fetchone()
    else:
        from sqlalchemy import text
        with engine.connect() as db:
            observed = db.execute(text('SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')).one()
    if (observed[0] != datetime.fromisoformat(expected['postmaster_start_UTC'])
            or observed[1] not in {'127.0.0.1', '127.0.0.1/32'} or observed[2] != 55483):
        raise ValueError('The approved PostgreSQL server generation changed')
    process()  # Same-connection metadata recheck before CREATE, never derive UTC from ticks.
