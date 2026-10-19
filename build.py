"""Build the desktop GUI from its spec without importing product settings."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "MetodoBase"
MANIFEST_NAME = "build-manifest.json"
TOOL_VERSIONS = {"pyinstaller": "6.22.3", "pyinstaller-hooks-contrib": "2026.8"}
RESOURCE_ROOTS = ("assets", "fonts", "static", "ui_desktop/pyside/styles")
RESOURCE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".icns", ".ttf", ".otf", ".qss"}
REQUIRED_RESOURCES = ("fonts/Inter/Inter-Regular.ttf", "ui_desktop/pyside/styles/amarillo_neon.qss")
# OPS10: retain the unverified design reference in source, never distribute it.
EXCLUDED_RESOURCES = frozenset({"assets/design-reference.png"})
EXCLUDED_BUNDLE_RESOURCES = frozenset("_internal/" + name for name in EXCLUDED_RESOURCES)
HIDDEN_IMPORTS = (
    "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui", "core.branding", "core.licencia",
    "ui_desktop.pyside.theme_manager", "ui_desktop.pyside.flow_controller", "ui_desktop.pyside.gym_app_window",
    "passlib.handlers.bcrypt", "passlib.handlers.pbkdf2", "reportlab.graphics.barcode.code128", "reportlab.graphics.barcode.code39",
)


class BuildError(RuntimeError):
    """The candidate cannot be built or accepted safely."""


def _linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _check_tree_path(path: Path, root: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise BuildError("Path escapes the expected root") from exc
    for part in (root, *(root / Path(*relative.parts[:i]) for i in range(1, len(relative.parts) + 1))):
        if _linked(part):
            raise BuildError("Symlink or junction in candidate path")
    if not path.resolve().is_relative_to(root.resolve()):
        raise BuildError("Resolved path escapes the expected root")


def read_version(root: Path = BASE_DIR) -> str:
    tree = ast.parse((root / "config/constantes.py").read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+){1,3}", value):
                return value
    raise BuildError("Missing literal product VERSION")


def _run(command: list[str], *, cwd: Path = BASE_DIR, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, cwd=cwd, env=env, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("Packaging command failed") from exc


def _git_read(root: Path, *args: str, input_data: bytes | None = None) -> bytes:
    """Read Git objects without user/global attributes, hooks or content filters."""
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM="1", GIT_NO_REPLACE_OBJECTS="1")
    command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}",
               "-c", f"core.attributesFile={os.devnull}", "-c", f"core.excludesFile={os.devnull}",
               "-c", "core.autocrlf=false", "-c", "core.eol=lf", *args]
    try:
        return subprocess.run(command, cwd=root, env=env, input=input_data, check=True,
                              capture_output=True, timeout=60).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise BuildError("Controlled Git read failed") from exc


def collect_resources(root: Path = BASE_DIR) -> list[tuple[str, str]]:
    """Only supported tracked assets; never broad directories or user config."""
    root = root.absolute()
    top = _git_read(root, "rev-parse", "--show-toplevel")
    if Path(top.decode("utf-8").strip()).resolve() != root.resolve():
        raise BuildError("Resource root must be the selected worktree root")
    inventory = _git_read(root, "ls-files", "-z", "--", *RESOURCE_ROOTS)
    resources, selected, folded = [], set(), set()
    for name in inventory.decode("utf-8").split("\0"):
        if not name:
            continue
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise BuildError("Unsafe tracked resource path")
        if relative.suffix.lower() not in RESOURCE_SUFFIXES:
            continue
        if name.casefold() in folded or _forbidden(relative):
            raise BuildError("Private or case-colliding tracked resource")
        folded.add(name.casefold())
        if relative.as_posix().casefold() in EXCLUDED_RESOURCES:
            continue
        source = root / relative
        _check_tree_path(source, root)
        if not source.is_file():
            raise BuildError("A tracked resource is missing")
        resources.append((str(source), relative.parent.as_posix()))
        selected.add(relative.as_posix())
    if not set(REQUIRED_RESOURCES).issubset(selected):
        raise BuildError("Required GUI resources are missing")
    return sorted(resources)


def _forbidden(relative: Path) -> bool:
    parts = [part.lower() for part in relative.parts]
    directories = {".git", ".venv", "venv", ".env", "backups", "registros", "planes", "logs", "datos"}
    name = parts[-1]
    return (relative.as_posix().casefold() in EXCLUDED_BUNDLE_RESOURCES or
            any(part in directories for part in parts) or name.startswith(".env") or
            (name.startswith(("licencia", "license_cache", "license_status")) and name.endswith(".json")) or
            name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".lic", ".dump", ".bak", ".log", ".key")))


def bundle_files(bundle: Path) -> dict[str, Path]:
    bundle = Path(bundle).absolute()
    if _linked(bundle) or not bundle.is_dir():
        raise BuildError("Expected a real onedir bundle directory")
    files, folded = {}, set()
    def walk_error(exc: OSError) -> None:
        raise BuildError("Bundle directory cannot be read completely") from exc

    for directory, directories, filenames in os.walk(bundle, followlinks=False, onerror=walk_error):
        for name in directories + filenames:
            path = Path(directory) / name
            _check_tree_path(path, bundle)
            relative = path.relative_to(bundle)
            if "\\" in relative.as_posix() or ":" in relative.as_posix() or _forbidden(relative):
                raise BuildError("Private data or unsafe name in bundle")
            if relative.as_posix().casefold() in folded:
                raise BuildError("Case-colliding bundle path")
            folded.add(relative.as_posix().casefold())
            if not path.is_file() and not path.is_dir():
                raise BuildError("Unexpected special file in bundle")
            if path.is_file() and relative.as_posix() != MANIFEST_NAME:
                files[relative.as_posix()] = path
    return dict(sorted(files.items()))


def validate_bundle(bundle: Path, target_platform: str | None = None) -> Path:
    files = bundle_files(bundle)
    target = target_platform or sys.platform
    executable_name = APP_NAME + (".exe" if target == "win32" else "")
    if executable_name not in files or files[executable_name].stat().st_size == 0:
        raise BuildError("Desktop executable is missing or empty")
    if not all("_internal/" + name in files for name in REQUIRED_RESOURCES):
        raise BuildError("Required bundled GUI resources are missing")
    plugins = {"win32": ("qwindows.dll", "qoffscreen.dll"),
               "linux": ("libqxcb.so", "libqoffscreen.so"),
               "darwin": ("libqcocoa.dylib", "libqoffscreen.dylib")}
    if target not in plugins:
        raise BuildError("Target platform needs an explicit packaging contract")
    for plugin in plugins[target]:
        if not any(f"_internal/PySide6/{prefix}plugins/platforms/{plugin}" in files for prefix in ("", "Qt/")):
            raise BuildError("Required Qt platform plugin is missing")
    return Path(bundle).absolute() / executable_name


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_manifest(bundle: Path, target_platform: str | None = None, *, source_commit: str | None = None) -> Path:
    validate_bundle(bundle, target_platform)
    manifest = {"schema": 1, "platform": target_platform or sys.platform,
                "files": {name: {"sha256": _digest(path), "bytes": path.stat().st_size} for name, path in bundle_files(bundle).items()}}
    if source_commit is not None:
        manifest["source_commit"] = source_commit
        manifest["tooling"] = TOOL_VERSIONS
        manifest["app_version"] = read_version(BASE_DIR)
        if manifest["platform"] == "win32":
            verify_windows_amd64(validate_bundle(bundle, "win32"))
            manifest["architecture"] = "x86_64"
    target = Path(bundle) / MANIFEST_NAME
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def verify_manifest(bundle: Path) -> dict:
    files = bundle_files(bundle)
    manifest_path = Path(bundle) / MANIFEST_NAME
    if _linked(manifest_path):
        raise BuildError("Manifest must be a regular file")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest["files"]
        if manifest.get("schema") != 1 or not isinstance(expected, dict) or set(expected) != set(files):
            raise BuildError("Bundle manifest does not match its file inventory")
        validate_bundle(bundle, manifest["platform"])
        for name, path in files.items():
            if expected[name] != {"sha256": _digest(path), "bytes": path.stat().st_size}:
                raise BuildError("Bundle bytes differ from the manifest")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BuildError("Bundle manifest is missing or invalid") from exc
    return manifest


def verify_windows_amd64(executable: Path) -> None:
    """Read the PE machine field; host architecture is not artifact evidence."""
    with executable.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise BuildError("Installer source is not a Windows PE executable")
        offset = struct.unpack_from("<I", header, 60)[0]
        if offset > executable.stat().st_size - 6:
            raise BuildError("Invalid PE header offset")
        stream.seek(offset)
        pe = stream.read(6)
        if pe[:4] != b"PE\0\0" or struct.unpack_from("<H", pe, 4)[0] != 0x8664:
            raise BuildError("This installer contract requires a verified Windows x64 executable")


def _inno_string(value: str) -> str:
    if any(character in value for character in ('"', "\r", "\n", "{", "}")):
        raise BuildError("Installer input contains unsupported preprocessor characters")
    return '"' + value + '"'


def prepare_installer(bundle: Path, expected_commit: str, output_dir: Path | None = None) -> Path:
    """Prepare inputs from a verified bundle; never run or install Inno Setup."""
    source_before = source_snapshot(expected_commit)
    bundle = Path(bundle).absolute()
    manifest = verify_manifest(bundle)
    if (manifest.get("platform") != "win32" or manifest.get("architecture") != "x86_64" or
            manifest.get("source_commit") != expected_commit or manifest.get("app_version") != read_version(BASE_DIR)):
        raise BuildError("Installer requires a versioned Windows x64 bundle of the exact source commit")
    verify_windows_amd64(validate_bundle(bundle, "win32"))
    output = (output_dir or BASE_DIR / "dist" / "installer-inputs").absolute()
    if output.resolve().is_relative_to(bundle.resolve()) or _linked(output) or _linked(output.parent):
        raise BuildError("Installer inputs must be outside the bundle without links")
    if output.exists():
        raise BuildError("Use a new installer input directory to preserve previous evidence")
    files = {**bundle_files(bundle), MANIFEST_NAME: bundle / MANIFEST_NAME}
    lines = []
    for name, path in sorted(files.items()):
        relative = Path(name)
        destination = "{app}" + ("\\" + str(relative.parent).replace("/", "\\") if relative.parent != Path(".") else "")
        # {app} is the one intended Inno constant. Source names are literal.
        source = _inno_string(str(path))
        suffix = "" if relative.parent == Path(".") else "\\" + relative.parent.as_posix().replace("/", "\\")
        _inno_string(suffix)
        lines.append(f'Source: {source}; DestDir: "{destination}"; Flags: ignoreversion')
    output.mkdir(parents=True)
    files_path = output / "verified-files.iss"
    definitions_path = output / "verified-settings.iss"
    entry_path = output / "installer-entry.iss"
    files_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    definitions = {
        "MyAppVersion": manifest["app_version"], "VerifiedSourceCommit": expected_commit,
        "VerifiedManifestSha256": _digest(bundle / MANIFEST_NAME),
        "VerifiedFilesInclude": str(files_path), "VerifiedOutputDir": str(output / "Output"),
    }
    definitions_path.write_text("".join(f"#define {key} {_inno_string(value)}\n" for key, value in definitions.items()), encoding="utf-8-sig")
    entry_path.write_text(f"#define PreparedInputs {_inno_string(str(definitions_path))}\n#include {_inno_string(str(BASE_DIR / 'setup_installer.iss'))}\n", encoding="utf-8-sig")
    if source_snapshot(expected_commit) != source_before or verify_manifest(bundle) != manifest:
        raise BuildError("Sources changed while preparing installer inputs; reject the directory")
    report = {"source_commit": expected_commit, "app_version": manifest["app_version"], "architecture": "x86_64",
              "manifest_sha256": _digest(bundle / MANIFEST_NAME), "files": len(files),
              "compiler_command": ["<verified ISCC.exe path>", str(entry_path)],
              "compiler_executed": False, "installer_tested": False, "signature_verified": False,
              "pending": ["Verify a pinned Inno compiler", "Compile and inspect payload against this manifest",
                          "Discardable Windows install/upgrade/uninstall test", "Authorized signing process"]}
    report_path = output / "installer-preparation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path


def create_distribution_zip(bundle: Path, output: Path | None = None) -> Path:
    """Publish the whole verified onedir tree, including _internal."""
    bundle = Path(bundle).absolute()
    manifest = verify_manifest(bundle)
    files = bundle_files(bundle)
    output = (Path(output) if output else bundle.parent / f"{APP_NAME}_v{read_version()}_{sys.platform}.zip").absolute()
    if output.resolve().is_relative_to(bundle.resolve()) or _linked(output) or _linked(output.parent):
        raise BuildError("ZIP output must be outside the bundle without links")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".desktop-zip-", suffix=".tmp", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in {**files, MANIFEST_NAME: bundle / MANIFEST_NAME}.items():
                archive.write(path, f"{APP_NAME}/{name}")
        verify_manifest(bundle)
        with zipfile.ZipFile(temporary) as archive:
            expected_names = {f"{APP_NAME}/{name}" for name in files} | {f"{APP_NAME}/{MANIFEST_NAME}"}
            if set(archive.namelist()) != expected_names or len(archive.namelist()) != len(expected_names):
                raise BuildError("ZIP inventory differs from the reviewed bundle")
            if json.loads(archive.read(f"{APP_NAME}/{MANIFEST_NAME}")) != manifest:
                raise BuildError("ZIP manifest changed while packaging")
            for name, expected in manifest["files"].items():
                with archive.open(f"{APP_NAME}/{name}") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != expected["sha256"]:
                        raise BuildError("ZIP payload differs from its manifest")
        os.replace(temporary, output)
        return output
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise BuildError("Distribution ZIP was not published") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def clean_build_dirs(root: Path = BASE_DIR) -> None:
    root = Path(root).absolute()
    if _linked(root) or root.resolve() == Path(root.anchor) or not (root / "build.py").is_file():
        raise BuildError("Unexpected build workspace")
    targets = [root / name for name in ("build", "dist")]
    for target in targets:
        _check_tree_path(target, root)
        if target.exists():
            bundle_files(target)
    for target in targets:
        if target.exists():
            shutil.rmtree(target)


def check_dependencies() -> None:
    for package, version in TOOL_VERSIONS.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise BuildError("Install the reviewed tooling lock in a temporary build environment") from exc
        if actual != version:
            raise BuildError("Build tooling differs from the pinned contract")


def _checkout_matches(blob: bytes, working: bytes, attributes: dict[str, str]) -> bool:
    """Only exact bytes or an explicit UTF-8 LF/CRLF checkout are supported."""
    if any(attributes.get(name, "unspecified") not in ("unspecified", "unset")
           for name in ("filter", "ident", "working-tree-encoding")):
        raise BuildError("Content filters, ident and encoded checkouts require separate review")
    text = attributes.get("text", "unspecified")
    eol = attributes.get("eol", "unspecified")
    if text not in ("unspecified", "set", "unset", "auto") or eol not in ("unspecified", "unset", "lf", "crlf"):
        raise BuildError("Unsupported committed checkout attributes")
    # Valid UTF-8 can still be binary (for example a control-byte payload).
    # Conservatively require its exact committed bytes even with text attrs;
    # Only TAB and line endings are supported controls for conversion. A lone
    # CR makes even valid UTF-8 binary to Git and must stay byte-exact too.
    binary_controls = any(value < 32 and value not in (9, 10, 13) or value == 127 for value in blob)
    lone_cr = b"\r" in blob.replace(b"\r\n", b"")
    if text == "unset" or binary_controls or lone_cr:
        return working == blob
    try:
        blob.decode("utf-8")
    except UnicodeDecodeError:
        return working == blob
    if eol == "lf":
        return b"\r\n" not in blob and working == blob
    if eol == "crlf":
        return b"\r\n" not in blob and working == blob.replace(b"\n", b"\r\n")
    # Existing historical CRLF blobs are accepted byte-for-byte. New checkout
    # conversion permits a uniform CRLF rendering of a canonical LF UTF-8 blob.
    return working == blob or (b"\r\n" not in blob and working == blob.replace(b"\n", b"\r\n"))


def source_snapshot(expected_commit: str) -> dict[str, str]:
    if not isinstance(expected_commit, str) or re.fullmatch(r"[a-f0-9]{40}", expected_commit) is None:
        raise BuildError("An explicit frozen source commit is required")
    root = BASE_DIR.absolute()
    top = _git_read(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if Path(top).resolve() != root.resolve() or _git_read(root, "rev-parse", "HEAD").decode().strip() != expected_commit:
        raise BuildError("Build requires the requested commit at the exact worktree root")
    info = Path(_git_read(root, "rev-parse", "--git-path", "info/attributes").decode("utf-8").strip())
    info = info if info.is_absolute() else root / info
    if info.exists() and any(line.strip() and not line.lstrip().startswith(b"#") for line in info.read_bytes().splitlines()):
        raise BuildError("Local info/attributes overrides are unsupported")
    tree = {}
    for entry in _git_read(root, "ls-tree", "-rz", "--full-tree", expected_commit).split(b"\0"):
        if entry:
            header, name = entry.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            name = name.decode("utf-8")
            if kind != "blob" or mode not in ("100644", "100755"):
                raise BuildError("Non-regular tracked objects require separate review")
            if Path(name).is_absolute() or ".." in Path(name).parts or "\\" in name or ":" in name:
                raise BuildError("Unsafe committed source path")
            tree[name] = (mode, oid)
    index = {}
    for entry in _git_read(root, "ls-files", "-s", "-z").split(b"\0"):
        if entry:
            header, name = entry.split(b"\t", 1)
            mode, oid, stage = header.decode("ascii").split()
            if stage != "0":
                raise BuildError("Unmerged index cannot be packaged")
            index[name.decode("utf-8")] = (mode, oid)
    if index != tree or _git_read(root, "ls-files", "--others", "--exclude-standard", "-z"):
        raise BuildError("Index or untracked source differs from the requested commit")
    attributes_raw = _git_read(root, "check-attr", "--source=" + expected_commit, "-z", "--stdin",
                               "text", "eol", "filter", "working-tree-encoding", "ident",
                               input_data=b"\0".join(name.encode("utf-8") for name in tree) + b"\0").split(b"\0")
    attributes = {name: {} for name in tree}
    for offset in range(0, len(attributes_raw) - 1, 3):
        name, attribute, value = (part.decode("utf-8") for part in attributes_raw[offset:offset + 3])
        attributes[name][attribute] = value
    oids = list(dict.fromkeys(oid for _, oid in tree.values()))
    data = _git_read(root, "cat-file", "--batch", input_data="".join(oid + "\n" for oid in oids).encode("ascii"))
    blobs, offset = {}, 0
    for expected_oid in oids:
        end = data.index(b"\n", offset)
        oid, kind, size = data[offset:end].decode("ascii").split()
        size = int(size)
        if oid != expected_oid or kind != "blob" or data[end + size + 1:end + size + 2] != b"\n":
            raise BuildError("Invalid committed object stream")
        blobs[oid] = data[end + 1:end + 1 + size]
        offset = end + size + 2
    files = {}
    for name, (_, oid) in tree.items():
        path = root / name
        _check_tree_path(path, root)
        if not path.is_file():
            raise BuildError("Tracked source is missing")
        working = path.read_bytes()
        if not _checkout_matches(blobs[oid], working, attributes[name]):
            raise BuildError("Working source bytes differ from the requested commit")
        files[name] = hashlib.sha256(working).hexdigest()
    return files


def build_executable(expected_commit: str) -> Path:
    source_before = source_snapshot(expected_commit)
    check_dependencies()
    bundle = BASE_DIR / "dist" / APP_NAME
    if bundle.exists():
        raise BuildError("Existing bundle makes a stale build ambiguous; use a fresh worktree or checked --clean")
    with tempfile.TemporaryDirectory(prefix="metodobase-build-profile-") as profile:
        allowed = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TMP", "TEMP", "LANG", "LC_ALL", "NUMBER_OF_PROCESSORS"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env.update({"PYTHON_DOTENV_DISABLED": "1", "METODOBASE_DATA_DIR": profile,
                    "APPDATA": profile, "LOCALAPPDATA": profile, "USERPROFILE": profile, "HOME": profile,
                    "PYTHONDONTWRITEBYTECODE": "1", "PYINSTALLER_CONFIG_DIR": str(Path(profile) / "pyinstaller")})
        _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(BASE_DIR / "dist"),
              "--workpath", str(BASE_DIR / "build"), str(BASE_DIR / "MetodoBase.spec")], env=env)
    if source_snapshot(expected_commit) != source_before:
        raise BuildError("Source changed during packaging; candidate rejected")
    validate_bundle(bundle)
    if sys.platform == "win32":
        shutil.copyfile(BASE_DIR / "metodobase_iniciar.bat", bundle / "metodobase_iniciar.bat")
    write_manifest(bundle, source_commit=expected_commit)
    if source_snapshot(expected_commit) != source_before:
        (bundle / MANIFEST_NAME).unlink(missing_ok=True)
        raise BuildError("Source changed during final manifest preparation; candidate rejected")
    return bundle


def run_tests() -> None:
    _run([sys.executable, "-X", "utf8", "tests/run_isolated.py", "tests/test_login_desktop.py", "tests/services",
          "tests/test_generacion_pdf.py", "tests/test_licencia.py", "tests/test_license_offline_security.py", "-q"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True, help="Exact integrated frozen commit to package")
    parser.add_argument("--clean", action="store_true", help="Remove only checked build/dist directories")
    parser.add_argument("--no-tests", action="store_true", help="Development only: omit desktop source tests")
    parser.add_argument("--test", action="store_true", help="Run isolated offscreen bundle diagnostic")
    parser.add_argument("--zip", action="store_true", help="Package the complete verified onedir tree")
    parser.add_argument("--prepare-installer", action="store_true", help="Prepare verified Inno input files without compiling")
    args = parser.parse_args(argv)
    try:
        before_tests = source_snapshot(args.source_commit)
        if args.clean:
            clean_build_dirs()
        if not args.no_tests:
            run_tests()
        if source_snapshot(args.source_commit) != before_tests:
            raise BuildError("Source changed during source tests")
        bundle = build_executable(args.source_commit)
        if args.test:
            _run([sys.executable, str(BASE_DIR / "validate_build.py"), "--bundle", str(bundle), "--gui-smoke"])
        if args.zip:
            print(create_distribution_zip(bundle))
        if args.prepare_installer:
            print(prepare_installer(bundle, args.source_commit))
        print(bundle)
        return 0
    except BuildError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
