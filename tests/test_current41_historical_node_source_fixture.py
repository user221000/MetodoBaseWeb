"""Closed historical Node input fixture controls; no Node, browser or SQL."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from tests.ci_web37 import node_current
from tests.ci_web39 import new38_sources
from tests.ci_web41 import historical_node_source_fixture as fixture

ROOT = Path(__file__).resolve().parents[1]
ADDITIONAL = json.loads((ROOT / "tests/ci_web39/node-routines-onboarding39.json").read_bytes())
NEW38 = json.loads((ROOT / new38_sources.CURRENT_MAP).read_bytes())
NEW_INPUTS = {name: pin for row in NEW38["phases"].values() for name, pin in row["input_files"].items()}
BINDINGS = [("additional", name) for name in ADDITIONAL["input_files"]]
BINDINGS += [("new38", name) for name in NEW_INPUTS]


@pytest.fixture(scope="module")
def admitted():
    return fixture.historical_payloads(ROOT)


def write_sources(root, payloads):
    root.mkdir()
    for name, raw in payloads.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return root


@pytest.fixture
def actual_copy(tmp_path, monkeypatch, admitted):
    actual = {name: (ROOT / name).read_bytes() for name in admitted}
    by_oid = {pin["git_blob"]: admitted[name] for name, pin in fixture.HISTORICAL_PINS.items()}
    monkeypatch.setattr(fixture, "git_blob", lambda root, oid, size: by_oid[oid])
    return write_sources(tmp_path / "actual", actual)


@pytest.fixture(scope="module")
def historical_root(tmp_path_factory, admitted):
    parent = tmp_path_factory.mktemp("metodobase-test-old-node-inputs")
    return write_sources(parent / "historical", admitted)


def test_all35_bindings31_paths_and44_unit_input_generation_are_explicit(admitted, historical_root):
    assert len(BINDINGS) == 35 and len(fixture.HISTORICAL_PINS) == 31
    assert len(ADDITIONAL["input_files"]) == 21 and len(NEW_INPUTS) == 14
    assert set(ADDITIONAL["input_files"]) | set(NEW_INPUTS) == set(fixture.HISTORICAL_PINS)
    assert len(fixture.CURRENT_CHANGED_PINS) == 11 and len(admitted) == 34
    assert "web/static/css/workspace.css" not in admitted
    rows, mapping = fixture.validate_fixture(historical_root)
    assert len(rows) == 8 and sum(len(row["expected_cases"]) for row in rows) == 94
    assert mapping["phases"] == NEW38["phases"]
    assert {key: row["cases"] for key, row in mapping["phases"].items()} == new38_sources.CASES
    for name, raw in admitted.items():
        assert fixture.record(raw) == {**fixture.HISTORICAL_PINS, **fixture.MAP_PINS}[name]
    assert all((ROOT / name).read_bytes().replace(b"\r\n", b"\n") != admitted[name]
               for name in fixture.CURRENT_CHANGED_PINS)
    with pytest.raises(ValueError, match="Additional Node direct or transitive"):
        node_current.require_additional_sources(ROOT, ADDITIONAL)
    for row in NEW38["phases"].values():
        with pytest.raises(ValueError, match="direct/transitive canonical Git source"):
            new38_sources.require_sources(ROOT, row)


@pytest.mark.parametrize("scope,name", BINDINGS)
@pytest.mark.parametrize("mutation", ("byte", "missing", "append"))
def test_every_original_binding_rejects_drift_and_missing_with_unchanged_guard(historical_root, scope, name, mutation):
    path = historical_root / name
    original = path.read_bytes()
    try:
        if mutation == "missing":
            path.unlink()
        else:
            path.write_bytes(bytes([original[0] ^ 1]) + original[1:] if mutation == "byte" else original + b"\n")
        with pytest.raises((ValueError, OSError)):
            if scope == "additional":
                node_current.require_additional_sources(historical_root, ADDITIONAL)
            else:
                row = next(row for row in NEW38["phases"].values() if name in row["input_files"])
                new38_sources.require_sources(historical_root, row)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize("name", tuple(fixture.HISTORICAL_PINS))
@pytest.mark.parametrize("mutation", ("byte", "missing"))
def test_every_current_counterpart_is_required_before_git_or_materialization(actual_copy, tmp_path, monkeypatch, name, mutation):
    path = actual_copy / name
    raw = path.read_bytes()
    if mutation == "missing":
        path.unlink()
    else:
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    monkeypatch.setattr(fixture, "git_blob", lambda *args: pytest.fail("Git before current admission"))
    with pytest.raises((ValueError, OSError)):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("name", tuple(fixture.CURRENT_CHANGED_PINS))
def test_current_generation_cannot_be_relabelled_as_historical(admitted, name):
    changed = dict(admitted)
    changed[name] = (ROOT / name).read_bytes()
    with pytest.raises(ValueError, match="original historical Node"):
        fixture.validate_payloads(changed)


@pytest.mark.parametrize("name", tuple(fixture.MAP_PINS))
@pytest.mark.parametrize("mutation", ("byte", "missing"))
def test_all_immutable_maps_are_required_before_recovery(actual_copy, tmp_path, monkeypatch, name, mutation):
    path = actual_copy / name
    if mutation == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    monkeypatch.setattr(fixture, "git_blob", lambda *args: pytest.fail("Git before descriptor admission"))
    with pytest.raises((ValueError, OSError)):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("mutation", ("extra", "missing", "descriptor", "wrong_git"))
def test_fixture_namespace_descriptor_and_payload_cannot_be_forged(admitted, mutation):
    changed = dict(admitted)
    name = next(iter(fixture.HISTORICAL_PINS))
    if mutation == "extra":
        changed["tests/unreviewed.cjs"] = b"pass\n"
    elif mutation == "missing":
        del changed[name]
    elif mutation == "descriptor":
        key = new38_sources.CURRENT_MAP
        value = json.loads(changed[key])
        value["phases"]["node-product38"]["expected_cases"].reverse()
        changed[key] = json.dumps(value).encode()
    else:
        changed[name] = admitted[next(key for key in fixture.HISTORICAL_PINS if key != name)]
    with pytest.raises(ValueError):
        fixture.validate_payloads(changed)


def test_wrong_git_content_refuses_before_any_fixture_creation(actual_copy, tmp_path, monkeypatch):
    monkeypatch.setattr(fixture, "git_blob", lambda *args: b"not the exact historical Git blob\n")
    with pytest.raises(ValueError):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_private_materialization_is_new_and_keeps_actual_sources_quiet(actual_copy, tmp_path, admitted):
    before = {name: (actual_copy / name).read_bytes() for name in admitted}
    root = fixture.materialize(actual_copy, tmp_path / "historical")
    assert {name: (actual_copy / name).read_bytes() for name in admitted} == before
    assert {name: (root / name).read_bytes() for name in admitted} == admitted
    fixture.validate_fixture(root)
    with pytest.raises(ValueError, match="new canonical"):
        fixture.materialize(actual_copy, root)
    with pytest.raises(ValueError, match="new canonical"):
        fixture.materialize(actual_copy, Path("relative"))
    (root / "extra.cjs").write_bytes(b"// extra\n")
    with pytest.raises(ValueError, match="namespace"):
        fixture.validate_fixture(root)


def test_late_current_source_change_refuses_before_materialization(actual_copy, tmp_path, monkeypatch):
    previous = fixture.git_blob
    calls = []
    name = next(iter(fixture.CURRENT_CHANGED_PINS))

    def changed(root, oid, size):
        calls.append(oid)
        result = previous(root, oid, size)
        if len(calls) == 1:
            path = root / name
            path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(fixture, "git_blob", changed)
    with pytest.raises(ValueError, match="changed during"):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert len(calls) == 31 and not (tmp_path / "refused").exists()


def test_returned_data_and_decoded_maps_cannot_poison_later_authentication(actual_copy, admitted):
    before = copy.deepcopy((fixture.MAP_PINS, fixture.HISTORICAL_PINS, fixture.CURRENT_CHANGED_PINS))
    first = fixture.historical_payloads(actual_copy)
    first[next(iter(fixture.HISTORICAL_PINS))] = b"mutated caller buffer"
    additional, mapping = fixture.descriptors(admitted)
    additional["commands"].clear()
    mapping["phases"].clear()
    second = fixture.historical_payloads(actual_copy)
    assert second == admitted and second is not admitted and second is not first
    assert (fixture.MAP_PINS, fixture.HISTORICAL_PINS, fixture.CURRENT_CHANGED_PINS) == before
    fixture.validate_payloads(second)


@pytest.mark.parametrize("frame", ("LF", "CRLF", "mixed", "bare_CR", "BOM"))
def test_input_frames_are_finite_and_old_Git_bytes_remain_exact(admitted, frame):
    raw = admitted["web/static/js/api.js"]
    if frame == "LF":
        assert fixture.canonical(raw) == raw
    elif frame == "CRLF":
        assert fixture.canonical(raw.replace(b"\n", b"\r\n")) == raw
    else:
        changed = raw.replace(b"\n", b"\r\n" if frame == "mixed" else b"\r", 1)
        if frame == "BOM":
            changed = b"\xef\xbb\xbf" + raw
        with pytest.raises(ValueError, match="uniform LF/CRLF"):
            fixture.canonical(changed)


def test_hardlink_and_oversize_sources_reject_before_git(actual_copy, tmp_path):
    name = next(iter(fixture.HISTORICAL_PINS))
    path = actual_copy / name
    original = path.read_bytes()
    other = tmp_path / "hardlink"
    os.link(path, other)
    with pytest.raises(ValueError, match="single-link"):
        fixture.historical_payloads(actual_copy)
    other.unlink()
    path.write_bytes(b"x" * (fixture.MAX_BYTES + 1))
    with pytest.raises(ValueError, match="bounded regular"):
        fixture.historical_payloads(actual_copy)
    path.write_bytes(original)


def test_actual_git_size_and_identity_limits_are_preserved():
    pin = next(iter(fixture.HISTORICAL_PINS.values()))
    with pytest.raises(ValueError, match="size differs"):
        fixture.git_blob(ROOT, pin["git_blob"], pin["bytes"] + 1)
    for oid, size in (("bad-oid", 1), (pin["git_blob"], True), (pin["git_blob"], fixture.MAX_BYTES + 1)):
        with pytest.raises(ValueError, match="bounded original Git"):
            fixture.git_blob(ROOT, oid, size)
