"""Visual changes must preserve existing interaction/identity contracts."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'docs/implementation/20261018-evolution/evidence/web-redesign-20261021/baseline-contract.json'


class Contract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.controls = []
        self.data = []

    def handle_starttag(self, tag, items):
        attrs = dict(items)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag in {'form', 'input', 'select', 'textarea', 'button'}:
            self.controls.append([tag, {key: value for key, value in attrs.items()
                if key not in {'style', 'class', 'for', 'title'}}])
        data = {key: value for key, value in attrs.items() if key.startswith('data-')}
        if data:
            self.data.append(data)


def describe(source):
    parser = Contract()
    parser.feed(source)
    scripts = [hashlib.sha256(value.encode()).hexdigest()
        for value in re.findall(r'<script\b[\s\S]*?</script>', source, re.I)]
    return {'ids': parser.ids, 'controls': parser.controls, 'data': parser.data, 'scripts': scripts}


BASE = json.loads(BASELINE.read_text(encoding='utf-8')) if BASELINE.exists() else {}


@pytest.mark.parametrize('name', list(BASE))
def test_existing_forms_selectors_and_scripts_are_preserved(name):
    current = describe((ROOT / name).read_text(encoding='utf-8'))
    expected = BASE[name]
    assert set(expected['ids']).issubset(current['ids'])
    assert current['controls'] == expected['controls']
    assert current['scripts'] == expected['scripts']
    for item in expected['data']:
        assert item in current['data']


def test_exact_public_brand_tokens_and_no_new_remote_assets():
    source = (ROOT / 'web/static/css/design-system.css').read_text(encoding='utf-8')
    for token in ['--mb-bg:#0c1117', '--mb-text:#edf2f7', '--mb-muted:#bcc8d5', '--mb-accent:#f7cd67', '--mb-support:#7de5d3']:
        assert token in source
    assert 'url(' not in source and '@import' not in source
    assert '[hidden] {display:none!important;}' in source


def test_landing_runtime_catalogue_expressions_and_destinations_are_unchanged():
    expected = json.loads((BASELINE.parent / 'landing-runtime-contract.json').read_text(encoding='utf-8'))
    source = (ROOT / 'web/templates/landing.html').read_text(encoding='utf-8')
    assert re.findall(r'\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\}', source) == expected['jinja']
    assert re.findall(r'href="([^"]+)"', source) == expected['hrefs']


@pytest.mark.parametrize('name', ['base.html', 'base_usuario.html'])
def test_shared_system_is_after_page_styles_and_mobile_menu_stays_in_flow(name):
    source = (ROOT / 'web/templates' / name).read_text(encoding='utf-8')
    assert source.index('design-system.css') > source.index('{% block head %}')
    assert 'class="mb-mobile-bar"' in source
    assert source.index('id="btn-hamburger"') < source.index('<main ')
    assert 'fonts.googleapis' not in source and 'fonts.gstatic' not in source
