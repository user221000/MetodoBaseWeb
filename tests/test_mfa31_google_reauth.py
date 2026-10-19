"""Original31 IDs run current33 bound-provider contracts; exact31 lives in history."""
from tests.google33_mfa_reauth_contract import (
    mfa_client, google_db, google_http, google_transport,
    test_fresh_google_primary_reauth_accepts_only_matching_persisted_account,
    test_google_primary_admission_budget_survives_credential_rotation,
    test_google_primary_cannot_reauthenticate_a_different_persisted_account,
    test_google_primary_reauth_rejects_stale_or_absent_auth_time_despite_new_iat,
)
