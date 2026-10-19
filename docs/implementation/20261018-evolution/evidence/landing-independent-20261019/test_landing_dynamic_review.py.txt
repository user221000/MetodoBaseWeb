"""Independent visible offer metadata must remain consistent with runtime catalog."""
from tests.test_landing_commercial import landing, Markup, assert_offer


def test_changed_billing_period_is_consistent_in_cards_and_catalog_note(landing, monkeypatch):
    from core.plan_catalog import get_plan_catalog, get_individual_plan_catalog
    from web.routes import pages
    business = get_plan_catalog('web')
    personal = get_individual_plan_catalog()
    for plan in [*business.values(), *personal.values()]:
        plan['moneda'] = 'TST'
        plan['periodo'] = 'year'
    business['free']['max_planes_por_cliente_dia'] = 2
    business['free']['max_planes_diarios'] = 11
    personal['starter']['max_planes_mes'] = 2
    monkeypatch.setattr(pages, 'get_plan_catalog', lambda _target: business)
    monkeypatch.setattr(pages, 'get_individual_plan_catalog', lambda: personal)
    response = landing[0].get('/')
    assert response.status_code == 200
    assert_offer(Markup(response.text), {key: plan for key, plan in business.items() if plan['audiencia'] == 'gym'}, personal)
    assert 'TST / year' in response.text
    assert 'con periodo mensual' not in response.text
