from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
BASE=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019')
DEST=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-runtime28-native-20261019/runtime-red-frozen')
source=BASE/'closure/source-tools-continuity.json'
assert json.loads(source.read_text())['source_and_git_controls_match_prebuild']
with (DEST/'closure/source-tools-continuity.json').open('xb') as f:f.write(source.read_bytes())
with (DEST/'scripts/seal_closed_runtime_phase.py').open('xb') as f:f.write(Path(__file__).read_bytes())
files=[]
for p in sorted(DEST.rglob('*')):
    assert not p.is_symlink()
    if not p.is_file():continue
    raw=p.read_bytes()
    if p.suffix in ['.json','.py','.md','.patch','.txt','.log']:
        raw.decode('utf-8',errors='strict')
    files.append({'file':p.relative_to(DEST).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
record={'sealed_utc':datetime.now(timezone.utc).isoformat(),'status':'FROZEN; real migration red, owned QEMU/network closed; PG handed off',
        'image_id':'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c',
        'source_head':'bc365c13b9af9e24129a56b4068059a67bb3afa0','files':files,'file_count':len(files),
        'late_continuity_receipt_included':True,'prior_publication_receipt_was_before_continuity_completed':True,
        'separate_native_openssl_manifest_sha256':'9b35765886380a8bd9295c4d39285bdc04c16b4e2bc9bee3fd9d177850295797',
        'native_symlink_cna_directories_unchanged':True,'no_web_startup_marker28_or_migrator_unset_acceptance':True}
manifest=DEST/'evidence-manifest.json'
with manifest.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
with (DEST/'evidence-manifest.sha256').open('x') as f:f.write(digest+'  evidence-manifest.json\n')
for item in files:
    p=DEST/item['file'];assert p.stat().st_size==item['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
print(json.dumps({'phase':str(DEST),'files':len(files),'manifest_sha256':digest,'bootstrap_v2_sha256':hashlib.sha256((DEST/'private_stdin_entrypoint_v2.py').read_bytes()).hexdigest(),
                  'source_migration_sha256':hashlib.sha256((DEST/'c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py').read_bytes()).hexdigest()}))
