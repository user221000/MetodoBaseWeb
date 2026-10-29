"""Current39 native-subtest evidence; main identities remain normative."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "current39-native-subtests-v1"
PYTEST_VERSION = "9.1.1"
MAX_BYTES = 64 * 1024**2
MAIN_CLASS = "_pytest.reports.TestReport"
SUBTEST_CLASS = "_pytest.subtests.SubtestReport"
BOUNDARY = "boundary-before-payload.private.txt"
PHASES = [{"when": phase, "outcome": "passed"} for phase in ("setup", "call", "teardown")]


def require(condition, reason):
    if not condition:
        raise ValueError("Current39 subtest evidence: " + reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def json_value(raw):
    require(type(raw) in (bytes, str), "UTF-8 JSON required")
    if type(raw) is bytes:
        require(b"\0" not in raw, "UTF-8 JSON required")
        raw = raw.decode("utf8")
    require("\0" not in raw, "UTF-8 JSON required")
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("Nonfinite subtest JSON number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def regular(path, *, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, "absolute canonical evidence path required")
    for item in (path, *path.parents):
        info = item.lstat()
        require(not item.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                "evidence path alias")
    require(stat.S_ISDIR(path.stat().st_mode) if directory else stat.S_ISREG(path.stat().st_mode),
            "regular evidence path required")
    return path


def current_binding():
    """Read source/tool bytes without importing an application or starting I/O."""
    from tests.ci_web38.prepare_collection import source_photo

    version = importlib.metadata.version("pytest")
    require(version == PYTEST_VERSION, "reviewed native pytest API differs")
    tools = {}
    for name in ("_pytest.subtests", "_pytest.unittest", "_pytest.junitxml", "_pytest.reports", "xdist.remote"):
        spec = importlib.util.find_spec(name)
        require(spec is not None and spec.origin is not None, "native reporting tool is absent")
        path = regular(Path(spec.origin).resolve(strict=True))
        tools[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    source = source_photo()
    return {"repository": str(ROOT), "HEAD": source["HEAD"], "files_sha256": digest(source["files"]),
            "pytest": version, "pytest_xdist": importlib.metadata.version("pytest-xdist"), "tools": tools}


def identities(rows):
    require(type(rows) is list and bool(rows), "independent main oracle required")
    require(all(type(row) is list and len(row) == 2 and all(type(item) is str and item for item in row)
                for row in rows), "main oracle identity type")
    values = [tuple(row) for row in rows]
    require(len(values) == len(set(values)), "duplicate main oracle identity")
    return values


def workers(values):
    require(type(values) is list and values in (["controller"], ["gw0", "gw1"]), "explicit serial or two-worker scope")
    return values


def exclusive_output(path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    return os.fdopen(descriptor, "wb")


def create_contract(directory, expected, actors):
    from scripts.scan_secrets import _private_evidence

    directory = _private_evidence(Path(directory))
    output = _private_evidence(directory / "actors")
    boundary = {path.name: {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in output.iterdir()}
    require(set(boundary) == ({BOUNDARY} if os.name == "nt" else set()), "private boundary witness inventory")
    rows = [list(row) for row in expected]
    identities(rows)
    workers(actors)
    value = {"schema": SCHEMA, "run_id": uuid.uuid4().hex, "expected": rows,
             "oracle_sha256": digest(rows), "workers": actors, "output": str(output), "boundary": boundary,
             "binding": current_binding()}
    path = directory / "contract.json"
    raw = canonical(value) + b"\n"
    with exclusive_output(path) as stream:
        stream.write(raw)
    return path, hashlib.sha256(raw).hexdigest()


def read_contract(path, expected_sha256, *, check_binding=True):
    from web.services.legacy_object_apply_boundary import verify

    path = regular(path)
    verify(path)
    require(path.stat().st_size <= 8 * 1024**2, "contract size")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha256, "contract hash differs")
    value = json_value(raw)
    require(type(value) is dict and set(value) == {"schema", "run_id", "expected", "oracle_sha256", "workers", "output", "boundary", "binding"},
            "contract fields")
    require(value["schema"] == SCHEMA and type(value["run_id"]) is str
            and re.fullmatch("[0-9a-f]{32}", value["run_id"]) is not None, "contract run identity")
    identities(value["expected"])
    workers(value["workers"])
    require(value["oracle_sha256"] == digest(value["expected"]), "oracle hash differs")
    output = regular(Path(value["output"]), directory=True)
    require(output.parent == path.parent and output.name == "actors", "output namespace differs")
    verify(output, directory=True)
    require(type(value["boundary"]) is dict and set(value["boundary"]) == ({BOUNDARY} if os.name == "nt" else set()),
            "private boundary witness inventory")
    for name, pin in value["boundary"].items():
        witness = regular(output / name)
        require(type(pin) is dict and set(pin) == {"bytes", "sha256"} and type(pin["bytes"]) is int
                and pin["bytes"] == witness.stat().st_size and pin["sha256"] == hashlib.sha256(witness.read_bytes()).hexdigest(),
                "private boundary witness changed")
    if check_binding:
        require(canonical(value["binding"]) == canonical(current_binding()), "source or reporting tools changed")
    return value


def item_identity(item):
    """Use item.name literally, including any :: inside parameter IDs."""
    return node_identity(item.nodeid, item.name)


def node_identity(nodeid, name):
    require(type(nodeid) is str and "::" in nodeid and type(name) is str and bool(name), "owner node identity type")
    path, qualified = nodeid.split("::", 1)
    if qualified == name:
        scope = []
    elif qualified.endswith("::" + name):
        scope = qualified[:-(len(name) + 2)].split("::")
    else:
        raise ValueError("Current39 subtest owner cannot be mapped to its main oracle")
    module = path.removesuffix(".py").replace("\\", "/").replace("/", ".")
    return [".".join([module, *scope]), name]


def integer(value):
    return type(value) is int and value >= 0


def read_actor(path):
    from web.services.legacy_object_apply_boundary import verify

    regular(path)
    verify(path)
    require(path.stat().st_size <= MAX_BYTES, "actor stream size")
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw, "truncated or noncanonical actor stream")
    rows = [json_value(line) for line in raw.splitlines()]
    require(rows and all(type(row) is dict for row in rows), "actor row type")
    require(all(type(row.get("sequence")) is int and row["sequence"] == index
                for index, row in enumerate(rows, 1)), "duplicate or missing event sequence")
    return rows


def require_exact_junit39(raw, expected, contract_path, contract_sha256, actors, *, pytest_exit):
    """Accept only exact main IDs plus completely observed passed subtests."""
    require(type(pytest_exit) is int and pytest_exit == 0, "runtime exit is not zero")
    value = read_contract(contract_path, contract_sha256)
    expected = [list(row) for row in expected]
    wanted = set(identities(expected))
    require(value["expected"] == expected and value["workers"] == actors, "runtime oracle or actor scope differs")
    output = Path(value["output"])
    require({path.name for path in output.iterdir()} == {actor + ".jsonl" for actor in actors} | set(value["boundary"]),
            "missing or foreign actor file")
    owners, owner_ids, counts = {}, {}, {}
    for actor in actors:
        rows = read_actor(output / (actor + ".jsonl"))
        header, collection, footer = rows[0], rows[1] if len(rows) > 1 else {}, rows[-1]
        require(set(header) == {"sequence", "event", "schema", "worker", "run_id", "contract_sha256", "binding"}
                and header["event"] == "header" and header["schema"] == SCHEMA and header["worker"] == actor
                and header["run_id"] == value["run_id"] and header["contract_sha256"] == contract_sha256
                and canonical(header["binding"]) == canonical(value["binding"]), "actor header or binding differs")
        require(set(collection) == {"sequence", "event", "main_count", "oracle_sha256"}
                and collection["event"] == "collection" and type(collection["main_count"]) is int
                and collection["main_count"] == len(wanted) and collection["oracle_sha256"] == value["oracle_sha256"],
                "actor collection differs")
        require(set(footer) == {"sequence", "event", "prior_events", "exitstatus", "owners", "subtests", "issues", "binding_unchanged"}
                and footer["event"] == "footer" and type(footer["prior_events"]) is int
                and footer["prior_events"] == len(rows) - 1 and type(footer["exitstatus"]) is int and footer["exitstatus"] == 0
                and footer["issues"] == [] and footer["binding_unchanged"] is True, "actor lacks complete successful closure")
        local, pending, sub_ids = {}, {}, {}
        for row in rows[2:-1]:
            event = row.get("event")
            require(event in {"subtest", "owner_closed"}, "unknown actor event")
            node = row.get("nodeid")
            require(type(node) is str and node and node not in local, "duplicate or late owner event")
            identity = row.get("identity")
            require(type(identity) is list and len(identity) == 2 and all(type(item) is str for item in identity)
                    and tuple(identity) in wanted and node_identity(node, identity[1]) == identity, "foreign owner identity")
            if event == "subtest":
                require(set(row) == {"sequence", "event", "nodeid", "identity", "report_class", "when", "outcome", "ordinal", "context_sha256"}
                        and row["report_class"] == SUBTEST_CLASS and row["when"] == "call" and row["outcome"] == "passed",
                        "subtest type, failure or skip")
                previous = pending.get(node, 0)
                require(type(row["ordinal"]) is int and row["ordinal"] == previous + 1, "duplicate or missing subtest ordinal")
                require(type(row["context_sha256"]) is str and re.fullmatch("[0-9a-f]{64}", row["context_sha256"]) is not None,
                        "subtest context digest")
                require(node not in sub_ids or sub_ids[node] == identity, "subtest owner identity changed")
                pending[node] = previous + 1
                sub_ids[node] = identity
            else:
                require(set(row) == {"sequence", "event", "nodeid", "identity", "phases", "subtests", "lifecycle_complete"}
                        and canonical(row["phases"]) == canonical(PHASES) and row["lifecycle_complete"] is True
                        and integer(row["subtests"]) and row["subtests"] == pending.get(node, 0), "owner lifecycle or subtest count differs")
                require(node not in owners and tuple(identity) not in owner_ids, "owner repeated across workers")
                require(node not in sub_ids or sub_ids[node] == identity, "closed owner identity changed")
                local[node] = row
                owners[node] = actor
                owner_ids[tuple(identity)] = node
                counts[tuple(identity)] = row["subtests"]
        require(set(pending) <= set(local), "subtest owner never closed")
        require(integer(footer["owners"]) and footer["owners"] == len(local)
                and integer(footer["subtests"]) and footer["subtests"] == sum(row["subtests"] for row in local.values()),
                "actor footer counters differ")
    require(set(owner_ids) == wanted, "missing main owner closure")
    require(type(raw) is bytes and len(raw) <= MAX_BYTES and b"\0" not in raw, "unsupported JUnit UTF-8 XML")
    text = raw.decode("utf8")
    require("<!DOCTYPE" not in text.upper() and "<!ENTITY" not in text.upper(), "unsupported JUnit XML")
    declaration = re.match(r"^\ufeff?<\?xml\b[^?]*\bencoding\s*=\s*['\"]([^'\"]+)['\"]", text, re.I)
    require(declaration is None or declaration[1].lower() == "utf-8", "unsupported JUnit UTF-8 encoding")
    root = ET.fromstring(text)
    require(root.tag in {"testsuite", "testsuites"}, "JUnit root differs")
    require(not any(list(root.iter(tag)) for tag in ("failure", "error", "skipped")), "JUnit contains failure, error or skip")
    cases = list(root.iter("testcase"))
    actual = [(case.get("classname"), case.get("name")) for case in cases]
    require(len(actual) == len(set(actual)) and set(actual) == wanted, "JUnit main identities differ")
    suites = list(root.iter("testsuite"))
    require(bool(suites), "JUnit suites missing")
    for suite in suites:
        selected = [(case.get("classname"), case.get("name")) for case in suite.iter("testcase")]
        for key in ("tests", "errors", "failures", "skipped"):
            require(re.fullmatch("0|[1-9][0-9]*", suite.get(key, "")) is not None, "JUnit declared counter type")
        require(all(suite.get(key) == "0" for key in ("errors", "failures", "skipped")), "JUnit declared failure or skip")
        require(int(suite.get("tests")) == len(selected) + sum(counts[identity] for identity in selected),
                "JUnit total is not exact main IDs plus observed subtests")
    subtests = sum(counts.values())
    return {"subtests_passed": subtests, "subtest_main_owners": len(owner_ids),
            "junit_declared_total": len(wanted) + subtests, "subtest_evidence_complete": True}
