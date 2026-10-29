"""Fresh loopback Linux Actions39 cluster; start/normal-stop only, never live.

The test-cluster migrator is intentionally privileged. Application roles remain
restricted. Every phase gets its own source/profile/generation-bound ACK. The
accepted historical37 cluster naming is retained by its unchanged shared guard.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess


def require_ci():
    from tests.ci_web39.pg_contract import ROOT
    from tests.billing13_legacy_apply37_pg_contract import private_workspace
    if (os.name != "posix" or os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() == 0
            or ROOT != Path(os.environ["GITHUB_WORKSPACE"]).resolve(strict=True)):
        raise ValueError("Only the exact non-root GitHub Actions checkout may own this test cluster")
    private_workspace()
    return ROOT, Path(os.environ["RUNNER_TEMP"]), Path("/usr/lib/postgresql/17/bin")


def write(path, value):
    with path.open("x", encoding="utf8") as output:
        json.dump(value, output, indent=2)
        output.write("\n")


def start():
    root, temporary, pg = require_ci()
    from scripts.scan_secrets import _private_evidence
    from tests.ci_web39 import pg_contract
    from tests.ci_web39.pg_tools_linux import tool_hashes
    from tests.ci_web38.prepare_collection import source_photo
    from tests.billing13_legacy_apply37_pg_contract import ci_generation
    from web.database.schema_control import expected_head
    os.umask(0o077)
    source = source_photo()
    if source["HEAD"] != os.environ["GITHUB_SHA"] or expected_head() != "20261023_privacy_disposition":
        raise ValueError("Only the exact current39 CI commit may be bootstrapped")
    for name in ("postgres", "pg_ctl", "pg_dump", "pg_restore", "psql", "initdb"):
        if subprocess.check_output([str(pg / name), "--version"], text=True).split()[2] != "17.11":
            raise ValueError("The signed exact17.11 PostgreSQL package is required")
    tool_hashes(pg, verify_versions=True)
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", 55483)) == 0:
            raise ValueError("The exclusive test PostgreSQL port is already occupied")
    private = _private_evidence(temporary / "ci37-pg-cluster-private")
    public = temporary / "current39-pg-public"
    public.mkdir(mode=0o700)
    password, app_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    (private / "initdb-password.private").write_text(password + "\n", encoding="utf8")
    data = private / "data"
    with (private / "bootstrap.private.log").open("xb") as log:
        subprocess.run([str(pg / "initdb"), "-D", str(data), "-U", "metodobase_test_admin",
            "--no-locale", "--encoding=UTF8", "--auth-local=trust", "--auth-host=scram-sha-256",
            "--pwfile=" + str(private / "initdb-password.private")], check=True, stdout=log, stderr=subprocess.STDOUT)
        subprocess.run([str(pg / "pg_ctl"), "-D", str(data), "-l", str(private / "postgresql.private.log"),
            "-o", "-h 127.0.0.1 -p 55483", "-w", "-t", "60", "start"], check=True, stdout=log, stderr=subprocess.STDOUT)
    raw = (data / "postmaster.pid").read_bytes()
    pid = int(raw.splitlines()[0])
    status = Path("/proc", str(pid), "stat").read_text()
    if Path("/proc", str(pid), "exe").resolve(strict=True) != pg / "postgres":
        raise ValueError("The fresh test postmaster executable differs")
    identity = {"pid": pid, "start_ticks": int(status[status.rindex(")") + 2:].split()[19]),
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "postmaster_pidfile_sha256": hashlib.sha256(raw).hexdigest(), "data": str(data),
                "port": 55483, "source_commit": source["HEAD"]}
    write(private / "cluster-identity.private.json", identity)
    import psycopg2
    from psycopg2 import sql
    control = psycopg2.connect(host="127.0.0.1", port=55483, dbname="postgres",
                              user="metodobase_test_admin", password=password)
    control.autocommit = True
    try:
        with control.cursor() as cursor:
            cursor.execute("SHOW server_version_num")
            if cursor.fetchone() != ("170011",):
                raise ValueError("The actual test server version differs")
            cursor.execute("SELECT inet_server_addr()::text,inet_server_port(),current_user")
            host, port, owner = cursor.fetchone()
            if host not in {"127.0.0.1", "127.0.0.1/32"} or port != 55483 or owner != "metodobase_test_admin":
                raise ValueError("The actual test control endpoint/owner differs")
            cursor.execute("CREATE ROLE metodobase_test_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD %s", (app_password,))
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier("metodobase_test_integration")))
            cursor.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname='metodobase_test_app'")
            if cursor.fetchone() != (False,) * 4:
                raise ValueError("The actual application role is privileged")
            cursor.execute("SELECT pg_postmaster_start_time()")
            started = cursor.fetchone()[0].isoformat()
    finally:
        control.close()
    profile = private / "profile.private.json"
    write(profile, {"METODOBASE_TEST_MIGRATOR_URL": "postgresql+psycopg2://metodobase_test_admin:" + password + "@127.0.0.1:55483/metodobase_test_integration",
                    "METODOBASE_TEST_POSTGRES_URL": "postgresql+psycopg2://metodobase_test_app:" + app_password + "@127.0.0.1:55483/metodobase_test_integration",
                    "METODOBASE_TEST_PG_BIN": str(pg)})
    generation = private / "generation39.private.json"
    write(generation, ci_generation(identity, started))
    for name in ("core", "restore"):
        value = pg_contract.build_contract(name, profile, generation)
        write(private / ("contract39-" + name + ".private.json"), value)
        write(private / ("ack39-" + name + ".private.json"), {
            "approved": True, "scope": pg_contract.SCOPE, "contract_sha256": pg_contract.digest(value),
            "expires_at_UTC": (datetime.now(UTC) + timedelta(hours=4)).isoformat()})
    if source_photo() != source:
        raise ValueError("The current39 source changed during test-cluster bootstrap")
    print(json.dumps({"scope": "fresh_ephemeral_Actions39_TEST_cluster_only",
                      "core_and_restore_authorizations_ready": True, "planned_UUIDs": 3, "required_cases": 5}))


def stop():
    _, temporary, pg = require_ci()
    private = temporary / "ci37-pg-cluster-private"
    data = private / "data"
    pidfile = data / "postmaster.pid"
    if pidfile.exists():
        row = json.loads((private / "cluster-identity.private.json").read_bytes())
        raw = pidfile.read_bytes()
        pid = int(raw.splitlines()[0])
        status = Path("/proc", str(pid), "stat").read_text()
        if (Path(row["data"]) != data or row["port"] != 55483 or pid != row["pid"]
                or hashlib.sha256(raw).hexdigest() != row["postmaster_pidfile_sha256"]
                or Path("/proc/sys/kernel/random/boot_id").read_text().strip() != row["boot_id"]
                or int(status[status.rindex(")") + 2:].split()[19]) != row["start_ticks"]
                or Path("/proc", str(pid), "exe").resolve(strict=True) != pg / "postgres"):
            raise ValueError("The exact owned test postmaster identity changed; no stop permitted")
        with (private / "normal-stop.private.log").open("xb") as log:
            subprocess.run([str(pg / "pg_ctl"), "-D", str(data), "-m", "smart", "-w", "-t", "60", "stop"],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        if pidfile.exists() or Path("/proc", str(pid)).exists():
            raise ValueError("The exact owned test postmaster did not close normally")
    print(json.dumps({"owned_Actions39_cluster_stopped_or_never_started": True, "forced_stop": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("start", "stop"))
    args = parser.parse_args()
    {"start": start, "stop": stop}[args.action]()


if __name__ == "__main__":
    main()
