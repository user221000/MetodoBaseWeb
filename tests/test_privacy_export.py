"""R31 privacy export: real persisted identity, bounded personal data only."""
import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from web.database.engine import get_engine
from web.database.models import (
    Cliente, ClientProgress, GenerationReservation, PlanGenerado, PurchaseIntent,
    RefreshToken, Subscription, Usuario, UserRole, UserSubscription,
)


@pytest.fixture
def privacy_case():
    from web.auth import crear_access_token
    from web.middleware.tenant import TenantMiddleware

    ids = {name: str(uuid.uuid4()) for name in ("owner", "member", "other")}
    with Session(get_engine()) as db:
        for name in ids:
            db.add(Usuario(id=ids[name], email=name + "@example.invalid", nombre=name,
                apellido="Synthetic", password_hash="synthetic-password-hash-omit",
                tipo="gym" if name == "owner" else "usuario",
                role=UserRole.OWNER if name == "owner" else UserRole.VIEWER,
                activo=True, session_version=0))
        db.flush()
        db.get(Usuario, ids["member"]).team_gym_id = ids["owner"]
        for name in ids:
            db.add(Cliente(gym_id=ids[name], id_cliente="profile-" + name, nombre="profile-" + name,
                email=name + "@example.invalid", edad=30, notas="own-health-note-" + name,
                alimentos_excluidos='["synthetic food"]'))
        db.flush()
        for name in ids:
            db.add(PlanGenerado(gym_id=ids[name], id_cliente="profile-" + name,
                ruta_pdf="C:/private/" + name + ".pdf", kcal_objetivo=2000,
                plan_json=json.dumps({"desayuno": {"kcal_objetivo": 500,
                    "alimentos": {"synthetic food": 100}}, "provider_secret": "omit-json-secret"})))
            db.add(ClientProgress(gym_id=ids[name], id_cliente="profile-" + name,
                peso_kg=70, notas="measurement-" + name))
            db.add(UserSubscription(user_id=ids[name], plan="starter", mes_actual="2026-10"))
            db.add(Subscription(gym_id=ids[name], plan="free" if name == "owner" else "pro_usuario",
                status="active", provider="stripe", stripe_customer_id="omit-customer-" + name,
                stripe_subscription_id="omit-provider-sub-" + name))
            db.add(PurchaseIntent(subject_id=ids[name], provider="stripe", operation="checkout",
                request_key="omit-idempotency-" + name, plan="pro_usuario", amount_cents=7900,
                provider_customer_id="omit-customer-" + name,
                provider_reference_id="omit-reference-" + name))
            db.add(GenerationReservation(user_id=ids[name], request_key="omit-request-" + name,
                period="2026-10", status="released"))
            db.add(RefreshToken(jti="omit-refresh-" + name, user_id=ids[name], expires_at=9999999999,
                created_at=1, revoked=False))
        db.commit()
    identities = {}
    for name, uid in ids.items():
        identity = {"id": uid, "email": name + "@example.invalid", "nombre": name,
            "tipo": "gym" if name == "owner" else "usuario",
            "role": "owner" if name == "owner" else "viewer",
            "team_gym_id": ids["owner"] if name == "member" else None, "session_version": 0}
        identities[name] = {**identity, "token": crear_access_token(identity)}
    app = FastAPI()
    from web.routes.privacy import router
    app.include_router(router, prefix="/api")
    app.add_middleware(TenantMiddleware)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, ids, identities


def request_export(case, actor="member", **params):
    return case[0].get("/api/usuario/privacidad/exportar", params=params,
        headers={"Authorization": "Bearer " + case[2][actor]["token"]})


def test_export_requires_authentication(privacy_case):
    assert privacy_case[0].get("/api/usuario/privacidad/exportar").status_code == 401


def test_member_exports_personal_space_and_never_professional_cartera(privacy_case):
    response = request_export(privacy_case)
    assert response.status_code == 200
    data = response.json()
    assert data["account"]["id"] == privacy_case[1]["member"]
    assert [p["nombre"] for p in data["profiles"]["records"]] == ["profile-member"]
    assert data["measurements"]["records"][0]["notas"] == "measurement-member"
    assert "own-health-note-member" in response.text
    assert "own-health-note-owner" not in response.text and "own-health-note-other" not in response.text
    assert "measurement-owner" not in response.text and "measurement-other" not in response.text
    assert len(data["plans"]["records"]) == 1


