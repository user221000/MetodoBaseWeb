"""Resource-only portable adapter for the frozen32 Windows lease fixture."""
import os
import uuid
from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine


@contextmanager
def owned_database(dialect,directory):
    assert dialect=='postgresql'
    import psycopg2
    import resource_guard
    from psycopg2 import sql

    from tests.isolation import validate_postgres_test_url
    assert resource_guard.INSTALLED
    source=validate_postgres_test_url(os.environ['METODOBASE_TEST_MIGRATOR_URL'])
    parts=urlsplit(source);name='metodobase_test_progress_'+uuid.uuid4().hex
    control=psycopg2.connect(source.replace('postgresql+psycopg2://','postgresql://',1));control.autocommit=True
    engine=None;created=False
    try:
        with control.cursor() as db:db.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(name)))
        created=True;url=urlunsplit(parts._replace(path='/'+name));engine=create_engine(url,pool_size=1,max_overflow=0)
        yield url,engine
    finally:
        if engine is not None:engine.dispose()
        try:
            if created:
                with control.cursor() as db:db.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        finally:control.close()
