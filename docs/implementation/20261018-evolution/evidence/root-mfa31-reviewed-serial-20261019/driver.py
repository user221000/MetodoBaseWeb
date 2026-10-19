from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

root=Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
ev=root/'docs/implementation/20261018-evolution/evidence'
serial=tmp/'metodobase-mfa31-reviewed-serial-20261019'
gate=tmp/'metodobase-mfa31-reviewed-serial-coverage-check-20261019'
control=tmp/'metodobase-mfa31-reviewed-serial-seal-v2-20261019'
private=tmp/'metodobase-mfa31-reviewed-serial-private-v2-20261019'
target=ev/'root-mfa31-reviewed-serial-20261019'
assert not target.exists() and not private.exists() and not control.exists()
sha=lambda blob:hashlib.sha256(blob).hexdigest()
encode=lambda value:(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
summary=json.loads((serial/'summary.private.json').read_bytes())
assert summary['head']=='de506b6077ba055587f02e7d839387e7f5c56f84'
assert summary['cases']==3057 and summary['exit']==0 and not summary['failures'] and not summary['timed_out']
assert summary['sources_packages_python_exact'] and summary['pip_before']==summary['pip_after']==0
assert summary['known_windows_skip_exact'] and len(summary['skips'])==1
cases=[]
for node in ET.parse(serial/'results.xml').findall('.//testcase'):
    assert node.find('error') is None and node.find('failure') is None
    cases.append({'case':node.get('classname','')+'::'+node.get('name',''),
                  'outcome':'skipped' if node.find('skipped') is not None else 'passed'})
assert len(cases)==len({row['case'] for row in cases})==3057
old=ev/'root-mfa31-terminal-sv-serial-diagnostic-20261019'
old_manifest=git('show','HEAD:'+str((old/'manifest.json').relative_to(root).as_posix()))
assert sha(old_manifest)=='e7474296a125900dc81a49de723b51d558e65465db59a7c777d927f1770cce6e'
old_cases=(old/'all-cases.STRUCTURAL.json').read_bytes()
old_manifest_rows=json.loads(old_manifest)
old_manifest_rows=old_manifest_rows.get('files',old_manifest_rows)
assert isinstance(old_manifest_rows,dict)
old_meta=old_manifest_rows['all-cases.STRUCTURAL.json']
assert len(old_cases)==old_meta['bytes'] and sha(old_cases)==old_meta['sha256']
old_ids={row['case'] for row in json.loads(old_cases)}
assert len(old_ids)==3047 and old_ids.issubset({row['case'] for row in cases})
preserved=json.loads((serial/'case-preservation.json').read_bytes());assert preserved['baseline3047_preserved'] and preserved['current3057_unique']
assert (serial/'before.json').read_bytes()==(serial/'after.json').read_bytes()
gate_receipt=json.loads((gate/'receipt.json').read_bytes());assert gate_receipt['exit']==0 and gate_receipt['head']==summary['head']
coverage_blob=(serial/'coverage.json').read_bytes();assert sha(coverage_blob)==gate_receipt['coverage_JSON_sha256']
critical={}
coverage=json.loads(coverage_blob)['files']
coverage={name.replace('\\','/'):value for name,value in coverage.items()}
for module in ['core/nutrition_validation.py','core/food_catalog.py','web/profile_schemas.py']:
    value=coverage[module]['summary']
    assert value['covered_lines']==value['num_statements'] and value['covered_branches']==value['num_branches']
    critical[module]=value
originals={}
for folder in [serial,gate]:
    for path in folder.iterdir():
        if path.is_file() and path.name!='.coverage':
            assert path.suffix.lower() not in {'.db','.sqlite','.sqlite3','.env'}
            originals[folder.name+'/'+path.name]=path.read_bytes()
control.mkdir()
acl_source=tmp/'metodobase-checkpoint125-evidence-seal-20261019/archive-acl.ps1'
acl=acl_source.read_text(encoding='utf8')
old_names="$names = @('terminal-sv-originals.zip','logging-originals.zip','fixture-clock-originals.zip')"
assert acl.count(old_names)==1
acl=acl.replace(old_names,"$names = @('serial-originals.zip')")
(control/'archive-acl.ps1').write_bytes(acl.encode())
def protect(mode):
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(control/'archive-acl.ps1'),
        '-Mode',mode,'-PrivateRoot',str(private)],capture_output=True)
    (control/('acl-'+mode+'.stdout.raw.log')).write_bytes(result.stdout)
    (control/('acl-'+mode+'.stderr.raw.log')).write_bytes(result.stderr)
    assert result.returncode==0,mode
    return json.loads(result.stdout.decode('utf-8-sig'))
