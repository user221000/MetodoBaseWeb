"""Collect selected fixture bindings privately; never execute test fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_web38.recipes import (
    CURRENT_RUNTIME_SELECTORS,
    WEB_SELECTORS,
    require_native_expiry_replacement,
    require_scanner_safety_companion,
)


def source_photo():
    names = set()
    for options in ([], ["--others", "--exclude-standard"]):
        names.update(subprocess.check_output(["git", "ls-files", "-z", *options], cwd=ROOT).split(b"\0"))
    files = {}
    for raw in sorted(names):
        if raw:
            name = raw.decode("utf8")
            path = ROOT / name
            if not name.startswith("docs/") and path.is_file():
                files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
            "files": files}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--current38", action="store_true")
    args = parser.parse_args()
    private = private_directory(args.private)
    if os.name == "nt":
        # The ACL was installed before this first payload. Preserve a fresh
        # readback; no retrospective claim is made about other scratch paths.
        acl = subprocess.check_output(["icacls", str(private)])
        (private / "dacl-before-payload.private.txt").write_bytes(acl)
    else:
        assert private.stat().st_mode & 0o777 == 0o700
    before = source_photo()
    (private / "before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf8")
    selectors = list(CURRENT_RUNTIME_SELECTORS if args.current38 else WEB_SELECTORS)
    if args.current38:
        evidence = private / "companion-bindings"
        evidence.mkdir()
        selectors += ["--web38-companion-evidence", str(evidence)]
    argv = [sys.executable, "-X", "utf8", "tests/ci_web38/collect.py", "--output", str(private / "oracle.json"),
            "--fixture-output", str(private / "fixtures.json"), *selectors]
    with (private / "collection.private.log").open("xb") as raw:
        completed = subprocess.run(argv, cwd=ROOT, stdout=raw, stderr=subprocess.STDOUT, check=False,
                                   timeout=180, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"))
    after = source_photo()
    (private / "after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf8")
    summary = {"status": "collection_only_no_runtime_acceptance", "returncode": completed.returncode,
               "current38_companions": args.current38,
               "source_quiet": before == after, "source_commit": before["HEAD"]}
    if completed.returncode == 0:
        identities = json.loads((private / "oracle.json").read_bytes())
        if args.current38:
            require_scanner_safety_companion(identities)
            require_native_expiry_replacement(identities)
        bindings = json.loads((private / "fixtures.json").read_bytes())["bindings"]
        affected = sorted({row["nodeid"].split("::", 1)[0] for row in bindings
                           if any(value["requires_review"] for value in row["fixtures"].values())})
        summary.update(required_cases=len(identities), modules_requiring_fixture_review=affected)
    (private / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf8")
    print(json.dumps(summary))
    return int(completed.returncode != 0 or before != after)


if __name__ == "__main__":
    raise SystemExit(main())
