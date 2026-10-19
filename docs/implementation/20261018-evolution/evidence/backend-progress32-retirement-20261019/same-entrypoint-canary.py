"""Same actual32 HTTP criteria before the new entrypoints and after them."""
# ruff: noqa: F811 -- pytest fixture parameters intentionally use fixture names
import pytest

from tests.test_personal_progress_http import (  # noqa:F401
    accepted,
    grant,
    progress_db,
    progress_http,
)


@pytest.mark.parametrize("operation", ["metadata", "withdraw"])
def test_fresh_primary_only_entry_exposes_only_own_consent(progress_http, operation):
    case = progress_http
    link = accepted(case)
    result, _ = grant(case, link)
    assert result.status_code == 200
    body = {"primary": {"method": "password", "email": case["emails"]["person"],
                        "password": "Synthetic progress password 42!"}}
    if operation == "withdraw":
        body.update(link_id=link, expected_consent_id=result.json()["consent"]["id"], expected_version=1)
    response = case["client_http"].post("/api/auth/progress-retirement/" + operation, json=body)
    assert response.status_code == 200
    assert response.json()["scope"] == "own_consent_retirement_only"
    assert "token" not in response.json() and "refresh_token" not in response.json()
