"""Metadata-only privacy controls; no services, providers or historical retarget."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tests import ci_diagnostics41 as diagnostics

RUN_SOURCE = b'''def main():
    validate()
    context.prepare()
    build_probe()
    evidence["seal"]()
'''
CANARY = "private-fixture-value-must-never-be-rendered"


class MessageTrap(ValueError):
    @property
    def args(self):
        raise AssertionError("Exception arguments were accessed")

    def __str__(self):
        raise AssertionError("Exception message was formatted")


class DiagnosticsPrivacy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ci41-metadata-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.binding = diagnostics.Binding.__new__(diagnostics.Binding)
        self.binding.root = self.root
        self.binding.source = "a" * 40
        self.binding.cache = {}
        self.files = {"tests/ci_image57/run.py": RUN_SOURCE,
                      "tests/ci_image57/context.py": b"def prepare():\n    raise ValueError()\n"}
        for name, raw in self.files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        def git_value(repository, *arguments):
            self.assertEqual(Path(repository), self.root)
            self.assertEqual(arguments[:2], ("cat-file", "blob"))
            source, name = arguments[2].split(":", 1)
            self.assertEqual(source, self.binding.source)
            return self.files[name]
        patcher = mock.patch.object(diagnostics, "git", side_effect=git_value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def frame(self, line):
        return self.binding.frame(str(self.root / "tests/ci_image57/run.py"), line)

    def test_exception_message_args_and_unknown_class_are_never_rendered(self):
        try:
            raise MessageTrap(CANARY)
        except MessageTrap as failure:
            result = diagnostics.exception_metadata(failure, self.binding)
        encoded = json.dumps(result)
        self.assertNotIn(CANARY, encoded)
        self.assertNotIn("MessageTrap", encoded)
        self.assertEqual(result["exception_type"], "OTHER")
        self.assertFalse(result["accepted"])

    def test_only_authenticated_relative_in_range_frames_are_admitted(self):
        good = self.frame(3)
        self.assertEqual(good["path"], "tests/ci_image57/run.py")
        self.assertEqual(good["source_sha256"], hashlib.sha256(RUN_SOURCE).hexdigest())
        self.assertIsNone(self.binding.frame(str(self.root.parent / "private.py"), 1))
        self.assertIsNone(self.binding.frame(str(self.root / "tests/private.py"), 1))
        self.assertIsNone(self.binding.frame("<stdin>", 1))
        self.assertIsNone(self.frame(99999))

    def test_changed_code_is_excluded_instead_of_getting_a_new_pin(self):
        (self.root / "tests/ci_image57/run.py").write_bytes(RUN_SOURCE + b"# changed\n")
        self.assertIsNone(self.frame(3))

    def test_forged_compile_filename_does_not_authenticate_executing_code(self):
        filename = str(self.root / "tests/ci_image57/run.py")
        namespace = {}
        exec(compile("def forged():\n    raise ValueError('synthetic-private')\n", filename, "exec"), namespace)
        try:
            namespace["forged"]()
        except ValueError as failure:
            result = diagnostics.exception_metadata(failure, self.binding)
        self.assertEqual(result["frames"], [])
        self.assertEqual(result["phase"], "unknown")

    def test_live_original_code_object_matches_compile_of_the_git_bytes(self):
        class Context:
            @staticmethod
            def prepare():
                raise MessageTrap(CANARY)
        namespace = {"validate": lambda: None, "context": Context}
        exec(compile(RUN_SOURCE, str(self.root / "tests/ci_image57/run.py"), "exec", dont_inherit=True), namespace)
        try:
            namespace["main"]()
        except MessageTrap as failure:
            result = diagnostics.exception_metadata(failure, self.binding)
        self.assertEqual(result["phase"], "context_prepare")
        self.assertEqual(len(result["frames"]), 1)
        self.assertEqual(result["frames"][0]["binding"], "code_git_compile_match")

    def test_four_coarse_phases_follow_the_bound_main_callsites(self):
        for line, expected in [(2, "path_validation"), (3, "context_prepare"), (4, "build_probe"), (5, "seal")]:
            with self.subTest(phase=expected):
                self.assertEqual(diagnostics.image_phase([self.frame(line)], self.binding), expected)

    def test_private_trace_projects_no_message_source_line_url_or_environment(self):
        filename = str(self.root / "tests/ci_image57/run.py").encode()
        trace = [b"Traceback (most recent call last):\n",
                 b'  File "' + filename + b'", line 3, in main\n',
                 ("    raise ValueError('" + CANARY + "')\n").encode(),
                 ("ValueError: " + CANARY + " https://example.invalid/private?secret=fixture\n").encode()]
        result = diagnostics.parse_traceback(trace, self.binding, "pg_bootstrap")
        self.assertEqual(result["exception_type"], "ValueError")
        self.assertEqual(result["phase"], "pg_bootstrap")
        self.assertEqual(len(result["frames"]), 1)
        self.assertEqual(result["frames"][0]["binding"], "text_location_only/path_git_match")
        encoded = json.dumps(result)
        for forbidden in [CANARY, "https:", "secret=", "raise ValueError", str(self.root)]:
            self.assertNotIn(forbidden, encoded)

    def test_at_most_two_frames_and_only_fixed_fields_are_published(self):
        filename = str(self.root / "tests/ci_image57/run.py").encode()
        trace = [b'  File "' + filename + b'", line ' + str(line).encode() + b', in main\n' for line in (2, 3, 4, 5)]
        trace.append(b"RuntimeError: private detail withheld\n")
        result = diagnostics.parse_traceback(trace, self.binding, "pg_bootstrap")
        self.assertEqual([frame["line"] for frame in result["frames"]], [4, 5])
        self.assertEqual(set(result), {"schema", "accepted", "phase", "exception_type", "source", "frames"})

    def test_oversized_private_line_is_rejected(self):
        with self.assertRaises(ValueError):
            diagnostics.parse_traceback([b"x" * (diagnostics.MAX_LINE + 1)], self.binding, "pg_bootstrap")

    def test_unavailable_source_proof_emits_only_fixed_failure_metadata(self):
        output = io.StringIO()
        with mock.patch.object(diagnostics, "Binding", side_effect=ValueError(CANARY)):
            with contextlib.redirect_stderr(output):
                diagnostics.emit_image_failure(ValueError(CANARY), self.root, ["--source", "a" * 40])
        result = json.loads(output.getvalue())
        self.assertIsNone(result["source"])
        self.assertEqual(result["frames"], [])
        self.assertNotIn(CANARY, output.getvalue())

    def test_private_trace_requires_the_owned_private_platform_boundary(self):
        private = self.root / "private"
        private.mkdir(mode=0o700)
        trace = private / "trace.log"
        trace.write_bytes(b"ValueError: synthetic-private\n")
        if os.name == "posix":
            private.chmod(0o700)
            trace.chmod(0o600)
            self.assertEqual(list(diagnostics.private_trace_lines(trace)), [b"ValueError: synthetic-private\n"])
            private.chmod(0o755)
        with self.assertRaises(ValueError):
            list(diagnostics.private_trace_lines(trace))


if __name__ == "__main__":
    unittest.main()
