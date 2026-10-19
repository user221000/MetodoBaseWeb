"""Independent postcommit notice and worker/log containment probes."""
from pathlib import Path
from threading import Event
from datetime import datetime,timezone
import importlib,time,json
import pytest
from sqlalchemy.orm import Session,sessionmaker
from fastapi.testclient import TestClient
from test_recovery_security import engine,old_hash,clean,seeded,case,issue,confirm,idle,snapshot,privacy,A,B,EMAIL,NEW,OLD

@pytest.mark.parametrize('ack',[False,1,'true'])
def test_non_boolean_mail_acceptance_does_not_claim_accepted_or_undo_digest(seeded,ack,caplog):
 from web.services import password_recovery as recovery
 before=recovery.recovery_status();observed=[]
 recovery.issue_request(EMAIL,'https://independent-recovery.example.invalid',factory=sessionmaker(bind=seeded),sender=lambda *args:observed.append(args) or ack)
 after=recovery.recovery_status()
 assert observed and snapshot(seeded)['reset'] is not None
 assert after['accepted']==before['accepted'] and after['unconfirmed']==before['unconfirmed']+1
 assert snapshot(seeded)['sv']==4 and snapshot(seeded)['live_rt']==1
 assert all(value not in caplog.text for value in [EMAIL,observed[0][2]])

def test_failed_postcommit_change_notice_never_undoes_or_marks_real_password_change_unconfirmed(case,monkeypatch,caplog):
 from web.services import email_service,password_recovery as recovery
 from web.auth import verify_password
 token=issue(case);before=recovery.recovery_status()
 def failure(*args):raise RuntimeError('independent-private-notice '+token+' '+NEW)
 monkeypatch.setattr(email_service,'send_password_changed',failure)
 response=confirm(case,token);assert response.status_code==200;privacy(response);idle(case)
 assert response.json()['code']=='password_reset_complete'
 after=snapshot(case.engine);assert after['sv']==5 and after['reset'] is None and after['live_rt']==0 and verify_password(NEW,after['hash'])
 assert recovery.recovery_status()['notification_unconfirmed']==before['notification_unconfirmed']+1
 assert all(value not in response.text+caplog.text for value in [token,NEW,'independent-private-notice'])

def test_worker_exception_releases_capacity_and_never_formats_private_error(caplog):
 from web.services.recovery_dispatcher import RecoveryDispatcher
 from web.database.tenant_context import tenant_scope,current_tenant
 class PrivateError(Exception):
  def __str__(self):raise AssertionError('Private exception string inspected')
  def __repr__(self):raise AssertionError('Private exception representation inspected')
 first,release,second=Event(),Event(),Event();observed=[]
 dispatcher=RecoveryDispatcher(workers=1,capacity=1)
 def fail():
  observed.append(current_tenant.get());first.set();assert release.wait(3);raise PrivateError()
 try:
  with tenant_scope(A):assert dispatcher.submit(fail)
  assert first.wait(2);assert dispatcher.submit(lambda:None) is False
  release.set();deadline=time.monotonic()+3
  while dispatcher.pending and time.monotonic()<deadline:time.sleep(.005)
  assert dispatcher.pending==0 and observed==['']
  assert dispatcher.submit(second.set);assert second.wait(2)
  deadline=time.monotonic()+3
  while dispatcher.pending and time.monotonic()<deadline:time.sleep(.005)
  assert dispatcher.pending==0
 finally:release.set();dispatcher.close()
 assert 'PrivateError' in caplog.text
