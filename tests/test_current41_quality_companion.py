"""Canaries for the collection-only authenticated quality41 companion.

The current41 collector compiles its registered historical quality source at
this logical path, retaining all56 original test IDs. Importing this file runs
only these additional canaries; it does not collect a duplicate set of56.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_image57 import authority
from tests.ci_web39 import quality, verify_quality
from tests.ci_web41 import collection, source_companion

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "tests/test_quality_web39.py"
COMPANION = "tests/test_current41_quality_companion.py"
RETIRED = "web/main_web.py:B324:6a3630fbfe01c7e5594bfc39ad6ceed9a089da8a2677f9c65f7ffa42b270632e"


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    """These are source/admission checks with no application SQL."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def clone():
    original = importlib.import_module("tests.test_quality_web39")
    return original, collection.clone_source(original, COMPANION)[0]


def unwrap(fixture):
    return fixture.__wrapped__


@pytest.fixture(scope="module")
def control(tmp_path_factory):
    target = authority.private_directory(tmp_path_factory.mktemp("quality41-canary") / "source", ROOT)
    verify_quality.copy_source(ROOT, target)
    proposal = json.loads((target / quality.PROPOSAL).read_bytes())
    for name, pin in proposal["bindings"].items():
        path = target / name
        raw = path.read_bytes()
        selected = next(value for value in (raw, raw.replace(b"\r\n", b"\n"))
                        if hashlib.sha256(value).hexdigest() == pin["authenticated_git_objects_sha256"])
        path.write_bytes(selected)
    _, current = clone()
    # As in the retained controls, test decisions exist only in the private copy.
    (target / quality.APPROVAL).write_text(json.dumps(current.approved_test_record(target)), encoding="utf8")
    return target


def test_only_six_explicit_collection_routes_and_all_original_names_survive():
    original, current = clone()
    assert len(collection.SOURCES) == 6 and collection.SOURCES[ORIGINAL] == COMPANION
    assert {name for name in vars(original) if name.startswith(("test_", "Test"))} == {
        name for name in vars(current) if name.startswith(("test_", "Test"))}
    assert original.TODAY == date(2026, 10, 29) and current.TODAY == date(2026, 11, 2)
    assert current.quality is original.quality and current.bandit_review is original.bandit_review
    assert current.quality.classify is original.quality.classify


@pytest.mark.parametrize("fixture_name,relative", [
    ("report", "tests/ci_web39/fixtures/bandit32-current095-fixture.json"),
    ("report311", "tests/ci_web39/fixtures/bandit32-python311-d8df-fixture.json"),
])
def test_both_complete_authenticated_fixtures_remove_exactly_one_named_record(fixture_name, relative):
    _, current = clone()
    raw = (ROOT / relative).read_bytes()
    parent = json.loads(raw)["report"]
    child = unwrap(getattr(current, fixture_name))()
    assert len(parent["results"]) == 32 and len(child["results"]) == 31
    assert sum(quality.fingerprint(row) == RETIRED for row in parent["results"]) == 1
    assert child == dict(parent, results=[row for row in parent["results"] if quality.fingerprint(row) != RETIRED])
    assert (ROOT / relative).read_bytes() == raw


@pytest.mark.parametrize("fixture_name", ["report", "report311"])
@pytest.mark.parametrize("fault", ["missing_retired", "duplicate_retired"])
def test_retirement_requires_exactly_one_record_even_after_whole_fixture_authentication(fixture_name, fault):
    original, current = clone()
    relative = "tests/ci_web39/fixtures/" + ("bandit32-current095-fixture.json" if fixture_name == "report" else "bandit32-python311-d8df-fixture.json")
    value = json.loads((ROOT / relative).read_bytes())
    index = next(i for i, row in enumerate(value["report"]["results"]) if quality.fingerprint(row) == RETIRED)
    if fault == "missing_retired":
        value["report"]["results"][index] = deepcopy(value["report"]["results"][(index + 1) % 32])
    else:
        value["report"]["results"][(index + 1) % 32] = deepcopy(value["report"]["results"][index])
    original_context = original.context
    # Only this disposable clone gets the inert parser; the original module,
    # parser, matcher and fixture bytes are never changed.
    current.context = SimpleNamespace(json_object=lambda raw: value)
    with pytest.raises(AssertionError):
        unwrap(getattr(current, fixture_name))()
    assert original.context is original_context


def test_current31_is_admitted_but_restored_retired_occurrence_and_old_date_reject(control):
    _, current = clone()
    report = unwrap(current.report)()
    accepted = current.classify(report, control)
    assert accepted["baseline_occurrences"] == 5 and accepted["new_occurrences"] == 26
    assert accepted["finite_current_review"]["historical_baseline_reapproved"] == 0
    with pytest.raises(ValueError):
        quality.classify(report, control, bandit_version="1.9.4", today=date(2026, 10, 29))
    parent = json.loads((ROOT / "tests/ci_web39/fixtures/bandit32-current095-fixture.json").read_bytes())["report"]
    with pytest.raises(ValueError):
        current.classify(parent, control)


@pytest.mark.parametrize("fault", ["missing_current", "duplicate_current", "changed_span"])
def test_current31_still_rejects_an_unreviewed_finding_multiset(control, fault):
    _, current = clone()
    report = deepcopy(unwrap(current.report)())
    index = next(i for i, row in enumerate(report["results"])
                 if row["filename"].replace("\\", "/").endswith("web/database/product_analytics_policy_v2.py"))
    if fault == "missing_current":
        report["results"].pop(index)
    elif fault == "duplicate_current":
        report["results"].append(deepcopy(report["results"][index]))
    else:
        report["results"][index]["col_offset"] += 1
    with pytest.raises(ValueError):
        current.classify(report, control)


def test_quality_parent_and_compiled_identity_and_its_assertion_mutations_are_finite():
    entry = source_companion.specification()["entries"][COMPANION]
    raw = (ROOT / ORIGINAL).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == entry["original_sha256_LF"]
    assert quality.git_recipe.object_id("blob", raw) == entry["original_git_blob"]
    assert entry["original_git_commit"] == "ba5fa52627e8f480f6bd5610ec22f31b64ed7fa5"
    changed = deepcopy(entry)
    changed["literal_edits"][0]["count"] = True
    with pytest.raises(ValueError):
        source_companion.rewrite(raw, changed)
    changed = deepcopy(entry)
    changed["current_sha256_LF"] = "0" * 64
    with pytest.raises(ValueError):
        source_companion.rewrite(raw, changed)
    from tests.ci_web41 import pg_contract
    assert {ORIGINAL, COMPANION} <= set(pg_contract.BOUND)
