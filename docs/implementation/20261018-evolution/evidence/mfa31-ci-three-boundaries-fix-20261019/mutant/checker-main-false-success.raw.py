"""Require every exact current31 PG node; historical30 reports are separate.

The checked set has 173 cases: R12 16/34/4, R24 publication2/race1,
MFA migration5/service12/restore1, followup2, RLS/worker81, export2, diary13.
No database, application or credential material is opened by this parser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NODEIDS_SHA256 = '1a4b9e09110d226cf9777fd3d6824692c2136c6b5e65785ce196585c5b43f860'


def required_reports() -> dict[str, frozenset[tuple[str, str]]]:
    raw = (ROOT / 'tests/ci_mfa31/current-report-nodeids.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != NODEIDS_SHA256:
        raise ValueError('Current31 node identity metadata differs')
    reports = json.loads(raw)
    result = {name: frozenset(map(tuple, values)) for name, values in reports.items()}
    if len(result) != 12 or sum(map(len, result.values())) != 173:
        raise ValueError('Current31 node identity scope differs')
    if any(len(result[name]) != len(values) for name, values in reports.items()):
        raise ValueError('Duplicate required node identity')
    return result


def read_report(path: Path) -> ET.Element:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 16 * 1024 * 1024:
        raise ValueError('A required current31 report is missing, linked or oversized')
    raw = path.read_bytes()
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('DTD/entity is not a JUnit acceptance report')
    root = ET.fromstring(raw)
    if root.tag not in {'testsuites', 'testsuite'}:
        raise ValueError('Unexpected JUnit document root')
    if any(root.findall('.//' + tag) for tag in ('skipped', 'failure', 'error')):
        raise ValueError('A current31 case failed, errored or skipped')
    suites = ([root] if root.tag == 'testsuite' else root.findall('testsuite'))
    if not suites or any(suite.findall('testsuite') for suite in suites):
        raise ValueError('Nested or missing JUnit suite')
    for suite in suites:
        cases = suite.findall('testcase')
        if not cases or len(cases) != len(suite.findall('.//testcase')):
            raise ValueError('Unexpected JUnit test structure')
        for key, expected in [('tests', len(cases)), ('failures', 0), ('errors', 0), ('skipped', 0)]:
            value = suite.get(key)
            if value is None or not value.isascii() or not value.isdecimal() or int(value) != expected:
                raise ValueError('JUnit declared counters differ from testcase structure')
    return root


def validate(directory: Path) -> int:
    identities = set()
    for name, required in required_reports().items():
        root = read_report(directory / name)
        actual = [(case.get('classname'), case.get('name')) for case in root.findall('.//testcase')]
        if len(actual) != len(required) or set(actual) != required:
            raise ValueError('Current31 full node identities are missing, substituted or duplicated')
        if identities.intersection(actual):
            raise ValueError('A current31 node was counted in multiple reports')
        identities.update(actual)
    return len(identities)


def main() -> int:
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
