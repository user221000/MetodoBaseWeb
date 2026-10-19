"""Protect the independently reproduced empty-checker and fake-runner bypasses."""
from pathlib import Path

import pytest

from tests import verify_member_links_ci as guard


def test_reviewed_executable_helpers_match_independent_anchors():
    guard.authenticate_current_gates()


@pytest.mark.parametrize('target,body', [
    ('tests/check_member_link_reports.py', 'REPORTS = {}\n'),
    ('tests/run_reviewed_ci28.py', 'print("historical_exit=0 without executing history")\n'),
])
def test_mutated_executable_helper_is_rejected_before_execution(tmp_path, monkeypatch, target, body):
    for name in guard.PINNED_CURRENT_GATES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((guard.ROOT / name).read_bytes())
    (tmp_path / target).write_text(body, encoding='utf8')
    monkeypatch.setattr(guard, 'ROOT', tmp_path)
    with pytest.raises(AssertionError, match=target):
        guard.authenticate_current_gates()


def test_runtime_checker_specification_cannot_erase_probe_generation(tmp_path, monkeypatch):
    from tests import check_member_link_reports
    monkeypatch.setattr(check_member_link_reports, 'REPORTS', {})
    with pytest.raises(AssertionError):
        guard.report_canaries(Path(tmp_path))
