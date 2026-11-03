"""Finite historical failure locations; never format exception payloads.

This standalone stdlib module authenticates a closed source set. Text-derived
locations are labelled as projections, distinct from CodeType observations.
The CLI reads only the two named CI30 private inputs on its POSIX CI runner.
No SQL, Docker, provider, subprocess, application import or service is invoked.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import hashlib
import json
import os
import re
import stat
import xml.etree.ElementTree as ET
from pathlib import Path
from types import CodeType

SCHEMA = "finite-historical-failure-metadata-v2"
MAX_PRIVATE = 8 * 1024**2
MAX_FRAMES = 32
KIND_NAMES = ("AssertionError", "ValueError", "TypeError", "KeyError", "IndexError", "OSError",
              "FileNotFoundError", "PermissionError", "TimeoutError", "RuntimeError", "ImportError",
              "ModuleNotFoundError", "MemoryError", "SystemExit", "KeyboardInterrupt")
KINDS = {getattr(builtins, name): name for name in KIND_NAMES}
ISSUES = frozenset({"input_rejected", "source_changed", "unmapped_failure", "private_log_unavailable",
                    "observer_rejected", "no_exception_observed"})
ROLES = frozenset({"quota_xml", "quota_log", "fixture_log", "driver_log", "browser_error_log"})
QUOTA_CASES = (
    "test_last_credit_accepts_only_one_of_three_processes",
    "test_subscription_get_cannot_erase_or_collide_with_reserved_credit[True]",
    "test_subscription_get_cannot_erase_or_collide_with_reserved_credit[False]",
)
SOURCES = {'30': {'commit': '57335e5b4bcba3c76c97d47e481b526fb52874a6',
        'files': {'tests/integration_quota_postgres.py': {'bytes': 8459,
                                                          'sha256': '6f4d3922e8cd1f3469ebe349acb8903b12ff04df80a1904526a1bd492bb9f4d2',
                                                          'Git_blob': '92fd5548946f0d347842dd2f84a2a70eb3494916'}}},
 '31': {'commit': 'de506b6077ba055587f02e7d839387e7f5c56f84',
        'files': {'tests/ci_mfa31/run_current_browser.py': {'bytes': 15278,
                                                            'sha256': '1fe14e412f04f0c0e879950c3db6e8f246440b36ee7f168f47e3fd88025fe4e0',
                                                            'Git_blob': 'a8422d47b15e6eaa289398735de0a14df7b5758c'},
                  'tests/e2e/run_member_link31_browser.py': {'bytes': 11189,
                                                             'sha256': '44b3ccfc8feb083fcec1c33493d57b5457a23f9292ae115bc7cbfbd5b6ed25e2',
                                                             'Git_blob': '0b53d81701c791efa79c9a9747896a275421792e'},
                  'tests/e2e/member_link31_postgres_server.py': {'bytes': 15062,
                                                                 'sha256': '1ab7d756eac90c10b3c928f94e054f1318106814ec408382838414014ad43c23',
                                                                 'Git_blob': '8c49ec3af7be21c1f958b68dec96945350436d3b'},
                  'tests/integration_schema_migrations.py': {'bytes': 15414,
                                                             'sha256': 'fd36441ac63e20a859c405138dd6c854240836c81ca6690de9039889f3545dae',
                                                             'Git_blob': 'abc1fc07ecd5c2b2be05b825e79dece1c4779ee3'},
                  'tests/integration_client_link_services.py': {'bytes': 18722,
                                                                'sha256': 'aabf3860a46b42cba27c498e12532995619531870d09b1eeff0d9f1867279708',
                                                                'Git_blob': '05329d0798e6af51c67d7f56bee64870722da257'},
                  'web/database/schema_control.py': {'bytes': 5362,
                                                     'sha256': '354bd11178435129b1caab8202bb95412f1172561ad14e9c27c894e0e8a004ca',
                                                     'Git_blob': '498b8799ac95f42261440a1bc9c513ec76b9c0ab'},
                  'web/settings.py': {'bytes': 279,
                                      'sha256': 'a52bf271c8c71854403e9d5a10f567894cf2d682959a8c581efea607669ab920',
                                      'Git_blob': '70edacc22206bb6ab0a2fd0cb5f8f5dd0db1073c'},
                  'config/env_validator.py': {'bytes': 3757,
                                              'sha256': '619b6f808789fc8f5d3179b5aaf15480686812e7f0ee48730ba27a4adadcfed5',
                                              'Git_blob': 'e0084e37c4c252faf9439223006c23d0833d7bdc'}}},
 '33': {'commit': 'c86d1a25fcd0b0befcb4b473c4144917122109fb',
        'files': {'tests/ci_google33/run_current_browser.py': {'bytes': 17278,
                                                               'sha256': '6664f87aab2db016772ebbeee0e234fb6aa2c2e4abbaf6ff014dc93777326ed4',
                                                               'Git_blob': 'dbfe4a5ad7c9e309cc9704add616e2d313ed0d77'},
                  'tests/e2e/run_member_link33_browser.py': {'bytes': 11332,
                                                             'sha256': '0e886f0ac82cebd21664d6cd243e743e2c76f16708627b2153d5587f4f13b95d',
                                                             'Git_blob': 'd91c2cb26c5ddb08a1c939d137d0a853f9628260'},
                  'tests/e2e/member_link33_postgres_server.py': {'bytes': 15260,
                                                                 'sha256': 'feb294dcb5c3563fc93813ed755a57714f7623fcd6dd916ad8742f49ebdb158a',
                                                                 'Git_blob': 'c04c3f6729e3d6299c0d1dbb2d0390661e676949'},
                  'tests/integration_schema_migrations.py': {'bytes': 15414,
                                                             'sha256': 'fd36441ac63e20a859c405138dd6c854240836c81ca6690de9039889f3545dae',
                                                             'Git_blob': 'abc1fc07ecd5c2b2be05b825e79dece1c4779ee3'},
                  'tests/integration_client_link_services.py': {'bytes': 18722,
                                                                'sha256': 'aabf3860a46b42cba27c498e12532995619531870d09b1eeff0d9f1867279708',
                                                                'Git_blob': '05329d0798e6af51c67d7f56bee64870722da257'},
                  'web/database/schema_control.py': {'bytes': 6166,
                                                     'sha256': '9a3aa96eaf79839380a12b8eeeb2e578fbb8520ca3baa462c90a9331c63a90ba',
                                                     'Git_blob': '59b6dfee619dcea65b307628ff8e9af492c820bb'},
                  'web/settings.py': {'bytes': 279,
                                      'sha256': 'a52bf271c8c71854403e9d5a10f567894cf2d682959a8c581efea607669ab920',
                                      'Git_blob': '70edacc22206bb6ab0a2fd0cb5f8f5dd0db1073c'},
                  'config/env_validator.py': {'bytes': 3757,
                                              'sha256': '619b6f808789fc8f5d3179b5aaf15480686812e7f0ee48730ba27a4adadcfed5',
                                              'Git_blob': 'e0084e37c4c252faf9439223006c23d0833d7bdc'}}}}

# These are text-only JavaScript locations, never Python AST or CodeType proof.
CJS_SOURCES = {"31": {"tests/e2e/member_link31_browser.cjs": {
    "bytes": 18150, "sha256": "ce49258340e40f1800aa1405d1460e9cc59cf4f6a05171257282bc0479b009b4",
    "Git_blob": "73ea842fbbc146b6c33f1da25914c359c06cf146", "lines": 83}}}
MISSING_ENTRY = {"33": {
    "path": "tests/e2e/member_link33_browser.cjs",
    "historical_tree": "65dc275f8056b3712de8f8ff0ec28135fd300429",
    "invoker": "tests/e2e/run_member_link33_browser.py", "line": 162}}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path.absolute():
        raise ValueError("Noncanonical diagnostic directory")
    for item in (path, *path.parents):
        value = item.lstat()
        if not stat.S_ISDIR(value.st_mode) or item.is_symlink() or getattr(value, "st_file_attributes", 0) & 1024:
            raise ValueError("Diagnostic directory alias")
    return path


def regular(path):
    path = Path(path)
    directory(path.parent)
    value = path.lstat()
    if (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1 or path.is_symlink()
            or getattr(value, "st_file_attributes", 0) & 1024 or path.resolve(strict=True) != path.absolute()):
        raise ValueError("Diagnostic input alias")
    return path


def read_bounded(path, limit):
    path = regular(path)
    before = path.lstat()
    if not 0 <= before.st_size <= limit:
        raise ValueError("Diagnostic input size")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        # On Windows these APIs expose different ctime meanings. Preserve all
        # five fields within each API; the four common fields still bind the
        # opened handle to the path. POSIX also requires cross-API ctime.
        if (identity(opened)[:4] != identity(before)[:4]
                or os.name != "nt" and identity(opened) != identity(before)):
            raise ValueError("Diagnostic opened identity differs")
        raw = stream.read(limit + 1)
        if identity(os.fstat(stream.fileno())) != identity(opened):
            raise ValueError("Diagnostic opened input changed")
    after = regular(path).lstat()
    if len(raw) != before.st_size or identity(before) != identity(after):
        raise ValueError("Diagnostic input changed")
    return raw, identity(after)


def private_directory(path):
    path = directory(path)
    # The historical CI runs on POSIX. Other platforms fail closed for private
    # raw input; source/AST and payload unit controls remain portable.
    if os.name != "posix" or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private CI boundary unavailable")
    return path


def exception_kind(error):
    return KINDS.get(type(error), "OTHER")


class SourceRegistry:
    def __init__(self, root, schema):
        if type(schema) is not str or schema not in SOURCES:
            raise ValueError("Unreviewed historical schema")
        self.root, self.schema = directory(root), schema
        self.spec = SOURCES[schema]
        self.raw, self.stats, self.codes, self.trees = {}, {}, {}, {}
        for name, pin in self.spec["files"].items():
            raw, info = read_bounded(self.root / name, pin["bytes"])
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                usedforsecurity=False).hexdigest()
            if len(raw) != pin["bytes"] or digest(raw) != pin["sha256"] or blob != pin["Git_blob"]:
                raise ValueError("Historical diagnostic source differs")
            self.raw[name], self.stats[name] = raw, info
            self.trees[name] = ast.parse(raw)
            code = compile(raw, str(self.root / name), "exec", dont_inherit=True)
            def codes(value):
                return (value, *(child for item in value.co_consts if isinstance(item, CodeType) for child in codes(item)))
            self.codes[name] = codes(code)
        self.cjs_raw, self.cjs_stats = {}, {}
        for name, pin in CJS_SOURCES.get(schema, {}).items():
            raw, info = read_bounded(self.root / name, pin["bytes"])
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                                usedforsecurity=False).hexdigest()
            if (len(raw) != pin["bytes"] or digest(raw) != pin["sha256"]
                    or blob != pin["Git_blob"] or len(raw.splitlines()) != pin["lines"]):
                raise ValueError("Historical CJS diagnostic source differs")
            self.cjs_raw[name], self.cjs_stats[name] = raw, info
        self.absent_entry()

    def absent_entry(self):
        if self.schema in MISSING_ENTRY:
            path = self.root / MISSING_ENTRY[self.schema]["path"]
            directory(path.parent)
            if os.path.lexists(path):
                raise ValueError("The original missing entrypoint must remain absent")

    def entrypoint(self):
        if self.schema in CJS_SOURCES:
            name, pin = next(iter(CJS_SOURCES[self.schema].items()))
            return {"path": name, "expected_absent": False, "origin": "authenticated_historical_cjs_source",
                    "source_sha256": pin["sha256"], "source_Git_blob": pin["Git_blob"], "lines": pin["lines"]}
        if self.schema in MISSING_ENTRY:
            self.absent_entry()
            entry = MISSING_ENTRY[self.schema]
            return {"path": entry["path"], "expected_absent": True,
                    "origin": "historical_tree_absence_bound_to_invoker", "historical_tree": entry["historical_tree"],
                    "invoker": self.location(entry["invoker"], entry["line"])}
        return None

    def quiet(self):
        for name, raw in self.raw.items():
            after, info = read_bounded(self.root / name, len(raw))
            if after != raw or info != self.stats[name]:
                raise ValueError("Historical diagnostic source changed")
        for name, raw in self.cjs_raw.items():
            after, info = read_bounded(self.root / name, len(raw))
            if after != raw or info != self.cjs_stats[name]:
                raise ValueError("Historical CJS diagnostic source changed")
        self.absent_entry()
        return True

    def cjs_location(self, name, line, column):
        if (type(name) is not str or name not in self.cjs_raw
                or type(line) is not int or type(column) is not int):
            return None
        lines = self.cjs_raw[name].splitlines()
        if not 1 <= line <= len(lines):
            return None
        # V8 stack columns count UTF-16 code units; include the end-of-line slot.
        width = len(lines[line - 1].decode("utf8").encode("utf-16-le")) // 2
        if not 1 <= column <= min(width + 1, 65536):
            return None
        pin = CJS_SOURCES[self.schema][name]
        return {"path": name, "source_sha256": pin["sha256"], "source_Git_blob": pin["Git_blob"],
                "line": line, "column": column, "line_sha256": digest(lines[line - 1]),
                "origin": "private_cjs_text_projection"}

    def project_cjs_text(self, raw):
        frames = []
        pattern = (r'    at (?:[^()\x00\r\n]{1,256} \(([^\x00\r\n]{1,2048}):([1-9][0-9]{0,5}):([1-9][0-9]{0,5})\)'
                   r'|([^()\x00\r\n]{1,2048}):([1-9][0-9]{0,5}):([1-9][0-9]{0,5}))')
        for line in raw.decode("utf8", errors="replace").splitlines():
            if len(line) > 65536:
                continue
            match = re.fullmatch(pattern, line)
            if match is None:
                continue
            reported, number, column = match.groups()[:3] if match[1] is not None else match.groups()[3:]
            names = [name for name in self.cjs_raw if reported in (name, str(self.root / name))]
            frame = self.cjs_location(names[0], int(number), int(column)) if len(names) == 1 else None
            if frame is not None and frame not in frames and len(frames) < MAX_FRAMES:
                frames.append(frame)
        return frames

    def location(self, name, line):
        if type(name) is not str or name not in self.raw or type(line) is not int:
            return None
        lines = self.raw[name].splitlines()
        if not 1 <= line <= len(lines):
            return None
        nodes = [node for node in ast.walk(self.trees[name]) if isinstance(node, ast.stmt)
                 and node.lineno <= line <= node.end_lineno]
        if not nodes:
            return None
        node = min(nodes, key=lambda value: (value.end_lineno - value.lineno, -value.lineno))
        pin = self.spec["files"][name]
        return {"path": name, "source_sha256": pin["sha256"], "source_Git_blob": pin["Git_blob"],
                "line": line, "line_sha256": digest(lines[line - 1]),
                "AST_span": {"kind": type(node).__name__, "first": node.lineno, "last": node.end_lineno,
                             "sha256": digest(ast.dump(node, include_attributes=False).encode())}}

    def code_location(self, code, line):
        for name, codes in self.codes.items():
            if code.co_filename == str(self.root / name) and any(code == expected for expected in codes):
                return self.location(name, line)
        return None

    def traceback(self, error):
        result, frame, count = [], BaseException.__traceback__.__get__(error), 0
        while frame is not None and count < 128:
            value = self.code_location(frame.tb_frame.f_code, frame.tb_lineno)
            if value is not None and value not in result and len(result) < MAX_FRAMES:
                result.append(value)
            count += 1
            frame = frame.tb_next
        return result

    def project_text(self, raw):
        frames, kinds = [], []
        for line in raw.decode("utf8", errors="replace").splitlines():
            if len(line) > 65536:
                continue
            match = re.fullmatch(r'\s*File "([^"\x00\r\n]{1,2048})", line ([1-9][0-9]{0,5}), in (?:[A-Za-z_][A-Za-z_0-9]*|<module>)', line)
            if match is None:
                match = re.match(r'^([^\x00\r\n]{1,2048}?\.py):([1-9][0-9]{0,5}): in [A-Za-z_][A-Za-z_0-9]*$', line)
            if match is not None:
                reported = match[1]
                names = [name for name in self.raw if reported in (name, str(self.root / name))]
                value = self.location(names[0], int(match[2])) if len(names) == 1 else None
                if value is not None and value not in frames and len(frames) < MAX_FRAMES:
                    frames.append(value)
            kind = re.match(r'^(?:E\s+)?([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*)(?::|$)', line)
            if kind is not None and kind[1].endswith(("Error", "Exception", "Exit", "Interrupt")):
                value = kind[1] if kind[1] in KIND_NAMES else "OTHER"
                if value not in kinds:
                    kinds.append(value)
        return {"exception_types": kinds, "frames": frames}


def empty(registry, origin):
    if origin not in {"private_xml_projection", "runtime_observer"}:
        raise ValueError("Diagnostic origin differs")
    return {"schema": SCHEMA, "historical_schema": registry.schema, "source_commit": registry.spec["commit"],
            "origin": origin, "diagnostic_accepted": False, "exception_type": "OTHER", "frames": [],
            "private_artifacts": [], "cases": [], "issues": [], "source_unchanged": False,
            "entrypoint": registry.entrypoint()}


def semlock_signature(raw):
    """A private text signature only; no stdlib source or cause is authenticated."""
    active, pending, observed = False, False, False
    for line in raw.decode("utf8", errors="replace").splitlines():
        if len(line) > 65536:
            active = pending = observed = False
            continue
        if line == "Traceback (most recent call last):":
            active, pending, observed = True, False, False
            continue
        if not active:
            continue
        frame = re.fullmatch(r'  File "[^"\x00\r\n]{1,2048}", line [1-9][0-9]{0,5}, in ([A-Za-z_][A-Za-z_0-9]*|<module>)', line)
        if frame is not None:
            pending = frame[1] == "__setstate__"
            continue
        if pending:
            observed |= line == "    self._semlock = _multiprocessing.SemLock._rebuild(*state)"
            pending = False
        if re.fullmatch(r"FileNotFoundError(?::[^\r\n]*)?", line):
            if observed:
                return True
            active = False
        elif line and not line.startswith("    "):
            active = pending = observed = False
    return False


def missing_entry_signature(registry, raw):
    """Require one exact Node entrypoint error block, not a suffix or co-occurrence."""
    if registry.schema not in MISSING_ENTRY:
        return False
    path = registry.root / MISSING_ENTRY[registry.schema]["path"]
    header = "Error: Cannot find module '" + str(path) + "'"
    lines = raw.decode("utf8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line != header:
            continue
        for cursor in range(index + 1, min(len(lines), index + 129)):
            frame = lines[cursor]
            if len(frame) > 65536 or not frame.startswith("    at "):
                break
            if frame.endswith(" {"):
                if lines[cursor + 1:cursor + 4] == ["  code: 'MODULE_NOT_FOUND',", "  requireStack: []", "}"]:
                    return True
                break
    return False


def signature_for(registry, role):
    if registry.schema == "30" and role == "quota_log":
        return {"kind": "spawn_semlock_rebuild_file_not_found", "origin": "private_text_signature"}
    if registry.schema == "33" and role == "driver_log":
        return {"kind": "node_entrypoint_module_not_found", "origin": "private_text_signature"}
    return None


def artifact(registry, role, raw):
    if role not in ROLES or len(raw) > MAX_PRIVATE:
        raise ValueError("Diagnostic artifact scope")
    projected = registry.project_text(raw)
    if registry.schema == "31" and role in {"driver_log", "browser_error_log"}:
        projected["frames"] = (projected["frames"] + registry.project_cjs_text(raw))[:MAX_FRAMES]
    found = ((registry.schema == "30" and role == "quota_log" and semlock_signature(raw))
             or (registry.schema == "33" and role == "driver_log" and missing_entry_signature(registry, raw)))
    return {"role": role, "origin": "private_text_projection", "bytes": len(raw), "sha256": digest(raw),
            **projected, "signals": [signature_for(registry, role)] if found else []}


def quota_cases(tree):
    """Accept only explicit JUnit containers and leaf outcomes, never descendants."""
    def container(node, allowed):
        if ((node.text or "").strip() or any((child.tail or "").strip() for child in node)
                or any(child.tag not in allowed for child in node)):
            raise ValueError("Quota JUnit container grammar")

    def leaf(node):
        if len(node):
            raise ValueError("Quota JUnit leaf grammar")

    def properties(node):
        container(node, {"property"})
        for child in node:
            leaf(child)
            if not child.get("name") or not set(child.attrib) <= {"name", "value"}:
                raise ValueError("Quota JUnit property grammar")

    def contents(node, allowed):
        container(node, allowed)
        for tag in allowed - {"testcase"}:
            if sum(child.tag == tag for child in node) > 1:
                raise ValueError("Duplicate quota JUnit container field")
        for child in node:
            if child.tag == "properties":
                properties(child)
            elif child.tag != "testcase":
                leaf(child)

    if tree.tag == "testsuites":
        container(tree, {"testsuite"})
        suites = list(tree)
    elif tree.tag == "testsuite":
        suites = [tree]
    else:
        raise ValueError("Quota JUnit root")
    cases = []
    for suite in suites:
        contents(suite, {"properties", "testcase", "system-out", "system-err"})
        for case in suite:
            if case.tag == "testcase":
                contents(case, {"properties", "failure", "error", "skipped", "system-out", "system-err"})
                if sum(child.tag in {"failure", "error", "skipped"} for child in case) > 1:
                    raise ValueError("Duplicate quota outcome")
                cases.append(case)
    return cases


def quota_bytes(registry, xml_raw, log_raw):
    if registry.schema != "30" or max(len(xml_raw), len(log_raw)) > MAX_PRIVATE:
        raise ValueError("Quota diagnostic scope")
    if b"<!DOCTYPE" in xml_raw.upper() or b"<!ENTITY" in xml_raw.upper():
        raise ValueError("Quota XML declaration")
    tree = ET.fromstring(xml_raw)
    cases = quota_cases(tree)
    if (len(cases) != 3 or {case.get("classname") for case in cases} != {"tests.integration_quota_postgres"}
            or sorted(case.get("name", "") for case in cases) != sorted(QUOTA_CASES)):
        raise ValueError("The exact three quota identities are required")
    result = empty(registry, "private_xml_projection")
    for name in QUOTA_CASES:
        case = next(case for case in cases if case.get("name") == name)
        outcomes = [node for node in case if node.tag in {"failure", "error", "skipped"}]
        if len(outcomes) > 1:
            raise ValueError("Duplicate quota outcome")
        projected = registry.project_text((outcomes[0].text or "").encode()) if outcomes else {"exception_types": [], "frames": []}
        result["cases"].append({"module": "tests.integration_quota_postgres", "name": name,
            "outcome": outcomes[0].tag if outcomes else "passed",
            "exception_type": projected["exception_types"][-1] if projected["exception_types"] else "OTHER",
            "frames": projected["frames"]})
        if outcomes and not projected["frames"]:
            result["issues"] = ["unmapped_failure"]
    result["private_artifacts"] = [artifact(registry, "quota_xml", xml_raw), artifact(registry, "quota_log", log_raw)]
    result["source_unchanged"] = registry.quiet()
    result["diagnostic_accepted"] = not result["issues"]
    return result


def validate(registry, value):
    template = empty(registry, value.get("origin"))
    if (set(value) != set(template) or value["schema"] != SCHEMA or value["historical_schema"] != registry.schema
            or value["source_commit"] != registry.spec["commit"]
            or value["origin"] != ("private_xml_projection" if registry.schema == "30" else "runtime_observer")
            or any(type(value[name]) is not bool for name in ("diagnostic_accepted", "source_unchanged"))
            or value["exception_type"] not in (*KIND_NAMES, "OTHER")
            or type(value["issues"]) is not list or len(value["issues"]) > len(ISSUES) or not set(value["issues"]) <= ISSUES
            or value["diagnostic_accepted"] and (value["issues"] or not value["source_unchanged"])
            or value["entrypoint"] != registry.entrypoint()
            or value["entrypoint"] is not None and type(value["entrypoint"].get("expected_absent")) is not bool):
        raise ValueError("Diagnostic payload differs")
    def frames(rows, *, cjs=False):
        if type(rows) is not list or len(rows) > MAX_FRAMES:
            raise ValueError("Diagnostic frame count")
        for row in rows:
            if type(row) is not dict:
                raise ValueError("Unauthenticated diagnostic frame")
            expected = (registry.cjs_location(row.get("path"), row.get("line"), row.get("column"))
                        if cjs and row.get("origin") == "private_cjs_text_projection"
                        else registry.location(row.get("path"), row.get("line")))
            if row != expected:
                raise ValueError("Unauthenticated diagnostic frame")
    frames(value["frames"])
    if type(value["private_artifacts"]) is not list or len(value["private_artifacts"]) > (3 if registry.schema == "31" else 2):
        raise ValueError("Diagnostic artifact inventory")
    roles = []
    for row in value["private_artifacts"]:
        if (set(row) != {"role", "origin", "bytes", "sha256", "exception_types", "frames", "signals"} or row["role"] not in ROLES
                or row["origin"] != "private_text_projection"
                or type(row["bytes"]) is not int or not 0 <= row["bytes"] <= MAX_PRIVATE
                or type(row["sha256"]) is not str or re.fullmatch('[0-9a-f]{64}', row["sha256"]) is None
                or type(row["exception_types"]) is not list
                or any(kind not in (*KIND_NAMES, "OTHER") for kind in row["exception_types"])
                or type(row["signals"]) is not list
                or row["signals"] not in ([], [signature_for(registry, row["role"])])
                or row["signals"] == [None]):
            raise ValueError("Diagnostic artifact fields")
        roles.append(row["role"])
        frames(row["frames"], cjs=registry.schema == "31" and row["role"] in {"driver_log", "browser_error_log"})
    if len(roles) != len(set(roles)) or (registry.schema == "30" and set(roles) not in (set(), {"quota_xml", "quota_log"})):
        raise ValueError("Diagnostic artifact roles")
    if registry.schema != "30" and not set(roles) <= ({"fixture_log", "driver_log", "browser_error_log"} if registry.schema == "31" else {"fixture_log", "driver_log"}):
        raise ValueError("Diagnostic member artifact roles")
    if type(value["cases"]) is not list or (registry.schema != "30" and value["cases"]):
        raise ValueError("Diagnostic case scope")
    if value["cases"]:
        if [row.get("name") for row in value["cases"]] != list(QUOTA_CASES):
            raise ValueError("Diagnostic case identities")
        for row in value["cases"]:
            if (set(row) != {"module", "name", "outcome", "exception_type", "frames"}
                    or row["module"] != "tests.integration_quota_postgres"
                    or row["outcome"] not in {"passed", "failure", "error", "skipped"}
                    or row["exception_type"] not in (*KIND_NAMES, "OTHER")):
                raise ValueError("Diagnostic case fields")
            frames(row["frames"])
    if value["diagnostic_accepted"] and ((registry.schema == "30" and (len(value["cases"]) != 3 or len(roles) != 2))
                                         or (registry.schema != "30" and not value["frames"])):
        raise ValueError("Accepted diagnostic lacks its exact observed scope")
    return value


def write_metadata(path, registry, value):
    validate(registry, value)
    if value["source_unchanged"]:
        registry.quiet()
    path = Path(path)
    directory(path.parent)
    if not path.is_absolute() or path.is_relative_to(registry.root) or path.exists() or path.is_symlink():
        raise ValueError("Fresh external diagnostic output required")
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > 128 * 1024:
        raise ValueError("Diagnostic output size")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)


class PrivateParser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("Invalid diagnostic CLI")


def main():
    parser = PrivateParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--quota-private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry = SourceRegistry(args.source, "30")
    result = empty(registry, "private_xml_projection")
    try:
        private_directory(registry.root)
        private_directory(args.quota_private)
        xml, _ = read_bounded(registry.root / "pytest-postgres-quota.xml", MAX_PRIVATE)
        log, _ = read_bounded(args.quota_private / "step-19.raw.log", MAX_PRIVATE)
        result = quota_bytes(registry, xml, log)
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError, MemoryError, RecursionError):
        result["issues"] = ["input_rejected"]
    write_metadata(args.output, registry, result)
    return 0 if result["diagnostic_accepted"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError, MemoryError, RecursionError):
        raise SystemExit(2) from None
