"""Narrow archive maintenance safety; every database is synthetic SQLite."""
import importlib
import sqlite3

import pytest


@pytest.fixture
def legacy_database():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE clientes(id_cliente TEXT PRIMARY KEY,nombre TEXT,peso_kg REAL,objetivo TEXT);
        INSERT INTO clientes VALUES('one','Synthetic one',70,'mantenimiento');
        INSERT INTO clientes VALUES('two','Synthetic two',80,'mantenimiento');
        CREATE TABLE planes_generados(id INTEGER PRIMARY KEY);
        INSERT INTO planes_generados VALUES(7);
        CREATE TABLE private_metadata(value TEXT);
        INSERT INTO private_metadata VALUES('synthetic private metadata');
    """)
    yield connection
    connection.close()


@pytest.fixture
def archive_engine(legacy_database, monkeypatch, tmp_path):
    # The archived import creates its historical FileHandler; confine that
    # side effect to this test's temp directory, never the repository/root DB.
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("scripts.archive.migrate_to_sa")
    engine = object.__new__(module.MigrationEngine)
    engine._legacy_conn = legacy_database
    return engine


def test_batch_keeps_valid_table_pagination_and_checkpoint(archive_engine):
    assert [row["id_cliente"] for row in archive_engine._read_legacy_batch("clientes", 0, 1)] == ["one"]
    assert [row["id_cliente"] for row in archive_engine._read_legacy_batch("clientes", 1, 1)] == ["two"]
    assert [row["id_cliente"] for row in archive_engine._read_legacy_batch("clientes", 0, 10, "one")] == ["two"]
    assert archive_engine._read_legacy_batch("planes_generados", 0, 1) == [{"id": 7}]


@pytest.mark.parametrize("table", ["private_metadata", "clientes WHERE 1=1", "clientes; DROP TABLE clientes"])
def test_batch_rejects_any_table_outside_closed_set(archive_engine, legacy_database, table):
    with pytest.raises(ValueError, match="Unsupported"):
        archive_engine._read_legacy_batch(table, 0, 10)
    assert legacy_database.execute("SELECT count(*) FROM clientes").fetchone()[0] == 2


@pytest.mark.parametrize("offset,limit", [(0, "1 OFFSET 1"), ("0; DROP TABLE clientes", 1)])
def test_batch_treats_limit_and_offset_as_values(archive_engine, legacy_database, offset, limit):
    with pytest.raises(sqlite3.DatabaseError):
        archive_engine._read_legacy_batch("clientes", offset, limit)
    assert legacy_database.execute("SELECT count(*) FROM clientes").fetchone()[0] == 2


@pytest.fixture
def validator(legacy_database):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from scripts.archive.validate_migration import MigrationValidator
    from web.database.models import Base, Cliente, Usuario, UserRole

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Usuario(id="synthetic-archive-gym", email="archive@example.invalid", nombre="Synthetic",
            tipo="gym", role=UserRole.OWNER, password_hash="synthetic"))
        db.flush()
        for identity, weight in (("one", 70), ("two", 80)):
            db.add(Cliente(id_cliente=identity, gym_id="synthetic-archive-gym", nombre="Synthetic " + identity,
                peso_kg=weight, objetivo="mantenimiento"))
        db.commit()
        value = MigrationValidator(":memory:")
        value._legacy_conn = legacy_database
        value._sa_session = db
        yield value
    engine.dispose()


@pytest.mark.parametrize("method", ["validate_data_parity", "validate_checksums"])
def test_validator_keeps_valid_sample_and_rejects_sql_fragment_limit(validator, legacy_database, method):
    check = getattr(validator, method)
    valid = check(sample_size=2)
    assert valid.passed
    assert valid.details["checked" if method == "validate_data_parity" else "mismatches"] == (
        2 if method == "validate_data_parity" else 0)
    invalid = check(sample_size="1 OFFSET 1")
    assert not invalid.passed and invalid.errors
    assert legacy_database.execute("SELECT count(*) FROM clientes").fetchone()[0] == 2


def test_checksum_still_detects_changed_synthetic_rows(validator):
    from web.database.models import Cliente

    validator._sa_session.query(Cliente).filter_by(id_cliente="one").one().peso_kg = 71
    validator._sa_session.commit()
    result = validator.validate_checksums(sample_size=2)
    # Preserve the historical advisory contract; this patch does not promote
    # the archived validator into a production acceptance/rollback decision.
    assert result.details["mismatches"] == 1 and result.warnings
