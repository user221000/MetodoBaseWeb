from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

root=Path('F:/MetodoBaseWeb-execution-20261018')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-recovery28-main-composition-20261019')
out.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.run(['git',*args],cwd=root,capture_output=True,check=True).stdout
head=git('rev-parse','HEAD').decode().strip()
assert head=='7cf4e6c996708f580054a798406ccdc3336a0fa6'
delta=git('diff','--name-only','92615d74ee3a4bd82333c4606cca7898eb324a88',head,'--','.',':!docs').decode().splitlines()
expected={'.github/workflows/ci.yml','.gitleaks.toml','scripts/scan_secrets.py',
          'tests/e2e/personal_diary_server.py','tests/test_secret_scan_fragment_pins.py',
          'tests/verify_recovery_ci.py','tests/verify_recovery_ci_baseline_trust.py'}
assert set(delta)==expected,delta
suffixes={'.py','.js','.cjs','.html','.css','.sql','.json','.toml','.yml','.yaml','.lock','.sh'}
paths=[p for p in git('ls-files','-z').decode().split('\0') if p and not p.startswith('docs/') and (root/p).suffix in suffixes]
photo=lambda:{p:sha((root/p).read_bytes()) for p in paths}
before=photo()
(out/'before-private.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
commands={
 'recovery-own6':[sys.executable,'tests/run_isolated.py','-q','tests/test_recovery28_review.py','--junitxml='+str(out/'own6.xml')],
 'ci28-composition':[sys.executable,'tests/verify_recovery_ci.py','--output',str(out/'ci28-verify'),'--verify-only'],
}
def execute(item):
    name,command=item
    run=subprocess.run(command,cwd=root,capture_output=True,timeout=90)
    (out/(name+'.log')).write_bytes(run.stdout+run.stderr)
    return name,run.returncode
with ThreadPoolExecutor(max_workers=2) as pool:
    exits=dict(pool.map(execute,commands.items()))
after=photo()
(out/'after-private.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
xml=ET.parse(out/'own6.xml').getroot()
suites=[xml] if xml.tag=='testsuite' else list(xml)
counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','errors','failures','skipped']}
status=git('status','--porcelain','--untracked-files=no').decode()
value={'main_commit':head,'accepted_recovery_composition':'92615d74ee3a4bd82333c4606cca7898eb324a88',
       'exact_non_document_delta':delta,'runtime_recovery_git_bytes_unchanged':True,
       'source_count':len(before),'sources_stable':before==after,
       'before_inventory_sha256':sha(json.dumps(before,sort_keys=True,separators=(',',':')).encode()),
       'after_inventory_sha256':sha(json.dumps(after,sort_keys=True,separators=(',',':')).encode()),
       'exits':exits,'junit_counts':counts,'tracked_status':status,
       'scope':'composition-only six independent maintained cases and CI28 verify-only; no broad/PG/restore/browser repetition',
       'private_raw_directory':str(out),
       'artifacts':{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file()}}
(out/'summary.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:value[k] for k in ['main_commit','source_count','sources_stable','exits','junit_counts']}))
assert before==after and not status and set(exits.values())=={0}
assert counts=={'tests':6,'errors':0,'failures':0,'skipped':0}
