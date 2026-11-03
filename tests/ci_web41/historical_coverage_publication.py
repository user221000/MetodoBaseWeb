"""Publish typed measured coverage without private source-symbol metadata.

Original coverage and acceptance inputs remain unchanged. The original pinned
publication scanner still checks every public byte. No test acceptance or
runtime execution is inferred from publishing an existing report.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import math
import os
import re
import stat
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath

MAX_BYTES = 32 * 1024**2
SCANNERS = {
    "tests/ci_mfa31/publish.py": "e7f2b8c190c59e01919a0d104d2ced79e10ebea0e7051f32ffa0686b73cf09fd",
    "tests/ci_google33/publish.py": "ee0820ff6f4758ddf87af2202979a8ddba8c81e4a79a516fae0f42ede1221df9",
}
BASE_HELPER_SHA = "439cdafa61a00965bd46028f23a0dfb8758c5acceab2bf23d9d23664e1e53ed4"
FILE_KEYS = {"executed_lines", "summary", "missing_lines", "excluded_lines", "executed_branches",
             "missing_branches", "functions", "classes"}
COUNTERS = {"covered_lines", "num_statements", "missing_lines", "excluded_lines", "num_branches",
            "num_partial_branches", "covered_branches", "missing_branches"}
PERCENTS = {"percent_covered", "percent_statements_covered", "percent_branches_covered"}
FILES = {"coverage.json", "coverage.xml", "pytest-web.xml", "pytest-web-shuffle.xml", "pytest-storage-sdk.xml"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def plain(path):
    path = Path(path)
    before = path.lstat()
    if (not path.is_absolute() or path.resolve(strict=True) != path.absolute()
            or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or getattr(before, "st_file_attributes", 0) & 1024 or before.st_size > MAX_BYTES):
        raise ValueError("Unsupported publication input")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    after = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if identity(before) != identity(after) or len(raw) > MAX_BYTES:
        raise ValueError("Publication input changed")
    return raw


def unique_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate publication JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


class Sources:
    def __init__(self, root, commit):
        self.root = Path(root)
        if (not self.root.is_absolute() or self.root.resolve(strict=True) != self.root.absolute()
                or not re.fullmatch("[0-9a-f]{40}", commit)):
            raise ValueError("Unsupported measured source")
        self.commit = commit
        if self.git("rev-parse", "HEAD").decode().strip() != commit:
            raise ValueError("Measured source HEAD differs")
        if Path(self.git("rev-parse", "--show-toplevel").decode().strip()).resolve() != self.root:
            raise ValueError("Measured source root differs")
        self.cache = {}
        self.observed = {}

    def git(self, *args):
        environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
        environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(self.root), *args],
                                       env=environment, stderr=subprocess.PIPE, timeout=30)

    def code(self, name):
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_./-]*", name)
                or PurePosixPath(name).as_posix() != name or ".." in PurePosixPath(name).parts):
            raise ValueError("Unsupported measured source path")
        if name not in self.cache:
            listing = self.git("ls-tree", "-z", self.commit, "--", name).split(b"\0")
            if len(listing) != 2 or not re.fullmatch(rb"100(?:644|755) blob [0-9a-f]{40}\t" + re.escape(name.encode()), listing[0]):
                raise ValueError("Measured source is not a regular Git blob")
            size = self.git("cat-file", "-s", self.commit + ":" + name)
            if not re.fullmatch(rb"(?:0|[1-9][0-9]{0,8})\n", size) or int(size) > MAX_BYTES:
                raise ValueError("Measured Git blob exceeds publication boundary")
            raw = self.git("show", self.commit + ":" + name)
            if len(raw) != int(size):
                raise ValueError("Measured Git blob size changed")
            observed = plain(self.root / name)
            if observed not in {raw, raw.replace(b"\n", b"\r\n") if b"\r" not in raw else raw}:
                raise ValueError("Measured source bytes differ")
            self.cache[name] = raw
            self.observed[name] = digest(observed)
        return self.cache[name]

    def finish(self):
        if (self.git("rev-parse", "HEAD").decode().strip() != self.commit
                or any(digest(plain(self.root / name)) != value for name, value in self.observed.items())):
            raise ValueError("Measured source changed during publication")

    def scanner(self):
        namespace = {"re": re, "io": io, "zipfile": zipfile, "ET": ET,
                     "PurePosixPath": PurePosixPath, "unicodedata": unicodedata}
        helper = self.code("tests/run_reviewed_ci30.py")
        if digest(helper) != BASE_HELPER_SHA:
            raise ValueError("Original path scanner helper differs")
        tree = ast.parse(helper)
        nodes = [n for n in tree.body if (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEVICES" for t in n.targets))
                 or (isinstance(n, ast.FunctionDef) and n.name in {"require", "canonical_name"})]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "<pinned-path-functions>", "exec"), namespace)  # noqa: S102 -- unchanged pinned AST functions
        admitted = []
        for path, pin in SCANNERS.items():
            try:
                raw = self.code(path)
            except subprocess.CalledProcessError:
                continue
            if digest(raw) == pin:
                admitted.append(raw)
                break
        if not admitted:
            raise ValueError("No unchanged original publication scanner")
        tree = ast.parse(admitted[0])
        nodes = [n for n in tree.body if (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"TOKEN", "CSRF", "FACTOR"} for t in n.targets))
                 or (isinstance(n, ast.FunctionDef) and n.name in {"scan", "xml_projection"})]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "<pinned-original-publication-functions>", "exec"), namespace)  # noqa: S102 -- unchanged scanner and XML privacy projection
        return namespace


def summary(value, counts):
    if not isinstance(value, dict) or set(value) != COUNTERS | PERCENTS | {p + "_display" for p in PERCENTS}:
        raise ValueError("Unsupported coverage summary")
    if any(type(value[k]) is not int or value[k] < 0 or value[k] != counts[k] for k in COUNTERS):
        raise ValueError("Coverage counters differ from measured lines or arcs")
    ratios = {
        "percent_covered": (value["covered_lines"] + value["covered_branches"], value["num_statements"] + value["num_branches"]),
        "percent_statements_covered": (value["covered_lines"], value["num_statements"]),
        "percent_branches_covered": (value["covered_branches"], value["num_branches"]),
    }
    for key, (numerator, denominator) in ratios.items():
        expected = 100 * numerator / denominator if denominator else 100.0
        if type(value[key]) not in {int, float} or not math.isfinite(value[key]) or not math.isclose(value[key], expected, abs_tol=1e-9):
            raise ValueError("Coverage percentage differs from measured counts")
        display = value[key + "_display"]
        if not isinstance(display, str) or not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,6})?", display):
            raise ValueError("Unsupported coverage display percentage")
        decimals = len(display.partition(".")[2])
        if abs(float(display) - expected) > 0.500001 * 10 ** -decimals:
            raise ValueError("Coverage display percentage differs")


def coverage_json(raw, sources):
    value = unique_json(raw)
    if not isinstance(value, dict) or set(value) != {"meta", "files", "totals"}:
        raise ValueError("Expected measured coverage JSON")
    meta = value["meta"]
    if (not isinstance(meta, dict) or set(meta) != {"format", "version", "timestamp", "branch_coverage", "show_contexts"}
            or type(meta["format"]) is not int or meta["format"] != 3 or meta["version"] != "7.16.2"
            or meta["branch_coverage"] is not True or meta["show_contexts"] is not False
            or not isinstance(meta["timestamp"], str) or not re.fullmatch(r"[0-9T:.+Z-]{19,40}", meta["timestamp"])
            or sources.code("requirements-test.lock").count(b"coverage==7.16.2 \\") != 1):
        raise ValueError("Unsupported measured coverage format or producer")
    files = value["files"]
    if not isinstance(files, dict) or not 0 < len(files) <= 5000:
        raise ValueError("Measured coverage files are absent or excessive")
    total = dict.fromkeys(COUNTERS, 0)
    normalized = {}
    projected = {}
    for name, row in files.items():
        path = name.replace("\\", "/")
        if path in normalized or not path.endswith(".py"):
            raise ValueError("Ambiguous measured coverage path")
        code = sources.code(path)
        line_count = len(code.splitlines())
        tree = ast.parse(code)
        leaf = tree.body[-1] if tree.body else None
        while isinstance(leaf, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and leaf.body:
            leaf = leaf.body[-1]
        # coverage7.16.2 can include the virtual EOF line when an excluded
        # ellipsis suite ends the authenticated source. It is never execution.
        excluded_eof = (isinstance(leaf, ast.Expr) and isinstance(leaf.value, ast.Constant)
                        and leaf.value.value is Ellipsis and leaf.end_lineno == line_count)
        if not isinstance(row, dict) or set(row) != FILE_KEYS or not all(isinstance(row[k], dict) for k in ("functions", "classes")):
            raise ValueError("Unsupported measured coverage file fields")
        for key in ("executed_lines", "missing_lines", "excluded_lines"):
            seq = row[key]
            limit = line_count + int(key == "excluded_lines" and excluded_eof)
            if (not isinstance(seq, list) or any(type(n) is not int or not 0 < n <= limit for n in seq)
                    or seq != sorted(set(seq))):
                raise ValueError("Unsupported measured coverage line positions")
        executed, missing, excluded = (set(row[k]) for k in ("executed_lines", "missing_lines", "excluded_lines"))
        if executed & missing or executed & excluded or missing & excluded:
            raise ValueError("Coverage line partitions overlap")
        arcs = {}
        for key in ("executed_branches", "missing_branches"):
            seq = row[key]
            if (not isinstance(seq, list) or any(not isinstance(a, list) or len(a) != 2
                    or any(type(n) is not int or n == 0 or abs(n) > line_count for n in a) for a in seq)):
                raise ValueError("Unsupported measured coverage arcs")
            arcs[key] = {tuple(a) for a in seq}
            if len(arcs[key]) != len(seq) or seq != sorted(seq) or any(a <= 0 for a, _ in arcs[key]):
                raise ValueError("Ambiguous measured coverage arcs")
        if arcs["executed_branches"] & arcs["missing_branches"]:
            raise ValueError("Coverage arc partitions overlap")
        counts = {"covered_lines": len(executed), "num_statements": len(executed | missing),
                  "missing_lines": len(missing), "excluded_lines": len(excluded),
                  "num_branches": len(arcs["executed_branches"] | arcs["missing_branches"]),
                  "covered_branches": len(arcs["executed_branches"]), "missing_branches": len(arcs["missing_branches"]),
                  "num_partial_branches": sum(a in executed for a, _ in arcs["missing_branches"])}
        summary(row["summary"], counts)
        for key in COUNTERS:
            total[key] += counts[key]
        projected[name] = {k: v for k, v in row.items() if k not in {"functions", "classes"}}
        normalized[path] = projected[name]
    summary(value["totals"], total)
    if total["covered_lines"] == 0 or total["num_statements"] == 0:
        raise ValueError("Coverage contains no measured execution")
    output = {"meta": meta, "files": projected, "totals": value["totals"]}
    return (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode(), normalized


def coverage_xml(raw, files, sources):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unsupported coverage XML declaration")
    root = ET.fromstring(raw)
    if root.tag != "coverage" or root.get("version") != "7.16.2":
        raise ValueError("Expected measured coverage XML")
    totals = {key: sum(row["summary"][key] for row in files.values()) for key in COUNTERS}
    for xml_key, json_key in (("lines-valid", "num_statements"), ("lines-covered", "covered_lines"),
                              ("branches-valid", "num_branches"), ("branches-covered", "covered_branches")):
        if root.get(xml_key) != str(totals[json_key]):
            raise ValueError("Coverage XML/JSON totals differ")
    attributes = {"coverage": {"version", "timestamp", "lines-valid", "lines-covered", "line-rate", "branches-valid", "branches-covered", "branch-rate", "complexity"},
                  "source": set(), "sources": set(), "packages": set(), "classes": set(), "methods": set(), "lines": set(),
                  "package": {"name", "line-rate", "branch-rate", "complexity"},
                  "class": {"name", "filename", "line-rate", "branch-rate", "complexity"},
                  "line": {"number", "hits", "branch", "condition-coverage", "missing-branches"}}
    classes = list(root.iter("class"))
    if not classes or len(classes) > len(files):
        raise ValueError("Coverage XML classes absent or excessive")
    hierarchy = {"coverage": {"sources", "packages"}, "sources": {"source"}, "source": set(),
                 "packages": {"package"}, "package": {"classes"}, "classes": {"class"},
                 "class": {"methods", "lines"}, "methods": set(), "lines": {"line"}, "line": set()}
    prefixes = []
    for node in root.iter():
        if node.tag not in attributes or not set(node.attrib) <= attributes[node.tag]:
            raise ValueError("Unsupported coverage XML fields")
        if any(child.tag not in hierarchy[node.tag] for child in node):
            raise ValueError("Unsupported coverage XML hierarchy")
        if node.tag == "source":
            text = node.text or ""
            target = Path(text)
            if not target.is_absolute() or target.resolve(strict=True) != target.absolute() or not target.is_relative_to(sources.root):
                raise ValueError("Unbound coverage XML source root")
            relative = target.relative_to(sources.root).as_posix()
            if relative != "." and not any(name.startswith(relative + "/") for name in files):
                raise ValueError("Coverage XML source directory is not measured")
            node.text = relative
            prefixes.append(relative)
        elif node.text and node.text.strip():
            raise ValueError("Unexpected coverage XML text")
        if node.tail and node.tail.strip():
            raise ValueError("Unexpected coverage XML tail")
        for key, text in node.attrib.items():
            if key == "version":
                valid = text == "7.16.2"
            elif key in {"filename", "name"}:
                valid = bool(re.fullmatch(r"[A-Za-z0-9_./-]+", text)) and ".." not in text.split("/")
            elif key == "branch":
                valid = text == "true"
            elif key == "condition-coverage":
                valid = bool(re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]+)?% \([0-9]+/[1-9][0-9]*\)", text))
            elif key == "missing-branches":
                valid = bool(re.fullmatch(r"(?:exit|[1-9][0-9]*)(?:,(?:exit|[1-9][0-9]*))*", text))
            else:
                valid = bool(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text))
                if key == "complexity":
                    valid = valid and text == "0"
            if not valid:
                raise ValueError("Unsupported coverage XML attribute value")

    def rate(text, numerator, denominator):
        expected = numerator / denominator if denominator else 1.0
        return text is not None and math.isclose(float(text), expected, rel_tol=0.00051, abs_tol=1e-10)

    if not rate(root.get("line-rate"), totals["covered_lines"], totals["num_statements"]) or not rate(
            root.get("branch-rate"), totals["covered_branches"], totals["num_branches"]):
        raise ValueError("Coverage XML total rates differ")
    grouped = {}
    for path, row in files.items():
        matching = [p for p in prefixes if p == "." or path.startswith(p + "/")]
        if not matching:
            raise ValueError("Measured JSON file has no XML source")
        prefix = max(matching, key=len)
        relative = path if prefix == "." else path[len(prefix) + 1:]
        package = PurePosixPath(relative).parent.as_posix().replace("/", ".")
        counts = grouped.setdefault(package, dict.fromkeys(COUNTERS, 0))
        for key in COUNTERS:
            counts[key] += row["summary"][key]
    package_nodes = list(root.findall("packages/package"))
    if len(package_nodes) != len(grouped) or {p.get("name") for p in package_nodes} != set(grouped):
        raise ValueError("Coverage XML package inventory differs")
    for node in package_nodes:
        counts = grouped[node.get("name")]
        if not rate(node.get("line-rate"), counts["covered_lines"], counts["num_statements"]) or not rate(
                node.get("branch-rate"), counts["covered_branches"], counts["num_branches"]):
            raise ValueError("Coverage XML package rates differ")
    seen = set()
    for node in classes:
        filename = node.get("filename", "")
        if filename in seen:
            raise ValueError("Duplicate coverage XML filename")
        seen.add(filename)
        candidates = [row for path, row in files.items() if path == filename or path.endswith("/" + filename)]
        if not candidates or node.get("name") != PurePosixPath(filename).name:
            raise ValueError("Unbound coverage XML filename")
        observed = []
        for line in node.findall("lines/line"):
            number = int(line.get("number", "0"))
            hits = line.get("hits")
            if number <= 0 or hits not in {"0", "1"}:
                raise ValueError("Unsupported coverage XML line measurement")
            observed.append((number, hits == "1"))
        def branch_measurements_match(row, class_node=node):
            for line in class_node.findall("lines/line"):
                number = int(line.get("number"))
                executed = [b for a, b in row["executed_branches"] if a == number]
                missing = [b for a, b in row["missing_branches"] if a == number]
                if not executed and not missing:
                    if set(line.attrib) != {"number", "hits"}:
                        return False
                    continue
                keys = {"number", "hits", "branch", "condition-coverage"} | ({"missing-branches"} if missing else set())
                match = re.fullmatch(r"([0-9.]+)% \(([0-9]+)/([0-9]+)\)", line.get("condition-coverage", ""))
                if (set(line.attrib) != keys or line.get("branch") != "true" or match is None
                        or int(match[2]) != len(executed) or int(match[3]) != len(executed) + len(missing)
                        or abs(float(match[1]) - 100 * len(executed) / (len(executed) + len(missing))) >= 1):
                    return False
                if missing and set(line.get("missing-branches", "").split(",")) != {"exit" if b < 0 else str(b) for b in missing}:
                    return False
            return True
        if len(observed) != len({n for n, _ in observed}) or not any(
                dict(observed) == {**dict.fromkeys(row["missing_lines"], False), **dict.fromkeys(row["executed_lines"], True)}
                and rate(node.get("line-rate"), row["summary"]["covered_lines"], row["summary"]["num_statements"])
                and rate(node.get("branch-rate"), row["summary"]["covered_branches"], row["summary"]["num_branches"])
                and branch_measurements_match(row) for row in candidates):
            raise ValueError("Coverage XML/JSON line measurements differ")
    return ET.tostring(root, encoding="utf8", xml_declaration=True)


def publish(source, commit, directory, output, names):
    sources = Sources(source, commit)
    scanner = sources.scanner()
    directory, output = Path(directory), Path(output)
    if (not directory.is_absolute() or directory.resolve(strict=True) != directory.absolute()
            or not output.is_absolute() or output.resolve(strict=False) != output.absolute() or output.exists()
            or output.is_relative_to(directory) or output.is_relative_to(sources.root)
            or set(names) - FILES or len(names) != len(set(names)) or not {"coverage.json", "coverage.xml"} <= set(names)):
        raise ValueError("Explicit distinct publication files and new external output required")
    inputs = {name: plain(directory / name) for name in names}
    projected_json, measured_files = coverage_json(inputs["coverage.json"], sources)
    outputs = {"coverage.json": projected_json, "coverage.xml": coverage_xml(inputs["coverage.xml"], measured_files, sources)}
    for name, raw in inputs.items():
        if name not in outputs:
            outputs[name] = scanner["xml_projection"](raw)
    for raw in outputs.values():
        scanner["scan"](raw)
    sources.finish()
    if inputs != {name: plain(directory / name) for name in names}:
        raise ValueError("Publication source or original measurements changed")
    output.mkdir(mode=0o700)
    manifest = []
    for name in names:
        with (output / name).open("xb") as stream:
            stream.write(outputs[name])
        manifest.append({"path": name, "raw_sha256": digest(inputs[name]), "public_sha256": digest(outputs[name]), "bytes": len(outputs[name])})
    receipt = {"schema": "typed-measured-coverage-publication-v1", "source_commit": commit, "files": manifest,
               "measured_source_files": len(measured_files), "source_file_sha256": {name: digest(sources.code(name)) for name in sorted(measured_files)},
               "omitted_private_fields": ["functions", "classes"], "all_other_JSON_measurements_unchanged": True,
               "original_scanner_unchanged": True, "original_measurements_unchanged": True,
               "runtime_execution_attested": False, "test_acceptance_inferred": False, "private_raw_uploaded": False}
    raw = (json.dumps(receipt, indent=2) + "\n").encode()
    scanner["scan"](raw)
    with (output / "publication.json").open("xb") as stream:
        stream.write(raw)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--files", nargs="+", required=True)
    args = parser.parse_args()
    publish(args.source, args.source_commit, args.directory, args.output, args.files)


if __name__ == "__main__":
    main()
