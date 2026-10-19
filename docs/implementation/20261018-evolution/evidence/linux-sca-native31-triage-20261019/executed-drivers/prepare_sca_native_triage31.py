from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request,urllib.error
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/sca-native-triage31-20261019'
OUT.mkdir(exist_ok=False);(OUT/'primary').mkdir()
sources={
 'native':LAB/'evidence/runtime28-native-20261019/native/native.json',
 'scan':LAB/'evidence/os-audit-bc365c1/results/scan.json',
 'scan_summary':LAB/'evidence/os-audit-bc365c1/results/scan-summary.json',
 'carry':LAB/'evidence/os-audit-bc365c1/triage-carry-forward.json',
 'prior_matrix':LAB/'evidence/os-audit-abd559a/triage-matrix/matrix-73.json',
 'tracker':LAB/'evidence/os-audit-abd559a/triage-primary/debian-security-tracker.raw.json',
 'predicted':LAB/'evidence/container-system-libpq-20261019/runtime-os-expected.json'}
inputs={k:{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in sources.items()}
assert inputs['native']['sha256']=='9cbf93d511d52a80272f9d5525058062f282202934c2dc6e26aa8347d774eaec'
assert inputs['tracker']['sha256']=='4bbd24a58d430e817d2db0f76f5fa391821ee92e5ce969c9587065b6279af543'
tracker_request=urllib.request.Request('https://security-tracker.debian.org/tracker/data/json',headers={'If-Modified-Since':'Mon, 19 Oct 2026 10:16:32 GMT'})
try:
    with urllib.request.urlopen(tracker_request,timeout=60) as r:
        raw=r.read();headers=dict(r.headers);status=r.status
    tracker_path=OUT/'primary/debian-security-tracker.current.raw.json'
    tracker_path.write_bytes(raw)
    tracker_info={'http_status':status,'headers':headers,'file':str(tracker_path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
except urllib.error.HTTPError as exc:
    assert exc.code==304
    tracker_info={'http_status':304,'reused_original':inputs['tracker'],'not_modified_since':'Mon, 19 Oct 2026 10:16:32 GMT'}
urls={
 'expat-R_2_9_0-Changes.txt':'https://raw.githubusercontent.com/libexpat/libexpat/R_2_9_0/expat/Changes',
 'expat-issue1160.json':'https://api.github.com/repos/libexpat/libexpat/issues/1160',
 'cpython-tag-3.12.15.json':'https://api.github.com/repos/python/cpython/git/ref/tags/v3.12.15',
 'cpython-pyexpat.c':'https://raw.githubusercontent.com/python/cpython/v3.12.15/Modules/pyexpat.c',
 'cpython-elementtree.c':'https://raw.githubusercontent.com/python/cpython/v3.12.15/Modules/_elementtree.c',
 'cpython-xmlparse.c':'https://raw.githubusercontent.com/python/cpython/v3.12.15/Modules/expat/xmlparse.c',
 'cpython-expat.h':'https://raw.githubusercontent.com/python/cpython/v3.12.15/Modules/expat/expat.h',
 'cpython-expat-Changes.txt':'https://raw.githubusercontent.com/python/cpython/v3.12.15/Modules/expat/Changes',
 'zlib-index.html':'https://zlib.net/',
 'sqlite-changes.html':'https://sqlite.org/changes.html',
 'sqlite-security.html':'https://sqlite.org/security.html',
 'xz-security.html':'https://tukaani.org/xz/security.html',
 'cryptography-changelog.html':'https://cryptography.io/en/latest/changelog/'}
ids=['CVE-2026-102633','CVE-2026-77214','CVE-2025-66382','CVE-2026-27171','CVE-2026-85091',
     'CVE-2021-45346','CVE-2025-70873','CVE-2026-50812','CVE-2026-50813',
     'CVE-2026-107161','CVE-2026-107708','CVE-2026-107778','CVE-2026-11850',
     'CVE-2024-26458','CVE-2024-26461','CVE-2015-3276','CVE-2020-15719','CVE-2026-22185']
for cve in ids:urls[cve+'.json']='https://cveawg.mitre.org/api/cve/'+cve
def fetch(item):
    name,url=item
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA-evidence/1.0'}),timeout=45) as r:
            raw=r.read();headers=dict(r.headers);final=r.url
        (OUT/'primary'/name).write_bytes(raw)
        return {'file':name,'url':url,'final_url':final,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'headers':headers}
    except Exception as exc:return {'file':None,'requested_file':name,'url':url,'failure_type':type(exc).__name__,'http_status':getattr(exc,'code',None)}
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,urls.items()))
receipt={'captured_utc':datetime.now(timezone.utc).isoformat(),'inputs':inputs,'tracker_revalidation':tracker_info,'sources':records,
         'scope':'Read-only native/OS triage, no image execution, source build, host installation or QEMU boot.'}
(OUT/'primary-input-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'folder':str(OUT),'source_count':len(records),'failed_sources':[r for r in records if r['file'] is None],
                  'tracker_http_status':tracker_info['http_status']},indent=2))
