"""A logout acknowledgement follows durable revocation in both real adapters."""

import importlib

import pytest


@pytest.mark.parametrize('factory', ['web.main_web', 'api.app'])
@pytest.mark.parametrize('failure', [None, 'before_commit', 'after_commit'])
def test_logout_confirmation_tracks_commit_and_revokes_old_sessions(factory, failure, test_gym_user, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import RefreshToken, Usuario

    app = importlib.import_module(factory).create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        pairs = [auth.crear_token_pair(test_gym_user) for _ in range(2)]
        headers = {'Authorization': 'Bearer ' + pairs[0]['access_token']}

        class UncertainSession(Session):
            def commit(self):
                if failure == 'after_commit':
                    super().commit()
                raise RuntimeError('Synthetic logout commit failure')

        with monkeypatch.context() as patch:
            if failure:
                patch.setattr(auth, '_get_session', lambda: UncertainSession(get_engine()))
            response = client.post('/api/auth/logout', headers=headers)
        durable = failure != 'before_commit'
        with Session(get_engine()) as db:
            assert db.get(Usuario, test_gym_user['id']).session_version == (1 if durable else 0)
            rows = db.query(RefreshToken).filter(RefreshToken.user_id == test_gym_user['id']).all()
            assert len(rows) == 2 and all(row.revoked is durable for row in rows)
        assert client.get('/api/auth/me', headers=headers).status_code == (401 if durable else 200)
        for pair in pairs:
            refreshed = client.post('/api/auth/refresh', json={'refresh_token': pair['refresh_token']})
            assert refreshed.status_code == (401 if durable else 200)
        if failure:
            assert response.status_code >= 500
            assert '"success":true' not in response.text.replace(' ', '').lower()
        else:
            assert response.status_code == 200
            assert response.json().get('success') is True
            assert response.json()['message'] == 'Sesión cerrada. Todas las sesiones revocadas.'
