"""Fresh CI PG service only: restricted image role, before/after image DDL."""
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg2
from psycopg2 import sql

from tests.isolation import validate_postgres_test_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['before', 'after'])
    args = parser.parse_args()
    admin = validate_postgres_test_url(os.environ['METODOBASE_TEST_MIGRATOR_URL'])
    runtime = validate_postgres_test_url(os.environ['METODOBASE_TEST_POSTGRES_URL'])
    a, b = urlsplit(admin), urlsplit(runtime)
    assert (a.hostname, a.port, a.path) == (b.hostname, b.port, b.path)
    assert a.path == '/metodobase_test_image' and a.port == 55483
    role = unquote(b.username or '')
    assert role == 'metodobase_test_app' and b.password
    with psycopg2.connect(admin.replace('postgresql+psycopg2://', 'postgresql://', 1)) as db, db.cursor() as cursor:
        cursor.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=%s', (role,))
        flags = cursor.fetchone()
        if args.stage == 'before':
            assert flags is None, 'Image role already exists; service is not fresh'
            cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %s').format(sql.Identifier(role)), (unquote(b.password),))
            cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO {}').format(sql.Identifier(role)))
        else:
            assert flags == (False, False, False, False)
            cursor.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(role)))
    print('Fresh CI image restricted-role stage completed; no credential values reported')


if __name__ == '__main__':
    main()
