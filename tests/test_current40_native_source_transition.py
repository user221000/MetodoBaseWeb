"""Current native source admission rejects drift before parent projections.

These are source controls. No Docker build, image inspection or deployment is
performed, and the original native/APT input authorities stay authoritative.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from tests.ci_image57 import authority, context, production_child

ROOT = Path(__file__).resolve().parents[1]
NAMES = tuple(context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"])


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def inputs():
    from tests.ci_web41.native40_source_fixture import production40_inputs
    return production40_inputs(ROOT)


def records(payloads):
    return {name: {"bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                 usedforsecurity=False).hexdigest()} for name, raw in payloads.items()}


def test_published_source_recovers_both_exact_parent_authorities():
    actual = inputs()
    parent, transition = context.native_parent_payloads(actual)
    assert transition == production_child.transition(context.native_transition())
    manifest = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]
    assert {name: (len(raw), hashlib.sha256(raw).hexdigest()) for name, raw in parent.items()} == {
        name: (pin["bytes"], pin["raw_sha256"]) for name, pin in manifest.items()}
    apt = dict(actual, Dockerfile=production_child.inverse(actual["Dockerfile"]))
    original_parent, original_transition = context.native_parent_payloads(apt)
    assert original_parent == parent and original_transition == context.native_transition()
    original, transition = context.native_parent_payloads(parent)
    assert original == parent and transition is None


@pytest.mark.parametrize("name", NAMES)
def test_each_of_twelve_actual_inputs_rejects_even_one_byte_drift(name):
    actual = inputs()
    actual[name] = actual[name] + b"\n"
    with pytest.raises(ValueError):
        context.native_parent_payloads(actual)


@pytest.mark.parametrize("offset", [0, production_child.PARENT_BYTES - 1,
                                  production_child.PARENT_BYTES, -1])
def test_parent_or_production_suffix_mutations_cannot_be_hidden_by_projection(offset):
    actual = inputs()
    raw = bytearray(actual["Dockerfile"])
    raw[offset] ^= 1
    actual["Dockerfile"] = bytes(raw)
    with pytest.raises(ValueError):
        context.native_parent_payloads(actual)
    with pytest.raises(ValueError):
        production_child.inverse(actual["Dockerfile"])


def test_forged_length_or_git_object_does_not_admit_same_hash_record():
    original = records(inputs())
    for key in ("bytes", "git_blob"):
        modified = deepcopy(original)
        modified["Dockerfile"][key] = 0 if key == "bytes" else "0" * 40
        with pytest.raises(ValueError):
            context.native_pins(modified)


def test_unknown_payload_or_missing_payload_cannot_enter_parent_transport():
    actual = inputs()
    for malformed in ({**actual, "extra": b""}, {name: raw for name, raw in actual.items() if name != "Dockerfile"}):
        with pytest.raises(ValueError):
            context.native_parent_payloads(malformed)
