"""Execute exactly five current41 payments criteria, retaining private originals."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence
from tests.ci_web41 import payments_contract as contract
from tests.ci_web38.reports import require_exact_junit


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("profile", "generation", "ack", "private", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if any(not getattr(args, key).is_absolute() for key in ("profile", "generation", "ack", "private", "output")):
        parser.error("Explicit absolute payments41 authorities are required")
    if args.output.exists() or args.private.exists():
        parser.error("Fresh private and public evidence paths are required")
    private = _private_evidence(args.private)
    result = {"accepted": False, "scope": contract.SCOPE, "planned_cases": 5, "PostgreSQL_executed": False,
              "Stripe_sandbox": False, "live_provider_calls": False, "historical_core_restore_budgets_unchanged": True}
    try:
        value = contract.build_contract(args.profile, args.generation)
        result["Root_ACK_sha256"] = contract.require_ack(args.ack, value)
        expected = [(contract.MODULE.removesuffix(".py").replace("/", "."), name) for name in contract.CASES]
        command = [sys.executable, "-B", "-X", "utf8", "tests/run_isolated.py", contract.MODULE,
            "-p", "tests.ci_web41.payments_fixtures", "--payments41-profile", str(args.profile),
            "--payments41-generation", str(args.generation), "--payments41-ack", str(args.ack),
            "--payments41-evidence", str(private / "runtime"), "-q", "--tb=short",
            "--basetemp=" + str(private / "pytest-data"), "--junitxml=" + str(private / "pytest.xml")]
        (private / "command.private.json").write_text(json.dumps(command, indent=2), encoding="utf8")
        environment = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
        for key in list(environment):
            upper = key.upper()
            if (upper == "DATABASE_URL" or upper.endswith("_DATABASE_URL") or upper.startswith(("AWS_", "S3_"))
                    or any(name in upper for name in ("STRIPE", "MERCADOPAGO", "SMTP", "RESEND", "SENTRY", "GOOGLE_CLIENT", "OPENAI_API"))):
                environment.pop(key, None)
        with (private / "pytest.private.log").open("xb") as output:
            child = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT)
            result["PostgreSQL_executed"] = True
            code = child.wait()
        result["pytest_exit"] = code
        if code == 0:
            require_exact_junit((private / "pytest.xml").read_bytes(), expected)
        closure = json.loads((private / "runtime/closure.json").read_bytes())
        stable = contract.build_contract(args.profile, args.generation) == value
        contract.require_ack(args.ack, value)
        result.update(closure=closure, exact_five_identities=code == 0, source_profile_generation_quiet=stable,
                      FileSetDigest=value["FileSetDigest"], accepted=code == 0 and closure["accepted"] is True and stable)
    except Exception as error:
        (private / "runner-error.private.log").write_text(traceback.format_exc(), encoding="utf8")
        result.update(accepted=False, error_class=type(error).__name__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps(result))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())
