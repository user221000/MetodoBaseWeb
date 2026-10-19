"""Independent explicit revision27 restore; the accepted26 fixture stays untouched.

Reuses its owned UUID database fixture and retains its complete row/object/
ledger assertions in this separate current-revision case.
"""
import base64
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from tests.integration_backup_restore_postgres import owned_databases as owned_databases


def test_revision27_populated_restore_keeps_diary_snapshots_and_all_revision26_contracts(owned_databases, tmp_path, monkeypatch):
    """Explicit27 restore; preserve all accepted26 row/object/ledger criteria."""
    import hashlib
    from sqlalchemy import MetaData, create_engine, func, select
    from sqlalchemy.orm import Session
    from scripts.backup_restore import create_backup, restore_backup
    from web.database.alembic.schema_contract_v1 import schema_signature
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
    migrated = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py", "--revision", "20261019_personal_diary"], cwd=root,
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
        original_rows = snapshot(source)
        with source.connect() as connection:
            original_signature = schema_signature(connection)
            policy_state = connection.exec_driver_sql(
                "SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class "
                "WHERE relnamespace='public'::regnamespace AND relkind='r' ORDER BY relname").all()
        assert len(original_signature["tables"]) == 26
        assert original_rows["alembic_version"][0]["version_num"] == "20261019_personal_diary"
        assert len(TENANT_COLUMNS) == 20
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
            (output / "postgres-restore-diary27-schema-drift.json").write_text(
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
        diary_http_proof = _verify_restored_diary27(target, restricted_target, diary_expected, monkeypatch)
        assert snapshot(target) == original_rows
        signature_hash = hashlib.sha256(json.dumps(original_signature, sort_keys=True).encode()).hexdigest()
        measurement = {"environment": "synthetic PostgreSQL explicit revision27; preserved revision26 private objects/ledger plus two-subject diary snapshots after source deletion",
            "tables": len(original_signature["tables"]), "schema_signature_sha256": signature_hash,
            "rls_families_force": len(TENANT_COLUMNS), "private_objects": len(descriptors),
            "pending_objects": 1, "legacy_files": 2,
            "individual_reservations": 4, "individual_consumed_credits": 3,
            "diary_days": 5, "diary_subjects": 2, "deleted_source_snapshot_preserved": True,
            "restored_diary_http": diary_http_proof,
            "alembic_revision": original_rows["alembic_version"][0]["version_num"],
            "rows_by_table": {name: len(rows) for name, rows in original_rows.items()},
            "backup_seconds": backup_seconds, "restore_seconds": restore_seconds,
            "snapshot_age_at_verification_seconds": (datetime.now(timezone.utc) - committed_at).total_seconds(),
            "scope": "Actual local candidate schema recovery; technical timings do not approve business RPO/RTO or production recovery."}
        output = Path(os.environ.get("METODOBASE_TEST_EVIDENCE_DIR", str(tmp_path)))
        output.mkdir(parents=True, exist_ok=True)
        (output / "postgres-restore-diary27-independent.json").write_text(
            json.dumps(measurement, indent=2) + "\n", encoding="utf-8")
    finally:
        if restricted_target is not None:
            restricted_target.dispose()
        source.dispose()
        target.dispose()


def _populate_diary27(source_url, admin):
    """Save through the real service/app role, then remove one source Plan."""
    from sqlalchemy import delete, select, text
    from sqlalchemy.orm import Session
    from tests.integration_provider_subjects import application_engine
    from web.database.models import Cliente, PersonalDiaryDay, PlanGenerado, Usuario, UserRole
    from web.personal_diary_schemas import CompletionOperation, MealOperation, WaterOperation
    from web.services.personal_diary_persistence import patch_diary_day, read_diary_day

    personal, member = 'restore-personal-user', 'restore-professional-member'
    instant = datetime(2026, 10, 19, 5, 59, 23, tzinfo=timezone.utc).astimezone(
        timezone(timedelta(hours=5, minutes=30)))
    days = [date(2026, 10, value) for value in (16, 17, 18)]

    def plan_body(kcal):
        option = {'alimento':'Avena β', 'gramos':100, 'equivalencia':'Synthetic serving',
                  'macros':{'kcal':kcal, 'proteina':10, 'carbs':15, 'grasa':2}}
        return json.dumps({meal:{'proteinas':{'opciones':[option]}}
                           for meal in ('desayuno','comida')}, ensure_ascii=False)

    with Session(admin) as db:
        db.add(Usuario(id=member, email='restore-member@example.invalid', nombre='Synthetic member',
            password_hash='synthetic-no-login', tipo='gym', role=UserRole.NUTRIOLOGO,
            team_gym_id='restore-release-gym', activo=True, session_version=0))
        db.commit()
        db.add(Cliente(id_cliente='restore-member-client', gym_id=member,
                       nombre='Independent member profile', activo=True))
        db.commit()
        plans = [PlanGenerado(gym_id=personal,id_cliente='restore-personal-client',
                              plan_json=plan_body(120)),
                 PlanGenerado(gym_id=member,id_cliente='restore-member-client',
                              plan_json=plan_body(310))]
        db.add_all(plans)
        db.commit()
        plan_ids = {personal:plans[0].id, member:plans[1].id}
    app = application_engine(source_url, admin)
    expected = {personal:{}, member:{}}
    try:
        with app.begin() as connection:
            connection.execute(text("SET TIME ZONE 'America/Mexico_City'"))
        def save(subject, day, operation):
            with Session(app) as db:
                state = patch_diary_day(db,subject,day,operation,now=instant)
                expected[subject][day.isoformat()] = state
                return state
        save(personal,days[2],WaterOperation(operation='water',expected_version=0,water_ml=1500))
        save(personal,days[2],MealOperation(operation='meal',expected_version=1,meal='desayuno',
             source_plan_id=plan_ids[personal],selections={'proteinas':0}))
        completed = save(personal,days[2],CompletionOperation(operation='completion',
                          expected_version=2,meal='desayuno',completed=True))
        assert completed['meals']['desayuno']['completed'] is True
        assert completed['created_at']=='2026-10-19T05:59:23+00:00'
        assert completed['local_date']=='2026-10-18'
        save(personal,days[1],MealOperation(operation='meal',expected_version=0,meal='comida',
             source_plan_id=plan_ids[personal],selections={'proteinas':0}))
        save(personal,days[1],WaterOperation(operation='water',expected_version=1,water_ml=500))
        save(personal,days[0],WaterOperation(operation='water',expected_version=0,water_ml=0))
        save(member,days[2],MealOperation(operation='meal',expected_version=0,meal='desayuno',
             source_plan_id=plan_ids[member],selections={'proteinas':0}))
        save(member,days[2],WaterOperation(operation='water',expected_version=1,water_ml=1800))
        save(member,days[1],WaterOperation(operation='water',expected_version=0,water_ml=900))
        with Session(admin) as db:
            db.execute(delete(PlanGenerado).where(PlanGenerado.id==plan_ids[personal]))
            db.commit()
            assert db.get(PlanGenerado,plan_ids[personal]) is None
            assert db.query(PersonalDiaryDay).count()==5
        # Removing the source Plan must not remove or rewrite saved snapshots;
        # a later water save still validates and preserves the complete meal.
        previous = expected[personal][days[1].isoformat()]['meals']
        changed = save(personal,days[1],WaterOperation(operation='water',expected_version=2,water_ml=750))
        assert changed['meals']==previous
        with Session(app) as db:
            assert read_diary_day(db,personal,days[2],now=instant)==completed
        with Session(admin) as db:
            row = db.scalar(select(PersonalDiaryDay).where(PersonalDiaryDay.user_id==personal,
                        PersonalDiaryDay.local_date==days[2]))
            assert row.created_at==datetime(2026,10,19,5,59,23)
    finally:
        app.dispose()
    with Session(admin) as db:
        ids = {subject:{row.local_date.isoformat():row.id for row in db.scalars(
            select(PersonalDiaryDay).where(PersonalDiaryDay.user_id==subject))} for subject in (personal,member)}
    return {'states':expected,'ids':ids,'deleted_source_id':plan_ids[personal], 'member_source_id':plan_ids[member]}


def _verify_restored_diary27(admin, app, expected, monkeypatch):
    """Read the restored composition using canonical auth/tenant in both apps."""
    import importlib
    from fastapi.testclient import TestClient
    from sqlalchemy import event, func, select, text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.orm import Session, sessionmaker
    from web.auth import crear_access_token, identity_from_user
    from web.database import engine as database
    from web.database.models import PersonalDiaryDay, PlanGenerado, Usuario
    from web.database.tenant_context import tenant_scope

    personal, member = 'restore-personal-user', 'restore-professional-member'
    with admin.connect() as db:
        assert db.scalar(select(func.count()).select_from(PlanGenerado).where(
            PlanGenerado.id==expected['deleted_source_id']))==0
    with Session(app) as db:
        assert db.scalars(select(PersonalDiaryDay)).all()==[]
    with app.connect() as db:
        flags=db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole '
                              'FROM pg_catalog.pg_roles WHERE rolname=current_user')).one()
        assert tuple(flags)==(False,False,False,False)
        assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
    with tenant_scope(personal), Session(app) as db:
        assert db.scalars(select(PersonalDiaryDay.user_id)).all()==[personal]*3
        assert db.query(PersonalDiaryDay).filter_by(user_id=member).update({'water_ml':1234})==0
        db.rollback()
        with pytest.raises(DBAPIError) as denied:
            db.add(PersonalDiaryDay(user_id=member,local_date=date(2026,10,15)))
            db.commit()
        assert denied.value.orig.pgcode=='42501'
        db.rollback()

    proofs = []
    with monkeypatch.context() as scoped:
        scoped.setattr(database,'_engine',app)
        scoped.setattr(database,'_SessionLocal',sessionmaker(bind=app,autoflush=False))
        for factory in ('web.main_web','api.app'):
            application=importlib.import_module(factory).create_app()
            assert not application.dependency_overrides
            with Session(app) as db:
                headers={subject:{'Authorization':'Bearer '+crear_access_token(identity_from_user(
                    db.get(Usuario,subject),db))} for subject in (personal,member,'restore-release-gym')}
            commits,dml=[],[]
            def committed(session):
                commits.append(True)
            def statement(conn,cursor,sql,parameters,context,executemany):
                if sql.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE'}:
                    dml.append(True)
            event.listen(Session,'after_commit',committed)
            event.listen(app,'before_cursor_execute',statement)
            try:
                with TestClient(application,raise_server_exceptions=False) as client:
                    # SaaS lifespan cleanup owns a legitimate startup commit.
                    # Observe the subsequent GET/export interval separately.
                    startup = {"commits":len(commits),"dml":len(dml)}
                    commits.clear(); dml.clear()
                    assert client.get('/api/usuario/diario/2026-10-18').status_code==401
                    for subject in (personal,member):
                        for day,state in expected['states'][subject].items():
                            response=client.get('/api/usuario/diario/'+day,headers=headers[subject])
                            assert response.status_code==200,response.text
                            assert response.headers['cache-control']=='no-store'
                            assert response.headers['referrer-policy']=='no-referrer'
                            result=response.json()
                            assert {key:value for key,value in result.items() if key!='today'}=={
                                key:value for key,value in state.items() if key!='today'}
                        page,after,seen=[],None,set()
                        for _ in range(10):
                            parameters={'limit':1}
                            if after is not None:parameters['after_diary']=after
                            response=client.get('/api/usuario/privacidad/exportar',params=parameters,
                                                headers=headers[subject])
                            assert response.status_code==200,response.text
                            exported=response.json()
                            assert exported['account']['id']==subject
                            assert [row['id_cliente'] for row in exported['profiles']['records']]==[
                                'restore-personal-client' if subject==personal else 'restore-member-client']
                            records=exported['personal_diary']['records']
                            page.extend(records)
                            after=exported['personal_diary']['next_after']
                            if after is None:break
                            assert after not in seen
                            seen.add(after)
                        else:pytest.fail('Diary export cursor did not terminate')
                        assert [row['local_date'] for row in page]==sorted(expected['states'][subject])
                        assert all(row['id']==expected['ids'][subject][row['local_date']] for row in page)
                        for row in page:
                            state=expected['states'][subject][row['local_date']]
                            assert row['meals']==state['meals'] and row['totals']==state['totals']
                            assert row['version']==state['version'] and row['water_ml']==state['water_ml']
                            assert row['created_at']==state['created_at'] and row['updated_at']==state['updated_at']
                    owner=client.get('/api/usuario/diario/2026-10-18',headers=headers['restore-release-gym'])
                    assert owner.status_code==403,owner.text
                    owner_export=client.get('/api/usuario/privacidad/exportar',headers=headers['restore-release-gym'])
                    assert owner_export.status_code==200
                    assert owner_export.json()['personal_diary']=={'records':[],'next_after':None}
                    assert commits==[] and dml==[]
            finally:
                event.remove(Session,'after_commit',committed)
                event.remove(app,'before_cursor_execute',statement)
            with app.connect() as db:
                assert db.scalar(text("SELECT current_setting('app.current_tenant',true)"))==''
                assert db.scalar(text('SELECT count(*) FROM personal_diary_days'))==0
            proofs.append({'factory':factory,'startup':startup,
                           'get_export_commits':len(commits),'get_export_dml':len(dml),
                           'restored_subject_days':[3,2],'cursor_pages_complete':True})
    return proofs
