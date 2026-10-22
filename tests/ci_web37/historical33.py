"""Materialize physical/contracts33 with an authenticated detached Git context.

No image is built and no Desktop product test is selected by this helper.
Original CI33 helpers, targets, assertions and source pins remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_google33.history import specification
from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_web37.raw_git import raw_blobs
from tests.run_reviewed_ci30 import git_environment, regular_directory

SOURCE = "e006516fe99ec0da65c4a0f563b8c5736e541b50"
SPEC_SHA256 = "e4c689243a926db2a598e2c0e047179d8605538ef8db17d18713b9d34f6a700c"


def materialize(output):
    output = private_directory(output)
    raw_spec = (ROOT / "tests/ci_web37/historical33-source.json").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw_spec).hexdigest() != SPEC_SHA256:
        raise ValueError("Historical33 complete-tree source metadata differs")
    spec = json.loads(raw_spec)
    if spec["commit"] != SOURCE or spec["image_build_selected"] is not False:
        raise ValueError("Historical33 source/scope differs")
    complete_tree = specification(ROOT, spec)
    # CI33 source/wiring/physical gates do not consume documentation. Preserve
    # the original evidence in Git, rather than duplicating 673MB of archives,
    # wheels, image receipts and historical screenshots in every CI job.
    expected = {name: row for name, row in complete_tree.items() if not name.startswith("docs/")}
    destination = output / "source"
    subprocess.run(["git", "--no-replace-objects", "worktree", "add", "--detach", "--no-checkout",
                    str(destination), SOURCE], cwd=ROOT, env=git_environment(), check=True, capture_output=True)
    subprocess.run(["git", "--no-replace-objects", "read-tree", SOURCE], cwd=destination,
                    env=git_environment(), check=True, capture_output=True)
    regular_directory(destination)
    records = []
    entries = {name: (oid, format(mode, "o")) for name, (mode, oid, size) in expected.items()}
    for name, raw, oid, mode in raw_blobs(ROOT, entries):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        for parent in (target.parent, *target.parent.parents):
            if parent == destination.parent:
                break
            regular_directory(parent)
        with target.open("xb") as out:
            out.write(raw)
        target.chmod(int(mode, 8))
        records.append({"path": name, "git_blob": oid, "bytes": len(raw),
                        "raw_sha256": hashlib.sha256(raw).hexdigest()})
    raw = (json.dumps(records, indent=2) + "\n").encode()
    with (output / "blobs.json").open("xb") as out:
        out.write(raw)
    result = {**spec, "raw_blobs_readback_without_checkout_filters": True,
              "registered_detached_source": True, "blobs_raw_sha256": hashlib.sha256(raw).hexdigest(),
              "materialized_non_docs_files": len(records),
              "original_historical_documentation_preserved_in_Git": True,
              "counted_as_current37": False}
    (output / "source.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.output)))
