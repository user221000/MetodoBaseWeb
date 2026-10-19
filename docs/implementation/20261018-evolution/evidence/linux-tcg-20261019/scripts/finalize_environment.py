from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
sys.path.insert(0,str(LAB/'scripts'))
import lab_control
state=lab_control.state()
health=json.loads((LAB/'evidence/linux-tcg-guest-health-final.json').read_text())
assert health['container_smoke_exit']==0 and health['guest']['redis_ping_set_get_delete_own_ttl_key']
original=json.loads((LAB/'evidence/linux-tcg-qemu-verified.json').read_text())

def digest(path,algorithm='sha256'):
    with path.open('rb') as stream:return hashlib.file_digest(stream,algorithm).hexdigest()

actual={};unsafe=[];tool=LAB/'tools/qemu'
for directory,dirs,files in os.walk(tool,followlinks=False):
    for name in dirs+files:
        p=Path(directory)/name
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:unsafe.append(str(p))
    for name in files:
        p=Path(directory)/name;actual[p.relative_to(tool).as_posix()]={'bytes':p.stat().st_size,'sha256':digest(p)}
assert not unsafe and actual==original['files']
base=Path(state['source_image'])
base_sha=digest(base,'sha512');assert base_sha==state['source_sha512']
assert getattr(base.stat(),'st_file_attributes',0)&1,'Golden image must remain readonly'
assert digest(LAB/'downloads/qemu-w64-setup-20260811.exe','sha512')==(LAB/'downloads/qemu-w64-setup-20260811.sha512').read_text().split()[0]
assert digest(Path(r'C:\Program Files\7-Zip\7z.exe'))=='83967f1b02b43c4efeda302795722c809e0e81b8307de73558d10484d5676a7d'
qmp=lab_control.qmp(state,['query-status','query-memory-size-summary','query-named-block-nodes'])
assert qmp['query-status']['return']['running'] and qmp['query-memory-size-summary']['return']['base-memory']==2147483648
nodes=qmp['query-named-block-nodes']['return']
base_nodes=[n for n in nodes if n.get('drv')=='qcow2' and Path(n.get('image',{}).get('filename','')).resolve()==base.resolve()]
assert len(base_nodes)==1 and base_nodes[0]['ro'] is True
for p in (LAB,tool,base,Path(state['overlay']),Path(state['seed_iso']),*(LAB/'instance/ssh').parents):
    assert not p.is_symlink() and not(getattr(p.lstat(),'st_file_attributes',0)&0x400)
report={'captured_utc':datetime.now(timezone.utc).isoformat(),'pid':state['pid'],'tools_files':len(actual),
        'tools_stable_after_boot_and_provision':True,'tool_inventory_sha256':hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'golden_image_sha512':base_sha,'golden_image_readonly_attribute':True,'golden_image_qmp_readonly':True,
        'source_image_unchanged':True,'qemu_installer_unchanged':True,'seven_zip_unchanged':True,'reparse_points':unsafe,
        'qmp':qmp,'scope':'Environment provenance and running owned guest only. No product source exported, no Dockerfile/base digest resolved, no product build/test or performance claim.'}
(LAB/'evidence/linux-tcg-environment-final.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pid':state['pid'],'tools_stable':True,'golden_image_unchanged_and_readonly':True,'guest_running':True,'resources':state['resources']},indent=2))
