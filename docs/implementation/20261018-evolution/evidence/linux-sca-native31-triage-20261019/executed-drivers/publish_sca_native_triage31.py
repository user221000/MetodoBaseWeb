from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');SRC=LAB/'evidence/sca-native-triage31-20261019'
EVIDENCE=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence')
DST=EVIDENCE/'linux-sca-native31-triage-20261019';CANDIDATE=EVIDENCE/'linux-container-runtime-installer-removal-20261019'
assert not DST.exists() and not CANDIDATE.exists();DST.mkdir();CANDIDATE.mkdir()
def sha(data):return hashlib.sha256(data).hexdigest()
def copy(source,target):
    assert source.is_file() and not source.is_symlink() and not target.exists()
    data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==sha(data)
    return {'source':str(source),'file':target.as_posix(),'bytes':len(data),'sha256':sha(data)}
def under(path,root):return path.resolve().is_relative_to(root.resolve())
for root in [SRC,DST,CANDIDATE]:
    for path in [root,*root.parents]:assert not path.is_symlink(),path
excluded=[];published=[]
for source in sorted(SRC.rglob('*')):
    if not source.is_file():continue
    assert under(source,SRC) and not source.is_symlink()
    name=source.name
    if name=='debian-security-tracker.current.raw.json' or name.endswith(('.deb','.whl','.tar.xz','.tar.gz')):
        excluded.append({'path':str(source),'relative_to_lab_triage':source.relative_to(SRC).as_posix(),'bytes':source.stat().st_size,'sha256':sha(source.read_bytes()),'scope':'Large public primary artifact retained in owned LAB; URL/headers/date in accompanying receipts. Not executed.'});continue
    published.append(copy(source,DST/source.relative_to(SRC)))
(DST/'large-primary-artifact-pointers.json').write_text(json.dumps(excluded,indent=2)+'\n',encoding='utf-8')
raws={
 'native811.json':LAB/'evidence/runtime28-native-20261019/native/native.json',
 'scan-full.json':LAB/'evidence/os-audit-bc365c1/results/scan.json',
 'scan-summary.json':LAB/'evidence/os-audit-bc365c1/results/scan-summary.json',
 'runtime-inventory55.json':LAB/'evidence/recovery28-image-bc365c1/runtime-inventory.json',
 'prior-os-matrix73.json':LAB/'evidence/os-audit-abd559a/triage-matrix/matrix-73.json',
 'debian-openssl-installed-changelog.txt':LAB/'evidence/os-audit-abd559a/triage-primary/debian-openssl-installed-changelog.raw.txt',
 'openssl-backport-comparison.json':LAB/'evidence/os-audit-abd559a/triage-primary/openssl-backport-comparison.json',
 'openssl-debian-backports-selection.json':LAB/'evidence/os-audit-abd559a/triage-primary/openssl-debian-backports-selection.json',
 'xz-ghsa-api.raw.txt':LAB/'evidence/os-audit-abd559a/triage-primary/xz-ghsa-api.raw.txt',
 'official-python-source-Dockerfile.txt':LAB/'evidence/image-pip-base-primary-20261019/official-python31215-source-Dockerfile.txt',
 'base-registry-provenance.json':LAB/'evidence/image-pip-base-primary-20261019/python31215-registry-provenance.json',
}
quiet_before={str(p):sha(p.read_bytes()) for p in raws.values()}
for name,source in raws.items():copy(source,DST/'reused-primary'/name)
openssl=EVIDENCE/'linux-runtime28-native-20261019/native-openssl-sec09'
for source in sorted(openssl.glob('CVE-*.json')):copy(source,DST/'reused-primary/openssl-cna13'/source.name)
drivers=['prepare_sca_native_triage31.py','audit_triage31_build_vendors.py','fetch_triage31_primary_expansion.py','analyze_triage31_source_and_vendors.py','analyze_triage31_source_and_vendors-v2.py','analyze_triage31_source_and_vendors-v3.py','inspect_triage31_predicted_debs.py','fetch_triage31_component_sources.py','consolidate_sca_native_triage31.py','consolidate_sca_native_triage31-v2.py','audit_triage31_ensurepip_asset.py','publish_sca_native_triage31.py']
for name in drivers:copy(LAB/'scripts'/name,DST/'executed-drivers'/name)
proof=LAB/'evidence/runtime-installer-removal-20261019-v2'
for source in sorted(proof.rglob('*')):
    if source.is_file():copy(source,CANDIDATE/source.relative_to(proof))
