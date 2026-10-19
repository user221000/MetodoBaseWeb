"""Reject plausible old/partial/mislabeled reports without opening services."""
import copy
import json

import pytest

from scripts import check_followup_fixture as fixture
from tests.e2e.normalize_followup_report import normalize
from web.database.alembic.history_index_contract_v1 import expected_history_index


def browser_report():
    return {'results': [{'name': 'original_' + str(i), 'passed': True} for i in range(8)],
            'pageErrors': [], 'startup_delta': {}, 'source_start': {'x': 'same'},
            'source_end': {'x': 'same'}, 'executed_revision': '20261019_personal_history_index',
            'model_tables': 29, 'actual_tables': 30,
            'history_order_index': expected_history_index('postgresql'),
            'screens': ['followup-320.png', 'followup-390.png', 'followup-1440.png',
                        'followup-stale-error.png', 'followup-late-session.png']}


def test_normalization_preserves_each_original_case_and_never_turns_failure_into_pass():
    value = browser_report()
    result = normalize(value, kind='browser', minimum=8)
    assert result['checks'] == value['results']
    for mutation in ('failure', 'failed-row', 'duplicate', 'reduced', 'source-change',
                     'startup-change', 'page-error', 'missing-screen', 'old-head', 'Boolean-count',
                     'wrong-index-direction', 'Boolean-index-direction'):
        bad = copy.deepcopy(value)
        if mutation == 'failure': bad['failure'] = {'name': 'SyntheticAfterAllChecks'}
        elif mutation == 'failed-row': bad['results'][0]['passed'] = False
        elif mutation == 'duplicate': bad['results'][1] = bad['results'][0].copy()
        elif mutation == 'reduced': bad['results'].pop()
        elif mutation == 'source-change': bad['source_end']['x'] = 'changed'
        elif mutation == 'startup-change': bad['startup_delta'] = {'x': 'changed'}
        elif mutation == 'page-error': bad['pageErrors'] = ['SyntheticFailure']
        elif mutation == 'missing-screen': bad['screens'].pop()
        elif mutation == 'old-head': bad['executed_revision'] = '20261019_account_recovery'
        elif mutation == 'Boolean-count': bad['model_tables'] = True
        elif mutation == 'wrong-index-direction': bad['history_order_index']['indoption'] = [0, 0, 0, 1]
        elif mutation == 'Boolean-index-direction': bad['history_order_index']['indoption'] = [False, False, True, True]
        with pytest.raises(ValueError, match='.'):
            normalize(bad, kind='browser', minimum=8)


@pytest.mark.parametrize('mutation', ['failed', 'duplicate', 'empty-label', 'Boolean-count', 'disagree', 'failure'])
def test_contract_normalizer_rejects_false_or_inconsistent_counts(mutation):
    good = {'total': 2, 'passed': 2, 'results': [{'name': 'a', 'passed': True}, {'name': 'b', 'passed': True}]}
    assert [row['case'] for row in normalize(good, kind='counts', minimum=2)['results']] == ['a', 'b']
    bad = copy.deepcopy(good)
    if mutation == 'failed': bad['results'][0]['passed'] = False
    elif mutation == 'duplicate': bad['results'][1]['name'] = 'a'
    elif mutation == 'empty-label': bad['results'][0]['name'] = ' '
    elif mutation == 'Boolean-count': bad['passed'] = True
    elif mutation == 'disagree': bad['total'] = 3
    elif mutation == 'failure': bad['failure'] = {}
    with pytest.raises(ValueError):
        normalize(bad, kind='counts', minimum=2)


def test_startup_metadata_uses_every_exact_owned_source_and_closed_physical_witness(tmp_path):
    import ast
    import hashlib

    tree = ast.parse((fixture.ROOT / 'tests/e2e/followup_server.py').read_text(encoding='utf8'))
    names = ast.literal_eval(next(node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                                 and any(isinstance(target, ast.Name) and target.id == 'names' for target in node.targets)))
    marker = {'fixture': 'r23-followup-real-pg', 'pid': 123, 'port': 8795,
              'database': 'metodobase_test_followup_' + 'a' * 16,
              'runtime_revision': '20261019_personal_history_index', 'model_tables': 29, 'actual_tables': 30,
              'application_role_restricted_nonowner': True, 'history_order_index': expected_history_index('postgresql'),
              'sources': {name: hashlib.sha256((fixture.ROOT / name).read_bytes()).hexdigest() for name in names}}
    target = tmp_path / 'startup.json'
    target.write_text(json.dumps(marker), encoding='utf8')
    fixture.validate(target, pid=123, port=8795)
    for mutation in ('old', 'wrong-pid', 'wrong-db', 'unrestricted', 'Boolean-table-count', 'ascending', 'omitted-source', 'changed-source'):
        bad = copy.deepcopy(marker)
        if mutation == 'old': bad['runtime_revision'] = '20261019_client_account_links'
        elif mutation == 'wrong-pid': bad['pid'] = 321
        elif mutation == 'wrong-db': bad['database'] = 'metodobase_test_integration'
        elif mutation == 'unrestricted': bad['application_role_restricted_nonowner'] = False
        elif mutation == 'Boolean-table-count': bad['actual_tables'] = True
        elif mutation == 'ascending': bad['history_order_index']['indoption'] = [0, 0, 0, 1]
        elif mutation == 'omitted-source': bad['sources'].pop('web/auth.py')
        elif mutation == 'changed-source': bad['sources']['web/auth.py'] = '0' * 64
        target.write_text(json.dumps(bad), encoding='utf8')
        with pytest.raises(AssertionError):
            fixture.validate(target, pid=123, port=8795)
