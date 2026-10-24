"""Finite authentic RAW for historical security tests; no current source admission."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

ARCHIVE_SHA256 = '15ae13ad81a65d7c25624abf654e0e40827156f2e87fd5e1b92c05d8bb578c71'
MANIFEST_SHA256 = 'd36763f60035fe1501d34eb573f595523c3d7381cb9c5b171b3be008bc2dfa42'
BOUND_NAMES = frozenset(('Dockerfile', 'docs/implementation/20261018-evolution/CUENTA_SEGURIDAD37_UI_IMPLEMENTACION.json', 'docs/implementation/20261018-evolution/evidence/backend-b19-offline-password-20261021/source.json', 'docs/implementation/20261018-evolution/evidence/backend-r12-api-cas-final-source.json', 'docs/implementation/20261018-evolution/evidence/desktop-real-build-9f3f32e-lf-source.json', 'docs/implementation/20261018-evolution/evidence/desktop-real-build-9f3f32e-source.json', 'docs/implementation/20261018-evolution/evidence/history-independent-20261019/browser57-own3/server.log', 'docs/implementation/20261018-evolution/evidence/mobile-nav-20261020/source.json', 'docs/implementation/20261018-evolution/evidence/notifications36-bootstrap-20261020/bootstrap-initial-driver.cjs', 'runtime-source/expat-sec10/rebuild_pyexpat.py', 'runtime-source/expat-sec10/source-pins.json', 'tests/bandit-reviewed-baseline.json', 'tests/check_quality.py', 'tests/ci_image57/bridge.py', 'tests/ci_image57/fixtures/container-inputs.json.RAW', 'tests/ci_image57/fixtures/runtime_probe57-69d49.py.RAW', 'tests/ci_image57/preflight.py', 'tests/ci_web37/container-inputs.json', 'tests/ci_web37/image_guest_preflight.py', 'tests/ci_web37/node-current37.json', 'tests/e2e/security_routines37_server_peer.py', 'tests/test_client_link_models.py', 'web/database/account_security_schema_v1.py', 'web/database/alembic/versions/20261019_followup_tasks.py', 'web/database/alembic/versions/20261020_account_security.py', 'web/database/alembic/versions/20261020_notifications.py', 'web/database/alembic/versions/20261020_nutrition_profile.py', 'web/database/followup_policy.py', 'web/database/followup_schema_v1.py', 'web/database/notification_policy.py', 'web/database/notification_schema_v1.py', 'web/database/schema_control.py', 'web/database/tenant_context.py'))


def historical_source(root, name):
    if type(name) is not str or str(PurePosixPath(name)) != name or ".." in PurePosixPath(name).parts:
        raise ValueError("Historical source name is not canonical")
    if name not in BOUND_NAMES:
        return (Path(root) / name).read_bytes()
    archive = Path(__file__).resolve().parents[1] / "fixtures/serial878-security-RAW.zip"
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Historical security capsule bytes differ")
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        infos = source.infolist()
        if len(infos) != len({entry.filename for entry in infos}) or any(
                entry.is_dir() or entry.flag_bits & 1 for entry in infos):
            raise ValueError("Historical security capsule members differ")
        manifest_raw = source.read("manifest.json")
        if hashlib.sha256(manifest_raw).hexdigest() != MANIFEST_SHA256:
            raise ValueError("Historical security manifest differs")
        document = json.loads(manifest_raw)
        if set(document) != {"schema", "files"} or document["schema"] != "serial878-finite-historical-security-sources-v1":
            raise ValueError("Historical security manifest schema differs")
        rows = document["files"]
        if set(rows) != BOUND_NAMES:
            raise ValueError("Historical security source inventory differs")
        expected = {"manifest.json", *("objects/" + row["sha256"] for row in rows.values())}
        if {entry.filename for entry in infos} != expected:
            raise ValueError("Historical security object inventory differs")
        row = rows[name]
        if set(row) != {"sha256", "bytes"} or type(row["bytes"]) is not int or row["bytes"] < 0:
            raise ValueError("Historical security descriptor differs")
        result = source.read("objects/" + row["sha256"])
        if len(result) != row["bytes"] or hashlib.sha256(result).hexdigest() != row["sha256"]:
            raise ValueError("Historical security RAW differs")
        return result

def completed_safety_scenario(*args, **kwargs):
    """Literal historical setup; complete only the mocked process transport."""
    import subprocess
    from tests import test_secret_scan_safety as original
    if hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest() != '7e7a274c33e7c305e6b2324e90c34358bbf775f465548693d6d7dd806873e474':
        raise ValueError("The original safety scenario bytes differ")
    actual_boundary_run = subprocess.run
    scanner, report, canary = original._scenario(*args, **kwargs)
    mocked_run = scanner.subprocess.run
    monkeypatch = args[1]

    def complete_mock(command, **options):
        if command[0] in {"whoami", "icacls"}:
            return actual_boundary_run(command, **options)
        reply = mocked_run(command, **options)
        if command[0] != "git" and command[1] != "version" and reply.returncode in {0, 1}:
            raw = Path(command[command.index("--report-path") + 1])
            count = len(json.loads(raw.read_bytes()))
            final = f"WRN leaks found: {count}" if count else "INF no leaks found"
            reply.stdout = b""
            reply.stderr = "6:47PM INF scanned ~37 bytes (37 bytes) in 1ms\n6:47PM " + final + "\n"
        return reply

    monkeypatch.setattr(scanner.subprocess, "run", complete_mock)
    return scanner, report, canary
