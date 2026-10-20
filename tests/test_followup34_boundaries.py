"""Private error boundaries and durable failure witnesses on both factories."""
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.nutrition35_fixtures import followup_db, followup_http, create, candidate
from web.database.models import FollowupTask, FollowupTaskEvent


def test_strict_stream_duplicate_keys_utf8_bools_and_body_limit(followup_http):
    c=followup_http;raw=c["raw"];headers={"Content-Type":"application/json","Idempotency-Key":str(uuid.uuid4())}
    for payload in (b'{"client_id":"a","client_id":"b"}',b'{"x":"\xff"}',b'{"x":NaN}',b'[]'):
        response=raw.post("/api/seguimiento/tareas",content=payload,headers=headers)
        assert response.status_code==422 and response.json()["detail"]["code"]=="followup_invalid_input"
    over=raw.post("/api/seguimiento/tareas",content=b' '*8193,headers=headers)
    assert over.status_code==413 and over.json()["detail"]["code"]=="followup_body_limit"
    evidence=candidate(c)
    invalid=raw.post("/api/seguimiento/tareas",json={"client_id":c["profile"],"cause":"no_saved_plan",
        "cause_evidence_hash":evidence["cause_evidence_hash"],"next_step":"review_plan_history","assignee_id":None,
        "expected_active_task_id":None,"confirm":1},headers=headers)
    assert invalid.status_code==422
    with Session(c["admin"]) as db:
        assert db.scalar(select(FollowupTask.id).where(FollowupTask.gym_id==c["user"])) is None


def test_validation_methods_redirect_errors_and_adjacent_paths_remain_separate(followup_http):
    raw=followup_http["raw"]
    responses=[raw.get("/api/seguimiento/tareas/INVALID"),raw.get("/api/seguimiento/tareas?limit=101"),
        raw.get("/api/seguimiento/metricas?from=0&through=2026-10-19"),raw.post("/api/seguimiento/contexto"),
        raw.get("/api/seguimiento/contexto/",follow_redirects=False)]
    assert [r.status_code for r in responses]==[422,422,422,405,307]
    for response in responses:
        assert response.headers["Cache-Control"]=="no-store"
        assert response.headers["Referrer-Policy"]=="no-referrer"
        assert "accounts.google.com" not in response.headers["Content-Security-Policy"]
    for path in ("/api/seguimiento/contextox","/api/seguimiento/tareas-extra","/seguimiento-extra"):
        response=raw.get(path)
        assert response.status_code==404 and response.headers["Referrer-Policy"]=="strict-origin-when-cross-origin"


@pytest.mark.parametrize("committed",[False,True])
def test_commit_failure_never_publishes_ack_and_explicit_replay_is_one_operation(followup_http,monkeypatch,committed):
    c=followup_http;real=Session.commit;injected=[]
    def broken(db):
        if any(isinstance(row,FollowupTaskEvent) for row in db.identity_map.values()):
            injected.append(True)
            if committed:real(db)
            raise RuntimeError("Synthetic commit ACK unavailable")
        return real(db)
    monkeypatch.setattr(Session,"commit",broken)
    response,body,key=create(c)
    assert injected==[True] and response.status_code==503 and "ack" not in response.json()
    assert response.json()["detail"]["code"]=="followup_unconfirmed"
    monkeypatch.setattr(Session,"commit",real)
    with Session(c["admin"]) as db:
        events=db.scalars(select(FollowupTaskEvent).where(FollowupTaskEvent.gym_id==c["user"])).all()
        assert len(events)==int(committed)
    replay=c["raw"].post("/api/seguimiento/tareas",json=body,headers={"Idempotency-Key":key})
    assert replay.status_code==200 and replay.json()["operation"]["replayed"] is committed
    with Session(c["admin"]) as db:
        assert len(db.scalars(select(FollowupTaskEvent).where(FollowupTaskEvent.gym_id==c["user"])).all())==1


@pytest.mark.parametrize("after_close",[False,True])
def test_owned_session_cleanup_failure_is_visible_before_headers(followup_http,monkeypatch,after_close):
    from web.services import followup_tasks as service
    original=service.context;attempts=[]
    def instrument(db,*args,**kwargs):
        result=original(db,*args,**kwargs)
        actual=db.close;invalidate=db.invalidate
        def broken():
            if after_close:actual()
            raise RuntimeError("Synthetic own close error")
        def invalidated():
            attempts.append("invalidate")
            return invalidate()
        db.close=broken;db.invalidate=invalidated
        return result
    monkeypatch.setattr(service,"context",instrument)
    response=followup_http["raw"].get("/api/seguimiento/contexto")
    assert response.status_code==503 and attempts==["invalidate"]
    assert "capabilities" not in response.json() and response.headers["Referrer-Policy"]=="no-referrer"


def test_generic_outer_500_is_opaque_and_private(followup_http,monkeypatch):
    from web.services import followup_tasks as service
    # An invalid exception payload makes the adapter's error serialization fail,
    # reaching the existing outer generic handler; never a raw SQL/provider error.
    def encoding_failure(*args,**kwargs):raise HTTPException(400,object())
    monkeypatch.setattr(service,"context",encoding_failure)
    response=followup_http["raw"].get("/api/seguimiento/contexto")
    assert response.status_code==500
    assert response.headers["Cache-Control"]=="no-store" and response.headers["Referrer-Policy"]=="no-referrer"
    assert "TypeError" not in response.text and "object at" not in response.text


def test_no_auth_is_private_without_broadening_primary_login_page(followup_http):
    raw=followup_http["raw"];saved=raw.headers.pop("Authorization")
    try:
        response=raw.get("/api/seguimiento/tareas")
        assert response.status_code==401 and response.headers["Referrer-Policy"]=="no-referrer"
        assert response.headers["Cache-Control"]=="no-store"
        login=raw.get("/login")
        assert "accounts.google.com" in login.headers["Content-Security-Policy"]
    finally:raw.headers["Authorization"]=saved


def test_early_local_bucket_429_is_private_before_route_execution(followup_http):
    from web.middleware.rate_limiter import RateLimiterMiddleware, RateLimiterStore
    raw=followup_http["raw"];layer=raw.app.middleware_stack
    while not isinstance(layer,RateLimiterMiddleware):
        layer=layer.app
    old,enabled=layer.store,layer.enabled
    layer.store=RateLimiterStore(requests_per_minute=1,burst_size=1)
    layer.enabled=True  # isolation deliberately disables all global limiters
    try:
        assert raw.get("/api/seguimiento/contexto").status_code==200
        denied=raw.get("/api/seguimiento/contexto")
        assert denied.status_code==429
        assert denied.headers["Cache-Control"]=="no-store" and denied.headers["Referrer-Policy"]=="no-referrer"
        assert "accounts.google.com" not in denied.headers["Content-Security-Policy"]
    finally:layer.store,layer.enabled=old,enabled


def test_read_failure_is_visible_unavailable_never_successful_zero_metrics(followup_http,monkeypatch):
    from web.database import followup_task_repository as repository
    def unavailable(*args,**kwargs):raise RuntimeError("Synthetic read failure")
    monkeypatch.setattr(repository,"counters",unavailable)
    response=followup_http["raw"].get("/api/seguimiento/metricas")
    assert response.status_code==503 and response.json()["detail"]["code"]=="followup_unavailable"
    assert "state_now" not in response.json() and "event_period" not in response.json()
    assert response.headers["Referrer-Policy"]=="no-referrer"
