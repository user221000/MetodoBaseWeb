"""Reject missing, reduced, duplicated or non-PostgreSQL R12 CI acceptance.

The minima preserve the current selected cases, rather than accepting any
nonempty XML file. The generic CI gate still checks every historical report.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

REPORTS = {
    'pytest-postgres-member-migrations.xml': (5, ('tests.integration_client_link_migrations',)),
    'pytest-postgres-member-services.xml': (16, ('tests.integration_client_link_services',)),
    'pytest-postgres-member-http.xml': (34, ('tests.integration_client_link_http',)),
    'pytest-postgres-member-races.xml': (4, ('tests.integration_client_link_service_races',
                                            'tests.integration_client_link_publication_cas')),
    'pytest-postgres-member-restore.xml': (1, ('tests.integration_client_link_restore',)),
}


def validate(directory: Path) -> int:
    """Validate only public JUnit structure; never open a database or log values."""
    identities = set()
    for name, (minimum, modules) in REPORTS.items():
        root = ET.parse(directory / name).getroot()
        cases = root.findall('.//testcase')
        if len(cases) < minimum or any(root.findall('.//' + tag) for tag in ('skipped', 'failure', 'error')):
            raise ValueError('Missing or unsuccessful current member link acceptance')
        for case in cases:
            identity = (case.get('classname'), case.get('name'))
            if identity[0] not in modules or not identity[1] or identity in identities:
                raise ValueError('Unexpected or repeated member link acceptance case')
            if name != 'pytest-postgres-member-restore.xml' and '[postgresql' not in identity[1]:
                raise ValueError('Member link acceptance is not the selected PostgreSQL case')
            if name == 'pytest-postgres-member-restore.xml' and identity[1] != (
                    'test_revision29_restore_preserves_member_links_and_all_revision26_27_28_contracts'):
                raise ValueError('The current populated member link restore was not executed')
            identities.add(identity)
    return len(identities)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        count = validate(args.directory)
    except (OSError, ET.ParseError, ValueError):
        parser.exit(1, 'Current member link PostgreSQL reports are missing, reduced or unsuccessful\n')
    print(f'{count} current member link PostgreSQL cases accepted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
