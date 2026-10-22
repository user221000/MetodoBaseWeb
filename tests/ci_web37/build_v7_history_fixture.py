"""Export only the original V7 assertion paths and their Git Merkle frames."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

from tests.ci_web37.git_recipe import object_id, tree_entries

SOURCE = "d568634be21fe0c745d21c110e344f161d3dd4b3"
BASE = "45eba8f1d50efebd7106106f8aa20bfda3c7b440"
SCAN = "b0fa556346a0097cd8a4372d586184a100758737"
PROPOSAL = "docs/implementation/20261018-evolution/evidence/security-r05-last1-independent-20261020/finite-proposal.zip"


def build(repository):
    def git(*args):
        return subprocess.check_output(["git", "--no-replace-objects", *args], cwd=repository)

    def raw(commit, name):
        return git("show", commit + ":" + name)

    with zipfile.ZipFile(io.BytesIO(raw(SOURCE, PROPOSAL))) as original:
        if original.namelist() != ["proposal.json"]:
            raise ValueError("The original V7 proposal framing differs")
        proposal = json.loads(original.read("proposal.json"))
    if len(proposal["witnesses"]) != 1:
        raise ValueError("The V7 original assertion has exactly one named source")
    witness = proposal["witnesses"][0]
    stable = ["scripts/reviewed_scan_locations.py", ".gitleaks.toml", "scripts/scan_secrets.py",
              "tests/test_secret_scan_finite_v6.py", "tests/test_security_r05_v5_current_peer.py",
              *[f"scripts/data/reviewed_scan_locations_v{n}.zip" for n in range(1, 7)]]
    reads = {(commit, name) for commit in ("HEAD", BASE) for name in stable}
    reads.add((SCAN, witness["file"]))
    phase = {"aliases": {"HEAD": SOURCE}, "git_reads": sorted(map(list, reads)), "files": {},
             "required_cases": 15, "tests": ["tests/test_secret_scan_finite_v7.py"],
             "scope": "authentic_frozen_V7_history_no_current_runtime_or_fullscan_claim"}
    routes = {(SOURCE if commit == "HEAD" else commit, name) for commit, name in reads}

    def add(commit, name, expected=None):
        payload = raw(commit, name)
        digest = hashlib.sha256(payload).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError("The original V7 physical source differs")
        routes.add((commit, name))
        phase["files"][name] = {"commit": commit, "path": name, "framing": "Git exact",
                                "materialized_sha256": digest}

    for name in [*stable, "scripts/data/reviewed_scan_locations_v7.zip", PROPOSAL, *phase["tests"]]:
        add(SOURCE, name)
    add(SCAN, witness["file"], witness["file_sha256"])
    objects = {}

    def get(oid, kind):
        if oid not in objects:
            actual = git("cat-file", "-t", oid).strip().decode("ascii")
            payload = git("cat-file", actual, oid)
            if actual != kind or object_id(kind, payload) != oid:
                raise ValueError("The original V7 Git frame differs")
            objects[oid] = (kind, payload)
        if objects[oid][0] != kind:
            raise ValueError("A V7 Git object cannot have two original kinds")
        return objects[oid][1]

    for commit, name in sorted(routes):
        first = get(commit, "commit").split(b"\n", 1)[0]
        if not first.startswith(b"tree "):
            raise ValueError("The original V7 commit root is malformed")
        oid = first[5:].decode("ascii")
        for index, part in enumerate(name.split("/")):
            kind, oid = tree_entries(get(oid, "tree"))[part]
            final = index == len(name.split("/")) - 1
            if kind != ("blob" if final else "tree"):
                raise ValueError("The original V7 route is not a regular file Merkle path")
            get(oid, "blob" if final else "tree")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for oid, (kind, payload) in sorted(objects.items()):
            info = zipfile.ZipInfo("objects/" + oid, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, kind.encode() + b" " + str(len(payload)).encode() + b"\0" + payload)
    archive = buffer.getvalue()
    manifest = {"schema": "original-git-r05-historical-v1", "objects": len(objects),
                "archive_sha256": hashlib.sha256(archive).hexdigest(),
                "routes": [{"commit": commit, "path": name} for commit, name in sorted(routes)],
                "phases": {"frozen-v7-author15": phase}}
    return archive, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive, manifest = build(args.repository)
    for name, raw in (("r05-v7-history-objects.zip", archive), ("r05-v7-history.json", manifest)):
        with (args.output / name).open("xb") as output:
            output.write(raw)
    print(json.dumps({"manifest_sha256": hashlib.sha256(manifest).hexdigest(), "bytes": len(archive),
                      "objects": json.loads(manifest)["objects"], "routes": len(json.loads(manifest)["routes"])}))


if __name__ == "__main__":
    raise SystemExit(main())
