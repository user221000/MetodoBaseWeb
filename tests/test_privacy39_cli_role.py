"""CLI canaries use the real role verifier and forbid reaching schema/apply."""
from contextlib import nullcontext
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('flags,owner',[((True,False),False),((False,True),False),((False,False),True)])
def test_operator_cli_rejects_effective_privileged_or_DDL_owner_role_before_work(monkeypatch,capsys,flags,owner):
    from scripts import privacy_disposition as cli
    import sqlalchemy
    # Import the real binding before the global engine double. Otherwise its
    # module-level alias can outlive monkeypatch and poison later SQLite work.
    from web.services import privacy_restore_binding
    from web.database import schema_control
    from web.database import tenant_context
    statements=[];closed=[]
    class Result:
        def one(self):return flags
        def scalar_one(self):return owner
    class Connection:
        dialect=SimpleNamespace(name='postgresql')
        def execute(self,statement,parameters=None):statements.append(str(statement));return Result()
    class Engine:
        dialect=SimpleNamespace(name='postgresql')
        def connect(self):return nullcontext(Connection())
        def dispose(self):closed.append(True)
    def schema_must_not_run(_):raise AssertionError('Schema/apply reached before privilege admission')
    monkeypatch.setenv('PRIVACY39_TEST_DATABASE_URL','postgresql+psycopg2://synthetic:synthetic@127.0.0.1:55483/metodobase_test_privacy39_role')
    monkeypatch.setattr(sqlalchemy,'create_engine',lambda *args,**kwargs:Engine())
    monkeypatch.setattr(tenant_context,'configure_tenant_engine',lambda engine:engine)
    monkeypatch.setattr(schema_control,'verify_runtime_schema',schema_must_not_run)
    code=cli.main(['inspect','--subject','synthetic','--request','a'*32,
        '--database-env','PRIVACY39_TEST_DATABASE_URL','--expected-database','metodobase_test_privacy39_role'])
    assert code==1 and closed==[True] and statements
    assert 'RuntimeError' in capsys.readouterr().out
