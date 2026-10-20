"""Literal R31 admission contracts with explicit schema36 database composition.

The historical schema35 fixture and all original assertions remain unchanged.
"""
from tests import notifications36_http as current
from tests import test_browser31_pre_auth_boundary as original
from tests import test_browser_session31_transport as transport

followup_db = current.followup_db
followup_http = current.notification_http
browser = transport.browser
test_legacy_Bearer_authority_and_browser_neighbors_keep_their_contract = original.test_legacy_Bearer_authority_and_browser_neighbors_keep_their_contract
test_rejected_cookie_transport_never_reaches_authentication_or_SQL = original.test_rejected_cookie_transport_never_reaches_authentication_or_SQL


__all__ = [
    "test_legacy_Bearer_authority_and_browser_neighbors_keep_their_contract",
    "test_rejected_cookie_transport_never_reaches_authentication_or_SQL",
]
