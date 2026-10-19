import sys,pathlib,os,json,hashlib
ROOT=pathlib.Path('F:/mb-r24-sec');sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True;os.chdir(ROOT)
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
import pytest
folder=pathlib.Path(__file__).parent
code=pytest.main([str(folder/'test_http_review.py'),'--confcutdir='+str(folder),'-q','--tb=short','--junitxml='+str(folder/'http.xml')])
origins={}
for name,module in list(sys.modules.items()):
    if name.startswith(('web.','api.','src.','tests.')) and getattr(module,'__file__',None):
        file=pathlib.Path(module.__file__).resolve();assert file.is_relative_to(ROOT),(name,str(file));origins[name]=str(file.relative_to(ROOT))
from web.database.models import Base
assert pathlib.Path(sys.modules[Base.__module__].__file__).resolve().is_relative_to(ROOT)
(folder/'http-origins.json').write_text(json.dumps({'source_root':str(ROOT),'module_origins':origins,'base_verified':True,'pytest_exit':code},indent=2),'utf-8')
raise SystemExit(code)
