"""Independent recovery state additions to the immutable diary27 restore case."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit

import pytest

OLD = 'RestoreOldPassword123!'
NEW = 'RestoreNewPassword456!'
RESET_FIELDS = ('password_reset_hash', 'password_reset_expires_at', 'password_reset_session_version')


def populate_recovery28(source_url, admin, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import Session, sessionmaker
    from tests.integration_provider_subjects import application_engine
    from web import auth
    from web.database import engine as database
    from web.database.models import Usuario, RefreshToken
    from web.services.password_recovery import issue_request, consume, digest

    subjects = ['restore-release-gym', 'restore-foreign-gym', 'restore-personal-user', 'restore-professional-member']
    app = application_engine(source_url, admin)
    instant = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
    tokens, pairs, revoked_jtis = {}, {}, []
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(database, '_engine', app)
            scoped.setattr(database, '_SessionLocal', sessionmaker(bind=app, autoflush=False))
            auth.init_auth()
            with Session(app) as db:
                for subject in subjects:
                    row = db.get(Usuario, subject)
                    row.password_hash = auth.hash_password(OLD)
                db.commit()
            for subject in subjects:
                with Session(app) as db:
                    identity = auth.identity_from_user(db.get(Usuario, subject), db)
                pairs[subject] = [auth.crear_token_pair(identity) for _ in range(2)]
                messages = []
                issue_request(identity['email'], 'https://restore.example.invalid', now=instant,
                              factory=sessionmaker(bind=app), sender=lambda *args: messages.append(args) or True)
                assert len(messages) == 1
                parsed = urlsplit(messages[0][2])
                assert parsed.query == ''
                tokens[subject] = parse_qs(parsed.fragment)['token'][0]
                assert len(tokens[subject]) == 43
            with Session(app) as db:
                consume(db, tokens['restore-personal-user'], NEW, now=instant + timedelta(seconds=1))
            auth.revocar_refresh_tokens_usuario('restore-professional-member')
            with Session(admin) as db:
                expected = {}
                for subject in subjects:
                    row = db.get(Usuario, subject)
                    completed = subject == 'restore-personal-user'
                    revoked = completed or subject == 'restore-professional-member'
                    assert row.session_version == int(revoked)
                    assert auth.verify_password(NEW if completed else OLD, row.password_hash)
                    values = tuple(getattr(row, field) for field in RESET_FIELDS)
                    if completed:
                        assert values == (None, None, None)
                    else:
                        assert values == (digest(tokens[subject]),
                                          (instant + timedelta(minutes=30)).astimezone(timezone.utc).replace(tzinfo=None), 0)
                        assert tokens[subject] != values[0] and len(values[0]) == 64
                    rows = list(db.scalars(select(RefreshToken).where(RefreshToken.user_id == subject)))
                    assert len(rows) == 2 and all(row.revoked is revoked for row in rows)
                    if revoked:
                        revoked_jtis.extend(row.jti for row in rows)
                    expected[subject] = {'state': values, 'session_version': row.session_version,
                        'authority': (row.email, row.nombre, row.apellido, row.tipo, row.role.value, row.team_gym_id, row.activo),
                        'revoked': revoked, 'password_changed': completed, 'refresh_jtis': sorted(row.jti for row in rows)}
    finally:
        app.dispose()
    assert len(set(revoked_jtis)) == 4
    return {'tokens': tokens, 'pairs': pairs, 'expected': expected, 'revoked_jtis': sorted(revoked_jtis)}


def reject_plain_recovery_material(rows, expected):
    material = json.dumps(rows, default=str)
    assert all(token not in material for token in expected['tokens'].values())


def exact_after_existing_startup_cleanup(backup_rows, expected):
    """Predict only the four seeded revoked IDs, using no observed target rows."""
    ids = set(expected['revoked_jtis'])
    assert len(ids) == 4
    rows = backup_rows['refresh_tokens']
    assert len(rows) == 8
    assert {row['jti'] for row in rows if row['revoked']} == ids
    assert all(row['expires_at'] > time.time() + 60 for row in rows)
    result = deepcopy(backup_rows)
    result['refresh_tokens'] = [row for row in rows if row['jti'] not in ids]
    assert len(result['refresh_tokens']) == 4
    return result


def verify_restored_recovery28_material(admin, app, expected):
    """Inspect complete restored material before any factory can clean tokens."""
    from sqlalchemy import select, text, update
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session
    from web import auth
    from web.database.models import Usuario, RefreshToken, AuthAuditLog
    with Session(admin) as db:
        for subject, state in expected['expected'].items():
            row = db.get(Usuario, subject)
            assert tuple(getattr(row, field) for field in RESET_FIELDS) == state['state']
            assert row.session_version == state['session_version']
            assert (row.email, row.nombre, row.apellido, row.tipo, row.role.value, row.team_gym_id, row.activo) == state['authority']
            assert auth.verify_password(NEW if state['password_changed'] else OLD, row.password_hash)
            rows = list(db.scalars(select(RefreshToken).where(RefreshToken.user_id == subject)))
            assert len(rows) == 2 and all(row.revoked is state['revoked'] for row in rows)
        assert db.query(AuthAuditLog).filter_by(event_type='password_reset_complete').count() == 1
        material = json.dumps([dict(row) for row in db.execute(select(Usuario.__table__)).mappings()], default=str)
        assert all(token not in material for token in expected['tokens'].values())
    constraint_codes = []
    with Session(app) as db:
        for values in [
            {'password_reset_expires_at': None}, {'password_reset_hash': 'f' * 63},
            {'password_reset_session_version': -1},
        ]:
            with pytest.raises(IntegrityError) as failure:
                db.execute(update(Usuario).where(Usuario.id == 'restore-release-gym').values(**values))
                db.commit()
            assert failure.value.orig.pgcode == '23514'
            constraint_codes.append(failure.value.orig.pgcode)
            db.rollback()
        with pytest.raises(IntegrityError) as failure:
            db.execute(update(Usuario).where(Usuario.id == 'restore-foreign-gym').values(
                password_reset_hash=expected['expected']['restore-release-gym']['state'][0]))
            db.commit()
        assert failure.value.orig.pgcode == '23505'
        constraint_codes.append(failure.value.orig.pgcode)
        db.rollback()
        for zone in ('UTC', 'America/Mexico_City'):
            db.execute(text("SELECT set_config('TimeZone',:zone,false)"), {'zone': zone})
            db.commit()
            row = db.get(Usuario, 'restore-release-gym')
            assert row.password_reset_expires_at == expected['expected']['restore-release-gym']['state'][1]
    return {'constraint_sqlstates': constraint_codes, 'utc_zones': ['UTC', 'America/Mexico_City'],
            'restored_refresh_rows_before_factory': 8, 'restored_revoked_rows_before_factory': 4,
            'all_reset_states_persisted_exactly': True, 'plain_bearer_absent_in_restored_accounts': True}


def verify_restored_recovery28(admin, app, expected, monkeypatch):
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
        actual = {row.jti for row in db.scalars(select(RefreshToken))}
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
