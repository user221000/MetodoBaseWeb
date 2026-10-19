"""Current email identity semantics and limiter mismatch, without providers."""
import asyncio

from sqlalchemy.orm import Session
from starlette.requests import Request


def test_existing_distinct_email_accounts_keep_distinct_rate_buckets(monkeypatch):
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole
    from web.middleware.rate_limiter import rate_limit_dependency
    from web.rate_limiter_redis import _sensitive_path
    from web import rate_limiter_redis
    import web.middleware.rate_limiter as limits
    from web.main_web import create_app
    create_app()
    names=['straße@example.invalid','strasse@example.invalid']
    with Session(get_engine()) as db:
        for index,email in enumerate(names):
            db.add(Usuario(id='normalization-'+str(index),email=email,nombre='Synthetic',tipo='usuario',
                role=UserRole.VIEWER,activo=True,password_hash='synthetic'))
        db.commit()
        assert db.query(Usuario).filter(Usuario.email.in_(names)).count()==2
    observed=[]
    async def capture(key,*args,**kwargs):
        observed.append(key)
        return True,{'retry_after':0},'synthetic'
    monkeypatch.setattr(rate_limiter_redis,'check_rate_limit',capture)
    monkeypatch.setattr(limits,'RATE_LIMIT_ENABLED',True)
    dependency=rate_limit_dependency(5,900,account_field='email')
    import json
    for email in names:
        body=json.dumps({'email':email}).encode()
        async def receive():
            return {'type':'http.request','body':body,'more_body':False}
        request=Request({'type':'http','method':'POST','path':'/api/auth/login',
            'headers':[],'client':('127.0.0.1',1234),'server':('test',80),'scheme':'http'},receive)
        asyncio.run(dependency(request))
    account_keys=[key for key in observed if ':account:' in key]
    assert len(account_keys)==2 and account_keys[0]!=account_keys[1]
    assert names[0].strip().lower()!=names[1].strip().lower()
    assert _sensitive_path('/api/auth/password-reset/request')
    assert _sensitive_path('/api/auth/password-reset/confirm')
