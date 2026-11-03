"""One pinned PG companion location; no bootstrap, app import or subprocess."""
from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tests import ci_diagnostics41 as diagnostics

ROOT = Path(__file__).resolve().parents[1]
CANARY = "private-pg-diagnostic-value-must-not-be-published"


class Current41PGCompanionDiagnostics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ci41-pg-companion-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.files = {}
        for name, (size, expected) in diagnostics.PG_INPUTS.items():
            raw = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (size, expected))
            self.files[name] = raw
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self.binding = diagnostics.Binding.__new__(diagnostics.Binding)
        self.binding.root = self.root
        self.binding.source = "a" * 40
        self.binding.cache = {}
        self.git_calls = []

        def git_value(repository, *arguments):
            self.assertEqual(Path(repository), self.root)
            self.assertEqual(arguments[:2], ("cat-file", "blob"))
            source, name = arguments[2].split(":", 1)
            self.assertEqual(source, self.binding.source)
            self.git_calls.append(name)
            return self.files[name]

        self.git_value = git_value
        patcher = mock.patch.object(diagnostics, "git", side_effect=git_value)
        self.git_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def frame(self, line, name=None):
        return self.binding.compiled_pg_frame(str(self.root / (name or diagnostics.PG_WRAPPER)), line)

    def trace(self, line, phase="pg_bootstrap", name=None):
        filename = str(self.root / (name or diagnostics.PG_WRAPPER)).encode()
        return diagnostics.parse_traceback([
            b'  File "' + filename + b'", line ' + str(line).encode() + b', in start\n',
            ("    raise CalledProcessError('" + CANARY + "')\n").encode(),
            ("subprocess.CalledProcessError: " + CANARY + " https://example.invalid/?private=value\n").encode(),
        ], self.binding, phase)

    def test_all_four_exact_callsites_have_only_fixed_operations_and_provenance(self):
        for line, (operation, _) in diagnostics.PG_CALLS.items():
            with self.subTest(line=line):
                frame = self.frame(line)
                self.assertEqual(frame, {
                    "path": diagnostics.PG_WRAPPER, "line": line,
                    "source_sha256": diagnostics.PG_COMPILED_SHA256,
                    "binding": "catalogue_compiled/text_location_only", "operation": operation,
                    "wrapper_sha256": diagnostics.PG_INPUTS[diagnostics.PG_WRAPPER][1],
                    "catalogue_sha256": diagnostics.PG_INPUTS[diagnostics.PG_CATALOGUE][1],
                    "parent_source_sha256": diagnostics.PG_INPUTS[diagnostics.PG_PARENT][1],
                })
        self.assertEqual(set(self.git_calls), set(diagnostics.PG_INPUTS))

    def test_projection_does_not_exec_import_app_or_launch_any_process(self):
        with mock.patch("builtins.exec", side_effect=AssertionError("exec forbidden")), \
                mock.patch.object(diagnostics.subprocess, "run", side_effect=AssertionError("process forbidden")):
            self.assertEqual(self.frame(66)["operation"], "pg_ctl_start")

    def test_original_physical_location_and_live_binding_contract_remain_separate(self):
        name = str(self.root / diagnostics.PG_WRAPPER)
        physical = self.binding.frame(name, 9)
        self.assertEqual(physical["source_sha256"], diagnostics.PG_INPUTS[diagnostics.PG_WRAPPER][1])
        self.assertNotIn("operation", physical)
        self.assertIsNone(self.binding.frame(name, 49))
        live = SimpleNamespace(f_code=compile("pass\n", name, "exec", dont_inherit=True))
        self.assertIsNone(self.binding.live_frame(live, 49))
        self.assertEqual(self.trace(9)["frames"][0]["binding"], "text_location_only/path_git_match")

    def test_unknown_module_namespace_and_extra_helpers_never_gain_compiled_frames(self):
        names = (diagnostics.PG_PARENT, "tests/ci_web41/pg_control.py", "tests/ci_web39/pg_tools_linux.py",
                 "tests/ci_web41/other.py", "tests/ci_web37/ci_cluster.py")
        for name in names:
            with self.subTest(name=name):
                self.assertIsNone(self.frame(49, name))
        self.assertEqual(self.git_calls, [])
        self.assertIsNone(self.binding.compiled_pg_frame("<stdin>", 49))
        self.assertIsNone(self.binding.compiled_pg_frame(str(self.root.parent / diagnostics.PG_WRAPPER), 49))

    def test_other_lines_and_non_integer_inputs_fail_before_reading_sources(self):
        for line in (True, False, None, "49", -1, 0, 1, 48, 50, 64, 65, 67, 135, 137, 151, 152, 1000001):
            with self.subTest(line=line):
                self.assertIsNone(self.frame(line))
        self.assertEqual(self.git_calls, [])

    def test_compiled_locations_are_not_admitted_outside_pg_bootstrap(self):
        for phase in ("unknown", "build_probe", "context_prepare", "seal"):
            with self.subTest(phase=phase):
                self.assertEqual(self.trace(66, phase)["frames"], [])
        self.assertEqual(self.trace(66)["frames"][0]["operation"], "pg_ctl_start")

    def test_changed_catalogue_byte_is_rejected_without_new_pin(self):
        self.changed_source_refuses(diagnostics.PG_CATALOGUE)

    def test_changed_parent_byte_is_rejected_without_new_pin(self):
        self.changed_source_refuses(diagnostics.PG_PARENT)

    def test_changed_wrapper_byte_is_rejected_without_new_pin(self):
        self.changed_source_refuses(diagnostics.PG_WRAPPER)

    def changed_source_refuses(self, name):
        (self.root / name).write_bytes(self.files[name] + b"\n")
        self.assertIsNone(self.frame(66))
        self.assertEqual(self.trace(66)["frames"], [])

    def test_even_git_agreement_cannot_admit_any_changed_reviewed_input(self):
        for name in diagnostics.PG_INPUTS:
            with self.subTest(name=name):
                original = self.files[name]
                self.files[name] += b"\n"
                (self.root / name).write_bytes(self.files[name])
                self.assertIsNone(self.frame(63))
                self.files[name] = original
                (self.root / name).write_bytes(original)

    def test_an_unavailable_git_blob_refuses_instead_of_using_a_disk_fallback(self):
        self.git_mock.side_effect = ValueError(CANARY)
        self.assertIsNone(self.frame(49))

    def test_wrong_catalogue_entry_or_revision_is_rejected(self):
        original = json.loads(self.files[diagnostics.PG_CATALOGUE])
        cases = []
        value = deepcopy(original)
        value["revision"] = "other"
        cases.append(value)
        value = deepcopy(original)
        value["entries"][diagnostics.PG_WRAPPER]["original"] = "tests/ci_web37/ci_cluster.py"
        cases.append(value)
        value = deepcopy(original)
        value["entries"][diagnostics.PG_WRAPPER]["current_sha256_LF"] = "0" * 64
        cases.append(value)
        value = deepcopy(original)
        del value["entries"][diagnostics.PG_WRAPPER]
        cases.append(value)
        for value in cases:
            with self.subTest(case=cases.index(value)):
                with mock.patch.object(diagnostics.json, "loads", return_value=value):
                    self.assertIsNone(self.frame(66))

    def test_edit_count_recount_empty_and_boolean_cannot_change_reconstruction(self):
        original = json.loads(self.files[diagnostics.PG_CATALOGUE])
        for fault in ("count", "bool", "empty", "new"):
            value = deepcopy(original)
            edit = value["entries"][diagnostics.PG_WRAPPER]["literal_edits"][0]
            if fault == "count":
                edit["count"] += 1
            elif fault == "bool":
                edit["count"] = True
            elif fault == "empty":
                edit["old"] = ""
            else:
                edit["new"] += "_forged"
            with self.subTest(fault=fault), mock.patch.object(diagnostics.json, "loads", return_value=value):
                self.assertIsNone(self.frame(66))

    def test_retained_parent_frame_pin_or_size_cannot_be_recounted(self):
        original = json.loads(self.files[diagnostics.PG_CATALOGUE])
        for key, replacement in (("bytes", 8511), ("sha256", "0" * 64)):
            value = deepcopy(original)
            for frame in value["entries"][diagnostics.PG_WRAPPER]["original_frames"]:
                frame[key] = replacement
            with self.subTest(key=key), mock.patch.object(diagnostics.json, "loads", return_value=value):
                self.assertIsNone(self.frame(63))

    def test_wrong_ast_call_body_namespace_and_extra_subprocess_are_rejected(self):
        real_parse = diagnostics.ast.parse
        for fault in ("body", "namespace", "extra"):
            def wrong_ast(source, fault=fault):
                tree = real_parse(source)
                nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                         and node.func.value.id == "subprocess"]
                if fault == "body":
                    nodes[0].keywords = []
                elif fault == "namespace":
                    nodes[0].func.value.id = "unreviewed"
                else:
                    extra = real_parse("subprocess.run([])\n").body[0]
                    extra.value.lineno = 140
                    tree.body.append(extra)
                return tree
            with self.subTest(fault=fault), mock.patch.object(diagnostics.ast, "parse", side_effect=wrong_ast):
                self.assertIsNone(self.frame(63))

    def test_source_drift_during_the_read_refuses_the_entire_companion_frame(self):
        def changing_git(repository, *arguments):
            raw = self.git_value(repository, *arguments)
            if self.git_calls[-1] == diagnostics.PG_PARENT:
                (self.root / diagnostics.PG_WRAPPER).write_bytes(self.files[diagnostics.PG_WRAPPER] + b"\n")
            return raw
        self.git_mock.side_effect = changing_git
        self.assertIsNone(self.frame(136))

    def test_an_alias_or_hardlinked_input_refuses_the_companion(self):
        source = self.root / diagnostics.PG_PARENT
        alias = self.root / "parent-alias.fixture"
        os.link(source, alias)
        self.assertIsNone(self.frame(63))

    def test_projected_trace_never_discloses_messages_arguments_commands_or_paths(self):
        result = self.trace(66)
        self.assertEqual(result["exception_type"], "CalledProcessError")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["frames"][0]["binding"], "catalogue_compiled/text_location_only")
        self.assertEqual(result["frames"][0]["operation"], "pg_ctl_start")
        encoded = json.dumps(result)
        for forbidden in (CANARY, "https:", "private=value", str(self.root), "127.0.0.1", "55483",
                          "--pwfile", "CalledProcessError('", "metodobase_test_admin", "postgresql+"):
            self.assertNotIn(forbidden, encoded)

    def test_invalid_utf8_filename_is_rejected_without_changing_error_class(self):
        trace = [b'  File "bad-\xff.py", line 66, in start\n', b"CalledProcessError: withheld\n"]
        result = diagnostics.parse_traceback(trace, self.binding, "pg_bootstrap")
        self.assertEqual(result["frames"], [])
        self.assertEqual(result["exception_type"], "CalledProcessError")


if __name__ == "__main__":
    unittest.main()
