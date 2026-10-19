"""Independent response contract checks; synthetic persisted authentication only."""
import pytest
from tests.test_personal_history_pagination import history_http


@pytest.mark.parametrize('case', ['success', 'invalid_cursor', 'invalid_limit', 'method'])
def test_private_history_response_keeps_declared_referrer_policy(history_http, case):
    client, _engine, identities = history_http
    headers = identities['history-person']
    path = '/api/usuario/historial'
    if case == 'success':
        response = client.get(path, headers=headers)
        assert response.status_code == 200
    elif case == 'invalid_cursor':
        response = client.get(path, headers=headers, params={'cursor':'malformed'})
        assert response.status_code == 422
    elif case == 'invalid_limit':
        response = client.get(path, headers=headers, params={'limit':0})
        assert response.status_code == 422
    else:
        response = client.post(path, headers=headers)
        assert response.status_code == 405
    assert 'no-store' in response.headers['cache-control'].lower().split(', ')
    assert response.headers['referrer-policy'] == 'no-referrer'
