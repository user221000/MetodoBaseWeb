"""Exercise the real cursor guard against inert DDL; PostgreSQL remains separate."""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from tests.ci_google33 import resource_guard as guard


@pytest.fixture
def guarded_cursor(tmp_path, monkeypatch):
    database = 'metodobase_test_google_' + 'a' * 32
    state = {'database': None, 'sessions': [], 'executed': []}
    monkeypatch.setattr(guard, 'root', lambda: tmp_path)
    monkeypatch.setattr(guard, 'OWNED', {})
    monkeypatch.setattr(guard, 'state', lambda name: (state['database'], state['sessions']))
    monkeypatch.setenv('CI33_RUN_NONCE', 'synthetic-inert-run')

    class InertCursor:
        def execute(self, query, variables=None):
            path = tmp_path / (database + '.json')
            lease = json.loads(path.read_bytes())
            if query.startswith('CREATE'):
                assert lease['state'] == 'exclusive_before_CREATE' and lease['oid'] is None
                events = (tmp_path / (database + '.events.jsonl')).read_text().splitlines()
                assert len(events) == 1 and json.loads(events[0])['state'] == 'exclusive_before_CREATE'
                state['database'] = (456789, 'synthetic_test_owner')
            else:
                assert lease['state'] == 'zero_sessions_before_ordinary_DROP' and state['sessions'] == []
                assert 'FORCE' not in query
                state['database'] = None
            state['executed'].append(query)

    # Only the C-extension transport base changes. The actual reviewed method
    # body, its globals and all checks execute, rather than a mirrored fake.
    node = next(n for n in ast.parse(Path(guard.__file__).read_text(encoding='utf8')).body
                if isinstance(n, ast.ClassDef) and n.name == 'Cursor')
    node = copy.deepcopy(node)
    node.bases = [ast.Name(id='InertCursor', ctx=ast.Load())]
    namespace = dict(vars(guard), InertCursor=InertCursor)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), guard.__file__, 'exec'), namespace)
    return namespace['Cursor'](), database, state, tmp_path


def test_exclusive_lease_and_journal_precede_create_then_normal_drop_is_fresh(guarded_cursor):
    cursor, database, state, directory = guarded_cursor
    cursor.execute('CREATE DATABASE "' + database + '" TEMPLATE template0')
    cursor.execute('DROP DATABASE "' + database + '" WITH (FORCE)')
    assert state['database'] is None and len(state['executed']) == 2
    value = json.loads((directory / (database + '.json')).read_bytes())
    assert value['state'] == 'closed_fresh_absent' and value['executed_FORCE'] is False
    events = [json.loads(line) for line in (directory / (database + '.events.jsonl')).read_text().splitlines()]
    assert [row['state'] for row in events] == ['exclusive_before_CREATE', 'created_exact_OID',
        'zero_sessions_before_ordinary_DROP', 'closed_fresh_absent']
    assert all(row['launcher'] == events[0]['launcher'] for row in events)


@pytest.mark.parametrize('mutation', ['active-session', 'changed-OID', 'foreign-database'])
def test_drop_rejects_uncertain_attribution_and_never_executes_destructive_sql(guarded_cursor, mutation):
    cursor, database, state, directory = guarded_cursor
    cursor.execute('CREATE DATABASE "' + database + '"')
    if mutation == 'active-session':
        state['sessions'] = [(999999, 'synthetic-backend-birth')]
    elif mutation == 'changed-OID':
        state['database'] = (987654, 'synthetic_test_owner')
    else:
        database = 'metodobase_test_google_' + 'b' * 32
    before = len(state['executed'])
    with pytest.raises(AssertionError):
        cursor.execute('DROP DATABASE "' + database + '" WITH (FORCE)')
    assert len(state['executed']) == before


def test_existing_exclusive_lease_is_never_overwritten_or_used_to_create(guarded_cursor):
    cursor, database, state, directory = guarded_cursor
    path = directory / (database + '.json')
    original = b'{"synthetic_existing_lease":true}'
    path.write_bytes(original)
    with pytest.raises(FileExistsError):
        cursor.execute('CREATE DATABASE "' + database + '"')
    assert path.read_bytes() == original and state['executed'] == []
