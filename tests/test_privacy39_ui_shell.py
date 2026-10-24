"""Actual inert HTTP shells on both factories; no provider or browser claim."""
import importlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from tests.privacy39_fixtures import database_schema,isolated_database,privacy39_engine  # noqa:F401


@pytest.mark.parametrize('factory',['api.app','web.main_web'])
@pytest.mark.parametrize('path',['/cuenta/seguridad','/mi-seguridad'])
@pytest.mark.parametrize('privacy_only',[False,True])
def test_same_security_shell_selects_one_GIS_owner_with_private_headers(factory,path,privacy_only,monkeypatch,privacy39_engine):
    from web.database import engine as database
    from web.settings import get_settings
    # The inert shell still constructs a real app and must pass its genuine39
    # schema guard. Bind the migrated fixture rather than the empty suite DB.
    monkeypatch.setattr(database,'_engine',privacy39_engine)
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=privacy39_engine,expire_on_commit=True,autoflush=False))
    monkeypatch.setenv('GOOGLE_CLIENT_ID','synthetic-privacy39-google-client')
    monkeypatch.setattr(get_settings(),'GOOGLE_CLIENT_ID','synthetic-privacy39-google-client')
    with TestClient(importlib.import_module(factory).create_app(),raise_server_exceptions=False) as client:
        response=client.get(path,params={'operacion':'privacidad'} if privacy_only else None)
    assert response.status_code==200
    assert response.headers['Cache-Control']=='no-store' and response.headers['Referrer-Policy']=='no-referrer'
    assert response.headers['X-Content-Type-Options']=='nosniff'
    csp=response.headers['Content-Security-Policy']
    assert "default-src 'none'" in csp and 'unsafe-inline' not in csp
    assert 'accounts.google.com/gsi/client' in csp and 'cdn.jsdelivr.net' not in csp
    assert 'data-account-privacy39' in response.text and 'account-privacy39.js' in response.text
    assert ('data-account-security37' in response.text) is (not privacy_only)
    assert ('account-security37.js' in response.text) is (not privacy_only)
    if privacy_only:
        assert 'data-google-client-id="synthetic-privacy39-google-client"' in response.text
        assert '<h1 id="privacy39-title">' in response.text
    else:
        assert '?operacion=privacidad' in response.text
        assert 'data-account-privacy39 data-login-url=' in response.text
    assert 'reauthentication_token' not in response.text  # No raw proof input in either view.
