"""Historical web scope must not launch Desktop product or offline licensing."""
from pathlib import Path

import pytest

from tests.ci_web37.run_historical31_web import command
from tests.ci_web37.scope import require_web_selection


def test_historical31_both_commands_keep_web_and_drop_all_desktop_modules():
    source = Path("/authentic31")
    for mode in ("serial", "parallel"):
        argv = command(source, mode)
        assert str(source / "tests/run_isolated.py") in argv
        assert "tests" in argv
        assert "--ignore=tests/test_login_desktop.py" in argv
        assert "--ignore-glob=tests/test_desktop*.py" in argv
        assert "--ignore=tests/test_license_offline_security.py" in argv
        assert argv[argv.index("-p") + 1] == "ci_web37.scope"
        assert "--web37-current-fixtures" not in argv
        if mode == "serial":
            assert {"--cov", "--cov-report=json", "--cov-report=xml", "--junitxml=pytest-web.xml"} <= set(argv)
        else:
            assert "--shuffle-seed=20261018" in argv
            assert argv[argv.index("-n") + 1] == "2"
            assert "--junitxml=pytest-web-shuffle.xml" in argv


def test_external_guard_rejects_desktop_before_fixtures_but_keeps_shared_web():
    for name in ("test_login_desktop.py", "test_desktop_entrypoints.py", "test_desktop_export_feedback.py",
                 "test_desktop_policy.py", "test_license_offline_security.py"):
        with pytest.raises(ValueError, match="outside the authorized web scope"):
            require_web_selection(["tests/" + name + "::inert_case_identity"])
    require_web_selection(["tests/test_catalog.py::test_shared_free10", "tests/test_layout.py::test_desktop_web_viewport"])


def test_historical_scope_does_not_accept_an_invented_execution_mode():
    with pytest.raises(ValueError, match="original serial or parallel"):
        command(Path("/authentic31"), "desktop")
