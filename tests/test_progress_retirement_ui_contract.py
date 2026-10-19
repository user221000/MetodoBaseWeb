"""SSR/markup controls only; no purpose API implementation is composed here."""
from html.parser import HTMLParser

from fastapi.testclient import TestClient


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


def page():
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        return client.get('/retirar-consentimientos')


def test_page_is_uncached_and_has_restrictive_meta_before_first_resource():
    response = page()
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    markup = Markup()
    markup.feed(response.text)
    policy = next(i for i, (_, attrs) in enumerate(markup.nodes) if attrs.get('http-equiv') == 'Content-Security-Policy')
    resources = [i for i, (tag, attrs) in enumerate(markup.nodes) if tag in {'script', 'link'}]
    assert policy < min(resources)
    assert "form-action 'none'" in markup.nodes[policy][1]['content']


def test_no_session_provider_third_party_or_hidden_identifier_fields():
    markup = Markup()
    markup.feed(page().text)
    scripts = [attrs['src'] for tag, attrs in markup.nodes if tag == 'script']
    assert len(scripts) == 2
    assert all(value.startswith('/static/js/retiro-consentimientos') for value in scripts)
    for tag, attrs in markup.nodes:
        assert not any(value.startswith(('https:', 'http:', '//')) for key, value in attrs.items() if key in {'src', 'href'} and value)
        if tag == 'input':
            assert 'name' not in attrs
            assert 'value' not in attrs
            assert 'disabled' in attrs
            assert attrs.get('type') != 'hidden'


def test_labels_focus_targets_and_paste_friendly_authentication():
    markup = Markup()
    markup.feed(page().text)
    labels = {attrs['for'] for tag, attrs in markup.nodes if tag == 'label'}
    inputs = {attrs['id']: attrs for tag, attrs in markup.nodes if tag == 'input'}
    assert set(inputs) <= labels
    assert inputs['retirement-password']['autocomplete'] == 'current-password'
    assert inputs['retirement-factor']['autocomplete'] == 'one-time-code'
    assert not any(key.startswith('on') for _, attrs in markup.nodes for key in attrs)
    assert any(attrs.get('id') == 'retirement-error' and attrs.get('tabindex') == '-1' and attrs.get('role') == 'alert' for _, attrs in markup.nodes)
    assert any(attrs.get('id') == 'retirement-status' and attrs.get('tabindex') == '-1' and attrs.get('role') == 'status' for _, attrs in markup.nodes)


def test_api_factory_mounts_the_same_public_form_and_discovery_links():
    from api.app import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get('/retirar-consentimientos')
        assert response.status_code == 200
        assert bool('id="retirement-page"' in response.text)
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.headers['Referrer-Policy'] == 'no-referrer'
        for route in ('/login-usuario', '/login-gym', '/mi-perfil'):
            assert bool('href="/retirar-consentimientos"' in client.get(route).text)
