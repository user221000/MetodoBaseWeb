"""Current41 source transitions retain criteria and reject unreviewed inputs."""
import ast
import difflib
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web41 import source_companion as current

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = current.specification()
ENTRIES = tuple(CATALOGUE["entries"])


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    """This module validates source/AST contracts and performs no SQL."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def policy_assertion_trace(before, after):
    def assertions(tree):
        return {node.name: [ast.dump(item, include_attributes=False) for item in ast.walk(node)
                           if isinstance(item, ast.Assert)] for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    a, b = assertions(before), assertions(after)
    assert set(a) == set(b)
    result = []
    for function in a:
        if a[function] == b[function]:
            continue
        assert len(b[function]) >= len(a[function])
        edits = []
        for tag, first, last, current_first, current_last in difflib.SequenceMatcher(a=a[function], b=b[function], autojunk=False).get_opcodes():
            if tag != "equal":
                assert tag != "delete"
                edits.append({"kind": tag, "before_index": first, "after_index": current_first,
                              "before": a[function][first:last], "after": b[function][current_first:current_last]})
        result.append({"function": function, "before_assertions": len(a[function]),
                       "after_assertions": len(b[function]), "edits": edits})
    return result


@pytest.mark.parametrize("name", ENTRIES)
@pytest.mark.parametrize("crlf", [False, True])
def test_only_both_complete_explicit_original_frames_recover_exact_current_source(name, crlf):
    entry = CATALOGUE["entries"][name]
    raw = (ROOT / entry["original"]).read_bytes().replace(b"\r\n", b"\n")
    if crlf:
        raw = raw.replace(b"\n", b"\r\n")
    result = current.rewrite(raw, entry)
    assert hashlib.sha256(result).hexdigest() == entry["current_sha256_LF"]
    assert current.source_bytes(name) == result
    compile(result, str(ROOT / name), "exec", dont_inherit=True)


@pytest.mark.parametrize("name", ENTRIES)
@pytest.mark.parametrize("fault", ["append", "BOM", "UTF16", "mixed", "byte"])
def test_any_unreviewed_original_byte_or_transport_refuses(name, fault):
    entry = CATALOGUE["entries"][name]
    raw = (ROOT / entry["original"]).read_bytes().replace(b"\r\n", b"\n")
    if fault == "append":
        raw += b"\n"
    elif fault == "BOM":
        raw = b"\xef\xbb\xbf" + raw
    elif fault == "UTF16":
        raw = raw.decode().encode("utf16")
    elif fault == "mixed":
        raw = raw.replace(b"\n", b"\r\n", 1)
    else:
        raw = bytes([raw[0] ^ 1]) + raw[1:]
    with pytest.raises(ValueError):
        current.rewrite(raw, entry)


@pytest.mark.parametrize("name", ENTRIES)
@pytest.mark.parametrize("fault", ["count", "bool", "empty", "result"])
def test_changed_edit_budget_or_output_identity_is_rejected(name, fault):
    entry = deepcopy(CATALOGUE["entries"][name])
    raw = (ROOT / entry["original"]).read_bytes()
    if fault == "count":
        entry["literal_edits"][0]["count"] += 1
    elif fault == "bool":
        entry["literal_edits"][0]["count"] = True
    elif fault == "empty":
        entry["literal_edits"][0]["old"] = ""
    else:
        entry["current_sha256_LF"] = "0" * 64
    with pytest.raises(ValueError):
        current.rewrite(raw, entry)


@pytest.mark.parametrize("name", ENTRIES)
def test_all_assertions_and_test_function_counts_remain_except_disclosed_revision_and_paths(name):
    entry = CATALOGUE["entries"][name]
    original = (ROOT / entry["original"]).read_bytes().replace(b"\r\n", b"\n")
    transformed = current.source_bytes(name)
    before = ast.parse(original)
    after = ast.parse(transformed)
    original_assertions = [ast.dump(node, include_attributes=False) for node in ast.walk(before) if isinstance(node, ast.Assert)]
    current_assertions = [ast.dump(node, include_attributes=False) for node in ast.walk(after) if isinstance(node, ast.Assert)]
    if "policy_assertion_trace" in entry:
        approved = {
            "tests/current41_stripe_refund_ledger_author.py": "test_partial_refund_cannot_be_reported_as_full_even_if_snapshot_says_full",
            "tests/current41_stripe_refund_ledger_peer.py": "test_partial_refund_is_never_misreported_as_full_refund",
            "tests/current41_stripe_webhook_version_contract.py": "test_stale_paid_snapshot_cannot_override_current_unfunded_invoice",
        }
        trace = policy_assertion_trace(before, after)
        if name == "tests/test_current41_quality_companion.py":
            assert entry["approved_policy_scope"] == 'current41_quality_date20261103_exact_MD5_retirement31_bindings408_technical19_source_no_baseline_reapproval'
            assert [row["function"] for row in trace] == ['report', 'report311', 'test_current_native_admission_checks_real_child2_ten_inherited_and_original21', 'test_native_source_admission_requires_no_site_packages_or_implicit_packaging', 'test_actual26_match_is_proposal_only_until_the_separate_test_approval', 'test_historical_actual311_report_still_requires_its_interpreter_and_exact_current_runtime_bindings', 'test_mixing_only_one_actual311_followup_descriptor_with312_never_matches_either_full_multiset', 'test_original_baseline_multiset_cannot_substitute_one_approved_occurrence_for_another', 'test_complete_approved_physical_sources_without_git_are_copied_byte_exactly']
        else:
            assert entry["approved_policy_scope"] == "user_partial_refund_keeps_paid_access_and_observed_cumulative_amount_no_time_extension"
            assert len(trace) == 1 and trace[0]["function"] == approved[name]
        assert trace == entry["policy_assertion_trace"]
    else:
        for index, assertion in enumerate(current_assertions):
            for edit in reversed(entry["literal_edits"]):
                assertion = assertion.replace(edit["new"], edit["old"])
            current_assertions[index] = assertion
        assert current_assertions == original_assertions
    names = lambda tree: [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name.startswith(("test_", "Test"))]
    current_names = names(after)
    for index, name_after in enumerate(current_names):
        for edit in reversed(entry["literal_edits"]):
            name_after = name_after.replace(edit["new"], edit["old"])
        current_names[index] = name_after
    assert current_names == names(before)


def test_current75_catalogue_preserves_old_exceptions_and_renews_only_two_published_routine_inputs():
    from tests.ci_web41 import composition

    value = composition.specification()
    original = json.loads((ROOT / "tests/ci_web39/current-fixture-map.json").read_bytes())
    assert value["schema"] == "20261102_payment_refund_facts"
    privacy = "tests/test_privacy39_http.py"
    assert set(value["modules"]) == set(original["modules"]) | {privacy} and len(value["modules"]) == 76
    changed = []
    for name in original["modules"]:
        entry = value["modules"][name]
        raw = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(raw).hexdigest() == entry["source_sha256_LF"]
        before = deepcopy(original["modules"][name])
        if before["source_sha256_LF"] != entry["source_sha256_LF"]:
            changed.append(name)
            before["source_sha256_LF"] = entry["source_sha256_LF"]
        # The exceptional scope label names its current runtime precisely.
        before = json.loads(json.dumps(before).replace("current39", "current41"))
        assert before == entry
    # The original routine renewals and the later finite email admission are separate.
    from tests.ci_web41.google_mail_fixture_transition import TRANSITIONS
    email_sources = {"tests/test_google33_http.py", "tests/test_google33_headers.py",
                     "tests/test_google33_conflict_window.py", "tests/test_account_security37_critical_edges.py",
                     "tests/test_google33_recovery.py", "tests/test_browser31_google_compat.py",
                     "tests/test_current_publication_fixture_review.py"}
    assert set(TRANSITIONS) == email_sources
    assert set(changed) == {"tests/test_routine_catalog.py", "tests/test_security_routines_http_peer.py"} | email_sources
    for name in email_sources:
        assert original["modules"][name]["source_sha256_LF"] == TRANSITIONS[name][0]
        assert value["modules"][name]["source_sha256_LF"] == TRANSITIONS[name][1]
    assert value["modules"][privacy] == {
        "source_sha256_LF": hashlib.sha256((ROOT / privacy).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "replacements": {
            "privacy39_engine": {"module": "tests.privacy39_fixtures", "function": "privacy39_engine"},
            "account37_engine": {"module": "tests.privacy39_fixtures", "function": "privacy39_engine"},
        },
    }


def test_actual41_composition_still_refuses_historical39_40_and_unknown_head(monkeypatch):
    from tests.ci_web41 import composition
    from web.database import schema_control

    for head in ("20261023_privacy_disposition", "20261031_gym_equipment", "unknown"):
        monkeypatch.setattr(schema_control, "expected_head", lambda: head)
        with pytest.raises(pytest.UsageError):
            composition.pytest_configure(SimpleNamespace(getoption=lambda _: True))
    monkeypatch.setattr(schema_control, "expected_head", lambda: "20261102_payment_refund_facts")
    config = SimpleNamespace(getoption=lambda _: True)
    composition.pytest_configure(config)
    assert config._web41_bindings == []


def test_unknown_companion_and_changed_catalogue_fail_closed(monkeypatch, tmp_path):
    with pytest.raises(ValueError):
        current.source_bytes("tests/not-reviewed.py")
    target = tmp_path / current.CATALOGUE
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / current.CATALOGUE).read_bytes() + b"\n")
    monkeypatch.setattr(current, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        current.specification()


def test_current_pg_file_set_tracks_every_authenticated_original_source_for_full_quietness():
    from tests.ci_web41 import pg_contract

    originals = {row["original"] for row in CATALOGUE["entries"].values()}
    assert originals <= set(pg_contract.BOUND)
