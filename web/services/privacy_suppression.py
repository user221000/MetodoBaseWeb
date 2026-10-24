"""Authenticated external suppression watermark and quarantined restore.

The registry lives outside the old backup. Every authority/freshness parameter
is supplied by the operator; there is no key, age, generation or allow default.
"""
from datetime import datetime, timedelta
import hashlib
import hmac
import json
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, update
from web.database.models import Base, PrivacyRequest, Usuario, UserRole, RefreshToken, MfaCredential
from web.database.tenant_context import tenant_scope, bind_verified_subject
from web.services.account_security import PENDING
from web.services.account_privacy import bump, prepare_items
from web.services.privacy_disposition import apply_batch
from web.services.privacy_policy import PrivacyPolicy, DELETABLE
from web.services import mfa_service as mfa


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def strict(raw):
    if not isinstance(raw,bytes) or len(raw)>4*1024*1024:
        raise ValueError('Bounded authenticated registry bytes required')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate registry field')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite registry')))


def authenticated_payload(raw,key):
    if not isinstance(key,bytes) or len(key)<32:
        raise ValueError('Independent explicit authentication key required')
    envelope=strict(raw)
    if not isinstance(envelope,dict) or set(envelope)!={'payload','hmac_sha256'}:
        raise ValueError('Closed registry envelope required')
    signature=envelope['hmac_sha256']
    expected=hmac.new(key,canonical(envelope['payload']),hashlib.sha256).hexdigest()
    if not isinstance(signature,str) or not hmac.compare_digest(expected,signature):
        raise ValueError('Registry authentication failed')
    return envelope['payload']


class Suppression(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)
    subject_id:str=Field(min_length=1,max_length=36)
    request_id:str=Field(pattern=r'^[0-9a-f]{32}$')
    minimum_session_version:int=Field(ge=1,le=2147483647)
    closed_at:datetime
    policy_digest:str=Field(pattern=r'^[0-9a-f]{64}$')
    categories:tuple[Literal['personal_diary_days','personal_client_progress'],...]

    @model_validator(mode='after')
    def closed(self):
        if self.closed_at.utcoffset() is None or set(self.categories)!=DELETABLE or len(self.categories)!=len(DELETABLE):
            raise ValueError('Aware closure and unique explicit categories required')
        return self


class SuppressionRegistry(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)
    schema:Literal['metodobase-privacy-suppressions-v1']
    registry_id:str=Field(pattern=r'^[A-Za-z0-9_.:-]{1,64}$')
    generation:int=Field(ge=1)
    issued_at:datetime
    valid_through:datetime
    coverage_through:datetime
    entries:tuple[Suppression,...]=Field(max_length=10000)


def authenticate_registry(raw,key,*,registry_id,minimum_generation,required_as_of,max_age,now):
    now=mfa.instant(now)
    if (type(minimum_generation) is not int or minimum_generation<1 or not isinstance(max_age,timedelta)
            or max_age.total_seconds()<=0 or required_as_of.utcoffset() is None):
        raise ValueError('Explicit external generation/watermark/age authority required')
    value=SuppressionRegistry.model_validate_json(canonical(authenticated_payload(raw,key)))
    times=(value.issued_at,value.valid_through,value.coverage_through)
    if (any(x.utcoffset() is None for x in times) or value.registry_id!=registry_id
            or value.generation<minimum_generation or not value.issued_at<=now<value.valid_through
            or now-value.issued_at>max_age or not required_as_of<=value.coverage_through<=value.issued_at
            or any(row.closed_at>value.coverage_through for row in value.entries)
            or len({row.subject_id for row in value.entries})!=len(value.entries)
            or len({row.request_id for row in value.entries})!=len(value.entries)):
        raise ValueError('Missing, stale, duplicate or mismatched suppression authority')
    return value


def authenticate_policy(raw,key,expected_digest):
    value=PrivacyPolicy.model_validate_json(canonical(authenticated_payload(raw,key)))
    if value.digest()!=expected_digest:
        raise ValueError('Explicit operational policy digest differs')
    return value


