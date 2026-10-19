"""Backup/restore acceptance on synthetic SQLite/objects and failure paths."""
import base64
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.backup_restore import BackupError, create_backup, main, restore_backup, verified_artifacts


@pytest.fixture
def synthetic_source(tmp_path):
    database = tmp_path / "source.db"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE synthetic (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO synthetic VALUES (1, 'synthetic-only')")
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / "plan.pdf").write_bytes(b"%PDF-1.4 synthetic")
    (objects / "logo.png").write_bytes(b"synthetic-logo")
    return database, objects


def test_backup_without_source_and_missing_source_fail(tmp_path):
    with pytest.raises(BackupError, match="No database source"):
        create_backup(tmp_path / "out", allow_plaintext_local=True)
    with pytest.raises(BackupError, match="source is missing"):
        create_backup(tmp_path / "out", sqlite_sources=(tmp_path / "absent.db",), allow_plaintext_local=True)
    assert main(["backup", "--output", str(tmp_path / "out")]) == 1


def test_encrypted_restore_preserves_database_objects_and_rejects_overwrite(tmp_path, synthetic_source, monkeypatch):
    database, objects = synthetic_source
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    manifest = create_backup(tmp_path / "backup", sqlite_sources=(database,), objects_root=objects)
    restored = tmp_path / "restored.db"
    destination = tmp_path / "restored-objects"
    report = restore_backup(manifest, sqlite_destination=restored, objects_destination=destination)
    assert report["restored"] == ["objects", "sqlite"]
    assert report["objects"] == 2
    with sqlite3.connect(restored) as conn:
        assert conn.execute("SELECT * FROM synthetic").fetchall() == [(1, "synthetic-only")]
    assert (destination / "plan.pdf").read_bytes() == (objects / "plan.pdf").read_bytes()
    with pytest.raises(BackupError, match="already exists"):
        restore_backup(manifest, sqlite_destination=restored, objects_destination=destination)


def test_tampered_or_wrong_key_backup_never_restores(tmp_path, synthetic_source, monkeypatch):
    database, _ = synthetic_source
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    manifest = create_backup(tmp_path / "backup", sqlite_sources=(database,))
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(reversed(range(32)))).decode())
    destination = tmp_path / "restored.db"
    with pytest.raises(BackupError, match="authentication failed"):
        restore_backup(manifest, sqlite_destination=destination)
    assert not destination.exists()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    data = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = manifest.parent / data["artifacts"][0]["file"]
    artifact.write_bytes(artifact.read_bytes() + b"tampered")
    with pytest.raises(BackupError, match="checksum mismatch"):
        with verified_artifacts(manifest):
            pytest.fail("Tampering must prevent restore")


def test_plaintext_remote_database_and_wrong_target_are_rejected(tmp_path):
    for url, name in [("postgresql://synthetic:synthetic@example.invalid/metodobase_test_db", "metodobase_test_db"),
        ("postgresql://synthetic:synthetic@127.0.0.1/production", "metodobase_test_db")]:
        with pytest.raises(BackupError):
            create_backup(tmp_path / "out", database_url=url, expected_database=name, allow_plaintext_local=True)


def test_encryption_is_required_by_default(tmp_path, synthetic_source, monkeypatch):
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    with pytest.raises(BackupError, match="ENCRYPTION_KEY"):
        create_backup(tmp_path / "out", sqlite_sources=(synthetic_source[0],))


def test_manifest_tampering_and_encryption_downgrade_fail_before_restore(tmp_path, synthetic_source, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    manifest = create_backup(tmp_path / "backup", sqlite_sources=(synthetic_source[0],))
    original = json.loads(manifest.read_text(encoding="utf-8"))
    tampered = dict(original, snapshot_id="substituted")
    manifest.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(BackupError, match="manifest authentication failed"):
        restore_backup(manifest, sqlite_destination=tmp_path / "restored.db")
    tampered = dict(original, encryption="none-local-test")
    manifest.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(BackupError, match="explicit local-test"):
        restore_backup(manifest, sqlite_destination=tmp_path / "restored.db")
    assert not (tmp_path / "restored.db").exists()
