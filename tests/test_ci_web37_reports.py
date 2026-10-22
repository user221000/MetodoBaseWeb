"""Independent counterfeit controls for the current web report boundary."""
import copy
import json

import pytest

from tests.ci_web37.reports import (
    CollectionOracle,
    junit_identities,
    node_cases,
    require_exact_junit,
)


def report(body='<testcase classname="tests.module" name="test_one"/>', **counters):
    values = {"tests": 1, "errors": 0, "failures": 0, "skipped": 0, **counters}
    attrs = " ".join(f'{key}="{value}"' for key, value in values.items())
    return ('<testsuites><testsuite ' + attrs + '>' + body + '</testsuite></testsuites>').encode()


def test_actual_required_identity_is_accepted():
    assert require_exact_junit(report(), [("tests.module", "test_one")]) == 1


@pytest.mark.parametrize("raw", [
    report("", tests=0), report(skipped=1), report(errors=1), report(failures=1),
    report(tests=2), report('<testcase name="test_one"/>'),
    report('<testcase classname="tests.module" name="test_one"><skipped/></testcase>'),
    report('<testcase classname="tests.module" name="test_one"><failure/></testcase>'),
    report('<testcase classname="tests.module" name="test_one"><error/></testcase>'),
    report('<testcase classname="tests.module" name="test_one"/>' * 2, tests=2),
    b'<!DOCTYPE testsuites [<!ENTITY x "control">]>' + report(),
    b'<publication complete="true" passed="1"/>',
])
def test_omitted_or_fabricated_junit_is_rejected(raw):
    with pytest.raises(ValueError):
        junit_identities(raw)


@pytest.mark.parametrize("expected", [[], [("tests.module", "wrong")],
                                         [("tests.module", "test_one")] * 2])
def test_required_collection_cannot_shrink_or_change(expected):
    with pytest.raises(ValueError):
        require_exact_junit(report(), expected)


def frontend():
    return {"passed": 2, "total": 2, "results": [
        {"case": "first invariant", "passed": True},
        {"name": "second invariant", "passed": True}]}


def test_frontend_exact_labels_are_accepted():
    assert node_cases(frontend(), ["first invariant", "second invariant"]) == 2


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(passed=True),
    lambda value: value.update(total=1),
    lambda value: value.update(results=[]),
    lambda value: value["results"].reverse(),
    lambda value: value["results"][1].update(name="first invariant"),
    lambda value: value["results"][0].update(passed=1),
    lambda value: value["results"][0].update(name="ambiguous"),
    lambda value: value["results"][0].pop("passed"),
])
def test_frontend_counter_only_success_or_weakened_cases_are_rejected(mutation):
    value = copy.deepcopy(frontend())
    mutation(value)
    with pytest.raises(ValueError):
        node_cases(value, ["first invariant", "second invariant"])


def test_collection_oracle_preserves_class_and_parameter_identity(tmp_path):
    from types import SimpleNamespace
    output = tmp_path / "oracle.json"
    plugin = CollectionOracle(output)
    session = SimpleNamespace(items=[SimpleNamespace(nodeid=
        "tests/test_module.py::TestBoundary::test_case[factory-a]", name="test_case[factory-a]")])
    plugin.pytest_collection_finish(session)
    plugin.pytest_sessionfinish(session, 0)
    assert json.loads(output.read_bytes()) == [["tests.test_module.TestBoundary", "test_case[factory-a]"]]


def test_failed_collection_never_produces_a_success_oracle(tmp_path):
    output = tmp_path / "oracle.json"
    CollectionOracle(output).pytest_sessionfinish(None, 2)
    assert not output.exists()


def test_parameter_slashes_and_double_colons_are_distinct_required_criteria(tmp_path):
    from types import SimpleNamespace
    names = ["test_path[dir/alias]", "test_path[dir\\alias]", "test_path[file::memory:]"]
    output = tmp_path / "oracle.json"
    plugin = CollectionOracle(output)
    session = SimpleNamespace(items=[SimpleNamespace(nodeid="tests/test_path.py::" + name, name=name)
                                     for name in names])
    plugin.pytest_collection_finish(session)
    plugin.pytest_sessionfinish(session, 0)
    assert json.loads(output.read_bytes()) == [["tests.test_path", name] for name in names]


def never_execute_migration(*args):
    raise AssertionError("Fixture review executed a migration")


def historical_fixture():
    run_migration("unused", "db_bootstrap.py", "--revision", "20261019_google_subjects")


run_migration = never_execute_migration


def test_selected_fixture_review_is_inert_and_preserves_old_target():
    from tests.ci_web37.fixture_review import fixture_contract
    actual = fixture_contract(historical_fixture)
    assert actual["requires_review"] is True
    assert actual["explicit_migration_targets"] == ["20261019_google_subjects"]


def test_unavailable_fixture_source_is_never_assumed_current():
    from tests.ci_web37.fixture_review import fixture_contract
    actual = fixture_contract(len)
    assert actual["requires_review"] is True and actual["source_unavailable"] is True
