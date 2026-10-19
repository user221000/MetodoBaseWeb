from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

root=Path(r'F:\MetodoBaseWeb-execution-20261018')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
ev=Path('docs/implementation/20261018-evolution/evidence')
base='edf267ca9f44228620535c8a661c3196598c1b8d'
git=lambda *args,cwd=root:subprocess.check_output(['git','--no-replace-objects',*args],cwd=cwd)
sha=lambda data:hashlib.sha256(data).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
definition=next(n for n in ast.parse((tmp/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'preserved-scanner','exec'))
contents={};provenance=[]
def add(name,blob,source):
    name=Path(name).as_posix();scan(blob,name)
    assert name.startswith(ev.as_posix()+'/') and '..' not in Path(name).parts
    assert name not in contents
    contents[name]=blob
    provenance.append({'path':name,'bytes':len(blob),'sha256':sha(blob),'source':source})
wt=Path(r'F:\mb-mfa31-contract-clock-keyword-20261019')
commit='d0121919e6207dd76bbb8c0c9bff5966c6930d3f'
assert sha(git('show',commit+':'+(ev/'backend-mfa31-contract-keyword-20261019/source.json').as_posix(),cwd=wt))=='2a737c46d05448acbafa9f097fcd606ea7f16d90f46de0c0264e435bf51b9cb7'
names=git('diff','--name-only','-z',commit+'^',commit,'--',ev.as_posix(),cwd=wt).decode().split('\0')[:-1]
for name in names:
    blob=git('show',commit+':'+name,cwd=wt)
    assert (wt/name).read_bytes()==blob
    add(name,blob,{'git_commit':commit,'git_raw_exact':True})
qa=Path(r'F:\mb-qa-contract31-clock-keyword-20261019')/ev/'qa-mfa31-contract-clock-independent-20261019'
manifest_sha='cac2e23365f4304d08929277addf1507378e5c271b95b2378e9a588921cb0e71'
assert sha((qa/'manifest.json').read_bytes())==manifest_sha
assert sha((qa/'source.json').read_bytes())=='dd6fd06c03da76a885cba1f1bf0e223ad46f334b20ae00b830aea5fd89bb884e'
members=json.loads((qa/'manifest.json').read_bytes())
for name,row in members.items():
    assert set(row)=={'bytes','sha256'}
    path=qa/name;assert path.resolve().is_relative_to(qa.resolve())
    blob=path.read_bytes();assert len(blob)==row['bytes'] and sha(blob)==row['sha256']
for path in sorted(qa.rglob('*')):
    if path.is_file():add(ev/qa.name/path.relative_to(qa),path.read_bytes(),{'producer_manifest_sha256':manifest_sha})
prepared=ev/'prepared-wave125-followup-20261019'
extras={'driver.py':Path(__file__).read_bytes(),'.gitattributes':b'* -text\n'}
folder=tmp/'metodobase-mfa31-reviewed-common-compose-20261019'
for path in folder.iterdir():
    assert path.is_file();extras['common31-compose/'+path.name]=path.read_bytes()
folder=tmp/'metodobase-mfa31-reviewed-common-preflight-20261019'
assert json.loads((folder/'summary.json').read_bytes())['parser_cases']==205
for path in folder.rglob('*'):
    if path.is_file():extras['common31-preflight/'+path.relative_to(folder).as_posix()]=path.read_bytes()
for name in ['metodobase-mfa31-reviewed-broad-prepare.py','metodobase-mfa31-reviewed-regression.py']:
    extras['broad31/'+name]=(tmp/name).read_bytes()
extras['root-import-preflight-erratum.json']=(json.dumps({
    'scope':'Preparation failures before the first MAIN import mutation',
    'first_failure':'Missing PurePosixPath dependency required by preserved recursive archive scanner; added import only.',
    'first_driver_RAW_sha256':sha((tmp/'metodobase-checkpoint125-import-pre-scan-dependency-failure.py').read_bytes()),
    'second_failure':'Closed c538 public driver had a synthetic live-key-shaped canary literal; scanner stopped before writes.',
    'resolution':'Ops produced separately sealed runtime31-c538-runtime72-diagnostic-public-20261019 with projected canary and executed RAW SHA link. Original closure unchanged.',
    'rejected_second_driver_RAW_preserved':False,
    'limit':'No reconstruction or claim of exact second failed driver RAW; its rejection is recorded in the tool transcript.'},indent=2)+'\n').encode()
for name,blob in extras.items():add(prepared/name,blob,{'kind':'root-followup-preparation'})
add(prepared/'import-ledger.json',(json.dumps({'base':base,'imports':provenance},indent=2)+'\n').encode(),{'kind':'ledger'})
manifest={Path(name).relative_to(prepared).as_posix():{'bytes':len(blob),'sha256':sha(blob)} for name,blob in contents.items() if Path(name).is_relative_to(prepared)}
add(prepared/'manifest.json',(json.dumps(manifest,indent=2)+'\n').encode(),{'kind':'manifest'})
for name,blob in sorted(contents.items(),key=lambda item:(Path(item[0]).name!='.gitattributes',item[0])):
    path=root/name
    assert not path.exists(),path
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as handle:handle.write(blob)
receipt={'base':base,'files':{name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in contents.items()}}
out=tmp/'metodobase-checkpoint125-delta-result.json';assert not out.exists()
out.write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps({'files':len(contents),'bytes':sum(map(len,contents.values())),'receipt':str(out)}))
