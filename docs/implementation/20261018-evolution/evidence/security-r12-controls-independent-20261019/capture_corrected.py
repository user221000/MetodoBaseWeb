from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).parent;ROOT=Path('F:/mb-r12-controls-s');BASE=Path('F:/mb-r12-last-s')
def h(b):return hashlib.sha256(b).hexdigest()
def git(root,*a):return subprocess.check_output(['git',*a],cwd=root)
phase=sys.argv[1];target=HERE/(phase+'-sources.json');assert not target.exists()
trees=[]
for root in (BASE,ROOT):
    paths=git(root,'ls-files','-z').decode().split('\0')[:-1]
    trees.append({'root':str(root),'head':git(root,'rev-parse','HEAD').decode().strip(),'tree':git(root,'rev-parse','HEAD^{tree}').decode().strip(),
        'files':{p:h((root/p).read_bytes()) for p in paths},'count':len(paths),'tracked_status':git(root,'status','--porcelain','--untracked-files=no').decode()})
proof=ROOT/'docs/implementation/20261018-evolution/evidence/r12-controls-author-20261019'
assert h((proof/'freeze.json').read_bytes())=='fe83315f63b8d2af2c874cf265caf21314038591871535ad21706c6670a8d778'
manifest=json.loads((proof/'evidence-manifest.json').read_bytes())
for name,value in manifest['files'].items():
    b=(proof/name).read_bytes();assert len(b)==value['bytes'] and h(b)==value['sha256'],name
    assert git(ROOT,'show','HEAD:'+str((proof/name).relative_to(ROOT)).replace('\\','/'))==b,name
assert len(manifest['files'])==manifest['file_count']==33
assert git(ROOT,'show','HEAD:'+str((proof/'evidence-manifest.json').relative_to(ROOT)).replace('\\','/'))==(proof/'evidence-manifest.json').read_bytes()
freeze=json.loads((proof/'freeze.json').read_bytes())
for name,value in freeze['source'].items():
    raw=(Path('F:/mb-r12-ui-fix29-20261019')/name).read_bytes();lf=(ROOT/name).read_bytes()
    assert h(raw)==value['RAW_sha256'] and h(lf)==value['LF_sha256'] and raw.replace(b'\r\n',b'\n')==lf,name
consumers='tests/e2e/member_link_consumers.cjs'
a=git(ROOT,'show','9397569:'+consumers);b=(ROOT/consumers).read_bytes();boundary=b'const tests=[];'
assert a[a.index(boundary):]==b[b.index(boundary):]
changed=git(ROOT,'diff','9397569','HEAD','--name-only').decode().splitlines()
assert {p for p in changed if p.startswith('web/')}==set(freeze['product_files'])
node=Path(subprocess.check_output(['powershell','-NoProfile','-Command','(Get-Command node).Source'],text=True).strip())
data={'trees':trees,'node_version':subprocess.check_output([str(node),'--version']).decode().strip(),'node_sha256':h(node.read_bytes()),
    'raw_proof_blobs_exact':34,'freeze_raw_sha256':h((proof/'freeze.json').read_bytes()),'existing16_test_bodies_byte_identical':True,
    'four_js_only':True,'qa3_driver_sha256':h((ROOT/'tests/e2e/member_link_controls.cjs').read_bytes())}
if phase!='before':
    old=json.loads((HERE/'before-sources.json').read_bytes());data['sources_stable']=old['trees']==trees;data['node_stable']=old['node_sha256']==data['node_sha256'] and old['node_version']==data['node_version']
target.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in data.items() if k!='trees'}))
