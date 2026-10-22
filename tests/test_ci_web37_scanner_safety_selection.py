"""The QA33 diagnostic transport must preserve all eleven original cases."""
import pytest

from tests.ci_web37.recipes import (
    CURRENT_RUNTIME_SELECTORS,
    SCANNER_SAFETY_CASES,
    SCANNER_SAFETY_COMPANION,
    SCANNER_SAFETY_ORIGINAL,
    require_scanner_safety_companion,
)


def identities():
    return [[SCANNER_SAFETY_COMPANION, name] for name in SCANNER_SAFETY_CASES]


def test_all_original_safety_criteria_have_exact_current_companions():
    assert "--ignore=tests/test_secret_scan_safety.py" in CURRENT_RUNTIME_SELECTORS
    assert "--ignore=tests/test_current_scanner_completion_safety.py" not in CURRENT_RUNTIME_SELECTORS
    require_scanner_safety_companion([*identities(), ["tests.other_web", "test_shared_catalog"]])


@pytest.mark.parametrize("fault", ["missing", "duplicate", "original-module", "renamed-case", "parameter-byte", "empty"])
def test_missing_duplicated_or_changed_original_criterion_refuses_before_runtime(fault):
    rows = identities()
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = rows[0]
    elif fault == "original-module":
        rows[0][0] = SCANNER_SAFETY_ORIGINAL
    elif fault == "renamed-case":
        rows[0][1] += "_different"
    elif fault == "parameter-byte":
        rows[5][1] = rows[5][1].replace("\\", "/")
    else:
        rows = []
    with pytest.raises(ValueError, match="eleven original scanner safety"):
        require_scanner_safety_companion(rows)