initial=LAB/'evidence/runtime-installer-removal-20261019'
for source in sorted(initial.rglob('*')):
    if source.is_file():copy(source,CANDIDATE/'initial-harness-failure'/source.relative_to(initial))
for name in ['verify_runtime_installer_removal31.py','verify_runtime_installer_removal31-v2.py']:copy(LAB/'scripts'/name,CANDIDATE/'executed-drivers'/name)
for name in ['runtime-installer-dependency-review.json','pip-vendor-function-review.json','build-vendor-inventory.json','ensurepip-asset-inventory-and-osv.json']:
    copy(SRC/name,CANDIDATE/'support'/name)
wt=Path(r'F:\mb-container-runtime-tools-20261019');head=subprocess.check_output(['git','-C',str(wt),'rev-parse','HEAD'],text=True).strip();assert head=='af548f71a8a763ba523853e85903a9ab8cf2b0a7';assert not subprocess.check_output(['git','-C',str(wt),'status','--porcelain'],text=True)
docker=subprocess.check_output(['git','-C',str(wt),'show','HEAD:Dockerfile']);assert sha(docker)=='c923b779d7e6c97c5ac180c68a7373a2b3fc2f2854453c0bff6f4ce07e6a2ea1'
copy(wt/'Dockerfile',CANDIDATE/'Dockerfile.checkout')
quiet_after={str(p):sha(p.read_bytes()) for p in raws.values()};assert quiet_before==quiet_after
integrity={'captured_utc':datetime.now(timezone.utc).isoformat(),'source_quiet':True,'raw_hashes_before':quiet_before,'raw_hashes_after':quiet_after,'candidate_head':head,'candidate_clean':True,'candidate_docker_git_sha256':sha(docker),'large_artifacts_retained_in_lab':len(excluded),'scope':'Only new evidence directories in MAIN. Existing frozen phases, source locks, images and source worktrees untouched; no QEMU/Docker or product startup.'}
for target in [DST,CANDIDATE]:
    (target/'publication-input-integrity.json').write_text(json.dumps(integrity,indent=2)+'\n',encoding='utf-8')
    for name in ['REVISION.md','CONTRATO.md']:
        if (target/name).exists():
            text=(target/name).read_text(encoding='utf-8');assert '\ufffd' not in text and 'Revisi?n' not in text
receipts=[]
for target in [DST,CANDIDATE]:
    rows=[]
    for p in sorted(target.rglob('*')):
        if p.is_file():rows.append({'path':p.relative_to(target).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
    manifest={'sealed_utc':datetime.now(timezone.utc).isoformat(),'root':str(target),'files':rows,'file_count_excluding_manifest':len(rows),'scope':'Frozen evidence. Manifest excludes itself and its SHA sidecar only. Technical claims retain their per-scope limits.'}
    data=(json.dumps(manifest,indent=2)+'\n').encode();(target/'manifest.json').write_bytes(data);digest=sha(data);(target/'manifest.sha256').write_text(digest+'  manifest.json\n',encoding='ascii')
    for row in rows:assert sha((target/row['path']).read_bytes())==row['sha256']
    report='REVISION.md' if (target/'REVISION.md').exists() else 'CONTRATO.md'
    receipts.append({'folder':str(target),'files_excluding_manifest_and_sidecar':len(rows),'manifest_sha256':digest,'report':report,'report_sha256':sha((target/report).read_bytes()),'total_bytes':sum(r['bytes'] for r in rows)})
receipt={'sealed_utc':datetime.now(timezone.utc).isoformat(),'frozen':True,'directories':receipts,'candidate_head':head,'no_qemu_or_build':True};path=LAB/'evidence/sca-native-triage31-publication-receipt.json';assert not path.exists();path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt,indent=2))
