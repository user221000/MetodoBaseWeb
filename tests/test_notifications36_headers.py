"""Private exact route shapes on normal, validation and outside-handler failures."""
from tests.notifications36_http import followup_db as followup_db,notification_http as notification_http


def check(response):
    assert response.headers["Cache-Control"]=="no-store"
    assert response.headers["Referrer-Policy"]=="no-referrer"
    assert response.headers["X-Content-Type-Options"]=="nosniff"
    csp=response.headers["Content-Security-Policy"]
    assert "accounts.google.com" not in csp and "cdn.jsdelivr.net" not in csp
    assert "default-src 'none'" in csp and "unsafe-inline" not in csp


def test_validation_methods_redirects_and_adjacent_paths(notification_http):
    raw=notification_http["raw"]
    for path in ("/api/notificaciones/contexto","/api/notificaciones/preferencias/unknown",
            "/api/notificaciones/outbox/invalid/cancelar","/notificaciones/excluir"):
        for suffix in ("","/","//"):
            for method in ("GET","HEAD","PATCH","OPTIONS"):
                check(raw.request(method,path+suffix,follow_redirects=False))
    for path in ("/api/notificaciones/contextox","/api/notificaciones/preferencias/unknown/extra","/notificaciones/excluirx"):
        response=raw.get(path)
        assert response.status_code==404
        assert response.headers["Referrer-Policy"]=="strict-origin-when-cross-origin"


def test_oversized_dynamic_identifier_remains_private_validation(notification_http):
    response=notification_http["raw"].post("/api/notificaciones/outbox/"+"a"*129+"/cancelar",json={})
    assert response.status_code==422
    check(response)


def test_external_failure_uses_factory_opaque500_and_private_headers(notification_http,monkeypatch):
    from web.routes.notifications import router
    c=notification_http
    route=next(row for row in c["raw"].app.routes if getattr(row,"original_router",None) is router)
    async def external_failure(scope,receive,send):
        raise RuntimeError("PRIVATE_NOTIFICATION_EXCEPTION_SENTINEL")
    monkeypatch.setattr(route,"handle",external_failure)
    response=c["raw"].get("/api/notificaciones/contexto",params={"context":"gym"})
    assert response.status_code==500
    assert "PRIVATE_NOTIFICATION_EXCEPTION_SENTINEL" not in response.text
    check(response)


def test_internal_http500_detail_is_opaque_and_private(notification_http,monkeypatch):
    from fastapi import HTTPException
    from web.services import notifications
    def failure(*args,**kwargs):
        raise HTTPException(500,"PRIVATE_NOTIFICATION_HTTP500_SENTINEL")
    monkeypatch.setattr(notifications,"context",failure)
    response=notification_http["raw"].get("/api/notificaciones/contexto",params={"context":"gym"})
    assert response.status_code==500
    assert "PRIVATE_NOTIFICATION_HTTP500_SENTINEL" not in response.text
    check(response)
