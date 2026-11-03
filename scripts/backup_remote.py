"""Publish/recover authenticated encrypted snapshots in a private S3 prefix.

This command does not capture remote objects, schedule jobs, delete retention,
restore a database, or authorize serving restored data. A completion index is
published last, only after reading every encrypted object back from storage.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backup_restore import (
    BackupError,
    checksum,
    decrypt,
    encrypt,
    encryption_key,
    manifest_authentication,
    verified_artifacts,
)

FORMAT = "metodobase-remote-backup-v1"
SNAPSHOT = re.compile(r"[0-9]{8}T[0-9]{12}Z\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
DEFAULT_LIMIT = 512 * 1024 * 1024
INDEX_LIMIT = 64 * 1024
PUBLIC_GROUPS = {
    "http://acs.amazonaws.com/groups/global/AllUsers",
    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
}


def _canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def _key() -> bytes:
    key = encryption_key()
    if key is None:
        raise BackupError("Backup encryption key is required")
    return key


def _prefix(prefix: str, snapshot_id: str) -> str:
    if not re.fullmatch(r"backups/metodobase(?:/[a-z0-9][a-z0-9_-]{0,63})?", prefix):
        raise BackupError("Use the dedicated backups/metodobase prefix")
    if not SNAPSHOT.fullmatch(snapshot_id):
        raise BackupError("Invalid snapshot identifier")
    return f"{prefix}/{snapshot_id}"


def _artifact_name(name: str, snapshot_id: str) -> bool:
    return bool(re.fullmatch(re.escape(snapshot_id)
        + r"-(?:postgres\.dump|objects\.zip|sqlite-[0-9]{1,3}\.db)\.enc", name))


def _error_code(error: Exception) -> str:
    response = getattr(error, "response", {})
    return str(response.get("Error", {}).get("Code", ""))


def _private_bucket(client, bucket: str) -> None:
    """Do not infer privacy from credentials or a private application URL."""
    policy = client.get_bucket_policy_status(Bucket=bucket)
    if policy.get("PolicyStatus", {}).get("IsPublic") is not False:
        raise BackupError("Backup bucket privacy is not verified")
    acl = client.get_bucket_acl(Bucket=bucket)
    if not isinstance(acl.get("Grants"), list) or any(
        grant.get("Grantee", {}).get("URI") in PUBLIC_GROUPS for grant in acl["Grants"]
    ):
        raise BackupError("Backup bucket has public or unknown access grants")


def _read(client, bucket: str, key: str, destination: Path, limit: int) -> bool:
    """Return False only for a missing object; bound bytes before local writes."""
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception as error:
        if _error_code(error) in {"NoSuchKey", "404", "NotFound"}:
            return False
        raise
    body = response["Body"]
    try:
        length = response.get("ContentLength")
        if type(length) is not int or length < 1 or length > limit:
            raise BackupError("Remote backup size is outside the configured bound")
        with destination.open("xb") as stream:
            remaining = length
            while remaining:
                block = body.read(min(1024 * 1024, remaining))
                if not block or len(block) > remaining:
                    raise BackupError("Remote backup is truncated or oversized")
                stream.write(block)
                remaining -= len(block)
            if body.read(1):
                raise BackupError("Remote backup is oversized")
    finally:
        body.close()
    return True


def _put_new(client, bucket: str, key: str, source: Path) -> bool:
    """Conditional create is essential: a retry must never overwrite a backup."""
    try:
        with source.open("rb") as stream:
            client.put_object(Bucket=bucket, Key=key, Body=stream,
                ContentLength=source.stat().st_size, ContentType="application/octet-stream",
                IfNoneMatch="*", Metadata={"sha256": checksum(source)})
        return True
    except Exception as error:
        if _error_code(error) in {"PreconditionFailed", "412"}:
            return False
        raise


def _same_remote(client, bucket: str, key: str, source: Path, directory: Path,
                 expected: dict | None = None) -> dict:
    expected_size, expected_hash = source.stat().st_size, checksum(source)
    if expected is not None and (expected_size != expected["bytes"] or expected_hash != expected["sha256"]):
        raise BackupError("Staged artifact differs from its authenticated descriptor")
    _put_new(client, bucket, key, source)
    destination = directory / (hashlib.sha256(key.encode()).hexdigest() + ".readback")
    if not _read(client, bucket, key, destination, expected_size):
        raise BackupError("Published backup object cannot be read back")
    if destination.stat().st_size != expected_size or checksum(destination) != expected_hash:
        raise BackupError("Remote backup readback does not match")
    return {"file": key.rsplit("/", 1)[1], "bytes": expected_size, "sha256": expected_hash}


def _stage_snapshot(manifest_path: Path, directory: Path, key: bytes, max_bytes: int) -> Path:
    """Copy bounded encrypted inputs, authenticate exact bytes, then leave originals alone."""
    if manifest_path.is_symlink() or manifest_path.stat().st_size > INDEX_LIMIT:
        raise BackupError("Manifest path or size is invalid")
    with manifest_path.open("rb") as stream:
        raw = stream.read(INDEX_LIMIT + 1)
    if len(raw) > INDEX_LIMIT:
        raise BackupError("Manifest changed beyond its byte bound")
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get("encryption") != "AES-256-GCM":
        raise BackupError("An encrypted authenticated snapshot is required")
    mac = manifest.get("manifest_mac")
    if not isinstance(mac, str) or not hmac.compare_digest(mac, manifest_authentication(manifest, key)):
        raise BackupError("Backup manifest authentication failed")
    snapshot = manifest.get("snapshot_id", "")
    _prefix("backups/metodobase", snapshot)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 64:
        raise BackupError("Snapshot artifact count is outside the bound")
    names = []
    total = len(raw) + 36
    for artifact in artifacts:
        name, size, digest = artifact.get("file"), artifact.get("bytes"), artifact.get("sha256")
        if (not isinstance(name, str) or not _artifact_name(name, snapshot)
            or type(size) is not int or size < 1 or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            raise BackupError("Invalid encrypted artifact descriptor")
        names.append(name)
        total += size
    if len(set(names)) != len(names) or total > max_bytes:
        raise BackupError("Snapshot exceeds the byte bound or contains duplicates")
    for artifact in artifacts:
        source = manifest_path.parent / artifact["file"]
        if source.is_symlink():
            raise BackupError("Snapshot contains a link")
        destination = directory / artifact["file"]
        with source.open("rb") as incoming, destination.open("xb") as outgoing:
            remaining = artifact["bytes"]
            while remaining:
                block = incoming.read(min(1024 * 1024, remaining))
                if not block:
                    raise BackupError("Snapshot changed during bounded staging")
                outgoing.write(block)
                remaining -= len(block)
            if incoming.read(1):
                raise BackupError("Snapshot changed during bounded staging")
        if checksum(destination) != artifact["sha256"]:
            raise BackupError("Backup artifact checksum mismatch")
    staged_manifest = directory / "snapshot-manifest.json"
    staged_manifest.write_bytes(raw)
    return staged_manifest


def publish_backup(manifest_path: Path, *, client, bucket: str,
                   prefix: str = "backups/metodobase", max_bytes: int = DEFAULT_LIMIT) -> dict:
    """Publish an existing verified snapshot, then an authenticated commit index."""
    key = _key()
    if type(max_bytes) is not int or not 1024 <= max_bytes <= 4 * 1024**3:
        raise BackupError("Invalid backup byte limit")
    with tempfile.TemporaryDirectory(prefix="mb-remote-publish-") as temporary:
        stage = Path(temporary)
        manifest_path = _stage_snapshot(manifest_path, stage, key, max_bytes)
        manifest_bytes = manifest_path.read_bytes()
        with verified_artifacts(manifest_path) as (manifest, _):
            snapshot = manifest["snapshot_id"]
            remote = _prefix(prefix, snapshot)
            artifacts = manifest["artifacts"]
            _private_bucket(client, bucket)
            entries = [_same_remote(client, bucket, remote + "/" + item["file"],
                       stage / item["file"], stage, expected=item) for item in artifacts]
            # Encrypt even the manifest, whose object paths may be sensitive.
            encrypted = stage / "manifest.json.enc"
            manifest_key = remote + "/manifest.json.enc"
            existing = _read(client, bucket, manifest_key, encrypted, INDEX_LIMIT + 64)
            if not existing:
                encrypt(manifest_path, encrypted, key)
                _put_new(client, bucket, manifest_key, encrypted)
                readback = stage / "manifest-readback.enc"
                if not _read(client, bucket, manifest_key, readback, INDEX_LIMIT + 64):
                    raise BackupError("Published manifest cannot be read back")
                encrypted = readback
            plain = stage / "manifest-verified.json"
            decrypt(encrypted, plain, key)
            if plain.read_bytes() != manifest_bytes:
                raise BackupError("Remote snapshot already contains a different manifest")
            entries.append({"file": "manifest.json.enc", "bytes": encrypted.stat().st_size,
                            "sha256": checksum(encrypted)})
            kinds = sorted({item["kind"] for item in artifacts})
            index = {"format": FORMAT, "snapshot_id": snapshot, "files": sorted(entries, key=lambda item: item["file"]),
                "coverage": {"artifact_kinds": kinds,
                    "object_capture": "local_tree" if "objects" in kinds else "not_included",
                    "cross_resource_consistency": "not_attested", "suppression_journal": "not_attested"},
                "authentication": "HMAC-SHA256-HKDF-v1"}
            index["manifest_mac"] = manifest_authentication(index, key)
            index_path = stage / "complete.json"
            index_path.write_bytes(_canonical(index))
            result = _same_remote(client, bucket, remote + "/complete.json", index_path, stage)
    return {"status": "verified_remote_backup", "snapshot_id": snapshot,
            "encrypted_files": len(entries), "bytes": sum(item["bytes"] for item in entries),
            "completion_sha256": result["sha256"], "coverage": index["coverage"],
            "retention_deletions": 0, "scheduled": False}


def fetch_backup(snapshot_id: str, output: Path, *, client, bucket: str,
                 prefix: str = "backups/metodobase", max_bytes: int = DEFAULT_LIMIT) -> dict:
    """Recover into a new local quarantine; never restore or serve a database."""
    key = _key()
    remote = _prefix(prefix, snapshot_id)
    if type(max_bytes) is not int or not 1024 <= max_bytes <= 4 * 1024**3:
        raise BackupError("Invalid backup byte limit")
    _private_bucket(client, bucket)
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    index_path = output / "complete.json"
    if not _read(client, bucket, remote + "/complete.json", index_path, INDEX_LIMIT):
        raise BackupError("Snapshot has no completed publication")
    index = json.loads(index_path.read_text(encoding="utf8"))
    if not isinstance(index, dict) or index.get("format") != FORMAT or index.get("snapshot_id") != snapshot_id:
        raise BackupError("Invalid remote snapshot index")
    mac = index.get("manifest_mac")
    if not isinstance(mac, str) or not hmac.compare_digest(mac, manifest_authentication(index, key)):
        raise BackupError("Remote snapshot index authentication failed")
    entries = index.get("files")
    if not isinstance(entries, list) or not 2 <= len(entries) <= 65:
        raise BackupError("Invalid remote snapshot file list")
    names = []
    total = 0
    for entry in entries:
        name, size, digest = entry.get("file"), entry.get("bytes"), entry.get("sha256")
        if (not isinstance(name, str) or (name != "manifest.json.enc" and not _artifact_name(name, snapshot_id))
            or type(size) is not int or size < 1 or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            raise BackupError("Invalid remote artifact descriptor")
        names.append(name)
        total += size
    if len(set(names)) != len(names) or names.count("manifest.json.enc") != 1 or total > max_bytes:
        raise BackupError("Remote snapshot is duplicate, incomplete or oversized")
    for entry in entries:
        path = output / entry["file"]
        if not _read(client, bucket, remote + "/" + entry["file"], path, entry["bytes"]):
            raise BackupError("A completed remote snapshot artifact is missing")
        if path.stat().st_size != entry["bytes"] or checksum(path) != entry["sha256"]:
            raise BackupError("Remote snapshot artifact integrity failed")
    manifest_path = output / (snapshot_id + "-manifest.json")
    decrypt(output / "manifest.json.enc", manifest_path, key)
    with verified_artifacts(manifest_path) as (manifest, _):
        if manifest["snapshot_id"] != snapshot_id or set(names) != {"manifest.json.enc", *[a["file"] for a in manifest["artifacts"]]}:
            raise BackupError("Remote index differs from the authenticated manifest")
    return {"status": "verified_local_quarantine", "snapshot_id": snapshot_id,
            "encrypted_files": len(entries), "coverage": index["coverage"], "serving": False,
            "restored_database": False}


def _client():
    import boto3
    from botocore.config import Config
    endpoint = os.environ.get("BACKUP_S3_ENDPOINT", "")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise BackupError("Configure an explicit HTTPS backup endpoint")
    names = ("BACKUP_S3_ACCESS_KEY", "BACKUP_S3_SECRET_KEY", "BACKUP_S3_BUCKET")
    if any(not os.environ.get(name) for name in names):
        raise BackupError("Backup destination configuration is incomplete")
    return boto3.client("s3", endpoint_url=endpoint,
        aws_access_key_id=os.environ["BACKUP_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["BACKUP_S3_SECRET_KEY"],
        region_name=os.environ.get("BACKUP_S3_REGION", "auto"),
        config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2},
                      s3={"addressing_style": "path"}))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("publish", "fetch"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--snapshot")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prefix", default="backups/metodobase")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args(argv)
    client = None
    failed = {"status": "failed", "operation": args.operation,
              "error": "backup_remote_operation_failed"}
    result, returncode = failed, 1
    try:
        _key()
        if args.operation == "publish" and args.manifest is None:
            raise BackupError("An encrypted snapshot manifest is required")
        if args.operation == "fetch" and (not args.snapshot or args.output is None):
            raise BackupError("A snapshot and new quarantine directory are required")
        client = _client()
        common = {"client": client, "bucket": os.environ["BACKUP_S3_BUCKET"],
                  "prefix": args.prefix, "max_bytes": args.max_bytes}
        result = (publish_backup(args.manifest, **common) if args.operation == "publish"
                  else fetch_backup(args.snapshot, args.output, **common))
        returncode = 0
    except Exception:  # noqa: BLE001 - never expose provider exceptions or secret-bearing URLs
        # Provider errors may contain URLs, credentials or customer object paths.
        result, returncode = failed, 1
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 - cleanup errors may also contain provider secrets
                result, returncode = failed, 1
    print(json.dumps(result, sort_keys=True))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
