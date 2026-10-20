"""Synthetic Jinja SSR semantics only; no auth, API, provider or browser claim."""
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]


class Nodes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


@pytest.mark.parametrize('template,theme,context', [
    ('cuenta_seguridad37.html', 'main-content', 'gym'),
    ('usuario_seguridad37.html', 'u-main', 'personal'),
    ('recordatorios.html', 'main-content', 'gym'),
    ('usuario_recordatorios.html', 'u-main', 'personal'),
])
def test_mobile_navigation_remains_unique_accessible_and_outside_main(template, theme, context):
    environment = Environment(loader=FileSystemLoader(ROOT / 'web/templates'), autoescape=True)
    environment.globals.update(csrf_token=lambda request: 'synthetic-layout-csrf')
    markup = environment.get_template(template).render(
        request=SimpleNamespace(state=SimpleNamespace(csp_nonce='synthetic-layout-nonce')),
        static_version='layout-only', google_client_id='', notification_context=context,
        account_login_url='/login-gym' if context == 'gym' else '/login-usuario',
    )
    parsed = Nodes()
    parsed.feed(markup)
    buttons = [attrs for tag, attrs in parsed.nodes if tag == 'button' and attrs.get('id') == 'btn-hamburger']
    assert len(buttons) == 1
    assert buttons[0]['aria-controls'] == 'main-sidebar'
    assert buttons[0]['aria-expanded'] == 'false'
    assert buttons[0]['aria-label'] == 'Abrir menú'
    assert len([attrs for tag, attrs in parsed.nodes if tag == 'aside' and attrs.get('id') == 'main-sidebar']) == 1
    assert len([attrs for tag, attrs in parsed.nodes if tag == 'main' and attrs.get('class') == theme]) == 1
    assert markup.index('id="btn-hamburger"') < markup.index('<main ')
    assert len([attrs for tag, attrs in parsed.nodes if tag == 'h1']) == 1
    scripts = [attrs for tag, attrs in parsed.nodes if tag == 'script' and 'src' in attrs]
    assert scripts
    assert all(attrs['nonce'] == 'synthetic-layout-nonce' for attrs in scripts)
