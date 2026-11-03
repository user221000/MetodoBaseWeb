"""Bounded snapshot orchestration, real crypto and isolated S3 failure controls."""
import base64
import io
import json
import os
import time
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import backup_capture_s3 as capture
from scripts.backup_restore import BackupError, verified_artifacts
from web.storage.objects import describe
from web.storage.s3 import S3ObjectStore


class Client:
    def __init__(self, contents):
        self.contents = contents
        self.reads = []
        self.close_error = False

    def get_object(self, *, Bucket, Key):
        self.reads.append(Key)
        if Key not in self.contents:
            raise RuntimeError("provider credential and customer value must not escape")
        data = self.contents[Key]
        return {"Body": io.BytesIO(data), "ContentLength": len(data)}

    def close(self):
        if self.close_error:
            raise RuntimeError("private-close-detail")


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, parameters=None):
        self.connection.statements.append((query, parameters))
        if query.startswith("SET LOCAL"):
            self.result = []
        elif "current_database()" in query:
            self.result = [self.connection.identity]
        elif "FROM public.alembic_version" in query:
            self.result = [(self.connection.revision,)]
        elif "pg_export_snapshot" in query:
            self.result = [(self.connection.snapshot,)]
        elif "FROM public.stored_objects ORDER BY id" in query:
            self.result = self.connection.rows[:parameters[0]]
        elif query == capture.REFERENCE_SQL:
            self.result = [(1, self.connection.bad_references)]
        elif query == capture.PUBLICATION_SQL:
            self.result = [(self.connection.bad_publications,)]
        elif "legacy" not in query and "COALESCE(ruta_pdf" in query:
            self.result = [self.connection.legacy]
        else:
            raise AssertionError("Unexpected capture SQL")

    def fetchone(self):
        return self.result[0]

    def fetchall(self):
        return list(self.result)


class Connection:
    def __init__(self, rows):
        self.rows = rows
        self.identity = ("metodobase_test_capture", 180006, "on", "repeatable read", "off", True)
        self.revision = "20261031_gym_equipment"
        self.snapshot = "00000003-00000007-1"
        self.bad_references = 0
        self.bad_publications = 0
        self.legacy = (0, 0)
        self.statements = []
        self.settings = None
        self.closed = False
        self.rolled_back = False

    def set_session(self, **kwargs):
        self.settings = kwargs

    def cursor(self):
        return Cursor(self)

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    data = b"%PDF-1.4 SYNTHETIC SNAPSHOT"
    descriptor = describe("synthetic-owner", "plan_pdf", data, "application/pdf")
    row = (descriptor.id, descriptor.owner_id, descriptor.kind, descriptor.key,
           descriptor.content_type, descriptor.byte_size, descriptor.sha256, "s3", "ready")
    connection = Connection([row])
    monkeypatch.setattr(capture, "_connect", lambda environment: connection)
    pg_bin = tmp_path / "pg18-bin"
    pg_bin.mkdir()
    for name in ("pg_dump", "pg_restore"):
        (pg_bin / (name + (".exe" if os.name == "nt" else ""))).write_bytes(b"synthetic-client-only")

    def identity(directory, environment, deadline):
        return {name: {"version": "18.6", "sha256": capture.checksum(capture._executable(directory, name))}
                for name in ("pg_dump", "pg_restore")}

    def dump(directory, environment, snapshot, destination, limits, deadline):
        assert not connection.closed and not connection.rolled_back
        assert connection.settings == {"isolation_level": "REPEATABLE READ", "readonly": True, "autocommit": False}
        assert snapshot == connection.snapshot
        assert environment["PGDATABASE"] == "metodobase_test_capture"
        destination.write_bytes(b"PGDMP SYNTHETIC CONSISTENT SNAPSHOT")

    monkeypatch.setattr(capture, "_native_identity", identity)
    monkeypatch.setattr(capture, "_run_dump", dump)
    client = Client({descriptor.key: data})
    arguments = {"database_url": "postgresql://synthetic:synthetic@127.0.0.1:54329/metodobase_test_capture?sslmode=disable",
        "expected_database": "metodobase_test_capture", "expected_revision": connection.revision,
        "pg_bin": pg_bin, "object_store": S3ObjectStore(client, "synthetic-bucket"),
        "limits": capture.CaptureLimits(max_dump_bytes=1024 * 1024, max_object_bytes=1024 * 1024)}
    return tmp_path, connection, client, descriptor, arguments


