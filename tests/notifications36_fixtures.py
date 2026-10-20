"""Current36 leases; no historical helper or process namespace is retargeted."""
from contextlib import contextmanager
from tests.followup34_fixtures import owned_database as sqlite_database

REVISION="20261020_notifications"
PREVIOUS="20261020_nutrition_profile"


@contextmanager
def owned_database(dialect,directory):
    if dialect=="postgresql":
        from tests.notifications36_owned import owned_database as lease
    else:
        assert dialect=="sqlite"
        lease=sqlite_database
    with lease(dialect,directory) as value:
        yield value
