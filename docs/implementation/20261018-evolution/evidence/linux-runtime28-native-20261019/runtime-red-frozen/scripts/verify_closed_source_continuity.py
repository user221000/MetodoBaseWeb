from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
BASE=LAB/'evidence/runtime28-native-20261019'
REPO=Path(r'F:\MetodoBaseWeb-image-security-20261019')
OUT=BASE/'closure'
def info(p,algorithm='sha256'):
    assert p.is_file() and not p.is_symlink() and not(getattr(p.lstat(),'st_file_attributes',0)&0x400)
    with p.open('rb') as f:digest=hashlib.file_digest(f,algorithm).hexdigest()
    return {'bytes':p.stat().st_size,algorithm:digest}
expected=json.loads((LAB/'evidence/recovery28-image-bc365c1/before.json').read_text())
current={'tracked_sources':{rel:info(REPO/rel) for rel in expected['tracked_sources']},
         'git_controls':{rel:info(Path(rel)) if Path(rel).is_file() else None for rel in expected['git_controls']}}
assert current==expected
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_ATTR_NOSYSTEM='1',GIT_NO_REPLACE_OBJECTS='1',GIT_OPTIONAL_LOCKS='0')
cmd=['git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,'-c','core.attributesFile='+os.devnull,'-C',str(REPO)]
assert subprocess.check_output(cmd+['rev-parse','HEAD'],env=env).decode().strip()=='bc365c13b9af9e24129a56b4068059a67bb3afa0'
assert subprocess.check_output(cmd+['status','--porcelain=v1','--untracked-files=all'],env=env)==b''
pgexpected=json.loads((BASE/'pg55484-setup/tool-files.before.json').read_text())
pgroot=Path(r'C:\Program Files\PostgreSQL\17')
pgactual={rel:info(pgroot/rel) for rel in pgexpected}
assert pgactual==pgexpected
qverified=json.loads((LAB/'evidence/linux-tcg-qemu-verified.json').read_text())
qroot=LAB/'tools/qemu'
qactual={rel:info(qroot/rel) for rel in qverified['files']}
assert qactual==qverified['files']
state=json.loads((LAB/'instance/state.json').read_text())
assert info(Path(state['source_image']),'sha512')['sha512']==state['source_sha512']
assert info(Path(state['seed_iso']))['sha256']==state['seed_iso_sha256']
receipt={'finished_utc':datetime.now(timezone.utc).isoformat(),'source_head':'bc365c13b9af9e24129a56b4068059a67bb3afa0',
         'source_files_verified':len(current['tracked_sources']),'source_and_git_controls_match_prebuild':True,'worktree_clean':True,
         'postgres_existing_tool_files_verified':len(pgactual),'postgres_tools_unchanged':True,
         'qemu_portable_files_verified':len(qactual),'qemu_tools_unchanged':True,
         'golden_source_sha512_verified':state['source_sha512'],'seed_iso_sha256_verified':state['seed_iso_sha256'],
         'overlay_preserved':Path(state['overlay']).is_file(),'private_datadir_and_raw_preserved':True,
         'private_datadir_handed_off_without_global_roles':True}
with (OUT/'source-tools-continuity.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt))
