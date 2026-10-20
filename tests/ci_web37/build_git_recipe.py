"""Materialize the reviewed finite RAW Git object proof; no object import."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_web37.git_recipe import (
    BASELINE,
    NATIVE,
    NATIVE_FILES,
    object_id,
    tree_entries,
)


def build(repository, destination):
    objects = {}

    def read(oid, kind):
        if oid not in objects:
            raw = subprocess.check_output(["git", "--no-replace-objects", "cat-file", kind, oid], cwd=repository)
            if object_id(kind, raw) != oid:
                raise ValueError("Original Git object identity differs during capture")
            objects[oid] = (kind, raw)
        if objects[oid][0] != kind:
            raise ValueError("Original Git object kind differs during capture")
        return objects[oid][1]

    def resolve(commit, path, leaf):
        oid = read(commit, "commit").split(b"\n", 1)[0].removeprefix(b"tree ").decode("ascii")
        parts = path.split("/")
        for index, part in enumerate(parts):
            kind, oid = tree_entries(read(oid, "tree"))[part]
            if kind != (leaf if index == len(parts) - 1 else "tree"):
                raise ValueError("Original Git source path kind differs during capture")
        return oid

    for path in NATIVE_FILES:
        read(resolve(NATIVE, path, "blob"), "blob")
    read(resolve(BASELINE, "requirements_web.lock", "blob"), "blob")

    def trees(oid):
        for kind, child in tree_entries(read(oid, "tree")).values():
            if kind == "tree":
                trees(child)

    trees(resolve(BASELINE, "tests/ci_google33", "tree"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as archive:
        for oid, (kind, payload) in sorted(objects.items()):
            info = zipfile.ZipInfo("objects/" + oid, (2026, 10, 20, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, kind.encode() + b" " + str(len(payload)).encode() + b"\0" + payload)
    return {"objects": len(objects), "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "commits": [NATIVE, BASELINE], "scope": "RAW objects and finite Merkle routes; no imported Git ancestry"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(build(ROOT, args.destination))
