"""Public SSR semantics only; GIS/provider/API33 and final CSP composition remain external gates."""
from html.parser import HTMLParser
from fastapi.testclient import TestClient


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


def test_google_page_semantics_and_no_serialized_proof():
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get('/cuenta/google')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    markup = Markup()
    markup.feed(response.text)
    labels = {attrs.get('for') for tag, attrs in markup.nodes if tag == 'label'}
    for tag, attrs in markup.nodes:
        if tag == 'input':
            assert 'name' not in attrs and 'value' not in attrs
            assert attrs.get('type') != 'hidden'
            if attrs.get('type') != 'checkbox':
                assert attrs['id'] in labels
                assert attrs['autocomplete'] in {'current-password', 'one-time-code'}
        if tag == 'script':
            assert attrs['src'].startswith('/static/js/')
            assert 'nonce' in attrs
        assert not any(key.startswith('on') for key in attrs)
    assert bool('novalidate' in response.text)
    identifiers = [attrs['id'] for _, attrs in markup.nodes if 'id' in attrs]
    assert len(identifiers) == len(set(identifiers))


def test_api_factory_mounts_same_page_without_fetching_a_provider():
    from api.app import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get('/cuenta/google')
    assert response.status_code == 200
    assert bool('id="google-link-page"' in response.text)
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'


def test_google_client_id_is_public_configuration_only_and_assets_remain_local(monkeypatch):
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'synthetic-public-client.apps.googleusercontent.com')
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get('/cuenta/google')
    markup = Markup()
    markup.feed(response.text)
    roots = [attrs for _, attrs in markup.nodes if attrs.get('id') == 'google-link-page']
    assert len(roots) == 1
    assert roots[0]['data-google-client-id'] == 'synthetic-public-client.apps.googleusercontent.com'
    assets = [attrs.get('src', attrs.get('href', '')) for tag, attrs in markup.nodes if tag in {'script', 'link'}]
    assert len(assets) == 5
    assert {value.split('?', 1)[0] for value in assets} == {
        '/static/css/google-vinculo.css', '/static/js/api.js',
        '/static/js/google-vinculo.js', '/static/js/google-vinculo-pagina.js',
        '/static/css/design-system.css'}
    assert all(value.startswith('/static/') for value in assets)
    assert not any('credential' in attrs or 'intent' in attrs or 'password' in attrs for _, attrs in markup.nodes)
