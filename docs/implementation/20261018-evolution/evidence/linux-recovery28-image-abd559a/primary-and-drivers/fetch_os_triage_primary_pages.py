from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.parse,urllib.request

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/os-audit-abd559a/triage-primary'
PAGES=OUT/'pages';PAGES.mkdir(exist_ok=False)
rows=json.loads((OUT/'selected-debian-entries.json').read_text())
ids=sorted({p['id'] for p in rows})
class Parser(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.links=[]
    def handle_data(self,data):self.parts.append(data)
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.links.append(href)
def fetch(identity):
    url='https://security-tracker.debian.org/tracker/'+identity
    req=urllib.request.Request(url,headers={'User-Agent':'MetodoBase-local-QA/1.0'})
    with urllib.request.urlopen(req,timeout=60) as response:data=response.read()
    (PAGES/(identity+'.html')).write_bytes(data)
    parser=Parser();parser.feed(data.decode('utf-8'))
    text=' '.join(' '.join(parser.parts).split())
    links=sorted({urllib.parse.urljoin(url,p) for p in parser.links})
    external=[p for p in links if urllib.parse.urlparse(p).hostname not in ('security-tracker.debian.org','nvd.nist.gov','www.cve.org','cve.mitre.org','security.debian.org')]
    return {'id':identity,'primary_url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'text':text,'external_primary_candidates':external}
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,ids))
(OUT/'page-extracts.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
(OUT/'pages-receipt.json').write_text(json.dumps({'retrieved_utc':datetime.now(timezone.utc).isoformat(),'pages':[{k:p[k] for k in ['id','primary_url','bytes','sha256']} for p in results]},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'retrieved':len(results),'all_ids_covered':set(ids)=={p['id'] for p in results}}))
