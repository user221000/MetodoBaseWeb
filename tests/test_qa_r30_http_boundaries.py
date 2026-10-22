"""Independent current37 API/SaaS privacy and opaque-error controls."""
import re

import pytest
from fastapi import HTTPException

from tests import product_analytics_fixtures as fixtures
from web.services import product_analytics as service

account37_engine = fixtures.account37_engine
followup_db = fixtures.followup_db
analytics_http = fixtures.analytics_http
PATH = '/api/analytics/producto'


def private(response):
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert response.headers['x-content-type-options'] == 'nosniff'
    policy = response.headers['content-security-policy']
    assert re.fullmatch("default-src 'none'; script-src 'self' 'nonce-[A-Za-z0-9_-]+'; "
        "style-src 'self'; connect-src 'self'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; object-src 'none'", policy)


@pytest.mark.parametrize('fault', ['runtime', 'http500', 'http503'])
def test_exact_paths_redact_reader_failure_status_headers_and_logs(analytics_http, monkeypatch, caplog, fault):
    calls = []

    def failed(*_args, **_kwargs):
        calls.append(True)
        if fault == 'runtime':
            raise RuntimeError('PRIVATE_QA_R30_READER_DETAIL')
        raise HTTPException(500 if fault == 'http500' else 503,
            {'private': 'PRIVATE_QA_R30_READER_DETAIL'}, headers={'X-Private-Probe': 'PRIVATE_QA_R30_READER_DETAIL'})

    monkeypatch.setattr(service, '_preparation', failed)
    for path in (PATH, PATH + '/'):
        response = analytics_http['raw'].get(path, params={'context': 'gym'})
        assert response.status_code == 503 and response.json()['detail']['code'] == 'analytics_unavailable'
        assert 'PRIVATE_QA_R30_READER_DETAIL' not in response.text + str(response.headers) + caplog.text
        assert 'x-private-probe' not in response.headers
        private(response)
    assert calls == [True, True]
    assert analytics_http['engine'].pool.checkedout() == 0


def test_unauthenticated_exact_paths_are_private_but_neighbours_keep_gis(analytics_http):
    raw = analytics_http['raw']
    raw.headers.pop('Authorization')
    for path in (PATH, PATH + '/'):
        response = raw.get(path, params={'context': 'personal'})
        assert response.status_code == 401 and response.headers['www-authenticate'] == 'Bearer'
        private(response)
        private(raw.head(path))
    for path in (PATH + 'x', PATH + '/x', '/login'):
        response = raw.get(path)
        assert response.headers['referrer-policy'] == 'strict-origin-when-cross-origin'
        assert 'https://accounts.google.com' in response.headers['content-security-policy']
