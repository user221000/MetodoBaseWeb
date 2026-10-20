"""Literal R31 admission contracts with explicit schema36 database composition.

The historical schema35 fixture and all original assertions remain unchanged.
"""
from tests.notifications36_http import followup_db as followup_db
from tests.notifications36_http import notification_http as followup_http
from tests.test_browser_session31_transport import browser as browser
from tests.test_browser31_pre_auth_boundary import (
    test_legacy_Bearer_authority_and_browser_neighbors_keep_their_contract,
    test_rejected_cookie_transport_never_reaches_authentication_or_SQL,
)


__all__ = [
    "test_legacy_Bearer_authority_and_browser_neighbors_keep_their_contract",
    "test_rejected_cookie_transport_never_reaches_authentication_or_SQL",
]
