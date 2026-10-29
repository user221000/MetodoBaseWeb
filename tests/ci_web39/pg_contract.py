"""Separate39 FileSet/phase/RootACK; reuse approved37 identity and owner guards.

Import is stdlib-only. No HEAD is invented for uncommitted privacy39 bytes.
The Root execution window remains exclusive/no-restart. No authority is emitted.
"""
from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'privacy39-pg-exclusive-v1'
RUNTIME_ROOTS = ('web', 'api', 'core', 'config', 'utils', 'src', 'static', 'fonts')
BOUND = ('conftest.py', 'alembic.ini', 'db_bootstrap.py', 'tests/__init__.py',
    'tests/isolation.py', 'tests/run_isolated.py', 'tests/account_security37_owned.py',
    'tests/ci_web37/pg_close.py', 'tests/ci_web37/pg_lease.py',
    'tests/billing13_legacy_apply37_pg_contract.py', 'tests/integration_schema_migrations.py',
    'tests/integration_provider_subjects.py', 'tests/integration_client_link_services.py',
    'tests/integration_product38_concurrency.py', 'tests/followup34_http.py',
    'tests/mfa31_contract_client.py', 'tests/integration_stored_objects_migrations.py',
    'tests/ci_web37/physical.py', 'tests/test_new_password_policy.py',
    'tests/test_new_password_policy_http.py', 'tests/test_password_blocklist19.py',
    'tests/test_account_security37_http.py', 'tests/test_password_blocklist19_canary.py',
    'tests/account_security38_http.py', 'tests/account_security37_http.py',
    'tests/privacy39_fixtures.py', 'tests/account37_qa_restore_helpers.py',
    'tests/ci_web37/pg_plan.py', 'tests/ci_web37/pg-legacy37.json',
    'scripts/backup_restore.py', 'scripts/scan_secrets.py',
    'tests/privacy39_pg_actors.py', 'tests/account_security37_fixtures.py',
    'tests/account37_qa_pg_fixtures.py',
    'tests/ci_google33/owned.py',
    'tests/ci_web37/__init__.py',
    'tests/ci_web37/pg_legacy.py',
    'tests/ci_web37/pg_legacy_fixtures.py',
    'tests/ci_web37/pg_observer.py',
    'tests/ci_web37/pg_rls_seed.py',
    'tests/followup34_fixtures.py',
    'tests/followup34_owned.py',
    'tests/google33_fixtures.py',
    'tests/google33_owned.py',
    'tests/integration_current33_mfa_postgres.py',
    'tests/integration_postgres.py',
    'tests/notifications36_restore_helpers.py',
    'tests/product38_fixtures.py',
    'tests/progress32_fixtures.py',
    'tests/test_nutrition35_profile_contract.py',
    'tests/ci_web37/scope.py',
    'tests/ci_web39/pg_control.py',
    'tests/ci_web39/pg_tools.py',
    'tests/ci_web39/pg_tools_linux.py',
    'tests/ci_web39/run_postgres.py',
    'tests/ci_web39/pg_admission.py',
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def phase(name):
    plan = json.loads((ROOT / 'tests/ci_web39/pg-plan.json').read_bytes())
    if plan['schema'] != SCOPE or plan['revision'] != '20261023_privacy_disposition' or plan['historical429_53_27_modified'] is not False:
        raise ValueError('Separate39 phase plan differs')
    selected = plan['phases'][name]
    numbers = ('UUIDs', 'concurrent_UUIDs', 'application_pool', 'admin_observer_pool', 'additional_application_workers', 'max_overflow')
    expected = {'core': (1, 1, 1, 1, 0, 0), 'restore': (2, 1, 1, 1, 0, 0)}
    if (set(plan['phases']) != set(expected) or any(type(selected[k]) is not int for k in numbers)
            or tuple(selected[k] for k in numbers) != expected[name]
            or selected['module'] != 'tests/integration_privacy39_' + {'core': 'postgres', 'restore': 'restore'}[name] + '.py'):
        raise ValueError('Separate39 selection/UUID/pool budget differs')
    return dict(selected, name=name)


def plain(path):
    value = path.lstat()
    if stat.S_ISLNK(value.st_mode) or getattr(value, 'st_file_attributes', 0) & 1024:
        raise ValueError('A PG39 bound path became an alias')
    return value


def source_files(selected):
    plain(ROOT)
    paths = set(BOUND) | {selected['module'], 'tests/ci_web39/pg-plan.json',
        'tests/ci_web39/__init__.py', 'tests/ci_web39/pg_contract.py',
        'tests/ci_web39/pg_fixtures.py', 'tests/ci_web39/pg_physical.py'}
    for name in RUNTIME_ROOTS:
        base = ROOT / name
        plain(base)
        for directory, children, files in os.walk(base, followlinks=False):
            for child in children:
                plain(Path(directory) / child)
            for child in files:
                path = Path(directory) / child
                if '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo'):
                    paths.add(path.relative_to(ROOT).as_posix())
    result = {}
    for name in sorted(paths):
        path = ROOT / name
        if not stat.S_ISREG(plain(path).st_mode):
            raise ValueError('A bound PG39 source is not regular')
        raw = path.read_bytes()
        result[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return result


def build_contract(name, profile_path, generation_path):
    from tests.billing13_legacy_apply37_pg_contract import generation, pg_binary_directory, private_workspace
    from tests.ci_web37.pg_lease import profile
    from web.services.legacy_object_apply_boundary import verify
    selected = phase(name)
    paths = [Path(value).resolve(strict=True) for value in (profile_path, generation_path)]
    for path in paths:
        if not path.is_relative_to(private_workspace()):
            raise ValueError('The PG39 profile and generation must remain private')
        verify(path)
    config = profile(paths[0])
    pg_binary_directory(config)
    files = source_files(selected)
    value = {'schema': SCOPE, 'repository': str(ROOT), 'phase': selected, 'revision': '20261023_privacy_disposition',
        'source_identity': 'FileSetDigest_not_Git_HEAD', 'FileSetDigest': digest(files), 'files': files,
        'profile_path': str(paths[0]), 'profile_sha256': hashlib.sha256(paths[0].read_bytes()).hexdigest(),
        'generation_path': str(paths[1]), 'generation_sha256': hashlib.sha256(paths[1].read_bytes()).hexdigest(),
        'generation': generation(paths[1]), 'server_port': 55483,
        'closure': 'owned603f_commonclose_e905_normal_DROP_strict_zero_fresh_absence',
        'exclusive_no_restart_Root_window_required': True,
        'historical429_53_27_retargeted': False}
    if os.name != 'nt':
        from tests.ci_web39.pg_tools_linux import tool_hashes
        value['Linux_PG_tools'] = tool_hashes(pg_binary_directory(config))
    return value


def require_ack(path, value):
    from tests.billing13_legacy_apply37_pg_contract import private_workspace
    from web.services.legacy_object_apply_boundary import verify
    path = Path(path)
    if not path.is_absolute() or not path.resolve(strict=True).is_relative_to(private_workspace()):
        raise ValueError('A fresh private Root39 ACK is required')
    verify(path)
    raw = path.read_bytes()
    ack = json.loads(raw)
    if (set(ack) != {'approved', 'scope', 'contract_sha256', 'expires_at_UTC'}
            or ack['approved'] is not True or ack['scope'] != SCOPE or value['schema'] != SCOPE
            or ack['contract_sha256'] != digest(value)):
        raise ValueError('The Root39 source/profile/generation/phase ACK differs')
    expiry = datetime.fromisoformat(ack['expires_at_UTC'])
    if expiry.tzinfo is None or not 0 < (expiry - datetime.now(UTC)).total_seconds() <= 8 * 3600:
        raise ValueError('The Root39 ACK expired or exceeds eight hours')
    return hashlib.sha256(raw).hexdigest()


def checked_runtime(name):
    from tests.ci_web37.pg_lease import profile
    value = build_contract(name, os.environ['PG39_PROFILE'], os.environ['PG39_GENERATION'])
    require_ack(os.environ['PG39_ACK'], value)
    return value, profile(value['profile_path'], expected_sha256=value['profile_sha256'])


@contextmanager
def creation_generation_guard(runtime):
    """Derived finite c6ff same-cursor fence; no37 scope/ACK is reused."""
    import psycopg2
    from psycopg2.extensions import cursor as Cursor
    from unittest.mock import patch
    from tests.billing13_legacy_apply37_pg_contract import check_generation
    connect = psycopg2.connect

    class Guarded(Cursor):
        def execute(self, query, variables=None):
            statement = query.as_string(self) if hasattr(query, 'as_string') else str(query)
            if statement.lstrip().upper().startswith('CREATE DATABASE'):
                current, config = checked_runtime(runtime.name)
                if (current != runtime.contract or config != runtime.profile or runtime.failed
                        or runtime.active != 1 or runtime.created >= runtime.contract['phase']['UUIDs']):
                    raise ValueError('PG39 phase/source/generation/UUID authority changed before CREATE')
                check_generation(current, config, cursor=self)
                runtime.created += 1
            return super().execute(query, variables)

    def guarded_connect(*args, **kwargs):
        if kwargs.get('connection_factory') is not None or kwargs.get('cursor_factory') not in (None, Guarded):
            raise ValueError('A foreign cursor cannot bypass the PG39 creation fence')
        return connect(*args, **dict(kwargs, cursor_factory=Guarded))
    with patch.object(psycopg2, 'connect', guarded_connect):
        yield
