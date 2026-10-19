"""Convert maintained R23 report fields without inventing successful checks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def normalize(value: object, *, kind: str, minimum: int) -> dict:
    """Reject inconsistent rows, errors, source changes and repeated labels."""
    if type(value) is not dict or type(minimum) is not int or minimum < 1:
        raise ValueError('Invalid follow-up report contract')
    rows = value.get('results')
    if type(rows) is not list or len(rows) < minimum or value.get('failure') is not None:
        raise ValueError('Missing or unsuccessful follow-up results')
    converted = []
    for row in rows:
        if type(row) is not dict or row.get('passed') is not True:
            raise ValueError('Unsuccessful follow-up case')
        name = row.get('name')
        if type(name) is not str or not name.strip():
            raise ValueError('Invalid follow-up case label')
        converted.append({'case' if kind == 'counts' else 'name': name, 'passed': True})
    if len({row.get('name') for row in rows}) != len(rows):
        raise ValueError('Repeated follow-up cases')
    if kind == 'counts':
        if (type(value.get('total')) is not int or type(value.get('passed')) is not int
                or value['total'] != value['passed'] or value['total'] != len(rows)):
            raise ValueError('Inconsistent follow-up counts')
        return {'total': len(rows), 'passed': len(rows), 'results': converted}
    if kind != 'browser':
        raise ValueError('Unknown follow-up report format')
    if (value.get('executed_revision') != '20261019_personal_history_index'
            or type(value.get('model_tables')) is not int or value['model_tables'] != 29
            or type(value.get('actual_tables')) is not int or value['actual_tables'] != 30):
        raise ValueError('Browser did not execute the current physical schema')
    from tests.e2e.run_member_link_browser import validate_history_index
    from web.database.alembic.history_index_contract_v1 import expected_history_index
    try:
        validate_history_index(value.get('history_order_index'), expected_history_index('postgresql'))
    except AssertionError as error:
        raise ValueError('Browser physical history index witness differs') from error
    if value.get('pageErrors') != [] or type(value.get('pageErrors')) is not list:
        raise ValueError('Browser errors were not empty')
    if value.get('startup_delta') != {} or type(value.get('startup_delta')) is not dict:
        raise ValueError('Startup sources differ from browser sources')
    first, last = value.get('source_start'), value.get('source_end')
    if type(first) is not dict or not first or first != last or type(last) is not dict:
        raise ValueError('Source bytes changed during browser acceptance')
    screens = value.get('screens')
    required = {'followup-320.png', 'followup-390.png', 'followup-1440.png',
                'followup-stale-error.png', 'followup-late-session.png'}
    if (type(screens) is not list or any(type(item) is not str for item in screens)
            or len(screens) != len(set(screens)) or not required.issubset(screens)):
        raise ValueError('Missing or repeated follow-up screens')
    return {'checks': converted, 'pageErrors': [], 'screens': screens,
            'executed_revision': value['executed_revision']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('--kind', choices=('counts', 'browser'), required=True)
    parser.add_argument('--minimum', type=int, required=True)
    args = parser.parse_args()
    try:
        if args.source.stat().st_size > 1048576:
            raise ValueError('Report exceeds its metadata budget')
        result = normalize(json.loads(args.source.read_bytes()), kind=args.kind, minimum=args.minimum)
        with args.target.open('xb') as output:
            output.write((json.dumps(result, indent=2) + '\n').encode('utf8'))
    except (OSError, TypeError, ValueError):
        parser.exit(1, 'Follow-up report is missing, inconsistent or unsuccessful\n')
    print('Follow-up report normalized without changing case outcomes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
