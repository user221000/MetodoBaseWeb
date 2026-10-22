"""Finite27-case PG contract. Plan/ACK validation is pure and never connects."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path('E:/MetodoBaseWorkspace')
MODULE = 'tests/integration_billing13_legacy_apply37_postgres.py'
SCOPE = 'actual37-pg-b13-r07-27-exclusive-v1'
PLAN = 'tests/billing13_legacy_apply37_pg_plan.json'
NEW_PATHS = (MODULE, 'tests/billing13_legacy_apply37_pg_fixtures.py',
    'tests/billing13_legacy_apply37_pg_contract.py', 'tests/billing13_legacy_apply37_pg_offline.py',
    PLAN, 'tests/ci_web37/run_postgres_b13_r07.py')
BOUND_PATHS = (
    'conftest.py', 'db_bootstrap.py', 'tests/run_isolated.py', 'tests/isolation.py',
    'tests/account_security37_owned.py', 'tests/account37_qa_pg_fixtures.py',
    'tests/integration_provider_subjects.py', 'tests/integration_schema_migrations.py',
    'tests/test_billing_reconciliation13.py', 'tests/test_billing_reconciliation13_cli.py',
    'tests/test_billing_reconciliation13_selection_peer.py', 'tests/test_billing_reconciliation13_session_peer.py',
    'tests/test_security_b13_cli_privacy_peer.py', 'tests/test_security_b13_boundaries_peer.py',
    'tests/test_legacy_object_apply.py', 'tests/test_legacy_object_apply_source.py', 'tests/test_legacy_object_apply_peer.py',
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


def generation(path):
    value = json.loads(Path(path).read_bytes())
    if (set(value) != {'postmaster_pid', 'master_creation_filetime_100ns', 'postmaster_start_UTC'}
            or type(value['postmaster_pid']) is not int or value['postmaster_pid'] <= 0
            or type(value['master_creation_filetime_100ns']) is not int or value['master_creation_filetime_100ns'] <= 0
            or datetime.fromisoformat(value['postmaster_start_UTC']).tzinfo is None):
        raise ValueError('A fresh exact Windows PG generation is required')
    return value


def build_contract(profile_path, generation_path, *, root=ROOT):
    from scripts.apply_legacy_objects import source_check
    from tests.ci_web37.pg_lease import profile
    from web.services.legacy_object_apply_boundary import verify
    paths = [Path(item).resolve(strict=True) for item in (profile_path, generation_path)]
    for path in paths:
        if not path.is_relative_to(WORKSPACE):
            raise ValueError('New PG profile and generation must stay in private E metadata')
        verify(path)
    config = profile(paths[0])
    if not Path(config['METODOBASE_TEST_PG_BIN']).resolve(strict=True).is_relative_to(WORKSPACE / 'tools'):
        raise ValueError('Use reviewed portable E PostgreSQL binaries')
    value = phase(root)
    head = source_check()['commit']  # Existing bounded Git authority neutralizes inherited GIT_*.
    return {'schema': SCOPE, 'source_commit': head, 'source_files': source_pins(root),
        'profile_path': str(paths[0]), 'profile_sha256': hashlib.sha256(paths[0].read_bytes()).hexdigest(),
        'generation_path': str(paths[1]), 'generation_sha256': hashlib.sha256(paths[1].read_bytes()).hexdigest(),
        'generation': generation(paths[1]), 'phase': value, 'server_port': 55483,
        'closure': 'planned_before_CREATE_exact_OID_normal_DROP_zero_sessions_fresh_absence'}


def require_ack(path, contract, *, now=None):
    path = Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(WORKSPACE):
        raise ValueError('A new source/profile/generation-bound E Root ACK is required')
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


def check_generation(contract, config, *, engine=None):
    expected = contract['generation']
    created, executable = windows_process_identity(expected['postmaster_pid'])
    if created != expected['master_creation_filetime_100ns'] or executable != Path(config['METODOBASE_TEST_PG_BIN']).resolve() / 'postgres.exe':
        raise ValueError('The approved PostgreSQL PID/birth/executable changed')
    if engine is None:
        import psycopg2
        with psycopg2.connect(config['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://', 'postgresql://', 1), connect_timeout=5) as db, db.cursor() as cursor:
            cursor.execute('SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')
            observed = cursor.fetchone()
    else:
        from sqlalchemy import text
        with engine.connect() as db:
            observed = db.execute(text('SELECT pg_postmaster_start_time(),inet_server_addr()::text,inet_server_port()')).one()
    if (observed[0] != datetime.fromisoformat(expected['postmaster_start_UTC'])
            or observed[1] not in {'127.0.0.1', '127.0.0.1/32'} or observed[2] != 55483):
        raise ValueError('The approved PostgreSQL server generation changed')
