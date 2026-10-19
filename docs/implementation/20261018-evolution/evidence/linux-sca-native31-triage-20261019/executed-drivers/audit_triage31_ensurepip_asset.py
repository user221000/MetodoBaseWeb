from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,io,json,re,tarfile,urllib.request,zipfile
O=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/sca-native-triage31-20261019');P=O/'primary/ensurepip';P.mkdir(exist_ok=False)
with tarfile.open(O/'primary/Python-3.12.15.tar.xz',mode='r:xz') as t:raw=t.extractfile('Python-3.12.15/Lib/ensurepip/_bundled/pip-25.0.1-py3-none-any.whl').read()
assert hashlib.sha256(raw).hexdigest()=='c46efd13b6aa8279f33f2864459c8ce587ea6a1a59ee20de055868d8f7688f7f'
z=zipfile.ZipFile(io.BytesIO(raw));assert z.testzip() is None
rows=[{'name':'pip','version':'25.0.1','kind':'wheel distribution'}]+[{'name':n,'version':v,'kind':'vendored declaration'} for n,v in re.findall(r'^\s*([\w.-]+)==([^\s#]+)',z.read('pip/_vendor/vendor.txt').decode(),re.M)]
payload=json.dumps({'queries':[{'package':{'name':r['name'],'ecosystem':'PyPI'},'version':r['version']} for r in rows]},separators=(',',':')).encode();(O/'osv-ensurepip-querybatch.request.json').write_bytes(payload)
with urllib.request.urlopen(urllib.request.Request('https://api.osv.dev/v1/querybatch',data=payload,headers={'Content-Type':'application/json'},method='POST'),timeout=60) as r:answer=r.read();headers=dict(r.headers)
(O/'osv-ensurepip-querybatch.response.json').write_bytes(answer);answers=json.loads(answer)['results'];assert len(rows)==len(answers)
ids=sorted({v['id'] for result in answers for v in result.get('vulns',[])})
def get(vid):
    url='https://api.osv.dev/v1/vulns/'+vid
    with urllib.request.urlopen(url,timeout=50) as r:data=r.read()
    (P/(vid+'.json')).write_bytes(data);return vid,json.loads(data)
with ThreadPoolExecutor(max_workers=4) as pool:advisories=dict(pool.map(get,ids))
result=[]
for row,answerrow in zip(rows,answers):
    result.append({**row,'osv_ids':[v['id'] for v in answerrow.get('vulns',[])],'cve_aliases':sorted({alias for v in answerrow.get('vulns',[]) for alias in advisories[v['id']].get('aliases',[]) if alias.startswith('CVE-')})})
receipt={'queried_utc':datetime.now(timezone.utc).isoformat(),'wheel_sha256':hashlib.sha256(raw).hexdigest(),'artifact':'PSF3.12.15 Lib/ensurepip/_bundled/pip-25.0.1-py3-none-any.whl','source_tar_sha256':'c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a','request_sha256':hashlib.sha256(payload).hexdigest(),'response_sha256':hashlib.sha256(answer).hexdigest(),'headers':headers,'queries':len(rows),'rows':result,'scope':'Release-source embedded wheel, not installed distribution metadata. Expected in official base from recipe, actual image filesystem bytes pending. Version matching only; affected subsets/functions not exhausted. Entire ensurepip is removed in final-runtime candidate af548, not in build stages.'}
(O/'ensurepip-asset-inventory-and-osv.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'queries':len(rows),'distinct_cve_aliases':len({c for r in result for c in r['cve_aliases']}),'matches':[r for r in result if r['osv_ids']]},indent=2))
