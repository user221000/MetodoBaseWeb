"""Public preparation page: explicit limits, safe rendering, no consent writes."""
import importlib
from copy import deepcopy
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

CONTACT = 'consultoriahernandez@icloud.com'

class Markup(HTMLParser):
    def __init__(self,text):
        super().__init__(); self.tags=[]; self.links=[]; self.text=[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        values=dict(attrs); self.tags.append((tag,values))
        if tag=='a': self.links.append(values.get('href',''))
    def handle_data(self,data): self.text.append(data)

@pytest.fixture(params=['web.main_web','api.app'])
def privacy_client(request):
    app=importlib.import_module(request.param).create_app()
    with TestClient(app,raise_server_exceptions=False) as client:
        yield client

def test_projection_has_explicit_preparation_status_and_no_invented_identity():
    from web.services.privacy_notice import public_privacy_notice
    first=public_privacy_notice(); second=public_privacy_notice()
    assert first==second and first is not second
    assert first['status']=='preparacion'
    assert first['version']=='2026-11-03-preparacion-1'
    assert first['integral_notice_available'] is False
    assert first['contact_email']==CONTACT
    assert first['responsible_name'] is first['responsible_address'] is None
    first['sections'][0]['paragraphs'].append('owned mutation')
    assert 'owned mutation' not in str(public_privacy_notice())

def test_public_page_is_unauthed_and_marks_notice_incomplete(privacy_client):
    answer=privacy_client.get('/privacidad')
    assert answer.status_code==200,answer.text
    assert answer.headers['content-type'].startswith('text/html')
    assert answer.headers['cache-control']=='no-store'
    assert answer.headers['referrer-policy']=='no-referrer'
    assert answer.headers['x-content-type-options']=='nosniff'
    parsed=Markup(answer.text); text=' '.join(parsed.text)
    assert 'Aviso integral en preparación' in text
    assert 'La identidad y el domicilio del responsable están pendientes de confirmar.' in text
    assert 'no sustituye un aviso de privacidad integral' in text
    assert CONTACT in text
    assert 'None' not in text and '{{' not in text and 'TODO' not in text
    assert [href for href in parsed.links if href.startswith('mailto:')]==['mailto:'+CONTACT]
    assert not any(tag in {'form','input','textarea','select','script','iframe'} for tag,_ in parsed.tags)

def test_public_page_has_no_sql_or_new_acceptance_writes(privacy_client):
    from web.database.engine import get_engine
    statements=[]
    def observed(connection,cursor,statement,parameters,context,many):
        statements.append(statement)
    engine=get_engine(); event.listen(engine,'before_cursor_execute',observed)
    try:
        answer=privacy_client.get('/privacidad')
    finally:
        event.remove(engine,'before_cursor_execute',observed)
    assert answer.status_code==200,answer.text
    assert statements==[]
    # Shared middleware emits its existing technical CSRF cookie. The public
    # page must never establish an account, tracking or acceptance cookie.
    cookies=SimpleCookie()
    for value in answer.headers.get_list('set-cookie'):
        cookies.load(value)
    assert set(cookies)=={'_csrf'}
    assert cookies['_csrf']['httponly'] and cookies['_csrf']['samesite']=='strict'

def test_rendered_text_is_escaped_and_contact_uri_is_fixed(privacy_client,monkeypatch):
    from web.routes import privacy_notice
    from web.services.privacy_notice import public_privacy_notice
    notice=deepcopy(public_privacy_notice())
    hostile='<script>ownedInjection()</script><img src=x onerror="ownedInjection()">'
    notice['title']='Heading '+hostile
    notice['status_message']='Status '+hostile
    notice['sections'][0]['title']='Section '+hostile
    notice['sections'][0]['paragraphs']=['Paragraph '+hostile]
    notice['contact_email']='other@example.invalid" onclick="ownedInjection()'
    monkeypatch.setattr(privacy_notice,'public_privacy_notice',lambda:notice)
    answer=privacy_client.get('/privacidad')
    assert answer.status_code==200,answer.text
    assert '&lt;script&gt;ownedInjection()&lt;/script&gt;' in answer.text
    parsed=Markup(answer.text)
    assert not any(tag in {'script','iframe'} for tag,_ in parsed.tags)
    assert not any(name.lower().startswith('on') for _,attrs in parsed.tags for name in attrs)
    assert not any(tag=='img' and attrs.get('src')=='x' for tag,attrs in parsed.tags)
    assert [href for href in parsed.links if href.startswith('mailto:')]==['mailto:'+CONTACT]
    assert 'Aviso integral en preparación' in ' '.join(parsed.text)

@pytest.mark.parametrize('template',['landing.html','registro.html','base.html','base_usuario.html',
                                    'suscripciones.html','usuario_suscripcion.html'])
def test_relevant_entry_points_link_to_public_information(template):
    source=Path(__file__).resolve().parents[1]/'web'/'templates'/template
    markup=Markup(source.read_text(encoding='utf8'))
    assert '/privacidad' in markup.links

@pytest.mark.parametrize('template',['suscripciones.html','usuario_suscripcion.html'])
def test_cancellation_copy_separates_renewal_from_data_deletion(template):
    source=Path(__file__).resolve().parents[1]/'web'/'templates'/template
    text=' '.join(Markup(source.read_text(encoding='utf8')).text)
    assert 'Cancelar la renovación no elimina' in text
    assert 'planes' in text and 'PDF' in text
