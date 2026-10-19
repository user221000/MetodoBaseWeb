from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,hashlib,urllib.request,io,tarfile,re
OUT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/sca-native-triage31-20261019');P=OUT/'primary';records=[]
def get(name,url,expected=None,size=None):
    assert not (P/name).exists()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA-evidence/1.0'}),timeout=60) as r:raw=r.read();headers=dict(r.headers)
        digest=hashlib.sha256(raw).hexdigest()
        if expected:assert digest==expected and len(raw)==size
        (P/name).write_bytes(raw);return {'file':name,'url':url,'bytes':len(raw),'sha256':digest,'headers':headers}
    except Exception as exc:return {'requested_file':name,'url':url,'failure_type':type(exc).__name__,'http_status':getattr(exc,'code',None)}
urls={
 'zlib-debian-source.dsc':'https://deb.debian.org/debian/pool/main/z/zlib/zlib_1.3.dfsg+really1.3.1-1.dsc',
 'sqlite-3.46.1-session.h':'https://raw.githubusercontent.com/sqlite/sqlite/version-3.46.1/ext/session/sqlite3session.h',
 'sqlite-3.46.1-session.c':'https://raw.githubusercontent.com/sqlite/sqlite/version-3.46.1/ext/session/sqlite3session.c',
 'sqlite-applyv3-fix-commit.json':'https://api.github.com/repos/sqlite/sqlite/commits/b869ed6b067d623cb1383549f2a18aa35508385d',
 'sqlite-concat-fix-commit.json':'https://api.github.com/repos/sqlite/sqlite/commits/c597ed79d1bd03f57198d10d1f431adda293cf2e',
 'cpython-3.12-current-expat.h':'https://raw.githubusercontent.com/python/cpython/3.12/Modules/expat/expat.h',
 'cpython-3.12-current-xmlparse.c':'https://raw.githubusercontent.com/python/cpython/3.12/Modules/expat/xmlparse.c',
 'python-release-31216.html':'https://www.python.org/downloads/release/python-31216/',
 'docker-official-current-312-Dockerfile':'https://raw.githubusercontent.com/docker-library/python/master/3.12/slim-trixie/Dockerfile',
 'openssl-vulnerabilities-index.html':'https://openssl-library.org/news/vulnerabilities/'}
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(lambda item:get(*item),urls.items()))
dsc=(P/'zlib-debian-source.dsc').read_text();section=dsc.split('Checksums-Sha256:\n',1)[1].split('\nFiles:',1)[0];tar_records=[]
for line in section.splitlines():
    parts=line.split()
    if len(parts)!=3 or len(parts[0])!=64:continue
    digest,size,name=parts
    tar_records.append(get(name,'https://deb.debian.org/debian/pool/main/z/zlib/'+name,digest,int(size)))
records.extend(tar_records)
source_inspection=[]
for row in tar_records:
    assert 'file' in row,row
    with tarfile.open(P/row['file'],mode='r:*') as tar:
        for member in tar.getmembers():
            if not member.isfile():continue
            if member.name.endswith('/gzwrite.c') or member.name.endswith('/crc32.c') or member.name.startswith('debian/patches/'):
                raw=tar.extractfile(member).read();source_inspection.append({'artifact':row['file'],'path':member.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gz_vacate_present':b'gz_vacate' in raw,'negative_len_guard_present':b'if (len2 <= 0)' in raw,'text':raw.decode('utf-8',errors='replace') if member.name.startswith('debian/patches/') else None})
out={'captured_utc':datetime.now(timezone.utc).isoformat(),'records':records,'zlib_source_inspection':source_inspection,'signature_scope':'Debian .dsc is PGP-signed text retrieved over official HTTPS. Hashes of component archives verified against .dsc; host GPG signature verification not performed. Existing APT binary snapshot hash validation and actual ELF comparison recorded separately.'}
(OUT/'component-source-receipt.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'sources':len(records),'failures':[r for r in records if 'file' not in r],'zlib_selected_source_records':len(source_inspection)},indent=2))
