"""Synthetic39 PG actors. Production Sessions have no test MFA prebinding."""
import base64
from datetime import date,timedelta
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session,sessionmaker
from web.database.models import (Usuario,UserRole,RefreshToken,MfaAuthorization,MfaCredential,
    Cliente,ClientProgress,PersonalDiaryDay,PrivacyRequest,PrivacyDispositionItem,ProductAnalyticsFact)
from web.services import mfa_service as mfa

PASSWORD='Synthetic account security password 42!'


def seed_actor(database,monkeypatch,*,professional=False):
    from web.auth import crear_token_pair,hash_password,identity_from_user
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(),'RESEND_API_KEY','synthetic-privacy39-no-network')
    monkeypatch.setattr(get_settings(),'MFA_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'Q'*32).decode())
    subject=str(uuid.uuid4())
    with Session(database.admin) as db:
        user=Usuario(id=subject,email=subject+'@example.invalid',password_hash=hash_password(PASSWORD),
            nombre='Synthetic39',tipo='gym' if professional else 'usuario',
            role=UserRole.OWNER if professional else UserRole.VIEWER)
        db.add(user);db.flush();expected=identity_from_user(user,db)
        pair=crear_token_pair(expected,db=db);db.commit()
    factory=sessionmaker(bind=database.app,expire_on_commit=True,autoflush=False)
    return {'factory':factory,'engine':database.app,'admin':database.admin,'expected':expected,
        'user':subject,'access':pair['access_token'],'refresh':pair['refresh_token']}


def proof(case,*,now=None):
    with case['factory']() as db:
        return mfa.reauthenticate(db,case['expected'],case['access'],password=PASSWORD,now=now)['reauthentication_token']


def enable_factor(case,now,*,pending=True):
    from web.services.mfa_crypto import encrypt
    from web.settings import get_settings
    proof(case,now=now)  # Genuine service creates the credential with its own actor binding.
    seed=b'F'*20
    with Session(case['admin']) as db:
        factor=db.get(MfaCredential,case['user']);assert factor is not None
        factor.generation=1;factor.enabled_at=now
        key=base64.urlsafe_b64decode(get_settings().MFA_ENCRYPTION_KEY)
        factor.secret_ciphertext=encrypt(seed,key,mfa._aad(factor,1,'active'))
        if pending:
            factor.pending_id=uuid.uuid4().hex;factor.pending_expires_at=now+timedelta(minutes=5)
            factor.pending_ciphertext=encrypt(b'N'*20,key,mfa._aad(factor,2,'pending:'+factor.pending_id))
        db.commit()
    return seed


def seed_personal_data(case):
    client=str(uuid.uuid4())
    with Session(case['admin']) as db:
        db.add(Cliente(id_cliente=client,gym_id=case['user'],nombre='Synthetic own39'));db.flush()
        db.add(PersonalDiaryDay(user_id=case['user'],local_date=date(2026,10,23),meals_json='{}'))
        db.add(ClientProgress(gym_id=case['user'],id_cliente=client));db.commit()
    return client


def policy_at(now):
    from web.services.privacy_policy import PrivacyPolicy,INVENTORY,DELETABLE
    return PrivacyPolicy.model_validate({'policy_id':'synthetic-privacy39-no-legal-authority','version':1,
        'valid_from':now-timedelta(minutes=5),'valid_through':now+timedelta(hours=1),
        'catalogue_tables':tuple(sorted({name for group in INVENTORY.values() for name in group})),
        'decisions':tuple({'category':category,'action':'delete' if category in DELETABLE else 'block',
            'basis_id':'synthetic-test-only'} for category in INVENTORY),
        'external_holds_reviewed':True,'hold_codes':()})


def request(case):
    from web.services.account_privacy import create_request
    return create_request(case['expected'],str(uuid.uuid4()),factory=case['factory'])


def close(case,row,policy,*,token=None,code=None,now=None):
    from web.services.account_privacy import close_account
    return close_account(case['expected'],case['access'],row['id'],row['version'],
        token if token is not None else proof(case,now=now),code=code,now=now,
        factory=case['factory'],policy_provider=lambda **_:policy)


def snapshot(engine,subject):
    """Trusted admin oracle only; no proof of production context is inferred."""
    predicates=(
        (Usuario,Usuario.id),(RefreshToken,RefreshToken.user_id),(MfaAuthorization,MfaAuthorization.user_id),
        (MfaCredential,MfaCredential.user_id),(Cliente,Cliente.gym_id),(ClientProgress,ClientProgress.gym_id),
        (PersonalDiaryDay,PersonalDiaryDay.user_id),(PrivacyRequest,PrivacyRequest.subject_id),
        (PrivacyDispositionItem,PrivacyDispositionItem.subject_id),(ProductAnalyticsFact,ProductAnalyticsFact.owner_id),
    )
    with Session(engine) as db:
        return {model.__table__.name:sorted([dict(row) for row in db.execute(select(model.__table__).where(column==subject)).mappings()],
            key=lambda row:repr(sorted(row.items()))) for model,column in predicates}
