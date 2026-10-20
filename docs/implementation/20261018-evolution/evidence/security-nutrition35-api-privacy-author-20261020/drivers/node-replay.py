from pathlib import Path
import ast, hashlib, importlib.metadata, json, os, shutil, subprocess, sys
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp');P=T/'metodobase-sec-nutrition35-api-peer-private-20261019';D=P/'node-current';D.mkdir(exist_ok=False)
SHA=lambda b:hashlib.sha256(b).hexdigest();save=lambda n,v:(D/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
script=(T/'metodobase-sec-nutrition35-api-peer-run-20261019.py').read_bytes();photo_ast=next(n for n in ast.parse(script).body if isinstance(n,ast.FunctionDef)and n.name=='photo')
ns={'R':R,'SHA':SHA,'subprocess':subprocess,'importlib':importlib,'Path':Path,'sys':sys,'shutil':shutil};exec(compile(ast.Module(body=[photo_ast],type_ignores=[]),'photo-function-only','exec'),ns);photo=ns['photo']
before=photo();save('before.json',before)
files=['tests/e2e/nutrition35_api.cjs','tests/e2e/nutrition35_state.cjs','tests/e2e/nutrition35_dom.cjs','tests/e2e/nutrition35_personal_generation.cjs','tests/e2e/security_nutrition35_peer.cjs'];results=[]
for i,name in enumerate(files):
 cmd=[shutil.which('node'),name];r=subprocess.run(cmd,cwd=R,env=dict(os.environ),capture_output=True,timeout=60)
 (D/f'{i}-stdout.RAW.log').write_bytes(r.stdout);(D/f'{i}-stderr.RAW.log').write_bytes(r.stderr)
 report=json.loads(r.stdout);assert isinstance(report['total'],int)and isinstance(report['passed'],int)
 results.append({'path':name,'SHA256':SHA((R/name).read_bytes()),'exit':r.returncode,'cases':report['total'],'passed':report['passed'],'own':name==files[-1]})
save('results.STRUCTURAL.json',results);after=photo();save('after.json',after);assert before==after
summary={'runs':len(results),'cases':sum(r['cases']for r in results),'passed':sum(r['passed']for r in results),'own_cases':results[-1]['cases'],'all_exit_zero':all(r['exit']==0 for r in results),'source_packages92_bothPython_Node_quiet':True,'scope':'Actual JS namespaces/controllers with synthetic RAM transports and minimal DOM only. No HTTP/provider/Chrome/layout assertion.'};save('summary.json',summary);print(json.dumps(summary))
