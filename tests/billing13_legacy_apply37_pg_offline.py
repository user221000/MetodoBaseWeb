"""Stdlib-only preparation guards, runnable with unittest; no pytest/DB import."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bounded_pg25_contract', ROOT / 'tests/billing13_legacy_apply37_pg_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class PreparedPG27(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='metodobase-pg25-pure-', dir='E:/MetodoBaseWorkspace/tmp')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def ack(self, value, **changes):
        path = self.root / 'new-ack-synthetic.json'
        row = {'approved': True, 'scope': contract.SCOPE, 'contract_sha256': contract.digest(value),
               'expires_at_UTC': (datetime.now(UTC) + timedelta(hours=1)).isoformat(), **changes}
        path.write_text(json.dumps(row), encoding='utf8')
        return path

    def test_node_inventory_is_exact27_unique_without_importing_product(self):
        value = contract.phase()
        self.assertEqual(value['nodeids'], contract.ast_nodeids())
        self.assertEqual(len(set(value['nodeids'])), 27)
        self.assertEqual((value['UUIDs'], value['concurrent_UUIDs'], value['restricted_application_pool_size'], value['max_overflow']), (1, 1, 1, 0))

    def test_incomplete_duplicate_or_expanded_inventory_is_rejected(self):
        tests = self.root / 'tests'
        tests.mkdir()
        (tests / Path(contract.MODULE).name).write_bytes((ROOT / contract.MODULE).read_bytes())
        for change in ({'UUIDs': 2}, {'UUIDs': True}, {'max_overflow': False},
                       {'cases': 24}, {'restricted_application_pool_size': 5},
                       {'nodeids': contract.ast_nodeids()[:-1] + [contract.ast_nodeids()[0]]}):
            value = {**contract.phase(), **change}
            (self.root / contract.PLAN).write_text(json.dumps(value), encoding='utf8')
            with self.assertRaises(ValueError):
                contract.phase(self.root)

    def test_fresh_ACK_binds_source_profile_generation_and_selection(self):
        value = {'schema': contract.SCOPE, 'source': 'synthetic-source', 'profile_sha256': 'a' * 64,
                 'generation': {'postmaster_pid': 123}, 'phase': {'cases': 27, 'UUIDs': 1}}
        path = self.ack(value)
        self.assertEqual(len(contract.require_ack(path, value)), 64)
        for key, other in [('source', 'changed'), ('profile_sha256', 'b' * 64),
                           ('generation', {'postmaster_pid': 124}), ('phase', {'cases': 26, 'UUIDs': 1})]:
            with self.assertRaises(ValueError):
                contract.require_ack(path, {**value, key: other})

    def test_old_phase_scope_boolean_and_expired_ACK_are_rejected(self):
        value = {'schema': contract.SCOPE}
        for changes in ({'scope': 'actual37-pg53-exclusive-v1'}, {'approved': 1},
                        {'expires_at_UTC': datetime.now(UTC).isoformat()},
                        {'expires_at_UTC': (datetime.now(UTC) + timedelta(hours=9)).isoformat()}):
            with self.assertRaises(ValueError):
                contract.require_ack(self.ack(value, **changes), value)

    def test_naive_or_nonidentity_generation_is_rejected(self):
        value = {'postmaster_pid': 123, 'master_creation_filetime_100ns': 456,
                 'postmaster_start_UTC': datetime.now(UTC).isoformat()}
        path = self.root / 'generation.json'
        path.write_text(json.dumps(value), encoding='utf8')
        self.assertEqual(contract.generation(path), value)
        for change in ({'postmaster_pid': True}, {'master_creation_filetime_100ns': 0},
                       {'postmaster_start_UTC': datetime.now().isoformat()}, {'foreign_key': 'reject'}):
            path.write_text(json.dumps({**value, **change}), encoding='utf8')
            with self.assertRaises(ValueError):
                contract.generation(path)

    def test_Windows_generation_reader_identifies_only_this_E_Python_process(self):
        created, executable = contract.windows_process_identity(os.getpid())
        self.assertGreater(created, 0)
        self.assertEqual(executable, Path(sys.executable).resolve())
        self.assertEqual(contract.windows_process_identity(os.getpid()), (created, executable))


if __name__ == '__main__':
    unittest.main()
