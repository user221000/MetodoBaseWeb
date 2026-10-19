"""Reversible entrypoint and installer-preparation tests; no GUI/compiler."""
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def packaging():
    return load("desktop_entrypoint_packaging", "build.py")


def test_setup_only_delegates_to_shared_recipe(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "build", SimpleNamespace(main=lambda arguments: calls.append(arguments) or 7))
    setup = load("desktop_setup_wrapper", "setup.py")
    assert setup.main(["build", "--source-commit", "a" * 40, "--zip"]) == 7
    assert calls == [["--source-commit", "a" * 40, "--zip"]]


def test_import_setup_and_config_never_loads_product_or_creates_profile(tmp_path):
    profile = tmp_path / "not-created-profile"
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "METODOBASE_DATA_DIR"):
        env[name] = str(profile / name)
    env["TRIAL_DAYS"] = "invalid-to-detect-import-of-product-constants"
    code = ("import sys,importlib.util,json;sys.path.insert(0,sys.argv[1]);"
            "import setup,build_config;print(json.dumps({'version':build_config.APP_VERSION,"
            "'loaded':any(n in sys.modules for n in ('config.constantes','core.licencia','PyInstaller'))}))")
    child = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(ROOT)], cwd=tmp_path,
                           env=env, capture_output=True, text=True, timeout=15)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == {"version": "2.0.0", "loaded": False}
    assert not profile.exists()


def test_batch_build_has_one_recipe_and_no_mutating_legacy_steps():
    script = (ROOT / "build_all.bat").read_text(encoding="utf-8").lower()
    commands = "\n".join(line for line in script.splitlines() if not line.strip().startswith("rem "))
    assert '"%~dp0build.py"' in commands
    assert "metodobase_build_python" in commands
    assert not re.search(r"\b(rmdir|del|pip|pyinstaller|iscc|pause)\b", commands)
    assert "setup.py" not in commands


@pytest.mark.skipif(sys.platform != "win32", reason="Windows batch semantics require Windows")
def test_new_batch_wrong_commit_from_other_cwd_preserves_files(tmp_path):
    sentinel = tmp_path / "keep.txt"
    sentinel.write_bytes(b"do not remove caller files")
    env = os.environ.copy()
    env["METODOBASE_BUILD_PYTHON"] = sys.executable
    result = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(ROOT / "build_all.bat"),
                             "--source-commit", "0" * 40], cwd=tmp_path, env=env, capture_output=True, timeout=15)
    assert result.returncode == 1
    assert sentinel.read_bytes() == b"do not remove caller files"
    assert (ROOT / "MetodoBase.spec").is_file()
    assert set(tmp_path.iterdir()) == {sentinel}


@pytest.mark.skipif(sys.platform != "win32", reason="Windows batch semantics require Windows")
def test_new_portable_launcher_missing_package_never_installs(tmp_path):
    launcher = tmp_path / "metodobase_iniciar.bat"
    launcher.write_bytes((ROOT / launcher.name).read_bytes())
    result = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher)],
                            cwd=tmp_path, capture_output=True, timeout=10)
    assert result.returncode == 2
    assert set(tmp_path.iterdir()) == {launcher}
    commands = launcher.read_text(encoding="utf-8").lower()
    assert "pip install" not in commands and "api_server.py" not in commands and "-m venv" not in commands


def test_iss_preserves_identity_and_data_without_auto_launch():
    script = (ROOT / "setup_installer.iss").read_text(encoding="utf-8")
    sections = re.findall(r"^\[([^]]+)\]", script, re.MULTILINE)
    assert "Run" not in sections and "UninstallDelete" not in sections
    assert "8A2F4E7B-3C9D-4B1A-A5E6-7F8D9C0B2E3A" in script
    assert "UsePreviousAppDir=yes" in script
    assert "ArchitecturesAllowed=x64compatible" in script
    assert "#include VerifiedFilesInclude" in script
    assert "#define MyAppVersion" not in script
    assert "#ifndef PreparedInputs" in script and "#error" in script
    assert 'Source: "dist' not in script


def pe_bytes(machine=0x8664):
    content = bytearray(128)
    content[:2] = b"MZ"
    struct.pack_into("<I", content, 60, 64)
    content[64:68] = b"PE\0\0"
    struct.pack_into("<H", content, 68, machine)
    return bytes(content)


@pytest.fixture
def windows_bundle(tmp_path, packaging):
    root = tmp_path / "synthetic bundle" / "MetodoBase"
    values = {"MetodoBase.exe": pe_bytes(), "_internal/fonts/Inter/Inter-Regular.ttf": b"font",
              "_internal/ui_desktop/pyside/styles/amarillo_neon.qss": b"QWidget {}",
              "_internal/PySide6/plugins/platforms/qwindows.dll": b"plugin",
              "_internal/PySide6/plugins/platforms/qoffscreen.dll": b"plugin"}
    for name, value in values.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    packaging.write_manifest(root, target_platform="win32", source_commit="a" * 40)
    return root


def test_installer_preparation_uses_exact_files_version_and_provenance(packaging, windows_bundle, tmp_path, monkeypatch):
    monkeypatch.setattr(packaging, "source_snapshot", lambda commit: {"synthetic": "stable"})
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("No compiler or GUI process allowed"))
    output = tmp_path / "prepared inputs"
    report = json.loads(packaging.prepare_installer(windows_bundle, "a" * 40, output).read_text())
    assert report["architecture"] == "x86_64" and report["app_version"] == "2.0.0"
    assert report["source_commit"] == "a" * 40
    assert report["compiler_executed"] is report["installer_tested"] is report["signature_verified"] is False
    listing = (output / "verified-files.iss").read_text(encoding="utf-8-sig")
    assert listing.count("Source:") == len(packaging.bundle_files(windows_bundle)) + 1
    assert "*" not in listing and "recursesubdirs" not in listing
    assert "build-manifest.json" in listing and "_internal" in listing
    settings = (output / "verified-settings.iss").read_text(encoding="utf-8-sig")
    assert '#define MyAppVersion "2.0.0"' in settings
    assert (output / "installer-entry.iss").is_file()


@pytest.mark.parametrize("mutation", ["version", "commit", "architecture", "platform", "bytes"])
def test_installer_rejects_unverified_or_mismatched_source(packaging, windows_bundle, tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(packaging, "source_snapshot", lambda commit: {})
    manifest_path = windows_bundle / "build-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if mutation == "bytes":
        (windows_bundle / "MetodoBase.exe").write_bytes(b"tampered")
    else:
        keys = {"version": "app_version", "commit": "source_commit", "architecture": "architecture", "platform": "platform"}
        manifest[keys[mutation]] = "different"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(packaging.BuildError):
        packaging.prepare_installer(windows_bundle, "a" * 40, tmp_path / "rejected inputs")
    assert not (tmp_path / "rejected inputs").exists()


@pytest.mark.parametrize("payload", [b"plain text", pe_bytes(0x014C), pe_bytes(0xAA64)])
def test_pe_architecture_is_read_from_bytes(packaging, tmp_path, payload):
    file = tmp_path / "synthetic.exe"
    file.write_bytes(payload)
    with pytest.raises(packaging.BuildError):
        packaging.verify_windows_amd64(file)
