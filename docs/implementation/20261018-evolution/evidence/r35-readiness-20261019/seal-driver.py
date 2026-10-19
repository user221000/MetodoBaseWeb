"""Preserve source-only initial R35 evaluation without claiming implementation."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(r'F:\MetodoBaseWeb-execution-20261018');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');DEST=ROOT/'docs/implementation/20261018-evolution/evidence/r35-readiness-20261019'
DEST.mkdir(exist_ok=False);(DEST/'.gitattributes').write_bytes(b'* -text\n')
for source,name in [(TEMP/'metodobase-r35-readiness-20261019/source-inventory.json','source-inventory.json'),(TEMP/'metodobase-r35-readiness.py','driver.py')]:shutil.copyfile(source,DEST/name)
data=json.loads((DEST/'source-inventory.json').read_bytes());assert data['head']=='3663a360e019880477e558d4ad98ce0ad533ab77' and data['file_count']==232 and data['source_stable'] and not data['hits'] and not data['manifest_candidates']
refs={'accessed_UTC':'2026-10-19','method':'Primary pages checked with web.run; no full-page archival bytes or source SHA claimed','references':[
 {'url':'https://web.dev/articles/install-criteria','published_updated':'2024-09-19','scope':'Current Chrome-team article consulted; promotion and installation differ. Not a test of a specific device/version.'},
 {'url':'https://developer.chrome.com/blog/update-install-criteria','published_updated':'2023-12-05','scope':'Historical documented change to menu installation and Lighthouse PWA category, not a current cross-browser guarantee.'},
 {'url':'https://www.w3.org/TR/2026/WD-appmanifest-20261016/','edition':'Working Draft 2026-10-16','scope':'Manifest metadata; draft status explicitly retained.'},
 {'url':'https://www.w3.org/TR/2026/CRD-service-workers-20260917/','edition':'Candidate Recommendation Draft 2026-09-17','scope':'Cache lifetime/explicit management and persistent storage; no clinical/legal compliance inference.'}],
 'decision':'Initial conditional evaluation remains in progress. No manifest/worker/installation or sensitive offline cache implemented, no pilot, use-retention measurement or benefit claimed.'}
(DEST/'references.json').write_bytes((json.dumps(refs,indent=2)+'\n').encode())
shutil.copyfile(__file__,DEST/'seal-driver.py')
files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(DEST.iterdir())}
(DEST/'manifest.json').write_bytes((json.dumps({'files':files},indent=2)+'\n').encode())
print(json.dumps({'files':len(files),'manifest':hashlib.sha256((DEST/'manifest.json').read_bytes()).hexdigest()}))
