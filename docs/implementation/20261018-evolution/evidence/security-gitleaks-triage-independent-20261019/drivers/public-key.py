"""Parse public packets only; no key import, GPG home or running service."""
from pathlib import Path
import base64,hashlib,json,re,urllib.request,urllib.parse
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-gitleaks-peer-private-20261019')
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019')
REL='docs/implementation/20261018-evolution/evidence/linux-expat-sec10-m2-prepared-20261019/author-evidence/primary/python-release-key.asc'
def packets(armor):
    text=armor.decode('ascii');parts=text.split('-----BEGIN PGP PUBLIC KEY BLOCK-----')[1:];result=[]
    for part in parts:
        part=part.split('-----END PGP PUBLIC KEY BLOCK-----')[0]
        encoded=[];started=False
        for line in part.splitlines():
            line=line.strip()
            if not line or ':' in line:continue
            if line.startswith('='):continue
            encoded.append(line)
        data=base64.b64decode(''.join(encoded),validate=True);i=0
        while i<len(data):
            head=data[i];i+=1;assert head&128
            if head&64:
                tag=head&63;n=data[i];i+=1
                if n<192:length=n
                elif n<224:length=((n-192)<<8)+data[i]+192;i+=1
                elif n==255:length=int.from_bytes(data[i:i+4],'big');i+=4
                else:raise ValueError('Partial body lengths not accepted')
            else:
                tag=(head>>2)&15;length_type=head&3;assert length_type!=3
                count=[1,2,4][length_type];length=int.from_bytes(data[i:i+count],'big');i+=count
            body=data[i:i+length];assert len(body)==length;i+=length
            if tag==6:
                assert body[0]==4 and len(body)<65536
                result.append({'kind':'public_primary_key','fingerprint':hashlib.sha1(b'\x99'+len(body).to_bytes(2,'big')+body).hexdigest().upper(),'public_key_packet_sha256':hashlib.sha256(body).hexdigest()})
            if tag==13:
                uid=body.decode('utf8');result.append({'kind':'uid','Thomas_Wouters_name':uid.startswith('Thomas Wouters <'),'uid_sha256':hashlib.sha256(body).hexdigest()})
    return result
url='https://github.com/Yhg1s.gpg'
request=urllib.request.Request(url,headers={'User-Agent':'MetodoBase-independent-readonly-review'})
with urllib.request.urlopen(request,timeout=30) as response:
    assert response.status==200 and urllib.parse.urlsplit(response.url).hostname=='github.com'
    official=response.read(256*1024+1);assert len(official)<=256*1024
with (PRIVATE/'python-org-linked-public-key.asc').open('xb') as output:output.write(official)
retained=(SOURCE/REL).read_bytes();a=packets(retained);b=packets(official)
original={r['fingerprint'] for r in a if r['kind']=='public_primary_key'}
current={r['fingerprint'] for r in b if r['kind']=='public_primary_key'}
assert original==current and all(v.endswith('A821E680E5FA6305') for v in original)
assert any(r.get('Thomas_Wouters_name') for r in a) and any(r.get('Thomas_Wouters_name') for r in b)
out={'official_role_source':'https://www.python.org/downloads/metadata/pgp/','official_linked_public_key':url,
    'retained_path':REL,'retained_key_sha256':hashlib.sha256(retained).hexdigest(),'official_key_download_sha256':hashlib.sha256(official).hexdigest(),
    'same_public_primary_fingerprints':True,'Python_org_key_id_suffix_matches':True,'public_primary_fingerprints':sorted(original),'retained_packets':a,'official_packets':b,
    'scope':'Public-key packet fingerprint and UID comparison with a Python.org linked source, not a new tarball signature verification or private-key operation.'}
(PRIVATE/'public-key-proof.STRUCTURAL.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
print(json.dumps({'public_primary_keys':len(original),'same_fingerprint':True,'official_role':'Thomas Wouters, Python3.12/3.13 source releases','key_id_suffix_matches_python_org':True,'UID_name_matches':True}))
