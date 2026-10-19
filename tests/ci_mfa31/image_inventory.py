"""Read real current image schema/linkage identity; stdin to owned container."""
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import inspect, text
from web.database.engine import get_engine
from web.database.models import Base
from web.database.schema_control import expected_head, verify_runtime_schema
from web.database.alembic.history_index_contract_v1 import expected_history_index, history_index_signature

assert os.getuid() != 0
assert 'MIGRATOR_DATABASE_URL' not in os.environ
parent = Path('/proc/1')
assert b'MIGRATOR_DATABASE_URL=' not in (parent / 'environ').read_bytes()
assert b'web/main_web.py' in (parent / 'cmdline').read_bytes()
status = dict(line.split(':', 1) for line in (parent / 'status').read_text().splitlines() if ':' in line)
assert status['NoNewPrivs'].strip() == '1' and int(status['CapEff'].strip(), 16) == 0
assert expected_head() == '20261019_mfa' and len(Base.metadata.tables) == 32
engine = get_engine()
verify_runtime_schema(engine, expected_revision='20261019_mfa')
with engine.connect() as db:
    assert len(inspect(db).get_table_names()) == 33
    assert db.scalar(text('SELECT version_num FROM alembic_version')) == '20261019_mfa'
    assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()) == (False, False, False, False)
    assert db.scalar(text('SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()'))
    index = history_index_signature(db)
    assert index == expected_history_index('postgresql')
sources = ['web/main_web.py', 'web/database/models.py', 'web/routes/mfa.py',
           'web/services/mfa_service.py', 'web/static/js/api.js', 'web/static/js/mfa-login.js',
           'web/static/js/mfa-ui.js', 'entrypoint.sh']
print(json.dumps({'complete': True, 'model_tables': 32, 'actual_tables': 33,
    'runtime_revision': expected_head(), 'history_order_index': index,
    'restricted_nonowner': True, 'migrator_absent_in_exec_child_and_pid1': True,
    'actual_pid1_main_web': True, 'lab_cap_eff_zero_no_new_privs': True,
    'sources_sha256': {name: hashlib.sha256(Path('/app', name).read_bytes()).hexdigest() for name in sources}}))
