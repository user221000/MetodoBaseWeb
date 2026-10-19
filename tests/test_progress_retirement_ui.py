"""Purpose-only public UI; synthetic SSR, never backend acceptance."""
import pytest
from fastapi.testclient import TestClient


def test_retirement_public_page_exists_without_login():
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get('/retirar-consentimientos')
    assert response.status_code == 200
    assert bool('id="retirement-page"' in response.text), 'Purpose-only controls missing'


@pytest.mark.parametrize('route', ['/login-usuario', '/login-gym', '/mi-perfil'])
def test_retirement_link_is_discoverable_without_an_api_lookup(route):
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    assert bool('href="/retirar-consentimientos"' in response.text), 'Retirement link missing'
