"""Require full110 R05 cases including all exact49 critical identities."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PIN = '621d73e264a4f7515ea94567b78ab2ee380ee48f64208c02b46c72fd800b7fc7'
FULL_PIN = '75f614af3405eae405b658fa385dd310b7de31ad46e31be33b1d852652a4f494'


def validate(path):
    from tests.check_mfa31_reports import read_report
    raw = (ROOT / 'tests/ci_google33/r05-critical49.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError('Reviewed49 source identity oracle differs')
    meta = json.loads(raw)
    full = (ROOT / 'tests/ci_google33/r05-full110.json').read_bytes()
    if hashlib.sha256(full).hexdigest() != FULL_PIN:
        raise ValueError('Full110 identity oracle differs')
    required = {'::'.join(row) for row in json.loads(full)}
    critical = set(meta['junit_classname_and_name'])
    cases = read_report(path).findall('.//testcase')
    actual = [c.get('classname', '') + '::' + c.get('name', '') for c in cases]
    if (meta['source'] != 'f7b12a71a89de2e35b0035ccef147a673ad50d29'
            or meta['count'] != len(critical) or len(critical) != 49
            or len(actual) != len(set(actual)) or len(actual) != 110
            or set(actual) != required
            or not critical <= set(actual)
            or len([name for name in actual if name.startswith('tests.test_secret_scan_reviewed_locations::')]) != 49):
        raise ValueError('Full R05 or reviewed49 identity scope differs')
    return 110


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    try:
        validate(args.report)
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, 'All110 R05 cases and exact49 critical identities must pass\n')
    print(json.dumps({'passed': 110, 'critical_exact': 49, 'global_secrets_scan_claimed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
