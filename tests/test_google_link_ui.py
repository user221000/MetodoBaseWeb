"""Original missing-page/discovery canary; no API33 acceptance."""
import pytest
from fastapi.testclient import TestClient


def test_google_link_page_exists():
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get('/cuenta/google')
    assert response.status_code == 200
    assert bool('id="google-link-page"' in response.text)


@pytest.mark.parametrize('route', ['/login-usuario', '/login-gym', '/mi-perfil', '/configuracion'])
def test_google_link_is_discoverable(route):
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    assert bool('href="/cuenta/google"' in response.text), 'Explicit binding discovery absent'
