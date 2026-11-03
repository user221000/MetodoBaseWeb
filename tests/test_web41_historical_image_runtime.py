"""Finite historical TEST salt, authentic blobs and negative source controls."""
import ast
import base64
import importlib.util
import io
import logging
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("historical_image_test_runtime", ROOT / "tests/ci_web41/historical_image_runtime.py")
companion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(companion)


def _git(root, *args):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(root), *args], stderr=subprocess.PIPE)


def _original(schema):
    spec = companion.specification(schema)
    return _git(ROOT, "show", spec["commit"] + ":" + spec["runner"])


@pytest.mark.parametrize("schema", ["31", "33"])
def test_whole_source_inverse_preserves_every_original_byte(schema):
    original = _original(schema)
    current = companion.adapted_bytes(original, schema)
    assert current.count(companion.ADDITION) == 1
    assert len(current) - len(original) == len(companion.ADDITION)
    assert current.replace(companion.ADDITION, b"") == original
    assert companion.digest(current) == companion.SOURCES[schema]["compiled_sha256"]


@pytest.mark.parametrize("schema", ["31", "33"])
def test_real_original_validator_requires_salt_and_accepts_only_valid_control(schema):
    spec = companion.specification(schema)
    raw = _original(schema)
    module = ast.parse(companion.adapted_bytes(raw, schema))
    image, = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "image"]
    assignment, = [n for n in image.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "runtime" for t in n.targets)]
    def runtime():
        return eval(compile(ast.Expression(assignment.value), "<exact-historical-test-runtime>", "eval"),
                    {"os": os, "base64": base64, "environment": {
                        "METODOBASE_TEST_POSTGRES_URL": "postgresql+psycopg2://metodobase_test_app:inert-only@127.0.0.1:55483/metodobase_test_image"}})
    first, second = runtime(), runtime()
    assert len(base64.urlsafe_b64decode(first["METODO_BASE_SALT"])) == 32
    assert first["METODO_BASE_SALT"] != second["METODO_BASE_SALT"]
    namespace = {"__name__": "_historical_validator_control"}
    exec(compile(_git(ROOT, "show", spec["commit"] + ":config/env_validator.py"), "<original-validator>", "exec"), namespace)  # noqa: S102 -- unchanged validator from the pinned ancestor
    for value, expected in ((None, 1), ("short", 1), (first["METODO_BASE_SALT"], 0)):
        environment = dict(first)
        environment.pop("METODO_BASE_SALT")
        if value is not None:
            environment["METODO_BASE_SALT"] = value
        capture = io.StringIO()
        handler = logging.StreamHandler(capture)
        logger = namespace["logger"]
        logger.addHandler(handler)
        try:
            with patch.dict(os.environ, environment, clear=True):
                try:
                    namespace["validate_env_vars"]()
                except SystemExit as error:
                    actual = error.code
                else:
                    actual = 0
        finally:
            logger.removeHandler(handler)
        assert actual == expected
        assert first["WEB_SECRET_KEY"] not in capture.getvalue()
        assert first["METODO_BASE_SALT"] not in capture.getvalue()


@pytest.mark.parametrize("schema", ["31", "33"])
@pytest.mark.parametrize("mutation", ["one_byte", "whole_crlf", "already_has_salt", "role_literal", "readiness_literal"])
def test_unreviewed_whole_runner_is_rejected(schema, mutation):
    raw = _original(schema)
    if mutation == "one_byte":
        altered = raw + b"\n"
    elif mutation == "whole_crlf":
        altered = raw.replace(b"\n", b"\r\n")
    elif mutation == "already_has_salt":
        altered = raw.replace(companion.OLD, companion.OLD + companion.ADDITION)
    elif mutation == "role_literal":
        altered = raw.replace(b"application_role_restricted_nonowner", b"application_role_restricted_nonownes", 1)
    else:
        altered = raw.replace(b"range(120)", b"range(121)", 1)
    assert altered != raw
    with pytest.raises(ValueError):
        companion.adapted_bytes(altered, schema)


@pytest.mark.parametrize("schema", ["30", "32", " 31", "31 ", "", 31, None])
def test_only_two_literal_sources_are_admitted(schema):
    with pytest.raises(ValueError):
        companion.specification(schema)


@pytest.fixture
def repository(tmp_path, monkeypatch):
    root = tmp_path / "owned-history"
    root.mkdir()
    _git(root, "init", "--initial-branch=owned-history")
    spec = dict(companion.SOURCES["31"])
    runner = root / spec["runner"]
    runner.parent.mkdir(parents=True)
    runner.write_bytes(_original("31"))
    (root / "README.md").write_bytes(b"authentic synthetic fixture\n")
    _git(root, "-c", "core.autocrlf=false", "add", "--", ".")
    _git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Owned immutable fixture")
    spec["commit"] = _git(root, "rev-parse", "HEAD").decode().strip()
    monkeypatch.setitem(companion.SOURCES, "31", spec)
    return root


def test_all_tracked_bytes_are_authenticated_without_test_imports(repository):
    result = companion.snapshot(repository, "31")
    assert result["tracked_files"] == 2
    assert result["source_commit"] == companion.SOURCES["31"]["commit"]
    assert result == companion.snapshot(repository, "31")


def test_tracked_non_runner_drift_is_rejected(repository):
    (repository / "README.md").write_bytes(b"forged synthetic fixture\n")
    with pytest.raises(ValueError):
        companion.snapshot(repository, "31")


def test_additional_runtime_input_is_rejected_but_original_doc_outputs_allowed(repository):
    (repository / "docs").mkdir()
    (repository / "docs/report.json").write_bytes(b"{}")
    companion.snapshot(repository, "31")
    (repository / "unreviewed.py").write_bytes(b"raise RuntimeError('never execute')\n")
    with pytest.raises(ValueError):
        companion.snapshot(repository, "31")


def test_head_mismatch_rejected(repository):
    (repository / "README.md").write_bytes(b"new source\n")
    _git(repository, "add", "--", "README.md")
    _git(repository, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Different HEAD")
    with pytest.raises(ValueError):
        companion.snapshot(repository, "31")


def test_hardlinked_source_rejected(repository, tmp_path):
    (tmp_path / "alias.md").hardlink_to(repository / "README.md")
    with pytest.raises(ValueError):
        companion.snapshot(repository, "31")


def test_standalone_boundary_refuses_current_pytest_packages_before_dispatch(repository, tmp_path):
    with pytest.raises(ValueError, match="standalone script"):
        companion.execute(repository, "31", tmp_path / "public", "metodobase-current31:" + "a" * 40,
                          tmp_path / "binding.json")
    assert not (tmp_path / "binding.json").exists()
