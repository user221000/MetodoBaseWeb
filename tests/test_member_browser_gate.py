"""Fail-closed metadata and public artifact boundaries; no browser/PG doubles."""
import copy
import json

import pytest

from tests.e2e.run_member_link_browser import PUBLIC_FILES, publish, validate_closure, validate_startup

HEAD = 'a' * 40
PORT = 8794


def marker():
    from web.database.alembic.history_index_contract_v1 import expected_history_index
    return {'fixture': 'r12-real-postgres30', 'head': HEAD, 'pid': 123,
            'port': PORT, 'database_kind': 'postgresql',
            'executed_revision': '20261019_personal_history_index',
            'model_target_revision': '20261019_personal_history_index',
            'business_contract_revision': '20261019_client_account_links',
            'history_order_index': expected_history_index('postgresql'),
            'model_tables': 29, 'actual_tables': 30,
            'application_role_restricted_nonowner': True,
            'runtime_pool_size': 20, 'runtime_max_overflow': 10,
            'R12_API_doubles': False, 'first_party_origin': 'http://127.0.0.1:8794'}


def test_actual_fixture_metadata_contract():
    validate_startup(marker(), HEAD, PORT)


@pytest.mark.parametrize('key,value', [
    ('fixture', 'another-fixture'), ('head', 'b' * 40), ('pid', True), ('port', 8795),
    ('database_kind', 'sqlite'), ('executed_revision', '20261019_account_recovery'),
    ('model_target_revision', '20261019_account_recovery'), ('model_tables', 26),
    ('actual_tables', 29), ('application_role_restricted_nonowner', False),
    ('runtime_pool_size', 1), ('runtime_max_overflow', 0), ('R12_API_doubles', True),
    ('first_party_origin', 'http://127.0.0.1:8795'),
])
def test_unreviewed_runtime_metadata_is_rejected(key, value):
    data = marker()
    data[key] = value
    with pytest.raises(AssertionError):
        validate_startup(data, HEAD, PORT)


def closure():
    return {'exact_owned_names': ['metodobase_test_migrations_' + 'a' * 12],
            'count': 1, 'remaining': [], 'all_owned_absent': True, 'fixture_error_class': None}


def test_exact_owned_database_closure():
    validate_closure(closure())


@pytest.mark.parametrize('key,value', [
    ('exact_owned_names', []), ('exact_owned_names', ['production']), ('count', True),
    ('count', 2), ('remaining', ['metodobase_test_migrations_' + 'a' * 12]),
    ('all_owned_absent', False), ('fixture_error_class', 'RuntimeError'),
])
def test_incomplete_or_foreign_cleanup_is_rejected(key, value):
    data = closure()
    data[key] = copy.deepcopy(value)
    with pytest.raises(AssertionError):
        validate_closure(data)


def artifacts(tmp_path):
    phase = tmp_path / 'private'
    output = tmp_path / 'public'
    phase.mkdir()
    output.mkdir()
    invitations = [{'token': str(index) * 43} for index in range(3)]
    (phase / 'mail.private.json').write_text(json.dumps(invitations), encoding='utf8')
    (phase / 'config.private.json').write_text('private credentials excluded', encoding='utf8')
    for name in PUBLIC_FILES:
        (phase / name).write_bytes(b'\x89PNG\r\n\x1a\nsynthetic' if name.endswith('.png') else b'{}\n')
    return phase, output


def test_only_explicit_public_allowlist_is_copied(tmp_path):
    phase, output = artifacts(tmp_path)
    assert publish(phase, output) == list(PUBLIC_FILES)
    assert sorted(path.name for path in output.iterdir()) == sorted(PUBLIC_FILES)
    assert not (output / 'mail.private.json').exists()
    assert not (output / 'config.private.json').exists()


