"""Synthetic E transport probes, NOT Linux/PG execution; explicit unittest only."""
import hashlib
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import billing13_legacy_apply37_pg_contract as contract


class CITransport(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='metodobase-ci27-unit-', dir='E:/MetodoBaseWorkspace/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)
        self.env = {'GITHUB_ACTIONS': 'true', 'GITHUB_WORKSPACE': str(ROOT), 'RUNNER_TEMP': str(self.temp),
            'TEMP': str(self.temp), 'TMP': str(self.temp), 'TMPDIR': str(self.temp), 'GITHUB_SHA': 'a' * 40}
        self.proxy = SimpleNamespace(name='posix', environ=self.env, geteuid=lambda: 1000)
        self.fake_temp = SimpleNamespace(gettempdir=lambda: str(self.temp))

    def linux(self):
        stack = ExitStack()
        stack.enter_context(patch.object(contract, 'os', self.proxy))
        stack.enter_context(patch.object(contract, 'tempfile', self.fake_temp))
        return stack

    def fixture(self):
        data = self.temp / 'ci37-pg-cluster-private/data'
        data.mkdir(parents=True)
        binary = self.temp / 'inert-binary'
        binary.write_bytes(b'inert-not-executable')
        stat = self.temp / 'proc-stat'
        stat.write_text('51777 (post)gres synthetic) S ' + ' '.join(['0'] * 18 + ['1234']), encoding='ascii')
        boot = self.temp / 'boot-id'
        boot.write_text('12345678-1234-1234-1234-123456789abc\n', encoding='ascii')
        pidfile = data / 'postmaster.pid'
        pidfile.write_bytes(b'51777\nsynthetic-not-a-real-cluster\n')
        value = {'schema': 'linux-ci-v1', 'postmaster_pid': 51777, 'start_ticks': 1234,
            'boot_id': boot.read_text().strip(), 'postmaster_start_UTC': '2026-10-22T00:00:00+00:00',
            'postmaster_pidfile_sha256': hashlib.sha256(pidfile.read_bytes()).hexdigest(), 'data': str(data)}
        def mapped(path, *args):
            name = str(path)
            return {'/proc/51777/stat': stat, '/proc/sys/kernel/random/boot_id': boot,
                '/proc/51777/exe': binary, '/proc/1/stat': stat,
                '/usr/lib/postgresql/17/bin/postgres': binary}.get(name, Path(path, *args))
        return value, stat, boot, pidfile, mapped

    def test_Windows_boundary_remains_E_and_has_no_CI_fallback(self):
        self.assertEqual(contract.private_workspace(), Path('E:/MetodoBaseWorkspace'))
        self.assertEqual(contract.temporary_root(), Path('E:/MetodoBaseWorkspace/tmp'))

    def test_CI_boundary_requires_all_existing_job_conditions(self):
        with self.linux():
            self.assertEqual(contract.private_workspace(), self.temp)
            for key, value in [('GITHUB_ACTIONS', 'false'), ('GITHUB_WORKSPACE', str(self.temp)), ('TMP', str(ROOT))]:
                original = self.env[key]
                self.env[key] = value
                with self.assertRaises(ValueError):
                    contract.private_workspace()
                self.env[key] = original
            self.proxy.geteuid = lambda: 0
            with self.assertRaises(ValueError):
                contract.private_workspace()

    def test_Linux_generation_is_strictly_typed_and_not_Windows_FILETIME(self):
        value, *_ = self.fixture()
        with self.linux():
            self.assertEqual(contract.validated_generation(value), value)
            for change in ({'postmaster_pid': True}, {'start_ticks': 1.0}, {'boot_id': 'invalid'},
                           {'postmaster_pidfile_sha256': 'x' * 64}, {'data': str(self.temp)},
                           {'postmaster_start_UTC': '2026-10-22T00:00:00'}, {'master_creation_filetime_100ns': 123}):
                with self.assertRaises(ValueError):
                    contract.validated_generation({**value, **change})

    def test_proc_last_parenthesis_and_every_identity_pin_are_checked(self):
        value, stat, boot, pidfile, mapped = self.fixture()
        with self.linux(), patch.object(contract, 'Path', mapped):
            contract.linux_process_identity(value)
            for changed in ({'start_ticks': 1235}, {'postmaster_pid': 1}, {'boot_id': 'a' * 36}, {'postmaster_pidfile_sha256': '0' * 64}):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    contract.linux_process_identity({**value, **changed})
            stat.write_text(stat.read_text().replace('1234', '1235'), encoding='ascii')
            with self.assertRaises(ValueError):
                contract.linux_process_identity(value)
        self.assertTrue(boot.exists() and pidfile.exists())

    def test_same_connection_pgstart_and_port_are_separate_pins(self):
        from datetime import datetime
        value, _, boot, _, mapped = self.fixture()
        calls = []
        class Cursor:
            def execute(self, sql):
                calls.append(sql)
            def fetchone(self):
                return datetime.fromisoformat(value['postmaster_start_UTC']), '127.0.0.1', 55483
        with self.linux(), patch.object(contract, 'Path', mapped), patch.object(contract, 'pg_binary_directory', lambda *_: None):
            contract.check_generation({'generation': value}, {}, cursor=Cursor())
            self.assertEqual(len(calls), 1)
            class Wrong(Cursor):
                def fetchone(self):
                    return datetime.fromisoformat(value['postmaster_start_UTC']), '127.0.0.1', 55484
            with self.assertRaises(ValueError):
                contract.check_generation({'generation': value}, {}, cursor=Wrong())
            class Changed(Cursor):
                def fetchone(self):
                    boot.write_text('changed-boot\n', encoding='ascii')
                    return super().fetchone()
            with self.assertRaises(ValueError):
                contract.check_generation({'generation': value}, {}, cursor=Changed())

    def test_preCREATE_adapter_checks_fresh_authority_and_only_one_creation(self):
        module = ModuleType('psycopg2')
        extension = ModuleType('psycopg2.extensions')
        sent, ordered = [], []
        class Cursor:
            def execute(self, query, variables=None):
                sent.append(str(query))
        extension.cursor = Cursor
        module.connect = lambda *_a, **kwargs: kwargs['cursor_factory']()
        from tests.billing13_legacy_apply37_pg_generation import (
            creation_generation_guard,
        )
        value, profile = {'source': 'synthetic'}, {'profile': 'synthetic'}
        def checked():
            ordered.append('authority')
            return value, profile
        def generation(*_args, **_kwargs):
            ordered.append('same-connection-generation')
        with patch.dict(sys.modules, {'psycopg2': module, 'psycopg2.extensions': extension}), patch.object(contract, 'checked_runtime', checked), patch.object(contract, 'check_generation', generation):
            with creation_generation_guard(value, profile):
                with self.assertRaises(ValueError):
                    module.connect(connection_factory=object)
                cursor = module.connect()
                cursor.execute('CREATE DATABASE synthetic_owned_uuid')
                self.assertEqual(ordered, ['authority', 'same-connection-generation'])
                with self.assertRaises(ValueError):
                    cursor.execute('CREATE DATABASE second_must_not_reach_driver')
                self.assertEqual(len(sent), 1)
            sent.clear()
            with patch.object(contract, 'checked_runtime', lambda: ({'changed': True}, profile)), creation_generation_guard(value, profile):
                with self.assertRaises(ValueError):
                    module.connect().execute('CREATE DATABASE changed_authority')
                self.assertEqual(sent, [])

    def test_only_executed_clean_PG27_summary_can_satisfy_CI(self):
        value = {'accepted': True, 'PostgreSQL_executed': True, 'scope': 'separate_current37_PG27',
            'selected_sources_quiet': True, 'source_packages_binaries_quiet': True,
            'PG_binaries_sources_packages_roles_quiet': True, 'case_count': 27,
            'normally_closed_UUIDs_fresh_absent': 1, 'pytest_exit': 0, 'pip_before': 0, 'pip_after': 0}
        contract.require_executed_summary(value)
        for change in ({'PostgreSQL_executed': False}, {'normally_closed_UUIDs_fresh_absent': True},
                       {'scope': 'prepared_PG27_AST_only'}, {'pytest_exit': False}, {'pip_after': 1},
                       {'PG_binaries_sources_packages_roles_quiet': False}, {'case_count': 26}):
            with self.assertRaises(ValueError):
                contract.require_executed_summary({**value, **change})

    def test_workflow_orders_third_ACK_27_and_required_summary_without_changing_429_53(self):
        import yaml
        source = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_bytes())
        steps = source['jobs']['current-postgres']['steps']
        indices = {name: next(index for index, step in enumerate(steps) if name in step.get('name', ''))
                   for name in ('complete429', 'original53', 'actual27', 'Stop only')}
        self.assertLess(indices['complete429'], indices['original53'])
        self.assertLess(indices['original53'], indices['actual27'])
        self.assertLess(indices['actual27'], indices['Stop only'])
        self.assertEqual(steps[indices['Stop only']]['if'], 'always()')
        run = steps[indices['actual27']]['run']
        self.assertIn('--lease-ack "$RUNNER_TEMP/ci37-pg-cluster-private/ack27.private.json"', run)
        self.assertNotIn('--plan-only', run)
        self.assertIn('require_executed_summary(value)', run)
        upload = next(step for step in steps if step.get('with', {}).get('name') == 'current37-billing13-legacy-apply-postgres27-required-summary')
        self.assertEqual(upload['with']['if-no-files-found'], 'error')
        self.assertTrue(upload['with']['path'].endswith('/27/summary.json'))
        bootstrap = next(step['run'] for step in steps if 'CI-only fresh' in step.get('name', ''))
        self.assertIn("'planned_UUIDs':71", bootstrap)
        self.assertIn("'required_identities':509", bootstrap)
        self.assertIn('value=contract27(profile,generation)', bootstrap)


if __name__ == '__main__':
    unittest.main()
