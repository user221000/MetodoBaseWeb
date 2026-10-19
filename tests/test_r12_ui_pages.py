"""UI shell composition on base28 only; does not test or claim a deployed R12 API."""
from pathlib import Path
import re

import pytest
from tests.test_landing_commercial import landing, Markup


@pytest.mark.parametrize('path,title',[
    ('/clientes/synthetic-client/vinculacion','Vínculo y plan compartido'),
    ('/mis-vinculos','Mis vínculos con gimnasios'),
    ('/auth/accept-client-link','Aceptar un vínculo con un gimnasio'),
])
def test_new_pages_render_without_private_data_and_use_only_own_assets(landing,path,title):
    client=landing[0]
    response=client.get(path)
    assert response.status_code==200
    assert title in response.text
    assert response.headers['referrer-policy']=='no-referrer'
    assert 'no-store' in response.headers['cache-control']
    markup=Markup(response.text)
    for tag,attrs in markup.elements:
        if tag=='script' and 'src' in attrs:
            assert attrs['src'].startswith('/static/js/')
            assert client.get(attrs['src']).status_code==200
        if tag=='link' and attrs.get('rel')=='stylesheet':
            assert attrs['href'].startswith('/static/css/')
            assert client.get(attrs['href']).status_code==200
    assert 'localStorage' not in response.text and 'sessionStorage' not in response.text
    assert 'Synthetic member' not in response.text


def test_fragment_bootstrap_precedes_assets_and_never_uses_a_query_bearer(landing):
    response=landing[0].get('/auth/accept-client-link')
    script=re.search(r'<script nonce="([^"]+)">([\s\S]*?)</script>',response.text)
    assert script and f"'nonce-{script.group(1)}'" in response.headers['content-security-policy']
    assert response.text.index('<script nonce=') < response.text.index('<link rel="stylesheet"')
    assert response.text.index('<script nonce=') < response.text.index('<script src=')
    assert 'history.replaceState(null' in script.group(2)
    assert 'fetch(' not in script.group(2)
    assert 'confirm:true' not in script.group(2)
    links=[a['href'] for tag,a in Markup(response.text).elements if tag=='a']
    assert '/registro?tipo=usuario' in links
    assert not any('token=' in link or 'return_to' in link for link in links)


def test_page_registration_is_unique_and_existing_profile_routes_remain_present(landing):
    from fastapi.routing import _iter_routes_with_context
    paths=[context.path if context else getattr(route,'path',None) for route,context in _iter_routes_with_context(landing[0].app.routes)]
    for path in ['/mis-vinculos','/auth/accept-client-link','/clientes/{client_id}/vinculacion','/mi-plan','/mi-perfil','/mi-historial']:
        assert paths.count(path)==1
    for name in ['vinculos-invitacion.js','vinculos-profesional.js','vinculos-lectura.js','vinculos-ui.js']:
        source=(Path(__file__).resolve().parents[1]/'web/static/js'/name).read_text(encoding='utf8')
        assert '.innerHTML' not in source
        assert 'localStorage' not in source and 'sessionStorage' not in source
