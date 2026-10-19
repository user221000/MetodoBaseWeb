"""Exact new private paths, method/slash/auth failures and GIS neighbours."""
import pytest
from tests.test_google33_http import google_db,google_http


def test_real_link_and_page_boundaries_have_private_headers_for_all_methods(google_http):
    client=google_http["client"]
    for method,path in [("GET","/api/auth/google/link/start"),("GET","/api/auth/google/link/confirm"),
            ("GET","/api/auth/google/link/unlink"),("POST","/api/auth/google/link/status"),
            ("POST","/api/auth/google/link/start"),("POST","/api/auth/google/link/confirm"),
            ("POST","/api/auth/google/link/unlink"),("GET","/api/auth/google/link/status"),
            ("GET","/api/auth/google/link/status/"),("GET","/cuenta/google"),("GET","/cuenta/google/")]:
        response=client.request(method,path,follow_redirects=False)
        assert response.status_code in (307,401,404,405,422)
        assert response.headers["Cache-Control"]=="no-store" and response.headers["Referrer-Policy"]=="no-referrer"
        policy=response.headers["Content-Security-Policy"]
        assert "unsafe-inline" not in policy and "cdn.jsdelivr.net" not in policy and "default-src 'none'" in policy
        assert ("accounts.google.com/gsi/client" in policy)==path.startswith("/cuenta/google")
    for path in ("/cuenta/google-extra","/api/auth/google/link/status-extra","/api/auth/google/linker","/api/auth/google/links"):
        response=client.get(path)
        assert response.status_code==404 and response.headers["Referrer-Policy"]=="strict-origin-when-cross-origin"


def test_link_dependency_closes_before_response_and_never_reports_uncertain_ack(google_http,monkeypatch):
    from web.routes import google_link
    from sqlalchemy.orm import Session,sessionmaker
    c=google_http
    class CloseFailure(Session):
        def close(self):
            super().close()
            raise RuntimeError("PRIVATE_CLOSE_SENTINEL")
    monkeypatch.setattr(google_link,"SessionLocal",sessionmaker(bind=c["engine"],class_=CloseFailure))
    # Primary authentication retains its normal Session; only the new function
    # dependency fails at close, after it read the authorized metadata.
    response=c["client"].get("/api/auth/google/link/status",headers=c["headers"])
    assert response.status_code==503 and "items" not in response.json() and "PRIVATE_CLOSE_SENTINEL" not in response.text
    assert response.headers["Cache-Control"]=="no-store" and response.headers["Referrer-Policy"]=="no-referrer"
    assert c["engine"].pool.checkedout()==0


@pytest.mark.parametrize("invalidate_unavailable",[False,True])
def test_precleanup_close_discards_only_owned_session_or_exposes_one_bounded_checkout(google_http,monkeypatch,caplog,invalidate_unavailable):
    from web.routes import google_link
    from sqlalchemy.orm import Session,sessionmaker
    c=google_http;held=[];invalidations=[]
    class BeforeClose(Session):
        def close(self):
            held.append(self)
            raise RuntimeError("PRIVATE_CLOSE_BEFORE_RELEASE")
        def invalidate(self):
            invalidations.append(True)
            if invalidate_unavailable:raise RuntimeError("PRIVATE_INVALIDATION_UNAVAILABLE")
            super().invalidate()
    monkeypatch.setattr(google_link,"SessionLocal",sessionmaker(bind=c["engine"],class_=BeforeClose))
    try:
        response=c["client"].get("/api/auth/google/link/status",headers=c["headers"])
        assert response.status_code==503 and "items" not in response.json()
        assert invalidations==[True]
        # Do not hide the compound-unavailable resource behind GC or destroy a
        # shared engine. Exactly this held Session may retain one checkout.
        assert c["engine"].pool.checkedout()==(1 if invalidate_unavailable else 0)
        assert "PRIVATE_CLOSE_BEFORE_RELEASE" not in caplog.text+response.text
        assert "PRIVATE_INVALIDATION_UNAVAILABLE" not in caplog.text+response.text
    finally:
        for db in held:Session.close(db)
    assert c["engine"].pool.checkedout()==0


