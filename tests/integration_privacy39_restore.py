"""Real PG39 backup/suppression: two sequential UUIDs, maximum one active.

This is an isolated database fixture, not evidence of production network
isolation, registry custody/publication, a real provider or permission to serve.
"""
import base64
from datetime import datetime,timedelta
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
import uuid
import pytest
from sqlalchemy import select,text
from sqlalchemy.orm import Session,sessionmaker
from tests.ci_web39.pg_fixtures import database_schema,isolated_database,pg39_runtime  # noqa:F401
from tests.ci_web39.pg_physical import physical_contract
from tests.ci_web39.pg_tools import observe_restore_tools
from tests.account37_qa_restore_helpers import private_backup_temporaries
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from tests.privacy39_pg_actors import (seed_actor,seed_personal_data,enable_factor,policy_at,
    proof,request,close,snapshot)
from scripts.backup_restore import create_backup,verified_artifacts
from web.database.models import (Usuario,RefreshToken,MfaCredential,PersonalDiaryDay,
    ClientProgress,PrivacyRequest,PrivacyDispositionItem,ProductAnalyticsFact)
from web.services import mfa_service as mfa
from web.services.mfa_crypto import totp
from web.services.privacy_policy import DELETABLE
from web.services.privacy_restore_binding import destination,restored_binding
from web.services.privacy_suppression import (SuppressionRegistry,encode_registry,
    apply_suppressions,restore_with_suppressions)


class IsolatedPGTestGate:
    """No HTTP server is started by this fixture. This is not an OS gate proof."""
    def __init__(self,target):self.target=target;self.quarantined=False;self.receipt=None
    def enter_quarantine(self,target):assert target==self.target;self.quarantined=True
    def require_isolated(self,target):assert target==self.target and self.quarantined
    def record_suppressed(self,receipt):
        assert self.quarantined and receipt['access_enabled'] is False
        self.receipt=receipt


class RestoredApplication:
    """Grant the approved synthetic role after --no-acl byte recovery only.

    The untouched application_engine helper grants table access through the
    owned migrator and returns the restricted, tenant-configured app1/0 engine.
    Every subsequent factory call returns a normal Session, with no MFA hook.
    """
    def __init__(self,url,admin):self.url=url;self.admin=admin;self.engine=None
    def __call__(self):
        if self.engine is None:self.engine=application_engine(self.url,self.admin)
        return sessionmaker(bind=self.engine,expire_on_commit=True,autoflush=False)()


def registry_for(entry,policy,now):
    return SuppressionRegistry.model_validate({'schema':'metodobase-privacy-suppressions-v1',
        'registry_id':'synthetic-privacy39-external-log','generation':9,'issued_at':now,
        'valid_through':now+timedelta(hours=1),'coverage_through':now,
        'entries':(entry,)})


def fact_snapshot(engine):
    with Session(engine) as db:
        return [dict(row) for row in db.execute(select(ProductAnalyticsFact.__table__).order_by(ProductAnalyticsFact.id)).mappings()]


