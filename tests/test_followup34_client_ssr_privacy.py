"""The dedicated client task shell and all its errors are private on both factories."""
from tests import nutrition35_fixtures as fixtures

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http


def test_client_task_shell_route_shape_is_private_on_every_method(followup_http):
    raw = followup_http["raw"]
    for client_id in ("A1B2C3D4", "invalid-identifier"):
        for suffix in ("", "/", "//"):
            for method in ("GET", "HEAD", "POST", "PATCH", "DELETE", "OPTIONS"):
                response = raw.request(method, "/clientes/" + client_id + "/seguimiento" + suffix,
                                       follow_redirects=False)
                # The shell is mounted by the UI composition. The privacy
                # boundary must also hold before/after dispatch, including404.
                assert response.status_code in {200, 307, 404, 405}
                assert response.headers["Cache-Control"] == "no-store"
                assert response.headers["Referrer-Policy"] == "no-referrer"
                assert "accounts.google.com" not in response.headers["Content-Security-Policy"]
                assert response.headers["X-Content-Type-Options"] == "nosniff"
    for path in ("/clientes/A1B2C3D4/seguimientox", "/clientes/A1B2C3D4/seguimiento/extra",
                 "/other/A1B2C3D4/seguimiento"):
        response = raw.get(path, follow_redirects=False)
        assert response.status_code == 404
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
