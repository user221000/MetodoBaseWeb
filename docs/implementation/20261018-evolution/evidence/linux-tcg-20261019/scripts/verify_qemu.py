from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, struct, subprocess

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
TOOL=LAB/'tools/qemu'

def info(path):
    with path.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'bytes':path.stat().st_size,'sha256':digest}

def snapshot(root):
    files={};unsafe=[]
    for directory,dirs,names in os.walk(root,followlinks=False):
        for name in dirs+names:
            p=Path(directory)/name
            if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:unsafe.append(str(p))
        for name in names:
            p=Path(directory)/name;files[p.relative_to(root).as_posix()]=info(p)
    return dict(sorted(files.items())),unsafe

for p in (TOOL,*TOOL.parents):
    assert p.is_dir() and not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400,p
entries=json.loads((LAB/'evidence/qemu-7zip-member-inventory.json').read_text())
before,unsafe=snapshot(TOOL)
assert not unsafe
expected={x['Path'].replace('\\','/'):x for x in entries}
assert len(before)==len(expected)==3389 and set(before)==set(expected)
assert len(before)==len(set(p.casefold() for p in before))
differences=[]
for rel,entry in expected.items():
    if entry['Size'].isdigit() and before[rel]['bytes']!=int(entry['Size']):differences.append(rel)
assert not differences,differences
for name in ('qemu-system-x86_64.exe','qemu-img.exe'):
    pe=(TOOL/name).read_bytes();offset=struct.unpack_from('<I',pe,0x3c)[0]
    assert pe[:2]==b'MZ' and pe[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',pe,offset+4)[0]==0x8664
profile=LAB/'instance/tool-profile';profile.mkdir()
allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TMP','TEMP','LANG','LC_ALL'}
env={k:v for k,v in os.environ.items() if k.upper() in allowed}
env.update(APPDATA=str(profile),LOCALAPPDATA=str(profile),USERPROFILE=str(profile),HOME=str(profile))
results=[]
for command in ([str(TOOL/'qemu-system-x86_64.exe'),'--version'],[str(TOOL/'qemu-img.exe'),'--version'],
                [str(TOOL/'qemu-system-x86_64.exe'),'-accel','help']):
    result=subprocess.run(command,cwd=profile,env=env,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,(command,result.stderr)
    results.append({'command':command,'exit':result.returncode,'stdout':result.stdout.decode('utf-8','replace'),'stderr':result.stderr.decode('utf-8','replace')})
assert '11.1.0' in results[0]['stdout'] and 'tcg' in results[2]['stdout']
after,unsafe_after=snapshot(TOOL)
assert before==after and not unsafe_after
report={'finished_utc':datetime.now(timezone.utc).isoformat(),'files':before,'unsafe_before':unsafe,'unsafe_after':unsafe_after,
        'archive_paths_and_sizes_match':True,'unknown_nsis_sizes':[x['Path'] for x in entries if not x['Size'].isdigit()],
        'tool_runs':results,'stable_tools':True,'installer_executed':False,'global_path_or_registry_edited':False}
(LAB/'evidence/linux-tcg-qemu-verified.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(before),'runs':results,'stable':True},indent=2))
