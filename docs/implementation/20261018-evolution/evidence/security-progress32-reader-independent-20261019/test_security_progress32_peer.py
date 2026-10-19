"""Independent source-read exception boundaries and live authority transitions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_progress32_postgres import progress_db, progress_http, make_source, blank_pool  # noqa:F401
from tests.test_personal_progress_http import shared_path


@pytest.mark.parametrize('failure', ['restore_statement', 'rollback_savepoint'])
def test_uncertain_restoration_never_returns_part_of_source_and_pool_reuse_is_clean(progress_http, monkeypatch, failure):
    from web.services import progress_readers as readers
    c=progress_http;link,consent=make_source(c);invalidations=[];triggered=[]
    def invalidated(connection, record, exception):invalidations.append(type(exception).__name__)
    event.listen(c['engine'].pool,'invalidate',invalidated)
    def restore_error(connection,cursor,statement,parameters,context,many):
        if statement.startswith("SELECT set_config('app.current_tenant'") and parameters.get('original')==c['gym']:
            triggered.append('restore');raise RuntimeError('Synthetic independent restore boundary')
    def rollback_error(connection,name,context):
        triggered.append('rollback');raise RuntimeError('Synthetic independent savepoint rollback boundary')
    if failure=='restore_statement':event.listen(c['engine'],'before_cursor_execute',restore_error)
    else:
        monkeypatch.setattr(readers,'_counts_sql',lambda dialect:text('SELECT 1/0'))
        event.listen(c['engine'],'rollback_savepoint',rollback_error)
    try:
        result=c['client_http'].get(shared_path(c,link,consent),headers=c['headers']['gym'])
    finally:
        event.remove(c['engine'].pool,'invalidate',invalidated)
        if failure=='restore_statement':event.remove(c['engine'],'before_cursor_execute',restore_error)
        else:event.remove(c['engine'],'rollback_savepoint',rollback_error)
    assert result.status_code==503
    assert result.json()['detail']['code']=='progress_unconfirmed'
    assert 'peso_kg' not in result.text and c['person'] not in result.text
    assert result.headers['Cache-Control']=='no-store'
    assert len(triggered)==1
    assert len(invalidations)==(1 if failure=='rollback_savepoint' else 0)
    assert c['engine'].pool.checkedout()==0
    blank_pool(c['engine'])
    assert c['client_http'].get('/api/auth/me',headers=c['headers']['other']).status_code==200


def test_authority_locks_block_updates_then_changed_source_and_reader_roles_deny_old_scope(progress_http):
    from web.database.models import Usuario,Subscription,ClientAccountLink,UserRole
    c=progress_http;link,consent=make_source(c);started=Event();release=Event()
    def hold(connection,cursor,statement,parameters,context,many):
        if 'WITH days AS MATERIALIZED' in statement:
            started.set();assert release.wait(10)
    event.listen(c['engine'],'before_cursor_execute',hold)
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            future=workers.submit(c['client_http'].get,shared_path(c,link,consent),headers=c['headers']['gym'])
            assert started.wait(10)
            for model,condition in [(Usuario,Usuario.id==c['person']),(Usuario,Usuario.id==c['gym']),
                    (Subscription,Subscription.gym_id==c['gym']),(ClientAccountLink,ClientAccountLink.id==link)]:
                with Session(c['admin']) as db:
                    with pytest.raises(DBAPIError) as busy:db.scalar(select(model).where(condition).with_for_update(nowait=True))
                    assert getattr(busy.value.orig,'pgcode',None)=='55P03'
            release.set();assert future.result(timeout=12).status_code==200
    finally:release.set();event.remove(c['engine'],'before_cursor_execute',hold)
    with Session(c['admin']) as db:db.get(Usuario,c['person']).role=UserRole.OWNER;db.commit()
    assert c['client_http'].get(shared_path(c,link,consent),headers=c['headers']['gym']).status_code==404
    with Session(c['admin']) as db:db.get(Usuario,c['person']).role=UserRole.VIEWER;db.get(Usuario,c['gym']).role=UserRole.VIEWER;db.commit()
    assert c['client_http'].get(shared_path(c,link,consent),headers=c['headers']['gym']).status_code==403
    blank_pool(c['engine'])

