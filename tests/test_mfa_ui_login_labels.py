"""Visible login labels remain programmatically associated after MFA mounting."""
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


class Labels(HTMLParser):
    def __init__(self):
        super().__init__()
        self.labels = set()
        self.inputs = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "label" and "for" in values:
            self.labels.add(values["for"])
        if tag == "input" and values.get("name") in {"email", "password"}:
            self.inputs[values["name"]] = values.get("id")


@pytest.mark.parametrize("template", ["login_gym.html", "login_usuario.html"])
def test_primary_fields_have_explicit_visible_labels(template):
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(root / "web/templates"), autoescape=select_autoescape())
    content = env.get_template(template).render(request=SimpleNamespace(state=SimpleNamespace(csp_nonce="synthetic")),
                                                google_client_id="", static_version="synthetic")
    labels = Labels()
    labels.feed(content)
    assert set(labels.inputs) == {"email", "password"}
    assert all(identifier and identifier in labels.labels for identifier in labels.inputs.values())
