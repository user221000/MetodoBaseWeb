from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,lzma,urllib.request
ROOT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/container-system-libpq-20261019')
OUT=ROOT/'primary-docs';OUT.mkdir(exist_ok=True)
urls={
 'psycopg-install.html':'https://www.psycopg.org/docs/install.html',
 'psycopg-news.html':'https://www.psycopg.org/docs/news.html',
 'debian-dsa6531.html':'https://lists.debian.org/debian-security-announce/2026/msg00444.html',
 'debian-openssl-tracker.html':'https://security-tracker.debian.org/tracker/DSA-6531-1',
 'debian-libpq5.html':'https://packages.debian.org/trixie/libpq5',
 'openssl-20260929.txt':'https://openssl-library.org/news/secadv/20260929.txt',
 'pip-build-interface.html':'https://pip.pypa.io/en/stable/reference/build-system/',
 'pip-secure-installs.html':'https://pip.pypa.io/en/stable/topics/secure-installs/'}
rows=[]
for name,url in urls.items():
    try:
        with urllib.request.urlopen(url,timeout=45) as r:raw=r.read();final=r.url
    except Exception as exc:
        rows.append({'url':url,'file':None,'fetch_error_type':type(exc).__name__,'http_status':getattr(exc,'code',None),'web_tool_primary_page_read_separately':True})
        continue
    with (OUT/name).open('xb') as f:f.write(raw)
    rows.append({'url':url,'final_url':final,'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
(OUT/'sources.json').write_text(json.dumps({'captured_utc':datetime.now(timezone.utc).isoformat(),'sources':rows},indent=2)+'\n')
wanted={'libpq5','libgssapi-krb5-2','libldap2','libkrb5-3','libk5crypto3','libkrb5support0','libcom-err2','libkeyutils1','libsasl2-2','libsasl2-modules-db'}
packages={}
for label,url in [('stable','https://deb.debian.org/debian/'),('updates','https://deb.debian.org/debian/'),('security','https://security.debian.org/debian-security/')]:
    for stanza in lzma.decompress((ROOT/'apt-primary'/(label+'.Packages.xz')).read_bytes()).decode().split('\n\n'):
        fields={}
        for line in stanza.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                k,v=line.split(': ',1);fields[k]=v
        if fields.get('Package') in wanted:
            packages[fields['Package']]={'package':fields['Package'],'version':fields['Version'],'source':fields.get('Source',fields['Package']),
                'depends':fields.get('Depends'),'bytes':int(fields['Size']),'sha256':fields['SHA256'],'url':url+fields['Filename'],'metadata_source':label}
assert set(packages)==wanted
result={'prepared_utc':datetime.now(timezone.utc).isoformat(),'kind':'Static expected runtime dependency closure; actual APT simulation/build inventory pending',
        'predicted_new_packages':sorted(packages.values(),key=lambda r:r['package']),
        'source_integrity':'HTTPS and index hashes recorded; APT OpenPGP verification is required before execution',
        'security_scope':'Every newly added OS source is in the next full OS audit; no closure of previous 71 IDs inferred.'}
(ROOT/'runtime-os-expected.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'primary_documents':len(rows),'expected_new_runtime_os_packages':len(packages),'actual_apt_simulation':False}))
