"""Reuse all forty frozen peer assertions with explicit portable transports.

Only Git reads, a worktree .git pointer copy and the local archive location are
adapted. The original functions, parameterization and assertion bodies are
compiled from the pinned RAW witness without text or AST edits.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web37 import container_inputs as subject
from tests.ci_web37.git_recipe import (
    BASELINE,
    NATIVE,
    load,
    require_historical33_unchanged,
)

ROOT = Path(__file__).resolve().parents[2]
PEER_RAW = Path(__file__).with_name("fixtures") / "container37-inputs-peer40.py.RAW"
PEER_SHA256 = "1eb22aa94088334d12a202ca2376d7da0b5e566795b0cefd765be4b5b679f76e"
FROZEN = "8c7089ea702083d64bba6b747a37bfd2e825e998"


def original_namespace():
    raw = PEER_RAW.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PEER_SHA256:
        raise ValueError("Original forty-case security peer RAW source differs")
    namespace = {"__name__": __name__, "__file__": str(ROOT / "tests/test_security_container37_inputs_peer.py")}
    # The complete source is authenticated by the finite RAW SHA256 above.
    exec(compile(raw, namespace["__file__"], "exec"), namespace)  # noqa: S102
    proof = load()

    def git(source, path):
        if source == NATIVE:
            return proof.blob(NATIVE, path)
        if source == "cd423" and path == "requirements_web.lock":
            return proof.blob(BASELINE, path)
        raise ValueError("Undeclared original peer Git read")

    def check_output(argv, *, cwd):
        if argv != ["git", "diff", "--name-only", "cd423", FROZEN, "--", "tests/ci_google33"] or cwd != ROOT:
            raise ValueError("Undeclared original peer subprocess transport")
        require_historical33_unchanged(ROOT, proof)
        return b""

    namespace["git"] = git
    namespace["subprocess"] = SimpleNamespace(check_output=check_output)
    return namespace


def export_tests():
    return {name: value for name, value in original_namespace().items() if name.startswith("test_")}


@pytest.fixture
def input_copy(tmp_path, monkeypatch):
    manifest = subject.json.loads((ROOT / "tests/ci_web37/container-inputs.json").read_bytes())
    for name in [*manifest["candidate_files"], "requirements_web.lock", "tests/ci_web37/container-inputs.json"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    return tmp_path


@pytest.fixture(scope="module")
def original_expat_source():
    archive = Path(os.environ["METODOBASE_TEST_PYTHON_SOURCE_ARCHIVE"])
    if not archive.is_absolute() or not archive.is_file():
        raise ValueError("The portable peer requires an explicit absolute Python source archive")
    recipe = original_namespace()["RECIPE"]
    lock = recipe.pins()
    selected = recipe.source_files(archive, lock)
    assert len(selected) == 31
    return selected["Modules/expat/xmlparse.c"], (ROOT / "runtime-source/expat-sec10/13c5f63.patch").read_bytes(), lock
