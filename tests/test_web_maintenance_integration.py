"""Auth startup and real factory source contracts; no database is opened."""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from web.middleware.maintenance import MaintenanceGate


REPO = Path(__file__).resolve().parents[1]
TOKEN = "c2" * 32
OPERATION = "9fa6258c-84f1-45b8-b8fc-9f245bd03f1a"


class IntegrationFragmentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="maintenance-fragments-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "control.json"
        self.calls = []

        def recorded(name, value=None):
            def run():
                self.calls.append(name)
                return value
            return run

        self.namespace = {
            "_get_secret_key": recorded("secret", "synthetic-config-value"),
            "_get_access_expire_minutes": recorded("access-expiry", 15),
            "_get_refresh_expire_days": recorded("refresh-expiry", 7),
            "_crear_tablas": recorded("legacy-noop"),
            "_seed_demo_users": recorded("seed"),
            "_cleanup_expired_refresh_tokens": recorded("cleanup", 0),
            "_logger": Mock(),
        }
        module_source = (REPO / "web/auth.py").read_text(encoding="utf8")
        node = next(node for node in ast.parse(module_source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "init_auth")
        source = ast.get_source_segment(module_source, node)
        exec(compile(source, "init_auth_fragment.py", "exec"), self.namespace)

    def control(self, active):
        self.path.write_text(json.dumps({"version": 1, "active": active,
                             "token": TOKEN, "operation": OPERATION}), encoding="utf8")

    def assert_config_loaded(self):
        self.assertEqual(self.namespace["SECRET_KEY"], "synthetic-config-value")
        self.assertEqual(self.namespace["ACCESS_TOKEN_EXPIRE_MINUTES"], 15)
        self.assertEqual(self.namespace["REFRESH_TOKEN_EXPIRE_DAYS"], 7)
        self.assertEqual(self.calls[:4], ["secret", "access-expiry", "refresh-expiry", "legacy-noop"])

    def test_default_preserves_config_seed_cleanup(self):
        self.namespace["init_auth"]()
        self.assert_config_loaded()
        self.assertEqual(self.calls[4:], ["seed", "cleanup"])

    def test_paused_guard_keeps_config_without_seed_or_cleanup(self):
        self.control(True)
        gate = MaintenanceGate(control_file=str(self.path))
        with gate.background_admission() as admitted:
            self.namespace["init_auth"](run_startup_writes=admitted)
        self.assertFalse(admitted)
        self.assert_config_loaded()
        self.assertEqual(len(self.calls), 4)

    def test_invalid_file_guard_keeps_config_without_seed_or_cleanup(self):
        self.path.write_bytes(b"invalid")
        gate = MaintenanceGate(control_file=str(self.path))
        with gate.background_admission() as admitted:
            self.namespace["init_auth"](run_startup_writes=admitted)
        self.assertFalse(admitted)
        self.assert_config_loaded()
        self.assertEqual(len(self.calls), 4)

    def test_configured_missing_file_keeps_config_without_seed_or_cleanup(self):
        gate = MaintenanceGate(control_file=str(self.path))
        with gate.background_admission() as admitted:
            self.namespace["init_auth"](run_startup_writes=admitted)
        self.assertFalse(admitted)
        self.assert_config_loaded()
        self.assertEqual(len(self.calls), 4)

    def test_admitted_startup_remains_counted_if_paused_inside_cleanup(self):
        self.control(False)
        gate = MaintenanceGate(control_file=str(self.path))
        counts = []

        def cleanup():
            self.control(True)
            counts.append(gate._active_jobs)

        self.namespace["_cleanup_expired_refresh_tokens"] = cleanup
        with gate.background_admission() as admitted:
            self.namespace["init_auth"](run_startup_writes=admitted)
            self.assertEqual(gate._active_jobs, 1)
        self.assertEqual(counts, [1])
        self.assertEqual(gate._active_jobs, 0)
        self.assert_config_loaded()

    def test_cleanup_failure_preserves_config_and_releases_job(self):
        self.control(False)
        gate = MaintenanceGate(control_file=str(self.path))

        def fail():
            raise RuntimeError("synthetic-startup-error")

        self.namespace["_cleanup_expired_refresh_tokens"] = fail
        with gate.background_admission() as admitted:
            self.namespace["init_auth"](run_startup_writes=admitted)
        self.assertEqual(gate._active_jobs, 0)
        self.assert_config_loaded()
        self.namespace["_logger"].warning.assert_called_once_with(
            "[AUTH] startup_cleanup_failed class=%s", "RuntimeError")

    def test_both_factories_guard_all_current_auth_cleanup_callers(self):
        for relative, count in (("web/main_web.py", 3), ("api/app.py", 1)):
            source = (REPO / relative).read_text(encoding="utf8")
            tree = ast.parse(source)
            parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
            callers = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                       and isinstance(node.func, ast.Name)
                       and node.func.id in {"init_auth", "cleanup_expired_tokens"}]
            with self.subTest(factory=relative):
                self.assertEqual(len(callers), count)
                for call in callers:
                    ancestor = parents[call]
                    while not isinstance(ancestor, ast.With):
                        ancestor = parents[ancestor]
                    context = ancestor.items[0].context_expr
                    self.assertEqual(ast.unparse(context), "maintenance_gate.background_admission()")
                    if call.func.id == "init_auth":
                        self.assertEqual(ast.unparse(call), "init_auth(run_startup_writes=admitted)")

    def test_both_factories_register_shared_gate_last_after_observability(self):
        for relative in ("web/main_web.py", "api/app.py"):
            source = (REPO / relative).read_text(encoding="utf8")
            tree = ast.parse(source)
            factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                           and node.name == "create_app")
            with self.subTest(factory=relative):
                tail = [ast.unparse(node) for node in factory.body[-3:]]
                self.assertEqual(tail, ["configure_observability(app)",
                    "app.add_middleware(MaintenanceMiddleware, gate=maintenance_gate)", "return app"])
                self.assertEqual(sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                                 and node.func.id == "MaintenanceGate" for node in ast.walk(factory)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
