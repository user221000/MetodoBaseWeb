"""Keep operator37 inputs explicit; actual39 inventory is refused, never adopted.

The two original operator families and their assertions remain untouched. This
file verifies the finite composition exception and a genuinely migrated39 input
with a real read-only inventory. No PostgreSQL server or provider is used.
"""
from copy import deepcopy
from datetime import UTC, datetime
import importlib
import json
from types import ModuleType
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from scripts.apply_legacy_objects import source_check
from tests.ci_web39 import composition
from tests.ci_web39 import sqlite_fixtures
from web.database.models import Cliente, PlanGenerado, UserRole, Usuario
from web.services import legacy_object_apply as service
from web.services import legacy_object_inventory as inventory
from web.services.legacy_object_apply_boundary import create_private_directory
from web.storage.configuration import ObjectStoreConfiguration
from web.storage.local import LocalObjectStore

current39_engine = sqlite_fixtures.followup_db


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def test_catalogue_remains74_with_exact72_current39_and_two_pinned_operator37_inputs():
    value = composition.specification()
    assert len(value["modules"]) == 74
    historical = {name for name, entry in value["modules"].items() if not entry["replacements"]}
    assert historical == set(composition.HISTORICAL37_MODULES)
    assert sum(bool(entry["replacements"]) for entry in value["modules"].values()) == 72
    for name in historical:
        assert value["modules"][name] == composition.historical37_entry(name)


@pytest.mark.parametrize("path", sorted(composition.HISTORICAL37_MODULES))
def test_original37_fixture_and_every_business_test_object_are_preserved_and_labelled(path):
    module = importlib.import_module(path.removesuffix(".py").replace("/", "."))
    original_fixture = module.account37_engine
    originals = {key: value for key, value in vars(module).items() if key.startswith(("test_", "Test"))}
    assert originals
    companion, receipt = composition.clone_namespace(module, composition.historical37_entry(path))
    assert companion is not module and companion.account37_engine is module.account37_engine is original_fixture
    assert all(getattr(companion, name) is getattr(module, name) is value for name, value in originals.items())
    assert receipt["test_objects_identical"] == len(originals)
    assert receipt["validation_scope"] == composition.HISTORICAL37_SCOPE
    assert receipt["original_module_unmodified"] is True
    binding = receipt["fixture_bindings"]
    assert len(binding) == 1 and binding[0]["preserved_operator_input_revision"] == "20261020_account_security"
    assert binding[0]["current_provider"] == binding[0]["original_provider"] == "tests.account_security37_fixtures.account37_engine"


@pytest.mark.parametrize("tamper", ["third_exception", "empty_current_binding", "wrong_pin", "wrong_preserved_provider",
                                    "retargeted_exception", "removed_exception", "wrong_split"])
def test_fixture_catalogue_rejects_unreviewed_exception_or_retarget(tamper):
    value = deepcopy(composition.specification())
    path = next(iter(composition.HISTORICAL37_MODULES))
    entry = value["modules"][path]
    if tamper == "third_exception":
        other = next(name for name in value["modules"] if name not in composition.HISTORICAL37_MODULES)
        value["modules"][other]["scope"] = composition.HISTORICAL37_SCOPE
    elif tamper == "empty_current_binding":
        other = next(name for name in value["modules"] if name not in composition.HISTORICAL37_MODULES)
        value["modules"][other]["replacements"] = {}
    elif tamper == "wrong_pin":
        entry["source_sha256_LF"] = "0" * 64
    elif tamper == "wrong_preserved_provider":
        entry["preserved_fixtures"]["account37_engine"]["module"] = "tests.ci_web39.sqlite_fixtures"
    elif tamper == "retargeted_exception":
        entry["replacements"] = entry["preserved_fixtures"]
    elif tamper == "removed_exception":
        entry["replacements"] = entry.pop("preserved_fixtures")
        entry.pop("scope")
    else:
        value["composition_scopes"] = {"current39_runtime_modules": 74, "historical37_operator_modules": 0}
    with pytest.raises(pytest.UsageError):
        composition.validate_specification(value)


