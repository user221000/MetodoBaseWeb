from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,urllib.request,hashlib
OUT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\sca-native-triage31-20261019')
def get(name,url):
    path=OUT/'primary'/name
    assert not path.exists(),name
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA-evidence/1.0'}),timeout=50) as r:
            data=r.read();headers=dict(r.headers);final=r.url
        path.write_bytes(data)
        return {'file':name,'url':url,'final_url':final,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'headers':headers}
    except Exception as exc:return {'requested_file':name,'url':url,'failure_type':type(exc).__name__,'http_status':getattr(exc,'code',None)}
urls={
 'cpython-annotated-tag-3.12.15.json':'https://api.github.com/repos/python/cpython/git/tags/f9e83c56c657be0a74ede2b5c523de4f9191d117',
 'expat-fix-77214-commit.json':'https://api.github.com/repos/libexpat/libexpat/commits/13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0',
 'expat-fix-102633-commit.json':'https://api.github.com/repos/libexpat/libexpat/commits/209801d7fbaf07ab74bae8cb32dd2ab9e5846118',
 'msgpack-fix-commit.json':'https://api.github.com/repos/msgpack/msgpack-python/commits/2c56ddb5d0025ed481d962c0f5d62d19dec7476d',
 'urllib3-fix-chunk-commit.json':'https://api.github.com/repos/urllib3/urllib3/commits/cd770b059b543be29298ea5c52afb0b1b090f5ed',
 'urllib3-fix-deflate-commit.json':'https://api.github.com/repos/urllib3/urllib3/commits/ea2ad7b21a80da3632f80016526a18864586077f',
 'urllib3-fix-proxy-commit.json':'https://api.github.com/repos/urllib3/urllib3/commits/07408cec79d1856d81bb42c74a904a24fdb9e465',
 'urllib3-fix-proxy2-commit.json':'https://api.github.com/repos/urllib3/urllib3/commits/b6447295fff7b38fdffc67e0df9712d60cef3cc3',
 'zlib-v1.3.1-gzwrite.c':'https://raw.githubusercontent.com/madler/zlib/v1.3.1/gzwrite.c',
 'zlib-v1.3.1-crc32.c':'https://raw.githubusercontent.com/madler/zlib/v1.3.1/crc32.c',
 'zlib-fix-negative-commit.json':'https://api.github.com/repos/madler/zlib/commits/ba829a458576d1ff0f26fc7230c6de816d1f6a77',
 'zlib-fix-vacate-commit.json':'https://api.github.com/repos/madler/zlib/commits/df84af25dc1942490e1d1c899a07619152a46148',
 'pip-latest-pypi.json':'https://pypi.org/pypi/pip/json',
 'pip-26.2.1-commit.json':'https://api.github.com/repos/pypa/pip/git/ref/tags/26.2.1',
 'python-312-releases.json':'https://api.github.com/repos/python/cpython/tags?per_page=100',
 'pillow-security.json':'https://api.github.com/repos/python-pillow/Pillow/security-advisories'}
for cve in ['CVE-2026-57585','CVE-2026-97687','CVE-2026-97688','CVE-2026-97689','CVE-2025-47273','CVE-2026-59890']:
    urls[cve+'.json']='https://cveawg.mitre.org/api/cve/'+cve
for repo,advisory in [('msgpack/msgpack-python','GHSA-6v7p-g79w-8964'),('urllib3/urllib3','GHSA-8988-9cw3-xx77'),('urllib3/urllib3','GHSA-gh4c-6fx4-qh6g'),('urllib3/urllib3','GHSA-vxq7-64xx-v4gw'),('pypa/setuptools','GHSA-5rjg-fvgr-3xxf'),('pypa/setuptools','GHSA-h35f-9h28-mq5c')]:
    urls['maintainer-'+advisory+'.json']='https://api.github.com/repos/'+repo+'/security-advisories/'+advisory
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(lambda item:get(*item),urls.items()))
tag=json.loads((OUT/'primary/cpython-annotated-tag-3.12.15.json').read_text())
assert tag['object']['type']=='commit'
commit=tag['object']['sha']
for label,path in [('pyexpat','Modules/pyexpat.c'),('elementtree','Modules/_elementtree.c'),('xmlparse','Modules/expat/xmlparse.c'),('expat-h','Modules/expat/expat.h')]:
    records.append(get('cpython-commit-'+label+'.json','https://api.github.com/repos/python/cpython/contents/'+path+'?ref='+commit))
receipt={'captured_utc':datetime.now(timezone.utc).isoformat(),'cpython_commit':commit,'records':records}
(OUT/'primary-expansion-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'sources':len(records),'failed':[x for x in records if 'file' not in x],'cpython_commit':commit},indent=2))
