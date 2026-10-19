from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,lzma,urllib.request
ROOT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/container-system-libpq-20261019')
OUT=ROOT/'apt-primary';OUT.mkdir(exist_ok=False)
records=[];selected=[]
def fetch(url,name):
    with urllib.request.urlopen(url,timeout=60) as r:raw=r.read()
    (OUT/name).write_bytes(raw)
    records.append({'url':url,'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return raw
for name,base,suite in [('stable','https://deb.debian.org/debian','trixie'),('updates','https://deb.debian.org/debian','trixie-updates'),('security','https://security.debian.org/debian-security','trixie-security')]:
    signed=fetch(base+'/dists/'+suite+'/InRelease',name+'.InRelease')
    index=fetch(base+'/dists/'+suite+'/main/binary-amd64/Packages.xz',name+'.Packages.xz')
    digest=hashlib.sha256(index).hexdigest()
    assert any(row.split()==[digest,str(len(index)),'main/binary-amd64/Packages.xz'] for row in signed.decode().splitlines())
    text=lzma.decompress(index).decode()
    for stanza in text.split('\n\n'):
        fields={}
        for line in stanza.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                k,v=line.split(': ',1);fields[k]=v
        if fields.get('Package') in ['gcc','gcc-14','libc6-dev','libpq5','libpq-dev','libssl3t64','libssl-dev']:
            selected.append({'suite':suite,'repository':base,'fields':fields})
result={'captured_utc':datetime.now(timezone.utc).isoformat(),'downloads':records,'selected':selected,
        'index_hash_matches_InRelease':True,
        'signature_status':'InRelease fetched intact; OpenPGP verification deferred to reviewed Linux APT/keyring before build. HTTPS/index hash is not a signature substitute.',
        'host_changes':'Downloads and metadata parsing only; QEMU remains off.'}
(OUT/'metadata.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'selected':[{'package':r['fields']['Package'],'version':r['fields']['Version'],'suite':r['suite'],'bytes':r['fields']['Size'],'sha256':r['fields']['SHA256']} for r in selected]},indent=2))