@pytest.mark.parametrize('bad', ['invitation', 'bearer', 'missing', 'empty', 'invalid-png'])
def test_incomplete_or_sensitive_artifacts_publish_nothing(tmp_path, bad):
    phase, output = artifacts(tmp_path)
    target = phase / 'browser-result.json'
    if bad == 'invitation':
        target.write_text(json.dumps({'proof': '0' * 43}), encoding='utf8')
    elif bad == 'bearer':
        target.write_bytes(b'A' * 40 + b'.' + b'b' * 64)
    elif bad == 'missing':
        target.unlink()
    elif bad == 'empty':
        target.write_bytes(b'')
    else:
        (phase / '01-explicit-acceptance.png').write_bytes(b'not a PNG')
    with pytest.raises(AssertionError):
        publish(phase, output)
    assert list(output.iterdir()) == []


@pytest.mark.parametrize('key,value', [
    ('fixture', 'r12-real-postgres29'),
    ('executed_revision', '20261019_client_account_links'),
    ('model_target_revision', '20261019_client_account_links'),
    ('business_contract_revision', '20261019_personal_history_index'),
])
def test_previous_runtime_or_relabelled_business_contract_is_rejected(key, value):
    data = marker()
    data[key] = value
    with pytest.raises(AssertionError):
        validate_startup(data, HEAD, PORT)


@pytest.mark.parametrize('key,value', [
    ('indoption', [0, 0, 0, 1]),
    ('indoption', [False, 0, 1, 1]),
    ('key_columns', 4.0), ('valid', 1), ('ready', False),
    ('predicate', 'deleted_at IS NOT NULL'), ('method', 'hash'),
    ('collations', [None] * 4), ('operator_classes', ['pg_catalog.text_ops'] * 4),
    ('unexpected', 'not-in-the-reviewed-index'),
])
def test_changed_or_type_coerced_physical_index_witness_is_rejected(key, value):
    data = marker()
    data['history_order_index'][key] = copy.deepcopy(value)
    with pytest.raises(AssertionError):
        validate_startup(data, HEAD, PORT)


def test_missing_physical_index_witness_is_rejected():
    data = marker()
    del data['history_order_index']
    with pytest.raises(KeyError):
        validate_startup(data, HEAD, PORT)


def normalize_report(tmp_path, data, *, expected_revision='20261019_personal_history_index'):
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source, target = tmp_path / 'input.json', tmp_path / 'normalized.json'
    source.write_text(json.dumps(data), encoding='utf8')
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B',
        str(root / 'tests/e2e/normalize_member_link_report.py'),
        '--input', str(source), '--output', str(target), '--expected-head', HEAD,
        '--expected-origin', 'http://127.0.0.1:8794', '--expected-revision', expected_revision],
        cwd=root, capture_output=True, timeout=10)
    return result, target


def browser_report():
    return {'head': HEAD, 'scope': 'Synthetic report-adapter test; no browser execution',
            'executed_revision': '20261019_personal_history_index',
            'passed': 16, 'total': 16, 'expected_total': 16,
            'report': [{'case': 'criterion-' + str(index), 'passed': True} for index in range(16)],
            'page_errors': [], 'network': {'API_doubles': False,
                                         'first_party_origin': 'http://127.0.0.1:8794'}}


def test_normalizer_preserves_explicit_current_revision_without_rerunning_cases(tmp_path):
    data = browser_report()
    result, target = normalize_report(tmp_path, data)
    assert result.returncode == 0
    normalized = json.loads(target.read_bytes())
    assert normalized['executed_revision'] == '20261019_personal_history_index'
    assert normalized['results'] == data['report']
    assert normalized['passed'] == normalized['total'] == 16


@pytest.mark.parametrize('change', ['previous-revision', 'missing-revision', 'wrong-type',
                                  'previous-expected-revision', 'incomplete-cases'])
def test_normalizer_rejects_missing_previous_or_incomplete_runtime_reports(tmp_path, change):
    data = browser_report()
    expected = '20261019_personal_history_index'
    if change == 'previous-revision':
        data['executed_revision'] = '20261019_client_account_links'
    elif change == 'missing-revision':
        del data['executed_revision']
    elif change == 'wrong-type':
        data['executed_revision'] = 30
    elif change == 'previous-expected-revision':
        expected = '20261019_client_account_links'
        data['executed_revision'] = expected
    else:
        data['report'].pop()
    result, target = normalize_report(tmp_path, data, expected_revision=expected)
    assert result.returncode != 0
    assert not target.exists()
