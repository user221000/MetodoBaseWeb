"""Current DOM regressions must fail before the historical visual inverse."""
import hashlib
import json
from pathlib import Path

import pytest

from tests.ci_web41 import visual_contract_current as current

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / name).read_text(encoding="utf8")


@pytest.mark.parametrize("name", current.CURRENT_TEMPLATES)
def test_current_dom_and_complete_historical_inverse_are_both_required(name):
    text = source(name)
    result = current.validate_current_dom(name, text)
    assert result["scope"] == "actual_current_template_semantics_before_historical_inverse"
    restored = current.restore_current_presentation(name, text)
    approved = current.specification()["templates"][name]
    assert hashlib.sha256(restored.encode()).hexdigest() == approved["historical_sha256"]
    assert current.blob(restored.encode()) == approved["historical_blob"]


@pytest.mark.parametrize("name", current.CURRENT_TEMPLATES)
def test_each_actual_template_rejects_new_controls_scripts_and_unreviewed_body(name):
    text = source(name)
    # These two guards run without any complete source hash or inverse check.
    for addition in ('<button type="button">Unexpected</button>',
                     '<script src="/static/js/unreviewed.js"></script>'):
        with pytest.raises(ValueError, match="actual current"):
            current.validate_current_dom(name, text + addition)
    # Nonsemantic byte drift cannot silently acquire the historical approval.
    assert current.validate_current_dom(name, text + " ")
    with pytest.raises(ValueError, match="complete current source"):
        current.restore_current_presentation(name, text + " ")


@pytest.mark.parametrize(("name", "before", "after"), [
    ("configuracion", 'data-permission="update:gym_profile"', 'data-permission="read:gym_profile"'),
    ("configuracion", 'data-gym-equipment-save disabled', 'data-gym-equipment-save'),
    ("configuracion", 'data-gym-equipment-clear disabled', 'data-gym-equipment-clear'),
    ("configuracion", 'maxlength="100"', 'maxlength="10000"'),
    ("registro", 'name="email"', 'name="unreviewed_email"'),
    ("registro", 'type="email"', 'type="text"'),
    ("registro", 'minlength="15"', 'minlength="8"'),
    ("registro", 'autocomplete="new-password"', 'autocomplete="off"'),
    ("registro", 'aria-describedby="registration-email-help"', 'aria-describedby="missing-help"'),
    ("mfa_account_partial", 'id="mfa-account-google-email" class="mfa-account-google-email" hidden', 'id="mfa-account-google-email" class="mfa-account-google-email"'),
    ("mfa_account_partial", 'pattern="[0-9]{6}"', 'pattern=".*"'),
    ("mfa_login_partial", 'id="mfa-login-email" class="mfa-login-proof" novalidate hidden', 'id="mfa-login-email" class="mfa-login-proof" novalidate'),
    ("usuario_mi_plan", 'id="btn-abrir-pdf"', 'id="removed-pdf"'),
    ("usuario_mi_plan", 'aria-label="Cerrar preferencias de alimentos"', 'aria-label=""'),
    ("landing", '{{ plan.precio_centavos }}', '{{ 0 }}'),
    ("landing", '{{ plan.max_planes_mes }}', '{{ 9999 }}'),
    ("landing", 'href="/registro?tipo=gym', 'href="/unreviewed?tipo=gym'),
    ("landing", 'aria-controls="demo-panel-clientes"', 'aria-controls="missing-panel"'),
])
def test_semantic_regressions_fail_without_relying_on_a_snapshot_hash(name, before, after):
    path = "web/templates/" + name + ".html"
    original = source(path)
    changed = original.replace(before, after, 1)
    assert changed != original, "The negative must alter the actual current source"
    with pytest.raises(ValueError, match="actual current"):
        current.validate_current_dom(path, changed)


@pytest.mark.parametrize("duplicate", ['type="text" type="email"', 'TYPE="text" type="email"'])
def test_first_html_attribute_cannot_be_hidden_by_a_later_duplicate(duplicate):
    path = "web/templates/registro.html"
    original = source(path)
    changed = original.replace('type="email"', duplicate, 1)
    assert changed != original
    with pytest.raises(ValueError, match="actual current duplicate HTML attribute"):
        current.validate_current_dom(path, changed)


@pytest.mark.parametrize("name", ["web/templates/unreviewed.html",
                                  "web/templates/../templates/landing.html",
                                  "/web/templates/landing.html"])
def test_current_projection_refuses_unlisted_or_alias_template_paths(name):
    with pytest.raises(ValueError, match="explicit current visual template"):
        current.restore_current_presentation(name, source("web/templates/landing.html"))


@pytest.mark.parametrize("frame", ["LF", "CRLF", "mixed", "changed"])
def test_fixture_only_admits_the_two_complete_reviewed_text_frames(tmp_path, monkeypatch, frame):
    raw = (ROOT / current.FIXTURE).read_bytes().replace(b"\r\n", b"\n")
    if frame == "CRLF":
        raw = raw.replace(b"\n", b"\r\n")
    elif frame == "mixed":
        raw = raw.replace(b"\n", b"\r\n", 1)
    elif frame == "changed":
        raw += b" "
    target = tmp_path / current.FIXTURE
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    monkeypatch.setattr(current, "ROOT", tmp_path)
    if frame in {"LF", "CRLF"}:
        assert len(current.specification()["templates"]) == 22
    else:
        with pytest.raises(ValueError, match="exact current visual transition"):
            current.specification()


def test_approved_control_changes_cannot_remove_or_weaken_original_security_attributes():
    specification = current.specification()
    for entry in specification["templates"].values():
        for change in entry["control_attribute_extensions"]:
            before, after = change["before"], change["current"]
            assert before[0] == after[0]
            assert set(before[1]) <= set(after[1])
            changed = {key for key in set(before[1]) | set(after[1])
                       if before[1].get(key) != after[1].get(key)}
            assert changed <= {"id", "placeholder", "pattern", "aria-describedby", "aria-label"}
            for key in ("data-permission", "disabled", "action", "method", "name", "type", "required", "minlength", "maxlength"):
                assert before[1].get(key) == after[1].get(key)
    # This file remains a contract over current source, not a new historical baseline.
    assert json.loads((ROOT / current.FIXTURE).read_text(encoding="utf8"))["baseline_sha256"] == "24de2f4c5cd272aed46f41788fc46443f8a39895c0e48b4bca3dfb02a7b2d9b3"
