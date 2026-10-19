"""Explicit database/object snapshots and guarded restore operations.

PostgreSQL credentials stay in child-process environment, never argv/logs.
No source means failure. Retention is deliberately an operator policy rather
than an implicit deletion. Encryption keys are supplied through environment.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import subprocess
import tempfile
from urllib.parse import parse_qs, unquote, urlsplit
import zipfile

MAGIC = b"MBACKUP1"


def manifest_authentication(manifest: dict, key: bytes) -> str:
    """Bind artifact roles, hashes and metadata with a separate derived key."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    authentication_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
        info=b"MetodoBase backup manifest authentication v1").derive(key)
    payload = {name: value for name, value in manifest.items() if name != "manifest_mac"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(authentication_key, canonical, hashlib.sha256).hexdigest()


class BackupError(RuntimeError):
    """Public operational error without provider credentials or record data."""


def checksum(path: Path) -> str:
    """Return SHA256 of a file without loading a database into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def encryption_key() -> bytes | None:
    """Decode the operator's base64 256-bit key without logging its value."""
    value = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    if not value:
        return None
    try:
        key = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise BackupError("Invalid backup encryption key") from None
    if len(key) != 32:
        raise BackupError("Backup encryption requires a 256-bit key")
    return key


def encrypt(source: Path, destination: Path, key: bytes) -> None:
    """Stream AES-256-GCM; authenticate header and artifact on restoration."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    nonce = os.urandom(12)
    encoder = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encoder.authenticate_additional_data(MAGIC)
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        outgoing.write(MAGIC + nonce)
        for block in iter(lambda: incoming.read(1024 * 1024), b""):
            outgoing.write(encoder.update(block))
        outgoing.write(encoder.finalize())
        outgoing.write(encoder.tag)


def decrypt(source: Path, destination: Path, key: bytes) -> None:
    """Verify GCM before callers can restore any decrypted data."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    size = source.stat().st_size
    if size < len(MAGIC) + 12 + 16:
        raise BackupError("Encrypted artifact is truncated")
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        if incoming.read(len(MAGIC)) != MAGIC:
            raise BackupError("Unknown backup encryption format")
        nonce = incoming.read(12)
        incoming.seek(-16, os.SEEK_END)
        tag = incoming.read(16)
        decoder = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        decoder.authenticate_additional_data(MAGIC)
        remaining = size - len(MAGIC) - 12 - 16
        incoming.seek(len(MAGIC) + 12)
        try:
            while remaining:
                block = incoming.read(min(1024 * 1024, remaining))
                if not block:
                    raise BackupError("Encrypted artifact is truncated")
                remaining -= len(block)
                outgoing.write(decoder.update(block))
            outgoing.write(decoder.finalize())
        except InvalidTag:
            raise BackupError("Backup authentication failed") from None


def pg_environment(url: str, expected_database: str) -> dict[str, str]:
    """Validate an explicit PostgreSQL destination and prepare libpq env."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2", "postgresql+psycopg"}:
        raise BackupError("Expected a PostgreSQL URL")
    database = unquote(parsed.path.lstrip("/"))
    if not expected_database or database != expected_database:
        raise BackupError("Database name does not match the explicit expected target")
    if not parsed.hostname or not database or not parsed.username:
        raise BackupError("Database connection details are incomplete")
    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    env.update({"PGHOST": parsed.hostname, "PGPORT": str(parsed.port or 5432),
        "PGDATABASE": database, "PGUSER": unquote(parsed.username),
        "PGPASSWORD": unquote(parsed.password or ""), "PGCONNECT_TIMEOUT": "10"})
    options = parse_qs(parsed.query)
    for option, key in {"sslmode": "PGSSLMODE", "sslrootcert": "PGSSLROOTCERT"}.items():
        if option in options:
            env[key] = options[option][0]
    return env


def _pg_run(name: str, arguments: list[str], env: dict[str, str], pg_bin: Path | None) -> None:
    executable = str(pg_bin / name) if pg_bin else name
    try:
        result = subprocess.run([executable, *arguments], env=env, capture_output=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise BackupError(f"{name} unavailable or timed out") from None
    if result.returncode:
        # libpq stderr can contain connection strings; retain only exit status.
        raise BackupError(f"{name} failed with exit status {result.returncode}")


def _archive_objects(root: Path, output: Path) -> list[dict]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise BackupError("Object source must be a directory")
    objects = []
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise BackupError("Object source contains a link outside the snapshot")
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                before = checksum(path)
                archive.write(path, relative)
                if checksum(path) != before:
                    raise BackupError("An object changed during backup; retry the snapshot")
                objects.append({"path": relative, "sha256": before, "bytes": path.stat().st_size})
    return objects


def create_backup(output: Path, *, database_url: str | None = None,
    expected_database: str = "", sqlite_sources: tuple[Path, ...] = (),
    objects_root: Path | None = None, pg_bin: Path | None = None,
    allow_plaintext_local: bool = False) -> Path:
    """Create a complete manifest last; an incomplete run never reports success.

    PostgreSQL uses pg_dump custom format; SQLite uses its online backup API.
    An explicit objects root is required when the deployment uses local files.
    Plaintext is restricted to isolated tests, never the production default.
    """
    if not database_url and not sqlite_sources:
        raise BackupError("No database source configured; no backup was created")
    key = encryption_key()
    if key is None and not allow_plaintext_local:
        raise BackupError("Configure BACKUP_ENCRYPTION_KEY before backing up")
    pg_env = pg_environment(database_url, expected_database) if database_url else None
    if allow_plaintext_local and pg_env and (pg_env["PGHOST"] not in {"127.0.0.1", "localhost", "::1"}
        or not expected_database.startswith("metodobase_test_")):
        raise BackupError("Plaintext mode is limited to isolated local test databases")
    for source in sqlite_sources:
        if not source.is_file():
            raise BackupError("A configured SQLite source is missing")
    output = output.resolve()
    if objects_root is not None and output.is_relative_to(objects_root.resolve()):
        raise BackupError("Backup output cannot be inside the object source")
    output.mkdir(parents=True, exist_ok=True)
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    manifest = {"format": 1, "snapshot_id": snapshot_id, "created_at": datetime.now(timezone.utc).isoformat(),
        "encryption": "AES-256-GCM" if key else "none-local-test", "artifacts": [], "objects": []}
    with tempfile.TemporaryDirectory(prefix="mb-backup-") as temporary:
        temp = Path(temporary)
        artifacts = []
        if pg_env:
            dump = temp / "postgres.dump"
            _pg_run("pg_dump", ["--format=custom", "--no-owner", "--no-acl", "--file", str(dump)], pg_env, pg_bin)
            _pg_run("pg_restore", ["--list", str(dump)], pg_env, pg_bin)
            artifacts.append(("postgres", dump))
        for index, source in enumerate(sqlite_sources):
            dump = temp / f"sqlite-{index}.db"
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as live, closing(sqlite3.connect(dump)) as copy:
                live.backup(copy)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise BackupError("SQLite snapshot integrity check failed")
            artifacts.append(("sqlite", dump))
        if objects_root is not None:
            archive = temp / "objects.zip"
            manifest["objects"] = _archive_objects(objects_root, archive)
            artifacts.append(("objects", archive))
        for kind, artifact in artifacts:
            name = snapshot_id + "-" + artifact.name + (".enc" if key else "")
            destination = output / name
            if key:
                encrypt(artifact, destination, key)
                verified = temp / (artifact.name + ".verified")
                decrypt(destination, verified, key)
                if checksum(verified) != checksum(artifact):
                    raise BackupError("Encrypted snapshot verification failed")
            else:
                shutil.copyfile(artifact, destination)
            manifest["artifacts"].append({"kind": kind, "file": name,
                "sha256": checksum(destination), "content_sha256": checksum(artifact), "bytes": destination.stat().st_size})
    path = output / (snapshot_id + "-manifest.json")
    if key:
        manifest["authentication"] = "HMAC-SHA256-HKDF-v1"
        manifest["manifest_mac"] = manifest_authentication(manifest, key)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@contextmanager
def verified_artifacts(manifest_path: Path, *, allow_plaintext_local: bool = False):
    """Authenticate every artifact before any restore side effect."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BackupError("Backup manifest is unreadable") from None
    if manifest.get("format") != 1 or not manifest.get("artifacts"):
        raise BackupError("Unsupported or empty backup manifest")
    key = encryption_key()
    encryption = manifest.get("encryption")
    if encryption not in {"AES-256-GCM", "none-local-test"}:
        raise BackupError("Unsupported backup encryption format")
    encrypted = encryption == "AES-256-GCM"
    if encrypted and key is None:
        raise BackupError("The snapshot decryption key is required")
    if encrypted:
        if manifest.get("authentication") != "HMAC-SHA256-HKDF-v1" or not isinstance(manifest.get("manifest_mac"), str):
            raise BackupError("Backup manifest authentication is required")
        if not hmac.compare_digest(manifest["manifest_mac"], manifest_authentication(manifest, key)):
            raise BackupError("Backup manifest authentication failed")
    elif not allow_plaintext_local:
        raise BackupError("Plaintext snapshots require explicit local-test mode")
    with tempfile.TemporaryDirectory(prefix="mb-restore-") as temporary:
        result = {}
        for artifact in manifest["artifacts"]:
            name = artifact["file"]
            if Path(name).name != name:
                raise BackupError("Artifact path is outside the snapshot")
            path = manifest_path.parent / name
            if not path.is_file() or checksum(path) != artifact["sha256"]:
                raise BackupError("Backup artifact checksum mismatch")
            plain = Path(temporary) / name
            if encrypted:
                decrypt(path, plain, key)
            else:
                shutil.copyfile(path, plain)
            if checksum(plain) != artifact["content_sha256"]:
                raise BackupError("Backup content checksum mismatch")
            result.setdefault(artifact["kind"], []).append(plain)
        yield manifest, result


def restore_backup(manifest_path: Path, *, database_url: str | None = None,
    expected_database: str = "", sqlite_destination: Path | None = None,
    objects_destination: Path | None = None, pg_bin: Path | None = None,
    allow_plaintext_local: bool = False) -> dict:
    """Restore only into empty explicit targets; no DROP/--clean/overwrite.

    PostgreSQL restoration is a single transaction. Objects are validated in a
    staging directory first. Database and filesystem are separate resources;
    a filesystem promotion failure is reported, never called full success.
    """
    with verified_artifacts(manifest_path, allow_plaintext_local=allow_plaintext_local) as (manifest, artifacts):
        pg_env = pg_environment(database_url, expected_database) if database_url else None
        if manifest["encryption"] == "none-local-test" and pg_env and (
            pg_env["PGHOST"] not in {"localhost", "127.0.0.1", "::1"}
            or not expected_database.startswith("metodobase_test_")):
            raise BackupError("Plaintext restores are limited to isolated local test databases")
        if "postgres" in artifacts and pg_env is None:
            raise BackupError("PostgreSQL restore destination is required")
        if "sqlite" in artifacts and (sqlite_destination is None or len(artifacts["sqlite"]) != 1):
            raise BackupError("Restore exactly one SQLite source to an explicit destination")
        if sqlite_destination and sqlite_destination.exists():
            raise BackupError("SQLite restore destination already exists")
        if "objects" in artifacts and objects_destination is None:
            raise BackupError("Objects restore destination is required")
        if objects_destination and objects_destination.exists() and any(objects_destination.iterdir()):
            raise BackupError("Object restore destination must be empty")
        if pg_env:
            import psycopg2
            try:
                with closing(psycopg2.connect(host=pg_env["PGHOST"], port=pg_env["PGPORT"], dbname=pg_env["PGDATABASE"],
                    user=pg_env["PGUSER"], password=pg_env["PGPASSWORD"], connect_timeout=10,
                    sslmode=pg_env.get("PGSSLMODE", "prefer"),
                    **({"sslrootcert": pg_env["PGSSLROOTCERT"]} if "PGSSLROOTCERT" in pg_env else {}))) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema'))")
                        if cursor.fetchone()[0]:
                            raise BackupError("PostgreSQL restore destination is not empty")
            except BackupError:
                raise
            except Exception:
                raise BackupError("Cannot verify the PostgreSQL restore destination") from None
        with tempfile.TemporaryDirectory(prefix="mb-objects-restore-") as temporary:
            stage = Path(temporary)
            if "objects" in artifacts:
                expected = {item["path"]: item for item in manifest["objects"]}
                with zipfile.ZipFile(artifacts["objects"][0]) as archive:
                    if set(archive.namelist()) != set(expected):
                        raise BackupError("Object manifest does not match the archive")
                    for entry in archive.infolist():
                        relative = PurePosixPath(entry.filename)
                        if relative.is_absolute() or ".." in relative.parts or "\\" in entry.filename or ":" in entry.filename:
                            raise BackupError("Unsafe object path in archive")
                        target = stage.joinpath(*relative.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(entry) as incoming, target.open("xb") as outgoing:
                            remaining = expected[entry.filename]["bytes"]
                            if remaining < 0 or remaining != entry.file_size:
                                raise BackupError("Object archive size does not match the manifest")
                            while remaining:
                                block = incoming.read(min(1024 * 1024, remaining))
                                if not block:
                                    raise BackupError("Object archive is truncated")
                                outgoing.write(block)
                                remaining -= len(block)
                        if checksum(target) != expected[entry.filename]["sha256"]:
                            raise BackupError("Restored object checksum mismatch")
            if "postgres" in artifacts:
                _pg_run("pg_restore", ["--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
                    "--dbname", pg_env["PGDATABASE"], str(artifacts["postgres"][0])], pg_env, pg_bin)
            if "sqlite" in artifacts:
                sqlite_destination.parent.mkdir(parents=True, exist_ok=True)
                with artifacts["sqlite"][0].open("rb") as incoming, sqlite_destination.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
            if objects_destination is not None:
                shutil.copytree(stage, objects_destination, dirs_exist_ok=True)
        return {"snapshot_id": manifest["snapshot_id"], "restored": sorted(artifacts), "objects": len(manifest["objects"])}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["backup", "restore", "verify"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--database-env", default="BACKUP_DATABASE_URL")
    parser.add_argument("--expected-database", default="")
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--objects", type=Path)
    parser.add_argument("--sqlite", type=Path, action="append", default=[])
    parser.add_argument("--allow-plaintext-local-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "backup":
            if args.output is None:
                raise BackupError("Backup output directory is required")
            path = create_backup(args.output, database_url=os.environ.get(args.database_env),
                expected_database=args.expected_database, sqlite_sources=tuple(p.resolve() for p in args.sqlite),
                objects_root=args.objects, pg_bin=args.pg_bin, allow_plaintext_local=args.allow_plaintext_local_test)
            print(json.dumps({"manifest": str(path), "status": "verified_backup"}))
        elif args.operation == "verify":
            if args.manifest is None:
                raise BackupError("Backup manifest is required")
            with verified_artifacts(args.manifest, allow_plaintext_local=args.allow_plaintext_local_test) as (manifest, artifacts):
                print(json.dumps({"snapshot_id": manifest["snapshot_id"], "verified_artifacts": len(artifacts)}))
        else:
            if args.manifest is None:
                raise BackupError("Backup manifest is required")
            print(json.dumps(restore_backup(args.manifest, database_url=os.environ.get(args.database_env),
                expected_database=args.expected_database, sqlite_destination=args.sqlite[0] if args.sqlite else None,
                objects_destination=args.objects, pg_bin=args.pg_bin, allow_plaintext_local=args.allow_plaintext_local_test)))
        return 0
    except (BackupError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
            "message": str(exc) if isinstance(exc, BackupError) else "Backup operation failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
