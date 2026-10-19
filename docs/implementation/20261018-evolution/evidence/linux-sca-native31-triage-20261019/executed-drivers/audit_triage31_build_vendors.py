from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from email.parser import BytesParser
import hashlib,json,re,urllib.request,zipfile
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/sca-native-triage31-20261019'
rows=[];members=[]
setuptools=LAB/'evidence/container-system-libpq-20261019/setuptools-84.0.0-py3-none-any.whl'
pip=next((LAB/'evidence/pip-bootstrap-26.2.1').glob('*.whl'))
assert hashlib.sha256(setuptools.read_bytes()).hexdigest()=='51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670'
assert hashlib.sha256(pip.read_bytes()).hexdigest()=='71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e'
for wheel in [pip,setuptools]:
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None
        names=z.namelist()
        members.extend({'wheel':wheel.name,'member':n,'bytes':z.getinfo(n).file_size,'sha256':hashlib.sha256(z.read(n)).hexdigest()} for n in names if '_vendor/' in n and not n.endswith('/'))
        if wheel==pip:
            raw=z.read('pip/_vendor/vendor.txt');(OUT/'pip-vendor.txt').write_bytes(raw)
            for name,version in re.findall(r'^\s*([\w.-]+)==([^\s#]+)',raw.decode(),re.M):
                rows.append({'outer_package':'pip','outer_version':'26.2.1','name':name,'version':version,'declaration':'pip/_vendor/vendor.txt',
                             'scope':'Expected contents of pinned wheel; pip runtime version measured in image99c, child build venv not created.'})
        else:
            for n in names:
                if '_vendor/' in n and n.endswith('.dist-info/METADATA'):
                    metadata=BytesParser().parsebytes(z.read(n))
                    rows.append({'outer_package':'setuptools','outer_version':'84.0.0','name':metadata['Name'],'version':metadata['Version'],
                                 'declaration':n,'scope':'Candidate build-tools wheel only; not installed in image99c or a built candidate venv.'})
(OUT/'build-vendor-inventory.json').write_text(json.dumps({'captured_utc':datetime.now(timezone.utc).isoformat(),'rows':rows,
    'wheel_files':{p.name:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [pip,setuptools]},
    'source_read_only':True,'package_code_executed':False},indent=2)+'\n',encoding='utf-8')
(OUT/'build-vendor-members.json').write_text(json.dumps(members,indent=2)+'\n',encoding='utf-8')
actual=json.loads((LAB/'evidence/recovery28-image-bc365c1/runtime-inventory.json').read_text())['runtime_inventory']['packages']
queries=[];mapping=[]
for package in actual:
    mapping.append({'scope':'actual99c_python_metadata','name':package['name'],'version':package['version']})
    queries.append({'package':{'name':package['name'],'ecosystem':'PyPI'},'version':package['version']})
for row in [{'outer_package':'build-env','outer_version':None,'name':'pip','version':'26.2.1'},{'outer_package':'build-env','outer_version':None,'name':'setuptools','version':'84.0.0'}]+rows:
    mapping.append({'scope':'candidate_buildtools_or_vendor_not_installed',**row})
    queries.append({'package':{'name':row['name'],'ecosystem':'PyPI'},'version':row['version']})
request=json.dumps({'queries':queries},separators=(',',':')).encode()
(OUT/'osv-python-querybatch.request.json').write_bytes(request)
req=urllib.request.Request('https://api.osv.dev/v1/querybatch',data=request,headers={'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=60) as r:raw=r.read();headers=dict(r.headers)
(OUT/'osv-python-querybatch.response.json').write_bytes(raw)
results=json.loads(raw)['results'];assert len(results)==len(mapping)
ids=sorted({v['id'] for result in results for v in result.get('vulns',[])})
def fetch(vid):
    url='https://api.osv.dev/v1/vulns/'+vid
    with urllib.request.urlopen(url,timeout=45) as r:payload=r.read()
    (OUT/'primary'/('OSV-'+vid+'.json')).write_bytes(payload)
    return vid,json.loads(payload)
with ThreadPoolExecutor(max_workers=4) as pool:advisories=dict(pool.map(fetch,ids))
reported=[]
for row,result in zip(mapping,results):
    reported.append({**row,'osv_ids':[v['id'] for v in result.get('vulns',[])],
                     'aliases':sorted({a for v in result.get('vulns',[]) for a in advisories[v['id']].get('aliases',[])})})
receipt={'queried_utc':datetime.now(timezone.utc).isoformat(),'endpoint':'https://api.osv.dev/v1/querybatch',
         'request_sha256':hashlib.sha256(request).hexdigest(),'response_sha256':hashlib.sha256(raw).hexdigest(),'headers':headers,
         'queries':len(queries),'actual_runtime_python_queries':55,'vendor_declarations':len(rows),'rows':reported,
         'scope':'Version matching only. Vendored subsets/backports and affected functions require separate analysis; no runtime image or build venv executed.'}
(OUT/'osv-python-analysis.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'queries':len(queries),'vendors':len(rows),'matches':[r for r in reported if r['osv_ids']]},indent=2))
