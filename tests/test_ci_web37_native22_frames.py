"""Two physical source frames never become a generic newline or path adapter."""
import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from tests.ci_web37 import native22_frames as subject
from tests.ci_web37.recipes import (
    NATIVE_EXPIRY_REQUIRED,
    NATIVE_PHYSICAL_ORIGINAL,
    require_native_expiry_replacement,
)


def fixture_copy(tmp_path):
    destination = tmp_path / "fixture"
    destination.mkdir()
    for name in ("native22-original-objects.zip", *(
            "native22-original-" + item + ".RAW" for item in subject.NAMES)):
        shutil.copyfile(subject.FIXTURES / name, destination / name)
    return destination


def test_original22_assertions_execute_without_Git_process_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Native22 source oracle cannot launch a process or network")
    for name in ("Popen", "run", "check_output"):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    copied = subject.export()[subject.TEST_NAME]
    copied()
    proof = subject.OriginalFrames()
    assert len(proof.proof.objects) == len(proof.proof.used) == 7
    assert set(proof.original) == set(proof.git_lf) == set(subject.NAMES)


@pytest.mark.parametrize("name", subject.NAMES)
def test_one_changed_host_byte_cannot_use_the_old_frame(name):
    proof = subject.OriginalFrames()
    actual = proof.git_lf[name]
    with pytest.raises(ValueError, match="exact authenticated Git LF"):
        proof.original_frame(name, bytes([actual[0] ^ 1]) + actual[1:])


@pytest.mark.parametrize("name", subject.NAMES)
def test_one_changed_old_preimage_byte_is_rejected(tmp_path, name):
    directory = fixture_copy(tmp_path)
    path = directory / ("native22-original-" + name + ".RAW")
    raw = path.read_bytes()
    path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="retained Windows preimage"):
        subject.OriginalFrames(directory)


@pytest.mark.parametrize("path", ["DB_bootstrap.py", "unknown.py"])
def test_other_case_or_unknown_path_has_no_transport(path):
    with pytest.raises(ValueError, match="two exact paths"):
        subject.OriginalFrames().original_frame(path, b"inert")


def test_one_changed_finite_object_archive_byte_is_rejected(tmp_path):
    directory = fixture_copy(tmp_path)
    path = directory / "native22-original-objects.zip"
    raw = path.read_bytes()
    path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(ValueError, match="finite object fixture"):
        subject.OriginalFrames(directory)


def test_every_original_assertion_code_object_default_and_marker_is_identical():
    from tests import test_security_native35_v7_peer as original
    old = getattr(original, subject.TEST_NAME)
    copied = subject.export()[subject.TEST_NAME]
    assert copied.__code__ is old.__code__
    assert copied.__defaults__ == old.__defaults__
    assert copied.__kwdefaults__ == old.__kwdefaults__
    assert copied.__dict__ == old.__dict__
    assert copied.__globals__["ROOT"] is not old.__globals__["ROOT"]
    assert Path(original.__file__).is_file()


def test_changed_original_test_source_cannot_enter_the_companion(tmp_path, monkeypatch):
    from tests import test_security_native35_v7_peer as original
    path = tmp_path / "modified.py"
    path.write_bytes(Path(original.__file__).read_bytes() + b"# source drift\n")
    monkeypatch.setattr(original, "__file__", str(path))
    with pytest.raises(ValueError, match="original assertion source"):
        subject.export()


def test_changed_current_manifest_is_not_replaced_by_old_data(tmp_path, monkeypatch):
    source = subject.ROOT / subject.MANIFEST
    target = tmp_path / subject.MANIFEST
    target.parent.mkdir(parents=True)
    value = json.loads(source.read_bytes())
    value["helper_union"].pop("alembic.ini")
    target.write_text(json.dumps(value), encoding="utf8")
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="authenticated original"):
        subject.export()


@pytest.mark.parametrize("fault", ["missing", "duplicate", "untransported-original"])
def test_native_recipe_requires_exactly_one_transported_original22_oracle(fault):
    rows = list(NATIVE_EXPIRY_REQUIRED)
    physical = rows[-1]
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows.append(physical)
    else:
        rows[-1] = NATIVE_PHYSICAL_ORIGINAL
    with pytest.raises(ValueError, match="historical native expiry refusal"):
        require_native_expiry_replacement(rows)
