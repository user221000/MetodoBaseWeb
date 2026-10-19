"""Packaging recipes are exercised with synthetic trees, never an application."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("desktop_packaging_author", ROOT / "build.py")
packaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packaging)


def test_spec_selects_gui_entry_and_safe_onedir_recipe():
    calls = {}
    class AnalysisResult:
        pure, scripts, binaries, datas = [], [], [], []
    def analysis(*args, **kwargs):
        calls["analysis"] = (args, kwargs)
        return AnalysisResult()
    def collect(*args, **kwargs):
        calls["collect"] = kwargs
    def exe(*args, **kwargs):
        calls["exe"] = kwargs
    namespace = {"SPECPATH": str(ROOT), "Analysis": analysis, "PYZ": lambda *a, **kw: None,
                 "EXE": exe, "COLLECT": collect, "BUNDLE": lambda *a, **kw: None}
    # Execute only spec declarations, with every PyInstaller constructor fake.
    with patch.dict(sys.modules, {"build": packaging}):
        exec(compile((ROOT / "MetodoBase.spec").read_text(encoding="utf-8"), "MetodoBase.spec", "exec"), namespace)
    arguments, options = calls["analysis"]
    assert arguments[0] == [str(ROOT / "main.py")]
    assert options["runtime_hooks"] == [str(ROOT / "scripts/desktop_runtime_hook.py")]
    assert all(Path(source).is_file() and not Path(source).is_dir() for source, _ in options["datas"])
    assert calls["exe"]["exclude_binaries"] is True
    assert calls["exe"]["console"] is False
    assert calls["exe"]["contents_directory"] == "_internal"
    assert calls["collect"]["upx"] is False


def test_resource_selection_excludes_configs_and_untracked_files():
    inventory = packaging.collect_resources(ROOT)
    paths = [Path(source).relative_to(ROOT).as_posix() for source, _ in inventory]
    assert set(packaging.REQUIRED_RESOURCES).issubset(paths)
    assert not any(name.startswith(("config/", "core/", "src/", "api/", ".env")) for name in paths)


def test_gui_validator_does_not_load_http_or_product_modules():
    spec = importlib.util.spec_from_file_location("desktop_validator_author", ROOT / "validate_build.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"build": packaging}):
        spec.loader.exec_module(module)
    assert "requests" not in module.__dict__
    assert "test_server" not in module.__dict__


def test_runtime_hook_normal_mode_has_no_application_import(tmp_path):
    source = ROOT / "scripts/desktop_runtime_hook.py"
    env = {"METODOBASE_DESKTOP_SMOKE_DIR": ""}
    code = "import runpy,sys;runpy.run_path(sys.argv[1]);assert not any(n.startswith(('PySide6','core.','config.','ui_desktop.')) for n in sys.modules)"
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(source)], cwd=tmp_path,
                            env=env, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_source_guard_rejects_absent_or_different_commit_before_build():
    with pytest.raises(packaging.BuildError):
        packaging.source_snapshot("")
    with pytest.raises(packaging.BuildError):
        packaging.source_snapshot("0" * 40)


def test_build_cli_requires_explicit_frozen_source_commit():
    result = subprocess.run([sys.executable, "-B", str(ROOT / "build.py"), "--no-tests"],
                            cwd=ROOT, capture_output=True, timeout=10)
    assert result.returncode == 2
    assert b"--source-commit" in result.stderr


def test_tooling_lock_is_separate_and_fully_pinned():
    inputs = (ROOT / "requirements_build.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" not in inputs
    assert "pytest" not in inputs
    lock = (ROOT / "requirements_build.lock").read_text(encoding="utf-8")
    for package, version in packaging.TOOL_VERSIONS.items():
        assert f"{package}=={version}" in lock
    assert "--hash=sha256:" in lock
