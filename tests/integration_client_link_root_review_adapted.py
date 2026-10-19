"""Explicit head29 adaptation of root's immutable experimental review criteria.

Original driver5cac8ec7 and corrected RR driver7328d119 remain in root evidence.
Only canonical schema/fixture, required publication columns/SHA and pre-begin
isolation differ. Additional author projection tests use valid four-meal sources.
"""
from datetime import datetime,timezone
import hashlib
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration_client_link_canonical_postgres import lab,clean_lab,tx,issue,accept,publish,GA,UA,CA


@pytest.mark.parametrize('table',['planes_generados','stored_objects'])
def test_owner_reactivation_cannot_restore_invalidated_source(lab,table):
    issued=issue(lab);accept(lab,issued);publication=publish(lab,issued)
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:id'),{'id':GA})
    with tx(lab,GA) as db:
        if table=='planes_generados':
            db.execute(text('UPDATE public.planes_generados SET deleted_at=:at WHERE id=:id'),{'at':datetime.now(timezone.utc),'id':lab['plans'][CA]})
        else:
            db.execute(text("UPDATE public.stored_objects SET status='pending' WHERE id=:id"),{'id':lab['objects'][CA].id})
        db.commit()
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=true WHERE id=:id'),{'id':GA})
        assert db.scalar(text('SELECT status FROM public.client_plan_publications WHERE id=:id'),{'id':publication})=='withdrawn'
    with tx(lab,UA) as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications WHERE id=:id'),{'id':publication})==0


def test_inactive_recipient_cannot_use_previous_publication_or_lock(lab):
    issued=issue(lab);accept(lab,issued);publication=publish(lab,issued)
    with lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:id'),{'id':UA})
    with tx(lab,UA) as db:
        assert db.execute(text('SELECT id FROM public.client_plan_publications WHERE id=:id FOR SHARE'),{'id':publication}).all()==[]


def test_source_noop_under_repeatable_read_preserves_publication(lab):
    from web.database.tenant_context import tenant_scope
    issued=issue(lab);accept(lab,issued);publication=publish(lab,issued)
    with tenant_scope(GA),lab['app'].connect().execution_options(isolation_level='REPEATABLE READ') as db:
        db.execute(text('UPDATE public.planes_generados SET plan_json=plan_json WHERE id=:id'),{'id':lab['plans'][CA]})
        db.commit()
    with tx(lab,UA) as db:
        assert db.scalar(text('SELECT id FROM public.client_plan_publications WHERE id=:id'),{'id':publication})==publication


def test_direct_publication_cannot_commit_payload_different_from_exact_source(lab):
    issued=issue(lab);accept(lab,issued)
    sql=text("""INSERT INTO public.client_plan_publications(id,gym_id,client_id,link_id,source_plan_id,source_object_id,object_key,content_type,byte_size,sha256,storage_backend,plan_json,plan_sha256,published_by,status)
      SELECT :id,l.gym_id,l.client_id,l.id,p.id,o.id,o.key,o.content_type,o.byte_size,o.sha256,o.storage_backend,:payload,:plan_sha,:gym,'published'
      FROM public.client_account_links l JOIN public.planes_generados p ON p.gym_id=l.gym_id AND p.id_cliente=l.client_id
      JOIN public.stored_objects o ON o.gym_id=p.gym_id AND o.id=p.pdf_object_id WHERE l.id=:link""")
    payload='{"desayuno":{"kcal_real":999999,"nota_privada":"synthetic-only"}}'
    with tx(lab,GA) as db:
        with pytest.raises(DBAPIError):
            db.execute(sql,{'id':str(uuid.uuid4()),'link':issued['link'],'payload':payload,'plan_sha':hashlib.sha256(payload.encode()).hexdigest(),'gym':GA})
            db.commit()
