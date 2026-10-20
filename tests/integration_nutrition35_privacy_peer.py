"""Original SEC21/22 HTTP assertions on actual current35 restricted PostgreSQL.

Only this module's fixture composition changes. Historical SQLite canaries and
their error expectations stay byte exact; no identity/MFA override is added.
"""
import pytest

from tests import integration_nutrition35_postgres as pg35
from tests.test_nutrition35_private_error_boundary import (
    test_read_query_validation_retains_detail_and_gains_private_headers as test_read_query_validation_retains_detail_and_gains_private_headers,
)
from tests.test_nutrition35_private_error_boundary import (
    test_unexpected_failure_logs_class_without_exception_values as test_unexpected_failure_logs_class_without_exception_values,
)
from tests.test_nutrition35_write_error_boundary import (
    test_client_write_routes_redact_all_invalid_envelopes as test_client_write_routes_redact_all_invalid_envelopes,
)
from tests.test_nutrition35_write_error_boundary import (
    test_personal_write_route_redacts_every_invalid_envelope as test_personal_write_route_redacts_every_invalid_envelope,
)
from tests.test_nutrition35_write_error_boundary import (
    test_read_queries_methods_and_route_neighbors_preserve_validation_contract as test_read_queries_methods_and_route_neighbors_preserve_validation_contract,
)
from tests.test_security_nutrition35_error_privacy_peer import (
    test_nonobject_declaration_envelope_is_not_reflected as test_nonobject_declaration_envelope_is_not_reflected,
)
from tests.test_security_nutrition35_error_privacy_peer import (
    test_object_declaration_validation_control_is_private as test_object_declaration_validation_control_is_private,
)
from tests.test_security_nutrition35_http_peer import (
    test_unexpected_profile_failure_keeps_private_error_headers as test_unexpected_profile_failure_keeps_private_error_headers,
)

followup_db = pg35.followup_db
followup_http = pg35.followup_http
personal35_http = pg35.personal35_http


@pytest.fixture(autouse=True)
def pool_cleanup_after_case(followup_db):
    yield
    pg35.blank_pool(followup_db[1])
