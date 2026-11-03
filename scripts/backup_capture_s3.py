"""Capture one read-only PostgreSQL18 snapshot and its immutable S3 objects.

The output is encrypted and authenticated, never automatically published or
restored. Legacy file references are counted as uncovered and produce exit2.
No scheduler, retention deletion, provider write or serving is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backup_restore import (
    BackupError,
    checksum,
    decrypt,
    encrypt,
    encryption_key,
    manifest_authentication,
    pg_environment,
)
from web.storage.objects import ObjectDescriptor, authorize, verify
from web.storage.s3 import S3ObjectStore

REVISIONS = {"20261031_gym_equipment", "20261102_payment_refund_facts"}
SNAPSHOT = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{8}-[0-9]{1,10}\Z")
MANIFEST_LIMIT = 64 * 1024
REFERENCE_SQL = """
WITH object_references AS (
 SELECT gym_id, pdf_object_id AS object_id, 'plan_pdf' AS kind
 FROM public.planes_generados WHERE pdf_object_id IS NOT NULL
 UNION ALL
 SELECT gym_id, logo_object_id, 'gym_logo'
 FROM public.gym_profiles WHERE logo_object_id IS NOT NULL
 UNION ALL
 SELECT gym_id, source_object_id, 'plan_pdf'
 FROM public.client_plan_publications WHERE source_object_id IS NOT NULL
)
SELECT count(*), count(*) FILTER (WHERE o.id IS NULL OR o.status <> 'ready'
 OR o.storage_backend <> 's3' OR o.kind <> r.kind)
FROM object_references r LEFT JOIN public.stored_objects o
 ON o.gym_id = r.gym_id AND o.id = r.object_id
"""
PUBLICATION_SQL = """
SELECT count(*) FROM public.client_plan_publications p
LEFT JOIN public.stored_objects o ON o.gym_id = p.gym_id AND o.id = p.source_object_id
WHERE p.source_object_id IS NOT NULL AND
 (o.id IS NULL OR p.object_key IS DISTINCT FROM o.key
 OR p.content_type IS DISTINCT FROM o.content_type
 OR p.byte_size IS DISTINCT FROM o.byte_size
 OR p.sha256 IS DISTINCT FROM o.sha256
 OR p.storage_backend IS DISTINCT FROM o.storage_backend)
