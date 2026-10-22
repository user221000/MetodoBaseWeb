"""Reject omitted, duplicated, skipped or fabricated current test reports."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path


def junit_identities(raw: bytes):
    if len(raw) > 64 * 1024 * 1024 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unsupported required JUnit document")
    root = ET.fromstring(raw)
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Required JUnit root differs")
    rows = list(root.iter("testcase"))
    if not rows or any(list(root.iter(tag)) for tag in ("skipped", "error", "failure")):
        raise ValueError("Required cases are empty, failed, errored or skipped")
    identities = [(row.attrib.get("classname"), row.attrib.get("name")) for row in rows]
    if any(not all(isinstance(value, str) and value for value in row) for row in identities):
        raise ValueError("A required JUnit identity is missing")
    if len(set(identities)) != len(identities):
        raise ValueError("Required JUnit identities are duplicated")
    for suite in root.iter("testsuite"):
        actual = list(suite.iter("testcase"))
        if int(suite.attrib.get("tests", "-1")) != len(actual):
            raise ValueError("Required JUnit declared total differs from executed identities")
        if any(int(suite.attrib.get(key, "-1")) != 0 for key in ("errors", "failures", "skipped")):
            raise ValueError("Required JUnit declared failures or omissions differ")
    return set(identities)


def require_exact_junit(raw: bytes, expected):
    actual = junit_identities(raw)
    expected = [tuple(row) for row in expected]
    if not expected or len(expected) != len(set(expected)) or actual != set(expected):
        raise ValueError("Executed identities differ from independently collected required cases")
    return len(actual)


def node_cases(report, expected):
    """Current31 case labels are normative; count-only success is insufficient."""
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise TypeError("Required frontend result rows are absent")
    rows = report["results"]
    names = []
    for row in rows:
        if not isinstance(row, dict) or row.get("passed") is not True:
            raise ValueError("A required frontend case failed or has no explicit Boolean success")
        labels = [row[key] for key in ("case", "name", "code") if key in row]
        if len(labels) != 1 or not isinstance(labels[0], str) or not labels[0]:
            raise ValueError("A required frontend case has an ambiguous label")
        names.append(labels[0])
    if (not names or len(set(names)) != len(names) or names != list(expected)
            or type(report.get("passed")) is not int or type(report.get("total")) is not int
            or report["passed"] != len(names) or report["total"] != len(names)):
        raise ValueError("Required frontend labels, order or counters differ")
    return len(names)


class CollectionOracle:
    """Independent pre-execution identity oracle, including class-based tests."""
    def __init__(self, output: Path, fixture_output: Path | None = None):
        self.output = output
        self.fixture_output = fixture_output
        self.identities = []
        self.fixture_bindings = []

    def pytest_collection_finish(self, session):
        for item in session.items:
            path, qualified = item.nodeid.split("::", 1)
            name = item.name
            if qualified == name:
                scope = []
            elif qualified.endswith("::" + name):
                scope = qualified[:-(len(name) + 2)].split("::")
            else:
                raise ValueError("Pytest identity cannot be mapped without altering parameter bytes")
            # Only the module path is normalized. Backslashes and :: inside a
            # parameter ID are real counterexamples, never path separators.
            module = path.removesuffix(".py").replace("\\", "/").replace("/", ".")
            self.identities.append([".".join([module, *scope]), name])
            if self.fixture_output is not None:
                from tests.ci_web37.fixture_review import fixture_contract
                # This is pytest's selected binding, after collection and
                # overriding rules, rather than an inferred import graph.
                selected = item._fixtureinfo.name2fixturedefs
                fixtures = {key: fixture_contract(value[-1].func)
                            for key, value in selected.items() if value}
                self.fixture_bindings.append({"nodeid": item.nodeid, "fixtures": fixtures})

    def pytest_sessionfinish(self, session, exitstatus):
        if exitstatus == 0:
            if not self.identities or len({tuple(row) for row in self.identities}) != len(self.identities):
                raise ValueError("Collected required identities are empty or duplicated")
            with self.output.open("x", encoding="utf8") as out:
                json.dump(self.identities, out, indent=2)
                out.write("\n")
            if self.fixture_output is not None:
                with self.fixture_output.open("x", encoding="utf8") as out:
                    json.dump({"scope": "collection_only_selected_fixtures_not_executed",
                               "bindings": self.fixture_bindings}, out, indent=2)
                    out.write("\n")
