"""Seal final local CI29 composition without copying extracted trees/probes twice."""
from pathlib import Path
import hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET
root=Path(r'F:\mb-r12-ci29-20261019');temporary=Path(r'C:\Users\Consu\AppData\Local\Temp');out=temporary/'metodobase-ci29-final-composition-20261019'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='4e875f99d5af4bb2a1ec4468de08e0fde948dfb7'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
summary=json.loads((out/'summary.json').read_bytes());assert all(row['exit']==0 for row in summary['results']) and summary['sources_packages_Git_Bash_stable']
review=json.loads((out/'guard/review.json').read_bytes());assert len(review['unauthorized_delta_canaries'])==25 and len(review['current_report_canaries'])==55 and len(review['current_inert_fixture_cases'])==27
cases=ET.parse(out/'unit.xml').findall('.//testcase');assert len(cases)==47 and not any(case.find(tag) is not None for case in cases for tag in ['failure','error','skipped'])
ev=root/'docs/implementation/20261018-evolution/evidence/ci-member-links29-composition-author-20261019';ev.mkdir(exist_ok=False);(ev/'.gitattributes').write_bytes(b'* -text\n')
for name in ['before.json','after.json','summary.json','pip.log','unit.xml','full-guard.stdout.log','full-guard.stderr.log','unit.stdout.log','unit.stderr.log']:shutil.copyfile(out/name,ev/name)
for name in ['review.json','canaries-raw.zip','historical.log']:
    shutil.copyfile(out/'guard'/name,ev/('guard-'+name))
for name in ['receipt.json','stdout.log','stderr.log']:shutil.copyfile(out/'guard/historical-ci28'/name,ev/('historical-'+name))
composition=temporary/'metodobase-ci29-archive-composition-20261019'
for name in ['cherry.log','conflicted-verifier.RAW.py','continue.log','receipt.json']:
    if (composition/name).is_file():shutil.copyfile(composition/name,ev/('composition-'+name))
for name in ['metodobase-ci29-archive-compose.py','metodobase-ci29-final-composition-run.py','metodobase-ci29-final-composition-seal.py']:shutil.copyfile(temporary/name,ev/name)
unchanged=['web','api','core','tests/e2e','.github/workflows/ci.yml']
subprocess.run(['git','diff','--exit-code','6c9347d226f57b967f4bb881ab005920f6c9b238','HEAD','--',*unchanged],cwd=root,check=True,capture_output=True)
sha=lambda value:hashlib.sha256(value).hexdigest()
manifest={'head':summary['head'],'scope':summary['scope'],'full_guard':{'distinct_reports':26,'unauthorized_delta_cases':25,'report_probes':55,'inert_process_cases':27,'historical_tree_blobs':4433},'unit_passed':47,'sources_packages_Git_Bash_stable':True,'sources':5347,'packages':89,'unchanged_since_real_browser6c':unchanged,'independent_archive_acceptance_at_seal':'Pending final independent proof; this receipt does not claim Actions/Linux or schema30.','files':{path.relative_to(ev).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(ev.rglob('*')) if path.is_file()}}
(ev/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
raw=sorted(path.relative_to(root).as_posix() for path in ev.rglob('*') if path.is_file())
for index in range(0,len(raw),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
for name in raw:assert subprocess.check_output(['git','show',':'+name],cwd=root)==(root/name).read_bytes(),name
assert set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1])==set(raw)
subprocess.run(['git','commit','-m','Seal local CI29 composition and exact historical archive verification'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'manifest_sha256':sha((ev/'manifest.json').read_bytes()),'RAW_blobs':len(raw),'unit_cases':47}))
