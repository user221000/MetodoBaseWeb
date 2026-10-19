"""R25 page/control canary; actual web factory, no accepted API32 claim."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("route,root_id", [
    ("/mi-progreso", "personal-progress-page"),
    ("/clientes/synthetic-progress-client/progreso", "professional-progress-page"),
])
def test_progress_page_has_accessible_loading_and_error_controls(route, root_id):
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    assert f'id="{root_id}"' in response.text
    assert 'id="progress-status"' in response.text
    assert 'role="status"' in response.text
    assert 'id="progress-error"' in response.text
    assert 'id="progress-refresh"' in response.text
    assert 'Referrer-Policy' in response.headers
    assert response.headers['Referrer-Policy'] == 'no-referrer'
