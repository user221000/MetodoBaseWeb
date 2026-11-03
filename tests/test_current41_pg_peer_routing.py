"""No SQL: original seven PG criteria, exact twelve IDs and owned fixture routing."""
import ast
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.sql.dml import Delete

from scripts.scan_secrets import _private_evidence
from tests import integration_payment41_qa_postgres as campaign
from tests import test_stripe_postgres_authority_peer as original
from tests import test_stripe_postgres_refund_peer as refunds
from tests.ci_web38.reports import require_exact_junit
from tests.ci_web41 import payments_contract as contract

ORIGINAL_FIVE = {
    "test_partial_full_replay_and_other_tenant_quota": "ebc35f12492610ae8eef2d8140c1b295851b1b8cedf9fb0af6493f3b1342a10c",
    "test_old_partial_and_full_keep_new_paid_renewal": "287dedab44ad8bee44313ae0af3743bcc4093906974ad55622e8f545a66a000b",
    "test_partial_never_extends_same_paid_invoice_or_resets_usage": "76bc53db549d49c4d7c21ca36a76100af8f8d3d47fa4ac9038271b5cff4dfce3",
    "test_concurrent_signed_refund_has_two_backends_and_one_cumulative_fact": "49d68e8f74568e7baa02f7527f578aa2c5a52a19668abbb7f886046f4c1d28d9",
    "test_actual_personal_team_history_is_own_and_rls_protected": "6b8ba2d067b5a8cb77570ef557427f8dc34cef21d4fad49ad805bc4010837808",
}
ORIGINAL_PEERS = {
    "tests/test_stripe_postgres_authority_peer.py": "b0cb1ffdfc12b629c6e90a2af4bd448e11a0a1dbaa96b382d746247c244d769b",
    "tests/test_stripe_postgres_refund_peer.py": "46ebf69e9f11293c9cf6cd4235aa82ba67e24ffe184bbf82870ed38672660460",
}


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def function_nodes(path):
    return {n.name: n for n in ast.parse(path.read_bytes()).body if isinstance(n, ast.FunctionDef)}


