"""Current-source quality admission; synthetic approvals stay in test copies."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tests.ci_image57 import authority, context
from tests.ci_web39 import bandit_review, quality, verify_quality

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 29)
PINS = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]


def approved_test_record(root):
    value = context.json_object((root / quality.APPROVAL).read_bytes())
    value["approval"] = "approved"
    value["reviewers"][1]["decision"] = "approved_finite_current26_context_only"
    return value


@contextmanager
def changed(path, data):
    original = path.read_bytes() if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    try:
        yield
    finally:
        if original is None:
            path.unlink()
        else:
            path.write_bytes(original)


@pytest.fixture(scope="module")
def source_template(tmp_path_factory):
    parent = tmp_path_factory.mktemp("current39-quality-source")
    target = authority.private_directory(parent / "source", ROOT)
    verify_quality.copy_source(ROOT, target)
    # Controls start from the exact approved Git frame even when the real
    # checkout was admitted as the complete captured RAW frame. Only this
    # private test copy changes; the positive controls also exercise RAW.
    proposal = context.json_object((target / quality.PROPOSAL).read_bytes())
    for name, pin in proposal["bindings"].items():
        path = target / name
        raw = path.read_bytes()
        selected = next(value for value in (raw, raw.replace(b"\r\n", b"\n"))
                        if hashlib.sha256(value).hexdigest() == pin["authenticated_git_objects_sha256"])
        assert len(selected) == pin["git_bytes"] and quality.git_recipe.object_id("blob", selected) == pin["git_blob"]
        path.write_bytes(selected)
    return target


@pytest.fixture
def control(source_template):
    # The actual repository registry is untouched. This temporary positive is
    # the same explicit test-approval model used by the original18 controls.
    value = approved_test_record(source_template)
    with changed(source_template / quality.APPROVAL, json.dumps(value).encode()):
        yield source_template


@pytest.fixture(scope="module")
def report():
    raw = (ROOT / "tests/ci_web39/fixtures/bandit32-current095-fixture.json").read_bytes()
    assert len(raw) == 46259 and hashlib.sha256(raw).hexdigest() == "76470a29289912ea763237136bf9cc465822bedc14c0ee651e44ac0084e90336"
    value = context.json_object(raw)
    assert value["source"] == "095290c4908b1a3afec0bd7448073bba51dbfd50"
    return value["report"]


@pytest.fixture(scope="module")
def report311():
    raw = (ROOT / "tests/ci_web39/fixtures/bandit32-python311-d8df-fixture.json").read_bytes()
    assert len(raw) == 45713 and hashlib.sha256(raw).hexdigest() == "8ef6cea7ad31ca1ab19f23e484243ac93acaeac313e648227c91d401e0b3ef6e"
    value = context.json_object(raw)
    assert value["source"] == "d8df9d4182e06d6c0a9a19915a4ccc8254980bd4"
    assert value["source_report_sha256"] == "2cd0fd41f4535440889f90d56d86f78137206636df3043bc258893d93614c855"
    assert value["Python"].startswith("3.11.15 ") and value["bandit_version"] == "1.9.4"
    return value["report"]


def classify(report, root, **kwargs):
    return quality.classify(report, root, bandit_version="1.9.4", today=TODAY, **kwargs)


def test_current_native_admission_checks_real_child2_ten_inherited_and_original21():
    value = quality.native_source_inputs(ROOT)
    assert value["native_input_count"] == 12 and value["inherited_input_count"] == 10
    assert value["parent_native_merkle_objects"] == 21
    assert value["native_input_transition"] == context.native_transition()
    assert value["runtime_distributions_expected"] == 57


def test_native_source_admission_requires_no_site_packages_or_implicit_packaging():
    code = ("import json,sys; sys.path.insert(0," + repr(str(ROOT)) + "); "
            "from tests.ci_web39.quality import native_source_inputs; "
            "value=native_source_inputs(__import__('pathlib').Path(" + repr(str(ROOT)) + ")); "
            "assert 'packaging' not in sys.modules; "
            "print(json.dumps([value['native_input_count'],value['inherited_input_count'],"
            "value['parent_native_merkle_objects'],value['runtime_distributions_expected']]))")
    process = subprocess.run([sys.executable, "-I", "-S", "-B", "-X", "utf8", "-c", code],
                             cwd=ROOT, capture_output=True, timeout=30, check=False)
    assert process.returncode == 0, process.stderr.decode("utf8", errors="replace")
    assert json.loads(process.stdout) == [12, 10, 21, 57]


@pytest.mark.parametrize("name", tuple(PINS))
def test_every_native_input_tamper_rejects_before_a_current_review(control, report, name):
    assert classify(report, control)["finite_current_review"]["approved_occurrences"] == 26
    path = control / name
    raw = path.read_bytes()
    with changed(path, bytes([raw[0] ^ 1]) + raw[1:]), pytest.raises(ValueError):
        classify(report, control)


def test_parent_transport_cannot_admit_the_current_quality_gate(control):
    payloads = {name: (control / name).read_bytes() for name in PINS}
    parent, _ = context.native_parent_payloads(payloads)
    with changed(control / "Dockerfile", parent["Dockerfile"]), changed(
            control / "requirements-container-apt-metadata.lock", parent["requirements-container-apt-metadata.lock"]):
        with pytest.raises(ValueError, match="current source child2"):
            quality.native_source_inputs(control)


@pytest.mark.parametrize("fault", ["body", "mixed-EOL", "bare-CR"])
def test_web_lock_must_match_the_current57_catalog_without_free_normalization(control, fault):
    path = control / "requirements_web.lock"
    raw = path.read_bytes()
    if fault == "body":
        raw += b"# unreviewed\n"
    elif fault == "mixed-EOL":
        raw = raw.replace(b"\n", b"\r\n", 1)
    else:
        raw += b"\r"
    with changed(path, raw), pytest.raises(ValueError):
        quality.native_source_inputs(control)


def test_actual26_match_is_proposal_only_until_the_separate_test_approval(control, report):
    proposal = context.json_object((control / quality.PROPOSAL).read_bytes())
    baseline = {row["fingerprint"] for row in json.loads((control / "tests/bandit-reviewed-baseline.json").read_bytes())["exceptions"]}
    new = [row for row in report["results"] if quality.fingerprint(row) not in baseline]
    checked = bandit_review.validate_candidate({"errors": [], "results": new}, control, proposal,
        context=quality.REVIEW_CONTEXT, bandit_version="1.9.4")
    assert checked["approved"] is False and checked["exceptions_applied"] == 0
    value = classify(report, control)
    assert value["baseline_occurrences"] == 6 and value["new_occurrences"] == 26
    assert value["finite_current_review"]["historical_baseline_reapproved"] == 0
    assert value["finite_current_review"]["OS_isolation_proven"] is False


def test_actual_tool_version_must_match_the_source_review(control, report):
    with pytest.raises(ValueError, match="contract|version"):
        quality.classify(report, control, bandit_version="0.0.0", today=TODAY)


def test_historical_actual311_report_still_requires_its_interpreter_and_exact_current_runtime_bindings(control, report311, report):
    assert classify(report, control)["new_occurrences"] == 26
    if sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 11):
        value = classify(report311, control)
        assert value["baseline_occurrences"] == 6 and value["new_occurrences"] == 26
        assert value["finite_current_review"]["approved_occurrences"] == 26
        assert value["finite_current_review"]["source_variant"] == "authenticated_git_objects"
        selected = report311
    else:
        with pytest.raises(ValueError, match="finding multiset"):
            classify(report311, control)
        selected = report
    path = control / "web/database/alembic/env.py"
    with changed(path, path.read_bytes() + b"\n# the historical fixture cannot admit a new source\n"):
        with pytest.raises(ValueError):
            classify(selected, control)


@pytest.mark.parametrize("line", [31, 66, 91, 119])
def test_mixing_only_one_actual311_followup_descriptor_with312_never_matches_either_full_multiset(control, report311, report, line):
    assert classify(report, control)["new_occurrences"] == 26
    value = copy.deepcopy(report)
    index = next(index for index, row in enumerate(value["results"])
                 if row["filename"].replace("\\", "/").endswith("web/database/followup_policy.py")
                 and row["line_number"] == line)
    exact311 = next(row for row in report311["results"]
                    if row["filename"].replace("\\", "/").endswith("web/database/followup_policy.py")
                    and row["line_number"] == line)
    assert quality.fingerprint(value["results"][index]) == quality.fingerprint(exact311)
    value["results"][index] = copy.deepcopy(exact311)
    assert len(value["results"]) == 32
    with pytest.raises(ValueError):
        classify(value, control)


@pytest.mark.parametrize("fault", ["missing", "extra-duplicate", "replace-with-duplicate", "expired"])
def test_original_baseline_multiset_cannot_substitute_one_approved_occurrence_for_another(control, report, fault):
    assert classify(report, control)["baseline_occurrences"] == 6
    value = copy.deepcopy(report)
    baseline_index = next(index for index, row in enumerate(value["results"]) if row["test_id"] == "B104")
    duplicated = next(row for row in value["results"]
                      if row["test_id"] == "B310" and row["filename"].replace("\\", "/").endswith("core/licencia.py"))
    today = TODAY
    if fault == "missing":
        value["results"].pop(baseline_index)
    elif fault == "extra-duplicate":
        value["results"].append(copy.deepcopy(duplicated))
    elif fault == "replace-with-duplicate":
        value["results"][baseline_index] = copy.deepcopy(duplicated)
        assert len(value["results"]) == 32
    else:
        today = date(2027, 1, 19)
    with pytest.raises(ValueError, match="six original baseline occurrences and multiplicities"):
        quality.classify(value, control, bandit_version="1.9.4", today=today)


@pytest.mark.parametrize("fault", ["pending", "expired", "root-missing", "matcher", "proposal", "IDs"])
def test_current_review_needs_its_own_root_decision_and_source_authority(control, report, fault):
    value = approved_test_record(control)
    if fault == "pending":
        value["approval"] = "pending"
    elif fault == "expired":
        value["reviewed_on"], value["expires_on"] = "2026-09-01", "2026-10-01"
    elif fault == "root-missing":
        value["reviewers"][1]["decision"] = "pending"
    elif fault == "matcher":
        value["matcher_sha256"] = "0" * 64
    elif fault == "proposal":
        value["proposal_canonical_sha256"] = "0" * 64
    else:
        value["occurrence_ids"] = value["occurrence_ids"][:-1]
    with changed(control / quality.APPROVAL, json.dumps(value).encode()), pytest.raises(ValueError):
        classify(report, control)


@pytest.mark.parametrize("fault", ["empty", "missing", "duplicate", "extra-B602", "span", "rule", "errors", "malformed"])
def test_missing_extra_or_changed_findings_cannot_pass_even_with_an_intact_source(control, report, fault):
    value = copy.deepcopy(report)
    index = next(index for index, row in enumerate(value["results"])
                 if row["filename"].replace("\\", "/").endswith("web/database/product_analytics_policy_v2.py"))
    if fault == "empty":
        value["results"] = []
    elif fault == "missing":
        value["results"].pop(index)
    elif fault == "duplicate":
        value["results"].append(copy.deepcopy(value["results"][index]))
    elif fault == "extra-B602":
        row = copy.deepcopy(value["results"][index])
        row["test_id"] = "B602"
        value["results"].append(row)
    elif fault == "span":
        value["results"][index]["col_offset"] += 1
    elif fault == "rule":
        value["results"][index]["test_id"] = "B602"
    elif fault == "errors":
        value["errors"] = [{"filename": "web/unknown.py", "reason": "unparsed"}]
    else:
        value["results"] = "not a result list"
    with pytest.raises((ValueError, TypeError, KeyError)):
        classify(value, control)


def test_adding_findings_to_the_old_baseline_cannot_bypass_the_current_review(control, report):
    path = control / "tests/bandit-reviewed-baseline.json"
    value = json.loads(path.read_bytes())
    value["exceptions"].extend({"fingerprint": quality.fingerprint(row), "expires": "2099-01-01"}
                               for row in report["results"])
    with changed(path, json.dumps(value).encode()), pytest.raises(ValueError, match="six-entry historical baseline"):
        classify(report, control)


@pytest.mark.parametrize("name", ["web/database/schema_control.py", "web/database/product_analytics_policy_v2.py",
                                  "web/services/current39_new_caller.py", "api_server.py"])
def test_whole_current_sources_and_callers_reject_drift_without_new_findings(control, report, name):
    path = control / name
    raw = path.read_bytes() if path.exists() else b""
    with changed(path, raw + b"\n# an unreviewed source change\n"), pytest.raises(ValueError):
        classify(report, control)


def test_web_scope_retains_runtime_source_and_operations_and_excludes_desktop():
    targets = quality.maintained_targets()
    assert "runtime-source" in targets and "api_server.py" in targets
    assert "db_bootstrap.py" in targets and "scripts/backup_daily.py" in targets
    assert not {"ui_desktop", "design_system", "main.py"} & set(targets)
    assert not any(path.name.startswith("test_desktop") for path in quality.syntax_paths())


@pytest.mark.parametrize("variant", ["captured_main_raw", "authenticated_git_objects"])
def test_complete_approved_physical_sources_without_git_are_copied_byte_exactly(source_template, tmp_path, monkeypatch, variant):
    assert not (source_template / ".git").exists()
    proposal = context.json_object((source_template / quality.PROPOSAL).read_bytes())

    def no_git(*args, **kwargs):
        pytest.fail("A complete authenticated physical universe must not need Git")

    monkeypatch.setattr(context, "git", no_git)
    target = tmp_path / "copied"
    target.mkdir()
    with ExitStack() as changes:
        for name, pin in proposal["bindings"].items():
            path = source_template / name
            raw = path.read_bytes()
            lf = raw.replace(b"\r\n", b"\n")
            expected = pin[variant + "_sha256"]
            selected = next(value for value in (raw, lf, lf.replace(b"\n", b"\r\n"))
                            if hashlib.sha256(value).hexdigest() == expected)
            changes.enter_context(changed(path, selected))
        records = verify_quality.copy_source(source_template, target)
        assert len(proposal["bindings"]) == 369
        for name, pin in proposal["bindings"].items():
            assert (target / name).read_bytes() == (source_template / name).read_bytes()
            assert records[name]["transport"] == "authenticated_physical_whole_universe"
            assert records[name]["source_variant"] == variant
            assert records[name]["sha256"] == pin[variant + "_sha256"]


@pytest.mark.parametrize("fault", ["mixed-universe", "body", "mixed-EOL", "bare-CR"])
def test_ineligible_or_mixed_physical_source_without_git_never_uses_git_to_hide_drift(source_template, tmp_path, monkeypatch, fault):
    proposal = context.json_object((source_template / quality.PROPOSAL).read_bytes())
    name = "web/database/followup_policy.py"
    path = source_template / name
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == proposal["bindings"][name]["authenticated_git_objects_sha256"]
    if fault == "mixed-universe":
        raw = raw.replace(b"\n", b"\r\n")
        assert hashlib.sha256(raw).hexdigest() == proposal["bindings"][name]["captured_main_raw_sha256"]
    elif fault == "body":
        raw += b"\n# a body change must not be replaced by HEAD\n"
    elif fault == "mixed-EOL":
        raw = raw.replace(b"\n", b"\r\n", 1)
    else:
        raw += b"\r"

    def no_git(*args, **kwargs):
        pytest.fail("Ineligible or absent Git transport must reject before any Git invocation")

    monkeypatch.setattr(context, "git", no_git)
    target = tmp_path / "copied"
    target.mkdir()
    expected = "Mixed physical source frames" if fault == "mixed-universe" else "Physical source drift"
    with changed(path, raw), pytest.raises(ValueError, match=expected):
        verify_quality.copy_source(source_template, target)


def test_workflow_selects_current_web_quality_and_real_regressions():
    text = (ROOT / ".github/workflows/ci.yml").read_text("utf8").split("  secrets:", 1)[0]
    assert all("tests/ci_web39/quality.py " + mode in text for mode in ("lint", "syntax", "security"))
    assert "tests/ci_web39/verify_quality.py --evidence" in text
    assert "tests/check_quality.py" not in text and "tests/verify_quality_guards.py" not in text
