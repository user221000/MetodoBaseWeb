"""Finite consumer controls that work before and after explicit Root approval."""
import copy
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from tests.ci_web37.bandit_registry import MATCHER, PROPOSAL, REGISTRY, apply_registry

ROOT = Path(__file__).resolve().parents[1]
REVIEW = json.loads(REGISTRY.read_bytes())
CANDIDATE = json.loads((ROOT / PROPOSAL).read_bytes())
CONTEXT = CANDIDATE["context_required"]


def report():
    return {"errors": [], "results": [{"filename": row["path"], "test_id": row["rule"],
        "line_number": row["line"], "col_offset": row["column"], "end_col_offset": row["end_column"],
        "line_range": row["bandit_line_range"], "code": "not authority", "issue_text": "not authority"}
        for row in CANDIDATE["occurrences"]]}


def approved_test_record():
    value = copy.deepcopy(REVIEW)
    value["approval"] = "approved"
    value["reviewers"][1]["decision"] = "approved_finite_22_context_only"
    return value


def source_copy(directory, variant):
    for name, pin in REVIEW["bindings"].items():
        raw = (ROOT / name).read_bytes()
        # Only synthetic fixtures for the seventeen explicit reviewed paths
        # construct these alternatives. The production consumer changes no byte.
        if variant == "authenticated_git_lf":
            raw = raw.replace(b"\r\n", b"\n")
            expected = pin["git_lf_sha256"]
        else:
            expected = pin["captured_main_raw_sha256"]
            lf = raw.replace(b"\r\n", b"\n")
            raw = next(value for value in (raw, lf, lf.replace(b"\n", b"\r\n"))
                       if hashlib.sha256(value).hexdigest() == expected)
        assert hashlib.sha256(raw).hexdigest() == expected
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    for name in (PROPOSAL, MATCHER):
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    return directory


@pytest.mark.parametrize("variant", ["captured_main_raw", "authenticated_git_lf"])
def test_only_two_finite_source_universes_match_with_an_explicit_test_approval(tmp_path, variant):
    approval = approved_test_record()
    assert approval["approval"] == "approved"
    assert approval["reviewers"][1] == {"role": "root", "decision": "approved_finite_22_context_only"}
    result = apply_registry(report(), source_copy(tmp_path, variant), approval,
        context=CONTEXT, bandit_version="1.9.4", today=date(2026, 10, 20))
    assert result["approved_occurrences"] == 22
    assert result["source_variant"] == variant
    assert result["historical_baseline_reapproved"] == 0
    assert result["OS_isolation_proven"] is False
    assert CANDIDATE["approval"] == "proposal_only_no_baseline_change"


@pytest.mark.parametrize("fault", ["pending", "expired", "future", "root-review", "tool", "context",
                                  "missing", "duplicate", "span", "source", "matcher", "caller",
                                  "mixed-framing", "occurrence-id", "extra-binding"])
def test_no_approval_applies_after_authority_context_multiset_or_source_changes(tmp_path, fault):
    root = source_copy(tmp_path, "captured_main_raw")
    registry = approved_test_record()
    actual = report()
    context = CONTEXT
    tool = "1.9.4"
    today = date(2026, 10, 20)
    if fault == "pending":
        registry["approval"] = "pending_root_review"
        registry["reviewers"][1]["decision"] = "pending_final_candidate_review"
    elif fault == "expired":
        today = date(2026, 11, 20)
    elif fault == "future":
        today = date(2026, 10, 19)
    elif fault == "root-review":
        registry["reviewers"][1]["decision"] = "pending_final_candidate_review"
    elif fault == "tool":
        tool = "1.9.5"
    elif fault == "context":
        context = "shared-host"
    elif fault == "missing":
        actual["results"].pop()
    elif fault == "duplicate":
        actual["results"][-1] = copy.deepcopy(actual["results"][-2])
    elif fault == "span":
        actual["results"][-1]["col_offset"] += 1
    elif fault in {"source", "matcher"}:
        target = root / (MATCHER if fault == "matcher" else "web/database/followup_policy.py")
        target.write_bytes(target.read_bytes() + b"\n# new unreviewed byte\n")
    elif fault == "caller":
        (root / "web/new_import.py").write_bytes(b"from web.database.followup_policy import _source\n")
    elif fault == "mixed-framing":
        name = next(name for name, pin in REVIEW["bindings"].items()
                    if pin["captured_main_raw_sha256"] != pin["git_lf_sha256"])
        target = root / name
        target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
    elif fault == "occurrence-id":
        registry["occurrence_ids"][0] = "unreviewed-occurrence"
    else:
        registry["bindings"]["unreviewed"] = next(iter(registry["bindings"].values()))
    with pytest.raises(ValueError):
        apply_registry(actual, root, registry, context=context, bandit_version=tool, today=today)
