"""Require exact versioned PostgreSQL identities and per-case runtime witnesses."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PINS = {'33': ('current33', 20, 240, 'bfe56b94eb761db950ef1da66eba4e6e7c175af960ea117e0258256811a8fc0b'),
        '32': ('historical32', 5, 38, '4bcfd2d3f323e6aaf8ab944d7de62c1872817b6e1a8e82d809a15528fb8bb5af')}


def required_reports(schema='33'):
    label, reports, cases, digest = PINS[schema]
    raw = (ROOT / ('tests/ci_google33/' + label + '-report-nodeids.json')).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Versioned full identity metadata differs')
    source = json.loads(raw)
    result = {name: frozenset(map(tuple, values)) for name, values in source.items()}
    flat = [row for values in result.values() for row in values]
    if (len(result) != reports or len(flat) != cases or len(set(flat)) != cases
            or any(len(result[name]) != len(rows) for name, rows in source.items())):
        raise ValueError('Versioned identity scope or uniqueness differs')
    migrations = next(values for name, values in result.items() if name.endswith('-migrations.xml'))
    if len(migrations) != 5 or any('[postgresql' not in name for _, name in migrations):
        raise ValueError('Five selected PostgreSQL migration identities are required')
    return result


def read_report(path):
    # The strict historical parser remains byte-exact and independently gated.
    from tests.check_mfa31_reports import read_report as strict_junit
    return strict_junit(path)


def read_witnesses(path, required, schema):
    from tests.ci_google33.witness import closed_json
    from tests.ci_google33.witness import validate as validate_witness
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8 * 1024 * 1024:
        raise ValueError('Missing, linked or oversized runtime witnesses')
    value = closed_json(path.read_bytes())
    if set(value) != {'schema', 'cases'} or value['schema'] != schema or not isinstance(value['cases'], list):
        raise ValueError('Runtime witness envelope differs')
    seen = set()
    for row in value['cases']:
        if not isinstance(row, dict) or set(row) != {'identity', 'phase', 'measurements', 'measurement_sources'}:
            raise ValueError('Runtime case witness differs')
        identity = tuple(row['identity'])
        if identity not in required or identity in seen or row['phase'] != 'after_business_before_teardown':
            raise ValueError('A runtime witness is missing, duplicated or unrelated')
        seen.add(identity)
        transition = '_migrations' in identity[0]
        pool = 6 if identity[0] == 'tests.integration_current33_r24_race' else 1
        if not isinstance(row['measurements'], list) or not 1 <= len(row['measurements']) <= 2:
            raise ValueError('Runtime measurements are absent or unbounded')
        if (not isinstance(row['measurement_sources'], list)
                or len(row['measurement_sources']) != len(row['measurements'])
                or any(v not in {'business_fixture_engine', 'postcase_restricted_probe'} for v in row['measurement_sources'])):
            raise ValueError('Runtime measurement provenance differs')
        for measurement in row['measurements']:
            validate_witness(measurement, schema=schema, pool=pool, transition=transition)
        if transition:
            previous = '20261019_personal_progress' if schema == '33' else '20261019_mfa'
            head = '20261019_google_subjects' if schema == '33' else '20261019_personal_progress'
            expected = previous if any(p in identity[1] for p in ('predecessor_drift', 'mid_migration_failure')) else head
            if any(m['runtime_revision'] != expected for m in row['measurements']):
                raise ValueError('Transition witness ended at the wrong revision')
    if seen != required:
        raise ValueError('Every exact business identity needs its own measured witness')


def validate(directory, schema='33'):
    identities = set()
    for name, required in required_reports(schema).items():
        root = read_report(directory / name)
        actual = [(case.get('classname'), case.get('name')) for case in root.findall('.//testcase')]
        if len(actual) != len(required) or set(actual) != required or identities.intersection(actual):
            raise ValueError('Full identities are missing, substituted, duplicated or counted twice')
        identities.update(actual)
        read_witnesses(directory / name.replace('.xml', '.witnesses.json'), required, schema)
    return len(identities)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--schema', choices=('32', '33'), default='33')
    args = parser.parse_args()
    try:
        count = validate(args.directory, args.schema)
    except (OSError, ET.ParseError, ValueError, KeyError, TypeError, StopIteration):
        parser.exit(1, 'Every exact versioned PostgreSQL identity and runtime witness must pass\n')
    print(json.dumps({'schema': args.schema, 'passed_nodes': count, 'historical31_counted_as_current33': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