def test_owner_exports_account_without_business_clients_or_plans(privacy_case):
    response = request_export(privacy_case, "owner")
    assert response.status_code == 200
    data = response.json()
    assert data["account"]["id"] == privacy_case[1]["owner"]
    for section in ("profiles", "plans", "measurements", "purchases", "generation_requests"):
        assert data[section]["records"] == []
    assert data["personal_subscription"] is None
    assert data["canonical_subscription"] is None
    assert data["scope"]["personal_space"] is False


def test_download_is_uncacheable_and_has_no_pii_filename(privacy_case):
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == 'attachment; filename="metodobase-datos-personales.json"'


def test_secrets_paths_provider_ids_and_opaque_tokens_are_not_exported(privacy_case):
    response = request_export(privacy_case)
    assert response.status_code == 200
    for forbidden in ("password_hash", "session_version", "invitation_token", "jti", "request_key",
        "provider_secret", "omit-json-secret", "C:/private", "ruta_pdf", "omit-refresh",
        "omit-provider-sub", "omit-customer", "omit-reference", "omit-idempotency", "omit-request"):
        assert forbidden not in response.text
    assert response.json()["purchases"]["records"][0]["amount_cents"] == 7900


def test_both_tenant_and_client_ownership_must_match(privacy_case):
    with Session(get_engine()) as db:
        db.add(PlanGenerado(gym_id=privacy_case[1]["member"], id_cliente="profile-other",
                           objetivo="foreign-client-marker"))
        db.add(ClientProgress(gym_id=privacy_case[1]["member"], id_cliente="profile-other",
                              notas="foreign-client-marker"))
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert "foreign-client-marker" not in response.text
    assert len(response.json()["plans"]["records"]) == 1


def test_ignored_authority_parameters_cannot_select_another_subject(privacy_case):
    response = request_export(privacy_case, gym_id=privacy_case[1]["owner"],
                              user_id=privacy_case[1]["other"], email="owner@example.invalid")
    assert response.status_code == 200
    assert response.json()["account"]["id"] == privacy_case[1]["member"]
    assert "own-health-note-owner" not in response.text and "own-health-note-other" not in response.text


@pytest.mark.parametrize("change", ["inactive", "deleted", "revoked", "membership_changed"])
def test_stale_identity_cannot_export(privacy_case, change):
    with Session(get_engine()) as db:
        user = db.get(Usuario, privacy_case[1]["member"])
        if change == "inactive":
            user.activo = False
        elif change == "deleted":
            user.deleted_at = datetime.now(timezone.utc)
        elif change == "revoked":
            user.session_version += 1
        else:
            user.team_gym_id = None
        db.commit()
    assert request_export(privacy_case).status_code == 401


def test_export_never_writes_or_creates_a_default_profile(privacy_case):
    with Session(get_engine()) as db:
        # Use an account with no dependent profile or plan.
        user = Usuario(id=str(uuid.uuid4()), email="empty@example.invalid", nombre="Empty",
                       password_hash="synthetic-only", tipo="usuario", role=UserRole.VIEWER)
        db.add(user)
        db.commit()
        uid = user.id
    from web.auth import crear_access_token
    token = crear_access_token({"id": uid, "email": "empty@example.invalid", "nombre": "Empty",
                               "tipo": "usuario", "role": "viewer"})
    statements = []
    def observed(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split(None, 1)[0].upper())
    event.listen(get_engine(), "before_cursor_execute", observed)
    try:
        response = privacy_case[0].get("/api/usuario/privacidad/exportar",
            headers={"Authorization": "Bearer " + token})
    finally:
        event.remove(get_engine(), "before_cursor_execute", observed)
    assert response.status_code == 200
    assert not set(statements).intersection({"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"})
    with Session(get_engine()) as db:
        assert db.execute(select(Cliente).where(Cliente.gym_id == uid)).first() is None


def test_cursor_pages_are_bounded_and_complete_without_duplication(privacy_case):
    with Session(get_engine()) as db:
        for index in range(5):
            db.add(PlanGenerado(gym_id=privacy_case[1]["member"], id_cliente="profile-member",
                               kcal_objetivo=2001 + index))
        db.commit()
    seen = []
    params = {"limit": 2}
    for _ in range(4):
        response = request_export(privacy_case, **params)
        assert response.status_code == 200
        page = response.json()["plans"]
        assert len(page["records"]) <= 2
        seen.extend(row["id"] for row in page["records"])
        if page["next_after"] is None:
            break
        params["after_plan"] = page["next_after"]
    assert len(seen) == len(set(seen)) == 6
    assert response.json()["scope"]["consistency"] == "live_keyset_pages"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"after_plan": -1},
    {"after_purchase": "not-a-uuid"}, {"after_generation": "not-a-uuid"}])
def test_invalid_volume_and_cursor_are_rejected(privacy_case, params):
    assert request_export(privacy_case, **params).status_code == 422


