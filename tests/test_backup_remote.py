"""Remote snapshot publication failure/restore controls using isolated storage."""
import base64
import io
import json
import sqlite3

import pytest
from botocore.exceptions import ClientError

from scripts import backup_remote as remote
from scripts.backup_restore import BackupError, create_backup, restore_backup


class Store:
    def __init__(self):
        self.objects = {}
        self.writes = []
        self.public = False
        self.grants = []
        self.fail_at = None
        self.corrupt_read = None

    def get_bucket_policy_status(self, **kwargs):
        return {"PolicyStatus": {"IsPublic": self.public}}

    def get_bucket_acl(self, **kwargs):
        return {"Grants": self.grants}

    def get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        value = self.objects[Key]
        if Key == self.corrupt_read:
            value = bytes([value[0] ^ 1]) + value[1:]
        return {"Body": io.BytesIO(value), "ContentLength": len(value)}

    def put_object(self, *, Bucket, Key, Body, ContentLength, ContentType, IfNoneMatch, Metadata):
        assert IfNoneMatch == "*"
        assert ContentType == "application/octet-stream"
        assert set(Metadata) == {"sha256"}
        if self.fail_at and Key.endswith(self.fail_at):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "secret-provider-detail"}}, "PutObject")
        if Key in self.objects:
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        data = Body.read()
        assert len(data) == ContentLength
        self.objects[Key] = data
        self.writes.append(Key)
        return {}

    def close(self):
        pass


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO sample VALUES (1, 'synthetic-only')")
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / "synthetic.pdf").write_bytes(b"%PDF synthetic-only")
    manifest = create_backup(tmp_path / "snapshot", sqlite_sources=(source,), objects_root=objects)
    return manifest, json.loads(manifest.read_text(encoding="utf8"))


def publish(snapshot, store):
    return remote.publish_backup(snapshot[0], client=store, bucket="synthetic-bucket")


def test_roundtrip_preserves_database_and_objects_without_serving(snapshot, tmp_path):
    store = Store()
    published = publish(snapshot, store)
    assert published["status"] == "verified_remote_backup"
    assert published["scheduled"] is False
    assert published["coverage"]["cross_resource_consistency"] == "not_attested"
    assert store.writes[-1].endswith("complete.json")
    assert all(b"synthetic-only" not in value for value in store.objects.values())
    output = tmp_path / "quarantine"
    result = remote.fetch_backup(published["snapshot_id"], output, client=store, bucket="synthetic-bucket")
    assert result["serving"] is False and result["restored_database"] is False
    recovered = output / (published["snapshot_id"] + "-manifest.json")
    restored = tmp_path / "restored.db"
    restore_backup(recovered, sqlite_destination=restored, objects_destination=tmp_path / "recovered-objects")
    with sqlite3.connect(restored) as conn:
        assert conn.execute("SELECT * FROM sample").fetchall() == [(1, "synthetic-only")]
    assert (tmp_path / "recovered-objects" / "synthetic.pdf").read_bytes() == b"%PDF synthetic-only"


def test_retry_is_byte_identical_and_does_not_overwrite(snapshot):
    store = Store()
    first = publish(snapshot, store)
    preserved = dict(store.objects)
    writes = list(store.writes)
    assert publish(snapshot, store) == first
    assert store.objects == preserved and store.writes == writes


@pytest.mark.parametrize("failure", ["objects.zip.enc", "manifest.json.enc", "complete.json"])
def test_partial_publication_has_no_completion_and_retry_recovers(snapshot, failure):
    store = Store()
    store.fail_at = failure
    with pytest.raises(ClientError):
        publish(snapshot, store)
    assert not any(key.endswith("complete.json") for key in store.objects)
    retained = dict(store.objects)
    store.fail_at = None
    assert publish(snapshot, store)["status"] == "verified_remote_backup"
    assert all(store.objects[key] == value for key, value in retained.items())


def test_corrupt_readback_prevents_completion(snapshot):
    store = Store()
    store.corrupt_read = "backups/metodobase/" + snapshot[1]["snapshot_id"] + "/" + snapshot[1]["artifacts"][0]["file"]
    with pytest.raises(BackupError, match="readback"):
        publish(snapshot, store)
    assert not any(key.endswith("complete.json") for key in store.objects)


def test_tampered_local_snapshot_has_no_storage_writes(snapshot):
    manifest, data = snapshot
    path = manifest.parent / data["artifacts"][0]["file"]
    path.write_bytes(path.read_bytes() + b"tamper")
    store = Store()
    with pytest.raises(BackupError, match="checksum|changed"):
        publish(snapshot, store)
    assert store.objects == {} and store.writes == []


def test_original_mutation_after_verification_cannot_change_published_snapshot(snapshot, tmp_path):
    manifest, data = snapshot
    original_bytes = manifest.read_bytes()
    original_artifact = manifest.parent / data["artifacts"][0]["file"]
    store = Store()
    original_privacy = store.get_bucket_policy_status

    def mutate_originals(**kwargs):
        original_artifact.write_bytes(b"mutated-after-authentication")
        manifest.write_bytes(b"mutated-original-manifest")
        return original_privacy(**kwargs)

    store.get_bucket_policy_status = mutate_originals
    published = publish(snapshot, store)
    store.get_bucket_policy_status = original_privacy
    output = tmp_path / "stable-quarantine"
    remote.fetch_backup(published["snapshot_id"], output, client=store, bucket="synthetic-bucket")
    assert (output / (published["snapshot_id"] + "-manifest.json")).read_bytes() == original_bytes
    restored = tmp_path / "stable.db"
    restore_backup(output / (published["snapshot_id"] + "-manifest.json"), sqlite_destination=restored,
                   objects_destination=tmp_path / "stable-objects")
    with sqlite3.connect(restored) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("synthetic-only",)


