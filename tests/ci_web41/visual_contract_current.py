"""Current DOM contracts plus a finite inverse for the historical visual oracle.

The inverse is not acceptance of current behavior: current controls, identity,
permissions, navigation, catalogue expressions and scripts are checked first.
The public catalogue and browser journeys have their own current-source gates.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = "tests/ci_web41/fixtures/visual-current-20261103.json"
FIXTURE_SHA256 = "8e0a535815be1fd83382a2b705f7aae4b9ef9fa81daf5197612b385c87deee45"
FIXTURE_BYTES = 273037
CURRENT_TEMPLATES = (
    "web/templates/accept_invite.html", "web/templates/account_recovery.html",
    "web/templates/base.html", "web/templates/base_usuario.html",
    "web/templates/clientes.html", "web/templates/configuracion.html",
    "web/templates/cuenta_seguridad37.html", "web/templates/dashboard.html",
    "web/templates/generar-plan.html", "web/templates/landing.html",
    "web/templates/login_gym.html", "web/templates/login_usuario.html",
    "web/templates/mfa_account_partial.html", "web/templates/mfa_login_partial.html",
    "web/templates/planes.html", "web/templates/registro.html",
    "web/templates/suscripciones.html", "web/templates/usuario_historial.html",
    "web/templates/usuario_mi_plan.html", "web/templates/usuario_perfil.html",
    "web/templates/usuario_seguridad37.html", "web/templates/usuario_suscripcion.html",
)
MESSAGE = "The approved current39 source or historical contract differs"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                        usedforsecurity=False).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("A current visual fixture contains a duplicate key")
        result[key] = value
    return result


def specification():
    path = ROOT / FIXTURE
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024
            or path.resolve(strict=True) != path.absolute() or info.st_nlink != 1):
        raise ValueError("The current visual fixture must be a plain owned source file")
    with path.open("rb") as handle:
        raw = handle.read(FIXTURE_BYTES * 2 + 1)
    lf = raw.replace(b"\r\n", b"\n")
    if (raw not in (lf, lf.replace(b"\n", b"\r\n")) or b"\r" in lf
            or len(lf) != FIXTURE_BYTES or digest(lf) != FIXTURE_SHA256):
        raise ValueError("The exact current visual transition fixture differs")
    value = json.loads(lf, object_pairs_hook=_pairs)
    if (value["schema"] != "reviewed-current-visual-transition-20261103-v1"
            or set(value["templates"]) != set(CURRENT_TEMPLATES)):
        raise ValueError("The finite current visual template scope differs")
    return value


class CurrentDOM(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids = []
        self.controls = []
        self.data = []
        self.script_sources = []
        self.feed(source)

    def handle_starttag(self, tag, items):
        if len({name for name, _ in items}) != len(items):
            raise ValueError(MESSAGE + ": actual current duplicate HTML attribute")
        attrs = dict(items)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag in {"form", "input", "select", "textarea", "button"}:
            self.controls.append([tag, {key: value for key, value in attrs.items()
                                      if key not in {"style", "class", "for", "title"}}])
        data = {key: value for key, value in attrs.items() if key.startswith("data-")}
        if data:
            self.data.append(data)
        if tag == "script" and "src" in attrs:
            self.script_sources.append(attrs["src"])


def _counter(controls):
    return Counter(json.dumps(item, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")) for item in controls)


def _control(dom, identity, tag, required):
    found = [attrs for actual_tag, attrs in dom.controls
             if actual_tag == tag and attrs.get("id") == identity]
    if len(found) != 1 or any(key not in found[0] or found[0][key] != value
                              for key, value in required.items()):
        raise ValueError(MESSAGE + ": current extension control " + identity)


def validate_current_dom(name, source):
    """Check current semantics without consulting the source hash or inverse.

    New controls are finite additions. Existing controls remain exact except
    the explicitly reviewed accessibility/placeholder additions. In particular
    permission, disabled, form action, field name/type and password limits are
    never discarded for a historical comparison.
    """
    if name not in CURRENT_TEMPLATES or not isinstance(source, str):
        raise ValueError("An explicit current visual template path is required")
    approved = specification()["templates"][name]
    dom = CurrentDOM(source)
    expected = approved["original_controls"].copy()
    for change in approved["control_attribute_extensions"]:
        expected.remove(change["before"])
        expected.append(change["current"])
    expected.extend(approved["added_controls"])
    if _counter(dom.controls) != _counter(expected):
        raise ValueError(MESSAGE + ": actual current forms or permissions")
    if (dom.ids != approved["current_ids"] or dom.data != approved["current_data"]
            or re.findall(r'href="([^"]+)"', source) != approved["current_hrefs"]
            or re.findall(r"\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\}", source) != approved["current_jinja"]):
        raise ValueError(MESSAGE + ": actual current identity, navigation or catalogue")
    scripts = [digest(value.encode()) for value in re.findall(r"<script\b[\s\S]*?</script>", source, re.IGNORECASE)]
    if scripts != approved["current_scripts"] or any(not value.startswith("/static/js/") for value in dom.script_sources):
        raise ValueError(MESSAGE + ": actual current scripts")
    for tag, attrs in dom.controls:
        if (tag == "input" and attrs.get("autocomplete") == "new-password"
                and (attrs.get("type") != "password" or attrs.get("minlength") != "15")):
            raise ValueError(MESSAGE + ": actual current password minimum")
    if name.endswith("/configuracion.html"):
        _control(dom, "gym-equipment-query", "input", {"type": "search", "maxlength": "100", "autocomplete": "off"})
        for flag in ("data-gym-equipment-save", "data-gym-equipment-clear"):
            matches = [attrs for tag, attrs in dom.controls if tag == "button" and flag in attrs]
            if len(matches) != 1 or "disabled" not in matches[0]:
                raise ValueError(MESSAGE + ": equipment write starts disabled")
    if name.endswith("/mfa_account_partial.html"):
        _control(dom, "mfa-account-google-email", "form", {"hidden": None})
        _control(dom, "mfa-account-google-email-code", "input",
                 {"type": "text", "inputmode": "numeric", "autocomplete": "one-time-code", "maxlength": "6", "pattern": "[0-9]{6}"})
    if name.endswith("/mfa_login_partial.html"):
        _control(dom, "mfa-login-email", "form", {"hidden": None})
        _control(dom, "mfa-login-email-code", "input",
                 {"minlength": "6", "maxlength": "6", "pattern": "[0-9]{6}", "required": None})
    if name.endswith("/usuario_mi_plan.html"):
        _control(dom, "btn-abrir-pdf", "button", {})
        _control(dom, "panel-excluir-close", "button", {"aria-label": "Cerrar preferencias de alimentos"})
    return {"controls": len(dom.controls), "ids": len(dom.ids), "scripts": len(scripts),
            "scope": "actual_current_template_semantics_before_historical_inverse"}


def restore_current_presentation(name, source):
    """Accept only the complete reviewed current source and its exact inverse."""
    validate_current_dom(name, source)
    approved = specification()["templates"][name]
    raw = source.encode("utf8")
    if digest(raw) != approved["current_sha256"] or blob(raw) != approved["current_blob"]:
        raise ValueError(MESSAGE + ": complete current source")
    for edit in reversed(approved["inverse_edits"]):
        begin = edit["current_offset"]
        end = begin + len(edit["current"])
        if source[begin:end] != edit["current"]:
            raise ValueError(MESSAGE + ": finite current inverse")
        source = source[:begin] + edit["original"] + source[end:]
    restored = source.encode("utf8")
    if digest(restored) != approved["historical_sha256"] or blob(restored) != approved["historical_blob"]:
        raise ValueError(MESSAGE + ": complete historical source")
    return source
