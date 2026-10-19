"""Independent integration controls; actual factories, HTTP auth and migrated32.

Only inherited offline delivery and explicitly named uncertain ACK seam are
doubles. No product source, historical assertion or auth dependency is changed.
"""
from datetime import timedelta
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.test_personal_progress_http import (
    progress_db, progress_http, accepted, command, grant, shared_path,
)


def private(response):
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_missing_authority_never_turns_ssr_into_api_access(progress_http):
    c = progress_http
    for path in (
        "/api/usuario/progreso/contexto",
        "/api/usuario/progreso/consentimientos",
        "/api/usuario/progreso/completados",
        "/api/clientes/" + c["client"] + "/progreso",
    ):
        response = c["client_http"].get(path)
        assert response.status_code == 401
        private(response)


def test_explicit_profile_and_future_measurement_have_no_hidden_write(progress_http):
    c = progress_http
    client = c["client_http"]
    context = client.get("/api/usuario/progreso/contexto", headers=c["headers"]["person"])
    assert context.status_code == 200
    assert context.json()["profiles"]["items"][0]["id"] == c["profile"]
    key = str(uuid.uuid4())
    path = "/api/usuario/progreso/mediciones/" + key
    response = client.put(path, headers=c["headers"]["person"],
                          json=command(c, measured_on=(c["today"] + timedelta(days=1)).isoformat()))
    assert response.status_code == 422
    private(response)
    assert client.get(path, headers=c["headers"]["person"]).status_code == 404
    assert client.get(path, headers=c["headers"]["other"]).status_code == 404


def test_expired_persisted_subscription_removes_shared_and_native_reads(progress_http):
    from web.database.models import Subscription
    from web.services.personal_diary_service import _clock
    c = progress_http
    link = accepted(c)
    result, _ = grant(c, link)
    assert result.status_code == 200
    path = shared_path(c, link, result.json()["consent"])
    assert c["client_http"].get(path, headers=c["headers"]["gym"]).status_code == 200
    with Session(c["admin"]) as db:
        subscription = db.scalar(select(Subscription).where(Subscription.gym_id == c["gym"]))
        subscription.current_period_end = _clock(None) - timedelta(seconds=1)
        db.commit()
    for target in (path, "/api/clientes/" + c["client"] + "/progreso"):
        response = c["client_http"].get(target, headers=c["headers"]["gym"])
        assert response.status_code in (403, 409)
        private(response)
        assert "measurements" not in response.json()


def test_professional_query_cannot_broaden_categories_or_date_scope(progress_http):
    c = progress_http
    link = accepted(c)
    key = str(uuid.uuid4())
    saved = c["client_http"].put("/api/usuario/progreso/mediciones/" + key,
        headers=c["headers"]["person"], json=command(c))
    assert saved.status_code == 200
    result, _ = grant(c, link, categories={"weight": False, "body_fat": True, "lean_mass": False, "completion": False},
                      through_date=c["today"].isoformat(), ongoing=False)
    assert result.status_code == 200
    path = shared_path(c, link, result.json()["consent"])
    response = c["client_http"].get(path, headers=c["headers"]["gym"])
    assert response.status_code == 200
    assert response.json()["measurements"]["items"][0]["values"] == {"grasa_corporal_pct": 21.0}
    assert "peso_kg" not in response.text
    assert response.json()["completion"] is None
    outside = path.replace("from=" + c["today"].isoformat(), "from=" + (c["today"] - timedelta(days=1)).isoformat())
    denied = c["client_http"].get(outside, headers=c["headers"]["gym"])
    assert denied.status_code in (403, 409, 422)
    private(denied)


def test_withdrawal_commit_ack_loss_has_real_readback_and_no_revival(progress_http, monkeypatch):
    from web.database import engine as database
    c = progress_http
    link = accepted(c)
    result, _ = grant(c, link)
    assert result.status_code == 200
    consent = result.json()["consent"]
    real = Session.commit
    lost = False
    class LoseOnce(Session):
        def commit(self):
            nonlocal lost
            real(self)
            if self.info.get("progress_commit_attempted") and not lost:
                lost = True
                raise RuntimeError("QA_PRIVATE_LOST_ACK")
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=c["engine"], class_=LoseOnce, expire_on_commit=True))
    target = "/api/usuario/vinculos/" + link + "/progreso/consentimiento"
    response = c["client_http"].post(target + "/retirar", headers=c["headers"]["person"],
        json={"expected_consent_id": consent["id"], "expected_version": consent["version"]})
    assert lost and response.status_code == 503
    assert response.json()["detail"]["code"] == "progress_unconfirmed"
    private(response)
    state = c["client_http"].get(target, headers=c["headers"]["person"])
    assert state.status_code == 200
    assert state.json()["consent"]["event"] == "withdraw"
    assert state.json()["consent"]["version"] == consent["version"] + 1
    denied = c["client_http"].get(shared_path(c, link, consent), headers=c["headers"]["gym"])
    assert denied.status_code == 409


def test_eighth_export_cursor_is_lowercase_only_and_does_not_authorize_other_actor(progress_http):
    c = progress_http
    link = accepted(c)
    result, _ = grant(c, link)
    assert result.status_code == 200
    consent = result.json()["consent"]
    base = "/api/usuario/privacidad/exportar?limit=1"
    response = c["client_http"].get(base, headers=c["headers"]["person"])
    assert response.status_code == 200
    records = response.json()["progress_consents"]["records"]
    assert [row["id"] for row in records] == [consent["id"]]
    assert set(records[0]) == {"id", "link_id", "version", "event", "protocol", "link_version", "source_profile_id", "categories", "from_date", "through_date", "ongoing", "created_at"}
    other = c["client_http"].get(base + "&after_progress_consent=" + consent["id"], headers=c["headers"]["other"])
    assert other.status_code == 200 and other.json()["progress_consents"]["records"] == []
    invalid = c["client_http"].get(base + "&after_progress_consent=" + consent["id"].upper(), headers=c["headers"]["person"])
    assert invalid.status_code == 422
    private(invalid)
