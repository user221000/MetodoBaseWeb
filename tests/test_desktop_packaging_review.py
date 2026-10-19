"""Independent checks of the desktop packaging boundary; no GUI or build runs."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packaging():
    spec = importlib.util.spec_from_file_location("desktop_packaging_independent_review", ROOT / "build.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bundle(path: Path, target: str = sys.platform) -> Path:
    path.mkdir(parents=True)
    binary = "MetodoBase.exe" if target == "win32" else "MetodoBase"
    files = {
        binary: b"synthetic executable; never launch",
        "_internal/fonts/Inter/Inter-Regular.ttf": b"synthetic font",
        "_internal/ui_desktop/pyside/styles/amarillo_neon.qss": b"QWidget {}",
        "_internal/python312.dll": b"synthetic runtime dependency",
    }
    extensions = {"win32": ("qwindows.dll", "qoffscreen.dll"),
                  "darwin": ("libqcocoa.dylib", "libqoffscreen.dylib")}
    for name in extensions.get(target, ("libqxcb.so", "libqoffscreen.so")):
        files["_internal/PySide6/plugins/platforms/" + name] = b"synthetic Qt plugin"
    for name, data in files.items():
        destination = path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return path


@pytest.fixture
def bundle(tmp_path):
    return _bundle(tmp_path / "release with spaces" / "MetodoBase")


def _directory_link(path: Path, target: Path):
    """Create only a temporary link. Its unlink never recurses into the target."""
    try:
        path.symlink_to(target, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        if sys.platform != "win32":
            pytest.skip("directory symlink unavailable")
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(path), str(target)],
        capture_output=True, timeout=10,
    )
    if result.returncode:
        pytest.skip("temporary directory link unavailable")


def _remove_directory_link(path: Path):
    if path.is_symlink():
        path.unlink()
    else:
        os.rmdir(path)


@pytest.mark.parametrize("target", ["win32", "linux", "darwin"])
def test_platform_structure_is_checked_without_launching(packaging, tmp_path, target, monkeypatch):
    value = _bundle(tmp_path / target / "MetodoBase", target)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("must not launch a process"))
    expected = "MetodoBase.exe" if target == "win32" else "MetodoBase"
    assert packaging.validate_bundle(value, target_platform=target) == value / expected


@pytest.mark.parametrize("missing", ["_internal", "_internal/fonts/Inter/Inter-Regular.ttf",
    "_internal/ui_desktop/pyside/styles/amarillo_neon.qss"])
def test_incomplete_onedir_is_rejected(packaging, bundle, missing):
    target = bundle / missing
    if target.is_dir():
        import shutil
        shutil.rmtree(target)
    else:
        target.unlink()
    with pytest.raises(packaging.BuildError):
        packaging.validate_bundle(bundle)


def test_gui_platform_plugin_is_mandatory(packaging, bundle):
    platform = "qwindows.dll" if sys.platform == "win32" else (
        "libqcocoa.dylib" if sys.platform == "darwin" else "libqxcb.so")
    (bundle / "_internal/PySide6/plugins/platforms" / platform).unlink()
    with pytest.raises(packaging.BuildError):
        packaging.validate_bundle(bundle)


def test_bare_executable_cannot_be_published_as_onedir(packaging, bundle):
    executable = bundle / ("MetodoBase.exe" if sys.platform == "win32" else "MetodoBase")
    with pytest.raises(packaging.BuildError):
        packaging.create_distribution_zip(executable)


@pytest.mark.parametrize("relative", [
    "_internal/.env", "_internal/config/.env.production", "_internal/licencia.lic",
    "_internal/config/licencia_config.json", "_internal/local.db", "_internal/local.sqlite3",
    "_internal/registros/clients.json", "_internal/planes/personal.pdf",
    "_internal/logs/runtime.log", "_internal/backups/customer.bak",
])
def test_accidental_user_material_is_rejected_before_manifest(packaging, bundle, relative):
    extra = bundle / relative
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"synthetic confidential content")
    with pytest.raises(packaging.BuildError):
        packaging.write_manifest(bundle)
    assert not (bundle / "build-manifest.json").exists()


def test_manifest_covers_the_exact_complete_tree(packaging, bundle):
    manifest = packaging.write_manifest(bundle)
    assert manifest == bundle / "build-manifest.json"
    packaging.verify_manifest(bundle)
    tree = packaging.bundle_files(bundle)
    assert "_internal/python312.dll" in tree
    assert "build-manifest.json" not in tree
    assert all("\\" not in path and not path.startswith("/") and ".." not in path.split("/") for path in tree)


@pytest.mark.parametrize("mutation", ["extra", "missing", "tampered", "malformed-manifest"])
def test_manifest_detects_payload_changes(packaging, bundle, mutation):
    packaging.write_manifest(bundle)
    item = bundle / "_internal/python312.dll"
    if mutation == "extra":
        (bundle / "_internal/extra.dll").write_bytes(b"unexpected")
    elif mutation == "missing":
        item.unlink()
    elif mutation == "tampered":
        item.write_bytes(b"different bytes, same harmless file name")
    else:
        (bundle / "build-manifest.json").write_text("{", encoding="utf-8")
    with pytest.raises(packaging.BuildError):
        packaging.verify_manifest(bundle)


def test_zip_contains_every_dependency_and_manifest_with_portable_names(packaging, bundle, tmp_path):
    packaging.write_manifest(bundle)
    expected = set(packaging.bundle_files(bundle)) | {"build-manifest.json"}
    result = packaging.create_distribution_zip(bundle, output=tmp_path / "distribution.zip")
    with zipfile.ZipFile(result) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert all("\\" not in name and ":" not in name and not name.startswith("/")
                   and ".." not in name.split("/") for name in names)
        # The optional distribution root must be the same for every file.
        stripped = {name.split("/", 1)[1] for name in names} if all(
            name.split("/", 1)[0] == names[0].split("/", 1)[0] for name in names) else set(names)
        assert stripped == expected or set(names) == expected
        dependency = next(name for name in names if name.endswith("_internal/python312.dll"))
        assert archive.read(dependency) == (bundle / "_internal/python312.dll").read_bytes()


def test_failed_validation_preserves_previous_zip_and_creates_no_partial(packaging, bundle, tmp_path):
    destination = tmp_path / "existing.zip"
    destination.write_bytes(b"previous artifact")
    packaging.write_manifest(bundle)
    (bundle / "_internal/python312.dll").write_bytes(b"tampered")
    with pytest.raises(packaging.BuildError):
        packaging.create_distribution_zip(bundle, output=destination)
    assert destination.read_bytes() == b"previous artifact"
    assert set(tmp_path.glob("existing.zip*")) == {destination}


def test_archive_write_failure_preserves_previous_zip_and_removes_partial(packaging, bundle, tmp_path, monkeypatch):
    destination = tmp_path / "existing.zip"
    destination.write_bytes(b"previous artifact")
    packaging.write_manifest(bundle)
    original_paths = set(tmp_path.rglob("*"))
    calls = []
    original = zipfile.ZipFile.write

    def fail_after_first_file(archive, *args, **kwargs):
        calls.append(args)
        if len(calls) == 2:
            raise OSError("synthetic disk write failure")
        return original(archive, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", fail_after_first_file)
    with pytest.raises((packaging.BuildError, OSError)):
        packaging.create_distribution_zip(bundle, output=destination)
    assert len(calls) >= 2
    assert destination.read_bytes() == b"previous artifact"
    assert set(tmp_path.rglob("*")) == original_paths


def test_zip_payload_must_match_manifest_even_when_source_recovers(packaging, bundle, tmp_path, monkeypatch):
    packaging.write_manifest(bundle)
    dependency = bundle / "_internal/python312.dll"
    original_bytes = dependency.read_bytes()
    destination = tmp_path / "existing.zip"
    destination.write_bytes(b"previous artifact")
    original_write = zipfile.ZipFile.write

    def transient_mutation(archive, filename, *args, **kwargs):
        if Path(filename) == dependency:
            dependency.write_bytes(b"transient bytes must never be published")
            try:
                return original_write(archive, filename, *args, **kwargs)
            finally:
                dependency.write_bytes(original_bytes)
        return original_write(archive, filename, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", transient_mutation)
    with pytest.raises(packaging.BuildError):
        packaging.create_distribution_zip(bundle, output=destination)
    assert dependency.read_bytes() == original_bytes
    assert destination.read_bytes() == b"previous artifact"


def test_unreadable_tree_must_fail_instead_of_being_silently_omitted(packaging, bundle, monkeypatch):
    original_walk = os.walk

    def inaccessible(*args, **kwargs):
        handler = kwargs.get("onerror")
        error = PermissionError("synthetic unreadable dependency directory")
        if handler is not None:
            handler(error)
        # Model os.walk's default omission of an unreadable subtree.
        yield from original_walk(*args, **kwargs)

    monkeypatch.setattr(os, "walk", inaccessible)
    with pytest.raises(packaging.BuildError):
        packaging.bundle_files(bundle)


def test_linked_directory_never_imports_external_data(packaging, bundle, tmp_path):
    outside = tmp_path / "outside release"
    outside.mkdir()
    protected = outside / "private.db"
    protected.write_bytes(b"external confidential sentinel")
    linked = bundle / "_internal/borrowed"
    _directory_link(linked, outside)
    try:
        with pytest.raises(packaging.BuildError):
            packaging.bundle_files(bundle)
        assert protected.read_bytes() == b"external confidential sentinel"
    finally:
        _remove_directory_link(linked)


def test_clean_refuses_output_directory_link_and_preserves_external_data(packaging, tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "build.py").write_text("# synthetic workspace marker", encoding="utf-8")
    outside = tmp_path / "outside workspace"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_bytes(b"never remove")
    link = workspace / "dist"
    _directory_link(link, outside)
    monkeypatch.setattr(packaging, "BASE_DIR", workspace)
    try:
        with pytest.raises(packaging.BuildError):
            packaging.clean_build_dirs(root=workspace)
        assert sentinel.read_bytes() == b"never remove"
    finally:
        _remove_directory_link(link)


def test_clean_preserves_source_spec_and_unrelated_files(packaging, tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "build.py").write_text("# synthetic workspace marker", encoding="utf-8")
    recipe = workspace / "MetodoBase.spec"
    recipe.write_text("source recipe", encoding="utf-8")
    cache = workspace / "__pycache__"
    cache.mkdir()
    marker = cache / "do-not-clean.pyc"
    marker.write_bytes(b"outside build output scope")
    for name in ("build", "dist"):
        (workspace / name).mkdir()
        (workspace / name / "artifact").write_bytes(b"old artifact")
    monkeypatch.setattr(packaging, "BASE_DIR", workspace)
    packaging.clean_build_dirs(root=workspace)
    assert recipe.read_text(encoding="utf-8") == "source recipe"
    assert marker.read_bytes() == b"outside build output scope"
    assert not (workspace / "build").exists()
    assert not (workspace / "dist").exists()


def test_import_and_version_read_never_load_product_or_touch_user_profile(tmp_path):
    home = tmp_path / "isolated profile"
    environment = dict(os.environ)
    for name in ("APPDATA", "LOCALAPPDATA", "HOME", "USERPROFILE", "XDG_DATA_HOME", "METODOBASE_DATA_DIR"):
        environment[name] = str(home / name)
    environment["TRIAL_DAYS"] = "deliberately-invalid-to-detect-product-import"
    code = (
        "import importlib.util,json,sys; from pathlib import Path; "
        "spec=importlib.util.spec_from_file_location('review_build',sys.argv[1]); "
        "m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m); "
        "print(json.dumps({'version':m.read_version(Path(sys.argv[2])),"
        "'product_loaded':any(k in sys.modules for k in ('config.constantes','core.licencia','main'))}))"
    )
    child = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT / "build.py"), str(ROOT)],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=15)
    assert child.returncode == 0, child.stderr
    result = json.loads(child.stdout)
    assert result == {"version": "2.0.0", "product_loaded": False}
    assert not home.exists()


def _git(root: Path, *arguments: str):
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    return subprocess.run(["git", "-C", str(root), *arguments], env=environment,
        capture_output=True, text=True, timeout=15, check=True)


def _resource_repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q")
    for name in ("fonts/Inter/Inter-Regular.ttf", "ui_desktop/pyside/styles/amarillo_neon.qss", "assets/tracked.png"):
        item = path / name
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_bytes(b"synthetic tracked resource")
    _git(path, "add", "--all")
    return path


def test_resources_include_only_tracked_allowed_files(packaging, tmp_path):
    root = _resource_repository(tmp_path / "resource repository")
    (root / "assets/untracked.png").write_bytes(b"not reviewed")
    (root / "assets/.env").write_bytes(b"synthetic secret")
    (root / "assets/database.db").write_bytes(b"synthetic user data")
    _git(root, "add", "assets/.env", "assets/database.db")
    selected = packaging.collect_resources(root)
    sources = {Path(source).relative_to(root).as_posix() for source, _ in selected}
    assert sources == {"fonts/Inter/Inter-Regular.ttf", "ui_desktop/pyside/styles/amarillo_neon.qss", "assets/tracked.png"}
    assert all(not Path(destination).is_absolute() and ".." not in Path(destination).parts for _, destination in selected)


def test_resource_inventory_ignores_inherited_git_context(packaging, tmp_path, monkeypatch):
    correct = _resource_repository(tmp_path / "selected repository")
    wrong = _resource_repository(tmp_path / "another repository")
    (wrong / "assets/other-only.png").write_bytes(b"must not enter the selected package")
    _git(wrong, "add", "assets/other-only.png")
    monkeypatch.setenv("GIT_DIR", str(wrong / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(wrong))
    monkeypatch.setenv("GIT_INDEX_FILE", str(wrong / ".git/index"))
    selected = packaging.collect_resources(correct)
    sources = {Path(source).relative_to(correct).as_posix() for source, _ in selected}
    assert "assets/tracked.png" in sources
    assert "assets/other-only.png" not in sources


def test_resource_inventory_rejects_subdirectory_instead_of_selecting_parent_repo(packaging, tmp_path):
    root = _resource_repository(tmp_path / "resource repository")
    with pytest.raises(packaging.BuildError):
        packaging.collect_resources(root / "assets")


@pytest.mark.parametrize("failure", [subprocess.CalledProcessError(73, ["synthetic"]), OSError("synthetic spawn failure")])
def test_subprocess_errors_are_fatal(packaging, monkeypatch, failure):
    def failed(*args, **kwargs):
        raise failure
    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(packaging.BuildError):
        packaging._run(["synthetic-command-never-executed"])


def test_existing_bundle_is_rejected_before_any_build_process(packaging, tmp_path, monkeypatch):
    workspace = tmp_path / "build workspace"
    _bundle(workspace / "dist/MetodoBase")
    monkeypatch.setattr(packaging, "BASE_DIR", workspace)
    monkeypatch.setattr(packaging, "check_dependencies", lambda: None)
    monkeypatch.setattr(packaging, "source_snapshot", lambda commit: {})
    monkeypatch.setattr(packaging, "_run", lambda *a, **k: pytest.fail("stale bundle must not start a build"))
    with pytest.raises(packaging.BuildError):
        packaging.build_executable("0" * 40)


@pytest.fixture
def validator(packaging, monkeypatch):
    monkeypatch.setitem(sys.modules, "build", packaging)
    spec = importlib.util.spec_from_file_location("desktop_validation_independent_review", ROOT / "validate_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_validation_default_never_starts_a_process(packaging, validator, bundle, monkeypatch, capsys):
    packaging.write_manifest(bundle)
    monkeypatch.setattr(sys, "argv", ["validate_build.py", "--bundle", str(bundle)])
    monkeypatch.setattr(validator, "gui_smoke", lambda *a, **k: pytest.fail("GUI opt-in required"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("static validation must not spawn"))
    assert validator.main() == 0
    assert json.loads(capsys.readouterr().out) == {"manifest_verified": True, "gui_executed": False}


def test_gui_orchestration_isolated_and_checks_receipt_without_launch(packaging, validator, bundle, monkeypatch):
    packaging.write_manifest(bundle)
    monkeypatch.setenv("DATABASE_URL", "synthetic-secret-never-inherit")
    monkeypatch.setenv("RESEND_API_KEY", "synthetic-secret-never-inherit")
    calls = []

    def synthetic_process(command, **kwargs):
        calls.append((command, kwargs))
        root = kwargs["cwd"]
        env = kwargs["env"]
        assert command == [str(bundle / ("MetodoBase.exe" if sys.platform == "win32" else "MetodoBase"))]
        assert root != ROOT and root.is_absolute()
        assert "DATABASE_URL" not in env and "RESEND_API_KEY" not in env
        assert env["QT_QPA_PLATFORM"] == "offscreen"
        for name in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME", "XDG_DATA_HOME", "METODOBASE_DATA_DIR"):
            assert Path(env[name]).is_relative_to(root)
        (root / "receipt.json").write_text(json.dumps({
            "nonce": env["METODOBASE_DESKTOP_SMOKE_NONCE"], "ok": True,
            "qt_platform": "offscreen", "python_network_blocked": True,
            "os_network_isolation_verified": False, "product_flow_executed": False,
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", synthetic_process)
    receipt = validator.gui_smoke(bundle)
    assert len(calls) == 1
    assert "nonce" not in receipt
    assert receipt["os_network_isolation_verified"] is False
    assert not calls[0][1]["cwd"].exists()


@pytest.mark.parametrize("defect", ["missing", "nonce", "ok", "qt_platform", "python_network_blocked", "invalid-json"])
def test_gui_receipt_failure_cannot_be_reported_success(packaging, validator, bundle, monkeypatch, defect):
    packaging.write_manifest(bundle)

    def synthetic_process(command, **kwargs):
        receipt = {"nonce": kwargs["env"]["METODOBASE_DESKTOP_SMOKE_NONCE"], "ok": True,
                   "qt_platform": "offscreen", "python_network_blocked": True}
        if defect not in ("missing", "invalid-json"):
            receipt[defect] = "invalid" if defect in ("nonce", "qt_platform") else False
        if defect != "missing":
            (kwargs["cwd"] / "receipt.json").write_text("{" if defect == "invalid-json" else json.dumps(receipt), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", synthetic_process)
    with pytest.raises(packaging.BuildError):
        validator.gui_smoke(bundle)


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "spawn"])
def test_gui_process_failure_cannot_be_reported_success(packaging, validator, bundle, monkeypatch, failure):
    packaging.write_manifest(bundle)
    roots = []

    def synthetic_process(command, **kwargs):
        roots.append(kwargs["cwd"])
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 0.01)
        if failure == "spawn":
            raise OSError("synthetic process unavailable")
        return subprocess.CompletedProcess(command, 73)

    monkeypatch.setattr(subprocess, "run", synthetic_process)
    with pytest.raises(packaging.BuildError):
        validator.gui_smoke(bundle)
    assert roots and not roots[0].exists()


def _frozen_repository(tmp_path: Path):
    root = _resource_repository(tmp_path / "frozen repository")
    _git(root, "-c", "user.name=Packaging Review", "-c", "user.email=packaging-review@example.invalid",
         "commit", "-q", "-m", "Synthetic packaging source")
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    return root, head


def test_source_snapshot_rejects_wrong_head_dirty_and_new_files(packaging, tmp_path, monkeypatch):
    root, head = _frozen_repository(tmp_path)
    monkeypatch.setattr(packaging, "BASE_DIR", root)
    assert "assets/tracked.png" in packaging.source_snapshot(head)
    with pytest.raises(packaging.BuildError):
        packaging.source_snapshot("0" * 40)
    extra = root / "new-source.py"
    extra.write_text("# not reviewed", encoding="utf-8")
    with pytest.raises(packaging.BuildError):
        packaging.source_snapshot(head)
    extra.unlink()
    (root / "assets/tracked.png").write_bytes(b"changed source")
    with pytest.raises(packaging.BuildError):
        packaging.source_snapshot(head)


def test_changed_source_during_synthetic_build_is_rejected_before_manifest(packaging, tmp_path, monkeypatch):
    workspace = tmp_path / "synthetic build workspace"
    workspace.mkdir()
    monkeypatch.setattr(packaging, "BASE_DIR", workspace)
    monkeypatch.setattr(packaging, "check_dependencies", lambda: None)
    snapshots = iter([{"main.py": "before"}, {"main.py": "after"}])
    monkeypatch.setattr(packaging, "source_snapshot", lambda commit: next(snapshots))
    monkeypatch.setattr(packaging, "_run", lambda *a, **k: _bundle(workspace / "dist/MetodoBase"))
    with pytest.raises(packaging.BuildError):
        packaging.build_executable("0" * 40)
    assert not (workspace / "dist/MetodoBase/build-manifest.json").exists()
