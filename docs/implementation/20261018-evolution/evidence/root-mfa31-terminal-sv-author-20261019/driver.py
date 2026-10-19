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

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');main=Path(r'F:\MetodoBaseWeb-execution-20261018')
root=Path(r'F:\mb-mfa31-terminal-sv-20261019');out=main/'docs/implementation/20261018-evolution/evidence/root-mfa31-terminal-sv-author-20261019'
head='6a75d096ea3d63d9e78c76d33b7e243160b23364';base='809eab28c40c112cb6e3c9d8caceebae28683abd'
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
sha=lambda blob:hashlib.sha256(blob).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain','--untracked-files=no')
assert not out.exists()
public={};private={};phases={}
for phase in ['before','after']:
    source=tmp/('metodobase-mfa31-terminal-sv-'+phase+'-20261019')
    summary=json.loads((source/'summary.json').read_bytes());phases[phase]=summary
    assert summary['cases']==14 and summary['sources_packages_python_exact']
    assert (source/'before.json').read_bytes()==(source/'after.json').read_bytes()
    for name in ['driver.py','before.json','after.json','pip-before.raw.log','pip-after.raw.log','summary.json']:
        public[phase+'/'+name]=(source/name).read_bytes()
    cases=ET.parse(source/'results.xml').findall('.//testcase')
    public[phase+'/cases.STRUCTURAL.json']=(json.dumps([{'case':case.get('classname','')+'::'+case.get('name',''),
     'outcome':next((kind for kind in ['failure','error','skipped'] if case.find(kind) is not None),'passed')} for case in cases],indent=2)+'\n').encode()
    for name in ['results.xml','stdout.private.raw.log','stderr.private.raw.log']:
        private[phase+'/'+name]=(source/name).read_bytes()
assert phases['before']['passed']==4 and phases['before']['failed']==10 and phases['after']['passed']==14
assert phases['before']['test_source_sha256']==phases['after']['test_source_sha256']
for prefix in ['metodobase-mfa31-terminal-sv-source-change-20261019','metodobase-mfa31-terminal-sv-freeze-20261019','metodobase-terminal-sv-compose-20261019']:
    for path in (tmp/prefix).iterdir():
        assert path.is_file();public[prefix+'/'+path.name]=path.read_bytes()
for name in ['web/services/mfa_service.py','web/static/js/mfa-ui.js','tests/test_mfa31_terminal_session_version.py']:
    public['source/after-GitLF/'+name]=git('show',head+':'+name)
    if name!='tests/test_mfa31_terminal_session_version.py':public['source/before-GitLF/'+name]=git('show',base+':'+name)
public['driver.py']=Path(__file__).read_bytes()
archive=tmp/'metodobase-mfa31-terminal-sv-originals-private-20261019.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as handle:
    for name,blob in private.items():handle.writestr(name,blob)
public['private-originals.json']=(json.dumps({'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),
 'files':{name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in private.items()}},indent=2)+'\n').encode()
public['source.json']=(json.dumps({'candidate':head,'base':base,'proposed_finding':'SEC15; new allocation must be checked against registry before insertion.',
 'same_driver_before_after':14,'before_failed':10,'before_controls_passed':4,'after_passed':14,
 'new_unique_HTTP_cases':8,'legacy_boundary_replays':2,'existing_control_replays':4,'old_assertions_changed':0,
 'test_sha256':phases['after']['test_source_sha256'],'scope':'Author scoped only; security peer and new full serial/n2 pending. No wrap/decrement of SV, no factor bypass, no schema change. Existing controls retain their original fixture provenance.',
 'sources_packages_python_quiet_each_phase':True,'sources':10179,'packages':89,'pip_each_phase':0},indent=2)+'\n').encode()
definition=next(node for node in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(node,ast.FunctionDef) and node.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
for name,blob in public.items():scan(blob,name)
out.mkdir();(out/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in public.items():
    path=out/name;assert path.resolve().is_relative_to(out.resolve())
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
(out/'manifest.json').write_bytes((json.dumps({name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in public.items()},indent=2)+'\n').encode())
print(json.dumps({'files':len(public),'manifest_sha256':sha((out/'manifest.json').read_bytes()),'source_sha256':sha(public['source.json']),'independent_acceptance':False}))
