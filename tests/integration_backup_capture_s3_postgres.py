"""Explicit PG18 mechanism test on two owned databases; never discovers production.

Requires METODOBASE_BACKUP_CAPTURE_TEST_ACK=isolated-pg18 and an explicit
loopback METODOBASE_TEST_MIGRATOR_URL plus METODOBASE_TEST_PG_BIN. The caller
owns the cluster lifecycle. This fixture never starts/stops a server or uses
FORCE, pg_terminate_backend, a provider, external SMTP or application workers.
"""
import base64
import io
import json
import os
from contextlib import closing
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import uuid4

import pytest

from scripts import backup_capture_s3 as capture
from scripts.backup_restore import BackupError, restore_backup, verified_artifacts
from tests.isolation import validate_postgres_test_url
from web.storage.objects import describe
from web.storage.s3 import S3ObjectStore

SCHEMA = """
CREATE TABLE alembic_version (version_num text PRIMARY KEY);
INSERT INTO alembic_version VALUES ('20261031_gym_equipment');
CREATE TABLE stored_objects (
 id text PRIMARY KEY, gym_id text NOT NULL, kind text NOT NULL, key text NOT NULL UNIQUE,
 content_type text NOT NULL, byte_size integer NOT NULL, sha256 text NOT NULL,
 storage_backend text NOT NULL, status text NOT NULL, UNIQUE (gym_id,id));
CREATE TABLE planes_generados (
 id integer PRIMARY KEY, gym_id text NOT NULL, pdf_object_id text, ruta_pdf text,
 FOREIGN KEY (gym_id,pdf_object_id) REFERENCES stored_objects(gym_id,id));
CREATE TABLE gym_profiles (
 id integer PRIMARY KEY, gym_id text NOT NULL, logo_object_id text, logo_url text,
 FOREIGN KEY (gym_id,logo_object_id) REFERENCES stored_objects(gym_id,id));
CREATE TABLE client_plan_publications (
 id integer PRIMARY KEY, gym_id text NOT NULL, source_object_id text, object_key text,
 content_type text, byte_size integer, sha256 text, storage_backend text,
 FOREIGN KEY (gym_id,source_object_id) REFERENCES stored_objects(gym_id,id));
ALTER TABLE stored_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE stored_objects FORCE ROW LEVEL SECURITY;
CREATE POLICY hidden_without_context ON stored_objects USING (false);
"""


class MemoryS3:
    def __init__(self):
        self.contents = {}
        self.reads = []

    def get_object(self, *, Bucket, Key):
        self.reads.append(Key)
        data = self.contents[Key]
        return {"Body": io.BytesIO(data), "ContentLength": len(data)}