@pytest.mark.parametrize("revision", sorted(capture.REVISIONS))
def test_authenticated_capture_preserves_exact_snapshot_objects_and_closes_tx(prepared, revision):
    root, connection, client, descriptor, arguments = prepared
    connection.revision = revision
    arguments["expected_revision"] = revision
    report = capture.capture_backup(root / "capture", **arguments)
    assert report["status"] == "verified_current_resources"
    assert connection.closed and connection.rolled_back
    assert client.reads == [descriptor.key]
    assert report["database_mutations"] == report["provider_writes"] == 0
    with verified_artifacts(Path(report["manifest"])) as (manifest, artifacts):
        assert manifest["capture"]["source_revision"] == revision
        assert manifest["capture"]["postgresql_consistency"] == "same_exported_snapshot"
        assert manifest["capture"]["serving_authorized"] is False
        assert artifacts["postgres"][0].read_bytes() == b"PGDMP SYNTHETIC CONSISTENT SNAPSHOT"
        with zipfile.ZipFile(artifacts["objects"][0]) as archive:
            assert archive.namelist() == [descriptor.key]
            assert archive.read(descriptor.key) == client.contents[descriptor.key]


def test_legacy_forty_references_remain_partial_and_authenticated(prepared):
    root, connection, _, _, arguments = prepared
    connection.legacy = (39, 1)
    report = capture.capture_backup(root / "legacy", **arguments)
    assert report["status"] == "partial_legacy_references"
    with verified_artifacts(Path(report["manifest"])) as (manifest, _):
        assert manifest["capture"]["status"] == "partial_legacy_references"
        assert manifest["capture"]["inventory_counts"]["legacy_plan_references_uncovered"] == 39
        assert manifest["capture"]["inventory_counts"]["legacy_logo_references_uncovered"] == 1
        assert manifest["capture"]["legacy_bytes"] == "not_captured"


@pytest.mark.parametrize("position,value", [(0, "wrong-db"), (1, 170011), (2, "off"),
    (3, "read committed"), (4, "on"), (5, False)])
def test_wrong_identity_or_filtered_visibility_never_produces_capture(prepared, position, value):
    root, connection, client, _, arguments = prepared
    identity = list(connection.identity)
    identity[position] = value
    connection.identity = tuple(identity)
    with pytest.raises(BackupError, match="visibility"):
        capture.capture_backup(root / "invalid", **arguments)
    assert connection.closed and connection.rolled_back
    assert not client.reads and not list((root / "invalid").glob("*-manifest.json"))


@pytest.mark.parametrize("failure", ["bad-reference", "publication-mismatch", "wrong-schema", "bad-snapshot"])
def test_reference_contract_failures_stop_before_dump_and_objects(prepared, failure, monkeypatch):
    root, connection, client, _, arguments = prepared
    if failure == "bad-reference":
        connection.bad_references = 1
    elif failure == "publication-mismatch":
        connection.bad_publications = 1
    elif failure == "wrong-schema":
        connection.revision = "unrecognized"
    else:
        connection.snapshot = "not-a-snapshot --password=forbidden"
    monkeypatch.setattr(capture, "_run_dump", lambda *args: pytest.fail("Invalid contract must prevent native dump"))
    with pytest.raises(BackupError):
        capture.capture_backup(root / "contract", **arguments)
    assert connection.closed and not client.reads


@pytest.mark.parametrize("position,value", [(3, "../escape"), (4, "text/html"),
    (5, 0), (6, "invalid-hash"), (7, "local"), (8, "unknown")])
def test_invalid_object_descriptors_are_rejected(prepared, position, value):
    root, connection, client, _, arguments = prepared
    row = list(connection.rows[0])
    row[position] = value
    connection.rows = [tuple(row)]
    with pytest.raises(BackupError):
        capture.capture_backup(root / "descriptor", **arguments)
    assert connection.closed and not client.reads


def test_pending_orphan_is_preserved_as_metadata_without_invented_bytes(prepared):
    root, connection, client, descriptor, arguments = prepared
    row = list(connection.rows[0])
    row[0] = "f" * 32
    row[8] = "pending"
    connection.rows.append(tuple(row))
    report = capture.capture_backup(root / "pending", **arguments)
    assert report["inventory_counts"]["pending_objects"] == 1
    assert report["inventory_counts"]["ready_objects"] == 1
    assert client.reads == [descriptor.key]


@pytest.mark.parametrize("failure", ["count", "metadata", "bytes", "duplicate"])
def test_inventory_bounds_fail_without_partial_object_collection(prepared, failure):
    root, connection, client, _, arguments = prepared
    if failure == "count":
        connection.rows *= 2
        arguments["limits"] = replace(arguments["limits"], max_objects=1)
    elif failure == "metadata":
        connection.rows *= 2
        arguments["limits"] = replace(arguments["limits"], max_objects=1, max_metadata_rows=1)
    elif failure == "bytes":
        arguments["limits"] = replace(arguments["limits"], max_object_bytes=1)
    else:
        connection.rows *= 2
    with pytest.raises(BackupError):
        capture.capture_backup(root / "bound", **arguments)
    assert connection.closed and not client.reads


