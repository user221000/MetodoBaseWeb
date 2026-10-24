"""Actual encrypted SQLite byte recovery plus external suppression; no serving."""
import base64
from datetime import date,timedelta
from pathlib import Path
import uuid
import pytest
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session,sessionmaker
from tests.privacy39_fixtures import (privacy39_engine,account37_engine,account37,database_schema,isolated_database)
from tests.account37_qa_restore_helpers import private_backup_temporaries
from tests.test_privacy39_policy import registry_bytes
from tests.test_privacy39_transactions import policy_for_now
from web.database.models import Cliente,ClientProgress,PersonalDiaryDay,Usuario,PrivacyRequest
from web.database.schema_control import verify_runtime_schema
from web.services import mfa_service as mfa
from web.services.privacy_policy import DELETABLE
from web.services.privacy_suppression import restore_with_suppressions


class IsolatedSQLiteTestGate:
    """Synthetic fixture has no server. This is not an OS/network isolation proof."""
    def __init__(self,destination):self.destination=destination;self.quarantined=False;self.receipt=None
    def enter_quarantine(self,destination):
        assert destination['sqlite_path']==self.destination.as_posix();self.quarantined=True
    def require_isolated(self,destination):
        assert self.quarantined and destination['sqlite_path']==self.destination.as_posix()
    def record_suppressed(self,receipt):assert receipt['access_enabled'] is False;self.receipt=receipt


def test_old_snapshot_cannot_reactivate_closed_subject_and_owned_data_is_suppressed(account37,tmp_path,monkeypatch):
    private_backup_temporaries(monkeypatch,tmp_path)
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY',base64.b64encode(b'S'*32).decode())
    case=account37;client=str(uuid.uuid4())
    with case['factory']() as db:
        db.add(Cliente(id_cliente=client,gym_id=case['user'],nombre='Synthetic restore personal'));db.flush()
        db.add(PersonalDiaryDay(user_id=case['user'],local_date=date(2026,10,23),meals_json='{}'))
        db.add(ClientProgress(gym_id=case['user'],id_cliente=client));db.commit()
    from scripts.backup_restore import create_backup
    source=Path(case['engine'].url.database).resolve()
    manifest=create_backup(tmp_path/'backup',sqlite_sources=(source,))
    current=mfa.instant();policy=policy_for_now()
    request_id=uuid.uuid4().hex
    entry={'subject_id':case['user'],'request_id':request_id,'minimum_session_version':1,
        'closed_at':current.isoformat(),'policy_digest':policy.digest(),'categories':sorted(DELETABLE)}
    raw=registry_bytes(issued_at=current.isoformat(),coverage_through=current.isoformat(),
        valid_through=(current+timedelta(hours=1)).isoformat(),entries=[entry])
    destination=(tmp_path/'restored.db').resolve();target=create_engine('sqlite:///'+destination.as_posix())
    gate=IsolatedSQLiteTestGate(destination)
    try:
        result=restore_with_suppressions(manifest,gate=gate,registry_raw=raw,registry_key=b'R'*32,
            registry_id='synthetic-external-log',minimum_generation=7,required_as_of=current,
            max_age=timedelta(minutes=5),now=lambda:current,factory=sessionmaker(bind=target),
            policy_provider=lambda **_:policy,migration_engine=target,max_batches=2,
            restore_options={'sqlite_destination':destination})
        assert result['access_enabled'] is False and result['quarantine_required'] and gate.receipt is result
        with Session(target) as db:
            user=db.get(Usuario,case['user']);assert not user.activo and user.session_version>=1
            assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==user.id)) is None
            assert db.scalar(select(ClientProgress.id).where(ClientProgress.gym_id==user.id)) is None
            assert db.get(PrivacyRequest,request_id).state=='partially_applied'
        with case['factory']() as db:
            assert db.get(Usuario,case['user']).activo  # Original snapshot source was not mutated.
    finally:target.dispose()


