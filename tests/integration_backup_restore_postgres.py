"""Independent encrypted PostgreSQL/object restore; requires a synthetic cluster.

Explicit invocation keeps ordinary unit tests provider/service independent.
The fixture owns and drops only its newly generated metodobase_test_* databases.
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit, urlunsplit
import uuid

import pytest

from tests.isolation import validate_postgres_test_url


@pytest.fixture
def owned_databases():
    import psycopg2
    from psycopg2 import sql

    url = os.environ["METODOBASE_TEST_MIGRATOR_URL"]
    validate_postgres_test_url(url)
    parsed = urlsplit(url)
    token = uuid.uuid4().hex[:12]
    names = ["metodobase_test_backup_" + token, "metodobase_test_restore_" + token]
    admin = psycopg2.connect(url.replace("postgresql+psycopg2://", "postgresql://", 1), connect_timeout=5)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            for name in names:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        urls = [urlunsplit(parsed._replace(path="/" + name)) for name in names]
        yield tuple(zip(names, urls))
    finally:
        with admin.cursor() as cursor:
            for name in names:
                assert name.startswith(("metodobase_test_backup_", "metodobase_test_restore_")) and name.endswith(token)
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        admin.close()


def test_encrypted_pg_restore_preserves_rows_constraints_and_private_objects(owned_databases, tmp_path, monkeypatch):
    import psycopg2
    from scripts.backup_restore import BackupError, create_backup, restore_backup

    (source_name, source_url), (target_name, target_url) = owned_databases
    source_dsn = source_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    target_dsn = target_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    pg_bin = Path(os.environ["METODOBASE_TEST_PG_BIN"]) if os.environ.get("METODOBASE_TEST_PG_BIN") else None
    with psycopg2.connect(source_dsn) as db, db.cursor() as cursor:
        cursor.execute("CREATE TABLE qa_gym (id integer PRIMARY KEY, name text NOT NULL)")
        cursor.execute("CREATE TABLE qa_client (id integer PRIMARY KEY, gym_id integer NOT NULL REFERENCES qa_gym(id), name text NOT NULL)")
        cursor.execute("CREATE TABLE qa_plan (id integer PRIMARY KEY, client_id integer NOT NULL REFERENCES qa_client(id), object_key text UNIQUE NOT NULL)")
        cursor.execute("INSERT INTO qa_gym VALUES (1,'Synthetic Gym')")
        cursor.execute("INSERT INTO qa_client VALUES (7,1,'Synthetic Client')")
        cursor.execute("INSERT INTO qa_plan VALUES (13,7,'gym-1/plan-13.pdf')")
    committed_at = datetime.now(timezone.utc)
    objects = tmp_path / "objects"
    (objects / "gym-1").mkdir(parents=True)
    (objects / "gym-1/plan-13.pdf").write_bytes(b"%PDF-1.4\nSynthetic isolated QA plan\n%%EOF")
    (objects / "gym-1/logo.png").write_bytes(b"Synthetic isolated QA logo")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    start = time.monotonic()
    manifest_path = create_backup(tmp_path / "backup", database_url=source_url,
        expected_database=source_name, objects_root=objects, pg_bin=pg_bin)
    backup_seconds = time.monotonic() - start
    # A later synthetic write must not appear in the earlier snapshot.
    with psycopg2.connect(source_dsn) as db, db.cursor() as cursor:
        cursor.execute("INSERT INTO qa_gym VALUES (2,'After snapshot')")
    start = time.monotonic()
    destination = tmp_path / "restored-objects"
    report = restore_backup(manifest_path, database_url=target_url, expected_database=target_name,
        objects_destination=destination, pg_bin=pg_bin)
    restore_seconds = time.monotonic() - start
    assert report["restored"] == ["objects", "postgres"]
    assert report["objects"] == 2
    with psycopg2.connect(target_dsn) as db, db.cursor() as cursor:
        cursor.execute("SELECT g.id,c.id,p.id,p.object_key FROM qa_gym g JOIN qa_client c ON c.gym_id=g.id JOIN qa_plan p ON p.client_id=c.id")
        assert cursor.fetchall() == [(1, 7, 13, "gym-1/plan-13.pdf")]
        cursor.execute("SELECT count(*) FROM qa_gym")
        assert cursor.fetchone()[0] == 1
    with psycopg2.connect(target_dsn) as db, db.cursor() as cursor, pytest.raises(psycopg2.IntegrityError):
        cursor.execute("INSERT INTO qa_plan VALUES (99,999,'missing-client.pdf')")
    for relative in ("gym-1/plan-13.pdf", "gym-1/logo.png"):
        assert (destination / relative).read_bytes() == (objects / relative).read_bytes()
    with pytest.raises(BackupError, match="not empty"):
        restore_backup(manifest_path, database_url=target_url, expected_database=target_name,
            objects_destination=tmp_path / "second-objects", pg_bin=pg_bin)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["encryption"] == "AES-256-GCM"
    measured = {"environment": "local Windows PostgreSQL synthetic schema: one gym, client, plan and two objects",
        "postgresql": "17.11", "source_committed_at": committed_at.isoformat(),
        "backup_seconds": backup_seconds, "restore_seconds": restore_seconds,
        "snapshot_age_at_verification_seconds": (datetime.now(timezone.utc) - committed_at).total_seconds(),
        "scope": "Measures this small technical restore only; business RPO/RTO and deployed-schema recovery remain separate acceptance."}
    output = Path(os.environ.get("METODOBASE_TEST_EVIDENCE_DIR", str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    (output / "postgres-restore-independent.json").write_text(json.dumps(measured, indent=2), encoding="utf-8")


def test_release_schema_restore_preserves_migrations_rows_relationships_and_objects(owned_databases, tmp_path, monkeypatch):
    """Restore the actual Alembic candidate, separate from the tiny tool probe."""
    import hashlib
    from sqlalchemy import MetaData, create_engine, func, select
    from sqlalchemy.orm import Session
    from scripts.backup_restore import create_backup, restore_backup
    from web.database.alembic.schema_contract_v1 import schema_signature
    from web.database.models import (Cliente, GymProfile, PlanGenerado, Usuario, UserRole,
                                     GymLicense, LicenseActivation, ProviderSubjectAssociation,
                                     GymGenerationReservation, StoredObject)
    from web.database.repository import _crear_planes_default
    from web.database.schema_control import verify_runtime_schema
    from web.database.tenant_context import tenant_scope
    from web.database.tenant_policy import TENANT_COLUMNS
    from web.storage.local import LocalObjectStore
    from web.storage.objects import ObjectAccessDenied, ObjectDescriptor, describe
    from tests.integration_provider_subjects import application_engine

    (source_name, source_url), (target_name, target_url) = owned_databases
    root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ, DATABASE_URL=source_url, METODOBASE_TEST_DATABASE_URL="")
    migrated = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py"], cwd=root,
        env=environment, capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    source, target = create_engine(source_url), create_engine(target_url)
    restricted_target = None
    pg_bin = Path(os.environ["METODOBASE_TEST_PG_BIN"]) if os.environ.get("METODOBASE_TEST_PG_BIN") else None
    objects = tmp_path / "objects"
    original_store = LocalObjectStore(objects)
    logo_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+yF9sAAAAASUVORK5CYII=")
    object_contents = {
        "pdf": ("restore-release-gym", "plan_pdf", b"%PDF-1.4\nSynthetic private restore\n%%EOF", "application/pdf"),
        "logo": ("restore-release-gym", "gym_logo", logo_bytes, "image/png"),
        "pending": ("restore-release-gym", "plan_pdf", b"%PDF-1.4\nSynthetic uncertain PUT orphan\n%%EOF", "application/pdf"),
        "foreign": ("restore-foreign-gym", "plan_pdf", b"%PDF-1.4\nSynthetic other owner\n%%EOF", "application/pdf"),
    }
    descriptors = {}
    for label, (owner, kind, content, content_type) in object_contents.items():
        descriptor = describe(owner, kind, content, content_type)
        original_store.put(descriptor, content, owner_id=owner)
        descriptors[label] = descriptor

    def snapshot(engine):
        metadata = MetaData()
        metadata.reflect(bind=engine)
        with engine.connect() as connection:
            return {table.name: [dict(row) for row in connection.execute(
                select(table).order_by(*table.primary_key.columns)).mappings()]
                for table in metadata.sorted_tables}

    try:
        with Session(source) as db:
            db.add(Usuario(id="restore-release-gym", email="restore-release@example.invalid",
                password_hash="synthetic-not-an-authentication-secret", nombre="Synthetic restore",
                tipo="gym", role=UserRole.OWNER, session_version=0, activo=True))
            db.add(Usuario(id="restore-foreign-gym", email="restore-foreign@example.invalid",
                password_hash="synthetic", nombre="Synthetic other owner", tipo="gym", role=UserRole.OWNER))
            db.commit()
            db.add(Cliente(id_cliente="restore-release-client", gym_id="restore-release-gym",
                nombre="Synthetic client", edad=30, peso_kg=70, estatura_cm=170))
            db.commit()
            for label, descriptor in descriptors.items():
                db.add(StoredObject(id=descriptor.id, gym_id=descriptor.owner_id,
                    kind=descriptor.kind, key=descriptor.key, content_type=descriptor.content_type,
                    byte_size=descriptor.byte_size, sha256=descriptor.sha256,
                    storage_backend="local", status="pending" if label == "pending" else "ready"))
            db.flush()
            db.add(GymProfile(gym_id="restore-release-gym", nombre_negocio="Synthetic restore",
                logo_url="restore-release-gym/logo.png", logo_object_id=descriptors["logo"].id))
            plan = PlanGenerado(gym_id="restore-release-gym", id_cliente="restore-release-client",
                ruta_pdf="restore-release-gym/release-plan.pdf", plan_json='{"synthetic": true}',
                kcal_objetivo=2000, kcal_real=1995, pdf_object_id=descriptors["pdf"].id)
            db.add(plan)
            db.add(PlanGenerado(gym_id="restore-release-gym", id_cliente="restore-release-client",
                ruta_pdf="restore-release-gym/release-plan.pdf", plan_json='{"legacy":true}',
                pdf_object_id=None))
            db.flush()
            captured = datetime(2026, 10, 18, 18, tzinfo=timezone.utc)
            result = {"success": True, "plan_id": plan.id, "label": "synthetic durable result"}
            db.add(GymGenerationReservation(gym_id="restore-release-gym", client_id="restore-release-client",
                request_key="synthetic-release-restore-request", request_hash="c" * 64,
                period="2026-10", local_date=captured.date(), timezone="America/Mexico_City",
                catalog_plan="free", status="completed", plan_id=plan.id,
                persisted_at=captured.replace(tzinfo=None), created_at=captured.replace(tzinfo=None),
                updated_at=captured.replace(tzinfo=None), result_json=json.dumps(result)))
            _crear_planes_default(db, "restore-release-gym")
            license_key = "synthetic-release-restore-issued-key"
            issued = GymLicense(gym_id="restore-release-gym", license_key=license_key,
                                plan_tier="clinica", max_clients=0, is_active=True)
            db.add(issued)
            db.flush()
            db.add_all([
                LicenseActivation(gym_id="restore-release-gym", issued_license_id=issued.id,
                    hardware_id="synthetic-bound-restore-hardware",
                    clave_hash=hashlib.sha256(license_key.encode()).hexdigest(),
                    email="restore-release@example.invalid", plan="clinica", expira=None),
                LicenseActivation(hardware_id="synthetic-unassociated-legacy-hardware",
                    clave_hash="0" * 64, email="unassociated@example.invalid", plan="standard",
                    activa=False, revocada=True, expira=datetime(2026, 1, 1)),
                ProviderSubjectAssociation(provider="stripe", resource_type="customer",
                    resource_id="cus_synthetic_release_restore", subject_id="restore-release-gym",
                    provenance="verified_purchase", source_ref="synthetic-local-restore-only"),
            ])
            db.commit()
        original_rows = snapshot(source)
        with source.connect() as connection:
            original_signature = schema_signature(connection)
            policy_state = connection.exec_driver_sql(
                "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname").all()
        assert len(original_signature["tables"]) == 25
        assert original_rows["alembic_version"][0]["version_num"] == "20261018_stored_objects"
        assert len(TENANT_COLUMNS) == 19
        assert {name for name, enabled, forced in policy_state if enabled or forced} == set(TENANT_COLUMNS)
        assert all(enabled and forced for name, enabled, forced in policy_state if name in TENANT_COLUMNS)
        committed_at = datetime.now(timezone.utc)
        (objects / "restore-release-gym").mkdir(parents=True)
        (objects / "restore-release-gym/release-plan.pdf").write_bytes(b"%PDF-1.4\nSynthetic release restore\n%%EOF")
        (objects / "restore-release-gym/logo.png").write_bytes(logo_bytes)
        monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
        start = time.monotonic()
        manifest_path = create_backup(tmp_path / "release-backup", database_url=source_url,
            expected_database=source_name, objects_root=objects, pg_bin=pg_bin)
        backup_seconds = time.monotonic() - start
        with Session(source) as db:
            db.get(Usuario, "restore-release-gym").nombre = "After snapshot"
            db.commit()
        start = time.monotonic()
        restored_objects = tmp_path / "restored-release-objects"
        restore_backup(manifest_path, database_url=target_url, expected_database=target_name,
            objects_destination=restored_objects, pg_bin=pg_bin)
        restore_seconds = time.monotonic() - start
        with target.connect() as connection:
            restored_signature = schema_signature(connection)
        if restored_signature != original_signature:
            def differences(expected, actual, path="schema"):
                if isinstance(expected, dict) and isinstance(actual, dict):
                    return [difference for key in sorted(set(expected) | set(actual))
                        for difference in differences(expected.get(key), actual.get(key), path + "." + key)]
                if isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual):
                    return [difference for index, (left, right) in enumerate(zip(expected, actual))
                        for difference in differences(left, right, path + f"[{index}]")]
                return [] if expected == actual else [{"field": path, "expected": expected, "restored": actual}]
            output = Path(os.environ.get("METODOBASE_TEST_EVIDENCE_DIR", str(tmp_path)))
            output.mkdir(parents=True, exist_ok=True)
            (output / "postgres-restore-release-schema-drift.json").write_text(
                json.dumps({"structural_differences": differences(original_signature, restored_signature)}, indent=2)
                + "\n", encoding="utf-8")
        verify_runtime_schema(target)
        assert snapshot(target) == original_rows
        with Session(target) as db:
            reservation = db.query(GymGenerationReservation).one()
            assert reservation.status == "completed" and reservation.persisted_at == captured.replace(tzinfo=None)
            assert json.loads(reservation.result_json) == result
            assert db.get(PlanGenerado, reservation.plan_id).id_cliente == reservation.client_id
        with target.connect() as connection:
            assert schema_signature(connection) == original_signature
            restored_policies = connection.exec_driver_sql(
                "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname").all()
            assert restored_policies == policy_state
        for relative in ("restore-release-gym/release-plan.pdf", "restore-release-gym/logo.png"):
            assert (restored_objects / relative).read_bytes() == (objects / relative).read_bytes()
        # Reconstruct both the restricted database connection and the adapter;
        # no original store instance, descriptor object or byte cache is reused.
        restored_store = LocalObjectStore(restored_objects)
        restricted_target = application_engine(target_url, target)
        with Session(restricted_target) as db:
            assert db.scalars(select(StoredObject)).all() == []
        with tenant_scope("restore-release-gym"), Session(restricted_target) as db:
            restored_metadata = {row.id: row for row in db.scalars(select(StoredObject))}
            assert set(restored_metadata) == {descriptors[label].id for label in ("pdf", "logo", "pending")}
            for label in ("pdf", "logo", "pending"):
                row = restored_metadata[descriptors[label].id]
                descriptor = ObjectDescriptor(row.id, row.gym_id, row.kind, row.key,
                    row.content_type, row.byte_size, row.sha256)
                assert row.status == ("pending" if label == "pending" else "ready")
                content = restored_store.read(descriptor, owner_id="restore-release-gym")
                assert content == object_contents[label][2]
                assert len(content) == row.byte_size and hashlib.sha256(content).hexdigest() == row.sha256
            assert db.get(PlanGenerado, result["plan_id"]).pdf_object_id == descriptors["pdf"].id
            assert db.query(GymProfile).one().logo_object_id == descriptors["logo"].id
            pending_id = descriptors["pending"].id
            assert db.scalar(select(func.count()).select_from(PlanGenerado).where(PlanGenerado.pdf_object_id == pending_id)) == 0
            assert db.scalar(select(func.count()).select_from(GymProfile).where(GymProfile.logo_object_id == pending_id)) == 0
            assert db.scalar(select(func.count()).select_from(PlanGenerado).where(PlanGenerado.pdf_object_id.is_(None))) == 1
            assert db.get(StoredObject, descriptors["foreign"].id) is None
        with tenant_scope("restore-foreign-gym"), Session(restricted_target) as db:
            row = db.query(StoredObject).one()
            foreign_descriptor = ObjectDescriptor(row.id, row.gym_id, row.kind, row.key,
                row.content_type, row.byte_size, row.sha256)
            assert restored_store.read(foreign_descriptor, owner_id="restore-foreign-gym") == object_contents["foreign"][2]
        with pytest.raises(ObjectAccessDenied):
            restored_store.read(foreign_descriptor, owner_id="restore-release-gym")
        with Session(restricted_target) as db:
            assert db.scalars(select(StoredObject)).all() == []
        with Session(target) as db:
            new_profile = GymProfile(gym_id="restore-release-gym", nombre_negocio="Sequence check")
            # Exercise the restored sequence without violating the gym's 1:1 key.
            new_user = Usuario(id="restore-sequence-gym", email="restore-sequence@example.invalid",
                password_hash="synthetic", nombre="Sequence check", tipo="gym", role=UserRole.OWNER)
            db.add(new_user)
            db.flush()
            new_profile.gym_id = new_user.id
            db.add(new_profile)
            db.flush()
            assert new_profile.id > original_rows["gym_profiles"][0]["id"]
            db.rollback()
        signature_hash = hashlib.sha256(json.dumps(original_signature, sort_keys=True).encode()).hexdigest()
        measurement = {"environment": "synthetic PostgreSQL Alembic25, ready PDF/logo, pending orphan, foreign owner and two legacy files",
            "tables": len(original_signature["tables"]), "schema_signature_sha256": signature_hash,
            "rls_families_force": len(TENANT_COLUMNS), "private_objects": len(descriptors),
            "pending_objects": 1, "legacy_files": 2,
            "alembic_revision": original_rows["alembic_version"][0]["version_num"],
            "rows_by_table": {name: len(rows) for name, rows in original_rows.items()},
            "backup_seconds": backup_seconds, "restore_seconds": restore_seconds,
            "snapshot_age_at_verification_seconds": (datetime.now(timezone.utc) - committed_at).total_seconds(),
            "scope": "Actual local candidate schema recovery; technical timings do not approve business RPO/RTO or production recovery."}
        output = Path(os.environ.get("METODOBASE_TEST_EVIDENCE_DIR", str(tmp_path)))
        output.mkdir(parents=True, exist_ok=True)
        (output / "postgres-restore-storage25-independent.json").write_text(
            json.dumps(measurement, indent=2) + "\n", encoding="utf-8")
    finally:
        if restricted_target is not None:
            restricted_target.dispose()
        source.dispose()
        target.dispose()
