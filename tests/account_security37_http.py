"""New current37 companion for real password, enrollment and MFA HTTP setup."""
import pytest

from tests import account_security37_fixtures
from tests.followup34_http import followup_http

account37_engine = account_security37_fixtures.account37_engine


@pytest.fixture(scope="module")
def followup_db(account37_engine):
    return account37_engine


account_http = followup_http