def test_all_five_current_bodies_and_all_original_pg_bytes_are_retained():
    functions = function_nodes(contract.ROOT / contract.MODULE)
    for name, digest in ORIGINAL_FIVE.items():
        assert hashlib.sha256(ast.dump(functions[name], include_attributes=False).encode()).hexdigest() == digest
    for name, digest in ORIGINAL_PEERS.items():
        assert hashlib.sha256((contract.ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest
    assert set(ORIGINAL_FIVE) == set(contract.CURRENT_CASES)


def test_original_callable_identity_decorators_and_three_surfaces_are_not_cloned_or_rewritten():
    for name in ("test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota",
                 "test_pg_concurrent_same_invoice_has_one_ledger_and_retryable_inbox_collision"):
        assert getattr(campaign, name) is getattr(original, name)
    name = "test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota"
    assert getattr(campaign, name) is getattr(refunds, name)
    assert campaign.pg_invoice is original.pg_invoice
    assert original.SURFACES == [("web", "/api/billing/webhook"), ("api", "/api/billing/webhook"),
                                 ("api", "/api/pagos/stripe/webhook")]
    for function in (campaign.test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota,
                     campaign.test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota):
        marks = [mark for mark in function.pytestmark if mark.name == "parametrize"]
        assert len(marks) == 1 and marks[0].args == ("surface", original.SURFACES)
    adapter = function_nodes(contract.ROOT / contract.MODULE)["migration_database"]
    assert len(adapter.decorator_list) == 1
    assert ast.unparse(adapter.decorator_list[0]) == "pytest.fixture"


def test_owned_oid_role_normal_closure_and_two_backend_oracles_remain_original():
    node = function_nodes(contract.ROOT / "tests/ci_web41/payments_fixtures.py")["payments41_database"]
    assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == "59d5ddc0eccff2513b3a53f7ed05d1a6ecb2274c7ccddd29b78a1086c9e018f1"
    assert contract.PLAN == {"cases": 12, "UUIDs": 1, "concurrent_UUIDs": 1, "application_pool": 2,
        "application_workers": 2, "max_overflow": 0, "database_admin_pool": 1,
        "control_observer_connections": 1, "historical_core_restore_budgets_unchanged": True}
    adapter = function_nodes(contract.ROOT / contract.MODULE)["migration_database"]
    assert [arg.arg for arg in adapter.args.args] == ["payments41_database", "monkeypatch"]
    assert not any(isinstance(n, ast.Name) and n.id == "run_migration" for n in ast.walk(adapter))
    assert not any(isinstance(n, ast.Constant) and isinstance(n.value, str) and
                   ("CREATE DATABASE" in n.value or "DROP DATABASE" in n.value or "pg_terminate_backend" in n.value)
                   for n in ast.walk(adapter))
    assert contract.SCOPE == "payments41-pg-twelve-criteria-one-uuid-two-backends-v2"
    assert set(ORIGINAL_PEERS) <= set(contract.BOUND)


def test_ack_unit_context_never_simulates_actions_workspace_or_uid():
    functions = function_nodes(contract.ROOT / "tests/test_current41_payments_contract.py")
    context = functions["ack_environment"]
    calls = [node for node in ast.walk(context) if isinstance(node, ast.Call)]
    setters = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "setenv"]
    assert len(setters) == 1 and isinstance(setters[0].args[0], ast.Name)
    loop = next(node for node in ast.walk(context) if isinstance(node, ast.For))
    assert ast.literal_eval(loop.iter) == ("TEMP", "TMP", "TMPDIR", "RUNNER_TEMP")
    assert not any(isinstance(node.func, ast.Attribute) and node.func.attr == "setattr" for node in calls)
    body = ast.unparse(context)
    assert "os.environ.get('GITHUB_ACTIONS') != 'true'" in body
    assert "private_workspace()" in body and "geteuid" not in body


def test_collection_selects_exact_twelve_and_the_owned_fixtures_without_running_sql(tmp_path):
    private = _private_evidence(tmp_path / "collection-private")
    identities, fixtures = private / "identities.json", private / "fixtures.json"
    command = [sys.executable, "-B", "-X", "utf8", "tests/ci_web38/collect.py", "--output", str(identities),
               "--fixture-output", str(fixtures), contract.MODULE,
               "-p", "tests.ci_web41.payments_fixtures", "--basetemp=" + str(private / "data")]
    with (private / "collection.private.log").open("xb") as log:
        result = subprocess.run(command, cwd=contract.ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    assert result.returncode == 0
    expected = {(contract.MODULE.removesuffix(".py").replace("/", "."), name) for name in contract.CASES}
    rows = [tuple(row) for row in json.loads(identities.read_bytes())]
    assert len(rows) == len(expected) == 12 and set(rows) == expected
    bindings = json.loads(fixtures.read_bytes())["bindings"]
    assert len(bindings) == 12
    for row in bindings:
        assert row["fixtures"]["payments41_database"]["module"] == "tests.ci_web41.payments_fixtures"
        if row["nodeid"].split("::", 1)[1] in contract.PEER_CASES:
            assert row["fixtures"]["migration_database"]["module"] == "tests.integration_payment41_qa_postgres"
            assert row["fixtures"]["pg_invoice"]["module"] == "tests.test_stripe_postgres_authority_peer"


def fixture_urls():
    name = "metodobase_test_payments41_" + "a" * 32
    url = make_url("postgresql+psycopg2://metodobase_test_owner@127.0.0.1:55483/" + name)
    admin = SimpleNamespace(url=url, dialect=SimpleNamespace(name="postgresql"), pool=SimpleNamespace(checkedout=lambda: 0))
    app = SimpleNamespace(url=url.set(username="metodobase_test_app"), dialect=SimpleNamespace(name="postgresql"), pool=SimpleNamespace(checkedout=lambda: 0))
    return SimpleNamespace(name=name, admin=admin, app=app)


@pytest.mark.parametrize("fault", ["sqlite", "foreign-name", "wrong-database", "wrong-host", "wrong-port", "remote-host", "non-test-role", "connection-override"])
def test_adapter_rejects_unowned_or_arbitrary_urls_before_any_row_delete(fault):
    fixture = fixture_urls()
    if fault == "sqlite":
        fixture.admin.dialect.name = "sqlite"
    elif fault == "foreign-name":
        fixture.name = "unowned"
    elif fault == "wrong-database":
        fixture.admin.url = fixture.admin.url.set(database="metodobase_test_foreign")
    elif fault == "wrong-host":
        fixture.app.url = fixture.app.url.set(host="localhost")
    elif fault == "wrong-port":
        fixture.app.url = fixture.app.url.set(port=55484)
    elif fault == "remote-host":
        fixture.admin.url = fixture.admin.url.set(host="example.invalid")
        fixture.app.url = fixture.app.url.set(host="example.invalid")
    elif fault == "non-test-role":
        fixture.admin.url = fixture.admin.url.set(username="other_owner")
    else:
        fixture.app.url = fixture.app.url.set(query={"host": "example.invalid"})
    with pytest.raises(ValueError):
        campaign._owned_peer_urls(fixture)


def test_adapter_uses_only_owned_engine_deletes_and_restores_no_legacy_database(monkeypatch):
    from web.database.models import Base
    fixture, operations = fixture_urls(), []
    fixture.app.dispose = lambda: operations.append("dispose_idle_owner_pool")
    @contextmanager
    def begin():
        yield SimpleNamespace(execute=operations.append)
    fixture.admin.begin = begin
    iterator = campaign.migration_database.__wrapped__(fixture, monkeypatch)
    assert next(iterator) == (fixture.admin.url.render_as_string(hide_password=False), fixture.admin)
    assert operations[0] == "dispose_idle_owner_pool"
    assert len(operations) == len(Base.metadata.sorted_tables) + 1
    assert all(isinstance(operation, Delete) and operation.table.name in Base.metadata.tables for operation in operations[1:])
    assert os.environ["METODOBASE_TEST_POSTGRES_URL"] == fixture.app.url.render_as_string(hide_password=False)
    with pytest.raises(StopIteration):
        next(iterator)


def test_adapter_refuses_checked_out_owner_pool_before_dispose_delete_or_peer(monkeypatch):
    fixture, operations = fixture_urls(), []
    fixture.app.pool.checkedout = lambda: 1
    fixture.app.dispose = lambda: operations.append("forbidden_dispose")
    fixture.admin.begin = lambda: operations.append("forbidden_delete")
    iterator = campaign.migration_database.__wrapped__(fixture, monkeypatch)
    with pytest.raises(AssertionError):
        next(iterator)
    assert operations == []


def test_original_pg_fixture_still_refuses_sqlite_before_migration(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SQLite refusal must happen before any migration")
    monkeypatch.setattr(original, "run_migration", forbidden)
    iterator = original.pg_invoice.__wrapped__(("sqlite://", SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))), monkeypatch)
    with pytest.raises(pytest.fail.Exception, match="SQLite is not a substitute"):
        next(iterator)


@pytest.mark.parametrize("fault", [None, "missing", "duplicate", "foreign", "sqlite", "skipped", "error", "failure"])
def test_exact_twelve_junit_cannot_drop_duplicate_or_substitute_a_peer(fault):
    module = contract.MODULE.removesuffix(".py").replace("/", ".")
    expected = [(module, name) for name in contract.CASES]
    suite = ET.Element("testsuite", tests="12", errors="0", failures="0", skipped="0")
    for classname, name in expected:
        ET.SubElement(suite, "testcase", classname=classname, name=name)
    if fault == "missing":
        suite.remove(suite[-1]); suite.set("tests", "11")
    elif fault == "duplicate":
        suite.append(deepcopy(suite[-1])); suite.set("tests", "13")
    elif fault == "foreign":
        suite[-1].set("name", "foreign_case")
    elif fault == "sqlite":
        suite[-1].set("name", suite[-1].get("name").replace("surface2", "sqlite-surface2"))
    elif fault in {"skipped", "error", "failure"}:
        ET.SubElement(suite[-1], fault)
        suite.set({"failure":"failures", "error":"errors", "skipped":"skipped"}[fault], "1")
    raw = ET.tostring(suite)
    if fault is None:
        assert require_exact_junit(raw, expected) == 12
    else:
        with pytest.raises(ValueError):
            require_exact_junit(raw, expected)
