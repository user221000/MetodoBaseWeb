"""Keep the new historical runner and exact current index cases fail closed."""
import ast
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tests import check_history_index_reports as reports
from tests import verify_history_index_ci as guard


@pytest.mark.parametrize('target,body', [
    ('tests/run_reviewed_ci29.py', 'print("pretend historical29 passed")\n'),
    ('tests/check_history_index_reports.py', 'REPORTS = {}\n'),
    ('web/database/alembic/history_index_contract_v1.py', 'def expected_history_index(_): return {}\n'),
])
def test_new_executable_or_witness_substitution_is_rejected_before_use(tmp_path, monkeypatch, target, body):
    for name in guard.PINNED_CURRENT_GATES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((guard.ROOT / name).read_bytes())
    (tmp_path / target).write_text(body, encoding='utf8')
    monkeypatch.setattr(guard, 'ROOT', tmp_path)
    with pytest.raises(AssertionError, match=target):
        guard.authenticate_current_gates()


def test_empty_runtime_index_specification_cannot_erase_probes(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, 'REPORTS', {})
    with pytest.raises(AssertionError):
        guard.index_report_canaries(tmp_path)


def test_equal_count_cannot_replace_the_ordered_query_with_a_migration(tmp_path):
    for filename, identities in reports.REPORTS.items():
        root = ET.Element('testsuite')
        for module, name in sorted(identities):
            ET.SubElement(root, 'testcase', classname=module, name=name)
        ET.ElementTree(root).write(tmp_path / filename)
    assert reports.validate(tmp_path) == 9
    filename = tmp_path / 'pytest-postgres-history-index.xml'
    root = ET.parse(filename).getroot()
    query = next(case for case in root if case.get('classname') == reports.QUERY)
    query.set('classname', reports.MIGRATIONS)
    query.set('name', 'unrelated_replacement[postgresql]')
    ET.ElementTree(root).write(filename)
    with pytest.raises(ValueError):
        reports.validate(tmp_path)


def test_historical29_materialization_preserves_reviewed_archive_protections():
    """The hardened extraction contract cannot drift in the second pin."""
    implementations = []
    for name in ('run_reviewed_ci28.py', 'run_reviewed_ci29.py'):
        tree = ast.parse((Path(__file__).parent / name).read_text(encoding='utf8'))
        implementations.append({node.name: ast.dump(node, include_attributes=False)
                                for node in tree.body if isinstance(node, ast.FunctionDef)
                                and node.name in {'canonical_name', 'tree_specification',
                                                  'validate_restore_environment', 'materialize'}})
    assert len(implementations[0]) == 4
    assert implementations[0] == implementations[1]
