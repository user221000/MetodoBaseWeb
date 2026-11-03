"""Privacy and finite identity controls; no Docker, app, or database execution."""
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from tests.ci_image57 import probe
from tests.ci_image57 import runtime_failure_diagnostic as subject

SOURCE = "1" * 40
IID = "sha256:" + "2" * 64
CID = "3" * 64
NONCE = "4" * 32
BOUND = b"import os\nassert False, 'do not publish this value'\n"
SENSITIVE = b"sk_live_private_example_never_publish"


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def fixture(tmp_path, monkeypatch):
    repository = tmp_path / "repo"
    private = tmp_path / "private"
    repository.mkdir()
    private.mkdir()
    monkeypatch.setattr(subject, "authenticate_contract", lambda root, source, contract: BOUND
                        if source == SOURCE and contract == {"source": SOURCE} else subject.reject())
    row = {"Id": CID, "Image": IID,
           "Config": {"User": "999:999", "Labels": {"metodobase.ci57.nonce": NONCE,
                       "org.opencontainers.image.revision": SOURCE}},
           "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                          "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges:true"],
                          "Memory": 512 * 1024**2, "NanoCpus": 1000000000, "PidsLimit": 128},
           "State": {"Running": False, "ExitCode": 1, "OOMKilled": False}}
    payloads = {"runtime-input-contract.json": json.dumps({"source": SOURCE}).encode(),
                "prepared-runtime-probe57.raw.py": BOUND, "bound-runtime-probe57.raw.py": BOUND,
                "runtime.iid": (IID + "\n").encode(), "container-id.private.txt": (CID + "\n").encode(),
                "runtime-ownership.private.json": json.dumps({"source": SOURCE, "image_id": IID, "nonce": NONCE}).encode(),
                "container-before.private.json": json.dumps([row]).encode(),
                "container-after.private.json": json.dumps([row]).encode(),
                "runtime-stderr.private.log": b'Traceback (most recent call last):\n  File "<stdin>", line 2, in <module>\nAssertionError: ' + SENSITIVE + b"\n"}
    for name, raw in payloads.items():
        (private / name).write_bytes(raw)
    return repository, private


def test_failed_runtime_projects_only_authenticated_locations_and_finite_state(tmp_path, monkeypatch):
    repository, private = fixture(tmp_path, monkeypatch)
    result = subject.diagnose(private, SOURCE, repository)
    assert result["accepted"] is False and result["diagnostic_only"] is True
    assert result["image_id"] == IID and result["exception_type"] == "AssertionError"
    assert result["frames"] == [subject.location(BOUND, 2)]
    assert result["frames"][0]["statement_kind"] == "Assert"
    assert result["state"] == {"container_id": CID, "exit_code": 1, "running": False, "oom_killed": False}
    serialized = json.dumps(result).encode()
    assert SENSITIVE not in serialized and b"do not publish" not in serialized
    assert b"Traceback" not in serialized and b"<module>" not in serialized
    assert (private / "runtime-stderr.private.log").read_bytes().endswith(SENSITIVE + b"\n")


@pytest.mark.parametrize("fault", ["prepared", "bound", "source", "iid", "nonce", "owner-source",
                                  "inspect-image", "inspect-id", "inspect-source", "state-bool", "state-range",
                                  "oom-type", "network", "privileged", "shares", "duplicate-key", "private-in-repo"])
