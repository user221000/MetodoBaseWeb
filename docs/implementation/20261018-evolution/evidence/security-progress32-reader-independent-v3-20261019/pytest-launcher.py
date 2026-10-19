from pathlib import Path
import json,os,sys
ROOT=Path(r"F:\mb-security-progress32-peer-20261019")
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
profile=json.loads(Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq\env.json").read_bytes())
os.environ.update(profile)
os.environ['SEC32_PRIVATE_LEASES']=r"C:\Users\Consu\AppData\Local\Temp\metodobase-sec32-peer-private-v3-20261019\leases"
os.environ['SEC32_BOUNDARY_RECEIPT']=r"C:\Users\Consu\AppData\Local\Temp\metodobase-sec32-peer-private-v3-20261019\parent-boundary.json"
from tests import progress32_fixtures
from tests.security_progress32_owned import owned_database
progress32_fixtures.owned_database=owned_database
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
