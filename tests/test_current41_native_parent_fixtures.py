"""Adversarial source fixtures; original APT and historical bodies stay intact."""
from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from tests.ci_image57 import authority, context, technical_child
from tests.ci_web39.native_parent_inputs import MODULES, ParentRoot
from tests.ci_web41 import collection
from tests.ci_web41 import native_parent_fixtures as provider

ROOT = Path(__file__).resolve().parents[1]
PARENT = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def tree(root):
    for name, raw in technical_child.read_payloads(ROOT).items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return root


def test_original_apt_fixture_is_the_exact_two_input_stage_after_both_authenticated_inverses():
    apt = provider.apt_child_inputs(ROOT)
    parent, transition = context.native_parent_payloads(apt)
    assert set(apt) == set(PARENT)
    assert transition == context.native_transition()
    assert {name for name in apt if apt[name] != parent[name]} == set(context.APT_CHILD_PINS)
    for name, pin in PARENT.items():
        assert all(technical_child.record(parent[name])[key] == value for key, value in pin.items())
    assert technical_child.record(apt["Dockerfile"]) == context.APT_CHILD_PINS["Dockerfile"]


@pytest.mark.parametrize("reads", [("Dockerfile",), ("Dockerfile", "requirements-container-apt-metadata.lock")])
def test_historical_root_transports_only_original_named_reads_after_all19_authentication(tmp_path, reads):
    parent = ParentRoot(ROOT, reads)
    parent.prepare(tmp_path)
    record = json.loads((tmp_path / "transport.json").read_bytes())
    assert technical_child.is_transition(record["actual_source_transition"])
    assert set(parent.files) == set(reads)
    assert {path.name for path in tmp_path.iterdir()} == {*reads, "transport.json"}
    for name in reads:
        observed = technical_child.record((parent / name).read_bytes())
        assert all(observed[key] == value for key, value in PARENT[name].items())
    assert parent / "requirements_web.lock" == ROOT / "requirements_web.lock"


@pytest.mark.parametrize("name", tuple(technical_child.PINS))
@pytest.mark.parametrize("fault", ["byte", "append", "missing"])
def test_every_current_input_is_required_before_either_historical_fixture_can_publish(tmp_path, name, fault):
    source = tree(tmp_path / "source")
    target = source / name
    if fault == "missing":
        target.unlink()
    else:
        raw = target.read_bytes()
        target.write_bytes((bytes([raw[0] ^ 1]) + raw[1:]) if fault == "byte" else raw + b"\n")
    destination = tmp_path / "transport"
    destination.mkdir()
    parent = ParentRoot(source, ("Dockerfile",))
    with pytest.raises((ValueError, OSError)):
        provider.apt_child_inputs(source)
    with pytest.raises((ValueError, OSError)):
        parent.prepare(destination)
    assert parent.files is None and list(destination.iterdir()) == []


@pytest.mark.parametrize("extra", ["extra.py", "nested/extra.py", "../extra-native.py", "../unreviewed/extra.py"])
def test_extra_runtime_files_and_descendants_cannot_hide_outside_the19_inputs(tmp_path, extra):
    source = tree(tmp_path / "source")
    target = source / technical_child.NATIVE_PREFIX / extra
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"synthetic unreviewed source\n")
    destination = tmp_path / "transport"
    destination.mkdir()
    with pytest.raises(ValueError, match="membership"):
        provider.apt_child_inputs(source)
    with pytest.raises(ValueError, match="membership"):
        ParentRoot(source, ("Dockerfile",)).prepare(destination)
    assert list(destination.iterdir()) == []


def test_old_parent_can_still_be_transported_without_current_native_files(tmp_path):
    current = technical_child.read_payloads(ROOT)
    original, _ = context.native_parent_payloads(current)
    source = tmp_path / "source"
    for name in PARENT:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original[name])
    destination = tmp_path / "transport"
    destination.mkdir()
    parent = ParentRoot(source, ("Dockerfile",))
    parent.prepare(destination)
    assert json.loads((destination / "transport.json").read_bytes())["actual_source_transition"] is None
    assert (parent / "Dockerfile").read_bytes() == original["Dockerfile"]


