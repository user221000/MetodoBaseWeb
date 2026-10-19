"""Reuse revocation follows the account -> refresh order needed by recovery."""
from sqlalchemy import event
from sqlalchemy.orm import Session


def test_refresh_reuse_locks_account_before_revoking_refresh():
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole,RefreshToken
    auth.init_auth()
    engine=get_engine()
    with Session(engine) as db:
        user=Usuario(id='reuse-order',email='reuse-order@example.invalid',nombre='Synthetic',tipo='usuario',
            role=UserRole.VIEWER,password_hash=auth.hash_password('SyntheticPassword123'),activo=True)
        db.add(user); db.commit()
        principal=auth.identity_from_user(user,db)
    old=auth.crear_token_pair(principal)['refresh_token']
    assert auth.rotar_refresh_token(old)
    groups,current=[],[]
    def sql(connection,cursor,statement,parameters,context,executemany):
        normalized=statement.lower().strip()
        if normalized.startswith('update refresh_tokens'): current.append('refresh')
        elif normalized.startswith('update usuarios'): current.append('account')
    def commit(connection):
        if current:
            groups.append(current.copy()); current.clear()
    event.listen(engine,'before_cursor_execute',sql); event.listen(engine,'commit',commit)
    try:
        assert auth.rotar_refresh_token(old) is None
    finally:
        event.remove(engine,'before_cursor_execute',sql); event.remove(engine,'commit',commit)
    with Session(engine) as db:
        assert db.get(Usuario,'reuse-order').session_version==1
        assert db.query(RefreshToken).filter_by(user_id='reuse-order',revoked=False).count()==0
    assert groups[0]==['refresh']
    assert groups[1][0]=='account',groups