"""


@dataclass(frozen=True)
class CaptureLimits:
    max_objects: int = 128
    max_metadata_rows: int = 1024
    max_object_bytes: int = 256 * 1024 * 1024
    max_dump_bytes: int = 128 * 1024 * 1024
    timeout_seconds: int = 300

    def validate(self) -> None:
        for value, lower, upper in (
            (self.max_objects, 1, 512), (self.max_metadata_rows, 1, 10000),
            (self.max_object_bytes, 1, 1024**3), (self.max_dump_bytes, 1024, 1024**3),
            (self.timeout_seconds, 10, 900),
        ):
            if type(value) is not int or not lower <= value <= upper:
                raise BackupError("Capture limits are invalid")
        if self.max_metadata_rows < self.max_objects:
            raise BackupError("Capture metadata bound must cover the object bound")


def _remaining(deadline: float) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise BackupError("Capture exceeded its time bound")
    return value


def _native_environment(database_url: str, expected_database: str, temporary: Path) -> dict:
    parsed = urlsplit(database_url)
    options = parse_qs(parsed.query, keep_blank_values=True)
    if parsed.fragment or set(options) - {"sslmode", "sslrootcert"} or any(len(value) != 1 for value in options.values()):
        raise BackupError("Unsupported backup database connection options")
    selected = pg_environment(database_url, expected_database)
    sslmode = selected.get("PGSSLMODE", "require")
    local = selected["PGHOST"] in {"localhost", "127.0.0.1", "::1"}
    if sslmode not in {"require", "verify-ca", "verify-full"} and not (local and sslmode == "disable"):
        raise BackupError("Remote capture requires an encrypted PostgreSQL connection")
    environment = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR", "COMSPEC") if name in os.environ}
    allowed = {"PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGCONNECT_TIMEOUT", "PGSSLROOTCERT"}
    environment.update({name: value for name, value in selected.items() if name in allowed})
    environment.update(PGSSLMODE=sslmode, PGCLIENTENCODING="UTF8", LC_ALL="C", LANG="C",
        PGAPPNAME="metodobase_readonly_snapshot", PGOPTIONS="-c default_transaction_read_only=on -c row_security=off",
        TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary))
    return environment


def _connect(environment: dict):
    import psycopg2
    arguments = {"host": environment["PGHOST"], "port": environment["PGPORT"],
        "dbname": environment["PGDATABASE"], "user": environment["PGUSER"],
        "password": environment["PGPASSWORD"], "sslmode": environment["PGSSLMODE"],
        "connect_timeout": 10, "application_name": environment["PGAPPNAME"],
        "options": environment["PGOPTIONS"]}
    if "PGSSLROOTCERT" in environment:
        arguments["sslrootcert"] = environment["PGSSLROOTCERT"]
    return psycopg2.connect(**arguments)


def _executable(pg_bin: Path, name: str) -> Path:
    if not pg_bin.is_absolute() or not pg_bin.is_dir():
        raise BackupError("An explicit PostgreSQL18 binary directory is required")
    path = pg_bin / (name + (".exe" if os.name == "nt" else ""))
    if path.is_symlink() or not path.is_file():
        raise BackupError("A required PostgreSQL18 executable is unavailable")
    return path


def _native_identity(pg_bin: Path, environment: dict, deadline: float) -> dict:
    identity = {}
    for name in ("pg_dump", "pg_restore"):
        executable = _executable(pg_bin, name)
        result = subprocess.run([str(executable), "--version"], env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=min(10, _remaining(deadline)), check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        match = re.fullmatch(rb"(?:pg_dump|pg_restore) \(PostgreSQL\) (18(?:\.[0-9]+){1,2})(?: [^\r\n]{0,150})?\r?\n?", result.stdout)
        if result.returncode or len(result.stdout) > 512 or not match:
            raise BackupError("PostgreSQL18 client identity is not verified")
        identity[name] = {"version": match.group(1).decode("ascii"), "sha256": checksum(executable)}
    return identity


def _copy_dump(stream, destination: Path, maximum: int, errors: list) -> None:
    """A reader thread bounds stdout even on Windows anonymous pipes."""
    try:
        total = 0
        with destination.open("xb") as outgoing:
            while block := stream.read(64 * 1024):
                total += len(block)
                if total > maximum:
                    raise BackupError("PostgreSQL dump exceeds its byte bound")
                outgoing.write(block)
    except Exception:  # noqa: BLE001 - communicate a fixed classification to the owning thread
        errors.append(True)


def _run_dump(pg_bin: Path, environment: dict, snapshot: str, destination: Path,
              limits: CaptureLimits, deadline: float) -> None:
    if not SNAPSHOT.fullmatch(snapshot):
        raise BackupError("PostgreSQL exported snapshot identifier is invalid")
    executable = _executable(pg_bin, "pg_dump")
    process = subprocess.Popen([str(executable), "--format=custom", "--no-owner", "--no-acl",
        "--no-password", "--lock-wait-timeout=5s", "--snapshot=" + snapshot], env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    errors = []
    reader = threading.Thread(target=_copy_dump,
        args=(process.stdout, destination, limits.max_dump_bytes, errors), daemon=True)
    reader.start()
    try:
        while process.poll() is None:
            _remaining(deadline)
            if errors:
                raise BackupError("PostgreSQL dump stream failed or exceeded its byte bound")
            time.sleep(min(0.05, _remaining(deadline)))
        reader.join(timeout=min(5, _remaining(deadline)))
        if reader.is_alive() or errors or process.returncode:
            raise BackupError("PostgreSQL snapshot dump did not complete")
    finally:
        # Only this newly created child is stopped on timeout/stream failure.
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        reader.join(timeout=5)
        process.stdout.close()
    if not destination.is_file() or not 5 < destination.stat().st_size <= limits.max_dump_bytes:
        raise BackupError("PostgreSQL snapshot dump has an invalid size")
    with destination.open("rb") as stream:
        if stream.read(5) != b"PGDMP":
            raise BackupError("PostgreSQL snapshot archive signature is invalid")
    result = subprocess.run([str(_executable(pg_bin, "pg_restore")), "--list", str(destination)],
        env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=_remaining(deadline), check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        raise BackupError("PostgreSQL snapshot archive cannot be inspected")


def _inventory(cursor, expected_database: str, expected_revision: str, limits: CaptureLimits) -> tuple:
    cursor.execute("""SELECT current_database(), current_setting('server_version_num')::int,
        current_setting('transaction_read_only'), current_setting('transaction_isolation'),
        current_setting('row_security'), (SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user)""")
    name, server, readonly, isolation, row_security, global_reader = cursor.fetchone()
    if (name != expected_database or not 180000 <= server < 190000 or readonly != "on"
        or isolation != "repeatable read" or row_security != "off" or global_reader is not True):
        raise BackupError("Database identity, read-only snapshot or global visibility is not verified")
    cursor.execute("SELECT version_num FROM public.alembic_version")
    revisions = cursor.fetchall()
    if revisions != [(expected_revision,)] or expected_revision not in REVISIONS:
        raise BackupError("Capture source schema revision differs")
    cursor.execute("SELECT pg_export_snapshot()")
    snapshot = cursor.fetchone()[0]
    if not isinstance(snapshot, str) or not SNAPSHOT.fullmatch(snapshot):
        raise BackupError("PostgreSQL exported snapshot identifier is invalid")
    cursor.execute("""SELECT id,gym_id,kind,key,content_type,byte_size,sha256,storage_backend,status
        FROM public.stored_objects ORDER BY id LIMIT %s""", (limits.max_metadata_rows + 1,))
    rows = cursor.fetchall()
    if len(rows) > limits.max_metadata_rows:
        raise BackupError("Object metadata exceeds the configured row bound")
    descriptors = []
    pending = 0
    for row in rows:
        if len(row) != 9 or row[8] not in {"ready", "pending"}:
            raise BackupError("Unsupported stored object state")
        if row[8] == "pending":
            pending += 1
            continue
        if row[7] != "s3":
            raise BackupError("Ready object requires a different capture backend")
        descriptor = ObjectDescriptor(*row[:7])
        authorize(descriptor, descriptor.owner_id)
        descriptors.append(descriptor)
    if len(descriptors) > limits.max_objects or sum(item.byte_size for item in descriptors) > limits.max_object_bytes:
        raise BackupError("Ready objects exceed the configured count or byte bound")
    if len({item.key for item in descriptors}) != len(descriptors) or len({item.id for item in descriptors}) != len(descriptors):
        raise BackupError("Object inventory contains duplicate identities")
    cursor.execute(REFERENCE_SQL)
    references, invalid = cursor.fetchone()
    if invalid:
        raise BackupError("A persisted object reference is unavailable or belongs to another owner")
    cursor.execute(PUBLICATION_SQL)
    if cursor.fetchone()[0]:
        raise BackupError("A published object descriptor differs from its stored object")
    cursor.execute("""SELECT
        (SELECT count(*) FROM public.planes_generados WHERE pdf_object_id IS NULL AND COALESCE(ruta_pdf,'') <> ''),
        (SELECT count(*) FROM public.gym_profiles WHERE logo_object_id IS NULL AND COALESCE(logo_url,'') <> '')""")
    legacy_plans, legacy_logos = cursor.fetchone()
    counts = {"ready_objects": len(descriptors), "pending_objects": pending,
        "object_references": references, "legacy_plan_references_uncovered": legacy_plans,
        "legacy_logo_references_uncovered": legacy_logos}
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise BackupError("Object inventory counts are invalid")
    return snapshot, descriptors, counts, server


def _capture_database(environment: dict, expected_database: str, expected_revision: str,
                      pg_bin: Path, dump: Path, limits: CaptureLimits, deadline: float) -> tuple:
    connection = _connect(environment)
    try:
        connection.set_session(isolation_level="REPEATABLE READ", readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL row_security = off")
            cursor.execute("SET LOCAL lock_timeout = 5000")
            cursor.execute("SET LOCAL statement_timeout = %s", (int(_remaining(deadline) * 1000),))
            cursor.execute("SET LOCAL idle_in_transaction_session_timeout = %s", (int(_remaining(deadline) * 1000),))
            inventory = _inventory(cursor, expected_database, expected_revision, limits)
            _run_dump(pg_bin, environment, inventory[0], dump, limits, deadline)
            return inventory
    finally:
        try:
            connection.rollback()
        finally:
            connection.close()


def capture_backup(output: Path, *, database_url: str, expected_database: str,
                   expected_revision: str, pg_bin: Path, object_store: S3ObjectStore,
                   limits: CaptureLimits | None = None) -> dict:
    """Produce a private encrypted set; return partial when legacy bytes are uncovered."""
    started = time.monotonic()
    limits = limits or CaptureLimits()
    limits.validate()
    key = encryption_key()
    if key is None:
        raise BackupError("Capture requires an encryption key")
    if expected_revision not in REVISIONS or not isinstance(object_store, S3ObjectStore):
        raise BackupError("Capture requires an explicit supported schema and S3 adapter")
    deadline = started + limits.timeout_seconds
    try:
        from scripts.scan_secrets import _private_evidence
        private = _private_evidence(output)
        required = limits.max_dump_bytes * 3 + limits.max_object_bytes * 3 + 64 * 1024 * 1024
        if shutil.disk_usage(private).free < required:
            raise BackupError("Insufficient private workspace for the bounded capture")
        with tempfile.TemporaryDirectory(prefix="capture-", dir=private) as temporary:
            stage = Path(temporary)
            environment = _native_environment(database_url, expected_database, stage)
            native = _native_identity(pg_bin, environment, deadline)
            dump = stage / "postgres.dump"
            snapshot, descriptors, counts, server = _capture_database(environment, expected_database,
                expected_revision, pg_bin, dump, limits, deadline)
            archive = stage / "objects.zip"
            objects = []
            with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as zipped:
                for descriptor in descriptors:
                    _remaining(deadline)
                    data = object_store.read(descriptor, owner_id=descriptor.owner_id)
                    _remaining(deadline)
                    verify(descriptor, data)
                    zipped.writestr(descriptor.key, data)
                    objects.append({"path": descriptor.key, "sha256": descriptor.sha256, "bytes": len(data)})
            current = datetime.now(UTC)
            snapshot_id = current.strftime("%Y%m%dT%H%M%S%fZ")
            partial = bool(counts["legacy_plan_references_uncovered"] + counts["legacy_logo_references_uncovered"])
            status = "partial_legacy_references" if partial else "verified_current_resources"
            manifest = {"format": 1, "snapshot_id": snapshot_id, "created_at": current.isoformat(),
                "encryption": "AES-256-GCM", "artifacts": [], "objects": objects,
                "capture": {"contract": "postgresql18-s3-exported-snapshot-v1", "status": status,
                    "source_revision": expected_revision, "server_version_num": server,
                    "snapshot_sha256": hashlib.sha256(snapshot.encode("ascii")).hexdigest(),
                    "inventory_sha256": hashlib.sha256(json.dumps([item.__dict__ for item in descriptors],
                        sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest(),
                    "inventory_counts": counts, "native_clients": native,
                    "postgresql_consistency": "same_exported_snapshot",
                    "objects_consistency": "immutable_descriptors_from_that_snapshot",
                    "legacy_bytes": "not_captured", "suppression_journal": "not_captured",
                    "global_roles": "not_captured", "serving_authorized": False}}
            for kind, artifact in (("postgres", dump), ("objects", archive)):
                _remaining(deadline)
                filename = snapshot_id + "-" + artifact.name + ".enc"
                destination = private / filename
                encrypt(artifact, destination, key)
                verified = stage / (artifact.name + ".verified")
                decrypt(destination, verified, key)
                content_hash = checksum(artifact)
                if checksum(verified) != content_hash:
                    raise BackupError("Encrypted capture verification failed")
                manifest["artifacts"].append({"kind": kind, "file": filename,
                    "sha256": checksum(destination), "content_sha256": content_hash,
                    "bytes": destination.stat().st_size})
            # Verify that native files did not change while invoked.
            for name, identity in native.items():
                if checksum(_executable(pg_bin, name)) != identity["sha256"]:
                    raise BackupError("PostgreSQL client changed during capture")
            manifest["authentication"] = "HMAC-SHA256-HKDF-v1"
            manifest["manifest_mac"] = manifest_authentication(manifest, key)
            encoded = json.dumps(manifest, ensure_ascii=True, indent=2).encode("ascii") + b"\n"
            if len(encoded) > MANIFEST_LIMIT:
                raise BackupError("Capture manifest exceeds the publication byte bound")
            candidate = private / (snapshot_id + "-manifest.pending")
            with candidate.open("xb") as stream:
                stream.write(encoded)
            recorded = json.loads(candidate.read_bytes())
            if not hmac.compare_digest(recorded["manifest_mac"], manifest_authentication(recorded, key)):
                raise BackupError("Capture manifest authentication failed")
            for artifact in recorded["artifacts"]:
                if checksum(private / artifact["file"]) != artifact["sha256"]:
                    raise BackupError("Encrypted capture changed before completion")
            _remaining(deadline)
            manifest_path = private / (snapshot_id + "-manifest.json")
            candidate.rename(manifest_path)
        return {"status": status, "snapshot_id": snapshot_id, "manifest": str(manifest_path),
            "source_revision": expected_revision, "inventory_counts": counts,
            "elapsed_seconds": round(time.monotonic() - started, 3), "provider_writes": 0,
            "database_mutations": 0, "serving": False, "scheduled": False}
    except BackupError:
        raise
    except Exception:  # noqa: BLE001 - source/provider exceptions may contain credentials or personal data
        raise BackupError("Capture operation failed; private diagnostics were not published") from None


def _configured_store() -> S3ObjectStore:
    from web.storage.configuration import ObjectStoreConfiguration, build_object_store
    return build_object_store(ObjectStoreConfiguration(backend="s3", production=True,
        bucket=os.environ.get("OBJECT_STORAGE_S3_BUCKET", ""),
        region=os.environ.get("OBJECT_STORAGE_S3_REGION", ""),
        endpoint=os.environ.get("OBJECT_STORAGE_S3_ENDPOINT") or None,
        access_key=os.environ.get("OBJECT_STORAGE_S3_ACCESS_KEY", ""),
        secret_key=os.environ.get("OBJECT_STORAGE_S3_SECRET_KEY", ""),
        session_token=os.environ.get("OBJECT_STORAGE_S3_SESSION_TOKEN") or None))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--expected-revision", required=True, choices=sorted(REVISIONS))
    parser.add_argument("--database-env", default="BACKUP_DATABASE_URL")
    parser.add_argument("--pg-bin", required=True, type=Path)
    parser.add_argument("--max-objects", type=int, default=128)
    parser.add_argument("--max-object-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--max-dump-bytes", type=int, default=128 * 1024 * 1024)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    store = None
    try:
        store = _configured_store()
        result = capture_backup(args.output, database_url=os.environ.get(args.database_env, ""),
            expected_database=args.expected_database, expected_revision=args.expected_revision,
            pg_bin=args.pg_bin, object_store=store, limits=CaptureLimits(max_objects=args.max_objects,
                max_object_bytes=args.max_object_bytes, max_dump_bytes=args.max_dump_bytes,
                timeout_seconds=args.timeout_seconds))
        store.client.close()
        store = None
        result["manifest_file"] = Path(result.pop("manifest")).name
        print(json.dumps(result, sort_keys=True))
        return 2 if result["status"] == "partial_legacy_references" else 0
    except Exception:  # noqa: BLE001 - no secret-bearing SDK/libpq error text in operational output
        print(json.dumps({"status": "failed", "error": "backup_capture_failed"}))
        return 1
    finally:
        if store is not None:
            try:
                store.client.close()
            except Exception:  # noqa: BLE001,S110 - report already failed; do not expose SDK text
                pass


if __name__ == "__main__":
    raise SystemExit(main())
