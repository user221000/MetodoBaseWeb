"""Counter-only output cannot replace the original source-bound Node criteria."""
import copy
import json
from pathlib import Path

import pytest

from tests.ci_web37 import node_current

ROOT = Path(__file__).resolve().parents[1]
MAPPING = json.loads((ROOT / "tests/ci_web37/node-routines-onboarding.json").read_bytes())


def entry(name):
    return next(row for row in MAPPING["commands"] if row["script"].endswith("/" + name))


def report(row):
    return {"scope": row["scope"], "passed": len(row["expected_cases"]), "total": len(row["expected_cases"]),
            "results": [{"case": label, "passed": True} for label in row["expected_cases"]]}


def test_additional_original_inventory_has_eight_programs_and_94_separate_criteria():
    rows = node_current.require_additional_sources(ROOT, MAPPING)
    assert len(rows) == 8
    assert sum(len(row["expected_cases"]) for row in rows) == 94
    assert all("browser_session31.cjs" != row["script"].split("/")[-1] for row in rows)


def test_missing_or_changed_transitive_input_is_rejected_without_execution():
    value = copy.deepcopy(MAPPING)
    value["input_files"]["core/routine_catalog.py"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="transitive input"):
        node_current.require_additional_sources(ROOT, value)


def test_duplicate_missing_reordered_failed_or_untyped_rows_are_rejected():
    row = entry("security_routines_transport_peer.cjs")
    original = report(row)
    assert node_current.validate_additional(json.dumps(original).encode(), row, ROOT) == 9
    for fault in ("duplicate", "missing", "order", "failed", "untyped", "scope"):
        value = copy.deepcopy(original)
        if fault == "duplicate":
            value["results"][1] = value["results"][0]
        elif fault == "missing":
            value["results"].pop()
        elif fault == "order":
            value["results"].reverse()
        elif fault == "failed":
            value["results"][0]["passed"] = False
        elif fault == "untyped":
            value["passed"] = "9"
        else:
            value["scope"] = "native browser"
        with pytest.raises(ValueError):
            node_current.validate_additional(json.dumps(value).encode(), row, ROOT)


def test_routine_public_lines_require_exact_names_and_typed_footer():
    row = entry("routines_panel.cjs")
    lines = ["PASS " + name for name in row["expected_cases"]]
    footer = {"passed": 13, "total": 13, "scope": row["scope"]}
    original = "\n".join([*lines, json.dumps(footer)]) + "\n"
    assert node_current.validate_additional(original.encode(), row, ROOT) == 13
    for value in (original.replace("PASS ", "FAIL ", 1), original.replace('"passed": 13', '"passed": 13.0'),
                  original + "diagnostic\n", "\n".join([*lines[::-1], json.dumps(footer)])):
        with pytest.raises((ValueError, TypeError)):
            node_current.validate_additional(value.encode(), row, ROOT)


def test_access_pair_requires_exact_counters_scope_and_original_assertion_regions(tmp_path):
    row = entry("routines_access_fences.cjs")
    original = {"passed": 2, "total": 2, "scope": row["scope"]}
    assert node_current.validate_additional(json.dumps(original).encode(), row, ROOT) == 2
    for count in (True, 2.0, "2", 0, 1, 3):
        with pytest.raises(ValueError):
            node_current.validate_additional(json.dumps({**original, "passed": count}).encode(), row, ROOT)
    for value in ({**original, "scope": "other"}, {**original, "diagnostic": "unexpected"}):
        with pytest.raises(ValueError):
            node_current.validate_additional(json.dumps(value).encode(), row, ROOT)
    target = tmp_path / row["script"]
    target.parent.mkdir(parents=True)
    source = (ROOT / row["script"]).read_bytes().replace(b"\r\n", b"\n")
    target.write_bytes(source.replace(b"assert.equal(bodies, 0);", b"assert.equal(bodies, 1);"))
    assert target.read_bytes() != source
    with pytest.raises(ValueError, match="assertion body"):
        node_current.validate_additional(json.dumps(original).encode(), row, tmp_path)
