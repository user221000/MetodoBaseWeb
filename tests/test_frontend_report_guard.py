"""A malformed frontend artifact must never turn a failed driver into acceptance."""

import copy
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "frontend_report_guard", Path(__file__).resolve().parents[1] / "scripts/check_frontend_report.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


@pytest.mark.parametrize("kind,report", [
    ("strings", {"checks": ["One", "Two"], "pageErrors": []}),
    ("named", {"checks": [{"name": "One"}, {"name": "Two"}], "pageErrors": [],
               "screens": ["mobile", "desktop"]}),
    ("counts", {"total": 2, "passed": 2,
                "results": [{"case": "One", "passed": True}, {"case": "Two", "passed": True}]}),
])
def test_real_report_shapes_and_truncated_or_repeated_acceptance(kind, report):
    screens = 2 if kind == "named" else 0
    guard.validate(report, kind, 2, screens)
    with pytest.raises(ValueError):
        guard.validate(report, kind, 3, screens)
    invalid = copy.deepcopy(report)
    rows = invalid["results" if kind == "counts" else "checks"]
    rows[1] = rows[0]
    with pytest.raises(ValueError):
        guard.validate(invalid, kind, 2, screens)


@pytest.mark.parametrize("report", [None, [], {}, {"checks": [], "pageErrors": []},
    {"checks": ["One"], "pageErrors": None}, {"checks": ["One"], "pageErrors": ["error"]},
    {"checks": [False], "pageErrors": []}, {"checks": [""], "pageErrors": []},
    {"checks": [{"name": "One"}], "pageErrors": []}])
def test_string_browser_guard_rejects_missing_or_untyped_results(report):
    with pytest.raises(ValueError):
        guard.validate(report, "strings", 1)


@pytest.mark.parametrize("changes", [
    {"total": True}, {"passed": True}, {"total": 1.0}, {"passed": 0},
    {"total": 2}, {"results": []}, {"results": [{"case": "One", "passed": 1}]},
    {"results": [{"case": "One", "passed": False}]}, {"results": [{"passed": True}]},
])
def test_contract_guard_rejects_inflated_counts_and_non_boolean_success(changes):
    report = {"total": 1, "passed": 1, "results": [{"case": "One", "passed": True}]}
    report.update(changes)
    with pytest.raises(ValueError):
        guard.validate(report, "counts", 1)


@pytest.mark.parametrize("checks,screens", [
    (["One"], ["mobile"]), ([{}], ["mobile"]), ([{"name": ""}], ["mobile"]),
    ([{"name": "One", "passed": False}], ["mobile"]),
    ([{"name": "One"}], []), ([{"name": "One"}], [False]),
])
def test_named_browser_guard_requires_success_names_and_screens(checks, screens):
    with pytest.raises(ValueError):
        guard.validate({"checks": checks, "screens": screens, "pageErrors": []}, "named", 1, 1)