def _suppression_subject_state(db,subject):
    from web.database.models import MfaCredential,PrivacyDispositionItem,RefreshToken
    user=db.get(Usuario,subject);factor=db.get(MfaCredential,subject)
    requests=db.scalars(select(PrivacyRequest).where(PrivacyRequest.subject_id==subject).order_by(PrivacyRequest.id)).all()
    items=db.scalars(select(PrivacyDispositionItem).where(PrivacyDispositionItem.subject_id==subject).order_by(PrivacyDispositionItem.id)).all()
    return {
        'user':(user.activo,user.session_version),
        'factor':None if factor is None else (factor.generation,factor.pending_id,factor.pending_ciphertext,factor.pending_expires_at),
        'requests':[tuple(getattr(row,column.name) for column in PrivacyRequest.__table__.columns) for row in requests],
        'items':[tuple(getattr(row,column.name) for column in PrivacyDispositionItem.__table__.columns) for row in items],
        'refresh':[tuple(row) for row in db.execute(select(RefreshToken.jti,RefreshToken.revoked).where(RefreshToken.user_id==subject).order_by(RefreshToken.jti))],
        'diary':list(db.scalars(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==subject).order_by(PersonalDiaryDay.id))),
        'progress':list(db.scalars(select(ClientProgress.id).where(ClientProgress.gym_id==subject).order_by(ClientProgress.id))),
    }


@pytest.mark.parametrize('autoflush',[True,False],ids=['autoflush-on','autoflush-off'])
@pytest.mark.parametrize('reject_commit',[False,True],ids=['commit','rollback'])
def test_suppression_existing_request_full_cas_pending_and_foreign_state_are_atomic(account37,autoflush,reject_commit):
    from web.database.models import MfaCredential,RefreshToken,UserRole
    from web.auth import crear_token_pair,identity_from_user
    from web.services import account_privacy
    from web.services.privacy_restore_binding import destination,restored_binding
    from web.services.privacy_suppression import authenticate_registry,apply_suppressions
    case=account37;current=mfa.instant();policy=policy_for_now();foreign=str(uuid.uuid4())
    request=account_privacy.create_request(case['expected'],str(uuid.uuid4()),factory=case['factory'],now=current)
    with case['factory']() as db:
        foreign_user=Usuario(id=foreign,email=foreign+'@example.invalid',password_hash='synthetic-no-login',nombre='Foreign sentinel',tipo='usuario',role=UserRole.VIEWER)
        db.add(foreign_user);db.flush()
        crear_token_pair(identity_from_user(foreign_user,db),db=db)
        for subject in (case['user'],foreign):
            factor=db.get(MfaCredential,subject)
            if factor is None:
                factor=MfaCredential(user_id=subject,factor_id=uuid.uuid4().hex,generation=0,last_counter=-1);db.add(factor)
            factor.pending_id=uuid.uuid4().hex;factor.pending_ciphertext='synthetic-opaque-pending'
            factor.pending_expires_at=current+timedelta(minutes=5)
            client=str(uuid.uuid4());db.add(Cliente(id_cliente=client,gym_id=subject,nombre='Synthetic CAS sentinel'));db.flush()
            db.add(PersonalDiaryDay(user_id=subject,local_date=date(2026,10,23),meals_json='{}'))
            db.add(ClientProgress(gym_id=subject,id_cliente=client))
        db.commit()
        before=_suppression_subject_state(db,case['user']);foreign_before=_suppression_subject_state(db,foreign)
    entry={'subject_id':case['user'],'request_id':request['id'],'minimum_session_version':1,
        'closed_at':current.isoformat(),'policy_digest':policy.digest(),'categories':sorted(DELETABLE)}
    raw=registry_bytes(issued_at=current.isoformat(),coverage_through=current.isoformat(),
        valid_through=(current+timedelta(hours=1)).isoformat(),entries=[entry])
    registry=authenticate_registry(raw,b'R'*32,registry_id='synthetic-external-log',minimum_generation=7,
        required_as_of=current,max_age=timedelta(minutes=5),now=current)
    options={'sqlite_destination':Path(case['engine'].url.database).resolve()}
    binding=restored_binding(destination(options),options)
    class CommitGateSession(Session):
        def commit(self):
            if reject_commit:raise RuntimeError('synthetic-suppression-commit-rejected')
            return super().commit()
    factory=sessionmaker(bind=case['engine'],class_=CommitGateSession,autoflush=autoflush)
    arguments={'now':current,'max_batches':2,'destination_binding':binding}
    if reject_commit:
        with pytest.raises(RuntimeError,match='synthetic-suppression-commit-rejected'):
            apply_suppressions(factory,registry,lambda **_:policy,**arguments)
    else:
        receipts=apply_suppressions(factory,registry,lambda **_:policy,**arguments)
        assert receipts==[{'subject_id':case['user'],'request_id':request['id'],'state':'suppressed',
            'minimum_session_version':1,'categories':sorted(DELETABLE)}]
        assert apply_suppressions(factory,registry,lambda **_:policy,**arguments)==receipts
    with case['factory']() as db:
        assert _suppression_subject_state(db,foreign)==foreign_before
        if reject_commit:
            assert _suppression_subject_state(db,case['user'])==before
        else:
            user=db.get(Usuario,case['user']);factor=db.get(MfaCredential,user.id)
            assert not user.activo and user.session_version==1
            assert factor.pending_id is None and factor.pending_ciphertext is None and factor.pending_expires_at is None
            assert not db.scalars(select(RefreshToken).where(RefreshToken.user_id==user.id,RefreshToken.revoked.is_(False))).all()
            assert not db.scalars(select(PersonalDiaryDay).where(PersonalDiaryDay.user_id==user.id)).all()
            assert not db.scalars(select(ClientProgress).where(ClientProgress.gym_id==user.id)).all()
            row=db.get(PrivacyRequest,request['id'])
            assert row.policy_digest==policy.digest() and row.closed_at is not None and row.version>request['version']
            assert row.state=='partially_applied'


