"""Disable-only capability remains independent of unrelated HTTP credentials."""
from urllib.parse import parse_qs,urlsplit
import uuid

from sqlalchemy import select,func
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db,notification_http
from tests.followup34_http import PASSWORD
from tests.test_notifications36_worker import prepared,Port,origin
from web.services import notification_worker as worker
from web.database.models import Usuario,NotificationPreference


def emitted(case,monkeypatch):
    identifier=prepared(case,monkeypatch);port=Port()
    worker.run_one(case["user"],"gym",identifier,origin(),port,factory=case["factory"])
    return parse_qs(urlsplit(port.messages[0].exclusion_url).fragment)["token"][0]


def latest(case,subject):
    with Session(case["admin"]) as db:
        row=db.scalar(select(NotificationPreference).where(NotificationPreference.user_id==subject).order_by(NotificationPreference.version.desc()))
        return None if row is None else (row.id,row.version,row.enabled)


def test_foreign_real_login_does_not_select_or_disable_its_own_preference(notification_http,monkeypatch):
    c=notification_http;token=emitted(c,monkeypatch)
    with Session(c["admin"]) as db:email=db.get(Usuario,c["member"]).email
    signed=c["raw"].post("/api/auth/login",json={"email":email,"password":PASSWORD})
    assert signed.status_code==200
    c["raw"].headers["Authorization"]="Bearer "+signed.json()["token"]
    me=c["raw"].get("/api/auth/me")
    assert me.status_code==200 and me.json()["id"]==c["member"]
    enabled=c["raw"].put("/api/notificaciones/preferencias/account_period_end",params={"context":"personal"},
        json={"expected_version":0,"enabled":True,"confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    assert enabled.status_code==200
    own=latest(c,c["member"])
    excluded=c["raw"].post("/api/notificaciones/excluir",json={"token":token})
    assert excluded.status_code==200 and excluded.json()=={"success":True}
    assert latest(c,c["user"])[2] is False and latest(c,c["member"])==own
    assert c["user"] not in excluded.text and c["member"] not in excluded.text


def test_missing_malformed_and_unknown_capability_leave_no_rows(notification_http):
    c=notification_http
    for header in (None,"Bearer malformed"):
        if header is None:c["raw"].headers.pop("Authorization",None)
        else:c["raw"].headers["Authorization"]=header
        response=c["raw"].post("/api/notificaciones/excluir",json={"token":"A"*43})
        assert response.status_code==200 and response.json()=={"success":True}
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id==c["user"]))==0


def test_contact_roundtrip_permanently_invalidates_old_exclusion(notification_http,monkeypatch):
    c=notification_http;token=emitted(c,monkeypatch)
    before=latest(c,c["user"])
    with Session(c["admin"]) as db:
        user=db.get(Usuario,c["user"]);original=user.email
        user.email="temporary-"+uuid.uuid4().hex+"@example.invalid";db.commit()
        user.email=original;db.commit()
    response=c["raw"].post("/api/notificaciones/excluir",json={"token":token})
    assert response.status_code==200 and response.json()=={"success":True}
    assert latest(c,c["user"])==before
