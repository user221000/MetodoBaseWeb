from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,json,re,urllib.request

OUT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019\evidence\image-pip-base-primary-20261019')
TAG='3.12.15-slim'
REGISTRY='https://registry-1.docker.io/v2/library/python/'

def sha(data):return hashlib.sha256(data).hexdigest()
auth='https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull'
token=json.load(urllib.request.urlopen(auth,timeout=30))['token']
headers={'Authorization':'Bearer '+token,'Accept':','.join(['application/vnd.oci.image.index.v1+json',
    'application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json',
    'application/vnd.docker.distribution.manifest.v2+json'])}
def fetch(path):
    request=urllib.request.Request(REGISTRY+path,headers=headers)
    with urllib.request.urlopen(request,timeout=60) as response:
        data=response.read();safe_headers={k:response.headers.get(k) for k in ('Content-Type','Content-Length','Docker-Content-Digest','Date','ETag')}
    return data,safe_headers

index_raw,index_headers=fetch('manifests/'+TAG)
index=json.loads(index_raw)
assert index_headers['Docker-Content-Digest']=='sha256:'+sha(index_raw)
selected=[m for m in index['manifests'] if m.get('platform',{}).get('os')=='linux' and m['platform'].get('architecture')=='amd64']
assert len(selected)==1
descriptor=selected[0]
manifest_raw,manifest_headers=fetch('manifests/'+descriptor['digest'])
assert descriptor['digest']=='sha256:'+sha(manifest_raw) and len(manifest_raw)==descriptor['size']
assert manifest_headers['Docker-Content-Digest']==descriptor['digest']
manifest=json.loads(manifest_raw)
config_raw,config_headers=fetch('blobs/'+manifest['config']['digest'])
assert 'sha256:'+sha(config_raw)==manifest['config']['digest']
config=json.loads(config_raw)
assert config['os']=='linux' and config['architecture']=='amd64'
assert 'PYTHON_VERSION=3.12.15' in config['config']['Env']
for filename,data in [('dockerhub-python31215-index.raw.json',index_raw),('dockerhub-python31215-amd64-manifest.raw.json',manifest_raw),('dockerhub-python31215-config.raw.json',config_raw)]:
    p=OUT/filename;assert not p.exists();p.write_bytes(data)

api='https://api.github.com/repos/docker-library/official-images/contents/library/python'
library=json.load(urllib.request.urlopen(api,timeout=30));library_bytes=base64.b64decode(library['content'])
assert hashlib.sha1(b'blob '+str(len(library_bytes)).encode()+b'\0'+library_bytes).hexdigest()==library['sha']
blocks=library_bytes.decode().split('\n\n')
matching=[]
for block in blocks:
    match=re.search(r'^Tags: (.*)$',block,re.M)
    if match and TAG in match.group(1).split(', '):matching.append(block)
assert len(matching)==1
block=matching[0]
source_commit=re.search(r'^GitCommit: ([a-f0-9]{40})$',block,re.M).group(1)
source_directory=re.search(r'^Directory: (.+)$',block,re.M).group(1)
source_url='https://raw.githubusercontent.com/docker-library/python/'+source_commit+'/'+source_directory+'/Dockerfile'
source_bytes=urllib.request.urlopen(source_url,timeout=30).read()
assert b'ENV PYTHON_VERSION 3.12.15' in source_bytes or b'ENV PYTHON_VERSION=3.12.15' in source_bytes
(OUT/'official-images-library-python.raw.txt').write_bytes(library_bytes)
(OUT/'official-python31215-source-Dockerfile.txt').write_bytes(source_bytes)
report={'captured_utc':datetime.now(timezone.utc).isoformat(),'tag':TAG,'registry_repository':'docker.io/library/python',
        'tag_index_digest':'sha256:'+sha(index_raw),'selected_platform':descriptor['platform'],
        'linux_amd64_manifest_digest':descriptor['digest'],'config_digest':manifest['config']['digest'],
        'verified_config_python':'3.12.15','index_headers':index_headers,'manifest_headers':manifest_headers,
        'config_headers':config_headers,'layer_digests':[x['digest'] for x in manifest['layers']],
        'official_images_library_api':api,'official_images_library_blob_sha1':library['sha'],
        'official_images_tag_block':block,'official_source_git_commit':source_commit,'official_source_directory':source_directory,
        'official_source_url':source_url,'official_source_sha256':sha(source_bytes),
        'scope':'Official registry bytes/digest/config and official-images source reference only. Runtime verification still required. Token/signature trust not logged or claimed.'}
(OUT/'python31215-registry-provenance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
