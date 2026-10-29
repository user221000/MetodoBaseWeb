"""Finite APT child and historical transports; no APT, Docker or service calls."""
from __future__ import annotations

import copy
import hashlib
import importlib
import io
import json
import shlex
import tarfile
import zipfile
from pathlib import Path
from types import FunctionType

import pytest

from tests.ci_image57 import authority, bridge, bridge_guest, context
from tests.ci_web39 import native_parent_inputs as historical
from tests.ci_web39 import recipes

ROOT = Path(__file__).resolve().parents[1]
PARENT = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]


@pytest.fixture(scope="module")
def actual_inputs():
    return {name: (ROOT / name).read_bytes() for name in PARENT}


def test_child_is_exactly_two_inputs_and_inverse_recovers_all_twelve_parent_pins(actual_inputs):
    restored, disclosure = context.native_parent_payloads(actual_inputs)
    assert disclosure == context.native_transition()
    assert {name for name in PARENT if actual_inputs[name] != restored[name]} == set(context.APT_CHILD_PINS)
    assert len(PARENT) == 12 and len(context.APT_CHILD_PINS) == 2
    for name, pin in PARENT.items():
        assert len(restored[name]) == pin["bytes"]
        assert hashlib.sha256(restored[name]).hexdigest() == pin["raw_sha256"]
    assert context.native_parent_payloads(restored) == (restored, None)
    docker = actual_inputs["Dockerfile"]
    assert docker.count(b"https://snapshot.debian.org/archive/debian/20261029T082808Z") == 6
    assert docker.count(b"https://snapshot.debian.org/archive/debian-security/20261029T131250Z") == 3
    assert b"check-valid-until=no" not in docker and b"Check-Valid-Until=false" not in docker
    assert b"Check-Date=false" not in docker


@pytest.mark.parametrize("name", tuple(PARENT))
def test_each_critical_input_tamper_is_rejected_including_all_ten_inherited(actual_inputs, name):
    bad = dict(actual_inputs)
    raw = bad[name]
    bad[name] = bytes([raw[0] ^ 1]) + raw[1:]
    with pytest.raises(ValueError):
        context.native_parent_payloads(bad)


@pytest.mark.parametrize("name", tuple(context.APT_CHILD_PINS))
def test_parent_child_mixture_is_rejected(actual_inputs, name):
    restored, _ = context.native_parent_payloads(actual_inputs)
    mixed = dict(actual_inputs)
    mixed[name] = restored[name]
    with pytest.raises(ValueError, match="two-input"):
        context.native_parent_payloads(mixed)


