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


ADDITIONAL_PROGRAMS = (
    "routines_panel.cjs", "routines_navigation.cjs", "routines_access_fences.cjs",
    "security_routines_transport_peer.cjs", "security_routines_dom_peer.cjs",
    "onboarding22_facts.cjs", "onboarding22_personal.cjs", "security_onboarding22_peer.cjs",
)


def require_additional_sources(root, mapping):
    commands = mapping["commands"]
    if ([row["script"] for row in commands] != ["tests/e2e/" + name for name in ADDITIONAL_PROGRAMS]
            or mapping["command_count"] != 8 or type(mapping["executions"]) is not int
            or mapping["executions"] != 94 or sum(len(row["expected_cases"]) for row in commands) != 94
            or mapping["legacy51_and_current13_repeated"] != 0):
        raise ValueError("Additional routine/onboarding original criteria differ")
    for name, pin in mapping["input_files"].items():
        raw = (root / name).read_bytes()
        if pin["framing"] == "normalized_lf":
            raw = raw.replace(b"\r\n", b"\n")
        elif pin["framing"] != "raw":
            raise ValueError("Undeclared additional Node source framing")
        if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise ValueError("Additional Node direct or transitive input differs")
    for row in commands:
        if not {row["script"], *row["dependencies"]} <= mapping["input_files"].keys():
            raise ValueError("An additional Node source is unbound")
    return commands


def validate_additional(raw, entry, root):
    text = raw.decode("utf8")
    if entry["format"] == "routine-pass-lines":
        lines = text.splitlines()
        if (len(lines) != len(entry["expected_cases"]) + 1
                or any(not line.startswith("PASS ") for line in lines[:-1])):
            raise ValueError("Routine ordered public pass-line framing differs")
        footer = json.loads(lines[-1])
        if set(footer) != {"passed", "total", "scope"}:
            raise ValueError("Routine public footer differs")
        value = {**footer, "results": [{"case": line[5:], "passed": True} for line in lines[:-1]]}
    elif entry["format"] == "source-bound-access-pair":
        value = json.loads(text)
        if (entry["script"] != "tests/e2e/routines_access_fences.cjs"
                or set(value) != {"passed", "total", "scope"}):
            raise ValueError("Original access-pair report framing differs")
        source = (root / entry["script"]).read_bytes().replace(b"\r\n", b"\n").splitlines(keepends=True)
        regions = entry["assertion_regions"]
        if len(regions) != 2 or [row["label"] for row in regions] != entry["expected_cases"]:
            raise ValueError("Original access-pair assertion regions differ")
        for row in regions:
            first, last = row["lines"]
            if hashlib.sha256(b"".join(source[first - 1:last])).hexdigest() != row["sha256"]:
                raise ValueError("Original access-pair assertion body differs")
        value = {**value, "results": [{"case": name, "passed": True} for name in entry["expected_cases"]]}
    elif entry["format"] in {"rows", "results"}:
        value = json.loads(text)
        if entry["format"] == "rows":
            if "results" in value or "rows" not in value:
                raise ValueError("Additional original peer rows differ")
            value = {**value, "results": value["rows"]}
    else:
        raise ValueError("Undeclared additional original Node report format")
    if value.get("scope") != entry["scope"]:
        raise ValueError("Additional original Node scope differs")
    return node_cases(value, entry["expected_cases"])
