"""CURRENT31 copy scopes the unchanged recovery28 witnesses to their subjects.

Only the initial refresh SELECT adds that explicit predicate. New MFA actors
and their full physical rows remain in the independent complete snapshot.
No original helper, prior assertion, schema target or expected state changes.
"""
import importlib
import time
from tests.recovery28_restore_helpers import NEW, OLD, RESET_FIELDS


def verify_restored_recovery28_current31(admin, app, expected, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import MetaData, select
    from sqlalchemy.orm import Session, sessionmaker
    from web import auth
    from web.database import engine as database
    from web.database.models import Usuario, RefreshToken, AuthAuditLog
    from web.rate_limiter import _buckets, _bucket_windows
    from web.services import email_service

    def projection():
        metadata = MetaData()
        metadata.reflect(bind=admin)
        assert AuthAuditLog.__tablename__ == 'auth_audit_log'
        changed_auth_tables = {'usuarios', 'refresh_tokens', AuthAuditLog.__tablename__}
        assert changed_auth_tables.issubset(metadata.tables)
        with admin.connect() as db:
            return {table.name: [dict(row) for row in db.execute(select(table).order_by(*table.primary_key.columns)).mappings()]
                    for table in metadata.sorted_tables if table.name not in changed_auth_tables}

    unchanged = projection()
    with Session(admin) as db:
        actual = {row.jti for row in db.scalars(select(RefreshToken).where(RefreshToken.user_id.in_(expected['expected'])))}
        alive = {jti for state in expected['expected'].values() if not state['revoked'] for jti in state['refresh_jtis']}
        assert len(actual) == 4 and actual == alive
        assert actual.isdisjoint(expected['revoked_jtis'])
    proofs = []
    with monkeypatch.context() as scoped:
        scoped.setattr(database, '_engine', app)
        scoped.setattr(database, '_SessionLocal', sessionmaker(bind=app, autoflush=False))
        scoped.setattr(email_service, 'send_password_changed', lambda *_: True)
        auth.init_auth()
        for factory, subject in [('web.main_web', 'restore-release-gym'), ('api.app', 'restore-foreign-gym')]:
            for key in list(_buckets):
                if key.startswith('rl:recovery-v1:'):
                    _buckets.pop(key, None)
                    _bucket_windows.pop(key, None)
            application = importlib.import_module(factory).create_app()
            assert not application.dependency_overrides
            with TestClient(application, raise_server_exceptions=False) as client:
                form = client.get('/auth/reset-password')
                assert form.status_code == 200
                assert form.headers['cache-control'] == 'no-store' and form.headers['referrer-policy'] == 'no-referrer'
                assert "script-src 'self'" in form.headers['content-security-policy']
                assert 'https:' not in form.headers['content-security-policy']
                for denied in ('restore-personal-user', 'restore-professional-member'):
                    result = client.post('/api/auth/password-reset/confirm', json={
                        'token': expected['tokens'][denied], 'new_password': NEW, 'confirm_password': NEW})
                    assert result.status_code == 400 and result.json()['detail']['code'] == 'password_reset_unavailable'
                    for pair in expected['pairs'][denied]:
                        assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + pair['access_token']}).status_code == 401
                        assert client.post('/api/auth/refresh', json={'refresh_token': pair['refresh_token']}).status_code == 401
                before = expected['pairs'][subject][0]
                assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + before['access_token']}).status_code == 200
                payload = {'token': expected['tokens'][subject], 'new_password': NEW, 'confirm_password': NEW}
                changed = client.post('/api/auth/password-reset/confirm', json=payload)
                assert changed.status_code == 200 and changed.json()['code'] == 'password_reset_complete'
                assert set(changed.json()) == {'code', 'message'}
                assert changed.headers['cache-control'] == 'no-store' and changed.headers['referrer-policy'] == 'no-referrer'
                assert client.get('/api/auth/me').status_code == 401
                assert set(changed.cookies.keys()).issubset({'_csrf'})
                assert client.post('/api/auth/password-reset/confirm', json=payload).status_code == 400
                for pair in expected['pairs'][subject]:
                    assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + pair['access_token']}).status_code == 401
                    assert client.post('/api/auth/refresh', json={'refresh_token': pair['refresh_token']}).status_code == 401
                email = expected['expected'][subject]['authority'][0]
                assert client.post('/api/auth/login', json={'email': email, 'password': OLD}).status_code == 401
                login = client.post('/api/auth/login', json={'email': email, 'password': NEW})
                assert login.status_code == 200
                assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + login.json()['token']}).status_code == 200
                exported = client.get('/api/usuario/privacidad/exportar', headers={'Authorization': 'Bearer ' + login.json()['token']})
                assert exported.status_code == 200
                assert all(field not in exported.text for field in RESET_FIELDS)
                assert all(token not in form.text + changed.text + exported.text for token in expected['tokens'].values())
                deadline = time.monotonic() + 5
                while application.state.recovery_dispatcher.pending and time.monotonic() < deadline:
                    time.sleep(.01)
                assert application.state.recovery_dispatcher.pending == 0
            with Session(admin) as db:
                row = db.get(Usuario, subject)
                assert row.session_version == 1 and all(getattr(row, field) is None for field in RESET_FIELDS)
                assert auth.verify_password(NEW, row.password_hash)
                assert (row.email, row.nombre, row.apellido, row.tipo, row.role.value, row.team_gym_id, row.activo) == expected['expected'][subject]['authority']
                assert db.query(AuthAuditLog).filter_by(user_id=subject, event_type='password_reset_complete').count() == 1
                assert db.query(RefreshToken).filter_by(user_id=subject, revoked=True).count() >= 2
            proofs.append({'factory': factory, 'restored_pending_bearer_consumed_once': True,
                           'old_access_refresh_rejected': True, 'normal_new_password_login': True, 'no_autologin': True})
    assert projection() == unchanged
    with Session(admin) as db:
        for subject in ('restore-personal-user', 'restore-professional-member'):
            row = db.get(Usuario, subject)
            assert tuple(getattr(row, field) for field in RESET_FIELDS) == expected['expected'][subject]['state']
            assert row.session_version == 1
    return {'pending_subjects': 2, 'prebackup_consumed_subjects': 1, 'prebackup_stale_sv_subjects': 1,
            'exact_seeded_revoked_ids_cleaned_by_existing_factory': 4,
            'remaining_live_refresh_before_reset': 4, 'business_projection_unchanged': True, 'http': proofs}
