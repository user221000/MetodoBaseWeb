"""Independent boundary/fault tests; real primary/factors, no identity override."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from fastapi import HTTPException
from tests.test_progress_retirement_http import progress_db,progress_http,retired_scope,query,enrollment,withdrawal,snapshot,METADATA


def invoke(c, data):
    from web.progress_retirement_schemas import Metadata
    from web.routes.progress_retirement import _execute
    return _execute(Metadata.model_validate(data),'metadata')


def test_close_raises_before_cleanup_after_confirmed_operation(retired_scope,monkeypatch,caplog):
    from web.database import engine as database
    from web.database.tenant_context import current_tenant
    c=retired_scope;held=[]
    class BeforeClose(Session):
        def close(self):
            if self.info.pop('retirement_commit_attempted',False):
                held.append(self)
                raise RuntimeError('PRIVATE_CLOSE_BEFORE_RELEASE')
            super().close()
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=c['engine'],class_=BeforeClose,expire_on_commit=True))
    outer=current_tenant.set(c['other'])
    try:
        with pytest.raises(HTTPException) as error:invoke(c,query(c))
        assert error.value.status_code==503
        assert current_tenant.get()==c['other']
        assert c['engine'].pool.checkedout()==0
        assert 'PRIVATE_CLOSE_BEFORE_RELEASE' not in caplog.text
    finally:
        current_tenant.reset(outer)
        for session in held:Session.close(session)


def test_admission_ack_loss_is_durable_and_does_not_consume_factor(retired_scope,monkeypatch):
    from web.database import engine as database
    from web.database.models import AuthAuditLog
    c=retired_scope;_,codes=enrollment(c)
    class AdmissionAckLost(Session):
        def commit(self):
            admission=any(getattr(row,'event_type',None)=='progress_retirement_attempt' for row in self.new)
            super().commit()
            if admission:raise RuntimeError('PRIVATE_ADMISSION_ACK_LOST')
    with monkeypatch.context() as seam:
        seam.setattr(database,'_SessionLocal',sessionmaker(bind=c['engine'],class_=AdmissionAckLost,expire_on_commit=True))
        result=c['client_http'].post(METADATA,json=query(c,factor={'recovery_code':codes[0]}))
    assert result.status_code==503 and 'items' not in result.json()
    with Session(c['admin']) as db:
        count=db.scalar(select(func.count()).select_from(AuthAuditLog).where(AuthAuditLog.user_id==c['person'],AuthAuditLog.event_type=='progress_retirement_attempt'))
        assert count==1
    retry=c['client_http'].post(METADATA,json=query(c,factor={'recovery_code':codes[0]}))
    assert retry.status_code==200 and retry.json()['items'][0]['link_id']==c['link']
    assert c['engine'].pool.checkedout()==0


def test_unavailable_commit_rollback_and_precleanup_close_invalidates_owned_session(retired_scope,monkeypatch,caplog):
    """One unavailable cleanup boundary: no successful commit/rollback/close release.

    Retain the exact Session to avoid GC masking a checked-out connection. The
    final block cleans up only our own retained Session after observing state.
    This is a compound driver/cleanup fault model, not a remote exploit claim.
    """
    from web.database import engine as database
    from web.database.tenant_context import current_tenant
    c=retired_scope;held=[]
    class UnavailableCleanup(Session):
        def commit(self):
            if any(getattr(row,'event_type',None)=='progress_retirement_metadata' for row in self.new):
                self.info['independent_cleanup_fault']=True
                raise RuntimeError('PRIVATE_DRIVER_COMMIT_UNAVAILABLE')
            super().commit()
        def rollback(self):
            if self.info.get('independent_cleanup_fault'):raise RuntimeError('PRIVATE_DRIVER_ROLLBACK_UNAVAILABLE')
            super().rollback()
        def close(self):
            if self.info.get('independent_cleanup_fault'):
                held.append(self)
                raise RuntimeError('PRIVATE_DRIVER_CLOSE_BEFORE_RELEASE')
            super().close()
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=c['engine'],class_=UnavailableCleanup,expire_on_commit=True))
    outer=current_tenant.set(c['other'])
    try:
        with pytest.raises(HTTPException) as error:invoke(c,query(c))
        assert error.value.status_code==503
        assert current_tenant.get()==c['other']
        assert all(marker not in caplog.text for marker in ['PRIVATE_DRIVER_COMMIT_UNAVAILABLE','PRIVATE_DRIVER_ROLLBACK_UNAVAILABLE','PRIVATE_DRIVER_CLOSE_BEFORE_RELEASE'])
        assert c['engine'].pool.checkedout()==0,'An owned active Session must be invalidated when rollback and pre-release close fail'
    finally:
        current_tenant.reset(outer)
        for session in held:
            session.info.pop('independent_cleanup_fault',None)
            Session.rollback(session);Session.close(session)