def test_unconfirmed_publication_rollback_and_preclose_failure_still_discard_owned_session(google_http,monkeypatch,caplog):
    from sqlalchemy import select
    from sqlalchemy.orm import Session,sessionmaker
    from tests.test_google33_http import start
    from web.database.models import AuthExternalIdentity,GoogleLinkIntent,Usuario
    from web.routes import google_link
    c=google_http;issued=start(c);assert issued.status_code==200
    held=[]
    class Unavailable(Session):
        def commit(self):
            if any(isinstance(row,AuthExternalIdentity) for row in self.new):
                self.info["compound_cleanup_fault"]=True
                raise RuntimeError("PRIVATE_COMMIT_UNAVAILABLE")
            super().commit()
        def rollback(self):
            if self.info.get("compound_cleanup_fault"):raise RuntimeError("PRIVATE_ROLLBACK_UNAVAILABLE")
            super().rollback()
        def close(self):
            if self.info.get("compound_cleanup_fault"):
                held.append(self);raise RuntimeError("PRIVATE_CLOSE_UNAVAILABLE")
            super().close()
    monkeypatch.setattr(google_link,"SessionLocal",sessionmaker(bind=c["engine"],class_=Unavailable,autoflush=False))
    try:
        response=c["client"].post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True})
        assert response.status_code==503 and response.json()["detail"]["code"]=="google_link_unconfirmed"
        assert c["engine"].pool.checkedout()==0
        with Session(c["admin"]) as db:
            assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c["user"])) is None
            assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==c["user"])) is None
            assert db.get(Usuario,c["user"]).session_version==0
        assert all(value not in caplog.text+response.text for value in ("PRIVATE_COMMIT_UNAVAILABLE","PRIVATE_ROLLBACK_UNAVAILABLE","PRIVATE_CLOSE_UNAVAILABLE"))
    finally:
        for db in held:
            db.info.pop("compound_cleanup_fault",None)
            Session.close(db)


def test_new_google_login_discards_only_its_resolution_session_before_any_pair(google_http,monkeypatch,caplog):
    import uuid
    from sqlalchemy.orm import Session,sessionmaker
    from web.database import engine as database
    from web.services import google_link
    c=google_http;held=[];invalidations=[];actual=google_link.resolve_or_register
    class CloseBefore(Session):
        def close(self):
            if self.info.get('own_google_resolution'):
                held.append(self);raise RuntimeError('PRIVATE_GOOGLE_PRIMARY_CLOSE')
            super().close()
        def invalidate(self):invalidations.append(True);super().invalidate()
    def resolve(db,*args,**kwargs):
        db.info['own_google_resolution']=True
        return actual(db,*args,**kwargs)
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=c['engine'],class_=CloseBefore,expire_on_commit=True,autoflush=False))
    monkeypatch.setattr(google_link,'resolve_or_register',resolve)
    c['google']['sub']=str(uuid.uuid4().int);c['google']['email']=uuid.uuid4().hex+'@thirdparty.example.invalid'
    try:
        response=c['client'].post('/api/auth/google',json={'credential':c['credential']()})
        assert response.status_code==503 and 'token' not in response.json() and 'refresh_token' not in response.json()
        assert invalidations==[True] and c['engine'].pool.checkedout()==0
        assert 'PRIVATE_GOOGLE_PRIMARY_CLOSE' not in caplog.text+response.text
    finally:
        for db in held:Session.close(db)


def test_provider_jwks_read_stops_at_bound_before_library_parse(google_http,monkeypatch):
    import httpx
    from sqlalchemy import func,select
    from sqlalchemy.orm import Session
    from web.database.models import AuthExternalIdentity,Usuario
    c=google_http;read=[];actual=httpx._client.AsyncClient
    class TooLarge(httpx.AsyncByteStream):
        async def __aiter__(self):
            for index in range(3):read.append(index);yield b'x'*70000
    def transport(request):
        assert str(request.url)=='https://www.googleapis.com/oauth2/v3/certs'
        assert request.method=='GET' and not request.url.query
        return httpx.Response(200,stream=TooLarge())
    def client(*args,**kwargs):
        assert kwargs['follow_redirects'] is False and kwargs['timeout']==10.0
        return actual(*args,**dict(kwargs,transport=httpx.MockTransport(transport)))
    with Session(c['admin']) as db:
        before=(db.scalar(select(func.count()).select_from(Usuario)),db.scalar(select(func.count()).select_from(AuthExternalIdentity)))
    monkeypatch.setattr(httpx,'AsyncClient',client)
    response=c['client'].post('/api/auth/google',json={'credential':c['credential']()})
    assert response.status_code==401 and response.json()['detail']['code']=='google_identity_invalid'
    assert read==[0,1] and 'token' not in response.json()
    with Session(c['admin']) as db:
        assert (db.scalar(select(func.count()).select_from(Usuario)),db.scalar(select(func.count()).select_from(AuthExternalIdentity)))==before