def encode_registry(value,key,*,registry_id,minimum_generation,required_as_of,max_age,now):
    """Explicit operator publisher payload; storage/CAS/custody stay external.

    The caller supplies a typed complete registry and external watermark. A
    durable request alone never invents complete coverage of other accounts.
    """
    if not isinstance(value,SuppressionRegistry):
        raise ValueError('A typed external registry is required')
    payload=value.model_dump(mode='json')
    if not isinstance(key,bytes) or len(key)<32:
        raise ValueError('Independent explicit authentication key required')
    raw=canonical({'payload':payload,'hmac_sha256':hmac.new(key,canonical(payload),hashlib.sha256).hexdigest()})
    authenticate_registry(raw,key,registry_id=registry_id,minimum_generation=minimum_generation,
        required_as_of=required_as_of,max_age=max_age,now=now)
    return raw


class IsolationGate(Protocol):
    """Operator implementation must enforce isolation independently of SQL/files."""
    def enter_quarantine(self,destination): ...
    def require_isolated(self,destination): ...
    def record_suppressed(self,receipt): ...


def apply_suppressions(factory,registry,policy_provider,*,now,max_batches,destination_binding):
    from web.services.privacy_restore_binding import require_binding,verify_application_connection
    if type(max_batches) is not int or not 1<=max_batches<=1000:
        raise ValueError('Explicit finite restore disposition budget required')
    receipts=[]
    for entry in registry.entries:
        with tenant_scope(entry.subject_id),factory() as db:
            try:
                require_binding(db.connection(),destination_binding)
                verify_application_connection(db.connection())
                # Restored account rows may predate closure. This is an
                # externally authenticated suppression, never a login proof.
                query=select(Usuario).where(Usuario.id==entry.subject_id).with_for_update(nowait=True)
                user=db.scalar(query.execution_options(populate_existing=True))
                if user is None:
                    receipts.append({'subject_id':entry.subject_id,'state':'absent','request_id':entry.request_id});continue
                if user.role==UserRole.OWNER or user.tipo in {'gym','admin'} or user.team_gym_id:
                    raise ValueError('Restored professional obligations require review')
                bind_verified_subject(db,user.id)
                policy=policy_provider(subject_id=user.id,now=now)
                if not isinstance(policy,PrivacyPolicy) or policy.digest()!=entry.policy_digest:
                    raise ValueError('Suppression policy binding differs')
                decisions=policy.admit(Base.metadata.tables,now=now)
                if any(decisions[name].action!='delete' for name in entry.categories):
                    raise ValueError('Suppression delete policy is not explicit')
                from web.database.mfa_policy import bind_mfa_actor
                bind_mfa_actor(db,user.id)  # Explicit external suppression authorizes only this actor.
                row=db.get(PrivacyRequest,entry.request_id,populate_existing=True)
                if row is not None and (row.subject_id!=user.id or row.policy_digest not in (None,entry.policy_digest)):
                    raise ValueError('Restored request identity differs')
                if row is None:
                    import uuid
                    row=PrivacyRequest(id=entry.request_id,subject_id=user.id,
                        idempotency_key=str(uuid.UUID(hex=entry.request_id)),intent='erase_personal_data',
                        state='requested',reason='external_suppression',created_at=entry.closed_at,updated_at=now)
                    db.add(row);db.flush()
                if row.closed_at is not None and mfa.aware(row.closed_at)!=entry.closed_at:
                    raise ValueError('Restored closure timestamp differs')
                # Load before prepare_items makes the request dirty: an
                # autoflush here must not publish policy without its CAS bump.
                factor=db.get(MfaCredential,user.id,populate_existing=True)
                prepare_items(db,row,policy,now)
                if (type(user.session_version) is not int or not 0<=user.session_version<=mfa.MAX_SV
                        or (user.activo and user.session_version==mfa.MAX_SV)):
                    raise ValueError('Restored session version has no safe capacity')
                user.session_version=max(user.session_version+int(user.activo),entry.minimum_session_version)
                user.activo=False
                user.invitation_token=user.invitation_expires=None
                user.password_reset_hash=user.password_reset_expires_at=user.password_reset_session_version=None
                for name in PENDING:setattr(user,name,None)
                if factor is not None:factor.pending_id=factor.pending_ciphertext=factor.pending_expires_at=None
                row.closed_at=entry.closed_at;row.state='eligible';row.reason='restored_suppression_pending';bump(row,now)
                db.flush()
                db.execute(update(RefreshToken).where(RefreshToken.user_id==user.id).values(revoked=True))
                db.flush();db.commit()
                complete=False
                for _ in range(max_batches):
                    output=apply_batch(db,user.id,row.id,row.version,policy,now=now)
                    db.commit()
                    statuses={item['category']:item['status'] for item in output['items']}
                    if all(statuses[name]=='deleted' for name in entry.categories):complete=True;break
                    if any(statuses[name] not in {'pending','deleted'} for name in entry.categories):break
                if not complete:raise ValueError('Suppression unresolved within the finite restore budget')
                receipts.append({'subject_id':user.id,'request_id':row.id,'state':'suppressed',
                    'minimum_session_version':user.session_version,'categories':list(entry.categories)})
            except BaseException:
                db.rollback();raise
    return receipts


