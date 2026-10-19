"""Convert an explicitly named producer label, preserving every successful row."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def normalize(value, label, minimum):
    if (not isinstance(value, dict) or set(value) != {'scope', 'passed', 'total', 'results'}
            or label not in {'name', 'code'} or type(minimum) is not int or minimum < 1
            or not isinstance(value['scope'], str) or not isinstance(value['results'], list)
            or type(value['total']) is not int or type(value['passed']) is not int
            or value['total'] != value['passed'] or value['total'] != len(value['results'])
            or value['total'] < minimum):
        raise ValueError('Incomplete producer VM report')
    rows = []
    for row in value['results']:
        if (not isinstance(row, dict) or set(row) != {label, 'passed'} or row['passed'] is not True
                or not isinstance(row[label], str) or not row[label].strip()):
            raise ValueError('Invalid producer label or unsuccessful row')
        rows.append({'case': row[label], 'passed': True})
    if len({row['case'] for row in rows}) != len(rows):
        raise ValueError('Repeated producer labels cannot count as distinct checks')
    return {'scope': value['scope'], 'passed': value['passed'], 'total': value['total'], 'results': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--label-field', required=True, choices=('name', 'code'))
    parser.add_argument('--minimum', type=int, required=True)
    args = parser.parse_args()
    try:
        if args.source.is_symlink() or not args.source.is_file() or not 0 < args.source.stat().st_size <= 1024 * 1024:
            raise ValueError('Missing, linked or oversized producer report')
        from tests.ci_google33.witness import closed_json
        result = normalize(closed_json(args.source.read_bytes()), args.label_field, args.minimum)
        with args.output.open('xb') as out:
            out.write((json.dumps(result, indent=2) + '\n').encode())
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(1, 'Producer VM report failed the exact typed label/count/success boundary\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
