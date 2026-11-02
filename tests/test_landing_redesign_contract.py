"""Public landing contracts through both HTTP factories; no providers or sign-up writes."""
import hashlib
import importlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient


class Markup(HTMLParser):
    """Collect public hooks and catalogue cards without browser behavior."""

    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.cards = {}
        self.current = None
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        self.elements.append((tag, attributes))
        if tag == "article":
            key = attributes.get("data-plan") or attributes.get("data-personal-plan")
            if key:
                self.current = {"elements": [], "text": [], "personal": "data-personal-plan" in attributes}
                self.cards[key] = self.current
        if self.current is not None:
            self.current["elements"].append((tag, attributes))

    def handle_data(self, value):
        if self.current is not None:
            self.current["text"].append(value)

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


@pytest.fixture(params=["api.app", "web.main_web"])
def public_landing(request):
    app = importlib.import_module(request.param).create_app()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        yield client, response, Markup(response.text)


def canonical_catalogs():
    from core.plan_catalog import get_individual_plan_catalog, get_plan_catalog

    return (
        {key: value for key, value in get_plan_catalog("web").items() if value["audiencia"] == "gym"},
        get_individual_plan_catalog(),
    )


def assert_catalog(markup, business, personal):
    assert set(markup.cards) == set(business) | set(personal)
    for key, plan in {**business, **personal}.items():
        card = markup.cards[key]
        price = next(attributes for _, attributes in card["elements"] if "data-price-centavos" in attributes)
        assert int(price["data-price-centavos"]) == plan["precio_centavos"]
        assert price["data-currency"] == plan["moneda"]
        assert price["data-period"] == plan["periodo"]
        assert f"${plan['precio_centavos'] / 100:.2f}" in "".join(card["text"])
        fields = {"max_planes_mes"} if card["personal"] else {
            "max_clientes", "max_registros_diarios", "max_planes_por_cliente_dia",
            "max_planes_diarios", "max_planes_mes",
        }
        values = {
            attributes["data-limit-field"]: int(attributes["data-value"])
            for _, attributes in card["elements"] if "data-limit-field" in attributes
        }
        assert values == {field: plan[field] for field in fields}
        link = next(attributes["href"] for tag, attributes in card["elements"] if tag == "a")
        parsed = urlsplit(link)
        assert parsed.scheme == parsed.netloc == ""
        assert parsed.path == "/registro"
        expected = {"tipo": ["usuario" if card["personal"] else "gym"]}
        if key not in {"free", "starter"}:
            expected["subscription_plan"] = [key]
        assert parse_qs(parsed.query) == expected


def test_live_catalogue_prices_quotas_and_public_subscription_intent(public_landing):
    business, personal = canonical_catalogs()
    assert_catalog(public_landing[2], business, personal)
    assert business["free"]["max_clientes"] == 10
    assert business["free"]["max_planes_diarios"] == 10
    assert business["free"]["max_planes_por_cliente_dia"] == 1
    assert business["free"]["max_planes_mes"] == 20
    assert personal["starter"]["max_planes_mes"] == 1
    assert personal["pro"]["max_planes_mes"] == 5


def test_catalogue_changes_are_rendered_without_marketing_snapshot(public_landing, monkeypatch):
    from web.routes import pages

    business, personal = canonical_catalogs()
    business["standard"]["precio_centavos"] = 15923
    business["free"]["max_clientes"] = 11
    business["free"]["max_planes_mes"] = 23
    business["free"]["max_planes_diarios"] = 14
    personal["starter"]["max_planes_mes"] = 3
    personal["pro"]["precio_centavos"] = 7923
    personal["pro"]["max_planes_mes"] = 7
    monkeypatch.setattr(pages, "get_plan_catalog", lambda target: business)
    monkeypatch.setattr(pages, "get_individual_plan_catalog", lambda: personal)
    response = public_landing[0].get("/")
    assert response.status_code == 200
    assert_catalog(Markup(response.text), business, personal)


