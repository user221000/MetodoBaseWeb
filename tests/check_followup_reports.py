"""Require both current PostgreSQL factories for the readonly follow-up feature."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

REPORT = 'pytest-postgres-followup.xml'
REQUIRED = frozenset({
    ('tests.integration_followup_postgres',
     'test_readonly_followup_double_owner_admin_scope_and_revocation[web.main_web-postgresql]'),
    ('tests.integration_followup_postgres',
     'test_readonly_followup_double_owner_admin_scope_and_revocation[api.app-postgresql]'),
})


def validate(directory: Path) -> int:
    """Reject a substituted factory/dialect even when the total stays two."""
    root = ET.parse(directory / REPORT).getroot()
    actual = [(case.get('classname'), case.get('name')) for case in root.findall('.//testcase')]
    if len(actual) != 2 or set(actual) != REQUIRED:
        raise ValueError('Both reviewed PostgreSQL factory cases are required')
    if any(root.findall('.//' + tag) for tag in ('skipped', 'failure', 'error')):
        raise ValueError('Follow-up PostgreSQL acceptance was unsuccessful')
    return len(actual)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        count = validate(args.directory)
    except (OSError, ET.ParseError, ValueError):
        parser.exit(1, 'Both follow-up PostgreSQL factory cases must pass\n')
    print(f'{count} follow-up PostgreSQL cases accepted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
