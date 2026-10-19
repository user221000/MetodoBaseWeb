"""Direct SQL publication must retain owner eligibility while waiting on bytes metadata."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration_client_link_canonical_postgres import lab,clean_lab,tx,issue,accept,publish,GA,CA


def test_direct_publisher_retains_owner_lock_before_waiting_for_object(lab):
    issued=issue(lab);accept(lab,issued)
    ready=Event();state={}
    def publisher():
        with tx(lab,GA) as db:
            state['pid']=db.scalar(text('SELECT pg_backend_pid()'));ready.set()
            identity=publish(lab,issued,connection=db)
            db.commit();return identity
    changed=False
    with lab['admin'].begin() as blocker,ThreadPoolExecutor(max_workers=1) as executor:
        blocker.execute(text('SELECT id FROM stored_objects WHERE id=:id FOR UPDATE'),{'id':lab['objects'][CA].id})
        future=executor.submit(publisher);assert ready.wait(2)
        with lab['admin'].connect() as observer:
            deadline=time.monotonic()+3
            while not observer.scalar(text('SELECT cardinality(pg_blocking_pids(:pid))>0'),{'pid':state['pid']}):
                assert time.monotonic()<deadline
                time.sleep(.01)
            try:
                observer.execute(text('SELECT id FROM usuarios WHERE id=:id FOR UPDATE NOWAIT'),{'id':GA})
                observer.execute(text('UPDATE usuarios SET activo=false WHERE id=:id'),{'id':GA})
                observer.commit();changed=True
            except DBAPIError as busy:
                assert busy.orig.pgcode=='55P03';observer.rollback()
        blocker.commit();identity=future.result(timeout=6)
    assert not changed,'Owner deactivation committed while direct publication held source locks and was still awaiting object'
    with lab['admin'].connect() as db:
        assert db.scalar(text('SELECT status FROM client_plan_publications WHERE id=:id'),{'id':identity})=='published'
