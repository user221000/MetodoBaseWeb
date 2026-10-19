"""Real temporary repositories exercise commit provenance, without builds."""
import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env).stdout


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("desktop_provenance_author", ROOT / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / "candidate with spaces"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "core.autocrlf", "false")
    (root / "main.py").write_bytes(b"# committed source\n")
    (root / "image.bin").write_bytes(b"\0binary\r\nbytes\xff")
    (root / ".gitattributes").write_text("*.sh text eol=lf\n", encoding="utf-8")
    (root / "entry.sh").write_bytes(b"#!/bin/sh\nexit 0\n")
    git(root, "add", ".")
    git(root, "-c", "user.name=Desktop Test", "-c", "user.email=desktop@example.invalid",
        "-c", "commit.gpgSign=false", "commit", "-qm", "Synthetic candidate")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    monkeypatch.setattr(module, "BASE_DIR", root)
    return module, root, head


@pytest.mark.parametrize("flag", ["assume-unchanged", "skip-worktree"])
def test_hidden_working_change_cannot_claim_committed_source(frozen, flag):
    module, root, head = frozen
    git(root, "update-index", "--" + flag, "main.py")
    (root / "main.py").write_bytes(b"# unreviewed replacement; never executed\n")
    assert git(root, "status", "--porcelain") == b""
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)


def test_normal_frozen_checkout_is_accepted_without_index_mutation(frozen):
    module, root, head = frozen
    index = Path(git(root, "rev-parse", "--git-path", "index").decode().strip())
    if not index.is_absolute():
        index = root / index
    before = index.read_bytes()
    assert set(module.source_snapshot(head)) == {"main.py", "image.bin", ".gitattributes", "entry.sh"}
    assert index.read_bytes() == before


def test_crlf_checkout_of_utf8_text_is_permitted(frozen):
    module, root, head = frozen
    (root / "main.py").write_bytes(b"# committed source\r\n")
    assert "main.py" in module.source_snapshot(head)


def test_explicit_lf_resource_rejects_crlf(frozen):
    module, root, head = frozen
    (root / "entry.sh").write_bytes(b"#!/bin/sh\r\nexit 0\r\n")
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)


def test_binary_bytes_are_never_normalized(frozen):
    module, root, head = frozen
    (root / "image.bin").write_bytes(b"\0binary\nbytes\xff")
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)


def test_committed_filter_is_rejected_without_running_it(frozen):
    module, root, head = frozen
    sentinel = root.parent / "filter-must-never-run"
    (root / ".gitattributes").write_text("main.py filter=private\n", encoding="utf-8")
    git(root, "-c", "filter.private.clean=cat", "add", ".gitattributes")
    git(root, "-c", "user.name=Desktop Test", "-c", "user.email=desktop@example.invalid",
        "-c", "commit.gpgSign=false", "commit", "-qm", "Unsupported filter declaration")
    git(root, "config", "filter.private.clean", "touch " + str(sentinel))
    head = git(root, "rev-parse", "HEAD").decode().strip()
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)
    assert not sentinel.exists()


def test_local_attributes_override_is_rejected(frozen):
    module, root, head = frozen
    path = Path(git(root, "rev-parse", "--git-path", "info/attributes").decode().strip())
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("main.py -text\n", encoding="utf-8")
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)
