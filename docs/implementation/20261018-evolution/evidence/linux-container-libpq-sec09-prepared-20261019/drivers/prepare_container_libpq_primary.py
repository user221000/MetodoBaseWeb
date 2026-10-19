from pathlib import Path
from datetime import datetime,timezone
import hashlib,io,json,tarfile,urllib.request
ROOT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/container-system-libpq-20261019')
ROOT.mkdir(exist_ok=False)
def fetch(url,name):
    with urllib.request.urlopen(url,timeout=60) as r:raw=r.read();headers=dict(r.headers)
    with (ROOT/name).open('xb') as f:f.write(raw)
    return raw,{'url':url,'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'headers':headers}
records=[];packages={}
for package,version in [('psycopg2','2.9.13'),('psycopg2-binary','2.9.13'),('setuptools',None),('wheel',None)]:
    url='https://pypi.org/pypi/'+package+('/'+version if version else '')+'/json'
    raw,record=fetch(url,package+'.metadata.json');records.append(record);j=json.loads(raw)
    packages[package]={'version':j['info']['version'],'requires_python':j['info']['requires_python'],'requires_dist':j['info']['requires_dist']}
    choices=[u for u in j['urls'] if (u['packagetype']=='sdist' if package=='psycopg2' else u['filename'].endswith('py3-none-any.whl') if package in ['wheel','setuptools'] else False)]
    if package=='psycopg2-binary':continue
    assert len(choices)==1
    choice=choices[0];asset,ar=fetch(choice['url'],choice['filename']);records.append(ar)
    assert ar['sha256']==choice['digests']['sha256'] and len(asset)==choice['size']
    packages[package]['asset']={'filename':choice['filename'],'url':choice['url'],'bytes':len(asset),'sha256':ar['sha256']}
    if package=='psycopg2':
        with tarfile.open(fileobj=io.BytesIO(asset),mode='r:gz') as tf:
            for name in ['pyproject.toml','setup.cfg']:
                m=tf.getmember('psycopg2-2.9.13/'+name)
                assert m.isfile()
                (ROOT/('psycopg2-'+name)).write_bytes(tf.extractfile(m).read())
summary={'captured_utc':datetime.now(timezone.utc).isoformat(),'packages':packages,'downloads':records,
         'download_scope':'PyPI metadata and assets only; no host installation or source execution',
         'signatures':'PyPI HTTPS and asset hash recorded; no signature equivalence asserted'}
(ROOT/'primary-assets.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'folder':str(ROOT),'packages':packages},indent=2))
