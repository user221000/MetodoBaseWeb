from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,tarfile,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(r'F:\mb-r25-qa-ui-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp')
EV=ROOT/'docs/implementation/20261018-evolution/evidence'
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
source=ast.parse((TEMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
scan_node=next(node for node in source.body if isinstance(node,ast.FunctionDef) and node.name=='scan')
exec(compile(ast.Module(body=[scan_node],type_ignores=[]),'<reviewed-token-scanner>','exec'))
def dump(path,data):
    raw=(json.dumps(data,indent=2)+'\n').encode();scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
def copy(path,raw):
    scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
for name,private,xml in [
    ('qa-r25-ui-independent-20261019','metodobase-r25-qa-ui-20261019','http-results.xml'),
    ('qa-r25-ui-http-replay-independent-20261019','metodobase-r25-qa-ui-http-replay-20261019','results.xml')]:
    out=EV/name;phase=TEMP/private
    before=json.loads((phase/'before.private.json').read_bytes());after=json.loads((phase/'after.private.json').read_bytes());assert before==after
    copy(out/'source-environment-before.json',(phase/'before.private.json').read_bytes())
    dump(out/'source-environment-quiet.json',{'before_SHA256':SHA((phase/'before.private.json').read_bytes()),'after_SHA256':SHA((phase/'after.private.json').read_bytes()),'exact_equal':True,'head':before['head'],
        'scope':'Full tracked RAW bytes and Python/Node/Chrome metadata in first phase; runtime prefixes and Python/test metadata in replay. These are separate measured intervals.'})
    cases=[]
    for row in ET.parse(phase/xml).iter('testcase'):
        failure=row.find('failure');error=row.find('error')
        cases.append({'class':row.get('classname'),'name':row.get('name'),'failed':failure is not None,'error':error is not None,'skipped':row.find('skipped') is not None})
    dump(out/'http-cases.json',{'cases':cases,'count':len(cases),'passed':sum(not(r['failed'] or r['error'] or r['skipped']) for r in cases),'failures':sum(r['failed'] for r in cases),'errors':sum(r['error'] for r in cases)})
    dump(out/'erratum-initial-classification.json',{'initial_run':'36 cases: 30 pass,6 new QA reds. The2 SSR and22 author HTTP passed.',
        'own_harness_errors':'Four reds were incorrect new expectations: plan-required is402, not403/409; completion retains its empty basis/items object. Export cache equality was also too narrow: no-store,max-age=0 satisfies no-store.',
        'actual_finding_after_unmask':'After these expectation corrections,12 own cases gave10 pass,2 product reds: uppercase new eighth cursor validation422 has Referrer-Policy strict-origin-when-cross-origin instead of no-referrer, both factories. No demonstrated payload leak. The private-header assertion remains unchanged.',
        'no_product_edits':True,'historical_tests_unchanged':True})
    archive=TEMP/(private+'-originals-private.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as target:
        for item in phase.iterdir():
            if item.is_file():target.write(item,item.name)
    dump(out/'private-originals-receipt.json',{'archive_name':archive.name,'bytes':archive.stat().st_size,'SHA256':SHA(archive.read_bytes()),'uploaded':False,
        'contains':'Original stdout/stderr/JUnit and source/environment photos. These RAW artifacts remain private; no token-bearing content is published.'})
    files=[]
    for item in sorted(out.iterdir()):
        if item.is_file():
            raw=item.read_bytes();scan(raw,item.name);files.append({'path':item.name,'bytes':len(raw),'SHA256':SHA(raw)})
    dump(out/'manifest.json',{'source_head':before['head'],'files':files})
    print(json.dumps({'prefix':str(out),'files':len(files),'manifest_SHA256':SHA((out/'manifest.json').read_bytes())}))