@pytest.mark.parametrize('raw',[b'',b'{}',registry_bytes()])
def test_absent_invalid_or_stale_external_registry_keeps_quarantine_before_byte_restore(tmp_path,raw):
    current=mfa.instant();destination=(tmp_path/'must-not-restore.db').resolve()
    gate=IsolatedSQLiteTestGate(destination)
    with pytest.raises(ValueError):
        restore_with_suppressions(tmp_path/'not-read.json',gate=gate,registry_raw=raw,registry_key=b'R'*32,
            registry_id='synthetic-external-log',minimum_generation=7,required_as_of=current,
            max_age=timedelta(minutes=5),now=lambda:current,factory=lambda:None,policy_provider=lambda **_:None,
            migration_engine=None,max_batches=1,restore_options={'sqlite_destination':destination})
    assert gate.quarantined and not destination.exists() and gate.receipt is None


@pytest.mark.parametrize('misbound',['application','migration'])
def test_effective_A_B_destination_mismatch_keeps_B_byteexact_and_quarantines_A(account37,tmp_path,monkeypatch,misbound):
    import hashlib
    private_backup_temporaries(monkeypatch,tmp_path)
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY',base64.b64encode(b'S'*32).decode())
    case=account37
    from scripts.backup_restore import create_backup
    source=Path(case['engine'].url.database).resolve()
    manifest=create_backup(tmp_path/'backup-mismatch',sqlite_sources=(source,))
    current=mfa.instant();policy=policy_for_now()
    entry={'subject_id':case['user'],'request_id':uuid.uuid4().hex,'minimum_session_version':1,
        'closed_at':current.isoformat(),'policy_digest':policy.digest(),'categories':sorted(DELETABLE)}
    raw=registry_bytes(issued_at=current.isoformat(),coverage_through=current.isoformat(),
        valid_through=(current+timedelta(hours=1)).isoformat(),entries=[entry])
    target_path=(tmp_path/'restored-A.db').resolve();target=create_engine('sqlite:///'+target_path.as_posix())
    gate=IsolatedSQLiteTestGate(target_path)
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        with pytest.raises(ValueError):
            restore_with_suppressions(manifest,gate=gate,registry_raw=raw,registry_key=b'R'*32,
                registry_id='synthetic-external-log',minimum_generation=7,required_as_of=current,
                max_age=timedelta(minutes=5),now=lambda:current,
                factory=case['factory'] if misbound=='application' else sessionmaker(bind=target),
                policy_provider=lambda **_:policy,migration_engine=case['engine'] if misbound=='migration' else target,
                max_batches=2,restore_options={'sqlite_destination':target_path})
        assert gate.quarantined and gate.receipt is None
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before
        with case['factory']() as db:
            user=db.get(Usuario,case['user']);assert user.activo and user.session_version==0
            assert db.get(PrivacyRequest,entry['request_id']) is None
    finally:target.dispose()
