"""SQLite exclusions require the full separate PostgreSQL obligations."""
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tests.ci_web41 import payments_contract, recipes


def test_only_two_pg_modules_move_from_serial_to_the_required_owned_gate():
    parent = recipes._current41(recipes.original.CURRENT_RUNTIME_SELECTORS)
    assert recipes.CURRENT_RUNTIME_SELECTORS[:len(parent)] == parent
    assert recipes.CURRENT_RUNTIME_SELECTORS[len(parent):] == (
        '--ignore=tests/test_stripe_postgres_authority_peer.py',
        '--ignore=tests/test_stripe_postgres_refund_peer.py',
    )
    assert recipes.WEB_SELECTORS == recipes.original.WEB_SELECTORS
    recipes.require_postgres_replacements([('tests.test_current41_pg_peer_routing', 'test_contract')])


@pytest.mark.parametrize('fault', ['missing-peer', 'duplicate-peer', 'missing-current', 'wrong-plan', 'unbound-source'])
def test_incomplete_replacement_is_rejected(fault, monkeypatch):
    if fault == 'missing-peer':
        monkeypatch.setattr(payments_contract, 'PEER_CASES', payments_contract.PEER_CASES[:-1])
    elif fault == 'duplicate-peer':
        monkeypatch.setattr(payments_contract, 'CASES', payments_contract.CASES[:-1] + payments_contract.CASES[:1])
    elif fault == 'missing-current':
        monkeypatch.setattr(payments_contract, 'CURRENT_CASES', payments_contract.CURRENT_CASES[:-1])
    elif fault == 'wrong-plan':
        monkeypatch.setattr(payments_contract, 'PLAN', dict(payments_contract.PLAN, cases=5))
    else:
        monkeypatch.setattr(payments_contract, 'BOUND', tuple(p for p in payments_contract.BOUND if p not in recipes.POSTGRES_REPLACEMENTS))
    with pytest.raises(ValueError, match='mandatory exact twelve'):
        recipes.require_postgres_replacements([('tests.test_current41_pg_peer_routing', 'test_contract')])


@pytest.mark.parametrize('identities', [[], [('tests.test_stripe_postgres_authority_peer', 'test_pg')],
    [('tests.test_current41_pg_peer_routing', 'test_contract'), ('tests.test_stripe_postgres_refund_peer', 'test_pg')]])
def test_invalid_sqlite_placement_is_rejected(identities):
    with pytest.raises(ValueError, match='separately required owned gate'):
        recipes.require_postgres_replacements(identities)


def test_workflow_requires_exact_pg_execution_and_normal_fresh_closure():
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_bytes())
    steps = workflow['jobs']['current-postgres']['steps']
    checks = [s['run'] for s in steps if 'run' in s and "payments['exact_twelve_identities']" in s['run']]
    assert len(checks) == 1
    body = checks[0].split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    # The financial tail runs the exact workflow assertions against valid and
    # independently corrupted synthetic reports, without PostgreSQL or files.
    tail = body.split("payments=json.loads", 1)[1].split('\n', 1)[1]
    good = dict(accepted=True, PostgreSQL_executed=True, planned_cases=12,
                exact_twelve_identities=True, original_current_five_retained=True,
                original_pg_peer_seven_executed=True, source_profile_generation_quiet=True,
                closure=dict(accepted=True, created_UUIDs=1, normally_closed_UUIDs=1,
                             fresh_database_and_OID_absent=True))
    exec(tail, {'payments': good})
    for key in good:
        changed = deepcopy(good)
        changed[key] = dict(changed[key], accepted=False) if key == 'closure' else 0
        with pytest.raises(AssertionError):
            exec(tail, {'payments': changed})
    for key in good['closure']:
        changed = deepcopy(good)
        changed['closure'][key] = 0
        with pytest.raises(AssertionError):
            exec(tail, {'payments': changed})
    for key in ('created_UUIDs', 'normally_closed_UUIDs'):
        for wrong in (True, 1.0, '1'):
            changed = deepcopy(good)
            changed['closure'][key] = wrong
            with pytest.raises(AssertionError):
                exec(tail, {'payments': changed})
    for wrong in (True, 12.0, '12'):
        changed = deepcopy(good)
        changed['planned_cases'] = wrong
        with pytest.raises(AssertionError):
            exec(tail, {'payments': changed})
