"""Apply the user's web-only scope outside the authentic historical31 source."""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_google33.history import specification, specifications
from tests.ci_web37.recipes import WEB_SELECTORS


def command(source, mode):
    if mode not in {"serial", "parallel"}:
        raise ValueError("Historical31 permits only its original serial or parallel web command")
    argv = [sys.executable, "-B", "-X", "utf8", str(source / "tests/run_isolated.py"),
            *WEB_SELECTORS, "-p", "ci_web37.scope", "-q", "--tb=short"]
    if mode == "serial":
        argv += ["--cov", "--cov-report=xml", "--cov-report=json", "--junitxml=pytest-web.xml"]
    else:
        argv += ["--shuffle-seed=20261018", "-n", "2", "--junitxml=pytest-web-shuffle.xml"]
    return argv


def original_bytes(source):
    spec = specifications()["31"]
    head = subprocess.check_output(["git", "--no-replace-objects", "rev-parse", "HEAD"], cwd=source).decode().strip()
    if head != spec["commit"]:
        raise ValueError("The historical31 web source is not its authentic detached revision")
    expected = specification(ROOT, spec)
    result = {}
    for name, (_mode, oid, size) in expected.items():
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("An authentic historical31 source file is absent or special")
        raw = path.read_bytes()
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()
        if len(raw) != size or digest != oid:
            raise ValueError("Historical31 original assertions or source bytes changed")
        result[name] = hashlib.sha256(raw).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--mode", choices=("serial", "parallel"), required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    before = original_bytes(source)
    # The child imports tests/models from the original source. This external
    # path supplies only the pure web-scope plugin under its distinct package.
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "tests"), PYTHONDONTWRITEBYTECODE="1")
    environment.pop("PYTEST_ADDOPTS", None)
    completed = subprocess.run(command(source, args.mode), cwd=source, env=environment, check=False)
    if original_bytes(source) != before:
        raise ValueError("Historical31 source changed during its scoped web execution")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
