from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import shutil
ROOT=Path('F:/mb-qa-native37-20261020');TASK=Path(__file__).resolve().parent;P=TASK/'private';P.mkdir(exist_ok=True)
MODE=sys.argv[1];assert MODE in ('before','after')
NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
PROFILE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('environment_peer',ROOT/'tests/e2e/native37_environment_qa.py');lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
sha=lambda data:hashlib.sha256(data).hexdigest()
def put(name,value):
 with (P/name).open('xb') as stream:stream.write(value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode())
if MODE=='before':
 author=subprocess.check_output(['git','--no-replace-objects','show','9fd6432a491efd5906e52619cce31acac1356192:tests/e2e/notifications36_bootstrap.cjs'],cwd=ROOT)
 assert sha(author)=='ed3b590d6462f6425e9eb49d62c24fd1e341ff88c1a9215e9a769126bff9f044'
 put('author-canary.raw.cjs',author);put('product-before.raw.js',(ROOT/'web/static/js/notifications36.js').read_bytes())
 put('own-canary-source-receipt.json',{'sha256':sha((TASK/'mount-own-review.cjs').read_bytes()),'author_canary_sha256':sha(author),
     'DACL_before_payload':'Phase root inherited protected current-user and SYSTEM full control before source/output creation',
     'transport_fixture_only':'Original notifications36_state prefix and browser_harness31; actual api.js loaded classic in same VM. No options.api/window.Api.',
     'own_oracles':'Four mounted late/session-boundary negatives plus two absent-widget controls; no unique-global-coverage claim'})
pre=lib.photograph(ROOT,TASK,MODE+'-pre',PROFILE,NODE,CHROME,DEPS)
lib.pipcheck(ROOT,TASK,MODE)
env=os.environ.copy();env['QA_REVIEW_ROOT']=str(ROOT)
commands={
 'author8':[str(NODE),'-e',"const fs=require('node:fs'),Module=require('node:module'),path=require('node:path');const file=path.join(process.cwd(),'tests/e2e/notifications36_bootstrap.cjs');const m=new Module(file);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));m._compile(fs.readFileSync(process.argv[1],'utf8'),file);",str(P/'author-canary.raw.cjs')],
 'own6':[str(NODE),str(TASK/'mount-own-review.cjs')],
}
if MODE=='after':
 for key,file in [('maintained-state19','notifications36_state.cjs'),('maintained-dom8','notifications36_dom.cjs'),('maintained-nav9','notifications36_nav.cjs')]:commands[key]=[str(NODE),'tests/e2e/'+file]
results={}
for key,command in commands.items():
 result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=25)
 put(MODE+'-'+key+'.stdout',result.stdout);put(MODE+'-'+key+'.stderr',result.stderr)
 value=json.loads(result.stdout);rows=value.get('results',[])
 results[key]={'exit_code':result.returncode,'passed':value['passed'],'total':value['total'],
  'failure_classes':[r.get('error_class') for r in rows if not r['passed']],
  'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr)}
 if MODE=='before':
  expected={'author8':(2,8,6),'own6':(2,6,4)}[key]
  assert (value['passed'],value['total'],len([r for r in rows if not r['passed']]))==expected
  assert result.returncode==1 and set(results[key]['failure_classes'])=={'TypeError'}
 else:
  assert result.returncode==0 and value['passed']==value['total']
post=lib.photograph(ROOT,TASK,MODE+'-post',PROFILE,NODE,CHROME,DEPS)
stable={key:pre[key]==post[key] for key in pre};assert all(stable.values())
put(MODE+'-summary.json',{'results':results,'head':pre['head'],'stable':stable,'source_files':len(pre['source']),
 'packages':len(pre['packages']),'installed_files':len(pre['installed']),'node_files':len(pre['node_files']),
 'pip':0,'no_Chrome_PG_HTTP_or_services_executed':True})
print(json.dumps({'mode':MODE,'head':pre['head'],'results':results,'all_fields_stable':True,'source_files':len(pre['source']),
 'packages':len(pre['packages']),'installed_files':len(pre['installed']),'node_files':len(pre['node_files']),'pip':0}))
