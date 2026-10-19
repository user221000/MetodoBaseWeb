from pathlib import Path
import json,os,sqlite3,subprocess,sys

ROOT=Path(r'F:\mb-qa-bootstrap-log-20261019')
PREVIOUS='20261019_client_account_links'

def test_own_post_verification_error_stays_opaque_and_unknown_logger_disabled(tmp_path):
    database=tmp_path/'qa-private-after-verify.db'
    witness=tmp_path/'qa-private-witness.json'
    environment=os.environ.copy()
    for key in ('DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL'):
        environment.pop(key,None)
    environment.update(DATABASE_URL='sqlite:///'+database.as_posix(),METODOBASE_ENV='testing',ENV='testing',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',QA_PRIVATE_WITNESS=str(witness))
    child="""from pathlib import Path
import json,logging,os,sys
import db_bootstrap
from web.database import schema_control
unknown=logging.getLogger('qa_unknown_logger_before_fileconfig')
assert unknown.disabled is False
original=schema_control.verify_runtime_schema
def fault_after_real_verify(engine,**kwargs):
    original(engine,**kwargs)
    assert unknown.disabled is True
    assert not db_bootstrap.logger.disabled
    record={'real_verify_completed':True,'unknown_logger_disabled':unknown.disabled,'bootstrap_enabled':not db_bootstrap.logger.disabled,'bootstrap_level':db_bootstrap.logger.level,'root_level':logging.getLogger().level,'sqlalchemy_level':logging.getLogger('sqlalchemy.engine').level}
    Path(os.environ['QA_PRIVATE_WITNESS']).write_text(json.dumps(record))
    raise RuntimeError('QA_PRIVATE_EXCEPTION_DETAIL_MARKER '+str(Path(os.environ['QA_PRIVATE_WITNESS'])))
schema_control.verify_runtime_schema=fault_after_real_verify
result=db_bootstrap.main(['--revision','20261019_client_account_links'])
unknown.error('QA_PRIVATE_UNKNOWN_LOGGER_MARKER')
raise SystemExit(result)
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',child],cwd=ROOT,env=environment,capture_output=True,check=False,timeout=60)
    for suffix,raw in [('stdout',result.stdout),('stderr',result.stderr)]:
        (tmp_path/('own-control.'+suffix+'.raw.log')).write_bytes(raw)
    output=(result.stdout+result.stderr).decode('utf-8',errors='strict')
    assert result.returncode==1
    facts=json.loads(witness.read_text())
    assert facts=={'real_verify_completed':True,'unknown_logger_disabled':True,'bootstrap_enabled':True,'bootstrap_level':20,'root_level':30,'sqlalchemy_level':30}
    assert output.count('Migration aborted class=RuntimeError; database not accepted for release')==1
    assert 'Migration completed and verified' not in output
    assert 'QA_PRIVATE_EXCEPTION_DETAIL_MARKER' not in output
    assert 'QA_PRIVATE_UNKNOWN_LOGGER_MARKER' not in output
    assert str(tmp_path) not in output
    assert 'Traceback' not in output
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone()==(PREVIOUS,)
