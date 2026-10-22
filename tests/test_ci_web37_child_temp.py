"""Fresh child TEMP is private; the original isolation predicates stay intact."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from scripts.scan_secrets import _private_evidence
from tests.ci_web37.run_web import ROOT, child_environment


PROBE = '''import json, os, sqlite3, tempfile
from pathlib import Path

def test_original_isolation_sqlite_and_pytest_paths(tmp_path):
    private=Path(os.environ["TMPDIR"]).resolve()
    assert Path(tempfile.gettempdir()).resolve()==private
    assert Path(os.environ["TEMP"]).resolve()==private
    assert Path(os.environ["TMP"]).resolve()==private
    root=Path(os.environ["_METODOBASE_TEST_ROOT"]).resolve()
    assert root.is_relative_to(private) and root.name.startswith("metodobase-test-")
    worker=Path(os.environ["METODOBASE_DATA_DIR"]).resolve()
    assert worker==root/"main"
    assert tmp_path.resolve().is_relative_to(private/"pytest-data")
    assert Path(os.environ["APPDATA"]).resolve()==worker/"appdata"
    assert Path(os.environ["LOCALAPPDATA"]).resolve()==worker/"localappdata"
    database=worker/"child-temp-canary.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE canary(value INTEGER NOT NULL)")
        connection.execute("INSERT INTO canary VALUES(1)")
        assert connection.execute("SELECT value FROM canary").fetchone()==(1,)
    with tempfile.TemporaryDirectory(prefix="child-canary-") as nested:
        assert Path(nested).resolve().is_relative_to(private)
    (private/"probe-result.json").write_text(json.dumps({"temp":str(private),
        "test_root":str(root),"worker":str(worker),"pytest_path":str(tmp_path.resolve()),
        "database":str(database),"sqlite_value":1}),encoding="utf8")
'''

REJECT = '''import json
from tests.isolation import prepare_environment
try:
    prepare_environment(discard_inherited=True)
except ValueError as error:
    assert str(error)=="Test data root must be a dedicated temporary directory"
    print(json.dumps({"rejected":True,"before_worker_creation":True}))
else:
    raise AssertionError("Original isolation admitted a root outside its contract")
'''


def test_temp_configuration_changes_only_the_child_copy(tmp_path):
    before = dict(os.environ)
    cached = tempfile.gettempdir()
    selected = child_environment(tmp_path, private_as_temp=True)
    legacy = child_environment(tmp_path)
    assert dict(os.environ) == before and tempfile.gettempdir() == cached
    assert all(selected[key] == str(tmp_path) for key in ("TEMP", "TMP", "TMPDIR"))
    assert all(legacy.get(key) == before.get(key) for key in ("TEMP", "TMP", "TMPDIR"))
    assert selected["_METODOBASE_TEST_ROOT"] == str(tmp_path / "metodobase-test-data")
    assert selected["METODOBASE_TEST_DATABASE_URL"] == selected["METODOBASE_TEST_REDIS_URL"] == ""


def test_original_isolation_pytest_and_sqlite_use_the_private_child_temp(tmp_path):
    private = _private_evidence(tmp_path / "positive-private")
    probe = private / "test_child_probe.py"
    probe.write_text(PROBE, encoding="utf8")
    environment = child_environment(private, private_as_temp=True)
    environment.pop("PYTEST_XDIST_WORKER", None)
    before = dict(os.environ)
    with (private / "pytest.private.log").open("xb") as log:
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "tests/run_isolated.py",
            str(probe), "-q", "--basetemp=" + str(private / "pytest-data"),
            "--junitxml=" + str(private / "pytest.xml"), "-p", "no:cacheprovider"],
            cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=30, check=False)
    assert completed.returncode == 0
    observed = json.loads((private / "probe-result.json").read_bytes())
    assert Path(observed["temp"]) == private.resolve() and observed["sqlite_value"] == 1
    assert Path(observed["database"]).is_relative_to(private.resolve())
    assert dict(os.environ) == before


@pytest.mark.parametrize("invalid", ["escape", "host-temp", "wrong-basename"])
def test_original_isolation_refuses_escape_host_temp_and_wrong_basename(tmp_path, invalid):
    private = _private_evidence(tmp_path / (invalid + "-private"))
    environment = child_environment(private, private_as_temp=True)
    host_temp = Path(os.environ.get("METODOBASE_CI37_HOST_TEMP", tempfile.gettempdir()))
    rejected = {
        "escape": private.parent / "metodobase-test-not-admitted",
        "host-temp": host_temp / "metodobase-test-not-admitted",
        "wrong-basename": private / "not-a-test-root",
    }[invalid]
    assert not rejected.exists()
    environment["_METODOBASE_TEST_ROOT"] = str(rejected)
    with (private / "refusal.private.log").open("xb") as log:
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", REJECT],
            cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=15, check=False)
    assert completed.returncode == 0
    assert not rejected.exists()
    assert json.loads((private / "refusal.private.log").read_bytes()) == {
        "rejected": True, "before_worker_creation": True}
