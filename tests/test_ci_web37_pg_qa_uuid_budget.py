"""Actual QA37 opens its module database and one damaged predecessor database.

No database is opened by these controls. The original source and assertions
remain selected; the finite lease budget describes both original owners.
"""
import ast
from pathlib import Path

import pytest

from tests.ci_web37 import pg_lease
from tests.ci_web37.pg_plan import phases

ROOT = Path(__file__).resolve().parents[1]
COMPLEMENT = ("independent-qa", "restore", "security-notifications", "onboarding-author",
              "onboarding-security", "qa26-primary", "qa26-registration")


def test_two_original_QA_databases_are_the_exact_success_budget():
    assert pg_lease.phase_budget("independent-qa", 2, succeeded=True) == 2


@pytest.mark.parametrize("value", [-1, 0, 1, 3, True, 2.0, "2"])
def test_missing_excess_or_untyped_success_is_refused(value):
    with pytest.raises(ValueError, match="UUID budget"):
        pg_lease.phase_budget("independent-qa", value, succeeded=True)


def test_partial_failed_child_keeps_normal_closure_without_claiming_success():
    assert pg_lease.phase_budget("independent-qa", 0, succeeded=False) == 2
    assert pg_lease.phase_budget("independent-qa", 1, succeeded=False) == 2


def test_the_two_original_owner_scopes_really_overlap_in_this_collection():
    source = ast.parse((ROOT / "tests/account37_qa_pg_fixtures.py").read_text(encoding="utf8"))
    functions = {node.name: node for node in source.body if isinstance(node, ast.FunctionDef)}
    module = functions["peer37_database"]
    assert ast.unparse(module.decorator_list[0]) == "pytest.fixture(scope='module')"
    assert sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == "owned_database" for node in ast.walk(module)) == 1
    auto = functions["pool_released_after_case"]
    assert ast.unparse(auto.decorator_list[0]) == "pytest.fixture(autouse=True)"
    assert [node.arg for node in auto.args.args] == ["peer37_database"]
    controls = ast.parse((ROOT / "tests/account37_qa_pg_controls.py").read_text(encoding="utf8"))
    drift = next(node for node in controls.body if isinstance(node, ast.FunctionDef)
                 and node.name == "test_predecessor_type_drift_is_rejected_before_contact_ddl_and_preserves_rows")
    assert sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == "owned_database" for node in ast.walk(drift)) == 1
    assert "run_migration(url, 'db_bootstrap.py', '--revision', '20261020_notifications')" in ast.unparse(drift)
    companion = ast.parse((ROOT / "tests/integration_security_account37_peer.py").read_text(encoding="utf8"))
    assert any(isinstance(node, ast.ImportFrom) and node.module == "tests.account37_qa_pg_fixtures"
               and {alias.name for alias in node.names} >= {"peer37_database", "pool_released_after_case"}
               for node in companion.body)
    assert any(isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
               and target.id == drift.name for target in node.targets)
               and ast.unparse(node.value) == "own." + drift.name for node in companion.body)


def test_only_QA_and_restore_require_two_simultaneous_UUIDs():
    rows = pg_lease.budgets()
    assert sum(row["UUIDs"] for row in rows) == 69
    assert {row["group"] for row in rows if row["concurrent_UUIDs"] == 2} == {"independent-qa", "restore"}
    assert all(row["concurrent_UUIDs"] == 1 for row in rows if row["group"] not in {"independent-qa", "restore"})


def test_the_explicit_complement_keeps_every_original_identity_once():
    rows = phases()
    accepted = [tuple(identity) for row in rows if row["key"] not in COMPLEMENT for identity in row["expected"]]
    remaining = [tuple(identity) for row in rows if row["key"] in COMPLEMENT for identity in row["expected"]]
    assert len(accepted) == len(set(accepted)) == 323
    assert len(remaining) == len(set(remaining)) == 106
    assert set(accepted).isdisjoint(remaining)
    assert set(accepted) | set(remaining) == {tuple(identity) for row in rows for identity in row["expected"]}
    selected = [row for row in pg_lease.budgets() if row["group"] in COMPLEMENT]
    assert [row["group"] for row in selected] == list(COMPLEMENT)
    assert sum(row["UUIDs"] for row in selected) == 9
    assert max(row["concurrent_UUIDs"] for row in selected) == 2
