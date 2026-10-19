"""Invalidation uncertainty stays opaque; release is observed, never assumed."""
import json,os
from pathlib import Path
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session,sessionmaker
from fastapi import HTTPException
from tests.test_progress_retirement_http import progress_db,progress_http,retired_scope,query


@pytest.mark.parametrize('release_before_error',[False,True])
def test_invalidation_failure_restores_scope_without_claiming_unobserved_release(retired_scope,monkeypatch,caplog,release_before_error):
    from web.database import engine as database
    from web.database.tenant_context import current_tenant
    from web.progress_retirement_schemas import Metadata
    from web.routes.progress_retirement import _execute
    c=retired_scope;held=[];invalidated=[];disposed=[]
    class UnavailableCleanup(Session):
        def commit(self):
            if any(getattr(row,'event_type',None)=='progress_retirement_metadata' for row in self.new):
                self.info['independent_invalidation_fault']=True
                raise RuntimeError('PRIVATE_COMMIT_UNAVAILABLE')
            super().commit()
        def rollback(self):
            if self.info.get('independent_invalidation_fault'):raise RuntimeError('PRIVATE_ROLLBACK_UNAVAILABLE')
            super().rollback()
        def close(self):
            if self.info.get('independent_invalidation_fault'):
                held.append(self)
                raise RuntimeError('PRIVATE_CLOSE_UNAVAILABLE')
            super().close()
        def invalidate(self):
            invalidated.append(self)
            if release_before_error:Session.invalidate(self)
            raise RuntimeError('PRIVATE_INVALIDATION_UNAVAILABLE')
    def disposal(engine):disposed.append(True)
    event.listen(c['engine'],'engine_disposed',disposal)
    monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=c['engine'],class_=UnavailableCleanup,expire_on_commit=True))
    outer=current_tenant.set(c['other'])
    try:
        with pytest.raises(HTTPException) as error:
            _execute(Metadata.model_validate(query(c)),'metadata')
        assert error.value.status_code==503 and error.value.detail['code']=='progress_retirement_unconfirmed'
        assert current_tenant.get()==c['other']
        assert len(held)==len(invalidated)==1 and held[0] is invalidated[0]
        assert disposed==[]
        assert all(marker not in caplog.text for marker in ['PRIVATE_COMMIT_UNAVAILABLE','PRIVATE_ROLLBACK_UNAVAILABLE','PRIVATE_CLOSE_UNAVAILABLE','PRIVATE_INVALIDATION_UNAVAILABLE'])
        assert 'invalidation class=RuntimeError' in caplog.text
        checkedout=c['engine'].pool.checkedout()
        assert checkedout==(0 if release_before_error else 1)
        observation={'factory':c['factory'],'invalidation_error_stage':'after_real_release' if release_before_error else 'before_real_release',
            'response':503,'context_restored':True,'only_new_owned_session_invalidated':True,'engine_dispose_called':False,
            'checkedout_observed_before_harness_cleanup':checkedout,
            'limit':'When invalidation itself fails before release, this model retains one checkout; no release guarantee is claimed.'}
        target=Path(os.environ['SEC_RETIREMENT_INVALIDATION_RECEIPTS'])/(c['factory'].replace('.','-')+'-'+str(release_before_error)+'.json')
        with target.open('x',encoding='utf8') as output:json.dump(observation,output,indent=2);output.write('\n')
    finally:
        event.remove(c['engine'],'engine_disposed',disposal)
        current_tenant.reset(outer)
        for session in held:
            session.info.pop('independent_invalidation_fault',None)
            Session.rollback(session);Session.close(session)
    assert c['engine'].pool.checkedout()==0
