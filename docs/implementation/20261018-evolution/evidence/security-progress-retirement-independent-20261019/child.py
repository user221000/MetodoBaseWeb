from pathlib import Path
import json,os,sys
root=Path(sys.argv[1]);raw=Path(sys.argv[2]);args=sys.argv[3:]
os.chdir(root);sys.path.insert(0,str(root))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
if '--postgres' in args:
    args.remove('--postgres')
    os.environ.update(json.loads(Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes()))
    os.environ['SEC32_PRIVATE_LEASES']=str(raw.parent/'leases')
    from tests.security_retirement_owned import owned_database
    import tests.retirement32_owned as author
    author.owned_database=owned_database
import pytest
raise SystemExit(pytest.main(args+['--basetemp='+str(raw/'pytest-run'),'--junitxml='+str(raw/'results.xml'),'-o','cache_dir='+str(raw/'pytest-cache')]))