@pytest.mark.parametrize("fault", ["missing", "extra", "CRLF", "inverse-count", "rehashed-unreviewed-byte"])
def test_inventory_framing_and_inverse_remain_required_after_child_hash_check(actual_inputs, monkeypatch, fault):
    bad = dict(actual_inputs)
    if fault == "missing":
        bad.pop("Dockerfile")
    elif fault == "extra":
        bad["unreviewed"] = b"arbitrary"
    elif fault == "CRLF":
        bad["Dockerfile"] = bad["Dockerfile"].replace(b"\n", b"\r\n")
    elif fault == "inverse-count":
        inverse = dict(context.APT_INVERSE)
        first, *rest = inverse["Dockerfile"]
        inverse["Dockerfile"] = ((first[0], first[1], first[2] + 1), *rest)
        monkeypatch.setattr(context, "APT_INVERSE", inverse)
    else:
        bad["Dockerfile"] += b"# unreviewed source even after a blind child hash refresh\n"
        pins = copy.deepcopy(context.APT_CHILD_PINS)
        raw = bad["Dockerfile"]
        pins["Dockerfile"] = {"bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                     usedforsecurity=False).hexdigest()}
        monkeypatch.setattr(context, "APT_CHILD_PINS", pins)
    with pytest.raises(ValueError):
        context.native_parent_payloads(bad)


def make_manifest(directory, payloads, disclosure):
    files = {**payloads, **{name: (ROOT / name).read_bytes() for name in context.CORPUS}}
    records = []
    archive = directory / "source-context.tar"
    with tarfile.open(archive, "x", format=tarfile.USTAR_FORMAT) as output:
        for name, raw in files.items():
            member = tarfile.TarInfo(name)
            member.mode = 0o644
            member.size = len(raw)
            output.addfile(member, io.BytesIO(raw))
            records.append({"path": name, "mode": "100644", "bytes": len(raw),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                         usedforsecurity=False).hexdigest()})
    manifest = {"source_commit": "a" * 40, "source_tree": "b" * 40,
        "archive_bytes": archive.stat().st_size, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "all_members_readback": True, "current57_critical_inputs_exact": 12,
        "runtime_distributions_expected": 57, "files": records,
        "raw_bytes": sum(row["bytes"] for row in records), "native_input_transition": disclosure}
    (directory / "source-manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    return manifest


def test_real_tar_readback_accepts_exact_child_and_refuses_missing_changed_or_untyped_descriptor(tmp_path, actual_inputs):
    manifest = make_manifest(tmp_path, actual_inputs, context.native_transition())
    value, records = context.validate_manifest(tmp_path, "a" * 40, proof_required=False)
    assert value == manifest and len(records) == 16
    # This is metadata/TAR validation; no synthetic Git proof is accepted here.
    variants = [None, {}, dict(context.native_transition(), changed_input_count=3),
                dict(context.native_transition(), date_or_expiry_override=0)]
    for disclosure in variants:
        changed = dict(manifest, native_input_transition=disclosure)
        (tmp_path / "source-manifest.json").write_text(json.dumps(changed), encoding="utf8")
        with pytest.raises(ValueError, match="disclosure"):
            context.validate_manifest(tmp_path, "a" * 40, proof_required=False)


def test_original_parent_context_remains_accepted_with_its_own_disclosure(tmp_path, actual_inputs):
    restored, _ = context.native_parent_payloads(actual_inputs)
    make_manifest(tmp_path, restored, None)
    assert context.validate_manifest(tmp_path, "a" * 40, proof_required=False)[0]["native_input_transition"] is None


@pytest.mark.parametrize("fault", ["absent", "changed", "parent-claim"])
def test_contract_must_repeat_child_disclosure_and_separate_parent_scope(monkeypatch, tmp_path, fault):
    disclosure = context.native_transition()
    monkeypatch.setattr(context, "validate_manifest", lambda *a, **k: ({"native_input_transition": disclosure}, {}))
    contract = {"schema": "current-image57-input-v1", "source": "a" * 40,
                "native_input_transition": disclosure, "native_source_checks_scope": "authenticated_parent_only"}
    if fault == "absent":
        contract.pop("native_input_transition")
    elif fault == "changed":
        contract["native_input_transition"] = dict(disclosure, inherited_input_count=9)
    else:
        contract["native_source_checks_scope"] = "exact_current57_parent"
    with pytest.raises(ValueError, match="disclosure|parent verification"):
        context.validate_contract(tmp_path, contract)


def test_transition_code_and_its_raw_authorities_already_travel_in_exact_bridge_capsule():
    assert bridge.CODE_PATHS == bridge_guest.CODE_PATHS
    assert "tests/ci_image57/context.py" in bridge.CODE_PATHS
    for name in ("container-inputs.json.RAW", "container_inputs.py.RAW", "image_context.py.RAW"):
        authority.raw(name)
        assert "tests/ci_image57/fixtures/" + name in bridge.CODE_PATHS
    assert len(bridge.CODE_PATHS) + len(bridge_guest.CONTEXT_NAMES) + 1 == 23


@pytest.mark.parametrize("name", tuple(historical.MODULES))
def test_companion_preserves_each_original_codetype_marks_and_original_globals(name):
    original = historical.authenticated_module(name)
    old = {label: value.__globals__["ROOT"] for label, value in vars(original).items()
           if label.startswith("test_") and isinstance(value, FunctionType)}
    companion = importlib.import_module(historical.MODULES[name]["companion"])
    for label, root in old.items():
        before = getattr(original, label)
        after = getattr(companion, label)
        assert after is not before and after.__code__ is before.__code__
        assert getattr(after, "pytestmark", []) == getattr(before, "pytestmark", [])
        assert before.__globals__["ROOT"] is root
        assert after.__globals__["ROOT"] is companion.PARENT_TRANSPORT
    assert companion.PARENT_TRANSPORT.reads == frozenset(historical.MODULES[name]["reads"])


@pytest.mark.parametrize("name", tuple(historical.MODULES))
def test_runtime_assertion_replacement_cannot_pass_source_only_authentication(monkeypatch, name):
    original = historical.authenticated_module(name)
    label = next(label for label in vars(original) if label.startswith("test_"))
    monkeypatch.setattr(original, label, lambda: None)
    with pytest.raises(ValueError, match="CodeType"):
        historical.authenticated_module(name)


def test_parent_proxy_authenticates_before_redirect_and_bandit_keeps_only_docker_transport(tmp_path):
    parent = historical.ParentRoot(ROOT, ("Dockerfile",))
    with pytest.raises(ValueError, match="before authenticated"):
        parent / "Dockerfile"
    parent.prepare(tmp_path)
    assert hashlib.sha256((parent / "Dockerfile").read_bytes()).hexdigest() == PARENT["Dockerfile"]["raw_sha256"]
    assert parent / "requirements-container-apt-metadata.lock" == ROOT / "requirements-container-apt-metadata.lock"
    assert set(parent.files) == {"Dockerfile"}


def companion_ids(originals=None):
    return [(pin["companion"], case) for name, pin in historical.MODULES.items()
            if originals is None or name in originals for case in historical.CASE_NAMES[name]]


def test_exact83_and_declared_full_subsets_are_required_by_current_recipes():
    rows = companion_ids()
    assert historical.require_parent_companions(rows) == 83
    for name, pin in historical.MODULES.items():
        assert historical.require_parent_companions(companion_ids({name}), {name}) == pin["count"]
        assert "--ignore=" + name.replace(".", "/") + ".py" in recipes.CURRENT_RUNTIME_SELECTORS
        assert not any(item == name.replace(".", "/") + ".py" for item in recipes.CONTROL_SELECTORS)
    assert "tests/test_current39_container_parent40.py" in recipes.CONTROL_SELECTORS


@pytest.mark.parametrize("fault", ["missing40", "missing25", "missing18", "duplicate", "original", "renamed", "subset", "empty"])
def test_identity_guard_rejects_missing_duplicated_relabelled_or_incomplete_subsets(fault):
    rows = companion_ids()
    if fault.startswith("missing"):
        count = int(fault.removeprefix("missing"))
        module = next(pin["companion"] for pin in historical.MODULES.values() if pin["count"] == count)
        rows.remove(next(row for row in rows if row[0] == module))
    elif fault == "duplicate":
        rows.append(rows[0])
    elif fault == "original":
        name = next(iter(historical.MODULES))
        rows[0] = (name, rows[0][1])
    elif fault == "renamed":
        rows[0] = (rows[0][0], "unreviewed")
    elif fault == "subset":
        rows = companion_ids({"tests.test_ci_web37_bandit_registry"})[:-1]
        with pytest.raises(ValueError):
            historical.require_parent_companions(rows, {"tests.test_ci_web37_bandit_registry"})
        return
    else:
        rows = []
    with pytest.raises(ValueError):
        historical.require_parent_companions(rows)


@pytest.mark.parametrize("suite", ["serial", "parallel", "controls", "registry-controls", "release-controls"])
def test_actual_runner_rejects_an_incomplete_parent_selection_before_execution(tmp_path, monkeypatch, suite):
    from tests.ci_web39 import run_web

    names = None
    if suite == "controls":
        names = {"tests.test_security_container37_portable_peer"}
    elif suite in {"registry-controls", "release-controls"}:
        names = {"tests.test_ci_web37_bandit_registry"}
    rows = companion_ids(names)[:-1]
    calls = []

    def collection_only(argv, source, environment, log):
        calls.append(argv)
        assert "--output" in argv, "Required selection reached runtime before guard"
        Path(argv[argv.index("--output") + 1]).write_text(json.dumps(rows), encoding="utf8")
        return 0

    monkeypatch.setattr(run_web, "execute", collection_only)
    monkeypatch.setattr(run_web, "python_source_archive", lambda _environment: None)
    monkeypatch.setattr(run_web, "require_scanner_safety_companion", lambda _rows: None)
    monkeypatch.setattr(run_web, "require_native_expiry_replacement", lambda _rows: None)
    with pytest.raises(ValueError, match="exact current39 companion identities"):
        run_web.pytest_gate(tmp_path, {}, suite)
    assert len(calls) == 1


@pytest.fixture(scope="module")
def ca_guard(actual_inputs):
    docker = actual_inputs["Dockerfile"]
    start = docker.index(context.CA_REPAIR_HUNK["anchor"])
    hunk = docker[start:start + context.CA_REPAIR_HUNK["bytes"]]
    assert hashlib.sha256(hunk).hexdigest() == context.CA_REPAIR_HUNK["sha256"]
    assert hunk.count(b"update-ca-certificates --fresh; \\\n") == 1
    assert hunk.count(b"python -I -B /tmp/metodobase-ca-g3.py ") == 2
    assert b"RUN <<" not in docker and b"# syntax=" not in docker
    quoted = hunk.split(b"printf '%s\\n' \\\n", 1)[1].split(b"        > /tmp/metodobase-ca-g3.py", 1)[0]
    code = ("\n".join(shlex.split(quoted.decode("utf8").replace("\\\n", ""))) + "\n").encode()
    assert hashlib.sha256(code).hexdigest() == "06f1f93e4003c07755d4ca2c2de405f02c57e3789d7df27008108108ee1a200b"
    namespace = {"__name__": "authenticated_Docker_CA_guard_inert"}
    exec(compile(code, "authenticated-Docker-CA-guard", "exec"), namespace)
    fixture = (ROOT / "tests/ci_web39/fixtures/base-ca-g3-20261029.zip").read_bytes()
    assert len(fixture) == 232112 and hashlib.sha256(fixture).hexdigest() == "bc342588c6536fba151d2fd71c3e27bbe26c8d4f3d1953119a3da21a0bc6eb59"
    with zipfile.ZipFile(io.BytesIO(fixture)) as archive:
        assert archive.namelist() == ["ca-certificates.crt", "ca-certificates.conf", "emSign_ECC_Root_CA_-_G3.crt"]
        inputs = {name: archive.read(name) for name in archive.namelist()}
    bundle, conf, source = (inputs[name] for name in ("ca-certificates.crt", "ca-certificates.conf", "emSign_ECC_Root_CA_-_G3.crt"))
    values = set(namespace["der_hashes"](bundle))
    state, changed = namespace["before_state"](bundle, conf, source, values)
    retained = [block for block in namespace["PEM"].findall(bundle)
                if namespace["der_hashes"](block) != [namespace["TARGET_DER"]]]
    after = b"\n".join(retained) + b"\n"
    return namespace, bundle, conf, source, values, state, changed, after


def test_actual_ca_guard_accepts_only_the_exact_other149_of_the_authenticated_base(ca_guard):
    guard, _bundle, _conf, source, values, state, changed, after = ca_guard
    remaining = values - {guard["TARGET_DER"]}
    result = guard["after_state"](state, after, changed, source, remaining, remaining)
    assert result["before_count"] == 150 and result["after_count"] == 149
    assert result["removed_der_sha256"] == [guard["TARGET_DER"]]
    assert result["other149_preserved"] is True and result["disabled_source_retained"] is True
    assert result["CApath_and_default_SSLContext_match"] is True
    # These are pure controls over public FROM bytes; update-ca, final CApath and
    # actual image startup still require their separate Linux execution.


@pytest.mark.parametrize("field", ["bundle", "config", "source"])
def test_ca_guard_refuses_any_changed_base_input_before_configuration_write(ca_guard, field):
    guard, bundle, conf, source, values, _state, _changed, _after = ca_guard
    inputs = {"bundle": bundle, "config": conf, "source": source}
    inputs[field] += b"\n"
    with pytest.raises(ValueError, match="Immutable base CA inputs differ"):
        guard["before_state"](inputs["bundle"], inputs["config"], inputs["source"], values)


@pytest.mark.parametrize("fault", ["target-retained", "other-removed", "other-replaced", "duplicate", "active-config",
                                   "source-changed", "CApath-target", "SSL-target", "state-authority"])
def test_ca_guard_rejects_target_retention_other_ca_loss_and_incomplete_tls_paths(ca_guard, fault):
    guard, bundle, conf, source, values, state, changed, after = ca_guard
    state = copy.deepcopy(state)
    capath = defaults = values - {guard["TARGET_DER"]}
    if fault == "target-retained":
        after = bundle
    elif fault == "other-removed":
        after = b"\n".join(guard["PEM"].findall(after)[1:]) + b"\n"
    elif fault == "other-replaced":
        after = b"\n".join(guard["PEM"].findall(after)[1:]) + b"\n" + source
    elif fault == "duplicate":
        after += guard["PEM"].findall(after)[0] + b"\n"
    elif fault == "active-config":
        changed = conf
    elif fault == "source-changed":
        source += b"\n"
    elif fault == "CApath-target":
        capath = values
    elif fault == "SSL-target":
        defaults = values
    else:
        state["before_der_sha256"][0] = "0" * 64
    with pytest.raises(ValueError):
        guard["after_state"](state, after, changed, source, capath, defaults)


def test_blind_child_hash_refresh_cannot_admit_a_changed_ca_hunk(actual_inputs, monkeypatch):
    bad = dict(actual_inputs)
    bad["Dockerfile"] = bad["Dockerfile"].replace(b"update-ca-certificates --fresh", b"update-ca-certificates        ", 1)
    raw = bad["Dockerfile"]
    pins = copy.deepcopy(context.APT_CHILD_PINS)
    pins["Dockerfile"] = {"bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                 usedforsecurity=False).hexdigest()}
    monkeypatch.setattr(context, "APT_CHILD_PINS", pins)
    with pytest.raises(ValueError, match="CA repair hunk SHA"):
        context.native_parent_payloads(bad)


def test_descriptor_cannot_omit_or_relabel_the_os_ca_source_transition():
    disclosure = context.native_transition()
    ca = disclosure["OS_truststore_repair"]
    assert ca["hunk_sha256"] == context.CA_REPAIR_HUNK["sha256"]
    assert ca["hunk_bytes"] == context.CA_REPAIR_HUNK["bytes"]
    assert ca["before_count"] == 150 and ca["after_count"] == 149
    assert ca["other149_required_unchanged"] is True
    assert ca["source_scope"] == "exact_build_guard_not_final_image_observation"


@pytest.mark.parametrize("is_child", [False, True])
def test_direct_build_probe_api_used_by_bridge_discloses_parent_and_child(tmp_path, monkeypatch, is_child):
    from tests import test_ci_image57_offline as original
    from tests.ci_image57 import run

    # Execute the existing complete inert Docker control unchanged, observing
    # its real API return. No Docker binary, process or image is involved.
    monkeypatch.setattr(original, "ARTIFACT", tmp_path)
    monkeypatch.setattr(original, "SERIAL", 0)
    actual = run.build_probe
    observed = []
    disclosure = context.native_transition() if is_child else None

    def capture(private, contract, docker, tag):
        contract = dict(contract, native_input_transition=disclosure)
        value = actual(private, contract, docker, tag)
        observed.append(value)
        return value

    monkeypatch.setattr(run, "build_probe", capture)
    original.Offline57("test_17_complete_simulated_build_probe_process_contract").test_17_complete_simulated_build_probe_process_contract()
    assert len(observed) == 1
    assert observed[0]["native_parent_merkle_objects"] == 21
    assert observed[0]["native_input_transition"] == disclosure