@pytest.mark.parametrize("path", sorted(composition.HISTORICAL37_MODULES))
def test_historical_exception_refuses_a_replaced_fixture_before_execution(monkeypatch, path):
    from tests.ci_web39.sqlite_fixtures import followup_db
    module = importlib.import_module(path.removesuffix(".py").replace("/", "."))
    monkeypatch.setattr(module, "account37_engine", followup_db)
    with pytest.raises(pytest.UsageError, match="preserved operator37 fixture provider"):
        composition.clone_namespace(module, composition.historical37_entry(path))


def test_preserved_fixture_source_pin_and_business_test_presence_are_required(monkeypatch):
    path = next(iter(composition.HISTORICAL37_MODULES))
    module = importlib.import_module(path.removesuffix(".py").replace("/", "."))
    with monkeypatch.context() as patch:
        patch.setattr(composition, "HISTORICAL37_PROVIDER_SHA256_LF", "0" * 64)
        with pytest.raises(pytest.UsageError, match="preserved operator37 fixture provider"):
            composition.clone_namespace(module, composition.historical37_entry(path))
    empty = ModuleType(module.__name__)
    empty.__dict__.update({key: value for key, value in vars(module).items() if not key.startswith(("test_", "Test"))})
    with pytest.raises(pytest.UsageError, match="business test object"):
        composition.clone_namespace(empty, composition.historical37_entry(path))


def test_actual39_inventory_refuses_before_SQL_PUT_or_journal(current39_engine, tmp_path, monkeypatch):
    engine = current39_engine
    identity = uuid.uuid4().hex
    owner, client = "apply39-" + identity[:12], "client39-" + identity[:12]
    pdf, logo = tmp_path / "legacy-pdf", tmp_path / "old/web/static/uploads/logos"
    pdf.mkdir()
    logo.mkdir(parents=True)
    original = pdf / "synthetic.pdf"
    original.write_bytes(b"%PDF-inert-current39-inventory-rejection-only")
    with Session(engine) as db:
        db.add(Usuario(id=owner, email=identity + "@example.invalid", nombre="Synthetic39", password_hash="unused-no-login",
                       tipo="gym", role=UserRole.OWNER))
        db.flush()
        db.add(Cliente(id_cliente=client, gym_id=owner, nombre="Synthetic39"))
        db.flush()
        db.add(PlanGenerado(gym_id=owner, id_cliente=client, ruta_pdf=str(original), fecha_generacion=datetime.now(UTC)))
        db.commit()
    private = create_private_directory(tmp_path / "private39")
    roots = inventory.InventoryRoots(pdf, logo)
    inv = private / "inventory39.jsonl"
    with inventory.readonly_inventory_connection(engine) as connection:
        inventory.write_inventory(connection, roots, inv)
    records = [json.loads(line) for line in inv.read_bytes().splitlines()]
    assert records[0]["source_revision"] == "20261023_privacy_disposition"
    assert records[-1]["complete"] is True and records[-1]["legacy_entries"] == 1
    configuration = ObjectStoreConfiguration(backend="local", local_root=tmp_path / "objects")
    manifest = private / "mapping39.json"
    manifest.write_bytes(service.canonical({"format": 1, "inventory_sha256": service.digest(inv.read_bytes()),
        "source": source_check(), "destination_sha256": service.destination_binding(configuration),
        "entries": [{"entry_sha256": service.entry_key(entry), "apply": True,
            "provenance_reference": "synthetic39-input-must-not-authorize-operator37"} for entry in records[1:-1]]}))
    manifest.chmod(0o600)
    statements = []
    def observe(*args): statements.append(args[2])
    event.listen(engine, "before_cursor_execute", observe)
    monkeypatch.setattr(LocalObjectStore, "put", lambda *_a, **_k: pytest.fail("Unsupported39 reached PUT"))
    monkeypatch.setattr(service.Journal, "__enter__", lambda *_a, **_k: pytest.fail("Unsupported39 opened a journal"))
    try:
        with pytest.raises(service.ApplyError, match="artifact_binding_changed"):
            service.Bundle(manifest, inv, roots, configuration, source_check=source_check)
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert statements == [] and not list(private.glob("*journal*"))
    assert not (tmp_path / "objects").exists()
    assert original.read_bytes() == b"%PDF-inert-current39-inventory-rejection-only"
