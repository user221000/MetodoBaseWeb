"""Scan a reproducible deliverable snapshot without printing secret values.

Gitleaks must be installed externally and verified against its release checksum.
Only tracked and unignored candidate files are copied. The sanitized report
contains locations/rules and source hashes, never matches, secrets or author
metadata. Exit1 alone cannot distinguish findings from a partial/error scan.
Historical Git objects and ignored local files are outside this tree scan.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

try:
    from scripts.reviewed_scan_locations import load_reviewed_locations
except ModuleNotFoundError:  # Direct `python scripts/scan_secrets.py` invocation.
    from reviewed_scan_locations import load_reviewed_locations

ROOT = Path(__file__).resolve().parents[1]
_CAPTURE_LIMIT = 4 * 1024 * 1024
_COMPLETE = re.compile(r"\S+ INF scanned ~([1-9][0-9]*) bytes "
    r"\([0-9]+(?:\.[0-9]{2})? (?:bytes|KB|MB|GB)\) in (?:[0-9]+(?:\.[0-9]+)?(?:ns|µs|ms|s|m|h))+")


def _assert_windows_acl(control: int, entries: list, sid: str) -> None:
    if (type(control) is not int or control & 0x1004 != 0x1004 or len(entries) != 2
            or {row[3] for row in entries} != {sid, "S-1-5-18"}
            or any(type(value) is not int for row in entries for value in row[:3])
            or any(row[:3] != (0, 3, 0x1F01FF) for row in entries)):
        raise OSError("Private DACL principals, full-control rights or inheritance differ")


def _set_windows_private_acl(path: Path, sid: str) -> None:
    """Replace the fresh directory DACL; grants alone retain explicit ACEs."""
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(pointer), pointer]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    api.GetSecurityDescriptorDacl.argtypes = [pointer, ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(pointer), ctypes.POINTER(wintypes.BOOL)]
    api.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    api.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        pointer, pointer, pointer, pointer]
    api.SetNamedSecurityInfoW.restype = wintypes.DWORD
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    descriptor, acl = pointer(), pointer()
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"D:P(A;OICI;FA;;;{sid})(A;OICI;FA;;;SY)", 1, ctypes.byref(descriptor), None):
        raise OSError("Cannot construct private DACL")
    try:
        present, defaulted = wintypes.BOOL(), wintypes.BOOL()
        if (not api.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                ctypes.byref(acl), ctypes.byref(defaulted)) or not present or not acl
                or api.SetNamedSecurityInfoW(str(path), 1, 0x80000004,
                    None, None, acl, None) != 0):
            raise OSError("Cannot establish private DACL")
    finally:
        kernel.LocalFree(descriptor)


def _verify_private_boundary(path: Path, sid: str | None) -> None:
    if os.name != "nt":
        if path.stat().st_mode & 0o777 != 0o700 or path.stat().st_uid != os.getuid():
            raise OSError("Private boundary differs")
        return
    import ctypes
    from ctypes import wintypes
    import struct

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        pointer, pointer, ctypes.POINTER(pointer), pointer, ctypes.POINTER(pointer)]
    api.GetNamedSecurityInfoW.restype = wintypes.DWORD
    api.GetSecurityDescriptorControl.argtypes = [pointer, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    api.GetSecurityDescriptorControl.restype = wintypes.BOOL
    api.GetAclInformation.argtypes = [pointer, pointer, wintypes.DWORD, wintypes.DWORD]
    api.GetAclInformation.restype = wintypes.BOOL
    api.GetAce.argtypes = [pointer, wintypes.DWORD, ctypes.POINTER(pointer)]
    api.GetAce.restype = wintypes.BOOL
    api.ConvertSidToStringSidW.argtypes = [pointer, ctypes.POINTER(wintypes.LPWSTR)]
    api.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    descriptor, acl = pointer(), pointer()
    if api.GetNamedSecurityInfoW(str(path), 1, 4, None, None, ctypes.byref(acl), None,
                                 ctypes.byref(descriptor)) != 0:
        raise OSError("Cannot verify private DACL")
    try:
        control, revision = wintypes.WORD(), wintypes.DWORD()
        information = (wintypes.DWORD * 3)()
        if (not acl or not api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision))
                or not api.GetAclInformation(acl, information, ctypes.sizeof(information), 2)):
            raise OSError("Cannot inspect private DACL")
        entries = []
        for index in range(information[0]):
            ace = pointer()
            if not api.GetAce(acl, index, ctypes.byref(ace)):
                raise OSError("Cannot inspect private ACE")
            kind, flags, size, mask = struct.unpack("<BBHI", ctypes.string_at(ace, 8))
            text = wintypes.LPWSTR()
            if size < 16 or not api.ConvertSidToStringSidW(pointer(ace.value + 8), ctypes.byref(text)):
                raise OSError("Cannot inspect private principal")
            try:
                entries.append((kind, flags, mask, text.value))
            finally:
                kernel.LocalFree(ctypes.cast(text, pointer))
        _assert_windows_acl(control.value, entries, sid)
    finally:
        kernel.LocalFree(descriptor)


def _private_evidence(requested: Path | None) -> Path:
    """A fresh private boundary precedes diagnostic/report/snapshot payloads."""
    if requested is not None:
        if not requested.is_absolute() or requested.exists() or requested.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Scanner evidence requires a fresh absolute path outside the deliverable")
        requested.mkdir(parents=True, mode=0o700)
        path = requested
    else:
        path = Path(tempfile.mkdtemp(prefix="metodobase-secrets-evidence-"))
        if path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Scanner evidence must be outside the deliverable")
    try:
        sid = None
        if os.name == "nt":
            identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                capture_output=True, text=True, check=True).stdout
            sid = next(csv.reader(io.StringIO(identity)))[1]
            _set_windows_private_acl(path, sid)
        else:
            path.chmod(0o700)
        _verify_private_boundary(path, sid)
        if os.name == "nt":
            boundary = subprocess.run(["icacls", str(path)], capture_output=True, check=True).stdout
            (path / "boundary-before-payload.private.txt").write_bytes(boundary)
    except (OSError, subprocess.SubprocessError, IndexError, StopIteration):
        raise RuntimeError("Private scanner evidence boundary failed; output withheld") from None
    return path


def _capture(path: Path, value: bytes | str | None) -> bool:
    raw = value.encode("utf8") if isinstance(value, str) else value or b""
    if not isinstance(raw, bytes):
        raise RuntimeError("Secret scanner returned invalid diagnostics; output withheld")
    path.write_bytes(raw[:_CAPTURE_LIMIT])
    return len(raw) <= _CAPTURE_LIMIT


def _require_complete(stderr: bytes | str | None, findings: int) -> int:
    """Only the exact successful8.30.1 summary may establish completion."""
    try:
        text = stderr.decode("utf8") if isinstance(stderr, bytes) else stderr
        lines = text.splitlines() if isinstance(text, str) else []
        summary = _COMPLETE.fullmatch(lines[0]) if len(lines) == 2 else None
        suffix = (f"WRN leaks found: {findings}" if findings else "INF no leaks found")
        if summary is None or re.fullmatch(r"\S+ " + re.escape(suffix), lines[1]) is None:
            raise ValueError("Missing complete summary")
        return int(summary.group(1))
    except (UnicodeError, ValueError):
        raise RuntimeError("Secret scanner did not prove complete execution; output withheld") from None

# Gitleaks 8.30.1 can return a partial Match/Secret at its 100000-byte
# fragment boundary. These two public build manifests were independently
# reviewed in full. A whole-file pin (including encoding/newlines), the copied
# bytes and the complete physical line must all agree; a truncated scanner
# match is never sufficient to classify a finding as a source fingerprint.
_FRAGMENT_FINGERPRINT_PINS = {
    "docs/implementation/20261018-evolution/evidence/desktop-real-build-9f3f32e-source.json": (
        frozenset({
            "3fb6f8d286ca2d7623958864eee58fea36c9c4d2995e3ea70a4b4a8f462c6ca4",
            "be8ead03dfb90d2f9c632e4d2e37956bfba03c3afaa0bb80ff46084e7eec97c1",
        }),
        "819d66037455156cb96888a31bd7f6377a07ddc4a3bbbce95479c040c7b24f03",
    ),
    "docs/implementation/20261018-evolution/evidence/desktop-real-build-9f3f32e-lf-source.json": (
        frozenset({
            "271d1c9e1bffc5a1e6ed1db56fdabc9673b663a37ee18ba56ffe3bed7b906b8a",
            "47e002ad2568ed7bba35407ec44ab98313730198325a89df89d02ff8bf31b8e5",
        }),
        "8f40c42dc97ded7a10f3600feb2967bec38babd080cf82ff798bff35207b83ee",
    ),
}


def _finding_name(value: object, snapshot: Path) -> str:
    """Require a canonical relative finding path inside the copied tree."""
    if not isinstance(value, str) or not value:
        raise ValueError("Secret scanner returned an invalid file path")
    path = Path(value)
    if path.is_absolute():
        path = path.relative_to(snapshot)
    if any(part in {"..", "."} for part in path.parts):
        raise ValueError("Secret scanner returned a noncanonical file path")
    name = path.as_posix()
    if not (snapshot / path).resolve().is_relative_to(snapshot):
        raise ValueError("Secret scanner returned an outside file path")
    return name


def _classify_fragment_fingerprint(
    item: dict, name: str, snapshot: Path, source_hashes: dict[str, str],
) -> dict | None:
    """Classify only the two reviewed immutable manifest lines.

    This does not establish a general hash allowlist. Any byte, path, rule,
    line, encoding or snapshot change leaves the finding blocking. The caller
    must still reject the entire run when its source/file-set stability check
    fails. Match, Secret and Finding.Line are deliberately never consulted.
    """
    pin = _FRAGMENT_FINGERPRINT_PINS.get(name)
    if pin is None or item.get("RuleID") != "generic-api-key":
        return None
    if (type(item.get("StartLine")) is not int
            or type(item.get("EndLine")) is not int
            or item["StartLine"] != 3081 or item["EndLine"] != 3081):
        return None
    file_hashes, line_hash = pin
    digest = source_hashes.get(name)
    if digest not in file_hashes:
        return None
    try:
        content = (snapshot / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            return None
        content.decode("utf-8", errors="strict")
        line = content.split(b"\n")[3080]
    except (OSError, UnicodeDecodeError, IndexError):
        return None
    # One terminal CR is the sole normalization, after checking the raw file.
    if line.endswith(b"\r"):
        line = line[:-1]
    if hashlib.sha256(line).hexdigest() != line_hash:
        return None
    return {"file": name, "line": 3081, "rule": "generic-api-key",
        "file_sha256": digest, "physical_line_sha256": line_hash,
        "reason": "reviewed immutable public source fingerprint; gitleaks 8.30.1 fragment boundary"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gitleaks", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--private-evidence", type=Path,
                        help="Fresh absolute diagnostic directory outside the deliverable; defaults to private Temp")
    args = parser.parse_args()
    tool = args.gitleaks.resolve(strict=True)
    report = args.report.resolve()
    private = _private_evidence(args.private_evidence)
    environment = {key: value for key, value in os.environ.items()
        if not key.upper().startswith("GITLEAKS_")}
    version = subprocess.run([str(tool), "version"], check=True, capture_output=True,
        text=True, env=environment, timeout=15).stdout.strip()
    if version != "8.30.1":
        raise RuntimeError("Reviewed secret scanner version must be 8.30.1")
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True)
    paths = sorted({value.decode("utf-8") for value in result.stdout.split(b"\0") if value})
    source_hashes = {}
    encoding_transforms = {}
    with tempfile.TemporaryDirectory(prefix="metodobase-secrets-", dir=private) as temporary:
        workspace = Path(temporary)
        snapshot = workspace / "snapshot"
        snapshot.mkdir()
        for name in paths:
            source = ROOT / name
            if not source.is_file() or source.resolve() == report:
                continue  # Deleted files and this run's generated report.
            if source.is_symlink() or not source.resolve().is_relative_to(ROOT):
                raise ValueError("Deliverable contains a symlink/outside file: " + name)
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            content = source.read_bytes()
            source_hashes[name] = hashlib.sha256(content).hexdigest()
            # Gitleaks treats BOM UTF16 as binary and misses ASCII secrets in
            # it. Transcode only the private snapshot; retain original hashes.
            encoding = None
            if content.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
                encoding = "utf-32"
            elif content.startswith((b"\xff\xfe", b"\xfe\xff")):
                encoding = "utf-16"
            elif content.startswith(b"\xef\xbb\xbf"):
                encoding = "utf-8-sig"
            if encoding:
                content = content.decode(encoding).encode("utf-8")
                encoding_transforms[name] = {"source_encoding": encoding,
                    "scanner_encoding": "utf-8", "scanner_sha256": hashlib.sha256(content).hexdigest()}
            destination.write_bytes(content)
        reviewed = load_reviewed_locations(snapshot, source_hashes, version)
        raw_report = workspace / "raw-redacted.json"
        empty_ignore = workspace / "empty.gitleaksignore"
        empty_ignore.write_text("", encoding="utf-8")
        try:
            scan = subprocess.run([str(tool), "dir", str(snapshot), "--config", str(snapshot / ".gitleaks.toml"),
                "--redact=100", "--no-banner", "--no-color", "--log-level=info",
                "--ignore-gitleaks-allow", "--gitleaks-ignore-path", str(empty_ignore),
                "--max-decode-depth=5", "--max-archive-depth=0",
                "--report-format=json", "--report-path", str(raw_report), "--timeout=0"],
                check=False, capture_output=True, cwd=workspace, env=environment, timeout=600)
        except subprocess.TimeoutExpired as error:
            _capture(private / "scan.stdout.private.log", error.output)
            _capture(private / "scan.stderr.private.log", error.stderr)
            if raw_report.is_file():
                (private / "raw-redacted.private.json").write_bytes(raw_report.read_bytes())
            raise RuntimeError("Secret scanner timed out before complete execution; output withheld") from None
        stdout_complete = _capture(private / "scan.stdout.private.log", scan.stdout)
        stderr_complete = _capture(private / "scan.stderr.private.log", scan.stderr)
        if raw_report.is_file():
            (private / "raw-redacted.private.json").write_bytes(raw_report.read_bytes())
        if not stdout_complete or not stderr_complete:
            raise RuntimeError("Secret scanner diagnostic limit exceeded; output withheld")
        if scan.stdout not in {b"", ""}:
            raise RuntimeError("Secret scanner returned unexpected stdout; output withheld")
        if scan.returncode not in {0, 1} or not raw_report.is_file():
            raise RuntimeError(f"Secret scanner failed; exit={scan.returncode}; output withheld")
        raw = json.loads(raw_report.read_text(encoding="utf-8"))
        if not isinstance(raw, list) or bool(raw) != (scan.returncode == 1):
            raise RuntimeError("Secret scanner returned inconsistent findings; output withheld")
        scanned_bytes = _require_complete(scan.stderr, len(raw))
        findings = []
        classified = []
        for item in raw:
            name = _finding_name(item["File"], snapshot)
            classification = _classify_fragment_fingerprint(item, name, snapshot, source_hashes)
            if classification is None:
                classification = reviewed.classify(item, name)
            if classification is not None:
                classified.append(classification)
                continue
            findings.append({"file": name, "line": item["StartLine"], "rule": item["RuleID"],
                "fingerprint": item.get("Fingerprint"), "file_sha256": source_hashes.get(name)})
    changed = [name for name, digest in source_hashes.items()
        if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    after_paths = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True)
    current = {value.decode("utf-8") for value in after_paths.stdout.split(b"\0") if value
        and (ROOT / value.decode("utf-8")).is_file()
        and (ROOT / value.decode("utf-8")).resolve() != report}
    changed.extend("added:" + name for name in sorted(current - source_hashes.keys()))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"tool": "gitleaks", "version": version,
        "binary_sha256": hashlib.sha256(tool.read_bytes()).hexdigest(),
        "scan_complete": True, "scanned_bytes": scanned_bytes,
        "scope": "tracked and unignored deliverable tree; no git history or ignored files",
        "exit_code": scan.returncode, "effective_exit_code": 2 if changed else (1 if findings else 0),
        "source_stable": not changed, "changed_files": changed,
        "raw_finding_count": len(raw), "classified_finding_count": len(classified),
        "remaining_finding_count": len(findings), "classified_findings": classified,
        "files": source_hashes, "encoding_transforms": encoding_transforms, "findings": findings},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gitleaks {version}: {len(source_hashes)} files, {len(raw)} raw findings, "
        f"{len(classified)} classified, {len(findings)} remaining; values withheld")
    return 2 if changed else (1 if findings else 0)


if __name__ == "__main__":
    raise SystemExit(main())
