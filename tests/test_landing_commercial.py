"""Commercial claims and linked audiences from both real HTTP factories, offline."""
import importlib
import json
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient
import pytest


class Markup(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.cards = {}
        self.card = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == 'article':
            key = attrs.get('data-plan') or attrs.get('data-personal-plan')
            self.card = {'elements':[], 'text':[], 'personal':'data-personal-plan' in attrs}
            self.cards[key] = self.card
        if self.card is not None:
            self.card['elements'].append((tag,attrs))

    def handle_data(self, value):
        if self.card is not None:
            self.card['text'].append(value)

    def handle_endtag(self, tag):
        if tag == 'article':
            self.card = None


@pytest.fixture(params=['web.main_web','api.app'])
def landing(request):
    with TestClient(importlib.import_module(request.param).create_app()) as client:
        response = client.get('/')
        assert response.status_code == 200
        yield client, response, Markup(response.text)


def test_public_offer_is_present_and_has_no_global_unlimited_or_speed_promise(landing):
    text = landing[1].text.lower()
    assert 'data-commercial-catalog' in text
    for unsupported in ['ilimitados en segundos','en 5 minutos','100% personalizado','siempre privada y segura','métricas y reportes de retención']:
        assert unsupported not in text


def assert_offer(markup, business, personal):
    assert set(markup.cards) == set(business)|set(personal)
    for key,plan in {**business,**personal}.items():
        card = markup.cards[key]
        price = next(attrs for _,attrs in card['elements'] if 'data-price-centavos' in attrs)
        assert int(price['data-price-centavos']) == plan['precio_centavos']
        assert price['data-currency'] == plan['moneda'] and price['data-period'] == plan['periodo']
        assert f"${plan['precio_centavos']/100:.2f}" in ''.join(card['text'])
        fields = {'max_planes_mes'} if card['personal'] else {'max_clientes','max_registros_diarios','max_planes_por_cliente_dia','max_planes_diarios','max_planes_mes'}
        limits = {attrs['data-limit-field']:int(attrs['data-value']) for _,attrs in card['elements'] if 'data-limit-field' in attrs}
        assert limits == {name:plan[name] for name in fields}
        assert [attrs['href'] for tag,attrs in card['elements'] if tag=='a'] == ['/registro?tipo=usuario' if card['personal'] else '/registro?tipo=gym']


def test_every_price_currency_period_and_limit_matches_canonical_catalog(landing):
    from core.plan_catalog import get_plan_catalog, get_individual_plan_catalog
    business = {key:plan for key,plan in get_plan_catalog('web').items() if plan['audiencia']=='gym'}
    assert_offer(landing[2],business,get_individual_plan_catalog())
    assert 'pro_usuario' not in landing[2].cards
    assert business['free']['max_clientes']==10
    assert business['free']['max_planes_por_cliente_dia']==1
    assert business['free']['max_planes_diarios']==10
    assert business['free']['max_planes_mes']==20


def test_runtime_catalog_change_renders_without_a_duplicated_offer_snapshot(landing,monkeypatch):
    from core.plan_catalog import get_plan_catalog, get_individual_plan_catalog
    from web.routes import pages
    business = get_plan_catalog('web')
    personal = get_individual_plan_catalog()
    business['standard']['precio_centavos'] = 15923
    business['free']['max_clientes'] = 11
    business['free']['max_planes_mes'] = 23
    personal['pro']['precio_centavos'] = 7923
    personal['pro']['max_planes_mes'] = 6
    monkeypatch.setattr(pages,'get_plan_catalog',lambda target:business)
    monkeypatch.setattr(pages,'get_individual_plan_catalog',lambda:personal)
    response = landing[0].get('/')
    assert response.status_code == 200
    assert_offer(Markup(response.text),{key:plan for key,plan in business.items() if plan['audiencia']=='gym'},personal)


def test_ctas_are_exact_audience_routes_and_fragment_links_exist(landing):
    allowed = {'/','/login-gym','/login-usuario','/registro?tipo=gym','/registro?tipo=usuario',
        '#contenido','#planes-negocio','#planes-personales','#datos-personales'}
    elements = landing[2].elements
    ids = [attrs['id'] for _,attrs in elements if 'id' in attrs]
    assert len(ids)==len(set(ids))
    links = [attrs['href'] for tag,attrs in elements if tag=='a']
    assert set(links)==allowed
    assert all(link[1:] in ids for link in links if link.startswith('#'))
    for path in ['/registro?tipo=gym','/registro?tipo=usuario','/login-gym','/login-usuario']:
        assert landing[0].get(path).status_code == 200


def test_synthetic_excerpt_is_copied_from_actual_generated_worker_result(landing):
    root = Path(__file__).resolve().parents[1]
    example = json.loads((root/'web/static/data/landing-example.json').read_text(encoding='utf8'))
    plan = json.loads((root/'docs/implementation/20261018-evolution/evidence/landing/worker-example/generated-plan.json').read_text(encoding='utf8'))
    assert set(example)=={'format','meal','groups'}
    assert example['format']=='worker_demo_excerpt_v1' and example['meal']=='desayuno'
    assert example['groups']==[{'group':group,'option':plan['desayuno'][group]['opciones'][0]} for group in ('proteinas','carbohidratos','grasas')]
    assert 'Ejemplo con datos de demostración' in landing[1].text
    assert 'no es una recomendación de alimentación ni una evaluación clínica' in landing[1].text
    assert not any(key in json.dumps(example) for key in ['token','id_cliente','pdf_url','ruta_pdf'])


def test_public_view_never_reads_credentials_fetches_private_data_or_writes(landing):
    import hashlib
    from sqlalchemy import event
    from web.database.engine import get_engine
    writes = []
    def observed(connection,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','ALTER','CREATE')):
            writes.append(statement)
    event.listen(get_engine(),'before_cursor_execute',observed)
    try:
        assert landing[0].get('/').status_code==200
    finally:
        event.remove(get_engine(),'before_cursor_execute',observed)
    assert writes==[]
    for legacy in ['localStorage','sessionStorage','window.location.replace','<script','https://fonts.']:
        assert legacy not in landing[1].text
    assert landing[0].get('/static/css/landing.css').status_code==200
    version = hashlib.sha256(Path('web/static/css/landing.css').read_bytes()).hexdigest()[:12]
    assert f'/static/css/landing.css?v={version}' in landing[1].text
    assert landing[0].get('/static/data/landing-example.json').status_code==200
    assert landing[0].get('/landing.html').status_code==404
    assert not Path('web/pages/landing.html').exists()
    # R29 retires the remaining unmounted commercial duplicate as well.
    assert not Path('web/pages/checkout.html').exists()
    for path in ['/checkout.html', '/pages/checkout.html', '/web/pages/checkout.html',
                 '/pages/landing.html', '/web/pages/landing.html']:
        assert landing[0].get(path).status_code == 404
