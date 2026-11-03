"""Current19 must authenticate before historical40 fixture bytes are returned."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

from tests.ci_image57 import authority, context, production_child, technical_child
from tests.ci_web41 import native40_source_fixture as subject

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def current_source(tmp_path):
    for name, raw in technical_child.read_payloads(ROOT).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return tmp_path


def test_current19_recovers_production40_twelve_and_preserves_authenticated_thirteenth_lock(current_source):
    actual = technical_child.read_payloads(current_source)
    all_parent = technical_child.inverse(actual)
    result = subject.production40_inputs(current_source)
    assert len(actual) == 19 and len(all_parent) == 13 and len(result) == 12
    assert set(all_parent) == set(result) | {"requirements_web.lock"}
    assert {name: technical_child.record(raw) for name, raw in result.items()} == technical_child.PARENT_PINS
    assert technical_child.record(all_parent["requirements_web.lock"]) == technical_child.LOCK_INVERSES["requirements_web.lock"]["parent_pin"]
    assert technical_child.record(result["Dockerfile"]) == production_child.DOCKER_PIN
    original, transition = context.native_parent_payloads(result)
    assert transition == production_child.transition(context.native_transition())
    parent = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]
    assert {name: {"bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in original.items()} == parent
    assert len(result["Dockerfile"]) > production_child.PARENT_BYTES


@pytest.mark.parametrize("name", tuple(technical_child.PINS))
@pytest.mark.parametrize("fault", ["append", "byte", "missing"])
def test_each_current_input_refuses_drift_before_any_inverse_or_historical_selection(current_source, monkeypatch, name, fault):
    path = current_source / name
    original = path.read_bytes()
    if fault == "append":
        path.write_bytes(original + b"\n")
    elif fault == "byte":
        changed = bytearray(original)
        changed[len(changed) // 2] ^= 1
        path.write_bytes(changed)
    else:
        path.unlink()
    calls = []
    inverse = technical_child.inverse
    def record(payloads):
        calls.append(set(payloads))
        return inverse(payloads)
    monkeypatch.setattr(technical_child, "inverse", record)
    with pytest.raises((ValueError, OSError)):
        subject.production40_inputs(current_source)
    assert calls == []


@pytest.mark.parametrize("name", ["runtime-source/technical-close-20261103/extra.txt", "runtime-source/extra/unknown.py"])
def test_extra_native_members_cannot_be_hidden_by_parent_selection(current_source, name):
    path = current_source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"unreviewed private fixture")
    with pytest.raises(ValueError):
        subject.production40_inputs(current_source)


@pytest.mark.parametrize("fault", ["extra", "missing", "foreign_same_count"])
def test_reader_result_requires_nineteen_exact_current_names_before_inverse(current_source, monkeypatch, fault):
    data = technical_child.read_payloads(current_source)
    if fault != "extra":
        data.pop("Dockerfile")
    if fault != "missing":
        data["unreviewed"] = b"private wrong member"
    monkeypatch.setattr(technical_child, "read_payloads", lambda root: data)
    def forbidden(value):
        pytest.fail("Incomplete current source reached an inverse")
    monkeypatch.setattr(technical_child, "inverse", forbidden)
    with pytest.raises(ValueError, match="nineteen current"):
        subject.production40_inputs(current_source)


@pytest.mark.parametrize("fault", ["missing_web", "changed_web", "extra", "APT_Docker"])
def test_inverse_must_recover_all_thirteen_exact_production_parent_payloads(current_source, monkeypatch, fault):
    inverse = technical_child.inverse
    def altered(actual):
        result = inverse(actual)
        if fault == "missing_web":
            result.pop("requirements_web.lock")
        elif fault == "changed_web":
            result["requirements_web.lock"] += b"\n"
        elif fault == "extra":
            result["extra"] = b""
        else:
            result["Dockerfile"] = production_child.inverse(result["Dockerfile"])
        return result
    monkeypatch.setattr(technical_child, "inverse", altered)
    with pytest.raises(ValueError):
        subject.production40_inputs(current_source)


def test_wrong_generation_transition_is_rejected_after_full_authentication(current_source, monkeypatch):
    parent = context.native_parent_payloads
    def wrong(payloads):
        original, _ = parent(payloads)
        return original, context.native_transition()
    monkeypatch.setattr(context, "native_parent_payloads", wrong)
    with pytest.raises(ValueError, match="production40 transition"):
        subject.production40_inputs(current_source)


def test_source_files_remain_current_after_fixture_read(current_source):
    photo = {name: technical_child.record(raw) for name, raw in technical_child.read_payloads(current_source).items()}
    subject.production40_inputs(current_source)
    assert {name: technical_child.record(raw) for name, raw in technical_child.read_payloads(current_source).items()} == photo


def test_original_native_offsets_are_all_meaningful_in_recovered_production_fixture(current_source):
    docker = subject.production40_inputs(current_source)["Dockerfile"]
    for offset in (0, production_child.PARENT_BYTES - 1, production_child.PARENT_BYTES, -1):
        changed = bytearray(docker)
        changed[offset] ^= 1
        with pytest.raises(ValueError):
            production_child.inverse(bytes(changed))


def test_existing_virtual_publisher_context_keeps_host_environment_and_excepthook_unchanged():
    import os

    from tests import test_ci_web37_pg_workflow as original
    before = dict(os.environ)
    hook = sys.excepthook
    environment = {"GITHUB_ACTIONS": "true", "GITHUB_WORKSPACE": str(original.ROOT), "GITHUB_SHA": "a" * 40}
    with pytest.raises(original.BeforeTool):
        original.execute_guard(environment)
    assert len(environment["observed_version_tool_calls"]) == 2
    assert "RUNNER_TEMP" not in environment
    assert os.environ == before and sys.excepthook is hook


def test_fixture_scope_never_claims_runtime_build_or_scanner_acceptance():
    result = subject.production40_inputs(ROOT)
    assert len(result) == 12 and set(result) == set(technical_child.PARENT_PINS)
    assert json.loads(technical_child.read_payloads(ROOT)[technical_child.ACTIVE_SOURCE_PINS])["python_version"] == "3.12.16"