def restore_with_suppressions(manifest,*,gate:IsolationGate,registry_raw,registry_key,
        registry_id,minimum_generation,required_as_of,max_age,now,factory,policy_provider,
        migration_engine,max_batches,restore_options):
    """Actual byte recovery then suppression in isolation; NEVER enables serving.

    Invalid/missing metadata or failures leave quarantine in place. The caller
    must independently authorize activation after this receipt and its own gate.
    """
    from web.services.privacy_restore_binding import (destination,restored_binding,
        require_binding,verify_application_connection,migrate_bound)
    target=destination(restore_options)
    gate.enter_quarantine(target);gate.require_isolated(target)
    if not callable(now):
        raise ValueError('An explicit live restore clock is required')
    registry=authenticate_registry(registry_raw,registry_key,registry_id=registry_id,
        minimum_generation=minimum_generation,required_as_of=required_as_of,max_age=max_age,now=now())
    if migration_engine is None or not callable(factory) or not callable(policy_provider):
        raise ValueError('Explicit isolated migration/session/policy integration required')
    from scripts.backup_restore import restore_backup
    restored=restore_backup(manifest,**restore_options)
    gate.require_isolated(target)
    binding=restored_binding(target,restore_options)
    # Bind the actual Session and migration connection before any application
    # row is read or any migration/disposition can change a database.
    with factory() as db:
        require_binding(db.connection(),binding)
        verify_application_connection(db.connection())
    with migration_engine.connect() as connection:require_binding(connection,binding)
    migrate_bound(migration_engine,binding)
    current=mfa.instant(now())
    authenticate_registry(registry_raw,registry_key,registry_id=registry_id,
        minimum_generation=minimum_generation,required_as_of=required_as_of,max_age=max_age,now=current)
    receipts=apply_suppressions(factory,registry,policy_provider,now=current,max_batches=max_batches,destination_binding=binding)
    gate.require_isolated(target)
    # Reauthenticate all authority after potentially long recovery. A caller
    # supplies a callable clock so an expired record cannot pass with stale now.
    final_now=now()
    authenticate_registry(registry_raw,registry_key,registry_id=registry_id,
        minimum_generation=minimum_generation,required_as_of=required_as_of,max_age=max_age,now=final_now)
    result={'schema':'privacy-suppressed-restore-v1','registry_id':registry.registry_id,
        'registry_generation':registry.generation,'registry_sha256':hashlib.sha256(registry_raw).hexdigest(),
        'destination_binding':binding,
        'byte_recovery':restored,'suppression_receipts':receipts,'quarantine_required':True,
        'access_enabled':False,'integral_erasure_claimed':False}
    gate.record_suppressed(result)
    return result
