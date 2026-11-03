"""Authenticate current19 before the original container37 peer data is exposed."""
import importlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_image57 import production_child, technical_child
from tests.ci_web37.composition import fixture_function
from tests.ci_web41 import historical_native37_peer_fixture as subject

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture
def current_source(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    for name, raw in technical_child.read_payloads(ROOT).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return root


def test_all_thirteen_parent_payloads_authenticate_before_only_three_are_selected(current_source):
    actual = technical_child.read_payloads(current_source)
    parent = technical_child.inverse(actual)
    selected = subject.historical_lock_payloads(current_source)
    assert len(actual) == 19 and len(parent) == 13 and len(selected) == 3
    assert set(selected) == set(subject.LOCK_FILES)
    assert selected == {name: parent[name] for name in subject.LOCK_FILES}
    contract = json.loads(selected["runtime-source/container37-contract.json"])
    assert contract["distributions"]["pyasn1"] == "0.6.4"
    assert contract["runtime_distribution_count"] == 57
    assert subject.verify_current_lock is importlib.import_module("tests.ci_web37.container_inputs").verify_current_lock


@pytest.mark.parametrize("name", tuple(technical_child.PINS))
@pytest.mark.parametrize("fault", ["append", "byte", "missing"])
def test_every_current_input_drift_refuses_before_inverse_or_publishing(
        current_source, tmp_path, monkeypatch, name, fault):
    path = current_source / name
    raw = path.read_bytes()
    if fault == "append":
        path.write_bytes(raw + b"\n")
    elif fault == "byte":
        changed = bytearray(raw)
        changed[len(changed) // 2] ^= 1
        path.write_bytes(changed)
    else:
        path.unlink()
    calls = []
    original = technical_child.inverse

    def inverse(payloads):
        calls.append(True)
        return original(payloads)

    monkeypatch.setattr(technical_child, "inverse", inverse)
    destination = tmp_path / "published"
    with pytest.raises((ValueError, OSError)):
        subject.materialize_lock_inputs(current_source, destination)
    assert calls == [] and not destination.exists()


@pytest.mark.parametrize("name", tuple(technical_child.PARENT_PINS) + ("requirements_web.lock",))
def test_every_restored_parent_including_unselected_files_is_verified(
        current_source, tmp_path, monkeypatch, name):
    original = technical_child.inverse

    def changed(payloads):
        result = original(payloads)
        result[name] += b"\n"
        return result

    monkeypatch.setattr(technical_child, "inverse", changed)
    destination = tmp_path / "published"
    with pytest.raises(ValueError, match="thirteen historical"):
        subject.materialize_lock_inputs(current_source, destination)
    assert not destination.exists()


@pytest.mark.parametrize("fault", ["extra", "missing", "foreign_same_count"])
def test_exact_current_membership_precedes_the_inverse(current_source, tmp_path, monkeypatch, fault):
    payloads = technical_child.read_payloads(current_source)
    if fault != "extra":
        payloads.pop("Dockerfile")
    if fault != "missing":
        payloads["foreign"] = b"not an approved input"
    monkeypatch.setattr(technical_child, "read_payloads", lambda root: payloads)
    monkeypatch.setattr(technical_child, "inverse", lambda value: pytest.fail("Inverse ran before source admission"))
    with pytest.raises(ValueError, match="nineteen authenticated"):
        subject.materialize_lock_inputs(current_source, tmp_path / "published")
    assert not (tmp_path / "published").exists()


@pytest.mark.parametrize("fault", ["extra", "missing_web", "foreign_same_count", "wrong_generation", "not_bytes"])
def test_exact_parent_generation_and_web_lock_cannot_be_hidden_by_selection(
        current_source, tmp_path, monkeypatch, fault):
    original = technical_child.inverse

    def changed(payloads):
        parent = original(payloads)
        if fault == "extra":
            parent["extra"] = b"unreviewed"
        elif fault in {"missing_web", "foreign_same_count"}:
            parent.pop("requirements_web.lock")
            if fault == "foreign_same_count":
                parent["foreign"] = b"unreviewed"
        elif fault == "wrong_generation":
            parent["Dockerfile"] = production_child.inverse(parent["Dockerfile"])
        else:
            parent["Dockerfile"] = bytearray(parent["Dockerfile"])
        return parent

    monkeypatch.setattr(technical_child, "inverse", changed)
    with pytest.raises(ValueError, match="thirteen historical"):
        subject.materialize_lock_inputs(current_source, tmp_path / "published")
    assert not (tmp_path / "published").exists()


@pytest.mark.parametrize("name", ["runtime-source/technical-close-20261103/unknown", "runtime-source/unknown.py"])
def test_extra_native_source_members_reject_before_fixture_creation(current_source, tmp_path, name):
    path = current_source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"unreviewed")
    with pytest.raises(ValueError):
        subject.materialize_lock_inputs(current_source, tmp_path / "published")
    assert not (tmp_path / "published").exists()


def test_hardlinked_current_input_cannot_enter_the_fixture(current_source, tmp_path):
    (tmp_path / "input-alias").hardlink_to(current_source / "requirements_web.lock")
    with pytest.raises(ValueError):
        subject.materialize_lock_inputs(current_source, tmp_path / "published")
    assert not (tmp_path / "published").exists()


def test_original_verifier_failure_cannot_publish_any_fixture(current_source, tmp_path, monkeypatch):
    def refuse(*args):
        raise ValueError("Original verifier refused")

    monkeypatch.setattr(subject, "verify_current_lock", refuse)
    with pytest.raises(ValueError, match="Original verifier refused"):
        subject.materialize_lock_inputs(current_source, tmp_path / "published")
    assert not (tmp_path / "published").exists()


@pytest.mark.parametrize("fault", ["existing_directory", "existing_file", "inside_source", "relative", "parent_traversal"])
def test_fixture_never_reuses_an_authority_or_writes_inside_current_source(current_source, tmp_path, fault):
    destination = tmp_path / "published"
    if fault == "existing_directory":
        destination.mkdir()
    elif fault == "existing_file":
        destination.write_bytes(b"retained fixture")
    elif fault == "inside_source":
        destination = current_source / "published"
    elif fault == "relative":
        destination = Path("relative-fixture")
    else:
        destination = tmp_path / ".." / "lexical-parent-fixture"
    with pytest.raises(ValueError, match="fresh unaliased"):
        subject.materialize_lock_inputs(current_source, destination)
    if fault == "existing_file":
        assert destination.read_bytes() == b"retained fixture"
    elif fault == "existing_directory":
        assert list(destination.iterdir()) == []
    else:
        assert not destination.exists()


def test_files_are_exclusive_and_private_before_first_byte(current_source, tmp_path, monkeypatch):
    original = os.open
    observed = []

    def opened(path, flags, mode):
        descriptor = original(path, flags, mode)
        observed.append((flags, mode, os.fstat(descriptor).st_size, stat.S_IMODE(os.fstat(descriptor).st_mode)))
        return descriptor

    monkeypatch.setattr(os, "open", opened)
    destination = subject.materialize_lock_inputs(current_source, tmp_path / "published")
    assert len(observed) == 3
    assert all(flags & os.O_EXCL and flags & os.O_CREAT and mode == 0o600 and size == 0
               for flags, mode, size, _ in observed)
    if os.name == "posix":
        assert stat.S_IMODE(destination.stat().st_mode) == 0o700
        assert all(mode == 0o600 for _, _, _, mode in observed)
    assert {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()} == set(subject.LOCK_FILES)
    assert {name: (destination / name).read_bytes() for name in subject.LOCK_FILES} == subject.historical_lock_payloads(current_source)


@pytest.mark.parametrize("name", ["tests.test_security_container37_count57_peer", "tests.test_security_container37_extras_peer"])
def test_old_peer_fixture_restores_its_root_and_keeps_every_test_CodeType(name, tmp_path):
    module = importlib.import_module(name)
    root = module.ROOT
    codes = {key: value.__code__ for key, value in vars(module).items() if key.startswith("test_") and callable(value)}
    fixture = fixture_function(module.historical_container37_inputs)
    with pytest.MonkeyPatch.context() as patch:
        fixture(SimpleNamespace(module=module), tmp_path, patch)
        assert module.ROOT != root and module.ROOT.is_relative_to(tmp_path)
        assert json.loads((module.ROOT / subject.LOCK_FILES[2]).read_bytes())["distributions"]["pyasn1"] == "0.6.4"
        assert all(getattr(module, key).__code__ is code for key, code in codes.items())
    assert module.ROOT is root


def test_fixture_provider_refuses_any_other_module_before_publishing(tmp_path, monkeypatch):
    def forbidden(*args):
        pytest.fail("An unreviewed module reached historical fixture creation")

    monkeypatch.setattr(subject, "materialize_lock_inputs", forbidden)
    request = SimpleNamespace(module=SimpleNamespace(__name__="tests.unreviewed", ROOT=ROOT))
    with pytest.raises(ValueError, match="two declared historical"):
        fixture_function(subject.historical_container37_inputs)(request, tmp_path, monkeypatch)
    assert list(tmp_path.iterdir()) == []


def test_current_source_does_not_downgrade_and_still_requires_current_runtime_gate(current_source, tmp_path):
    before = {name: technical_child.record(raw) for name, raw in technical_child.read_payloads(current_source).items()}
    destination = subject.materialize_lock_inputs(current_source, tmp_path / "published")
    after = {name: technical_child.record(raw) for name, raw in technical_child.read_payloads(current_source).items()}
    assert before == after
    actual_contract, _ = technical_child.details(current_source)
    assert actual_contract["distributions"]["pyasn1"] == "0.6.5"
    assert actual_contract["runtime_distribution_count"] == 57
    assert json.loads((destination / subject.LOCK_FILES[2]).read_bytes())["distributions"]["pyasn1"] == "0.6.4"
