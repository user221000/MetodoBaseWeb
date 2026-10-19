"""Seal only public real-browser evidence; never copy the private fixture phase."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import psycopg2
root=Path(r'F:\mb-r12-ci29-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-portable-browser-first-20261019')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='6c9347d226f57b967f4bb881ab005920f6c9b238'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
summary=json.loads((out/'summary.json').read_bytes());assert summary['exit_code']==0 and summary['sources_packages_tools_config_stable'] is True
assert summary['foreign_chrome_preserved'] and summary['new_Chrome_process_IDs']==[]
configuration=json.loads(Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
closure=json.loads((out/'public/database-closure.json').read_bytes());assert closure['count']==1 and closure['all_owned_absent']
with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as db,db.cursor() as cursor:
    cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(closure['exact_owned_names'],));remaining=[row[0] for row in cursor.fetchall()]
assert remaining==[]
(out/'independent-db-absence.json').write_text(json.dumps({'exact_owned_names':closure['exact_owned_names'],'remaining':remaining,'readonly_catalog_check':True},indent=2)+'\n',encoding='utf8')
ev=root/'docs/implementation/20261018-evolution/evidence/ci-member-links29-browser-author-20261019';ev.mkdir(exist_ok=False)
(ev/'.gitattributes').write_bytes(b'* -text\n')
public=json.loads((out/'public/receipt.json').read_bytes())['public_files']+['receipt.json']
(ev/'public').mkdir()
for name in public:shutil.copyfile(out/'public'/name,ev/'public'/name)
for name in ['summary.json','before.json','after.json','before-pip.log','after-pip.log','foreign-chrome-before.json','foreign-chrome-after.json','orchestrator.stdout.log','orchestrator.stderr.log','independent-db-absence.json']:
    shutil.copyfile(out/name,ev/name)
for name in ['metodobase-ci29-portable-browser-run.py','metodobase-ci29-portable-browser-seal.py']:shutil.copyfile(Path(__file__).parent/name,ev/name)
sha=lambda value:hashlib.sha256(value).hexdigest()
manifest={'head':summary['head'],'scope':summary['scope'],'passed_browser_criteria':16,'owned_uuid_closed_and_independently_absent':True,'own_listener_closed':True,'foreign_chrome_preserved':True,'no_remaining_new_Chrome_processes':True,'source_package_tool_config_stability':True,'sources':5292,'packages':89,'Node_dependency_files':157,'private_phase_copied':False,'files':{path.relative_to(ev).as_posix():{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())} for path in sorted(ev.rglob('*')) if path.is_file()}}
(ev/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
token=re.compile(rb'[A-Za-z0-9_-]{30,}\.[a-f0-9]{64}(?![a-f0-9])')
for path in ev.rglob('*'):
    if path.is_file() and path.suffix in {'.json','.log','.jsonl'}:assert not token.search(path.read_bytes()),path
raw=sorted(path.relative_to(root).as_posix() for path in ev.rglob('*') if path.is_file())
for index in range(0,len(raw),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
for name in raw:assert subprocess.check_output(['git','show',':'+name],cwd=root)==(root/name).read_bytes(),name
assert set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1])==set(raw)
subprocess.run(['git','commit','-m','Preserve actual portable member browser and exact resource closure'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'manifest_sha256':sha((ev/'manifest.json').read_bytes()),'RAW_blobs':len(raw),'browser_passed':16}))
