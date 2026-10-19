"""Explicit30 restore; accepted26/27/28/29 fixtures and assertions stay immutable.

Copies the complete revision29 populated restore and its unchanged helpers.
Adds exact physical index preservation and a post-restore ASC-only drift canary.
No business RPO/RTO, production recovery or query latency is accepted here.
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from tests.integration_backup_restore_postgres import owned_databases as historical_owned_databases
from tests.integration_diary_restore_review import _populate_diary27, _verify_restored_diary27
from tests.client_link_restore_helpers import populate_links29, verify_restored_links29
from web.database.member_link_policy_v1 import MEMBER_LINK_TABLES
from tests.recovery28_restore_helpers import (populate_recovery28, reject_plain_recovery_material,
    exact_after_existing_startup_cleanup, verify_restored_recovery28_material, verify_restored_recovery28)


@pytest.fixture
def owned_databases():
    """Retain the accepted generator's exact UUID ownership and finalizer."""
    import psycopg2
    from tests.isolation import validate_postgres_test_url
    # Validate the private evidence destination before creating either DB.
    out = Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR'])
    assert out.is_absolute() and out.is_dir()
    generator = historical_owned_databases.__wrapped__()
    resources = next(generator)
    names = [name for name, _url in resources]
    assert len(names) == 2
    suffix = names[0].removeprefix('metodobase_test_backup_')
    assert len(suffix) == 12 and all(char in '0123456789abcdef' for char in suffix)
    assert names == ['metodobase_test_backup_' + suffix, 'metodobase_test_restore_' + suffix]
    try:
        with (out/'history-index30-author-owned-created.json').open('x', encoding='utf8') as stream:
            json.dump({'names': names, 'ownership': 'Exact generated resources returned by immutable accepted fixture'}, stream, indent=2)
            stream.write('\n')
        yield resources
    finally:
        generator.close()
        url = os.environ['METODOBASE_TEST_MIGRATOR_URL']
        validate_postgres_test_url(url)
        with psycopg2.connect(url.replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as db, db.cursor() as cursor:
            cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)', (names,))
            remaining = [row[0] for row in cursor.fetchall()]
        with (out/'history-index30-author-owned-closed.json').open('x', encoding='utf8') as stream:
            json.dump({'names': names, 'remaining': remaining, 'dropped_exactly_owned': remaining == []}, stream, indent=2)
            stream.write('\n')
        assert remaining == []


