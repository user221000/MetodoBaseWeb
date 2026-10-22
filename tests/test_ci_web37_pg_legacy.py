"""Collection-only provenance and seed conservation, without SQL or fixtures."""
import ast
import importlib
from pathlib import Path

import pytest

from tests.ci_web37.pg_legacy import export_group, specification

ROOT = Path(__file__).resolve().parents[1]
GROUPS = tuple(specification()["groups"])


@pytest.mark.parametrize("group", GROUPS)
def test_original_domain_assertion_objects_and_parameters_have_an_explicit_current_fixture(group):
    entry = specification()["groups"][group]
    original = importlib.import_module(entry["module"])
    companion = export_group(group)
    names = {row[1].split("[", 1)[0] for row in entry["original_cases"]}
    assert names == entry["test_objects"].keys()
    assert all(companion[name] is getattr(original, name) for name in names)
    assert entry["fixture_bindings"]
    assert entry["expected_pool"] == (6 if group == "r24-race" else 1)


def test_rls_seed_keeps_the_complete_original_fixture_body_and_omits_its_force_owner():
    old = ast.parse((ROOT / "tests/integration_postgres.py").read_text(encoding="utf8"))
    owner = next(row for row in old.body if isinstance(row, ast.FunctionDef) and row.name == "owned_postgres_database")
    original = next(row for row in ast.walk(owner) if isinstance(row, ast.With)
                    and ast.unparse(row.items[0].context_expr) == "Session(admin)")
    new = ast.parse((ROOT / "tests/ci_web37/pg_rls_seed.py").read_text(encoding="utf8"))
    seed = next(row for row in new.body if isinstance(row, ast.FunctionDef))
    assert len(seed.body) == 1
    assert ast.dump(seed.body[0], include_attributes=False) == ast.dump(original, include_attributes=False)
    assert not any(isinstance(row, ast.Name) and row.id in {"control", "subprocess", "create_engine"}
                   for row in ast.walk(new))