created=protect('create');verified=protect('verify');assert verified['verified_before_payload']
archive=private/'serial-originals.zip';assert archive.stat().st_size==0
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED)as handle:
    for name,blob in originals.items():handle.writestr(name,blob)
with zipfile.ZipFile(archive)as handle:
    assert set(handle.namelist())==set(originals)
    for name,blob in originals.items():assert handle.read(name)==blob
final=protect('final')
for folder in [serial,gate]:
    for path in folder.iterdir():
        name=folder.name+'/'+path.name
        if name in originals:assert path.read_bytes()==originals[name]
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
blobs={'.gitattributes':b'* -text\n','driver.py':Path(__file__).read_bytes(),
    'summary.STRUCTURAL.json':encode({**{key:value for key,value in summary.items() if key!='failures'},
        'passed':3056,'failure_count':0,'error_count':0,'scope':'Schema31 web suite only;1358.688s is diagnostic duration, not a product SLO. No PostgreSQL, Redis, Chrome, Linux image or Actions execution here.'}),
    'all-cases.STRUCTURAL.json':encode(cases),'case-preservation.RAW.json':(serial/'case-preservation.json').read_bytes(),
    'before.RAW.json':(serial/'before.json').read_bytes(),'after.RAW.json':(serial/'after.json').read_bytes(),
    'pip-before.RAW.log':(serial/'pip-before.raw.log').read_bytes(),'pip-after.RAW.log':(serial/'pip-after.raw.log').read_bytes(),
    'coverage/receipt.RAW.json':(gate/'receipt.json').read_bytes(),'coverage/critical-modules.STRUCTURAL.json':encode(critical),
    'coverage/stdout.RAW.log':(gate/'stdout.raw.log').read_bytes(),'coverage/stderr.RAW.log':(gate/'stderr.raw.log').read_bytes(),
    'coverage/driver.py':(gate/'driver.py').read_bytes(),'archive-acl.ps1':(control/'archive-acl.ps1').read_bytes(),
    'source.json':encode({'source':summary['head'],'status':'PASS_WEB31_SERIAL_ONLY','private_original_files':{name:{'bytes':len(blob),'sha256':sha(blob)}for name,blob in originals.items()},
        'private_archive':{'basename':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'members':len(originals)},
        'archive_ACL_created_verified_before_payload':verified,'archive_ACL_final':final,
        'original_files_unchanged':True,'original_directory_ACL_at_creation_attested':False,
        'preparation_errata':[
            'First preflight assumed a direct manifest instead of the files map; failed before any writes, driver preserved.',
            'Next ACL script was blocked by the default PowerShell execution policy before any private directory existed. Its controls/logs/driver remain unchanged. This successor uses a process-only ExecutionPolicy switch; no machine or user policy is changed.'],
        'excluded':['binary .coverage database','pytest temporary directories and test databases'],
        'baseline3047_committed_manifest_sha256':sha(old_manifest),'exact_case_preservation':preserved,
        'venv_python_executable_hash_before_after':json.loads((serial/'before.json').read_bytes())['python_sha256'],
        'python_base_executable_hash_not_observed_in_this_serial_phase':True,
        'scope':'Serial and actual coverage gate only. Parallel mode runs separately; prior rejected results remain immutable.'})}
for name,blob in blobs.items():scan(blob,name)
target.mkdir();(target/'.gitattributes').write_bytes(blobs.pop('.gitattributes'))
for name,blob in blobs.items():
    path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as handle:handle.write(blob)
manifest={path.relative_to(target).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in target.rglob('*')if path.is_file()}
(target/'manifest.json').write_bytes(encode(manifest))
print(json.dumps({'prefix':str(target),'files':len(manifest)+1,'source_sha256':sha((target/'source.json').read_bytes()),'manifest_sha256':sha((target/'manifest.json').read_bytes()),'private_original_files':len(originals)}))