def test_mismatch_fails_closed(tmp_path, monkeypatch, fault):
    repository, private = fixture(tmp_path, monkeypatch)
    source = SOURCE
    if fault in {"prepared", "bound"}:
        name = "prepared-runtime-probe57.raw.py" if fault == "prepared" else "bound-runtime-probe57.raw.py"
        (private / name).write_bytes(BOUND + b"# drift\n")
    elif fault == "source":
        source = "5" * 40
    elif fault == "iid":
        (private / "runtime.iid").write_text("foreign")
    elif fault in {"nonce", "owner-source"}:
        path = private / "runtime-ownership.private.json"
        row = json.loads(path.read_bytes())
        row["nonce" if fault == "nonce" else "source"] = "5" * (32 if fault == "nonce" else 40)
        path.write_text(json.dumps(row))
    elif fault == "duplicate-key":
        (private / "runtime-input-contract.json").write_bytes(b'{"source":1,"source":2}')
    elif fault == "private-in-repo":
        repository = private
    else:
        path = private / "container-after.private.json"
        row = json.loads(path.read_bytes())[0]
        if fault == "inspect-image":
            row["Image"] = "sha256:" + "5" * 64
        elif fault == "inspect-id":
            row["Id"] = "5" * 64
        elif fault == "inspect-source":
            row["Config"]["Labels"]["org.opencontainers.image.revision"] = "5" * 40
        elif fault == "state-bool":
            row["State"]["ExitCode"] = True
        elif fault == "state-range":
            row["State"]["ExitCode"] = 256
        elif fault == "oom-type":
            row["State"]["OOMKilled"] = 0
        elif fault == "network":
            row["HostConfig"]["NetworkMode"] = "host"
        elif fault == "privileged":
            row["HostConfig"]["Privileged"] = True
        elif fault == "shares":
            row["Mounts"] = [{"Source": "sensitive"}]
        path.write_text(json.dumps([row]))
    with pytest.raises(ValueError):
        subject.diagnose(private, source, repository)


@pytest.mark.parametrize("fault", ["oversized", "hardlink", "alias", "symlink"])
def test_file_boundaries(tmp_path, fault):
    path = tmp_path / "raw"
    path.write_bytes(b"12")
    if fault == "oversized":
        with pytest.raises(ValueError):
            subject.read(path, 1)
    elif fault == "hardlink":
        alias = tmp_path / "alias"
        alias.hardlink_to(path)
        with pytest.raises(ValueError):
            subject.read(path)
    elif fault == "alias":
        folder = tmp_path / "folder"
        folder.mkdir()
        with pytest.raises(ValueError):
            subject.read(folder / ".." / "raw")
    else:
        link = tmp_path / "link"
        try:
            link.symlink_to(path)
        except OSError:
            pytest.skip("Platform lacks symlink creation privilege")
        with pytest.raises(ValueError):
            subject.read(link)


def test_read_is_bounded_even_if_file_grows_after_initial_stat(tmp_path, monkeypatch):
    path = tmp_path / "raw"
    path.write_bytes(b"1234")
    original = Path.open
    requests = []

    class Reader:
        def __enter__(self):
            self.stream = original(path, "rb")
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, size):
            requests.append(size)
            return b"x" * size

    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: Reader())
    with pytest.raises(ValueError):
        subject.read(path, 4)
    assert requests == [5]


@pytest.mark.parametrize("stderr,kind,count", [
    (b'  File "/tmp/foreign", line 2, in secret\nAssertionError: secret', "AssertionError", 0),
    (b'  File "<stdin>", line 2, in secret\nForeignSecretError: secret', "OTHER", 1),
    (b'ValueError: sk_live_sensitive\n', "ValueError", 0),
    (b'prefix AssertionError: secret', "OTHER", 0),
])
def test_trace_is_text_location_only_and_never_forwards_messages(stderr, kind, count):
    result = subject.project_trace(stderr, BOUND)
    assert result["exception_type"] == kind and len(result["frames"]) == count
    assert b"secret" not in json.dumps(result).encode().lower()


@pytest.mark.parametrize("line", [0, 3, True, -1])
def test_out_of_range_locations_rejected(line):
    with pytest.raises(ValueError):
        subject.location(BOUND, line)


def test_cli_invalid_boundary_is_fixed_nonzero_and_never_formats_exception(tmp_path, monkeypatch, capsys):
    def hostile(*args):
        raise ValueError(SENSITIVE.decode())

    monkeypatch.setattr(subject, "diagnose", hostile)
    assert subject.main(["--private", str(tmp_path), "--source", SOURCE]) == 1
    output = capsys.readouterr()
    assert SENSITIVE.decode() not in output.out + output.err
    assert json.loads(output.out)["diagnostic_status"] == "WITHHELD_INVALID_OR_UNAVAILABLE_BOUNDARY"


def test_blob_size_rejected_before_content_read(monkeypatch):
    calls = []

    def fake(root, *args, **kwargs):
        calls.append(args)
        return b"999999999\n"

    monkeypatch.setattr(subject, "git", fake)
    with pytest.raises(ValueError):
        subject.blob(Path("."), SOURCE, "source", 32)
    assert len(calls) == 1 and calls[0][1] == "-s"


