"""Actual historical29 stays historical under model30; no PG needed for this focal."""
import importlib
import pytest
from sqlalchemy import create_engine,event
from sqlalchemy.orm import Session,sessionmaker

def test_genuine_SQLite29_explicit_pin_accepts_but_current30_and_factories_fail_without_writes(tmp_path,monkeypatch):
    from tests.integration_schema_migrations import run_migration
    from web.database import engine as database
    from web.database.alembic.schema_contract_v1 import schema_signature
    from web.database.schema_control import verify_runtime_schema
    from web.database.models import Usuario,UserRole
    engine=create_engine('sqlite:///'+str(tmp_path/'genuine-historical29.db'));url=str(engine.url)
    try:
        run_migration(url,'db_bootstrap.py','--revision','20261019_client_account_links')
        with Session(engine) as session:
            session.add(Usuario(id='qa-historical29-only',email='qa-historical29@example.invalid',nombre='Synthetic historical29',password_hash='synthetic-not-an-authentication-secret',tipo='gym',role=UserRole.OWNER));session.commit()
        with engine.connect() as connection:
            signature=schema_signature(connection)
            baseline={name:connection.exec_driver_sql('SELECT * FROM "'+name+'"').all() for name in ['alembic_version','usuarios','gym_profiles','refresh_tokens']}
        verify_runtime_schema(engine,expected_revision='20261019_client_account_links')
        with pytest.raises(RuntimeError,match='revision'):verify_runtime_schema(engine)
        monkeypatch.setattr(database,'_engine',engine);monkeypatch.setattr(database,'_SessionLocal',sessionmaker(bind=engine,autoflush=False))
        for factory in ['web.main_web','api.app']:
            statements=[]
            def observed(connection,cursor,sql,parameters,context,executemany):
                if sql.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:statements.append(sql.split(' ',1)[0])
            event.listen(engine,'before_cursor_execute',observed)
            try:
                with pytest.raises(RuntimeError,match='revision'):importlib.import_module(factory).create_app()
            finally:event.remove(engine,'before_cursor_execute',observed)
            assert statements==[]
        with engine.connect() as connection:
            assert schema_signature(connection)==signature
            assert {name:connection.exec_driver_sql('SELECT * FROM "'+name+'"').all() for name in baseline}==baseline
    finally:engine.dispose()
