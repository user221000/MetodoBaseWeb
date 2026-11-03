"""The current41 Linux cluster is TCP-only without altering retained authority."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENTRY = 'tests/ci_web41/ci_cluster.py'
OLD_OPTIONS = '-h 127.0.0.1 -p 55483'
NEW_OPTIONS = OLD_OPTIONS + " -c unix_socket_directories=''"


def companion():
    spec = importlib.util.spec_from_file_location(
        'current41_socket_contract_under_test', ROOT / 'tests/ci_web41/source_companion.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def module_sources():
    module = companion()
    entry = module.specification()['entries'][ENTRY]
    parent = (ROOT / entry['original']).read_bytes()
    return module, entry, parent, module.source_bytes(ENTRY).decode()


def baseline(entry, parent):
    text = parent.replace(b'\r\n', b'\n').decode()
    for edit in entry['literal_edits'][:-1]:
        assert text.count(edit['old']) == edit['count']
        text = text.replace(edit['old'], edit['new'])
    return text


def test_cluster_remains_an_explicit_finite_companion():
    entries = companion().specification()['entries']
    assert len(entries) == 19
    assert 'tests/test_current41_quality_companion.py' in entries
    assert ENTRY in entries
    assert set(entries[ENTRY]) == {
        'original', 'original_sha256_LF', 'original_frames', 'literal_edits', 'current_sha256_LF'}
    assert len(entries[ENTRY]['original_frames']) == 2


def test_retained_original_and_three_previous_edits_remain_exact():
    _, entry, parent, _ = module_sources()
    assert entry['original'] == 'tests/ci_web39/ci_cluster.py'
    assert entry['original_sha256_LF'] == 'dcb624fbde74a74c0509422f271920a795b4fdbaa3a519b9137020c5302772f2'
    assert hashlib.sha256(parent.replace(b'\r\n', b'\n')).hexdigest() == entry['original_sha256_LF']
    assert entry['literal_edits'][:-1] == [
        {'old': 'tests.ci_web39', 'new': 'tests.ci_web41', 'count': 3},
        {'old': '20261023_privacy_disposition', 'new': '20261102_payment_refund_facts', 'count': 1},
        {'old': 'current39', 'new': 'current41', 'count': 3}]


def test_compiled_source_has_one_exact_additive_socket_edit():
    _, entry, parent, current = module_sources()
    assert entry['literal_edits'][-1] == {
        'old': json.dumps(OLD_OPTIONS), 'new': json.dumps(NEW_OPTIONS), 'count': 1}
    old = baseline(entry, parent)
    assert old.count(json.dumps(OLD_OPTIONS)) == 1
    assert current == old.replace(json.dumps(OLD_OPTIONS), json.dumps(NEW_OPTIONS))
    assert len(old.splitlines()) == len(current.splitlines()) == 151


def test_entire_module_AST_matches_after_reversing_only_socket_constant():
    _, entry, parent, current = module_sources()
    revised = ast.parse(current)
    changed = []
    for node in ast.walk(revised):
        if isinstance(node, ast.Constant) and node.value == NEW_OPTIONS:
            node.value = OLD_OPTIONS
            changed.append(node)
    assert len(changed) == 1
    assert ast.dump(revised) == ast.dump(ast.parse(baseline(entry, parent)))


def test_actual_pg_ctl_start_keeps_loopback_port_and_disables_only_unix_sockets():
    _, _, _, current = module_sources()
    start = next(node for node in ast.parse(current).body if isinstance(node, ast.FunctionDef) and node.name == 'start')
    calls = [node for node in ast.walk(start) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == 'run']
    launch = [node for node in calls if any(isinstance(value, ast.Constant) and value.value == 'start'
              for value in node.args[0].elts)]
    assert len(launch) == 1
    arguments = launch[0].args[0].elts
    index = next(index for index, node in enumerate(arguments) if isinstance(node, ast.Constant) and node.value == '-o')
    assert shlex.split(arguments[index + 1].value) == [
        '-h', '127.0.0.1', '-p', '55483', '-c', 'unix_socket_directories=']
    assert {key.arg: ast.literal_eval(key.value) for key in launch[0].keywords
            if key.arg == 'check'} == {'check': True}


def test_authentication_roles_durability_and_smart_stop_remain_retained():
    _, _, _, current = module_sources()
    assert '"--auth-local=trust", "--auth-host=scram-sha-256"' in current
    assert 'NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE' in current
    assert '"-m", "smart", "-w", "-t", "60", "stop"' in current
    assert '"postmaster_pidfile_sha256"' in current and '"start_ticks"' in current and '"boot_id"' in current
    assert 'fsync=off' not in current and 'synchronous_commit=off' not in current
    assert 'host="127.0.0.1", port=55483' in current


@pytest.mark.parametrize('mutation', [
    lambda parent: parent + b'\n',
    lambda parent: parent.replace(b'55483', b'55484', 1),
    lambda parent: parent.replace(b'scram-sha-256', b'trust', 1)])
def test_unreviewed_parent_bytes_are_rejected(mutation):
    module, entry, parent, _ = module_sources()
    with pytest.raises(ValueError, match='historical source frame differs'):
        module.rewrite(mutation(parent), entry)


@pytest.mark.parametrize('field,value', [('count', 2), ('old', 'unreviewed input')])
def test_socket_edit_count_or_input_drift_is_rejected(field, value):
    module, entry, parent, _ = module_sources()
    altered = copy.deepcopy(entry)
    altered['literal_edits'][-1][field] = value
    with pytest.raises(ValueError, match='literal edit count differs'):
        module.rewrite(parent, altered)


def test_unreviewed_result_pin_is_rejected():
    module, entry, parent, _ = module_sources()
    altered = copy.deepcopy(entry)
    altered['current_sha256_LF'] = '0' * 64
    with pytest.raises(ValueError, match='complete resulting current41 source differs'):
        module.rewrite(parent, altered)


def test_unreviewed_catalogue_framing_is_rejected(tmp_path):
    module = companion()
    original = ROOT / module.CATALOGUE
    path = tmp_path / module.CATALOGUE
    path.parent.mkdir(parents=True)
    path.write_bytes(original.read_bytes() + b' ')
    module.ROOT = tmp_path
    with pytest.raises(ValueError, match='catalogue differs'):
        module.specification()
