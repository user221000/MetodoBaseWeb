"""Keep the old unexpired control and require actual V7 expiry criteria."""
import pytest

from tests.ci_web37.recipes import (
    CURRENT_RUNTIME_SELECTORS,
    NATIVE_EXPIRED_ORIGINAL,
    NATIVE_EXPIRY_REQUIRED,
    require_native_expiry_replacement,
)


def test_only_the_original_RED_node_is_replaced_by_the_complete_current_criteria():
    assert "--deselect=tests/test_security_native35_original_expiry_canary.py::test_original_expired_sql_ack_must_refuse_before_first_fixture_admission" in CURRENT_RUNTIME_SELECTORS
    assert "--ignore=tests/test_security_native35_original_expiry_canary.py" not in CURRENT_RUNTIME_SELECTORS
    require_native_expiry_replacement([*NATIVE_EXPIRY_REQUIRED, ("tests.other", "test_shared_catalog")])


@pytest.mark.parametrize("fault", ["original-control", "before-fixture", "phase", "old-RED", "duplicate", "renamed"])
def test_missing_changed_or_historical_RED_criterion_refuses_the_current_gate(fault):
    rows = list(NATIVE_EXPIRY_REQUIRED)
    if fault in {"original-control", "before-fixture", "phase"}:
        rows.pop({"original-control": 0, "before-fixture": 1, "phase": 2}[fault])
    elif fault == "old-RED":
        rows.append(NATIVE_EXPIRED_ORIGINAL)
    elif fault == "duplicate":
        rows.append(rows[1])
    else:
        rows[1] = (rows[1][0], rows[1][1].replace("[True]", "[False]"))
    with pytest.raises(ValueError, match="historical native expiry refusal"):
        require_native_expiry_replacement(rows)
