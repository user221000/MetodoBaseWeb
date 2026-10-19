from pathlib import Path
import hashlib,json,re,shutil,xml.etree.ElementTree as ET
root=Path(r'F:\MetodoBaseWeb-execution-20261018');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');source=tmp/'metodobase-main-r23-r24-regression-first-20261019';dest=root/'docs/implementation/20261018-evolution/evidence/main-r23-r24-regression-20261019';sha=lambda b:hashlib.sha256(b).hexdigest()
report=json.loads((source/'summary.private.json').read_bytes());assert report['head']=='eea8f773fba9b7f92241958139fcefa23b9ee1d4' and report['coverage_exit']==0 and report['sources_packages_stable'] and report['pip_exit']==0
before=json.loads((source/'before.json').read_bytes());after=json.loads((source/'after.json').read_bytes());assert before==after and len(before['files'])==9542 and len(before['packages'])==89
preserved=json.loads((source/'baseline-case-preservation.json').read_bytes());assert all(r['baseline_unique_ids']==2492 and r['current_unique_ids']==2598 and not r['missing'] for r in preserved.values())
for result in report['results']:
    assert result['exit']==0 and not result['timed_out'] and result['cases']==2598 and not result['failures'] and len(result['skips'])==1
    skip=result['skips'][0];assert (skip['module'],skip['case'])==('tests.test_object_storage','test_symlink_cannot_redirect_a_private_document')
    xml=ET.fromstring((source/(result['mode']+'.xml')).read_bytes());assert len(xml.findall('.//testcase'))==2598 and len(xml.findall('.//skipped'))==1 and not xml.findall('.//failure') and not xml.findall('.//error')
def sensitive(blob):
    for m in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=m.start()
        if p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p]):return True
    return bool(re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob))
dest.mkdir(exist_ok=False);(dest/'.gitattributes').write_bytes(b'* -text\n');private=[];mapping={}
for path in source.iterdir():
    if not path.is_file():continue
    blob=path.read_bytes()
    if path.name.startswith('.coverage-'):
        private.append({'name':path.name,'sha256':sha(blob),'bytes':len(blob),'reason':'Coverage SQLite internal binary retained locally; public XML/JSON and gate logs published.'});continue
    assert not sensitive(blob),path
    name=path.name.replace('.private','');assert name!='summary.json' or path.name=='summary.private.json'
    if name=='summary.json':name='run-summary.raw.json'
    (dest/name).write_bytes(blob);mapping[name]={'private_source_name':path.name,'RAW_sha256':sha(blob),'public_sha256':sha(blob),'byte_exact':True}
for name in ['metodobase-main-r23-r24-regression.py','metodobase-main-r23-r24-regression-prepare.py',Path(__file__).name]:
    blob=(tmp/name).read_bytes();assert not sensitive(blob);(dest/name).write_bytes(blob)
summary={'head':report['head'],'results':[{**r,'passed':r['cases']-len(r['skips'])} for r in report['results']],'coverage_gate_exit':0,'coverage_required_modules':'nutrition_validation,food_catalog,profile_schemas:100%lines/branches','baseline2492case_ids_preserved_each_mode':True,'sources':9542,'packages':89,'before_after_exact':True,'pip_before_after_exit':0,'RAW_mapping':mapping,'private_binary_receipts':private,'scope':'Composed MAIN R23/R24/SEC11 schema30 Windows synthetic broad gates only. One known Windows symlink skip per mode; no PG/Redis/Linux/Actions/image/provider/SLO claim. No source or criterion relaxed.'}
(dest/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
manifest={'files':{p.relative_to(dest).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file()}}
(dest/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode());print(json.dumps({'manifest_sha256':sha((dest/'manifest.json').read_bytes()),'summary_sha256':sha((dest/'summary.json').read_bytes()),'files':len(manifest['files'])+1,'head':report['head'],'passed_each_mode':2597,'known_skip_each_mode':1}))