def test_demo_and_compact_registration_have_named_accessible_hooks(public_landing):
    _, response, markup = public_landing
    ids = [attributes["id"] for _, attributes in markup.elements if "id" in attributes]
    assert len(ids) == len(set(ids))
    for name in ("landing-demo", "demo-tabs", "registration-invite", "registration-invite-panel",
                 "registration-invite-toggle", "registration-invite-close", "registration-invite-register",
                 "demo-client-search", "demo-client-empty", "demo-previous", "demo-next", "demo-progress",
                 "demo-expand", "pricing-controls", "pricing-compare"):
        assert name in ids
    panels = [attributes for _, attributes in markup.elements if attributes.get("role") == "tabpanel"]
    assert {panel["id"] for panel in panels} == {
        "demo-panel-clientes", "demo-panel-plan", "demo-panel-historial", "demo-panel-rutinas",
    }
    tabs = [attributes for tag, attributes in markup.elements if tag == "button" and "data-demo-tab" in attributes]
    assert len(tabs) == 4
    assert all(tab.get("role") == "tab" and tab.get("aria-controls") in ids for tab in tabs)
    assert sum("hidden" not in panel for panel in panels) == 1
    assert "datos de ejemplo" in response.text
    radios = [attributes for tag, attributes in markup.elements if tag == "input" and attributes.get("name") == "invite-audience"]
    assert {radio["value"] for radio in radios} == {"gym", "usuario"}
    search = next(attributes for tag, attributes in markup.elements if attributes.get("id") == "demo-client-search")
    assert search.get("type") == "search"
    assert "disabled" in search
    clients = [attributes for _, attributes in markup.elements if "data-demo-client" in attributes]
    assert len(clients) == 3 and all(client.get("data-client-name") for client in clients)
    choices = [attributes for tag, attributes in markup.elements if tag == "button" and "data-pricing-audience" in attributes]
    assert {choice["data-pricing-audience"] for choice in choices} == {"gym", "usuario"}
    assert all(choice.get("aria-controls") in ids for choice in choices)
    controls = next(attributes for _, attributes in markup.elements if attributes.get("id") == "pricing-controls")
    assert "hidden" in controls
    plan_pickers = [attributes for _, attributes in markup.elements if "data-plan-picker" in attributes]
    assert plan_pickers and all("hidden" in picker for picker in plan_pickers)
    # Every price/limit remains rendered and reachable before JS enhancement.
    cards = [attributes for tag, attributes in markup.elements if tag == "article"
             and ("data-plan" in attributes or "data-personal-plan" in attributes)]
    assert len(cards) == 6 and all("hidden" not in card for card in cards)
    details = [attributes for tag, attributes in markup.elements if tag == "details"
               and "plan-details" in attributes.get("class", "").split()]
    assert len(details) == 6


def test_first_party_script_is_versioned_and_has_current_csp_nonce(public_landing):
    client, response, markup = public_landing
    nonce = re.search(r"'nonce-([^']+)'", response.headers["content-security-policy"]).group(1)
    scripts = [attributes for tag, attributes in markup.elements if tag == "script"]
    own = [script for script in scripts if script.get("src", "").startswith("/static/js/landing.js?")]
    assert len(own) == 1
    assert own[0]["nonce"] == nonce
    root = Path(__file__).resolve().parents[1]
    version = hashlib.sha256((root / "web/static/js/landing.js").read_bytes()).hexdigest()[:12]
    assert own[0]["src"] == "/static/js/landing.js?v=" + version
    assert all(script.get("nonce") == nonce for script in scripts)
    for path in ("/static/js/landing.js", "/static/css/landing.css"):
        assert client.get(path).status_code == 200
    css_version = hashlib.sha256((root / "web/static/css/landing.css").read_bytes()).hexdigest()[:12]
    assert "/static/css/landing.css?v=" + css_version in response.text


def test_navigation_targets_exist_and_existing_registration_pages_remain_reachable(public_landing):
    client, _, markup = public_landing
    ids = {attributes["id"] for _, attributes in markup.elements if "id" in attributes}
    for tag, attributes in markup.elements:
        if tag != "a":
            continue
        href = attributes.get("href", "")
        parsed = urlsplit(href)
        assert parsed.scheme in {"", "https", "mailto"}
        if href.startswith("#"):
            assert href[1:] in ids
        if parsed.path == "/registro":
            assert parse_qs(parsed.query)["tipo"] in [["gym"], ["usuario"]]
    for path in ("/registro?tipo=gym", "/registro?tipo=usuario",
                 "/registro?tipo=gym&subscription_plan=standard",
                 "/registro?tipo=usuario&subscription_plan=pro",
                 "/login-gym", "/login-usuario"):
        assert client.get(path).status_code == 200


def test_landing_request_has_no_database_writes_or_sensitive_demo_transport(public_landing):
    from sqlalchemy import event

    from web.database.engine import get_engine

    writes = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE")):
            writes.append(statement)

    event.listen(get_engine(), "before_cursor_execute", observe)
    try:
        assert public_landing[0].get("/").status_code == 200
    finally:
        event.remove(get_engine(), "before_cursor_execute", observe)
    assert writes == []
    script = (Path(__file__).resolve().parents[1] / "web/static/js/landing.js").read_text(encoding="utf-8")
    for forbidden in ("fetch(", "XMLHttpRequest", "mb_token", "mb_refresh_token", "mb_email", "mb_tipo"):
        assert forbidden not in script
    assert "escritorio sigue soportada" not in public_landing[1].text
    example = json.loads((Path(__file__).resolve().parents[1] / "web/static/data/landing-example.json").read_text(encoding="utf-8"))
    for group in example["groups"]:
        assert str(group["option"]["gramos"]) in public_landing[1].text

