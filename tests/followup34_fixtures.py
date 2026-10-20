"""Current34 fixtures, no retargeting of any accepted22-33 fixture/target."""
from contextlib import contextmanager
from pathlib import Path
import uuid

from sqlalchemy import create_engine

REVISION = "20261019_followup_tasks"
PREVIOUS = "20261019_google_subjects"


@contextmanager
def owned_database(dialect, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if dialect == "postgresql":
        from tests.followup34_owned import owned_database as lease
        with lease(dialect, directory) as value:
            yield value
        return
    url = "sqlite:///"+(directory/(uuid.uuid4().hex+".db")).as_posix()
    engine = create_engine(url, connect_args={"check_same_thread": False})
    try:
        yield url, engine
    finally:
        engine.dispose()


def signature(connection):
    import importlib
    return importlib.import_module("web.database.alembic.versions.20261019_followup_tasks").signature(connection)
