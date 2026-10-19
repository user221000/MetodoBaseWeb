"""OPS10: exact non-distributable design reference, synthetic artifacts only."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "assets/design-reference.png"


@pytest.fixture
def packaging():
    spec = importlib.util.spec_from_file_location("desktop_packaging_ops10", ROOT / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tracked_resources(path: Path, reference: str) -> dict[str, bytes]:
    path.mkdir()
    resources = {
        "fonts/Inter/Inter-Regular.ttf": b"synthetic font",
        "ui_desktop/pyside/styles/amarillo_neon.qss": b"QWidget {}",
        reference: b"synthetic non-distributable design reference",
        "assets/examples/design-reference.png": b"unrelated exact-basename resource",
        "assets/design-reference-v2.png": b"unrelated different-name resource",
    }
    for relative, content in resources.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for arguments in (["init", "--quiet"], ["add", "--all"]):
        result = subprocess.run(["git", "-c", "core.autocrlf=false", *arguments],
                                cwd=path, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
    return resources


def _synthetic_bundle(path: Path, forbidden: str | None = None) -> Path:
    executable = "MetodoBase.exe" if sys.platform == "win32" else "MetodoBase"
    plugins = {"win32": ("qwindows.dll", "qoffscreen.dll"),
               "darwin": ("libqcocoa.dylib", "libqoffscreen.dylib")}
    content = {
        executable: b"synthetic executable, never launched",
        "_internal/fonts/Inter/Inter-Regular.ttf": b"synthetic font",
        "_internal/ui_desktop/pyside/styles/amarillo_neon.qss": b"QWidget {}",
        "_internal/assets/examples/design-reference.png": b"allowed different exact path",
        "_internal/assets/design-reference-v2.png": b"allowed different exact filename",
    }
    for plugin in plugins.get(sys.platform, ("libqxcb.so", "libqoffscreen.so")):
        content["_internal/PySide6/plugins/platforms/" + plugin] = b"synthetic Qt plugin"
    if forbidden is not None:
        content[forbidden] = b"synthetic non-distributable design reference"
    for relative, data in content.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return path


def _coherent_manifest(bundle: Path) -> Path:
    """Forge a valid old-contract inventory, independent of packaging helpers."""
    files = {}
    for path in bundle.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            files[path.relative_to(bundle).as_posix()] = {
                "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    target = bundle / "build-manifest.json"
    target.write_text(json.dumps({"schema": 1, "platform": sys.platform, "files": files}),
                      encoding="utf-8")
    return target


def test_actual_tracked_design_reference_is_retained_but_not_collected(packaging):
    original = ROOT / REFERENCE
    before = original.read_bytes()
    tracked = subprocess.run(["git", "--no-optional-locks", "ls-files", "-z", "--", REFERENCE],
                             cwd=ROOT, capture_output=True, check=True, timeout=10)
    assert tracked.stdout == (REFERENCE + "\0").encode()
    selected = {Path(source).relative_to(ROOT).as_posix()
                for source, _ in packaging.collect_resources(ROOT)}
    assert REFERENCE not in selected
    assert original.read_bytes() == before
    assert set(packaging.REQUIRED_RESOURCES).issubset(selected)


@pytest.mark.parametrize("reference", [REFERENCE, "assets/DESIGN-REFERENCE.PNG"])
def test_real_git_resource_inventory_excludes_only_exact_casefold_path(packaging, tmp_path, reference):
    root = tmp_path / "tracked repository"
    expected = _tracked_resources(root, reference)
    selected = {Path(source).relative_to(root).as_posix()
                for source, _ in packaging.collect_resources(root)}
    assert selected == set(expected) - {reference}
    assert {relative: (root / relative).read_bytes() for relative in expected} == expected


@pytest.mark.parametrize("forbidden", [
    "_internal/assets/design-reference.png",
    "_INTERNAL/ASSETS/DESIGN-REFERENCE.PNG",
])
@pytest.mark.parametrize("operation", ["bundle_files", "write_manifest", "verify_manifest", "zip"])
def test_coherent_bundle_with_exact_reference_is_rejected(packaging, tmp_path, forbidden, operation):
    bundle = _synthetic_bundle(tmp_path / "MetodoBase", forbidden)
    _coherent_manifest(bundle)
    output = tmp_path / "previous.zip"
    output.write_bytes(b"previous distribution must survive rejection")
    if operation == "zip":
        call = lambda: packaging.create_distribution_zip(bundle, output)
    else:
        call = lambda: getattr(packaging, operation)(bundle)
    with pytest.raises(packaging.BuildError):
        call()
    assert output.read_bytes() == b"previous distribution must survive rejection"
    assert not list(tmp_path.glob(".desktop-zip-*"))


def test_other_paths_and_names_remain_distributable(packaging, tmp_path):
    bundle = _synthetic_bundle(tmp_path / "MetodoBase")
    packaging.write_manifest(bundle)
    manifest = packaging.verify_manifest(bundle)
    allowed = {"_internal/assets/examples/design-reference.png",
               "_internal/assets/design-reference-v2.png"}
    assert allowed.issubset(manifest["files"])
    output = packaging.create_distribution_zip(bundle, tmp_path / "candidate.zip")
    with zipfile.ZipFile(output) as archive:
        assert {"MetodoBase/" + name for name in allowed}.issubset(archive.namelist())
        assert "MetodoBase/_internal/" + REFERENCE not in archive.namelist()

