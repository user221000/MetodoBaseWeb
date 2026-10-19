"""Real factories for exact API/page privacy; pages are a separate UI delta."""
# ruff: noqa: F811 -- pytest fixture parameters intentionally use fixture names
from tests.test_personal_progress_http import progress_db, progress_http  # noqa:F401


def test_exact_api_and_page_policy_for_errors_methods_and_neighbors(progress_http):
    client = progress_http["client_http"]
    for path in ("/api/auth/progress-retirement/metadata", "/api/auth/progress-retirement/withdraw",
                 "/retirar-consentimientos"):
        for suffix in ("", "/"):
            for method in ("GET", "POST", "OPTIONS"):
                response = client.request(method, path + suffix, follow_redirects=False)
                assert response.headers["referrer-policy"] == "no-referrer"
                assert response.headers["cache-control"] == "no-store"
                policy = response.headers["content-security-policy"]
                assert "default-src 'none'" in policy and "https://accounts.google.com" not in policy
                assert "unsafe-inline" not in policy
    for path in ("/api/auth/progress-retirement/metadata-neighbor", "/retirar-consentimientos-neighbor", "/login"):
        response = client.get(path)
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "https://accounts.google.com/gsi/client" in response.headers["content-security-policy"]
