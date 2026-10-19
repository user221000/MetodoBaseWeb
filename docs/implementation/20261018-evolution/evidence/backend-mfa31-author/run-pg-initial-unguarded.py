"""Private child configuration, immutable labelled outputs, never print URLs."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path("F:/mb-mfa31-20261019")
HERE = Path(__file__).parent
OUT = ROOT / "docs/implementation/20261018-evolution/evidence/backend-mfa31-author"
PRIVATE = Path("C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json")

if "--child" in sys.argv:
    sys.path.insert(0, str(ROOT))
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    config = json.loads(PRIVATE.read_text(encoding="utf-8-sig"))
    from urllib.parse import urlsplit
    for key in ("METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL"):
        value = validate_postgres_test_url(config[key])
        assert urlsplit(value).port == 55483
        os.environ[key] = value
    os.environ["METODOBASE_TEST_PG_BIN"] = config["METODOBASE_TEST_PG_BIN"]
    label = sys.argv[sys.argv.index("--child") + 1]
    os.environ["METODOBASE_HISTORY_ORDERED_PROOF_DIR"] = str(OUT)
    import pytest
    raise SystemExit(pytest.main(sys.argv[sys.argv.index("--child") + 2:] + ["-q", "--tb=short", "--junitxml=" + str(HERE / (label + ".xml"))]))

label = sys.argv[1]
assert re.fullmatch(r"[a-z0-9-]+", label)
assert not (OUT / (label + ".log")).exists()
def photo():
    paths = subprocess.check_output(["git", "--no-replace-objects", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")[:-1]
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(set(paths))
        if not name.startswith("docs/") and (ROOT/name).is_file()}
def packages():
    return sorted((item.metadata["Name"], item.version) for item in importlib.metadata.distributions())
before, before_packages = photo(), packages()
result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(Path(__file__)), "--child", label, *sys.argv[2:]],
    cwd=ROOT, capture_output=True, env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"}, timeout=900)
raw = result.stdout + result.stderr
(HERE / (label + ".raw.log")).write_bytes(raw)
# Connection URLs/passwords are read only by the child. Pattern projection
# protects a diagnostic URL if a third-party exception ever includes it.
filtered, replacements = re.subn(rb"postgres(?:ql)?(?:\+psycopg2)?://[^\s\x22\x27<>]+", b"[REDACTED_PRIVATE_CONNECTION]", raw)
(OUT / (label + ".log")).write_bytes(filtered)
cases = []
if (HERE / (label + ".xml")).exists():
    xml = (HERE / (label + ".xml")).read_bytes()
    (OUT / (label + ".xml")).write_bytes(xml)
    cases = list(ET.fromstring(xml).iter("testcase"))
after, after_packages = photo(), packages()
report = {"exit_code":result.returncode,"cases":len(cases),
    "failures":sum(case.find("failure") is not None for case in cases),
    "errors":sum(case.find("error") is not None for case in cases),
    "skipped":sum(case.find("skipped") is not None for case in cases),
    "source_files":len(before),"source_stable":before==after,
    "packages":len(before_packages),"packages_stable":before_packages==after_packages,
    "log_raw_sha256":hashlib.sha256(raw).hexdigest(),"log_published_sha256":hashlib.sha256(filtered).hexdigest(),
    "redactions":replacements,"private_raw_directory":str(HERE)}
for name, value in [("summary",report),("source-before",before),("source-after",after),
        ("packages-before",before_packages),("packages-after",after_packages)]:
    with (OUT / (label + "-" + name + ".json")).open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(json.dumps(value,indent=2)+"\n")
print(json.dumps(report))
raise SystemExit(result.returncode)
