"""Independent precommit constraint failures retain admission and atomic state."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.test_google33_http import google_db, google_http  # noqa: F401
from tests.test_google33_http import test_commit_uncertainty_never_returns_proof_or_session  # noqa: F401
from tests.test_security_google33_peer import issue


@pytest.mark.parametrize('rollback_uncertain', [False, True])
def test_confirm_precommit_constraint_rolls_back_all_mutations_or_reports_uncertainty(
    google_http, monkeypatch, rollback_uncertain,
):
    from web.database.models import (
        AuthAuditLog, AuthExternalIdentity, GoogleLinkIntent,
        MfaCredential, RefreshToken, Usuario,
    )
    from web.services import google_link

    c = google_http
    prepared = issue(c)
    assert prepared.status_code == 200
    original_revoke = google_link.mfa._revoke_sessions
    original_rollback = Session.rollback
    observed = []
    with Session(c['admin']) as db:
        initial_refresh = {row.jti: row.revoked for row in db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == c['user']))}
        initial_version = db.get(Usuario, c['user']).session_version

    def constraint_after_real_mutation(db, user):
        original_revoke(db, user)
        db.flush()
        observed.append(True)
        db.info['independent_confirm_constraint'] = True
        raise IntegrityError('independent synthetic constraint', None, Exception('synthetic'))

    def rollback(db):
        if rollback_uncertain and db.info.get('independent_confirm_constraint'):
            raise RuntimeError('PRIVATE_CONFIRM_ROLLBACK_UNAVAILABLE')
        return original_rollback(db)

    monkeypatch.setattr(google_link.mfa, '_revoke_sessions', constraint_after_real_mutation)
    monkeypatch.setattr(Session, 'rollback', rollback)
    reply = c['client'].post('/api/auth/google/link/confirm', headers=c['headers'],
        json={'intent': prepared.json()['intent'], 'confirm': True})
    assert reply.status_code == (503 if rollback_uncertain else 409)
    assert reply.json()['detail']['code'] == (
        'google_link_unconfirmed' if rollback_uncertain else 'google_link_conflict')
    assert not {'token', 'refresh_token', 'challenge', 'intent'} & reply.json().keys()
    assert 'PRIVATE_CONFIRM' not in reply.text and 'synthetic' not in reply.text
    assert reply.headers['Cache-Control'] == 'no-store'
    assert reply.headers['Referrer-Policy'] == 'no-referrer'
    assert "default-src 'none'" in reply.headers['Content-Security-Policy']
    assert 'accounts.google.com' not in reply.headers['Content-Security-Policy']
    assert observed == [True]
    with Session(c['admin']) as db:
        assert db.get(Usuario, c['user']).session_version == initial_version
        intent = db.scalar(select(GoogleLinkIntent).where(GoogleLinkIntent.user_id == c['user']))
        assert intent.consumed_at is None
        assert db.scalar(select(func.count()).select_from(AuthExternalIdentity).where(
            AuthExternalIdentity.user_id == c['user'])) == 0
        assert db.scalar(select(func.count()).select_from(AuthAuditLog).where(
            AuthAuditLog.user_id == c['user'], AuthAuditLog.event_type == 'google_identity_linked')) == 0
        assert {row.jti: row.revoked for row in db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == c['user']))} == initial_refresh
        assert db.get(MfaCredential, c['user']).attempts['google_link:confirm']['count'] == 1
    assert c['engine'].pool.checkedout() == 0