def test_only_the_changed_locks_are_added_to_the_original_historical_named_reads(tmp_path):
    previous = {"Dockerfile", "requirements-container-apt-metadata.lock"}
    reads40 = MODULES["tests.test_security_container37_portable_peer"]["reads"]
    reads25 = MODULES["tests.test_security_docker72_portability_peer"]["reads"]
    assert set(reads40) == previous | {"requirements-container.lock", "requirements_web.lock"}
    assert set(reads25) == previous | {"requirements-container.lock", "requirements_web.lock"}
    assert MODULES["tests.test_ci_web37_bandit_registry"]["reads"] == ("Dockerfile",)
    parent = ParentRoot(ROOT, reads40)
    parent.prepare(tmp_path)
    for name in ("requirements-container.lock", "requirements_web.lock"):
        pin = technical_child.LOCK_INVERSES[name]["parent_pin"]
        assert technical_child.record((parent / name).read_bytes()) == pin
        assert (parent / name).read_bytes() != (ROOT / name).read_bytes()
    assert set(json.loads((tmp_path / "transport.json").read_bytes())["transported_inputs"]) == set(reads40)


@pytest.mark.parametrize("read", ["../unreviewed", "unreviewed", "web/source.py"])
def test_an_undeclared_parent_read_is_refused_before_any_transport(tmp_path, read):
    parent = ParentRoot(ROOT, ("Dockerfile", read))
    with pytest.raises(ValueError, match="Undeclared"):
        parent.prepare(tmp_path)
    assert parent.files is None and list(tmp_path.iterdir()) == []


def test_fixture_clone_preserves_all_original_objects_globals_and_marks():
    original = importlib.import_module(provider.ORIGINAL_MODULE)
    before = dict(vars(original))
    companion, receipt = collection.clone_parent_fixture(original)
    assert vars(original) == before
    assert companion is not original and companion.actual_inputs is provider.actual_inputs
    assert original.actual_inputs is before["actual_inputs"]
    tests = {name: value for name, value in before.items() if name.startswith(("test_", "Test"))}
    assert len(tests) == receipt["historical_test_objects_identical"] == 20
    assert {name for name in vars(companion) if name.startswith(("test_", "Test"))} == set(tests)
    for name, value in tests.items():
        assert getattr(companion, name) is value and value.__globals__ is vars(original)
    marker = provider.actual_inputs._fixture_function_marker
    assert marker.scope == "module" and marker.params is None
    assert len(collection.SOURCES) == 6
    assert collection.PARENT_FIXTURES == {provider.ORIGINAL: "actual_inputs"}


@pytest.mark.parametrize("crlf", [False, True])
def test_both_exact_historical_frames_keep_their_full_codetypes(tmp_path, monkeypatch, crlf):
    raw = (ROOT / provider.ORIGINAL).read_bytes().replace(b"\r\n", b"\n")
    path = tmp_path / provider.ORIGINAL
    path.parent.mkdir(parents=True)
    path.write_bytes(raw.replace(b"\n", b"\r\n") if crlf else raw)
    spec = importlib.util.spec_from_file_location(provider.ORIGINAL_MODULE, path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    monkeypatch.setattr(provider, "ROOT", tmp_path)
    provider.authenticate_original(original)


def test_a_changed_original_assertion_function_is_rejected_before_fixture_replacement(monkeypatch):
    original = importlib.import_module(provider.ORIGINAL_MODULE)
    name = next(name for name in vars(original) if name.startswith("test_"))
    monkeypatch.setattr(original, name, lambda: None)
    with pytest.raises(ValueError, match="CodeType"):
        collection.clone_parent_fixture(original)


def test_an_extra_original_test_identity_is_rejected(monkeypatch):
    original = importlib.import_module(provider.ORIGINAL_MODULE)
    monkeypatch.setattr(original, "test_unreviewed_extra", lambda: None, raising=False)
    with pytest.raises(ValueError, match="inventory"):
        collection.clone_parent_fixture(original)


def test_a_replaced_provider_function_is_rejected_before_any_source_transport(monkeypatch):
    original = importlib.import_module(provider.ORIGINAL_MODULE)
    monkeypatch.setattr(provider, "apt_child_inputs", lambda _root: {})
    with pytest.raises(pytest.UsageError, match="CodeType"):
        collection.clone_parent_fixture(original)


def test_unreviewed_provider_source_bytes_are_rejected(tmp_path, monkeypatch):
    path = tmp_path / collection.PARENT_PROVIDER
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / collection.PARENT_PROVIDER).read_bytes() + b"\n")
    monkeypatch.setattr(collection, "ROOT", tmp_path)
    with pytest.raises(pytest.UsageError, match="provider source differs"):
        collection.clone_parent_fixture(importlib.import_module(provider.ORIGINAL_MODULE))