@pytest.mark.parametrize("damage", ["absent", "changed", "oversized"])
def test_missing_or_changed_s3_bytes_never_publish_complete_manifest(prepared, damage):
    root, connection, client, descriptor, arguments = prepared
    if damage == "absent":
        client.contents.clear()
    elif damage == "changed":
        client.contents[descriptor.key] = b"x" * descriptor.byte_size
    else:
        client.contents[descriptor.key] += b"extra"
    with pytest.raises(BackupError) as error:
        capture.capture_backup(root / "damaged", **arguments)
    assert "credential" not in str(error.value) and "customer" not in str(error.value)
    assert connection.closed and not list((root / "damaged").glob("*-manifest.json"))


def test_dump_failure_closes_exporter_without_fetching_objects(prepared, monkeypatch):
    root, connection, client, _, arguments = prepared
    def fail(*args):
        raise RuntimeError("private-database-password")
    monkeypatch.setattr(capture, "_run_dump", fail)
    with pytest.raises(BackupError) as error:
        capture.capture_backup(root / "dump-failure", **arguments)
    assert "private-database-password" not in str(error.value)
    assert connection.closed and connection.rolled_back and not client.reads


def test_native_child_environment_excludes_application_secrets(tmp_path, monkeypatch):
    for name in ("BACKUP_ENCRYPTION_KEY", "STRIPE_SECRET_KEY", "OBJECT_STORAGE_S3_SECRET_KEY", "PGSERVICE"):
        monkeypatch.setenv(name, "do-not-inherit")
    environment = capture._native_environment(
        "postgresql://operator:database-password@db.example.invalid/expected?sslmode=verify-full", "expected", tmp_path)
    assert environment["PGPASSWORD"] == "database-password"
    assert environment["PGOPTIONS"] == "-c default_transaction_read_only=on -c row_security=off"
    assert all(name not in environment for name in (
        "BACKUP_ENCRYPTION_KEY", "STRIPE_SECRET_KEY", "OBJECT_STORAGE_S3_SECRET_KEY", "PGSERVICE", "PATH"))


@pytest.mark.parametrize("url", ["postgresql://a:b@remote.invalid/db?sslmode=disable",
    "postgresql://a:b@remote.invalid/db?options=untrusted", "postgresql://a:b@remote.invalid/other",
    "postgresql://a:b@remote.invalid/db?sslmode=require&sslmode=disable"])
def test_connection_overrides_or_wrong_database_are_rejected(tmp_path, url):
    with pytest.raises(BackupError):
        capture._native_environment(url, "db", tmp_path)


def test_dump_stream_never_writes_past_the_bound(tmp_path):
    errors = []
    destination = tmp_path / "bounded.dump"
    capture._copy_dump(io.BytesIO(b"x" * (200 * 1024)), destination, 100 * 1024, errors)
    assert errors == [True]
    assert destination.stat().st_size <= 100 * 1024


def test_deadline_and_missing_key_fail_closed(prepared, monkeypatch):
    root, connection, _, _, arguments = prepared
    with pytest.raises(BackupError, match="time bound"):
        capture._remaining(time.monotonic() - 1)
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY")
    with pytest.raises(BackupError, match="encryption key"):
        capture.capture_backup(root / "no-key", **arguments)
    assert not connection.statements and not (root / "no-key").exists()


def test_cli_partial_exit_and_cleanup_failure_never_leak_provider_text(prepared, monkeypatch, capsys):
    root, connection, client, _, arguments = prepared
    connection.legacy = (39, 1)
    monkeypatch.setenv("BACKUP_DATABASE_URL", arguments["database_url"])
    monkeypatch.setattr(capture, "_configured_store", lambda: arguments["object_store"])
    cli = ["--expected-database", arguments["expected_database"], "--expected-revision", arguments["expected_revision"],
           "--pg-bin", str(arguments["pg_bin"])]
    assert capture.main([*cli, "--output", str(root / "partial-cli")]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "partial_legacy_references"
    client.close_error = True
    connection.closed = connection.rolled_back = False
    assert capture.main([*cli, "--output", str(root / "cleanup-cli")]) == 1
    assert json.loads(capsys.readouterr().out) == {"status": "failed", "error": "backup_capture_failed"}


@pytest.mark.parametrize("legacy", [(0, 0), (39, 1)])
def test_new_capture_manifest_survives_existing_remote_transport(prepared, legacy):
    from scripts.backup_remote import fetch_backup, publish_backup
    from tests.test_backup_remote import Store
    root, connection, _, _, arguments = prepared
    connection.legacy = legacy
    captured = capture.capture_backup(root / "transport-capture", **arguments)
    remote = Store()
    published = publish_backup(Path(captured["manifest"]), client=remote, bucket="synthetic-backup")
    assert published["coverage"]["cross_resource_consistency"] == "not_attested"
    output = root / "transport-quarantine"
    fetch_backup(captured["snapshot_id"], output, client=remote, bucket="synthetic-backup")
    with verified_artifacts(output / (captured["snapshot_id"] + "-manifest.json")) as (manifest, _):
        assert manifest["capture"]["status"] == captured["status"]
        assert manifest["capture"]["inventory_counts"]["legacy_plan_references_uncovered"] == legacy[0]
        assert manifest["capture"]["serving_authorized"] is False
