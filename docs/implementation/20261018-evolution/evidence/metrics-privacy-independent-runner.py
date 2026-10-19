from pathlib import Path
import importlib.util,json,os,socket,sys
r=Path(__file__).parent;a=Path('F:/MetodoBaseWeb-metrics-20261019');sys.path.insert(0,str(a));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True)
block_external_sockets()
import pytest
class Results:
 def __init__(self):self.items=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or (report.when in {'setup','teardown'} and report.failed):self.items.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome})
plugin=Results();mode=sys.argv[1]
os.environ['INDEPENDENT_METRICS_SOURCE']=str(r/'baseline-metrics.py' if mode=='baseline' else a/'web/middleware/metrics.py')
exit_code=pytest.main([str(r/'test_metrics_security_review.py'),'-q','--tb=short','-o','cache_dir='+str(r/('cache-'+mode)),'--junitxml='+str(r/('results-'+mode+'.xml'))],plugins=[plugin])
record={'scope':'Independent synthetic ASGI and direct middleware canaries; external socket connect/connect_ex blocked, loopback permitted for Windows asyncio self-pipe, providers cleared, no production data or HTTP listener','source':os.environ['INDEPENDENT_METRICS_SOURCE'],'exit_code':int(exit_code),'total':len(plugin.items),'passed':sum(x['outcome']=='passed' for x in plugin.items),'results':plugin.items}
(r/('results-'+mode+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
raise SystemExit(exit_code)