@pytest.fixture
def owned_databases(tmp_path):
    import psycopg2
    from psycopg2 import sql
    assert os.environ.get("METODOBASE_BACKUP_CAPTURE_TEST_ACK") == "isolated-pg18"
    url = os.environ["METODOBASE_TEST_MIGRATOR_URL"]
    validate_postgres_test_url(url)
    parsed = urlsplit(url.replace("postgresql+psycopg2://", "postgresql://", 1))
    assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    pg_bin = Path(os.environ["METODOBASE_TEST_PG_BIN"])
    assert pg_bin.is_absolute()
    token = uuid4().hex
    names = ["metodobase_test_capture_" + token, "metodobase_test_restore_" + token]
    role = "metodobase_test_reader_" + token
    password = "synthetic_" + uuid4().hex
    admin = psycopg2.connect(urlunsplit(parsed), connect_timeout=5)
    admin.autocommit = True
    created = []
    role_oid = None
    result = {"source": None, "target": None, "names": names, "token": token, "pg_bin": pg_bin,
              "role": role, "role_password": password, "restricted_url": None}
    try:
        with admin.cursor() as cursor:
            cursor.execute("SELECT current_setting('server_version_num')::int, rolsuper FROM pg_roles WHERE rolname=current_user")
            version, superuser = cursor.fetchone()
            assert 180000 <= version < 190000 and superuser is True
            for name in names:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                cursor.execute("SELECT oid FROM pg_database WHERE datname=%s", (name,))
                created.append((name, cursor.fetchone()[0]))
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD %s").format(sql.Identifier(role)), (password,))
            cursor.execute("SELECT oid FROM pg_roles WHERE rolname=%s", (role,))
            role_oid = cursor.fetchone()[0]
        result["source"], result["target"] = [urlunsplit(parsed._replace(path="/" + name, query="sslmode=disable")) for name in names]
        host = "[" + parsed.hostname + "]" if ":" in parsed.hostname else parsed.hostname
        restricted = parsed._replace(netloc=quote(role) + ":" + quote(password) + "@" + host + ":" + str(parsed.port or 5432),
                                     path="/" + names[0], query="sslmode=disable")
        result["restricted_url"] = urlunsplit(restricted)
        with closing(psycopg2.connect(result["source"], connect_timeout=5)) as source, source, source.cursor() as cursor:
            cursor.execute(SCHEMA)
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(names[0]), sql.Identifier(role)))
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
            cursor.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(role)))
        yield result
    finally:
        try:
            with admin.cursor() as cursor:
                for name, oid in reversed(created):
                    assert name in names and name.endswith(token)
                    cursor.execute("SELECT oid FROM pg_database WHERE datname=%s", (name,))
                    assert cursor.fetchone() == (oid,)
                    cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datid=%s", (oid,))
                    assert cursor.fetchone() == (0,), "Owned test database must close normally before DROP"
                    cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
                    cursor.execute("SELECT count(*) FROM pg_database WHERE datname=%s", (name,))
                    assert cursor.fetchone() == (0,)
                if role_oid is not None:
                    assert role.endswith(token)
                    cursor.execute("SELECT oid FROM pg_roles WHERE rolname=%s", (role,))
                    assert cursor.fetchone() == (role_oid,)
                    cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
                    cursor.execute("SELECT count(*) FROM pg_roles WHERE rolname=%s", (role,))
                    assert cursor.fetchone() == (0,)
        finally:
            admin.close()
        (tmp_path / "owned-normal-close.json").write_text(json.dumps({"operation": token,
            "databases_absent": len(created), "role_absent": role_oid is not None,
            "forced_disconnects": 0, "provider_operations": 0}), encoding="utf8")


def _insert(source_url, descriptor, plan_id):
    import psycopg2
    with closing(psycopg2.connect(source_url, connect_timeout=5)) as connection, connection, connection.cursor() as cursor:
        cursor.execute("INSERT INTO stored_objects VALUES (%s,%s,%s,%s,%s,%s,%s,'s3','ready')",
            (descriptor.id, descriptor.owner_id, descriptor.kind, descriptor.key,
             descriptor.content_type, descriptor.byte_size, descriptor.sha256))
        cursor.execute("INSERT INTO planes_generados VALUES (%s,%s,%s,NULL)",
                       (plan_id, descriptor.owner_id, descriptor.id))


