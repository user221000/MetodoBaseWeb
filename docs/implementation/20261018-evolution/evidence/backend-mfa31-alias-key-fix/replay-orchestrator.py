"""Own immutable-driver replay: SQLite/ASGI, no PG, no provider network."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path("F:/mb-mfa31-keys-fix-20261019")
HERE = Path(__file__).parent
OUT = ROOT / "docs/implementation/20261018-evolution/evidence/backend-mfa31-alias-key-fix"


def photograph():
    names = subprocess.check_output(["git", "--no-replace-objects", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")[:-1]
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(set(names))
        if not name.startswith("docs/") and (ROOT / name).is_file()}


def packages():
    return sorted((item.metadata["Name"], item.version) for item in importlib.metadata.distributions())


def main():
    label = sys.argv[1]
    assert label in {"before", "after", "maintained-after", "maintained-mounted-after", "maintained-route-inventory-after"}
    assert not (OUT / (label + ".log")).exists()
    before, package_before = photograph(), packages()
    if label.startswith("maintained-"):
        command = [sys.executable, "-X", "utf8", "-B", "tests/run_isolated.py",
            "tests/test_mfa31_payment_alias_keys.py", "-q", "--tb=short", "--junitxml=" + str(HERE / (label + ".xml"))]
    else:
        command = [sys.executable, "-X", "utf8", "-B", str(HERE / label / "run_action_keys.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=240)
    raw = result.stdout + result.stderr
    # The immutable tests assert only status/call metadata. Refuse publication
    # of an enrollment URI or a signed token if an unexpected error includes it.
    import re
    assert b"otpauth://" not in raw and re.search(rb"[A-Za-z0-9_-]+\.[0-9a-fA-F]{64}", raw) is None
    (OUT / (label + ".log")).write_bytes(raw)
    xml_path = HERE / (label + ".xml") if label.startswith("maintained-") else HERE / label / "action-keys.xml"
    xml = xml_path.read_bytes()
    (OUT / (label + ".xml")).write_bytes(xml)
    cases = list(ET.fromstring(xml).iter("testcase"))
    after, package_after = photograph(), packages()
    report = {"label": label, "exit": result.returncode, "cases": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skips": sum(case.find("skipped") is not None for case in cases),
        "driver_sha256": hashlib.sha256((HERE / "before/test_action_keys.py").read_bytes()).hexdigest(),
        "source_files": len(before), "sources_quiet": before == after,
        "packages": len(package_before), "packages_quiet": package_before == package_after,
        "stdout_sha256": hashlib.sha256(raw).hexdigest(), "xml_sha256": hashlib.sha256(xml).hexdigest(),
        "scope": "Real local auth/MFA/rate/SQLite transactions; synthetic billing port, no PG/Chrome/provider network"}
    for suffix, data in [("summary", report), ("source-before", before), ("source-after", after),
                         ("packages-before", package_before), ("packages-after", package_after)]:
        with (OUT / (label + "-" + suffix + ".json")).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(data, indent=2) + "\n")
    if not label.startswith("maintained-"):
        origins = (HERE / label / "action-key-origins.json").read_bytes()
        (OUT / (label + "-origins.json")).write_bytes(origins)
        assert json.loads(origins)["source_root"] == str(ROOT)
    print(json.dumps(report))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