def test_staged_mutation_during_upload_prevents_completion(snapshot, monkeypatch):
    store = Store()
    original = remote._put_new

    def mutate_before_upload(client, bucket, key, source):
        if key.endswith("sqlite-0.db.enc"):
            source.write_bytes(b"x" * source.stat().st_size)
        return original(client, bucket, key, source)

    monkeypatch.setattr(remote, "_put_new", mutate_before_upload)
    with pytest.raises(BackupError, match="readback"):
        publish(snapshot, store)
    assert not any(key.endswith("complete.json") for key in store.objects)


@pytest.mark.parametrize("condition", ["public-policy", "public-acl"])
def test_public_destination_is_rejected(snapshot, condition):
    store = Store()
    if condition == "public-policy":
        store.public = True
    else:
        store.grants = [{"Grantee": {"URI": "http://acs.amazonaws.com/groups/global/AllUsers"}}]
    with pytest.raises(BackupError, match="privacy|public"):
        publish(snapshot, store)
    assert store.writes == []


def test_wrong_key_or_tampered_index_cannot_fetch(snapshot, tmp_path, monkeypatch):
    store = Store()
    published = publish(snapshot, store)
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(reversed(range(32)))).decode())
    with pytest.raises(BackupError, match="authentication"):
        remote.fetch_backup(published["snapshot_id"], tmp_path / "wrong-key", client=store, bucket="synthetic-bucket")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    key = store.writes[-1]
    index = json.loads(store.objects[key])
    index["coverage"]["cross_resource_consistency"] = "invented"
    store.objects[key] = json.dumps(index).encode()
    with pytest.raises(BackupError, match="authentication"):
        remote.fetch_backup(published["snapshot_id"], tmp_path / "tampered-index", client=store, bucket="synthetic-bucket")


@pytest.mark.parametrize("damage", ["missing", "modified"])
def test_completed_snapshot_with_damaged_artifact_is_rejected(snapshot, tmp_path, damage):
    store = Store()
    published = publish(snapshot, store)
    artifact = store.writes[0]
    if damage == "missing":
        del store.objects[artifact]
    else:
        store.objects[artifact] = b"x" * len(store.objects[artifact])
    with pytest.raises(BackupError, match="missing|integrity"):
        remote.fetch_backup(published["snapshot_id"], tmp_path / "damaged", client=store, bucket="synthetic-bucket")
    assert not list((tmp_path / "damaged").glob("*-manifest.json"))


def test_recovery_never_overwrites_existing_directory(snapshot, tmp_path):
    store = Store()
    published = publish(snapshot, store)
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "keep"
    sentinel.write_text("retain", encoding="ascii")
    with pytest.raises(FileExistsError):
        remote.fetch_backup(published["snapshot_id"], output, client=store, bucket="synthetic-bucket")
    assert sentinel.read_text(encoding="ascii") == "retain"


def test_bound_and_prefix_rejection_before_remote_writes(snapshot):
    store = Store()
    with pytest.raises(BackupError, match="byte bound"):
        remote.publish_backup(snapshot[0], client=store, bucket="synthetic-bucket", max_bytes=1024)
    with pytest.raises(BackupError, match="dedicated"):
        remote.publish_backup(snapshot[0], client=store, bucket="synthetic-bucket", prefix="customer-objects")
    assert store.writes == []


def test_cli_suppresses_provider_secrets(snapshot, monkeypatch, capsys):
    store = Store()
    store.fail_at = "complete.json"
    monkeypatch.setenv("BACKUP_S3_BUCKET", "synthetic-bucket")
    monkeypatch.setattr(remote, "_client", lambda: store)
    assert remote.main(["publish", "--manifest", str(snapshot[0])]) == 1
    output = capsys.readouterr().out
    assert json.loads(output) == {"status": "failed", "operation": "publish", "error": "backup_remote_operation_failed"}
    assert "secret-provider-detail" not in output and str(snapshot[0]) not in output


@pytest.mark.parametrize("operation_fails", [False, True])
def test_cli_cleanup_failure_is_private_and_never_reports_success(snapshot, monkeypatch, capsys, operation_fails):
    store = Store()
    if operation_fails:
        store.fail_at = "complete.json"

    def close_failure():
        raise RuntimeError("synthetic-private-cleanup-detail")

    store.close = close_failure
    monkeypatch.setenv("BACKUP_S3_BUCKET", "synthetic-bucket")
    monkeypatch.setattr(remote, "_client", lambda: store)
    assert remote.main(["publish", "--manifest", str(snapshot[0])]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {"status": "failed", "operation": "publish",
                                     "error": "backup_remote_operation_failed"}
    assert output.err == "" and "synthetic-private-cleanup-detail" not in output.out
    assert "verified_remote_backup" not in output.out


def test_database_only_coverage_is_explicit(snapshot, tmp_path):
    source = snapshot[0].parent.parent / "source.db"
    manifest = create_backup(tmp_path / "database-only", sqlite_sources=(source,))
    result = remote.publish_backup(manifest, client=Store(), bucket="synthetic-bucket")
    assert result["coverage"]["artifact_kinds"] == ["sqlite"]
    assert result["coverage"]["object_capture"] == "not_included"
