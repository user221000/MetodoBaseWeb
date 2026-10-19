"""Preserve the failed candidate and report its exact structural difference."""
from pathlib import Path
import importlib.util,json,yaml
ROOT=Path(r'F:\mb-r23-history30-20261019');path=ROOT/'tests/verify_history_index_ci.py';TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
spec=importlib.util.spec_from_file_location('recover_guard',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
norm=lambda p:p.read_bytes().replace(b'\r\n',b'\n')
def write(name,value):(ROOT/name).write_bytes(value.encode())
scope={'ROOT':ROOT,'path':path,'norm':norm,'write':write,'json':json,'vm_step':module.FOLLOWUP_VM_STEP,'pg_step':module.FOLLOWUP_PG_STEP,'report_step':module.FOLLOWUP_REPORT_STEP,'browser_step':module.FOLLOWUP_BROWSER_STEP,'browser_upload':module.FOLLOWUP_BROWSER_UPLOAD,'browser_run':module.FOLLOWUP_BROWSER_STEP['run']}
source=(TEMP/'metodobase-r23-ci-prepare.py').read_text(encoding='utf8');tail=source[source.index('# Preserve workflow text'):]
tail=tail[:tail.index('assert yaml.safe_load(workflow)==expected')]
exec(compile(tail,'original-workflow-candidate','exec'),scope)
candidate=scope['workflow'];expected=scope['expected'];actual=yaml.safe_load(candidate)
(TEMP/'metodobase-r23-ci-candidate-failed.yml').write_text(candidate,encoding='utf8')
def differences(a,b,path='root'):
    if type(a) is not type(b):return [{'path':path,'kind':'type'}]
    if isinstance(a,dict):
        out=[]
        for key in set(a)|set(b):
            if key not in a or key not in b:out.append({'path':path+'.'+str(key),'kind':'missing-key'})
            else:out.extend(differences(a[key],b[key],path+'.'+str(key)))
        return out
    if isinstance(a,list):
        if len(a)!=len(b):return [{'path':path,'kind':'length','expected':len(a),'actual':len(b)}]
        return [entry for i,(x,y) in enumerate(zip(a,b)) for entry in differences(x,y,path+'.'+str(i))]
    return [] if a==b else [{'path':path,'kind':'value','expected':a,'actual':b}]
rows=differences(expected,actual)
(TEMP/'metodobase-r23-ci-initial-diff.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8')
print(json.dumps(rows))