def _arguments(context, store, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    return {"database_url": context["source"], "expected_database": context["names"][0],
        "expected_revision": "20261031_gym_equipment", "pg_bin": context["pg_bin"],
        "object_store": S3ObjectStore(store, "synthetic-bucket"),
        "limits": capture.CaptureLimits(max_dump_bytes=8 * 1024 * 1024,
            max_object_bytes=8 * 1024 * 1024, timeout_seconds=120)}


def test_pg18_exported_snapshot_excludes_concurrent_new_reference_from_dump_and_objects(owned_databases, tmp_path, monkeypatch):
    import psycopg2
    context = owned_databases
    store = MemoryS3()
    first_bytes = b"%PDF SYNTHETIC BEFORE EXPORTED SNAPSHOT"
    later_bytes = b"%PDF SYNTHETIC COMMITTED AFTER EXPORTED SNAPSHOT"
    first = describe("synthetic-owner", "plan_pdf", first_bytes, "application/pdf")
    later = describe("synthetic-owner", "plan_pdf", later_bytes, "application/pdf")
    store.contents[first.key] = first_bytes
    _insert(context["source"], first, 1)
    native_dump = capture._run_dump
    observed = {"concurrent_commit": False}

    def dump_after_concurrent_commit(*args):
        _insert(context["source"], later, 2)
        store.contents[later.key] = later_bytes
        observed["concurrent_commit"] = True
        native_dump(*args)

    monkeypatch.setattr(capture, "_run_dump", dump_after_concurrent_commit)
    report = capture.capture_backup(tmp_path / "captured", **_arguments(context, store, monkeypatch))
    assert observed["concurrent_commit"] is True
    assert report["status"] == "verified_current_resources"
    assert report["inventory_counts"]["ready_objects"] == 1
    assert store.reads == [first.key]
    destination = tmp_path / "restored-objects"
    restore = restore_backup(Path(report["manifest"]), database_url=context["target"],
        expected_database=context["names"][1], objects_destination=destination, pg_bin=context["pg_bin"])
    assert restore["objects"] == 1 and (destination / first.key).read_bytes() == first_bytes
    assert not (destination / later.key).exists()
    with closing(psycopg2.connect(context["source"], connect_timeout=5)) as source, source.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM stored_objects")
        assert cursor.fetchone() == (2,)
    with closing(psycopg2.connect(context["target"], connect_timeout=5)) as restored, restored.cursor() as cursor:
        cursor.execute("SELECT id FROM stored_objects")
        assert cursor.fetchall() == [(first.id,)]
        cursor.execute("SELECT id FROM planes_generados")
        assert cursor.fetchall() == [(1,)]
        cursor.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='stored_objects'::regclass")
        assert cursor.fetchone() == (True, True)
    with verified_artifacts(Path(report["manifest"])) as (manifest, _):
        assert manifest["capture"]["server_version_num"] // 10000 == 18
        assert manifest["capture"]["native_clients"]["pg_dump"]["version"].startswith("18.")
    (tmp_path / "snapshot-concurrency-receipt.json").write_text(json.dumps({
        "status": "PASS", "schema_scope": "minimal synthetic capture-contract tables, not full application schema",
        "source_rows_after_concurrent_commit": 2, "restored_rows_from_exported_snapshot": 1,
        "verified_objects": 1, "provider_operations": 0, "serving": False,
        "capture_elapsed_seconds": report["elapsed_seconds"]}), encoding="utf8")


def test_pg18_restricted_rls_reader_is_rejected_instead_of_empty_success(owned_databases, tmp_path, monkeypatch):
    context = owned_databases
    store = MemoryS3()
    arguments = _arguments(context, store, monkeypatch)
    arguments["database_url"] = context["restricted_url"]
    with pytest.raises(BackupError, match="global visibility"):
        capture.capture_backup(tmp_path / "restricted", **arguments)
    assert not store.reads and not list((tmp_path / "restricted").glob("*-manifest.json"))


def test_pg18_actual_legacy_reference_count_produces_partial_snapshot(owned_databases, tmp_path, monkeypatch):
    import psycopg2
    context = owned_databases
    store = MemoryS3()
    with closing(psycopg2.connect(context["source"], connect_timeout=5)) as source, source, source.cursor() as cursor:
        cursor.executemany("INSERT INTO planes_generados VALUES (%s,'synthetic-owner',NULL,'synthetic-missing.pdf')",
                           [(index,) for index in range(1, 40)])
        cursor.execute("INSERT INTO gym_profiles VALUES (1,'synthetic-owner',NULL,'synthetic-missing-logo.png')")
    report = capture.capture_backup(tmp_path / "legacy", **_arguments(context, store, monkeypatch))
    assert report["status"] == "partial_legacy_references"
    assert report["inventory_counts"]["legacy_plan_references_uncovered"] == 39
    assert report["inventory_counts"]["legacy_logo_references_uncovered"] == 1
    assert report["inventory_counts"]["ready_objects"] == 0 and not store.reads
    with verified_artifacts(Path(report["manifest"])) as (manifest, _):
        assert manifest["capture"]["status"] == "partial_legacy_references"
