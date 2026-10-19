"""Check the real current30 fixture witness before and after its browser run."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def validate(path: Path, *, pid: int, port: int) -> None:
    """Authenticate only the owned synthetic marker and read source bytes."""
    from tests.e2e.run_member_link_browser import validate_history_index
    from web.database.alembic.history_index_contract_v1 import expected_history_index

    if path.stat().st_size > 65536:
        raise ValueError('Fixture report exceeds its metadata budget')
    marker = json.loads(path.read_bytes())
    assert marker['fixture'] == 'r23-followup-real-pg'
    assert type(marker['pid']) is int and marker['pid'] == pid and pid > 0
    assert type(marker['port']) is int and marker['port'] == port == 8795
    assert re.fullmatch(r'metodobase_test_followup_[0-9a-f]{16}', marker['database'])
    assert marker['runtime_revision'] == '20261019_personal_history_index'
    assert type(marker['model_tables']) is int and marker['model_tables'] == 29
    assert type(marker['actual_tables']) is int and marker['actual_tables'] == 30
    assert marker['application_role_restricted_nonowner'] is True
    validate_history_index(marker['history_order_index'], expected_history_index('postgresql'))
    sources = marker['sources']
    assert type(sources) is dict and len(sources) == 28
    # The marker cannot omit the runtime factories, physical guard or driver.
    required = frozenset(['api/app.py', 'web/main_web.py', 'web/routes/followup.py', 'web/database/followup_repository.py', 'web/services/followup_policy.py', 'web/services/followup_service.py', 'web/templates/dashboard.html', 'web/static/js/api.js', 'web/static/js/main.js', 'web/static/js/dashboard-seguimiento.js', 'web/auth.py', 'web/auth_deps.py', 'web/services/permissions.py', 'web/database/models.py', 'web/database/tenant_context.py', 'web/database/tenant_policy.py', 'web/database/engine.py', 'web/middleware/security_headers.py', 'tests/isolation.py', 'web/database/schema_control.py', 'web/database/alembic/history_index_contract_v1.py', 'config/constantes.py', 'tests/e2e/followup_server.py', 'tests/e2e/dashboard_followup_browser.cjs', 'requirements_web-windows.lock', 'requirements-test-windows.lock', 'tests/e2e/package.json', 'tests/e2e/package-lock.json'])
    assert set(sources) == required
    for name, digest in sources.items():
        candidate = (ROOT / name).resolve()
        assert candidate.is_relative_to(ROOT) and candidate.is_file()
        assert hashlib.sha256(candidate.read_bytes()).hexdigest() == digest, name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    try:
        validate(args.report, pid=args.pid, port=args.port)
    except (AssertionError, KeyError, OSError, TypeError, ValueError):
        parser.exit(1, 'Current follow-up fixture metadata/source validation failed\n')
    print('Current physical30 follow-up fixture accepted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
