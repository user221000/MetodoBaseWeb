from pathlib import Path
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

tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');main=Path(r'F:\MetodoBaseWeb-execution-20261018')
root=Path(r'F:\mb-mfa31-compose-20261019');source=tmp/'metodobase-mfa31-composed-serial-20261019'
out=main/'docs/implementation/20261018-evolution/evidence/root-mfa31-composed-serial-diagnostic-20261019'
archive=tmp/'metodobase-mfa31-composed-serial-originals-private-20261019.zip'
assert not out.exists() and not archive.exists()
sha=lambda data:hashlib.sha256(data).hexdigest()
report=json.loads((source/'summary.private.json').read_bytes())
assert report['head']=='809eab28c40c112cb6e3c9d8caceebae28683abd' and report['exit']==1 and not report['timed_out']
assert report['cases']==3039 and len(report['failures'])==2 and len(report['skips'])==1
assert report['sources_packages_python_exact'] and report['pip_before']==report['pip_after']==0
before=(source/'before.json').read_bytes();after=(source/'after.json').read_bytes();assert before==after
old_dir=main/'docs/implementation/20261018-evolution/evidence/main-r23-r24-regression-20261019'
manifest=(old_dir/'manifest.json').read_bytes()
assert subprocess.check_output(['git','show','HEAD:'+str((old_dir/'manifest.json').relative_to(main)).replace('\\','/')],cwd=main)==manifest
old_raw=(old_dir/'serial.xml').read_bytes();meta=json.loads(manifest)['files']['serial.xml']
assert sha(old_raw)==meta['sha256'] and len(old_raw)==meta['bytes']
old=ET.fromstring(old_raw).findall('.//testcase');current_raw=(source/'results.xml').read_bytes()
current=ET.fromstring(current_raw).findall('.//testcase')
identity=lambda case:case.get('classname','')+'::'+case.get('name','')
baseline={identity(case) for case in old};actual={identity(case) for case in current}
assert len(baseline)==2598 and len(actual)==3039 and baseline.issubset(actual)
gate=subprocess.run([sys.executable,'-X','utf8','-B','tests/check_coverage.py',str(source/'coverage.json')],cwd=root,capture_output=True,timeout=30)
public={
 'driver.py':Path(__file__).read_bytes(),'coverage-gate.stdout.raw.log':gate.stdout,'coverage-gate.stderr.raw.log':gate.stderr,
 'after.json':after,'pip-after.raw.log':(source/'pip-after.raw.log').read_bytes(),
 'run-driver.py':(source/'driver.py').read_bytes(),
}
failures=[{'case':item['case'],'kind':item['kind'],'numeric_assertions':re.findall(r'assert [0-9]+ [=!<>]+ [0-9]+',item['message'])} for item in report['failures']]
summary={key:value for key,value in report.items() if key!='failures'}
summary.update(failures=failures,passed=3036,result='REJECTED_COMPOSED_SERIAL_TWO_TERMINAL_SESSION_LOGIN_FAILURES',
 previous_full_2598_case_ids_preserved=True,previous_unique_cases=2598,added_case_ids=441,
 coverage_gate_exit=gate.returncode,original_xml_sha256=sha(current_raw),
 before_reference={'path':'prepared-wave123-20261019/broad-serial-start/before.json','sha256':sha(before)},
 scope='Full serial diagnostic, not acceptance. The two original recovery boundary cases fail on new-password login401 at terminalSV. No assertions are changed.')
public['summary.STRUCTURAL.json']=(json.dumps(summary,indent=2)+'\n').encode()
public['all-cases.STRUCTURAL.json']=(json.dumps([{'case':identity(case),
 'outcome':next((kind for kind in ['failure','error','skipped'] if case.find(kind) is not None),'passed')} for case in current],indent=2)+'\n').encode()
private={name:(source/name).read_bytes() for name in ['results.xml','stdout.private.raw.log','stderr.private.raw.log','summary.private.json','coverage.xml','coverage.json']}
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as handle:
    for name,blob in sorted(private.items()):handle.writestr(name,blob)
public['private-originals.json']=(json.dumps({'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),
 'files':{name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in private.items()}},indent=2)+'\n').encode()
definition=next(node for node in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(node,ast.FunctionDef) and node.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
for name,blob in public.items():scan(blob,name)
out.mkdir();(out/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in public.items():(out/name).write_bytes(blob)
(out/'manifest.json').write_bytes((json.dumps({name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in public.items()},indent=2)+'\n').encode())
assert gate.returncode==0
print(json.dumps({'files':len(public),'manifest_sha256':sha((out/'manifest.json').read_bytes()),'coverage_gate_exit':gate.returncode,'baseline_cases_preserved':2598,'matrix_accepted':False}))
