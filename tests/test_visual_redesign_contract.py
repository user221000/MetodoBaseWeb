"""Visual changes must preserve existing interaction/identity contracts."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'docs/implementation/20261018-evolution/evidence/web-redesign-20261021/baseline-contract.json'
CURRENT39_EXTENSION = ROOT / 'tests/ci_web39/fixtures/templates-feature62-extension.json'
CURRENT39_EXTENSION_SHA256_LF = 'cb5a95f9b00b333c042014ea88449f119af6b6aa8f761b968c033d4a246cafc8'
CURRENT39_TEMPLATES = tuple('web/templates/' + name + '.html' for name in (
    'dashboard', 'accept_invite', 'account_recovery', 'clientes',
    'cuenta_seguridad37', 'registro', 'usuario_mi_plan', 'usuario_seguridad37',
))
NEW_PASSWORD_TEMPLATES = tuple('web/templates/' + name + '.html' for name in (
    'accept_invite', 'account_recovery', 'registro',
))


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


def restore_approved_current39_contract(name, source, fixture_raw=None):
    """Invert only exact approved62db95e6 frontend edits for these eight files.

    Actual new password fields must require15 before historical comparison.
    This checks source/visual consistency, not backend password or privacy safety.
    No Git process, product rewrite or historical baseline update occurs.
    """
    fixture_raw = CURRENT39_EXTENSION.read_bytes() if fixture_raw is None else fixture_raw
    fixture_raw = fixture_raw.replace(b'\r\n', b'\n')
    if hashlib.sha256(fixture_raw).hexdigest() != CURRENT39_EXTENSION_SHA256_LF:
        raise ValueError('The approved current39 extension fixture differs')
    specification = json.loads(fixture_raw)
    if set(specification['templates']) != set(CURRENT39_TEMPLATES) or name not in CURRENT39_TEMPLATES:
        raise ValueError('The approved current39 template scope differs')
    approved = specification['templates'][name]
    current = describe(source)
    for selector in approved['required_password_selectors_min15']:
        matches = [attrs for tag, attrs in current['controls'] if tag == 'input'
                   and attrs.get('type') == 'password' and all(attrs.get(key) == value for key, value in selector.items())]
        if (len(matches) != 1 or matches[0].get('minlength') != '15'
                or matches[0].get('autocomplete') != 'new-password'):
            raise ValueError('The actual current39 new password minimum differs')
    def blob(raw):
        return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw,
                            usedforsecurity=False).hexdigest()
    raw = source.encode('utf8')
    if (hashlib.sha256(raw).hexdigest() != approved['current_sha256']
            or blob(raw) != approved['current_blob']
            or hashlib.sha256(BASELINE.read_bytes()).hexdigest() != specification['historical_contract_sha256']
            or len(current['controls']) != approved['current_control_count']
            or len(current['scripts']) != approved['current_script_count']
            or not set(approved['exact_added_ids']) <= set(current['ids'])):
        raise ValueError('The approved current39 source or historical contract differs')
    for edit in reversed(approved['inverse_edits']):
        start = edit['current_character_offset']
        end = start + len(edit['current'])
        if source[start:end] != edit['current']:
            raise ValueError('An exact approved current39 edit differs')
        source = source[:start] + edit['original'] + source[end:]
    restored = source.encode('utf8')
    if (hashlib.sha256(restored).hexdigest() != approved['restored_sha256']
            or blob(restored) != approved['restored_blob']):
        raise ValueError('The current39 inverse differs from the approved original')
    return source


def restore_approved_dashboard_contract(source, fixture_raw=None):
    return restore_approved_current39_contract('web/templates/dashboard.html', source, fixture_raw)


@pytest.mark.parametrize('name', list(BASE))
def test_existing_forms_selectors_and_scripts_are_preserved(name):
    source = (ROOT / name).read_text(encoding='utf-8')
    current = describe(restore_approved_current39_contract(name, source) if name in CURRENT39_TEMPLATES else source)
    expected = BASE[name]
    assert set(expected['ids']).issubset(current['ids'])
    assert current['controls'] == expected['controls']
    assert current['scripts'] == expected['scripts']
    for item in expected['data']:
        assert item in current['data']


def test_dashboard39_approved_extension_preserves_all49_original_controls_and_scripts():
    source = (ROOT / 'web/templates/dashboard.html').read_text(encoding='utf8')
    restored = restore_approved_dashboard_contract(source)
    assert len(describe(source)['controls']) == 52
    assert len(describe(source)['scripts']) == 3
    assert len(describe(restored)['controls']) == 49
    assert len(describe(restored)['scripts']) == 2
    assert describe(restored) == BASE['web/templates/dashboard.html']


@pytest.mark.parametrize('change', [
    'original-change', 'original-delete', 'extension-change', 'extension-delete',
    'extra-control', 'extra-script', 'R23-script', 'origin-call',
])
def test_dashboard39_inverse_refuses_original_or_extension_drift(change):
    source = (ROOT / 'web/templates/dashboard.html').read_text(encoding='utf8')
    if change == 'original-change':
        changed = source.replace('id="dd-nombre"', 'id="unapproved-name"', 1)
    elif change == 'original-delete':
        changed = re.sub(r'<input\b[^>]*id="dd-nombre"[^>]*>', '', source, count=1)
    elif change == 'extension-change':
        changed = source.replace('id="client-origin-value"', 'id="unapproved-origin"', 1)
    elif change == 'extension-delete':
        approved = json.loads(CURRENT39_EXTENSION.read_bytes())['templates']['web/templates/dashboard.html']
        changed = source.replace(approved['inverse_edits'][0]['current'], '', 1)
    elif change == 'extra-control':
        changed = source + '<button type="button">Unapproved</button>'
    elif change == 'extra-script':
        changed = source + '<script src="/static/js/unapproved.js"></script>'
    elif change == 'R23-script':
        changed = source.replace('dashboard-seguimiento.js?v=r23-1', 'unapproved.js', 1)
    else:
        changed = source.replace('ProductOrigin.showClient(c.id_cliente)', "ProductOrigin.showClient('other')", 1)
    assert changed != source
    with pytest.raises(ValueError, match='approved current39 source'):
        restore_approved_dashboard_contract(changed)


@pytest.mark.parametrize('change', ['source-hash', 'restored-hash', 'extra-insertion'])
def test_dashboard39_inverse_refuses_modified_approval_even_with_recomputed_source_hash(change):
    source = (ROOT / 'web/templates/dashboard.html').read_text(encoding='utf8')
    fixture = json.loads(CURRENT39_EXTENSION.read_bytes())
    approved = fixture['templates']['web/templates/dashboard.html']
    if change == 'extra-insertion':
        start = len(source)
        source += '<button type="button">Unapproved</button>'
        approved['inverse_edits'].append({'current_character_offset': start,
            'current': '<button type="button">Unapproved</button>', 'original': ''})
        approved['current_sha256'] = hashlib.sha256(source.encode()).hexdigest()
    else:
        approved['current_sha256' if change == 'source-hash' else 'restored_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='approved current39 extension fixture'):
        restore_approved_dashboard_contract(source, json.dumps(fixture).encode())


@pytest.mark.parametrize('name', CURRENT39_TEMPLATES)
def test_each_approved39_inverse_returns_the_exact_original_visual_contract(name):
    source = (ROOT / name).read_text(encoding='utf8')
    assert describe(restore_approved_current39_contract(name, source)) == BASE[name]


@pytest.mark.parametrize('name', CURRENT39_TEMPLATES)
def test_each_approved39_template_refuses_additional_control_script_or_source_drift(name):
    source = (ROOT / name).read_text(encoding='utf8')
    for addition in ('<button type="button">Unapproved</button>',
                     '<script src="/static/js/unapproved.js"></script>', ' '):
        with pytest.raises(ValueError, match='approved current39 source'):
            restore_approved_current39_contract(name, source + addition)


@pytest.mark.parametrize('name', [name for name in CURRENT39_TEMPLATES if BASE[name]['controls']])
def test_each_original_control_contract_refuses_change_and_deletion(name):
    source = (ROOT / name).read_text(encoding='utf8')
    tag, attrs = next((tag, attrs) for tag, attrs in BASE[name]['controls'] if attrs.get('id'))
    changed = source.replace('id="' + attrs['id'] + '"', 'id="unapproved-control"', 1)
    deleted = re.sub('<' + tag + r'\b[^>]*\bid="' + re.escape(attrs['id']) + r'"[^>]*>', '', source, count=1)
    assert changed != source and deleted != source
    for rejected in (changed, deleted):
        with pytest.raises(ValueError):
            restore_approved_current39_contract(name, rejected)


@pytest.mark.parametrize('name', NEW_PASSWORD_TEMPLATES)
def test_actual39_new_password_inputs_require15_before_historical_visual_comparison(name):
    source = (ROOT / name).read_text(encoding='utf8')
    password_inputs = [attrs for tag, attrs in describe(source)['controls']
                       if tag == 'input' and attrs.get('type') == 'password']
    assert len(password_inputs) == 2
    assert all(attrs.get('minlength') == '15' and attrs.get('autocomplete') == 'new-password'
               for attrs in password_inputs)
    for changed in (source.replace('minlength="15"', 'minlength="8"'),
                    source.replace(' minlength="15"', '')):
        assert changed != source
        with pytest.raises(ValueError, match='actual current39 new password minimum'):
            restore_approved_current39_contract(name, changed)


def test_approved39_template_transport_rejects_unlisted_paths():
    source = (ROOT / 'web/templates/dashboard.html').read_text(encoding='utf8')
    for name in ('web/templates/unapproved.html', 'web/templates/../templates/dashboard.html'):
        with pytest.raises(ValueError, match='template scope'):
            restore_approved_current39_contract(name, source)


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
