from pathlib import Path
import os,sys,json
ROOT=Path(r'F:/mb-progress32-retirement-20261019')
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
if '--postgres' in sys.argv:
    sys.argv.remove('--postgres')
    os.environ.update(json.loads(Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes()))
from tests import progress32_fixtures
from tests.retirement32_owned import owned_database
original=progress32_fixtures.owned_database
progress32_fixtures.owned_database=lambda dialect,directory:owned_database(dialect,directory) if dialect=='postgresql' else original(dialect,directory)
os.environ['RETIREMENT32_PRIVATE_LEASES']=str(Path(__file__).parent/'leases')
os.environ['SEC32_BOUNDARY_RECEIPT']=str(Path(__file__).parent/'baseline-parent-boundary.json')
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
