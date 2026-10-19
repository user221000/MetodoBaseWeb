"""Require all selected physical-index30 and populated-restore acceptance cases.

Historical29 reports retain their separate unchanged checker. These exact
identities prevent replacing a missing index case with an unrelated PG case.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

MIGRATIONS = 'tests.integration_personal_history_index_migrations'
QUERY = 'tests.integration_personal_history_ordered_query'
RESTORE = 'tests.integration_personal_history_index_restore'
REPORTS = {
    'pytest-postgres-history-index.xml': frozenset({
        (MIGRATIONS, 'test_populated29_upgrade_repeat_and_index_only_rollback[postgresql]'),
        *((MIGRATIONS, 'test_same_columns_drift_or_missing_index_rejected_without_runtime_repair[postgresql-' + kind + ']')
          for kind in ('direction', 'identity_order', 'collation', 'missing')),
        (MIGRATIONS, 'test_unknown29_drift_aborts_before_any_index_ddl[postgresql]'),
        (MIGRATIONS, 'test_failure_after_actual_index_ddl_rolls_back_rows_guards_and_revision[postgresql]'),
        (QUERY, 'test_mixed_history_order_ownership_complete_pages_and_pg_work_budget[postgresql]'),
    }),
    'pytest-postgres-history-index-restore.xml': frozenset({
        (RESTORE, 'test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts'),
    }),
}


def validate(directory: Path) -> int:
    """Read only public JUnit structure and reject omissions/substitutions."""
    seen = set()
    for filename, required in REPORTS.items():
        root = ET.parse(directory / filename).getroot()
        cases = root.findall('.//testcase')
        if any(root.findall('.//' + tag) for tag in ('skipped', 'failure', 'error')):
            raise ValueError('Unsuccessful physical index acceptance')
        actual = [(case.get('classname'), case.get('name')) for case in cases]
        if len(actual) != len(required) or set(actual) != required or seen.intersection(actual):
            raise ValueError('Missing, repeated or substituted physical index acceptance')
        seen.update(actual)
    return len(seen)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        count = validate(args.directory)
    except (OSError, ET.ParseError, ValueError):
        parser.exit(1, 'Physical history index PostgreSQL reports are missing or unsuccessful\n')
    print(f'{count} physical history index PostgreSQL cases accepted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
