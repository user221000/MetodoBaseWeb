from pathlib import Path
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
main=Path(r'F:\MetodoBaseWeb-execution-20261018')
root=Path(r'F:\mb-saas-observability-20261019')
out=main/'docs/implementation/20261018-evolution/evidence/root-r17-observability-author-20261019'
assert not out.exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
head='b50058280b9e4989799732b81a8a10292ebaba92'
base='bd34893c4b6f806041b0cc6b7f156e9286886748'
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
blobs={};private={}
names=git('diff','--name-only','-z',base,head).decode().split('\0')[:-1]
assert len(names)==7
existing=set(git('ls-tree','-r','--name-only','-z',base).decode().split('\0')[:-1])
for name in names:
    blobs['source/after-GitLF/'+name]=git('show',head+':'+name)
    if name in existing:blobs['source/before-GitLF/'+name]=git('show',base+':'+name)

phases={}
for label,folder in [('initial-freeze','metodobase-saas-observability-frozen-20261019'),
                     ('boundary-freeze','metodobase-r17-boundary-frozen-20261019')]:
    source=tmp/folder
    for name in ['driver.py','before.json','after.json','pip-before.raw.log','pip-after.raw.log','summary.json']:
        blobs[label+'/'+name]=(source/name).read_bytes()
    assert (source/'before.json').read_bytes()==(source/'after.json').read_bytes()
    summary=json.loads((source/'summary.json').read_bytes());assert summary['exit']==0
    phases[label]={'cases':summary['cases'],'exit':0,'role':'author replay; overlapping cases are not summed'}
    for name in ['pytest.xml','pytest.stdout.private.raw.log','pytest.stderr.private.raw.log']:
        private[folder+'/'+name]=(source/name).read_bytes()

xmls={label:tmp/('metodobase-saas-observability-'+label+'-20261019.xml') for label in ['before','after','mounted','final','parent-fixed-harness']}
xmls['boundary-security-replay']=tmp/'metodobase-r17-root-boundary-replay-20261019/review.xml'
for label,path in xmls.items():
    raw=path.read_bytes();cases=ET.fromstring(raw).findall('.//testcase')
    result={'RAW_sha256':sha(raw),'cases':len(cases),
     'passed':sum(not any(c.find(t) is not None for t in ['failure','error','skipped']) for c in cases),
     'failed':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),
     'skipped':sum(c.find('skipped') is not None for c in cases),
     'identities':[c.get('classname','')+'::'+c.get('name','') for c in cases]}
    phases[label]=result;private[path.name]=raw
    log=path.with_suffix('.private.log')
    if log.exists():private[log.name]=log.read_bytes()
    blobs['phases/'+label+'.STRUCTURAL.json']=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
assert phases['boundary-security-replay']['cases']==24 and phases['boundary-security-replay']['passed']==24
for folder in ['metodobase-saas-observability-source-change-20261019','metodobase-saas-observability-source-change-v2-20261019',
               'metodobase-saas-observability-style-20261019','metodobase-r17-private-boundary-fix-20261019']:
    for path in (tmp/folder).iterdir():
        assert path.is_file()
        blobs['preconditions/'+folder+'/'+path.name]=path.read_bytes()
blobs['driver.py']=Path(__file__).read_bytes()
blobs['limitations.json']=(json.dumps({
 'source':head,'base':base,'author_only':True,'independent_review':'Separate immutable before and same-driver peer replay; not reattributed here.',
 'phases':phases,
 'initial_before_harness':'METRICS_ENABLED inherited false affected four collection cases; not all initial red cases are causal product failures. Parent-fixed-harness phase uses final opt-in harness.',
 'writer1':'Stopped on ambiguous indentation guard before factory writes. A subsequent interim test ran after that failure and does not represent final mounted product.',
 'writer2':'Factory edits succeeded, RAW-before filename flattening failed for Windows separators. No complete original RAW-before claim; original Git blobs are preserved explicitly as GitLF.',
 'style':'Four-file AST equality recorded; separate trailing blank-only fix after private-header delta also AST equal.',
 'scope':'Actual ASGI factories with isolated SQLite metadata; no PostgreSQL, browser, external provider, distributed aggregation, full body streaming or production SLO claim.'},ensure_ascii=False,indent=2)+'\n').encode())
archive=tmp/'metodobase-r17-author-originals-private-20261019.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as handle:
    for name,blob in sorted(private.items()):handle.writestr(name,blob)
blobs['private-originals-receipt.json']=(json.dumps({'private_archive':str(archive),'bytes':archive.stat().st_size,
 'sha256':sha(archive.read_bytes()),'files':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in sorted(private.items())}},indent=2)+'\n').encode())
for name,blob in blobs.items():scan(blob,name)
manifest={name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in sorted(blobs.items())}
out.mkdir();(out/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in blobs.items():
    path=out/name;assert path.resolve().is_relative_to(out.resolve())
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
(out/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
assert all((out/n).read_bytes()==b for n,b in blobs.items())
print(json.dumps({'directory':str(out),'files':len(blobs),'manifest_sha256':sha((out/'manifest.json').read_bytes()),'private_originals_not_published':True}))
