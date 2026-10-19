from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,io,json,tarfile,urllib.request
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/expat-sec10-preparation32-20261019';OUT.mkdir(exist_ok=False);(OUT/'primary').mkdir()
CACHE=LAB/'evidence/sca-native-triage31-20261019';records=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def get(name,url,expected=None):
    path=OUT/'primary'/name;assert not path.exists()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA-evidence/1.0'}),timeout=60) as r:raw=r.read();headers=dict(r.headers)
    if expected:assert sha(raw)==expected
    path.write_bytes(raw);return {'file':name,'url':url,'bytes':len(raw),'sha256':sha(raw),'headers':headers}
urls={
 'expat-site.html':'https://libexpat.github.io/',
 'expat-release-latest.json':'https://api.github.com/repos/libexpat/libexpat/releases/latest',
 'expat-release-2.8.5.json':'https://api.github.com/repos/libexpat/libexpat/releases/tags/R_2_8_5',
 'expat-tag-2.9.0.json':'https://api.github.com/repos/libexpat/libexpat/git/ref/tags/R_2_9_0',
 'cpython-pyexpat-doc.html':'https://docs.python.org/3.12/library/pyexpat.html'}
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(lambda pair:get(*pair),urls.items()))
latest=json.loads((OUT/'primary/expat-release-latest.json').read_text());assert latest['tag_name']=='R_2_9_0'
for rel in [latest,json.loads((OUT/'primary/expat-release-2.8.5.json').read_text())]:
    asset=next(a for a in rel['assets'] if a['name'].endswith('.tar.xz') and not a['name'].endswith('.asc'))
    digest=asset.get('digest');assert digest and digest.startswith('sha256:')
    records.append(get(asset['name'],asset['browser_download_url'],digest.split(':',1)[1]))
    signature=next((a for a in rel['assets'] if a['name']==asset['name']+'.asc'),None)
    if signature:records.append(get(signature['name'],signature['browser_download_url']))
source=CACHE/'primary/Python-3.12.15.tar.xz';assert sha(source.read_bytes())=='c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a'
with tarfile.open(source,mode='r:xz') as tar:cpy={m.name.split('Python-3.12.15/Modules/expat/',1)[1]:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile() and m.name.startswith('Python-3.12.15/Modules/expat/')}
def release_lib(name):
    with tarfile.open(OUT/'primary'/name,mode='r:xz') as tar:return {m.name.split('/lib/',1)[1]:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile() and '/lib/' in m.name}
old=release_lib('expat-2.8.5.tar.xz');new=release_lib('expat-2.9.0.tar.xz');comparison=[]
for name,data in sorted(cpy.items()):
    comparison.append({'file':name,'cpython_sha256':sha(data),'upstream_285_sha256':sha(old[name]) if name in old else None,'upstream_290_sha256':sha(new[name]) if name in new else None,'cpython_same_as_upstream_285':data==old.get(name),'upstream_changed_285_to290':old.get(name)!=new.get(name) if name in old and name in new else None,'cpython_specific':name not in old})
(OUT/'release-vs-cpython-source-comparison.json').write_text(json.dumps({'cpython_base_source_sha256':sha(source.read_bytes()),'files':comparison,'new_upstream_lib_filenames_not_in_cpython':sorted(set(new)-set(cpy))},indent=2)+'\n',encoding='utf-8')
for name in ['expat.h','expat_external.h','xmlparse.c','internal.h']:
    import difflib
    if cpy[name]!=old[name]:
        diff=''.join(difflib.unified_diff(old[name].decode().splitlines(keepends=True),cpy[name].decode().splitlines(keepends=True),fromfile='upstream-2.8.5/'+name,tofile='cpython-3.12.15/'+name));(OUT/('cpython-integration-'+name+'.diff')).write_text(diff,encoding='utf-8')
receipt={'captured_utc':datetime.now(timezone.utc).isoformat(),'records':records,'release_current':'2.9.0','existing_sources_reused_without_redownload':{'psf_tar_path':str(source),'psf_tar_sha256':sha(source.read_bytes()),'cve_77214_sha256':sha((CACHE/'primary/CVE-2026-77214.json').read_bytes()),'fix_commit_json_sha256':sha((CACHE/'primary/expat-fix-77214-commit.json').read_bytes())},'scope':'Read-only release/source comparison. Asset SHA256 checked against official GitHub API digest. Detached signatures retrieved where published, not yet locally verified. No build, native load, installation or QEMU.'}
(OUT/'primary-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'records':len(records),'release':latest['tag_name'],'cpython_files':len(cpy),'cpython_specific':[r['file'] for r in comparison if r['cpython_specific']],'cpython_modified_upstream':[r['file'] for r in comparison if not r['cpython_specific'] and not r['cpython_same_as_upstream_285']],'upstream_changed':[r['file'] for r in comparison if r['upstream_changed_285_to290']]},indent=2))
