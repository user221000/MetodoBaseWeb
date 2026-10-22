"""Finite pre-CREATE generation fence around the unchanged owned37 helper."""
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def creation_generation_guard(contract, config):
    import psycopg2
    from psycopg2.extensions import cursor as Cursor

    from tests.billing13_legacy_apply37_pg_contract import (
        check_generation,
        checked_runtime,
    )

    connect = psycopg2.connect
    creations = 0

    class Guarded(Cursor):
        def execute(self, query, variables=None):
            nonlocal creations
            statement = query.as_string(self) if hasattr(query, 'as_string') else str(query)
            if statement.lstrip().upper().startswith('CREATE DATABASE'):
                current, profile = checked_runtime()
                if current != contract or profile != config or creations != 0:
                    raise ValueError('Single UUID/source/profile/generation authority changed before CREATE')
                check_generation(contract, config, cursor=self)
                creations += 1
            return super().execute(query, variables)

    def guarded_connect(*args, **kwargs):
        if kwargs.get('connection_factory') is not None or kwargs.get('cursor_factory') not in (None, Guarded):
            raise ValueError('A foreign cursor factory cannot bypass the current37 creation fence')
        kwargs['cursor_factory'] = Guarded
        return connect(*args, **kwargs)

    with patch.object(psycopg2, 'connect', guarded_connect):
        yield
