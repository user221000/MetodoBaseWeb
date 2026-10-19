from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.metadata as metadata,json,os,re,subprocess,sys,time

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
ROOT=LAB/'evidence/recovery28-image-abd559a-final'
OUT=ROOT/'sca';OUT.mkdir(exist_ok=False)
HEAD='abd559a9ea3227e6c3bdb141241c11f7196c7682'
assert metadata.version('pip-audit')=='2.10.1'
assert Path(sys.prefix).name=='metodobase-candidate-web-20261018'
def sha(data):return hashlib.sha256(data).hexdigest()
def info(path):return {'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}
def dependencies():
    packages=[];files={}
    for package in metadata.distributions():
        packages.append({'name':package.metadata['Name'],'version':package.version})
        for item in package.files or []:
            path=Path(package.locate_file(item)).resolve()
            if path.is_file():files[str(path)]=info(path)
    return {'packages':sorted(packages,key=lambda p:p['name'].lower()),'files':files}
source_baseline=json.loads((ROOT/'before.json').read_text())
REPO=Path(r'F:\MetodoBaseWeb-image-pip-20261019')
def sources():
    return {'tracked_sources':{rel:info(REPO/rel) for rel in source_baseline['tracked_sources']},
            'git_controls':{path:info(Path(path)) if Path(path).is_file() else None for path in source_baseline['git_controls']}}
before={'dependencies':dependencies(),'sources':sources()}
assert before['sources']==source_baseline
(OUT/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
inventory=(ROOT/'runtime-inventory.json').read_bytes();value=json.loads(inventory)
rows=value['runtime_inventory']['packages']
assert len(rows)==55 and len({re.sub(r'[-_.]+','-',p['name']).lower() for p in rows})==55
for package in rows:
    assert re.fullmatch(r'[A-Za-z0-9_.-]+',package['name']) and re.fullmatch(r'[A-Za-z0-9_.+!-]+',package['version'])
requirements=OUT/'actual-image-55.txt'
requirements.write_text(''.join(p['name']+'=='+p['version']+'\n' for p in rows),encoding='utf-8',newline='\n')
command=[sys.executable,'-B','-m','pip_audit','--no-deps','--disable-pip','--strict','--vulnerability-service','osv',
 '--progress-spinner','off','--cache-dir',str(OUT/'cache'),'--format','json','--output',str(OUT/'audit.json'),'-r',str(requirements)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
started=time.monotonic();run=subprocess.run(command,capture_output=True,timeout=300,env=env)
(OUT/'audit.log').write_bytes(run.stdout+run.stderr)
check=subprocess.run([sys.executable,'-B','-m','pip','check'],capture_output=True,timeout=60,env=env)
(OUT/'tool-pip-check.log').write_bytes(check.stdout+check.stderr)
after={'dependencies':dependencies(),'sources':sources()}
(OUT/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
summary={'finished_utc':datetime.now(timezone.utc).isoformat(),'image_id':value['image_id'],'image_source':HEAD,
 'runtime_inventory_sha256':sha(inventory),'actual_distributions':55,'tool':'pip-audit 2.10.1','service':'OSV',
 'scope':'Exact Python distributions installed in Linux product image. Excludes Debian OS packages, source-built CPython and application behavior.',
 'command':command,'exit':run.returncode,'seconds':round(time.monotonic()-started,3),'tool_pip_check_exit':check.returncode,
 'requirements_sha256':sha(requirements.read_bytes()),'source_and_tool_dependencies_stable':before==after,
 'tool_distributions':len(before['dependencies']['packages']),'tool_tracked_files':len(before['dependencies']['files'])}
if (OUT/'audit.json').is_file():
    audit=json.loads((OUT/'audit.json').read_text())
    summary['audited_dependencies']=len(audit['dependencies'])
    summary['vulnerability_count']=sum(len(p.get('vulns',[])) for p in audit['dependencies'])
    canonical=lambda name:re.sub(r'[-_.]+','-',name).lower()
    audited={canonical(p['name']):p['version'] for p in audit['dependencies']}
    assert audited=={canonical(p['name']):p['version'] for p in rows}
summary['artifacts']={p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
assert before==after and check.returncode==0
assert run.returncode==0 and summary.get('audited_dependencies')==55 and summary.get('vulnerability_count')==0
