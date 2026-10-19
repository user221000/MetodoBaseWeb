"""Use the existing UUID fixture and independently confirm its cleanup."""
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest

from tests.integration_schema_migrations import migration_database as _owned_fixture


@pytest.fixture(params=['sqlite', 'postgresql'])
def history_migration_database(request, tmp_path):
    owner = _owned_fixture.__wrapped__(request, tmp_path)
    url, engine = next(owner)
    name = None
    try:
        if engine.dialect.name == 'postgresql':
            parsed = urlsplit(url)
            assert parsed.hostname in ('127.0.0.1', 'localhost', 'postgres')
            name = parsed.path.removeprefix('/')
            assert re.fullmatch('metodobase_test_migrations_[0-9a-f]{12}', name)
        yield url, engine
    finally:
        owner.close()
        if name is not None:
            import psycopg2
            from tests.isolation import validate_postgres_test_url
            parent = validate_postgres_test_url(os.environ['METODOBASE_TEST_MIGRATOR_URL'])
            with psycopg2.connect(parent.replace('postgresql+psycopg2://', 'postgresql://', 1)) as db, db.cursor() as cursor:
                cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s', (name,))
                assert cursor.fetchone()[0] == 0
            output = os.environ.get('METODOBASE_HISTORY_ORDERED_PROOF_DIR')
            if output:
                with (Path(output)/'owned-database-closures.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps({'database': name, 'created_by_fixture': True, 'removed_and_absence_checked': True})+'\n')
