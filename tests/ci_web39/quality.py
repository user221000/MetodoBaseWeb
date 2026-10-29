"""Current web quality; finite current39 review never inherits parent22 approval."""
from __future__ import annotations

import ast
from collections import Counter
from datetime import UTC, datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.check_quality import fingerprint
from tests.ci_image57 import authority, context
from tests.ci_web37 import git_recipe
from tests.ci_web37.quality import OPERATIONAL, RUNTIME

REVIEW_CONTEXT = "current39-child2-signed-APT-exact-OS-CA-and-static-SQL-only"
PROPOSAL = "tests/ci_web39/bandit26-current-proposal.json"
APPROVAL = "tests/ci_web39/bandit26-current-approval.json"
BASELINE_SHA256 = "14cfe86f9fbff144c0b887ba2b72db7af656a1b88dc09e2e10ce61229bc83996"
BASELINE_BLOB = "8f322ee7fd970239f6a6c8f58a9b5faa1e2d538c"


def maintained_targets():
    return [*RUNTIME, *OPERATIONAL]


def syntax_paths(root=None):
    root = ROOT if root is None else Path(root)
    paths = {root / name for name in OPERATIONAL}
    for name in (*RUNTIME, "tests"):
        paths.update((root / name).rglob("*.py"))
    return sorted(path for path in paths
                  if path.name not in {"test_login_desktop.py", "test_license_offline_security.py"}
                  and not path.name.startswith("test_desktop"))


def native_source_inputs(root):
    """Validate the actual child2, ten inherited inputs and original21 proof.

    This reads authenticated source bytes only. It imports no application,
    installs nothing and makes no build, runtime, OS isolation or SCA claim.
    """
    root = authority.regular_directory(Path(root))
    manifest = context.json_object(authority.raw("container-inputs.json.RAW"))
    payloads = {name: authority.regular_file(root / name).read_bytes()
                for name in manifest["candidate_files"]}
    parent, transition = context.native_parent_payloads(payloads)
    if transition is None or transition != context.native_transition():
        raise ValueError("Quality39 requires the exact current source child2")
    proof = git_recipe.load()
    if len(proof.objects) != 21:
        raise ValueError("The original native21 proof differs")
    for name, pin in manifest["source_files"].items():
        original = proof.blob(git_recipe.NATIVE, name)
        if (hashlib.sha256(original).hexdigest() != pin["raw_sha256"]
                or git_recipe.object_id("blob", original) != pin["blob"]
                or (name != "Dockerfile" and parent[name] != original)):
            raise ValueError("The unchanged native source proof differs")
    web = authority.regular_file(root / "requirements_web.lock").read_bytes()
    lf = web.replace(b"\r\n", b"\n")
    if b"\r" in lf or (b"\r\n" in web and b"\n" in web.replace(b"\r\n", b"")):
        raise ValueError("The web lock has mixed or bare-CR framing")
    catalog = context.json_object(payloads["runtime-source/container37-contract.json"])
    digest = hashlib.sha256(lf).hexdigest()
    if (digest != catalog["web_lock_raw_sha256"]
            or type(catalog["runtime_distribution_count"]) is not int
            or catalog["runtime_distribution_count"] != 57 or len(catalog["distributions"]) != 57):
        raise ValueError("The actual web lock and current57 catalog differ")
    return {"native_input_count": 12, "inherited_input_count": 10,
            "parent_native_merkle_objects": 21, "native_input_transition": transition,
            "web_lock_raw_sha256": digest, "runtime_distributions_expected": 57,
            "scope": "source_inputs_only_no_build_runtime_OS_isolation_or_SCA_acceptance"}


def classify(report, root, *, bandit_version, today=None):
    """Keep the six original baseline entries and require a new current review."""
    if type(report) is not dict or report.get("errors") != [] or type(report.get("results")) is not list:
        raise ValueError("Bandit returned malformed results or analysis errors")
    today = datetime.now(UTC).date() if today is None else today
    raw = authority.regular_file(root / "tests/bandit-reviewed-baseline.json").read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    if (b"\r" in lf or (b"\r\n" in raw and b"\n" in raw.replace(b"\r\n", b""))
            or len(lf) != 2741 or hashlib.sha256(lf).hexdigest() != BASELINE_SHA256
            or git_recipe.object_id("blob", lf) != BASELINE_BLOB):
        raise ValueError("The unchanged six-entry historical baseline differs")
    baseline = context.json_object(lf)
    approved = Counter(item["fingerprint"] for item in baseline["exceptions"]
                       if item["expires"] >= today.isoformat())
    observed = Counter(fingerprint(finding) for finding in report["results"]
                       if fingerprint(finding) in approved)
    new = [finding for finding in report["results"] if fingerprint(finding) not in approved]
    if sum(approved.values()) != 6 or observed != approved:
        raise ValueError("Exactly the six original baseline occurrences and multiplicities are required")
    native = native_source_inputs(root)
    from tests.ci_web39.bandit_review import apply_review

    proposal = context.json_object(authority.regular_file(root / PROPOSAL).read_bytes())
    approval = context.json_object(authority.regular_file(root / APPROVAL).read_bytes())
    matched = apply_review({"errors": [], "results": new}, root, proposal, approval,
                           context=REVIEW_CONTEXT, bandit_version=bandit_version, today=today)
    return {"native_source_inputs": native, "baseline_occurrences": len(report["results"]) - len(new),
            "finite_current_review": matched, "new_occurrences": len(new)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["lint"]:
        return subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "ruff", "check",
                               *maintained_targets(), "--select", "F821"], cwd=ROOT, check=False).returncode
    if argv == ["syntax"]:
        paths = syntax_paths()
        for path in paths:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        print(f"Parsed {len(paths)} maintained web and test Python files")
        return 0
    report_target = None
    if len(argv) == 3 and argv[:2] == ["security", "--report"]:
        report_target = Path(argv[2])
        if not report_target.is_absolute() or report_target.exists():
            raise ValueError("Bandit RAW needs a fresh absolute file")
        authority.regular_directory(report_target.parent)
    elif argv != ["security"]:
        raise SystemExit("usage: python tests/ci_web39/quality.py lint|syntax|security [--report PRIVATE_FILE]")
    process = subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "bandit", "-q", "-r",
                              *maintained_targets(), "-ll", "--skip", "B101", "-f", "json"],
                             cwd=ROOT, capture_output=True, check=False)
    if report_target is not None:
        with report_target.open("xb") as output:
            output.write(process.stdout)
    if process.returncode not in {0, 1} or not process.stdout.strip():
        print(process.stderr.decode("utf8", errors="replace"))
        return process.returncode or 1
    try:
        report = context.json_object(process.stdout)
        result = classify(report, ROOT, bandit_version=importlib.metadata.version("bandit"))
    except (ValueError, KeyError, TypeError, OSError, ImportError) as error:
        print(f"Current39 finite review refused: {error}")
        if type(locals().get("report")) is dict:
            for finding in report.get("results", []):
                if type(finding) is dict:
                    print(f"Observed {finding.get('test_id')} {finding.get('filename')}:{finding.get('line_number')}")
        return 1
    print(json.dumps({"scope": "current39_web_static_quality_only", "findings": len(report["results"]), **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
