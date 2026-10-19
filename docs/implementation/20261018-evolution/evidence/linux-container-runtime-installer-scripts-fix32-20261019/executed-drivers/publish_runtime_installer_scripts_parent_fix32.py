from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');SRC=LAB/'evidence/runtime-installer-scripts-parent-fix32-20261019'
MAIN=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence');DST=MAIN/'linux-container-runtime-installer-scripts-fix32-20261019'
BACKEND=MAIN/'backend-container-installer-static-review-20261019';WT=Path(r'F:\mb-container-runtime-tools-20261019')
def sha(b):return hashlib.sha256(b).hexdigest()
def cp(source,target):
    assert source.is_file() and not source.is_symlink() and not target.exists();data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==sha(data)
assert not DST.exists();DST.mkdir()
input_paths=[BACKEND/'test_runtime_installer_paths.py',BACKEND/'freeze.json']+[WT/rel for rel in subprocess.check_output(['git','-C',str(WT),'ls-files','*lock'],text=True).splitlines()]
before={str(p):sha(p.read_bytes()) for p in input_paths};assert len(input_paths)==14
assert before[str(input_paths[0])]=='67388a1948844492550986f63fb9eab776c8b86a92a94ccf5be26adc81e630f4'
assert before[str(input_paths[1])]=='cd6cbf607fd161b253b327210b7c2d0b85c21e98eed69a79071b64a7373a3bab'
freeze=json.loads((SRC/'freeze.json').read_text());assert not subprocess.check_output(['git','-C',str(WT),'status','--porcelain']);assert freeze['head']==subprocess.check_output(['git','-C',str(WT),'rev-parse','HEAD'],text=True).strip()
for source in sorted(SRC.rglob('*')):
    if source.is_file():cp(source,DST/source.relative_to(SRC))
cp(input_paths[0],DST/'independent-driver/test_runtime_installer_paths.py');cp(input_paths[1],DST/'prior-independent-rejection/freeze.json')
for name in ['verify_runtime_installer_scripts_parent_fix32.py','publish_runtime_installer_scripts_parent_fix32.py']:cp(LAB/'scripts'/name,DST/'executed-drivers'/name)
cp(WT/'Dockerfile',DST/'Dockerfile.checkout')
after={str(p):sha(p.read_bytes()) for p in input_paths};assert before==after
(DST/'publication-integrity.json').write_text(json.dumps({'captured_utc':datetime.now(timezone.utc).isoformat(),'source_quiet':True,'inputs_before':before,'inputs_after':after,'candidate_head':freeze['head'],'candidate_clean':True,'scope':'New evidence prefix only. Previous freezes, source locks and MAIN product files unchanged. No build, image/VM, network or cleanup execution.'},indent=2)+'\n',encoding='utf-8')
assert '\ufffd' not in (DST/'REVISION.md').read_text(encoding='utf-8')
rows=[{'path':p.relative_to(DST).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(DST.rglob('*')) if p.is_file()]
manifest={'sealed_utc':datetime.now(timezone.utc).isoformat(),'root':str(DST),'head':freeze['head'],'files':rows,'file_count_excluding_manifest':len(rows),'scope':'Frozen correction evidence. Independent 3-case driver repeated unchanged, no actual image acceptance.'};data=(json.dumps(manifest,indent=2)+'\n').encode();(DST/'manifest.json').write_bytes(data);digest=sha(data);(DST/'manifest.sha256').write_text(digest+'  manifest.json\n',encoding='ascii')
for row in rows:assert sha((DST/row['path']).read_bytes())==row['sha256']
receipt={'folder':str(DST),'head':freeze['head'],'manifest_sha256':digest,'report_sha256':sha((DST/'REVISION.md').read_bytes()),'files_excluding_manifest_and_sidecar':len(rows),'frozen':True,'no_image_or_vm_execution':True};(LAB/'evidence/runtime-installer-scripts-parent-fix32-publication.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt,indent=2))
