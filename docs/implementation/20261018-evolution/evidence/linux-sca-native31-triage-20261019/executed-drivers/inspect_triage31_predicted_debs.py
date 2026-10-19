from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,io,json,tarfile,urllib.request,lzma
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/sca-native-triage31-20261019';P=OUT/'primary'
def sha(b):return hashlib.sha256(b).hexdigest()
def deb_members(data):
    assert data[:8]==b'!<arch>\n';offset=8
    while offset<len(data):
        head=data[offset:offset+60];assert head[58:]==b'`\n';size=int(head[48:58]);name=head[:16].decode().strip().rstrip('/');start=offset+60;yield name,data[start:start+size];offset=start+size+(size%2)
def inspect(item):
    url=item['url'];path=P/(item['package']+'_'+item['version'].replace(':','_')+'.deb');assert not path.exists()
    with urllib.request.urlopen(url,timeout=60) as r:data=r.read();headers=dict(r.headers)
    assert len(data)==item['bytes'] and sha(data)==item['sha256'];path.write_bytes(data)
    ar=dict(deb_members(data));key=next(k for k in ar if k.startswith('data.tar.'));files=[];elf=[]
    with tarfile.open(fileobj=io.BytesIO(ar[key]),mode='r:*') as tar:
        for m in tar.getmembers():
            assert not m.name.startswith('/') and '..' not in Path(m.name).parts
            files.append({'path':m.name,'type':m.type.decode('ascii'),'bytes':m.size,'linkname':m.linkname})
            if m.isfile():
                raw=tar.extractfile(m).read()
                if raw.startswith(b'\x7fELF'):elf.append({'path':m.name,'bytes':len(raw),'sha256':sha(raw),'class_bits':{1:32,2:64}[raw[4]],'string_matches':{s:(s.encode()+b'\0') in raw for s in ['sqlite3changeset_apply_v3','gz_vacate','gzprintf','crc32_combine64']}})
    return {'expected_package':item,'artifact':{'file':path.name,'url':url,'bytes':len(data),'sha256':sha(data),'headers':headers},'files':files,'elf':elf,'scope':'Read-only archive inspection; package not installed or executed. Metadata hashes reused from pinned official APT indices; signature/expiry execution gate remains pending Linux build.'}
pred=json.loads((LAB/'evidence/container-system-libpq-20261019/runtime-os-expected.json').read_text())['predicted_new_packages']
# Locate actual base library artifacts in the same official APT index snapshot.
actual=json.loads((LAB/'evidence/runtime28-native-20261019/native/native.json').read_text());wanted={x['name'].split(':')[0]:x['version'] for x in actual['dpkg_packages'] if x['name'].split(':')[0] in {'zlib1g','libsqlite3-0','perl-base'}}
extra=[]
for label,base in [('stable','https://deb.debian.org/debian/'),('security','https://security.debian.org/debian-security/'),('updates','https://deb.debian.org/debian/')]:
    raw=lzma.decompress((LAB/('evidence/container-system-libpq-20261019/apt-primary/'+label+'.Packages.xz')).read_bytes()).decode()
    for paragraph in raw.split('\n\n'):
        if not any(paragraph.startswith('Package: '+n+'\n') for n in wanted):continue
        fields={};key=None
        for line in paragraph.splitlines():
            if line.startswith(' '):fields[key]+='\n'+line
            elif ': ' in line:key,value=line.split(': ',1);fields[key]=value
        name=fields['Package']
        if fields['Version']!=wanted[name]:continue
        extra.append({'package':name,'version':fields['Version'],'source':fields.get('Source',name),'bytes':int(fields['Size']),'sha256':fields['SHA256'],'url':base+fields['Filename'],'metadata_source':label})
assert {x['package'] for x in extra}==set(wanted)
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(inspect,pred+extra))
path=OUT/'predicted-and-base-deb-file-inspection.json';assert not path.exists();path.write_text(json.dumps({'captured_utc':datetime.now(timezone.utc).isoformat(),'predicted_packages':10,'actual_base_packages':len(extra),'rows':rows},indent=2)+'\n',encoding='utf-8')
native_by_sha={x['sha256']:x['path'] for x in actual['elf_files']}
for row in rows:
    row['matching_observed_elf']=[{'artifact_file':x['path'],'observed_path':native_by_sha[x['sha256']],'sha256':x['sha256']} for x in row['elf'] if x['sha256'] in native_by_sha]
verification={'rows':[{'package':r['expected_package']['package'],'scope':'predicted' if r['expected_package'] in pred else 'actual base package','matching_observed_elf':r['matching_observed_elf'],'specific_files':[f for f in r['files'] if any(s in f['path'] for s in ['digestmd5','libldap','liblmdb','File/Temp.pm','Archive/Tar.pm','Pod/Text.pm'])]} for r in rows]}
(OUT/'deb-native-and-components-crosscheck.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'archives':len(rows),'predicted':10,'base':len(extra),'base_elf_matches':sum(len(r['matching_observed_elf']) for r in rows)},indent=2))
