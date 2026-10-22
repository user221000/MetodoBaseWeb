"""Materialize authenticated35 web/test blobs for unchanged physical35 tests.

This is a separate historical source, never an old database under models37.
No Desktop runtime/test is selected. No environment or dependency is copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from tests.ci_web37.raw_git import raw_blobs

ROOT = Path(__file__).resolve().parents[2]
HISTORICAL35 = "b17c08efe9c7debff3d98321b59e164ee42803e5"
MODULE35 = "tests/test_nutrition35_migrations.py"
TREES = {"api", "web", "core", "src", "utils", "config", "tests", "fonts", "static"}


def selected(name):
    parts = name.split("/")
    return parts[0] in TREES or (len(parts) == 1 and (
        name.endswith((".py", ".ini", ".lock", ".sh")) or name == ".gitattributes"))


def materialize(destination: Path):
    destination = destination.absolute()
    if destination.exists() or destination.is_relative_to(ROOT):
        raise ValueError("Historical35 source needs a new directory outside the current checkout")
    revision = subprocess.check_output(["git", "--no-replace-objects", "rev-parse", HISTORICAL35],
                                       cwd=ROOT).decode().strip()
    if revision != HISTORICAL35:
        raise ValueError("Historical35 commit differs")
    listing = subprocess.check_output(["git", "--no-replace-objects", "ls-tree", "-r", "-z", HISTORICAL35],
                                      cwd=ROOT).split(b"\0")
    files = {}
    for record in listing:
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        name = raw_name.decode("utf8")
        if not selected(name):
            continue
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise ValueError("Historical35 source contains an unsupported selected object")
        if name.startswith(("/", "\\")) or any(part in {"", ".", ".."} for part in name.split("/")):
            raise ValueError("Historical35 source path differs")
        if "\\" in name or ":" in name or name.casefold() in {old.casefold() for old in files}:
            raise ValueError("Historical35 path alias differs")
        files[name] = (oid.decode(), mode.decode())
    if MODULE35 not in files:
        raise ValueError("Historical35 physical module is absent")
    current = (ROOT / MODULE35).read_bytes().replace(b"\r\n", b"\n")
    original = subprocess.check_output(["git", "--no-replace-objects", "show", HISTORICAL35 + ":" + MODULE35], cwd=ROOT)
    if current != original.replace(b"\r\n", b"\n"):
        raise ValueError("Original physical35 assertions differ from their historical source")
    destination.mkdir(mode=0o700)
    records = []
    for name, raw, oid, mode in raw_blobs(ROOT, files):
        target = destination.joinpath(*name.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open("xb") as out:
            out.write(raw)
        target.chmod(int(mode, 8) & 0o777)
        records.append({"path": name, "git_blob": oid, "raw_sha256": hashlib.sha256(raw).hexdigest()})
    if {row["path"] for row in records} != set(files):
        raise ValueError("Historical35 materialization omitted selected source")
    return {"scope": "authenticated_historical35_web_test_blobs_not_current37_runtime",
            "commit": HISTORICAL35, "files": records,
            "physical_module": MODULE35, "original_assertions_unchanged": True,
            "Desktop_execution": False, "dependencies_copied": False,
            "raw_git_blobs_without_archive_export_or_checkout_filters": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.output)
    with args.manifest.open("x", encoding="utf8") as out:
        json.dump(receipt, out, indent=2)
        out.write("\n")
    print(json.dumps({"commit": HISTORICAL35, "authenticated_source_files": len(receipt["files"]),
                      "original_physical_module_preserved": True}))


if __name__ == "__main__":
    main()