@pytest.mark.parametrize("raw", [None, "not-json", "[]", '{"desayuno":null}'])
def test_missing_or_malformed_legacy_plan_is_reported_without_reading_disk(privacy_case, raw, monkeypatch):
    with Session(get_engine()) as db:
        record = db.execute(select(PlanGenerado).where(PlanGenerado.gym_id == privacy_case[1]["member"])).scalar_one()
        record.plan_json = raw
        db.commit()
    monkeypatch.setattr("builtins.open", lambda *a, **k: pytest.fail("Export must not read legacy PDF paths"))
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert response.json()["plans"]["records"][0]["content_status"] == "unavailable_legacy_content"


def test_stale_principal_fields_do_not_override_persisted_account(privacy_case):
    with Session(get_engine()) as db:
        db.get(Usuario, privacy_case[1]["member"]).nombre = "Persisted current name"
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert response.json()["account"]["nombre"] == "Persisted current name"


def test_legacy_professional_gym_type_keeps_only_own_personal_space(privacy_case):
    from web.auth import crear_access_token
    with Session(get_engine()) as db:
        db.get(Usuario, privacy_case[1]["member"]).tipo = "gym"
        db.commit()
    identity = {**privacy_case[2]["member"], "tipo": "gym"}
    privacy_case[2]["member"]["token"] = crear_access_token(identity)
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert response.json()["scope"]["personal_space"] is True
    assert [p["nombre"] for p in response.json()["profiles"]["records"]] == ["profile-member"]


def test_soft_deleted_personal_records_are_visible_in_export_without_becoming_active(privacy_case):
    with Session(get_engine()) as db:
        record = db.execute(select(Cliente).where(Cliente.gym_id == privacy_case[1]["member"])).scalar_one()
        record.deleted_at, record.activo = datetime.now(timezone.utc), False
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert response.json()["profiles"]["records"][0]["deleted_at"] is not None
    assert response.json()["profiles"]["records"][0]["activo"] is False
    with Session(get_engine()) as db:
        assert db.execute(select(Cliente).where(Cliente.gym_id == privacy_case[1]["member"])).scalar_one().activo is False


def test_bad_nested_legacy_json_does_not_break_export_or_release_unknown_keys(privacy_case):
    raw = {"desayuno": {"tipo_plan": ["invalid"], "proteinas": {"provider_secret": "hidden",
        "cantidad_objetivo": 40, "opciones": [None, {"alimento": "Synthetic", "gramos": 100,
            "password_hash": "hidden", "macros": {"proteina": 20, "provider_secret": "hidden"}}]},
        "vegetales": [None, {"alimento": "Synthetic", "gramos": 10, "token": "hidden"}]}}
    with Session(get_engine()) as db:
        db.execute(select(PlanGenerado).where(PlanGenerado.gym_id == privacy_case[1]["member"])).scalar_one().plan_json = json.dumps(raw)
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert "hidden" not in response.text and "provider_secret" not in response.text
    content = response.json()["plans"]["records"][0]["structured_plan"]["desayuno"]
    assert content["proteinas"]["opciones"][0]["macros"] == {"proteina": 20}


def test_oversized_body_is_reported_explicitly_and_not_silently_truncated(privacy_case):
    from web.services.privacy_export import MAX_PLAN_JSON_CHARS
    with Session(get_engine()) as db:
        db.execute(select(PlanGenerado).where(PlanGenerado.gym_id == privacy_case[1]["member"])).scalar_one().plan_json = " " * (MAX_PLAN_JSON_CHARS + 1)
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    body = response.json()["plans"]["records"][0]
    assert body["structured_plan"] is None and body["content_status"] == "oversized_legacy_content"


def test_service_rejects_ambient_professional_tenant_and_resets_context(privacy_case):
    from fastapi import HTTPException
    from web.database.tenant_context import current_tenant
    from web.services.privacy_export import export_personal_data
    token = current_tenant.set(privacy_case[1]["owner"])
    try:
        with Session(get_engine()) as db:
            with pytest.raises(HTTPException) as error:
                export_personal_data(db, privacy_case[1]["member"])
        assert error.value.status_code == 403
        assert current_tenant.get() == privacy_case[1]["owner"]
    finally:
        current_tenant.reset(token)


@pytest.mark.parametrize("limit", [0, 201, True, "100"])
def test_service_enforces_its_volume_contract_independently(privacy_case, limit):
    from web.services.privacy_export import export_personal_data
    with Session(get_engine()) as db:
        with pytest.raises(ValueError, match="page size"):
            export_personal_data(db, privacy_case[1]["member"], limit=limit)


