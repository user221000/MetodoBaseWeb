"""Current33 physical witnesses from actual connections, never model count alone."""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import inspect,text

REVISION='20261019_google_subjects'


def physical_contract(engine,*,expected_pool=1,schema='33'):
    from web.database.models import Base
    from web.database.schema_control import expected_head,verify_runtime_schema
    from web.database.alembic.history_index_contract_v1 import expected_history_index,history_index_signature
    revision_expected={'33':REVISION,'32':'20261019_personal_progress'}[schema]
    model_expected={'33':35,'32':33}[schema]
    assert engine.dialect.name=='postgresql'
    assert expected_head()==revision_expected and len(Base.metadata.tables)==model_expected
    verify_runtime_schema(engine,expected_revision=revision_expected)
    assert engine.pool.size()==expected_pool
    with engine.connect() as db:
        physical=len(inspect(db).get_table_names())
        revision=db.scalar(text('SELECT version_num FROM alembic_version'))
        flags=tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one())
        database_nonowner=db.scalar(text('SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()'))
        owned=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)"))
        force=db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
        functions=db.execute(text("SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prosecdef,p.proconfig,p.proacl::text,pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)")).all()
        triggers=db.execute(text("SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid),t.tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace='public'::regnamespace AND NOT t.tgisinternal ORDER BY c.relname,t.tgname")).all()
        fks=db.execute(text("SELECT c.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated,k.condeferrable,k.condeferred FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relnamespace='public'::regnamespace AND k.contype='f' ORDER BY c.relname,k.conname")).all()
        gucs=tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.client_invitation_digest',true),current_setting('app.mfa_actor',true)")).one())
        index=history_index_signature(db);google=None
        if schema=='33':
            from web.database.google_identity_policy import signature as google_signature
            google=google_signature(db)
        assert physical==model_expected+1 and revision==revision_expected and flags==(False,)*4
        assert database_nonowner is True and owned==0 and force==26
        assert len(functions)=={'33':26,'32':24}[schema] and len(triggers)=={'33':12,'32':10}[schema] and fks and all(row[3] for row in fks)
        assert all(row[3]=='O' for row in triggers)
        assert gucs==('','','') and index==expected_history_index('postgresql')
        assert 'progress_consents' in inspect(db).get_table_names()
        if schema=='33':assert {'auth_external_identities','google_link_intents'}<=set(inspect(db).get_table_names())
    digest=lambda values:hashlib.sha256(json.dumps(values,default=list,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'runtime_revision':revision,'model_tables':len(Base.metadata.tables),'actual_tables':physical,
        'application_role_restricted_nonowner':True,'role_flags4':list(flags),'owned_tables':owned,
        'FORCE_RLS_tables':force,'application_pool_size':expected_pool,'signed_functions':len(functions),
        'signed_triggers':len(triggers),'functions_sha256':digest([list(row) for row in functions]),
        'triggers_sha256':digest([list(row) for row in triggers]),'foreign_keys_sha256':digest([list(row) for row in fks]),
        'google_identity_signature_sha256':digest(google),'blank_GUCs':True,'history_index':index}