def test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts(owned_databases, tmp_path, monkeypatch):
    """Explicit30; preserve all26/27/28/29 criteria and physical index ordering."""
    import hashlib
    from sqlalchemy import MetaData, create_engine, func, select
    from sqlalchemy.orm import Session
    from scripts.backup_restore import create_backup, restore_backup
    from web.database.alembic.schema_contract_v1 import schema_signature
    from web.database.alembic.security_contract_v1 import tenant_security_signature
    from web.database.alembic.member_link_security_v1 import member_link_security_signature
    # BEGIN HISTORY30 INDEX IMPORTS
    from web.database.alembic.history_index_contract_v1 import (
        INDEX_NAME, create_history_index, expected_history_index, history_index_signature,
    )
    # END HISTORY30 INDEX IMPORTS
    from web.database.models import (Cliente, GymProfile, PlanGenerado, Usuario, UserRole,
                                     GymLicense, LicenseActivation, ProviderSubjectAssociation,
                                     GymGenerationReservation, StoredObject,
                                     GenerationReservation, UserSubscription)
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
    migrated = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py", "--revision", "20261019_personal_history_index"], cwd=root,
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
        "personal": ("restore-personal-user", "plan_pdf", b"%PDF-1.4\nSynthetic personal publication\n%%EOF", "application/pdf"),
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
            db.add(Usuario(id="restore-personal-user", email="restore-personal@example.invalid",
                password_hash="synthetic", nombre="Synthetic personal", tipo="usuario", role=UserRole.VIEWER))
            db.commit()
            db.add(Cliente(id_cliente="restore-release-client", gym_id="restore-release-gym",
                nombre="Synthetic client", edad=30, peso_kg=70, estatura_cm=170))
            db.add(Cliente(id_cliente="restore-personal-client", gym_id="restore-personal-user",
                nombre="Synthetic personal client", edad=30, peso_kg=70, estatura_cm=170))
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
            personal_plan = PlanGenerado(gym_id="restore-personal-user", id_cliente="restore-personal-client",
                plan_json='{"personal":true}', pdf_object_id=descriptors["personal"].id)
            db.add(personal_plan)
            db.flush()
            personal_plan_id = personal_plan.id
            captured = datetime(2026, 10, 18, 18, tzinfo=timezone.utc)
            db.add(UserSubscription(user_id="restore-personal-user", plan="pro", status="active",
                max_planes_mes=5, planes_usados_mes=3, mes_actual="2026-10"))
            for key, status, protocol, linked, marker in [
                    ("restore-personal-completed", "completed", 1, personal_plan.id, captured),
                    ("restore-personal-result-deleted", "completed", 1, None, captured),
                    ("restore-personal-legacy-unresolved", "reserved", 0, None, None),
                    ("restore-personal-released", "released", 1, None, None)]:
                db.add(GenerationReservation(id=key, user_id="restore-personal-user", request_key=key,
                    period="2026-10", status=status, publication_protocol=protocol,
                    plan_id=linked, persisted_at=marker, created_at=captured, updated_at=captured))
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
        diary_expected = _populate_diary27(source_url, source)
        recovery_expected = populate_recovery28(source_url, source, monkeypatch)
        links_expected = populate_links29(source_url, source, objects)
        original_rows = snapshot(source)
        assert all(token not in json.dumps(original_rows, default=str) for token in links_expected["tokens"])
        reject_plain_recovery_material(original_rows, recovery_expected)
        with source.connect() as connection:
            original_signature = schema_signature(connection)
            original_security = tenant_security_signature(connection)
            original_member_security = member_link_security_signature(connection)
            # BEGIN HISTORY30 SOURCE INDEX
            original_history_index = history_index_signature(connection)
            assert original_history_index == expected_history_index("postgresql")
            # END HISTORY30 SOURCE INDEX
            policy_state = connection.exec_driver_sql(
                "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname").all()
        assert len(original_signature["tables"]) == 29
        assert original_rows["alembic_version"][0]["version_num"] == "20261019_personal_history_index"
        assert len(TENANT_COLUMNS) == 20
        assert {name for name, enabled, forced in policy_state if enabled or forced} == set(TENANT_COLUMNS) | set(MEMBER_LINK_TABLES)
        assert all(enabled and forced for name, enabled, forced in policy_state if name in set(TENANT_COLUMNS) | set(MEMBER_LINK_TABLES))
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
            restored_security = tenant_security_signature(connection)
            restored_member_security = member_link_security_signature(connection)
            # BEGIN HISTORY30 RESTORED INDEX
            restored_history_index = history_index_signature(connection)
            assert restored_history_index == expected_history_index("postgresql")
            assert restored_history_index == original_history_index
            # END HISTORY30 RESTORED INDEX
        if restored_security != original_security or restored_member_security != original_member_security:
            output = Path(os.environ['METODOBASE_TEST_EVIDENCE_DIR'])
            (output/'postgres-restore-history-index30-security-drift.json').write_text(json.dumps({
                'expected_tenant_security':original_security,'restored_tenant_security':restored_security,
                'expected_member_security':original_member_security,'restored_member_security':restored_member_security,
            },indent=2)+'\n',encoding='utf-8')
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
            (output / "postgres-restore-history-index30-schema-drift.json").write_text(
                json.dumps({"structural_differences": differences(original_signature, restored_signature)}, indent=2)
                + "\n", encoding="utf-8")
        verify_runtime_schema(target, expected_revision="20261019_personal_history_index")
        # BEGIN HISTORY30 ASC-ONLY RESTORED DRIFT
        # Change only the timestamp sort direction; v1 deliberately omits it.
        restored_revision = original_rows["alembic_version"][0]["version_num"]
        with target.begin() as connection:
            connection.exec_driver_sql("DROP INDEX " + INDEX_NAME)
            connection.exec_driver_sql(
                "CREATE INDEX ix_planes_gym_cliente_history ON planes_generados "
                "(gym_id, id_cliente, fecha_generacion ASC NULLS LAST, id DESC NULLS LAST) "
                "WHERE deleted_at IS NULL"
            )
            wrong_history_index = history_index_signature(connection)
            assert wrong_history_index == {**original_history_index, "indoption": [0, 0, 0, 1]}
            assert schema_signature(connection) == restored_signature == original_signature
            assert tenant_security_signature(connection) == original_security
            assert member_link_security_signature(connection) == original_member_security
        assert snapshot(target) == original_rows
        with pytest.raises(RuntimeError, match="history ordering"):
            verify_runtime_schema(target, expected_revision=restored_revision)
        with target.begin() as connection:
            connection.exec_driver_sql("DROP INDEX " + INDEX_NAME)
            create_history_index(connection)
            assert history_index_signature(connection) == restored_history_index == original_history_index
            assert schema_signature(connection) == restored_signature == original_signature
            assert tenant_security_signature(connection) == original_security
            assert member_link_security_signature(connection) == original_member_security
        verify_runtime_schema(target, expected_revision=restored_revision)
        assert snapshot(target) == original_rows
        # END HISTORY30 ASC-ONLY RESTORED DRIFT
        assert restored_security == original_security and restored_member_security == original_member_security
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
        with tenant_scope("restore-personal-user"), Session(restricted_target) as db:
            from fastapi import HTTPException
            from web.services.generation_quota import finish_generation

            row = db.query(StoredObject).one()
            assert row.id == descriptors["personal"].id and row.status == "ready"
            descriptor = ObjectDescriptor(row.id, row.gym_id, row.kind, row.key,
                row.content_type, row.byte_size, row.sha256)
            content = restored_store.read(descriptor, owner_id="restore-personal-user")
            assert content == object_contents["personal"][2]
            assert len(content) == row.byte_size and hashlib.sha256(content).hexdigest() == row.sha256
            completed = db.get(GenerationReservation, "restore-personal-completed")
            assert completed.plan_id == personal_plan_id and completed.persisted_at == captured.replace(tzinfo=None)
            assert db.get(PlanGenerado, completed.plan_id).pdf_object_id == descriptor.id
            finish_generation(db, completed.id, "restore-personal-user", completed.plan_id, success=True)
            for key in ("restore-personal-completed", "restore-personal-result-deleted", "restore-personal-released"):
                finish_generation(db, key, "restore-personal-user", None, success=False)
                finish_generation(db, key, "restore-personal-user", None, success=False)
            with pytest.raises(HTTPException) as retained:
                finish_generation(db, "restore-personal-legacy-unresolved", "restore-personal-user", None, success=False)
            assert retained.value.status_code == 503
            db.rollback()
            assert db.query(UserSubscription).one().planes_usados_mes == 3
            assert db.get(GenerationReservation, "restore-personal-result-deleted").persisted_at == captured.replace(tzinfo=None)
            assert db.get(GenerationReservation, "restore-personal-result-deleted").plan_id is None
            assert db.get(GenerationReservation, "restore-personal-legacy-unresolved").status == "reserved"
            assert db.get(GenerationReservation, "restore-personal-legacy-unresolved").publication_protocol == 0
        assert snapshot(target) == original_rows
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
        links_proof = verify_restored_links29(target, restricted_target, restored_objects, links_expected, monkeypatch)
        assert snapshot(target) == original_rows
        physical_backup_rows = original_rows
        recovery_material = verify_restored_recovery28_material(target, restricted_target, recovery_expected)
        original_rows = exact_after_existing_startup_cleanup(physical_backup_rows, recovery_expected)
        diary_http_proof = _verify_restored_diary27(target, restricted_target, diary_expected, monkeypatch)
        assert snapshot(target) == original_rows
        recovery_proof = verify_restored_recovery28(target, restricted_target, recovery_expected, monkeypatch)
        signature_hash = hashlib.sha256(json.dumps(original_signature, sort_keys=True).encode()).hexdigest()
        measurement = {"environment": "synthetic PostgreSQL explicit revision30; preserved26/27/28/29 and physical history index",
            "tables": len(original_signature["tables"]), "schema_signature_sha256": signature_hash,
            "rls_families_force": len(TENANT_COLUMNS) + len(MEMBER_LINK_TABLES), "private_objects": len(descriptors),
            "pending_objects": 1, "legacy_files": 2,
            "individual_reservations": 4, "individual_consumed_credits": 3,
            "diary_days": 5, "diary_subjects": 2, "deleted_source_snapshot_preserved": True,
            "restored_diary_http": diary_http_proof,
            "restored_recovery": recovery_proof,
            "restored_member_links": links_proof,
            # BEGIN HISTORY30 MEASUREMENT
            "source_history_index": original_history_index,
            "restored_history_index": restored_history_index,
            "wrong_asc_history_index": wrong_history_index,
            "asc_only_drift_rejected_with_unchanged_v1_schema_and_rows": True,
            "correct_index_recreated_and_runtime_rows_security_reverified": True,
            # END HISTORY30 MEASUREMENT
            "restored_recovery_material_before_factory": recovery_material,
            "physical_backup_rows_by_table": {name: len(rows) for name, rows in physical_backup_rows.items()},
            "alembic_revision": original_rows["alembic_version"][0]["version_num"],
            "rows_by_table": {name: len(rows) for name, rows in original_rows.items()},
            "backup_seconds": backup_seconds, "restore_seconds": restore_seconds,
            "snapshot_age_at_verification_seconds": (datetime.now(timezone.utc) - committed_at).total_seconds(),
            "scope": "Actual local candidate schema recovery; technical timings do not approve business RPO/RTO or production recovery."}
        output = Path(os.environ.get("METODOBASE_TEST_EVIDENCE_DIR", str(tmp_path)))
        output.mkdir(parents=True, exist_ok=True)
        (output / "postgres-restore-history-index30-author.json").write_text(
            json.dumps(measurement, indent=2) + "\n", encoding="utf-8")
    finally:
        if restricted_target is not None:
            restricted_target.dispose()
        source.dispose()
        target.dispose()
