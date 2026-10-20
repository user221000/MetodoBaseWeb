from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys, time
ROOT=Path('F:/mb-qa-browser31-20261020')
TASK=Path(__file__).resolve().parent
P=TASK/'private'
NODE=Path('C:/Program Files/nodejs/node.exe')
spec=importlib.util.spec_from_file_location('phasebase','C:/Users/Consu/AppData/Local/Temp/metodobase-qa-nutrition35-saas-20261020/phase.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.ROOT=ROOT;base.TASK=TASK;base.PRIVATE=P
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot(label):
    result=base.snapshot(label)
    result['node']={'path':str(NODE),'sha256':sha(NODE)}
    result['JS_helpers']={p.name:sha(p) for p in TASK.glob('*.cjs')}
    (P/(label+'-snapshot.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
def run(stage):
    before=snapshot(stage+'-before');base.pipcheck(stage+'-before')
    programs=[('author',['run-author.cjs'])] if stage=='before' else [('own',['own-controls.cjs']),('legacy',['tests/e2e/browser_export_compat31.cjs','current33_export_controls'])]
    results=[];env=dict(os.environ,DETACH31_SOURCE_ROOT=str(ROOT))
    for name,args in programs:
        file=TASK/args[0] if name!='legacy' else ROOT/args[0]
        started=time.monotonic()
        r=subprocess.run([str(NODE),str(file),*args[1:]],cwd=ROOT,env=env,capture_output=True)
        (P/(stage+'-'+name+'.stdout')).write_bytes(r.stdout);(P/(stage+'-'+name+'.stderr')).write_bytes(r.stderr)
        report=json.loads(r.stdout);row={'name':name,'exit':r.returncode,'passed':report['passed'],'total':report['total'],'elapsed_s':round(time.monotonic()-started,3)}
        if stage!='before':
            check=subprocess.run([sys.executable,str(ROOT/'scripts/check_frontend_report.py'),str(P/(stage+'-'+name+'.stdout')),'--format','counts','--minimum',str(6 if name=='own' else 21)],cwd=ROOT,capture_output=True)
            (P/(stage+'-'+name+'-parser.stdout')).write_bytes(check.stdout);(P/(stage+'-'+name+'-parser.stderr')).write_bytes(check.stderr)
            row['actual_parser_exit']=check.returncode
        results.append(row);print(json.dumps(row),flush=True)
    after=snapshot(stage+'-after');base.pipcheck(stage+'-after')
    quiet={key:before[key]==after[key] for key in before};assert all(quiet.values()),quiet
    result={'stage':stage,'head':before['head'],'results':results,'quiet':quiet,'source_count':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'pip':[0,0],'Chrome_PG':False}
    (TASK/(stage+'-result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'closed':True,'stage':stage,'quiet':quiet}),flush=True)
if __name__=='__main__':run(sys.argv[1])
