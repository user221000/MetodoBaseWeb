"""Export original R05 historical Git frames for review; no Git mutation."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

from tests.ci_web37.git_recipe import object_id, tree_entries

SOURCE = "f0608fb086b08bbd59ce595e9a906c58308d3328"
V5 = "c60b7f4554c2e640faad805571d00fc0973fd45c"
V5_PARENT = "c4d9ba37a377fdc972c242e7b132146a91e45c38"
V5_SCAN = "8d6b18521c719ff789ebd32c493457b6810b2b48"
V6 = "287a51865a9d346f7e45bb09d3a2e13a4922c636"
V6_BASE = "ab8bd90d65bde1a502f50c8ef0edd1d3dd417e1c"
V6_SCAN = "ca09d2f803bcd1e2b977db7b708fa6559c9b5617"
PROPOSAL5 = "docs/implementation/20261018-evolution/evidence/security-r05-753-independent-20261020/finite-proposal.zip"
PROPOSAL6 = "docs/implementation/20261018-evolution/evidence/root-r05-223-proposal-20261020/finite-proposal.zip"
INVENTORY = "docs/implementation/20261018-evolution/evidence/ops-ci37-r05-history-portability-20261020/git-read-inventory-v5.json"


def build(repository):
    def git(*args):
        return subprocess.check_output(["git", "--no-replace-objects", *args], cwd=repository)

    def raw(commit, name):
        return git("show", commit + ":" + name)

    def proposal(commit, name):
        with zipfile.ZipFile(io.BytesIO(raw(commit, name))) as archive:
            return json.loads(archive.read("proposal.json"))

    old_inventory = json.loads(raw("4ce2967b67bca274933ed6b50f9ff3764a86b829", INVENTORY))
    routes = {(row["commit"], row["path"]) for row in old_inventory["queries"]}
    proposal5, proposal6 = proposal(V5, PROPOSAL5), proposal(V6, PROPOSAL6)
    phases = {}

    def phase(name, aliases, reads, cases, tests):
        value = {"aliases": aliases, "git_reads": sorted([list(row) for row in reads]),
                 "files": {}, "required_cases": cases, "tests": tests,
                 "scope": "authentic_frozen_history_no_current_runtime_or_fullscan_claim"}
        phases[name] = value
        return value

    def add(phase_value, commit, name, framing="Git exact", expected=None):
        data = raw(commit, name)
        routes.add((commit, name))
        if framing == "Git LF to CRLF":
            if b"\r" in data:
                raise ValueError("The declared finite historical CRLF source is not Git LF")
            data = data.replace(b"\n", b"\r\n")
        digest = hashlib.sha256(data).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError("The original physical proposal binding differs")
        row = {"commit": commit, "path": name, "framing": framing, "materialized_sha256": digest}
        previous = phase_value["files"].get(name)
        if previous is not None and previous["materialized_sha256"] != digest:
            raise ValueError("Two historical sources propose different bytes for one phase path")
        phase_value["files"][name] = row

    reads5 = set(routes)
    # The literal peer spells its parent with '^'; the commit frame proves it.
    reads5 = {(V5 + "^" if commit == V5_PARENT else commit, path) for commit, path in reads5}
    frozen5 = phase("frozen-v5-peer60", {V5 + "^": V5_PARENT}, reads5, 60,
                    ["tests/test_security_r05_v5_current_peer.py"])
    for name in [".gitleaks.toml", ".gitattributes", "scripts/scan_secrets.py", "scripts/reviewed_scan_locations.py",
                 "tests/test_secret_scan_finite_v4.py", PROPOSAL5,
                 *[f"scripts/data/reviewed_scan_locations_v{number}.zip" for number in range(1, 6)]]:
        add(frozen5, V5, name)
    add(frozen5, SOURCE, frozen5["tests"][0])
    for row in proposal5["physical_file_frames"]:
        add(frozen5, V5_SCAN, row["file"], "Git exact" if row["framing"] == "Git exact" else "Git LF to CRLF",
            row["source_sha256"])

    reads6 = {(V6_SCAN, row["path"]) for row in proposal6["files"]}
    stable = [".gitleaks.toml", "scripts/scan_secrets.py", "scripts/reviewed_scan_locations.py",
              "tests/test_secret_scan_finite_v5.py", *[f"scripts/data/reviewed_scan_locations_v{n}.zip" for n in range(1, 6)]]
    reads6 |= {(commit, path) for commit in (V6_BASE, "HEAD") for path in stable}
    frozen6 = phase("frozen-v6-author48", {"HEAD": V6}, reads6, 48, ["tests/test_secret_scan_finite_v6.py"])
    for commit, name in reads6:
        routes.add((V6 if commit == "HEAD" else commit, name))
    for name in [*stable, "scripts/data/reviewed_scan_locations_v6.zip", PROPOSAL6, *frozen6["tests"]]:
        add(frozen6, V6, name)
    for row in proposal6["files"]:
        add(frozen6, V6_SCAN, row["path"], expected=row["source_digest"])

    current = phase("current-750-transport24", {},
                    {(row["commit"], row["path"]) for row in old_inventory["queries"]
                     if row["commit"] not in {V5, V5_PARENT}}, 24, ["tests/test_security_r05_753_peer.py"])
    add(current, SOURCE, current["tests"][0])
    add(current, V5, PROPOSAL5)

    objects = {}

    def get(oid, kind):
        if oid not in objects:
            actual = git("cat-file", "-t", oid).strip().decode("ascii")
            payload = git("cat-file", actual, oid)
            if actual != kind or object_id(kind, payload) != oid:
                raise ValueError("The original Git object differs during export")
            objects[oid] = (kind, payload)
        if objects[oid][0] != kind:
            raise ValueError("An original Git identity cannot have two types")
        return objects[oid][1]

    for commit, path in sorted(routes):
        first = get(commit, "commit").split(b"\n", 1)[0]
        if not first.startswith(b"tree "):
            raise ValueError("The original commit root is malformed")
        oid = first[5:].decode("ascii")
        for index, part in enumerate(path.split("/")):
            kind, oid = tree_entries(get(oid, "tree"))[part]
            get(oid, "blob" if index == len(path.split("/")) - 1 else "tree")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for oid, (kind, payload) in sorted(objects.items()):
            frame = kind.encode() + b" " + str(len(payload)).encode() + b"\0" + payload
            info = zipfile.ZipInfo("objects/" + oid, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, frame)
    archive = buffer.getvalue()
    manifest = {"schema": "original-git-r05-historical-v1", "objects": len(objects),
                "archive_sha256": hashlib.sha256(archive).hexdigest(),
                "routes": [{"commit": commit, "path": path} for commit, path in sorted(routes)], "phases": phases}
    return archive, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive, manifest = build(args.repository)
    for name, raw in (("r05-history-objects.zip", archive), ("r05-history.json", manifest)):
        with (args.output / name).open("xb") as output:
            output.write(raw)
    print(json.dumps({"manifest_sha256": hashlib.sha256(manifest).hexdigest(), "bytes": len(archive),
                      "objects": json.loads(manifest)["objects"], "routes": len(json.loads(manifest)["routes"])}))


if __name__ == "__main__":
    raise SystemExit(main())
