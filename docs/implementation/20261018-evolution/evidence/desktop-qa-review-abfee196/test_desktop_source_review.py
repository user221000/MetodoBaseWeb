"""Independent real-Git adversarial source checks; no build or GUI."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

SOURCE = Path(r"F:\MetodoBaseWeb-desktop-20261019")


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(root), *args], env=env)


@pytest.fixture
def frozen(tmp_path):
    root = tmp_path / "frozen with spaces"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "core.autocrlf", "false")
    files = {"main.py": b"# source\n", "legacy.txt": b"historical\r\ncontent\r\n",
             "binary.dat": b"\x01\x02\x03\x04\x05\x06\n"}
    for name, data in files.items():
        (root / name).write_bytes(data)
    git(root, "add", ".")
    git(root, "-c", "user.name=QA", "-c", "user.email=qa@example.invalid",
        "-c", "commit.gpgSign=false", "commit", "-qm", "Synthetic source")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    spec = importlib.util.spec_from_file_location("desktop_qa_final", SOURCE / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE_DIR = root
    return module, root, head


def gitpath(root, name):
    item = Path(git(root, "rev-parse", "--git-path", name).decode().strip())
    return item if item.is_absolute() else root / item


def inventory(root):
    return {"index": hashlib.sha256(gitpath(root, "index").read_bytes()).hexdigest(),
            "config": hashlib.sha256(gitpath(root, "config").read_bytes()).hexdigest(),
            "flags": git(root, "ls-files", "-v")}


@pytest.mark.parametrize("flag", ["assume-unchanged", "skip-worktree"])
def test_positive_snapshot_preserves_existing_index_flags(frozen, flag):
    module, root, head = frozen
    git(root, "update-index", "--" + flag, "main.py")
    before = inventory(root)
    assert len(module.source_snapshot(head)) == 3
    assert inventory(root) == before


def test_staged_bytes_rejected_even_when_working_bytes_match_commit(frozen):
    module, root, head = frozen
    (root / "main.py").write_bytes(b"# staged unreviewed replacement\n")
    git(root, "add", "main.py")
    (root / "main.py").write_bytes(b"# source\n")
    before = inventory(root)
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)
    assert inventory(root) == before


def test_global_and_environment_attributes_cannot_change_frozen_policy(frozen, monkeypatch, tmp_path):
    module, root, head = frozen
    (root / "main.py").write_bytes(b"# source\r\n")
    attributes = tmp_path / "outside-attributes"
    attributes.write_text("main.py text eol=lf filter=do-not-run\n", encoding="utf8")
    config = tmp_path / "outside-config"
    config.write_text('[core]\n attributesfile = "' + attributes.as_posix() + '"\n', encoding="utf8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.worktree")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(tmp_path / "wrong-tree"))
    before = inventory(root)
    assert "main.py" in module.source_snapshot(head)
    assert inventory(root) == before
    assert config.read_text(encoding="utf8").endswith('"\n')


def test_local_external_attributes_and_fsmonitor_are_not_executed(frozen, tmp_path):
    module, root, head = frozen
    sentinel = tmp_path / "must-not-exist"
    attributes = tmp_path / "unreviewed-attributes"
    attributes.write_text("main.py text eol=lf filter=do-not-run\n", encoding="utf8")
    git(root, "config", "core.attributesFile", str(attributes))
    git(root, "config", "core.fsmonitor", "echo forbidden > " + str(sentinel))
    git(root, "config", "filter.do-not-run.clean", "echo forbidden > " + str(sentinel))
    (root / "main.py").write_bytes(b"# source\r\n")
    before = inventory(root)
    assert "main.py" in module.source_snapshot(head)
    assert not sentinel.exists()
    assert inventory(root) == before


@pytest.mark.parametrize("name,changed", [
    ("legacy.txt", b"historical\ncontent\n"),
    ("main.py", b"# source\r\n# extra\n"),
])
def test_historical_crlf_or_mixed_content_cannot_be_normalized(frozen, name, changed):
    module, root, head = frozen
    (root / name).write_bytes(changed)
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)


def test_git_binary_control_bytes_require_exact_commit_bytes(frozen):
    module, root, head = frozen
    assert b"i/-text" in git(root, "ls-files", "--eol", "binary.dat")
    (root / "binary.dat").write_bytes(b"\x01\x02\x03\x04\x05\x06\r\n")
    assert b"w/-text" in git(root, "ls-files", "--eol", "binary.dat")
    with pytest.raises(module.BuildError):
        module.source_snapshot(head)