def test_many_large_plans_obey_byte_budget_and_all_pages_preserve_every_id(privacy_case, monkeypatch):
    from web.services import privacy_export
    raw = json.dumps({"desayuno": {"alimentos": {"Synthetic " + "x" * 8000: 100}, "kcal_objetivo": 500}})
    with Session(get_engine()) as db:
        db.add_all(PlanGenerado(gym_id=privacy_case[1]["member"], id_cliente="profile-member", plan_json=raw)
                   for _ in range(100))
        db.commit()
        expected = list(db.execute(select(PlanGenerado.id).where(PlanGenerado.gym_id == privacy_case[1]["member"])
                                  .order_by(PlanGenerado.id)).scalars())
    parsed = []
    original = privacy_export._plan_content
    def observed(raw_value, stored_length=None):
        parsed.append(stored_length)
        return original(raw_value, stored_length)
    monkeypatch.setattr(privacy_export, "_plan_content", observed)
    seen, after = [], None
    for page_number in range(20):
        params = {"limit": 200}
        if after is not None:
            params["after_plan"] = after
        response = request_export(privacy_case, **params)
        assert response.status_code == 200
        assert len(response.content) <= privacy_export.MAX_EXPORT_BYTES
        page = response.json()["plans"]
        assert len(json.dumps(page, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) <= privacy_export.MAX_SECTION_BYTES
        seen.extend(item["id"] for item in page["records"])
        if page_number == 0:
            assert len(parsed) < 100 and 1 < len(page["records"]) < 100
        after = page["next_after"]
        if after is None:
            break
    assert seen == expected and len(seen) == 101
    assert page_number > 0


def test_sql_projection_never_fetches_oversized_legacy_plan_body(privacy_case, monkeypatch):
    from web.services import privacy_export
    raw = " " * (privacy_export.MAX_PLAN_JSON_CHARS + 1)
    with Session(get_engine()) as db:
        db.execute(select(PlanGenerado).where(PlanGenerado.gym_id == privacy_case[1]["member"])).scalar_one().plan_json = raw
        db.commit()
    captured = []
    original = privacy_export._plan_content
    def observed(raw_value, stored_length=None):
        captured.append((raw_value, stored_length))
        return original(raw_value, stored_length)
    monkeypatch.setattr(privacy_export, "_plan_content", observed)
    response = request_export(privacy_case)
    assert response.status_code == 200
    assert captured == [(None, len(raw))]


def test_single_plan_over_byte_budget_is_explicit_manual_review_not_partial_food_list(privacy_case):
    from web.services.privacy_export import MAX_SECTION_BYTES
    raw = json.dumps({"desayuno": {"alimentos": {"Synthetic " + "x" * MAX_SECTION_BYTES: 100}}})
    with Session(get_engine()) as db:
        db.execute(select(PlanGenerado).where(PlanGenerado.gym_id == privacy_case[1]["member"])).scalar_one().plan_json = raw
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    page = response.json()["plans"]
    assert len(page["records"]) == 1
    assert page["records"][0]["structured_plan"] is None
    assert page["records"][0]["content_status"] == "content_requires_authorized_review"


def test_unbounded_personal_note_returns_explicit_review_error(privacy_case):
    from web.services.privacy_export import MAX_TEXT_CHARS
    with Session(get_engine()) as db:
        db.execute(select(Cliente).where(Cliente.gym_id == privacy_case[1]["member"])).scalar_one().notas = "x" * (MAX_TEXT_CHARS + 1)
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "privacy_record_requires_review"
    assert "xxxxxxx" not in response.text


def test_inconsistent_generation_reference_does_not_expose_foreign_plan_id(privacy_case):
    with Session(get_engine()) as db:
        other_plan = db.execute(select(PlanGenerado).where(PlanGenerado.gym_id == privacy_case[1]["other"])).scalar_one()
        db.execute(select(GenerationReservation).where(GenerationReservation.user_id == privacy_case[1]["member"])).scalar_one().plan_id = other_plan.id
        db.commit()
    response = request_export(privacy_case)
    assert response.status_code == 200
    request = response.json()["generation_requests"]["records"][0]
    assert request["plan_id"] is None
    assert request["result_reference_status"] == "requires_authorized_review"


def test_router_readonly_dependency_does_not_commit_the_request_session(privacy_case):
    commits = []
    def observed(session):
        commits.append(True)
    event.listen(Session, "after_commit", observed)
    try:
        response = request_export(privacy_case)
    finally:
        event.remove(Session, "after_commit", observed)
    assert response.status_code == 200
    assert commits == []