def test_pg39_old_active_snapshot_requires_live_suppression_and_physical_binding_before_access(pg39_runtime,tmp_path,monkeypatch):
    from web.services.product_analytics_v2 import origin
    private_backup_temporaries(monkeypatch,tmp_path)
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY',base64.b64encode(b'S'*32).decode())
    registry_key=b'R'*32;now=mfa.instant();policy=policy_at(now)
    pg_bin=Path(pg39_runtime.profile['METODOBASE_TEST_PG_BIN'])
    with pg39_runtime.database(tmp_path/'source-lease') as (source_url,admin):
        run_migration(source_url,'db_bootstrap.py','--revision','20261023_privacy_disposition')
        app=application_engine(source_url,admin)
        try:
            physical_contract(app);database=SimpleNamespace(admin=admin,app=app)
            a,b=(seed_actor(database,monkeypatch) for _ in range(2))
            seed_personal_data(a);seed_personal_data(b)
            seed=enable_factor(a,now);proof(b,now=now)
            for case,label in ((a,'demo'),(b,'customer')):
                with case['factory']() as db:
                    origin(db,case['expected'],'personal',None,value=label,expected_version=0)
            before_a=snapshot(admin,a['user']);before_b=snapshot(admin,b['user'])
            facts=fact_snapshot(admin)
            options={'database_url':source_url,'expected_database':urlsplit(source_url).path.lstrip('/'),'pg_bin':pg_bin}
            source_binding=restored_binding(destination(options),options)
            assert datetime.fromisoformat(source_binding['server_start'])==datetime.fromisoformat(pg39_runtime.contract['generation']['postmaster_start_UTC'])
            with admin.connect() as connection:
                assert source_binding['database_oid']==connection.scalar(text('SELECT oid FROM pg_database WHERE datname=current_database()'))
            # Actual source witness, deliberately wrong OID/start/database, then
            # real restricted Sessions: no row is read or changed before reject.
            provisional={'subject_id':a['user'],'request_id':uuid.uuid4().hex,'minimum_session_version':1,
                'closed_at':now,'policy_digest':policy.digest(),'categories':tuple(sorted(DELETABLE))}
            registry=registry_for(provisional,policy,now)
            for field,bad in (('database_oid',source_binding['database_oid']+1),
                    ('server_start','2000-01-01T00:00:00+00:00'),('database','metodobase_test_account37_'+uuid.uuid4().hex)):
                invalid={**source_binding,field:bad}
                with pytest.raises(ValueError):
                    apply_suppressions(a['factory'],registry,lambda **_:policy,now=now,max_batches=2,destination_binding=invalid)
                assert snapshot(admin,a['user'])==before_a and snapshot(admin,b['user'])==before_b
            with observe_restore_tools(pg39_runtime,source_url,admin,app,'source',tmp_path):
                manifest=create_backup(tmp_path/'encrypted-backup',database_url=source_url,
                    expected_database=options['expected_database'],pg_bin=pg_bin)
            # This durable close happens AFTER the active snapshot was captured.
            row=request(a);now=mfa.instant();token=proof(a,now=now)
            output=close(a,row,policy,token=token,code=totp(seed,int(now.timestamp())//30),now=now)
            assert output['account_closed'] and output['sessions_revoked']
            with Session(admin) as db:
                closed=db.get(PrivacyRequest,row['id']);user=db.get(Usuario,a['user'])
                entry={'subject_id':a['user'],'request_id':row['id'],'minimum_session_version':user.session_version,
                    'closed_at':mfa.aware(closed.closed_at),'policy_digest':closed.policy_digest,
                    'categories':tuple(sorted(DELETABLE))}
            registry=registry_for(entry,policy,now)
            registry_raw=encode_registry(registry,registry_key,registry_id=registry.registry_id,
                minimum_generation=9,required_as_of=now,max_age=timedelta(minutes=5),now=now)
            source_name=options['expected_database'];subject_a=a['user'];subject_b=b['user']
            assert snapshot(admin,subject_b)==before_b
        finally:assert app.pool.checkedout()==admin.pool.checkedout()==0
    assert pg39_runtime.active==0 and pg39_runtime.created==pg39_runtime.closed==1
    with verified_artifacts(manifest) as (metadata,artifacts):
        assert metadata['encryption']=='AES-256-GCM' and metadata['authentication']=='HMAC-SHA256-HKDF-v1'
        assert set(artifacts)=={'postgres'}
    with pg39_runtime.database(tmp_path/'target-lease') as (target_url,admin):
        target_name=urlsplit(target_url).path.lstrip('/');assert target_name!=source_name
        options={'database_url':target_url,'expected_database':target_name,'pg_bin':pg_bin}
        gate=IsolatedPGTestGate(destination(options));factory=RestoredApplication(target_url,admin)
        try:
            with observe_restore_tools(pg39_runtime,target_url,admin,None,'target',tmp_path):
                result=restore_with_suppressions(manifest,gate=gate,registry_raw=registry_raw,registry_key=registry_key,
                    registry_id=registry.registry_id,minimum_generation=9,required_as_of=now,max_age=timedelta(minutes=5),
                    now=mfa.instant,factory=factory,policy_provider=lambda **_:policy,migration_engine=admin,
                    max_batches=2,restore_options=options)
            assert result is gate.receipt and gate.quarantined
            assert result['quarantine_required'] and result['access_enabled'] is False and result['integral_erasure_claimed'] is False
            binding=result['destination_binding'];assert binding['database']==target_name
            assert binding['database_oid']!=source_binding['database_oid']
            assert datetime.fromisoformat(binding['server_start'])==datetime.fromisoformat(pg39_runtime.contract['generation']['postmaster_start_UTC'])
            physical_contract(factory.engine)
            with Session(admin) as db:
                user=db.get(Usuario,subject_a);assert not user.activo and user.session_version>=entry['minimum_session_version']
                factor=db.get(MfaCredential,subject_a)
                assert factor is not None and (factor.pending_id,factor.pending_ciphertext,factor.pending_expires_at)==(None,None,None)
                assert db.scalar(select(RefreshToken.jti).where(RefreshToken.user_id==subject_a,RefreshToken.revoked.is_(False))) is None
                assert db.scalar(select(PersonalDiaryDay.id).where(PersonalDiaryDay.user_id==subject_a)) is None
                assert db.scalar(select(ClientProgress.id).where(ClientProgress.gym_id==subject_a)) is None
                saved=db.get(PrivacyRequest,entry['request_id'])
                assert saved.state=='partially_applied' and saved.closed_at is not None
                items=db.scalars(select(PrivacyDispositionItem).where(PrivacyDispositionItem.request_id==saved.id)).all()
                assert len(items)==9 and {item.category for item in items if item.status=='deleted'}==set(DELETABLE)
            assert snapshot(admin,subject_b)==before_b and fact_snapshot(admin)==facts
            assert result['suppression_receipts'][0]['state']=='suppressed'
        finally:
            if factory.engine is not None:assert factory.engine.pool.checkedout()==0
            assert admin.pool.checkedout()==0
    assert pg39_runtime.active==0 and pg39_runtime.created==pg39_runtime.closed==2
