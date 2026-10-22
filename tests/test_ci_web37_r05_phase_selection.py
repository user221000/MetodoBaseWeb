"""Require registry-specific original assertions separately from current runtime."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from tests.ci_web37 import run_web
from tests.ci_web37.recipes import CURRENT_RUNTIME_SELECTORS, R05_FROZEN_PHASES


def test_each_relocated_module_has_its_complete_explicit_replacement():
    assert {"--ignore=tests/test_security_r05_v5_current_peer.py",
            "--ignore=tests/test_secret_scan_finite_v6.py",
            "--ignore=tests/test_secret_scan_finite_v7.py",
            "--ignore=tests/test_security_r05_753_peer.py"} <= set(CURRENT_RUNTIME_SELECTORS)
    assert R05_FROZEN_PHASES == (("frozen-v5-peer60", 60), ("frozen-v6-author48", 48), ("frozen-v7-author15", 15))
    assert "--ignore=tests/test_current37_r05_750.py" not in CURRENT_RUNTIME_SELECTORS


def harness(monkeypatch, fault=None):
    """Synthetic metadata is only a refusal control, never a runtime result."""
    from tests.ci_web37 import git_history
    from tests.ci_web37 import r05_v7_history
    original = b"immutable literal source witness\n"
    manifest = {"phases": {phase: {"required_cases": count, "files": {
        "tests/literal.py": {"materialized_sha256": hashlib.sha256(original).hexdigest()}}}
        for phase, count in R05_FROZEN_PHASES}}
    if fault == "manifest":
        manifest["phases"][R05_FROZEN_PHASES[0][0]]["required_cases"] = 59
    monkeypatch.setattr(git_history, "load", lambda: SimpleNamespace(manifest=manifest))
    monkeypatch.setattr(r05_v7_history, "load", lambda: SimpleNamespace(manifest=manifest))
    invocations = []

    def execute(argv, source, environment, raw_path):
        phase = argv[argv.index("--phase") + 1]
        private = run_web.Path(argv[argv.index("--private") + 1])
        private.mkdir()
        count = dict(R05_FROZEN_PHASES)[phase]
        invocations.append(phase)
        first = phase == R05_FROZEN_PHASES[0][0]
        if first and fault == "child_exit":
            return 1
        literal = private / "source/tests/literal.py"
        literal.parent.mkdir(parents=True)
        literal.write_bytes(original + (b"changed" if first and fault == "source" else b""))
        row = {"accepted": True, "phase": phase, "required_cases": count,
               "passed_exact_unique_cases": count, "process_or_network_attempts": 0,
               "Git_repository_present": False, "current_runtime_claim": False}
        if first and fault in {"accepted", "phase", "required_cases", "passed_exact_unique_cases",
                               "process_or_network_attempts", "Git_repository_present", "current_runtime_claim"}:
            row[fault] = {"accepted": False, "phase": "different-phase", "required_cases": count - 1,
                          "passed_exact_unique_cases": count - 1, "process_or_network_attempts": 1,
                          "Git_repository_present": True, "current_runtime_claim": True}[fault]
        (private / "result.json").write_text(json.dumps(row), encoding="utf8")
        cases = [f'<testcase classname="synthetic.refusal.control" name="case-{i}"/>' for i in range(count)]
        if first and fault == "duplicate":
            cases[-1] = cases[0]
        skipped = first and fault == "skipped"
        if skipped:
            cases[-1] = '<testcase classname="synthetic.refusal.control" name="last"><skipped/></testcase>'
        xml = f'<testsuite tests="{count}" failures="0" errors="0" skipped="{int(skipped)}">' + "".join(cases) + "</testsuite>"
        (private / "pytest.xml").write_text(xml, encoding="utf8")
        return 0

    monkeypatch.setattr(run_web, "execute", execute)
    return invocations


def test_both_literal_phases_are_mandatory_and_never_claim_current_runtime(tmp_path, monkeypatch):
    invocations = harness(monkeypatch)
    result = run_web.r05_history_gate(tmp_path, {})
    assert invocations == [phase for phase, _ in R05_FROZEN_PHASES]
    assert result["accepted"] is True and result["passed"] == 123
    assert result["current_runtime_claim"] is False
    assert [row["passed"] for row in result["frozen_R05_phases"]] == [60, 48, 15]


@pytest.mark.parametrize("fault", ["manifest", "child_exit", "accepted", "phase", "required_cases",
    "passed_exact_unique_cases", "process_or_network_attempts", "Git_repository_present",
    "current_runtime_claim", "source", "skipped", "duplicate"])
def test_failed_changed_or_unattributable_phase_refuses_the_gate(tmp_path, monkeypatch, fault):
    invocations = harness(monkeypatch, fault)
    with pytest.raises(ValueError):
        run_web.r05_history_gate(tmp_path, {})
    assert invocations == ([] if fault == "manifest" else [R05_FROZEN_PHASES[0][0]])