def test_real_container_validation_is_not_replaced():
    row = {"Image": IID}
    with pytest.raises(ValueError):
        probe.validate_container(deepcopy(row), IID, SOURCE, NONCE)


@pytest.mark.parametrize("fault", [None, "source", "head", "producer", "hash", "mode", "tree", "extra", "symlink"])
def test_contract_comes_from_exact_git_inventory_before_rebind(tmp_path, monkeypatch, fault):
    root = tmp_path / "repo"
    folder = root / "tests/ci_image57"
    folder.mkdir(parents=True)
    contents = {"tests/ci_image57/" + name: b"# finite producer fixture\n" for name in subject.PRODUCERS}
    for name, raw in contents.items():
        (root / name).write_bytes(raw)
    app = b"# app bytes\n"
    contents["web/example.py"] = app
    contract = {"source": SOURCE, "source_tree": "5" * 40,
                "app_hashes": {"web/example.py": subject.digest(app)},
                "app_modes": {"web/example.py": "100644"}}

    def fake_git(repository, *args, **kwargs):
        assert repository == root
        if args[:2] == ("cat-file", "-t"):
            return b"commit\n"
        if args[:2] == ("rev-parse", "HEAD"):
            return (("9" * 40 if fault == "head" else SOURCE) + "\n").encode()
        if args[0] == "rev-parse":
            return (("9" * 40 if fault == "tree" else "5" * 40) + "\n").encode()
        if args[0] == "ls-tree":
            return ((b"120000" if fault == "symlink" else b"100644")
                    + b" blob " + b"6" * 40 + b" 12\tweb/example.py\0")
        name = args[2].split(":", 1)[1]
        return (str(len(contents[name])).encode() + b"\n" if args[1] == "-s" else contents[name])

    monkeypatch.setattr(subject, "git", fake_git)
    calls = []
    monkeypatch.setattr(probe, "bind", lambda actual: calls.append(actual) or BOUND)
    if fault == "source":
        contract["source"] = "9" * 40
    elif fault == "producer":
        (folder / subject.PRODUCERS[0]).write_bytes(b"# changed\n")
    elif fault == "hash":
        contract["app_hashes"]["web/example.py"] = "9" * 64
    elif fault == "mode":
        contract["app_modes"]["web/example.py"] = "100755"
    elif fault == "extra":
        contract["app_hashes"]["web/extra.py"] = "9" * 64
    if fault is None:
        assert subject.authenticate_contract(root, SOURCE, contract) == BOUND
        assert calls == [contract]
    else:
        with pytest.raises(ValueError):
            subject.authenticate_contract(root, SOURCE, contract)
        assert not calls


def test_changed_producer_rejected_before_import_in_fresh_process(tmp_path):
    root = tmp_path / "isolated-repository"
    folder = root / "tests/ci_image57"
    folder.mkdir(parents=True)
    (root / "tests/__init__.py").write_bytes(b"")
    for name in subject.PRODUCERS:
        (folder / name).write_bytes(b"# authenticated inert source\n")
    (folder / "runtime_failure_diagnostic.py").write_bytes(Path(subject.__file__).read_bytes())
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    for args in (["init", "--quiet"], ["add", "--", "tests"],
                 ["-c", "user.name=Local diagnostic control", "-c", "user.email=control@invalid.example",
                  "commit", "--quiet", "-m", "isolated finite producer control"]):
        subprocess.run(["git", *args], cwd=root, env=env, check=True, capture_output=True, timeout=15)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, env=env, text=True).strip()
    sentinel = root / "IMPORT_EXECUTED"
    (folder / "context.py").write_text("from pathlib import Path\nPath(" + repr(str(sentinel))
                                        + ").write_text('unsafe import executed')\n", encoding="utf8")
    program = ("import sys\nfrom pathlib import Path\nsys.path.insert(0," + repr(str(root)) + ")\n"
               "from tests.ci_image57 import runtime_failure_diagnostic as s\n"
               "try:\n s.authenticate_contract(Path(" + repr(str(root)) + ")," + repr(source) + ",{})\n"
               "except ValueError:\n print('REJECTED_BEFORE_IMPORT')\n")
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", program],
                            cwd=root, env=env, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0 and result.stdout.strip() == b"REJECTED_BEFORE_IMPORT"
    assert result.stderr == b"" and not sentinel.exists()
