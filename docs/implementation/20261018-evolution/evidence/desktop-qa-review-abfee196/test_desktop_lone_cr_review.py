"""A lone CR must not authorize mutation of a binary-classified blob."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

SOURCE = Path(r"F:\MetodoBaseWeb-desktop-20261019")
REPORT = Path(os.environ["METODOBASE_DESKTOP_LONE_CR_REPORT"])


def test_lone_cr_binary_source_must_match_committed_bytes(tmp_path):
    root = tmp_path / "lone CR source"
    root.mkdir()
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}

    def git(*arguments):
        return subprocess.check_output(["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
                                        "-C", str(root), *arguments], env=environment)

    git("init", "-q")
    git("config", "core.autocrlf", "false")
    original = b"line\rbreak\n"
    changed = b"line\rbreak\r\n"
    assert original.decode("utf8")
    path = root / "lone-cr.dat"
    path.write_bytes(original)
    git("add", ".")
    git("-c", "user.name=QA", "-c", "user.email=qa@example.invalid",
        "-c", "commit.gpgSign=false", "commit", "-qm", "Synthetic lone CR source")
    head = git("rev-parse", "HEAD").decode().strip()
    classification = git("ls-files", "--eol").decode().strip()
    assert "i/-text" in classification
    path.write_bytes(changed)
    index = root / ".git/index"
    before = index.read_bytes()
    spec = importlib.util.spec_from_file_location("desktop_lone_cr_review", SOURCE / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE_DIR = root
    accepted = True
    try:
        module.source_snapshot(head)
    except module.BuildError:
        accepted = False
    report = {"scope": "Own real temporary Git repository; no build/GUI/product changes",
              "buildSha256": hashlib.sha256((SOURCE / "build.py").read_bytes()).hexdigest(),
              "gitClassification": classification, "gitWorkingClassification": git("ls-files", "--eol").decode().strip(),
              "originalHex": original.hex(), "changedHex": changed.hex(),
              "committedSha256": hashlib.sha256(original).hexdigest(),
              "workingSha256": hashlib.sha256(changed).hexdigest(),
              "sourceGuardAccepted": accepted, "indexUnchanged": index.read_bytes() == before}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    assert report["indexUnchanged"]
    assert accepted is False, "Lone CR binary blob was accepted after LF-to-CRLF mutation"
