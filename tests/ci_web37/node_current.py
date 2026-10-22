"""Exact additional UI27/37 VM criteria, separate from the legacy51 inventory."""
from __future__ import annotations

import hashlib
import json

from tests.ci_web37.reports import node_cases


def report(raw, entry):
    text = raw.decode("utf8")
    if entry["format"] == "public-pass-lines":
        lines = text.splitlines()
        if len(lines) != len(entry["expected_cases"]) + 1:
            raise ValueError("Public proof report framing differs")
        names = []
        for line in lines[:-1]:
            if not line.startswith("PASS ") or not line.removeprefix("PASS "):
                raise ValueError("Public proof report success lines differ")
            names.append(line[5:])
        footer = json.loads(lines[-1])
        if (set(footer) != {"passed", "failed", "runtime"} or type(footer["failed"]) is not int
                or footer["failed"] != 0 or footer["runtime"] != "Node VM; no native browser"):
            raise ValueError("Public proof report typed footer differs")
        return {"passed": footer["passed"], "total": len(names),
                "results": [{"case": name, "passed": True} for name in names]}
    value = json.loads(text)
    if entry["format"] == "rows":
        if not isinstance(value, dict) or "results" in value or "rows" not in value:
            raise ValueError("Independent UI peer report framing differs")
        return {**value, "results": value["rows"]}
    if entry["format"] != "results":
        raise ValueError("Undeclared additional UI report format")
    return value


def require_sources(root, mapping):
    for name, pin in mapping["input_files"].items():
        raw = (root / name).read_bytes()
        if pin["framing"] == "normalized_lf":
            raw = raw.replace(b"\r\n", b"\n")
        elif pin["framing"] != "raw":
            raise ValueError("Undeclared current UI source framing")
        if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise ValueError("A current UI direct or transitive source differs")
    commands = mapping["commands"]
    if (len(commands) != 13 or len({entry["script"] for entry in commands}) != 13
            or type(mapping["executions"]) is not int or mapping["executions"] != 147
            or sum(len(entry["expected_cases"]) for entry in commands) != mapping["executions"]
            or any(entry["script"] == "tests/e2e/browser_session31.cjs" for entry in commands)):
        raise ValueError("Additional UI command/criterion inventory differs")
    for entry in commands:
        if not entry["expected_cases"] or not {entry["script"], *entry["dependencies"]} <= mapping["input_files"].keys():
            raise ValueError("A current UI command has an unbound direct or transitive input")
    return commands


def validate(raw, entry):
    return node_cases(report(raw, entry), entry["expected_cases"])
