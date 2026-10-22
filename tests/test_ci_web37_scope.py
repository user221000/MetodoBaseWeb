"""Protect the user's web-only boundary without dropping shared web criteria."""
import pytest

from tests.ci_web37.scope import require_web_selection


@pytest.mark.parametrize("module", [
    "test_login_desktop", "test_desktop_entrypoints", "test_desktop_packaging",
    "test_desktop_packaging_ops10", "test_desktop_provenance", "test_desktop_packaging_review",
    "test_license_offline_security",
])
def test_desktop_product_nodes_are_rejected_before_execution(module):
    with pytest.raises(ValueError, match="authorized web scope"):
        require_web_selection(["tests/" + module + ".py::test_canary"])


def test_shared_free_catalog_and_desktop_web_viewport_are_retained():
    require_web_selection([
        "tests/test_catalog_contract.py::test_catalog_copies_keep_personal_monthly_limits_separate_from_gym_daily_limits",
        "tests/test_frontend_report_guard.py::test_report[desktop]",
    ])


def test_path_separator_alias_cannot_reintroduce_desktop_product_validation():
    with pytest.raises(ValueError, match="authorized web scope"):
        require_web_selection([r"tests\test_license_offline_security.py::test_canary"])
