"""Run the separately leased original53 criteria; never replay legacy429."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence
from tests.ci_google33.run_postgres import photo, role_catalog
from tests.ci_web37.evidence import boundary_before_payload, seal, write
from tests.ci_web37.pg53 import contract, phase, require_ack
from tests.ci_web37.pg_lease import profile
from tests.ci_web37.reports import require_exact_junit
from tests.ci_web37.run_postgres import audit_leases, journal
from tests.ci_web37.run_web import environment_photo, execute, observe_junit


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--pg-profile", type=Path)
    parser.add_argument("--lease-ack", type=Path)
    args = parser.parse_args()
    if not args.private.is_absolute() or not args.output.is_absolute() or args.output.exists():
        parser.error("Fresh absolute private/public paths are required")
    if not args.plan_only and (args.pg_profile is None or args.lease_ack is None):
        parser.error("A separate source-bound PG53 ACK and readonly profile are required")
    row = phase()
    private = _private_evidence(args.private)
    acl = boundary_before_payload(private)
    before = environment_photo()
    write(private / "before.json", before)
    environment = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    for key in list(environment):
        upper = key.upper()
        if (upper == "DATABASE_URL" or upper.endswith("_DATABASE_URL") or upper.startswith(("AWS_", "S3_"))
                or any(name in upper for name in ("STRIPE", "MERCADOPAGO", "SMTP", "RESEND", "SENTRY", "GOOGLE_CLIENT", "OPENAI_API"))):
            environment.pop(key, None)
    environment.update(_METODOBASE_TEST_ROOT=str(private / "metodobase-test-data"), METODOBASE_TEST_REDIS_URL="")
    result = {"accepted": False, "scope": "separate_original53_plan_only" if args.plan_only else "separate_original53_PG_phase",
              "source_commit": before["source"]["HEAD"], "PostgreSQL_executed": False,
              "legacy429_replayed": False, "Chrome": False, "Docker": False, "Redis": False, "Desktop_runtime": False}
    leases = pg_before = roles = None
    pip_before = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-before.private.log")
    try:
        if pip_before:
            raise ValueError("Dependency consistency failed before original53 execution")
        argv = [sys.executable, "-B", "-X", "utf8", "tests/ci_web37/collect.py", "--output", str(private / "oracle.json"), row["module"]]
        code = execute(argv, ROOT, environment, private / "collection.private.log")
        if code or set(map(tuple, json.loads((private / "oracle.json").read_bytes()))) != set(map(tuple, row["expected"])):
            raise ValueError("The separately collected original53 identities differ")
        result["collected_cases"] = 53
        if args.plan_only:
            result["accepted"] = True
        else:
            value = contract(ROOT, before["source"], args.pg_profile)
            require_ack(args.lease_ack, value)
            write(private / "lease-contract.json", value)
            environment.update(profile(args.pg_profile, expected_sha256=value["profile_sha256"]))
            pg_bin = Path(environment["METODOBASE_TEST_PG_BIN"]).resolve(strict=True)
            pg_before, roles = photo(ROOT, pg_bin), role_catalog(environment)
            write(private / "PG-before.json", pg_before)
            write(private / "roles-before.private.json", roles)
            lease_root = _private_evidence(Path(tempfile.gettempdir()) / ("metodobase-account37-author-pg-r30-ppl-" + uuid.uuid4().hex))
            leases = lease_root / "leases"
            leases.mkdir()
            evidence, case_journal = private / "evidence", private / "execution-journal"
            evidence.mkdir()
            case_journal.mkdir()
            environment.update(ACCOUNT37_PRIVATE_LEASES=str(leases), R30_PPL_PRIVATE=str(lease_root),
                               R30_PPL_PG_ACK="ROOT-R30-PPL53-ONE-UUID", METODOBASE_TEST_EVIDENCE_DIR=str(evidence))
            write(private / "lease-namespace.private.json", {"path": str(lease_root), "TEMP_TMP_unchanged": True})
            argv = [sys.executable, "-B", "-X", "utf8", "tests/run_isolated.py", row["module"],
                    "-p", "tests.ci_web37.scope", "--web37-execution-journal", str(case_journal),
                    "-q", "--tb=short", "--basetemp=" + str(private / "pytest-data"), "--junitxml=" + str(private / "pytest.xml")]
            write(private / "command.private.json", argv)
            ack_hash = require_ack(args.lease_ack, value)
            journal(private / "phase.private.jsonl", {"event": "START", "group": "r30-ppl53", "lease_ACK_sha256": ack_hash})
            result["PostgreSQL_executed"] = True
            code = execute(argv, ROOT, environment, private / "pytest.private.log")
            result.update(pytest_exit=code, **observe_junit(private / "pytest.xml", row["expected"]))
            result["normally_closed_UUIDs_fresh_absent"] = audit_leases(leases, environment)
            if result["normally_closed_UUIDs_fresh_absent"] != 1:
                raise ValueError("The separate original53 phase exceeded or missed its one UUID")
            if code == 0:
                require_exact_junit((private / "pytest.xml").read_bytes(), row["expected"])
                result["accepted"] = True
            journal(private / "phase.private.jsonl", {"event": "FINISH", **result})
    except Exception as error:  # noqa: BLE001 -- retain a rejected phase before normal cleanup/audit
        (private / "runner-error.private.log").write_text(traceback.format_exc(), encoding="utf8")
        result.update(accepted=False, runner_error_class=type(error).__name__)
    finally:
        if leases is not None:
            try:
                result["normally_closed_UUIDs_fresh_absent"] = audit_leases(leases, environment)
                for path in sorted(leases.glob("lease-*.json")):
                    (private / path.name).write_bytes(path.read_bytes())
                for path in sorted((leases.parent / "witnesses").glob("*.json")):
                    (private / path.name).write_bytes(path.read_bytes())
                pg_after, after_roles = photo(ROOT, pg_bin), role_catalog(environment)
                write(private / "PG-after.json", pg_after)
                write(private / "roles-after.private.json", after_roles)
                result["PG_binaries_sources_packages_roles_quiet"] = pg_before == pg_after and roles == after_roles
                result["accepted"] = result["accepted"] and result["PG_binaries_sources_packages_roles_quiet"]
            except Exception as error:  # noqa: BLE001 -- no termination or FORCE DROP fallback
                (private / "lease-refusal.private.log").write_text(traceback.format_exc(), encoding="utf8")
                result.update(accepted=False, lease_refusal_class=type(error).__name__)
        after = environment_photo()
        write(private / "after.json", after)
        pip_after = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-after.private.log")
        result.update(pip_before=pip_before, pip_after=pip_after, source_packages_binaries_quiet=before == after,
                      accepted=result["accepted"] and before == after and pip_before == pip_after == 0)
    print(json.dumps(seal(private, args.output, result, acl)))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())
