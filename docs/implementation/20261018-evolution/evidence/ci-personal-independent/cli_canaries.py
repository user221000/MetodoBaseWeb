"""Independent CLI canaries against the frozen frontend report guard."""
from pathlib import Path
import copy
import json
import subprocess
import sys

ROOT=Path(r"F:\MetodoBaseWeb-execution-20261018")
OUT=Path(__file__).resolve().parent
GUARD=ROOT/"scripts/check_frontend_report.py"
CASES=[]

def add(label,kind,payload,accepted=False,minimum=2,screens=0,raw=None,missing=False):
    CASES.append(dict(label=label,kind=kind,payload=payload,accepted=accepted,
                      minimum=minimum,screens=screens,raw=raw,missing=missing))

strings={"checks":["One","Two"],"pageErrors":[]}
named={"checks":[{"name":"One"},{"name":"Two","passed":True}],"pageErrors":[],"screens":["mobile","desktop"]}
counts={"total":2,"passed":2,"results":[{"case":"One","passed":True},{"case":"Two","passed":True}]}
for kind,report in [('strings',strings),('named',named),('counts',counts)]:
    screens=2 if kind=='named' else 0
    add(kind+' genuine shape',kind,report,True,screens=screens)
    for bad in (None,[],{},False,42):
        add(kind+' invalid top '+str(bad),kind,bad,screens=screens)
    add(kind+' empty file',kind,None,raw='',screens=screens)
    add(kind+' malformed JSON',kind,None,raw='{synthetic',screens=screens)
    add(kind+' missing file',kind,None,missing=True,screens=screens)
    add(kind+' zero minimum',kind,report,minimum=0,screens=screens)
    add(kind+' negative screen minimum',kind,report,screens=-1)

for key,values in {'total':[True,False,2.0,'2',3,9007199254740992],
                   'passed':[True,False,2.0,'2',1,3],
                   'results':[None,{},[],[{'case':'One','passed':True}],
                              [{'case':'One','passed':True}]*2,
                              [{'case':'One','passed':True},{'case':'Two','passed':1}],
                              [{'case':'One','passed':True},{'case':'Two','passed':'true'}],
                              [{'case':'One','passed':True},{'case':'Two','passed':False}],
                              [{'case':'One','passed':True},{'case':'Two'}],
                              [{'case':'One','passed':True},{'case':' ','passed':True}],
                              [{'case':'One','passed':True},{'case':False,'passed':True}]]}.items():
    for index,value in enumerate(values):
        report=copy.deepcopy(counts);report[key]=value
        add('counts '+key+' invalid '+str(index),'counts',report)

for kind,original in [('strings',strings),('named',named)]:
    screens=2 if kind=='named' else 0
    for errors in (None,False,{},'error',['synthetic error']):
        report=copy.deepcopy(original);report['pageErrors']=errors
        add(kind+' pageErrors '+repr(errors),kind,report,screens=screens)
    for checks in (None,{},[],[True,False],['One','One'],['One',' '],
                   [{'name':'One'},{'name':'Two','passed':False}],
                   [{'name':'One'},{'name':'Two','passed':1}]):
        report=copy.deepcopy(original);report['checks']=checks
        add(kind+' invalid checks '+repr(checks),kind,report,screens=screens)
for screens in (None,False,'mobile',[],['mobile'],['mobile','mobile'],['mobile',False],['mobile',' ']):
    report=copy.deepcopy(named);report['screens']=screens
    add('named invalid screens '+repr(screens),'named',report,screens=2)
# Extra checks cannot mask an explicit failed check.
report=copy.deepcopy(named);report['checks'].append({'name':'Failed third','passed':False})
add('named surplus failure','named',report,screens=2)

results=[]
for index,case in enumerate(CASES):
    path=OUT/('canary-'+str(index)+'.json')
    if not case['missing']:
        path.write_text(case['raw'] if case['raw'] is not None else json.dumps(case['payload']),encoding='utf8')
    command=[sys.executable,'-X','utf8',str(GUARD),str(path),'--format',case['kind'],
             '--minimum',str(case['minimum']),'--minimum-screens',str(case['screens'])]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    matched=(result.returncode==0)==case['accepted']
    results.append({'label':case['label'],'expectedAcceptance':case['accepted'],
                    'exit':result.returncode,'matched':matched,'stderr':result.stderr.strip()})
(OUT/'cli-canaries.json').write_text(json.dumps({'total':len(results),'matched':sum(r['matched'] for r in results),'results':results},indent=2),encoding='utf8')
print('CLI canaries',len(results),'matched',sum(r['matched'] for r in results))
for row in results:
    if not row['matched']:print(row)
raise SystemExit(0 if all(r['matched'] for r in results) else 1)
