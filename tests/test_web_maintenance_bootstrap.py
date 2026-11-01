"""A fresh container must preserve an explicitly paused deployment seed."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from web.maintenance_bootstrap import FILE_ENV, SEED_ENV, install_control, main


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="maintenance-bootstrap-")
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / "private" / "maintenance.json"
        self.value = {"version": 1, "active": True, "token": "a" * 64,
                      "operation": "fd0d1345-e3fa-4c58-b6d9-6adbd2cf59dd"}
        self.environment = {FILE_ENV: str(self.target), SEED_ENV: json.dumps(self.value)}

    def test_default_unconfigured_is_inert(self):
        with patch.dict(os.environ, {FILE_ENV: "", SEED_ENV: ""}):
            self.assertFalse(install_control())
        self.assertFalse(self.target.exists())

    def test_incomplete_pairs_fail(self):
        for env in ({FILE_ENV: str(self.target), SEED_ENV: ""},
                    {FILE_ENV: "", SEED_ENV: json.dumps(self.value)}):
            with self.subTest(env_field=bool(env[FILE_ENV])), patch.dict(os.environ, env):
                with self.assertRaises(ValueError): install_control()
        self.assertFalse(self.target.exists())

    def test_fresh_container_starts_paused(self):
        with patch.dict(os.environ, self.environment):
            self.assertTrue(install_control())
        self.assertEqual(json.loads(self.target.read_text()), self.value)

    def test_restart_reinstalls_authoritative_seed(self):
        with patch.dict(os.environ, self.environment):
            install_control()
            self.target.write_text(json.dumps({**self.value, "active": False}))
            install_control()
        self.assertTrue(json.loads(self.target.read_text())["active"])

    def test_explicit_reopen_seed(self):
        self.value["active"] = False
        self.environment[SEED_ENV] = json.dumps(self.value)
        with patch.dict(os.environ, self.environment): install_control()
        self.assertFalse(json.loads(self.target.read_text())["active"])

    def test_invalid_seed_does_not_replace_existing_control(self):
        with patch.dict(os.environ, self.environment): install_control()
        original = self.target.read_bytes()
        for raw in ('{', '{}', json.dumps({**self.value, "active": 1}),
                    json.dumps({**self.value, "token": "bad"}),
                    json.dumps(self.value)[:-1] + ',"active":false}', 'x' * 4097):
            with self.subTest(length=len(raw)), patch.dict(os.environ, {**self.environment, SEED_ENV: raw}):
                with self.assertRaises(ValueError): install_control()
            self.assertEqual(self.target.read_bytes(), original)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_relative_or_wrong_name_rejected(self):
        for path in ('relative/maintenance.json', str(self.target.with_name('other.json'))):
            with patch.dict(os.environ, {**self.environment, FILE_ENV: path}):
                with self.assertRaises(ValueError): install_control()

    def test_failure_logs_no_seed(self):
        from io import StringIO
        output = StringIO()
        with patch.dict(os.environ, {**self.environment, SEED_ENV: 'bad-private-seed'}), patch('sys.stderr', output):
            self.assertEqual(main(), 78)
        self.assertEqual(output.getvalue(), 'Maintenance bootstrap failed; web worker was not started.\n')


if __name__ == '__main__': unittest.main()
