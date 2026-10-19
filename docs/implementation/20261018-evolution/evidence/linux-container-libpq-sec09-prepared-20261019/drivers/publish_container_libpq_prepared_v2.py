from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
ROOT=LAB/'evidence/container-system-libpq-20261019'
WT=Path(r'F:\mb-container-pq-20261019')
DEST=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-container-libpq-sec09-prepared-20261019')
HEAD='d038f1c3860296f42ba41ce9ee64a8a4e6300ebc'
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-c','core.hooksPath=NUL','-C',str(WT),*args])
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain=v1','--untracked-files=all')
stat=json.loads((ROOT/'static-verification.json').read_text())
assert stat['check_count']==29
DEST.mkdir(exist_ok=True)
assert not any(DEST.iterdir()), 'Initial publication directory must be empty'
git_blob_files={}
def copy(p,relative):
    assert p.is_file() and not p.is_symlink()
    out=DEST/relative;out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(p.read_bytes())
for rel,expected in stat['candidate_files'].items():
    raw=git('show',HEAD+':'+rel)
    worktree_raw=(WT/rel).read_bytes()
    assert raw==worktree_raw.replace(b'\r\n',b'\n') and hashlib.sha256(worktree_raw).hexdigest()==expected['sha256']
    out=DEST/'candidate'/rel;out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(raw)
    git_blob_files[rel]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'worktree_bytes':len(worktree_raw),'worktree_sha256':expected['sha256'],'only_crlf_normalization_difference':raw!=worktree_raw}
for name in ['CONTRATO.md','primary-assets.json','runtime-os-expected.json','static-verification.json','static-verification-initial-before-no-remove.json','docker-runs.syntax-only.sh',
             'psycopg2-pyproject.toml','psycopg2-setup.cfg','psycopg2.metadata.json','psycopg2-binary.metadata.json','psycopg2.latest.metadata.json','psycopg2-binary.latest.metadata.json','setuptools.metadata.json']:
    copy(ROOT/name,name)
for p in (ROOT/'primary-docs').iterdir():
    if p.is_file():copy(p,Path('primary-docs')/p.name)
for name in ['metadata.json','stable.InRelease','updates.InRelease','security.InRelease']:
    copy(ROOT/'apt-primary'/name,Path('apt-primary')/name)
scripts=['prepare_container_libpq_primary.py','fetch_container_apt_primary.py','prepare_container_libpq_locks.py','verify_container_libpq_static.py',
         'verify_container_libpq_static_v2.py','record_container_libpq_primary_docs.py','record_container_libpq_primary_docs_v2.py','publish_container_libpq_prepared.py','publish_container_libpq_prepared_v2.py']
for name in scripts:copy(LAB/'scripts'/name,Path('drivers')/name)
diff=git('diff',HEAD+'^',HEAD,'--','Dockerfile')
(DEST/'Dockerfile.delta.patch').write_bytes(diff)
receipt={'frozen_utc':datetime.now(timezone.utc).isoformat(),'candidate_head':HEAD,'worktree':str(WT),'worktree_clean':True,
         'base_head':stat['base_head'],'exclusive_git_blob_files':git_blob_files,'static_worktree_files':stat['candidate_files'],'own_static_checks':29,
         'build':False,'qemu_started':False,'host_installation_or_global_config':False,
         'apt_signature_verification':'Pending Linux APT/keyring gate; raw InRelease is not a verified signature claim.',
         'primary_assets_retained_in_lab':str(ROOT),'asset_archives_not_copied_to_repository':True,
         'wheel_0_48_download_was_exploratory_unused_backend_requires_only_setuptools':True,
         'initial_harness_error':'Static V1 cp1252 read rejected UTF-8 Dockerfile; static V2 explicit UTF-8 passed. Publication V1 rejected CRLF checkout vs LF blob before copying any files; publication V2 verifies both hashes and publishes exact LF Git blobs. No source execution.',
         'raw_primary_docs_downloads':4,'primary_doc_urls_with_recorded_urllib403':4,
         'separate_native_cna_frozen_manifest_sha256':'9b35765886380a8bd9295c4d39285bdc04c16b4e2bc9bee3fd9d177850295797',
         'r18_sec09_open_until_actual_build_native_sca_and_pertinent_tests':True}
(DEST/'freeze.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(DEST/'.gitattributes').write_text('* -text\n',encoding='ascii')
files=[]
for p in sorted(DEST.rglob('*')):
    if p.is_file():files.append({'file':p.relative_to(DEST).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest=DEST/'evidence-manifest.json'
manifest.write_text(json.dumps({'status':'FROZEN static candidate; build not authorized in current Chrome window','candidate_head':HEAD,'file_count':len(files),'files':files},indent=2)+'\n',encoding='utf-8')
digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
(DEST/'evidence-manifest.sha256').write_text(digest+'  evidence-manifest.json\n',encoding='ascii')
for item in files:assert hashlib.sha256((DEST/item['file']).read_bytes()).hexdigest()==item['sha256']
print(json.dumps({'folder':str(DEST),'file_count':len(files),'manifest_sha256':digest,'static_receipt_sha256':hashlib.sha256((DEST/'static-verification.json').read_bytes()).hexdigest(),'contract_sha256':hashlib.sha256((DEST/'CONTRATO.md').read_bytes()).hexdigest()},indent=2))
