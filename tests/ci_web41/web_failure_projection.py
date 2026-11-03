"""Static Git test locations only; never emit parameter IDs or assertion text.

This is diagnostic metadata, not runtime code attestation or an acceptance gate.
The original runner still owns its exit code, JUnit and coverage decisions.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

MAX_REPORT = 64 * 1024 * 1024
MAX_MANIFEST = 8 * 1024 * 1024
MAX_PHOTO = 16 * 1024 * 1024
MAX_ROWS = 20000
MAX_XML_NODES = 200000
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,159}\Z")
MODULE = re.compile(r"tests(?:\.[A-Za-z_][A-Za-z0-9_]{0,159}){1,15}\Z")
TEST_PATH = re.compile(r"tests/(?:[A-Za-z_][A-Za-z0-9_]*/)*(?:test_|integration_)[A-Za-z0-9_]+\.py\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")

# Exactly three existing pytest identities exceed the ordinary4096 boundary.
# Digests cover the complete private [classname, name] JSON pair; no parameter
# value is stored here or emitted. Source pins are canonical Git blob bytes.
# Subsets may contain only the applicable entries. The original runner still
# owns full collection identity equality and acceptance; this only locates RED.
LONG_IDENTITIES = {
    "edc50555adb86c2bf14013516a8aadf3b89603d526e50897f206c95ee43914cb": (
        "tests.test_nutrition35_profile_contract", 16452,
        "tests/test_nutrition35_profile_contract.py",
        "test_corrupt_stored_declarations_fail_instead_of_becoming_unknown",
        "1737cd4130b708d08f159eff5d3fa6138e3600814ee76de6b08f5abe6d471c38",
    ),
    "8667dcdebbbcd9e69f455f17c21cc68050709d2d786588405c6c382ee8ee25f2": (
        "tests.test_web_api_contract_audit", 4194,
        "tests/test_web_api_contract_audit.py",
        "test_documented_transport_rejections_do_not_reach_provider",
        "33420e2382e6a7af4b0c1e2c3bc34bdc9844033c7b5bafc06107d604030f4d70",
    ),
    "be69b6fafc7b2ad771fa945db6a783bf54610584bd21c3545b7a1816fcac676f": (
        "tests.test_web_api_contract_audit", 4199,
        "tests/test_web_api_contract_audit.py",
        "test_documented_transport_rejections_do_not_reach_provider",
        "33420e2382e6a7af4b0c1e2c3bc34bdc9844033c7b5bafc06107d604030f4d70",
    ),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def plain_bytes(path, limit):
    """No aliases, reparse points, hardlinks, unbounded reads or changed inputs."""
    path = Path(path)
    before = path.lstat()
    if (not path.is_absolute() or path.absolute() != path.resolve(strict=True)
            or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or getattr(before, "st_file_attributes", 0) & 1024 or before.st_size > limit):
        raise ValueError("Unsupported diagnostic input")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    after = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if len(raw) > limit or identity(before) != identity(after):
        raise ValueError("Unsupported diagnostic input")
    return raw


class GitSources:
    """Read Git blobs without checkout filters, imports or executing test code."""
    def __init__(self, root, source, file_photo):
        self.root = Path(root)
        if (not self.root.is_absolute() or self.root.resolve(strict=True) != self.root.absolute()
                or not HEX40.fullmatch(source) or not isinstance(file_photo, dict)
                or len(file_photo) > 25000):
            raise ValueError("Unsupported diagnostic source")
        self.source = source
        self.photo = file_photo
        if self.git("rev-parse", "HEAD").decode().strip() != source:
            raise ValueError("Diagnostic source differs")
        top = Path(self.git("rev-parse", "--show-toplevel").decode().strip())
        if top.resolve(strict=True) != self.root:
            raise ValueError("Diagnostic source differs")
        self.metadata_directories = {
            Path(self.git("rev-parse", "--absolute-git-dir").decode().strip()),
            Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()),
        }
        self.closed_attributes()
        raw = self.git("ls-tree", "-r", "-z", "--full-tree", source, "--", "tests")
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Diagnostic source inventory exceeds limit")
        self.files = {}
        for line in raw.split(b"\0"):
            if not line:
                continue
            metadata, name = line.split(b"\t", 1)
            mode, kind, blob = metadata.decode("ascii").split()
            name = name.decode("utf8")
            if (mode in {"100644", "100755"} and kind == "blob"
                    and HEX40.fullmatch(blob) and TEST_PATH.fullmatch(name)):
                if name in self.files:
                    raise ValueError("Ambiguous diagnostic source")
                self.files[name] = blob
        self.cache = {}

    def git(self, *arguments):
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_ATTR_NOSYSTEM="1", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        result = subprocess.run(["git", "--no-replace-objects", "-c", "core.attributesFile=", "-C", str(self.root), *arguments],
                                capture_output=True, check=True, timeout=15, env=environment)
        return result.stdout

    def closed_attributes(self):
        snapshots = []
        for directory in sorted(self.metadata_directories):
            if not directory.is_absolute() or directory.resolve(strict=True) != directory.absolute():
                raise ValueError("Unsupported Git metadata boundary")
            path = directory / "info/attributes"
            try:
                info = path.lstat()
            except FileNotFoundError:
                if path.resolve(strict=False) != path.absolute():
                    raise ValueError("Unsupported Git attributes boundary") from None
                snapshots.append((str(path), None))
                continue
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != 0
                    or getattr(info, "st_file_attributes", 0) & 1024
                    or path.resolve(strict=True) != path.absolute()):
                raise ValueError("Uncommitted Git attributes are not admitted")
            snapshots.append((str(path), info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns))
        return snapshots

    def code(self, name):
        if name not in self.files:
            raise ValueError("Untracked diagnostic source")
        if name not in self.cache:
            blob = self.files[name]
            size = int(self.git("cat-file", "-s", blob))
            if not 0 < size <= 1024 * 1024:
                raise ValueError("Diagnostic test source exceeds limit")
            raw = self.git("cat-file", "blob", blob)
            observed = self.photo.get(name)
            if not isinstance(observed, str) or not HEX64.fullmatch(observed):
                raise ValueError("Test source was not photographed")
            frames = {digest(raw)}
            closed = self.closed_attributes()
            attributes = self.git("check-attr", "--source=" + self.source, "-z", "text", "eol", "filter", "working-tree-encoding", "--", name).split(b"\0")
            if self.closed_attributes() != closed:
                raise ValueError("Git attributes boundary changed")
            values = {attributes[index + 1]: attributes[index + 2]
                      for index in range(0, len(attributes) - 1, 3)}
            if values.get(b"filter") != b"unspecified" or values.get(b"working-tree-encoding") != b"unspecified":
                raise ValueError("Unsupported source transport")
            if (values.get(b"text") in {b"unspecified", b"set", b"auto"}
                    and values.get(b"eol") in {b"unspecified", b"lf", b"crlf"}
                    and b"\r" not in raw):
                frames.add(digest(raw.replace(b"\n", b"\r\n")))
            if observed not in frames:
                raise ValueError("Photographed source differs from Git")
            tree = ast.parse(raw)
            if sum(1 for _ in ast.walk(tree)) > 50000:
                raise ValueError("Diagnostic AST exceeds limit")
            self.cache[name] = (raw, tree)
        return self.cache[name]

    def location(self, classname, name):
        if (not isinstance(classname, str) or not MODULE.fullmatch(classname)
                or not isinstance(name, str) or not 0 < len(name) <= 4096
                or any(ord(char) < 32 or char == "\\" for char in name)):
            return None
        pieces = classname.split(".")
        candidates = []
        for end in range(2, len(pieces) + 1):
            path = "/".join(pieces[:end]) + ".py"
            if path in self.files:
                candidates.append((path, pieces[end:]))
        if len(candidates) != 1:
            return None
        path, scopes = candidates[0]
        try:
            raw, tree = self.code(path)
        except (ValueError, SyntaxError, UnicodeError):
            return None
        base, bracket, remainder = name.partition("[")
        valid_name = IDENTIFIER.fullmatch(base) and base.startswith("test_")
        if bracket and (not remainder.endswith("]") or "[" in remainder):
            valid_name = False
        namespace = tree.body
        if scopes:
            valid_name = valid_name and all(IDENTIFIER.fullmatch(part) and part.startswith("Test") for part in scopes)
            for scope in scopes:
                classes = [node for node in namespace if isinstance(node, ast.ClassDef) and node.name == scope]
                if len(classes) != 1:
                    valid_name = False
                    break
                namespace = classes[0].body
        definitions = [node for node in namespace if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == base]
        symbol = {"classes": scopes, "function": base} if valid_name and len(definitions) == 1 else None
        return {"path": path, "blob_sha1": self.files[path], "source_sha256": digest(raw), "symbol": symbol}


def long_locations(expected, sources):
    """Authenticate finite long IDs without relaxing the ordinary lookup guard.

    Matching/report accounting retains the original identity. Only the short,
    reviewed function name reaches the existing static source resolver.
    Authenticate even passed or unreported oracle members before projecting.
    """
    locations = {}
    for classname, name in expected:
        if len(name) <= 4096:
            continue
        if not any((classname, len(name)) == entry[:2] for entry in LONG_IDENTITIES.values()):
            raise ValueError("Unsupported long diagnostic identity")
        try:
            identity = json.dumps([classname, name], ensure_ascii=False, separators=(",", ":")).encode("utf8")
        except UnicodeError:
            raise ValueError("Unsupported long diagnostic identity") from None
        entry = LONG_IDENTITIES.get(digest(identity))
        if entry is None or (classname, len(name)) != entry[:2]:
            raise ValueError("Unsupported long diagnostic identity")
        _, _, path, function, source_sha256 = entry
        raw, _ = sources.code(path)
        if digest(raw) != source_sha256:
            raise ValueError("Unreviewed long diagnostic source")
        location = sources.location(classname, function)
        if (location is None or location["path"] != path
                or location["source_sha256"] != source_sha256
                or location["symbol"] != {"classes": [], "function": function}):
            raise ValueError("Unresolved long diagnostic symbol")
        locations[(classname, name)] = location
    return locations


def project(raw, manifest_raw, sources):
    if len(raw) > MAX_REPORT or len(manifest_raw) > MAX_MANIFEST:
        raise ValueError("Diagnostic input exceeds limit")
    text = raw.decode("utf8")
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("Unsupported diagnostic XML")
    encoding = re.search(r'''<\?xml[^>]*encoding\s*=\s*["']([^"']+)["']''', text[:200], re.IGNORECASE)
    if encoding and encoding.group(1).lower().replace("-", "") != "utf8":
        raise ValueError("Unsupported diagnostic XML encoding")
    expected = json.loads(manifest_raw)
    if (not isinstance(expected, list) or not 0 < len(expected) <= MAX_ROWS
            or any(not isinstance(row, list) or len(row) != 2
                   or not isinstance(row[0], str) or not 0 < len(row[0]) <= 4096
                   or not isinstance(row[1], str) or not row[1] for row in expected)):
        raise ValueError("Unsupported diagnostic manifest")
    expected_set = {tuple(row) for row in expected}
    if len(expected_set) != len(expected):
        raise ValueError("Ambiguous diagnostic manifest")
    finite_locations = long_locations(expected, sources)
    document = ET.fromstring(text)
    if document.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Unsupported diagnostic XML")
    nodes = list(document.iter())
    if len(nodes) > MAX_XML_NODES:
        raise ValueError("Diagnostic XML exceeds limit")
    cases = list(document.iter("testcase"))
    if not cases or len(cases) > MAX_ROWS:
        raise ValueError("Diagnostic report exceeds limit")
    counts = Counter()
    groups = {}
    seen = set()
    multiplicity = Counter((case.get("classname"), case.get("name")) for case in cases)
    for case in cases:
        identity = (case.get("classname"), case.get("name"))
        if identity in seen:
            counts["duplicate_report_identity"] += 1
        seen.add(identity)
        markers = [tag for tag in ("failure", "error", "skipped") for _ in case.findall(tag)]
        if len(markers) > 1:
            counts["ambiguous_outcome"] += 1
            continue
        outcome = markers[0] if markers else "passed"
        counts[outcome] += 1
        if outcome == "passed":
            continue
        if multiplicity[identity] != 1:
            counts["ambiguous_report_identity"] += 1
            continue
        if identity not in expected_set:
            counts["unresolved_report_identity"] += 1
            continue
        location = finite_locations.get(identity)
        if location is None:
            location = sources.location(*identity)
        if location is None:
            counts["unresolved_location"] += 1
            continue
        key = location["path"]
        row = groups.setdefault(key, {key: location[key] for key in ("path", "blob_sha1", "source_sha256")})
        row.setdefault("outcomes", Counter())[outcome] += 1
        if location["symbol"] is None:
            row["unresolved_symbol_count"] = row.get("unresolved_symbol_count", 0) + 1
        else:
            symbol = location["symbol"]
            symbol_key = (tuple(symbol["classes"]), symbol["function"], outcome)
            row.setdefault("symbols", Counter())[symbol_key] += 1
    result_rows = []
    for path in sorted(groups):
        row = groups[path]
        symbols = row.pop("symbols", {})
        row["outcomes"] = dict(sorted(row["outcomes"].items()))
        row["symbols"] = [{"classes": list(classes), "function": function, "outcome": outcome, "count": count}
                          for (classes, function, outcome), count in sorted(symbols.items())]
        row.setdefault("unresolved_symbol_count", 0)
        result_rows.append(row)
    if sources.git("rev-parse", "HEAD").decode().strip() != sources.source:
        raise ValueError("Diagnostic source changed")
    sources.closed_attributes()
    return {"schema": "static-git-test-failure-locations-v1", "diagnostic_available": True,
            "source_commit": sources.source, "report_sha256": digest(raw), "manifest_sha256": digest(manifest_raw),
            "manifest_entries": len(expected), "reported_entries": len(cases), "counters": dict(sorted(counts.items())),
            "locations": result_rows, "runtime_code_attestation": False,
            "scope": "Static Git locations only; outcomes and duplicates do not change test acceptance"}


def project_files(root, report, expected):
    report = Path(report)
    raw = plain_bytes(report, MAX_REPORT)
    manifest_raw = plain_bytes(report.parent / "oracle.json", MAX_MANIFEST)
    if json.loads(manifest_raw) != expected:
        raise ValueError("Diagnostic manifest differs from runner")
    before = json.loads(plain_bytes(report.parent / "before.json", MAX_PHOTO))
    source = before["source"]
    result = project(raw, manifest_raw, GitSources(root, source["HEAD"], source["files"]))
    result["source_photo_sha256"] = digest(json.dumps(source["files"], sort_keys=True, separators=(",", ":")).encode())
    return result
