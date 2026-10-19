"""Current33 fixtures; all historical32 helpers and contracts remain intact."""
from contextlib import contextmanager
from pathlib import Path
import uuid
from sqlalchemy import create_engine
PREVIOUS="20261019_personal_progress"
REVISION="20261019_google_subjects"

@contextmanager
def owned_database(dialect, directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if dialect == "postgresql":
        from tests.google33_owned import owned_database as lease
        with lease(dialect,directory) as value:yield value
        return
    url="sqlite:///"+(directory/(uuid.uuid4().hex+".db")).as_posix()
    engine=create_engine(url,connect_args={"check_same_thread":False})
    try:yield url,engine
    finally:engine.dispose()

def signature(connection):
    from tests.progress32_fixtures import signature as previous
    from web.database.google_identity_policy import signature as google
    return {**previous(connection),"google_identity_security":google(connection)}
