"""Independent configuration roots and real SDK transport, without provider I/O."""
import importlib

import pytest

from web.storage.configuration import ObjectStoreConfiguration, build_object_store


def _clear_proxies(monkeypatch):
    for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
                 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'REQUEST_METHOD'):
        monkeypatch.delenv(name, raising=False)


def _s3_configuration(endpoint='https://objects.example.invalid'):
    return ObjectStoreConfiguration(backend='s3', bucket='synthetic-composition-review',
        region='us-east-1', endpoint=endpoint, access_key='synthetic-explicit-access',
        secret_key='synthetic-explicit-secret')


def test_explicit_s3_uses_system_tls_trust_despite_inherited_ca_bundle(monkeypatch, tmp_path):
    _clear_proxies(monkeypatch)
    monkeypatch.setenv('AWS_CA_BUNDLE', str(tmp_path / 'synthetic-untrusted-ca.pem'))
    store = build_object_store(_s3_configuration())
    try:
        # Inspect the effective transport used by the pinned real SDK, rather
        # than asserting how this application spells its constructor call.
        assert store.client._endpoint.http_session._verify is True
    finally:
        store.client.close()


@pytest.mark.parametrize('variable,endpoint', [
    ('HTTPS_PROXY', 'https://objects.example.invalid'),
    ('HTTP_PROXY', 'http://127.0.0.1:9'),
    ('ALL_PROXY', 'https://objects.example.invalid'),
])
def test_explicit_s3_never_selects_an_inherited_transport_proxy(monkeypatch, variable, endpoint):
    _clear_proxies(monkeypatch)
    monkeypatch.setenv(variable, 'http://synthetic-untrusted-proxy.example.invalid:9')
    store = build_object_store(_s3_configuration(endpoint))
    try:
        actual_proxy = store.client._endpoint.http_session._proxy_config.proxy_url_for(endpoint)
        assert actual_proxy is None
    finally:
        store.client.close()


@pytest.mark.parametrize('factory', ['web.main_web', 'api.app'])
@pytest.mark.parametrize('backend', ['local', 's3'])
def test_real_factories_compose_the_explicit_destination_without_provider_io(factory, backend, monkeypatch, tmp_path):
    from botocore.client import BaseClient
    from config.settings import get_settings
    from web.storage.local import LocalObjectStore
    from web.storage.objects import describe
    from web.storage.runtime import _configured_store, get_object_store
    from web.storage.s3 import S3ObjectStore

    settings = get_settings()
    values = dict(OBJECT_STORAGE_BACKEND=backend,
        OBJECT_STORAGE_LOCAL_ROOT=str(tmp_path / 'private-volume') if backend == 'local' else '',
        OBJECT_STORAGE_S3_BUCKET='synthetic-composition-review' if backend == 's3' else '',
        OBJECT_STORAGE_S3_REGION='us-east-1' if backend == 's3' else '',
        OBJECT_STORAGE_S3_ENDPOINT='https://objects.example.invalid' if backend == 's3' else '',
        OBJECT_STORAGE_S3_ACCESS_KEY='synthetic-explicit-access' if backend == 's3' else '',
        OBJECT_STORAGE_S3_SECRET_KEY='synthetic-explicit-secret' if backend == 's3' else '',
        OBJECT_STORAGE_S3_SESSION_TOKEN='')
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(BaseClient, '_make_api_call', lambda *args, **kwargs: pytest.fail('Composition must not invoke a provider API'))
    _configured_store.cache_clear()
    store = None
    try:
        app = importlib.import_module(factory).create_app()
        store = app.state.private_object_store
        assert store is get_object_store()
        if backend == 'local':
            assert isinstance(store, LocalObjectStore)
            assert store.root == (tmp_path / 'private-volume').resolve()
            content = b'%PDF-1.4\nSynthetic composed local destination\n%%EOF'
            descriptor = describe('synthetic-composition-owner', 'plan_pdf', content, 'application/pdf')
            store.put(descriptor, content, owner_id=descriptor.owner_id)
            assert LocalObjectStore(store.root).read(descriptor, owner_id=descriptor.owner_id) == content
        else:
            assert isinstance(store, S3ObjectStore)
            assert store.bucket == 'synthetic-composition-review'
            assert store.client.meta.endpoint_url == 'https://objects.example.invalid'
            credentials = store.client._request_signer._credentials.get_frozen_credentials()
            assert credentials.access_key == 'synthetic-explicit-access'
            assert credentials.secret_key == 'synthetic-explicit-secret' and credentials.token is None
            assert not list(tmp_path.iterdir())
    finally:
        if isinstance(store, S3ObjectStore):
            store.client.close()
        _configured_store.cache_clear()
