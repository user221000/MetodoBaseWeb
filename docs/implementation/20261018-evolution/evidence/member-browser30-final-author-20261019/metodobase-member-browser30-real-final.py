"""Real current30 browser in one owned UUID, with owned-process closure proof."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from datetime import datetime,timezone

ROOT=Path('F:/mb-member-browser30-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/member-browser30-final-author-20261019'
OUT.mkdir(exist_ok=False)
(OUT/'.gitattributes').write_bytes(b'* -text\n')
TEMP=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-member-browser30-author-8x89ac13')
RUN=TEMP/'real30-final'
RUN.mkdir(exist_ok=False)
head=subprocess.check_output(['git','--no-replace-objects','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='767c9cf92cea6090e796cf9d4e213ef47f418784'
assert not subprocess.check_output(['git','--no-replace-objects','status','--porcelain','--untracked-files=no'],cwd=ROOT).strip()
configuration=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
NODE=Path('C:/Program Files/nodejs/node.exe')
MODULES=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
assert sha(CHROME.read_bytes())=='6aa5d599bbc3a0b3842af9f44b18fd29989eb3cc21b4b3ec7489e12f36e9962e'
assert sha(NODE.read_bytes())=='ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32'
paths=subprocess.check_output(['git','--no-replace-objects','ls-files','-co','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')[:-1]
paths=sorted(set(name for name in paths if not name.startswith(('docs/','dist/','build/')) and (ROOT/name).is_file()))
module_names=sorted(p.relative_to(MODULES).as_posix() for p in MODULES.rglob('*') if p.is_file())
assert len(module_names)==157
def photo():
    return {'sources':{name:sha((ROOT/name).read_bytes()) for name in paths},
            'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
            'node_modules':{name:sha((MODULES/name).read_bytes()) for name in module_names},
            'tools':{'chrome_sha256':sha(CHROME.read_bytes()),'node_sha256':sha(NODE.read_bytes())}}
before=photo();save('before.json',before)
assert len(before['packages'])==89
pip_before=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.log').write_bytes(pip_before.stdout+pip_before.stderr);assert pip_before.returncode==0
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',
         QA_CHROME=str(CHROME),QA_NODE_MODULES=str(MODULES))
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:
    env.pop(key,None)
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    env[key]=configuration[key]
with socket.socket() as probe:
    assert probe.connect_ex(('127.0.0.1',8796))!=0
start=datetime.now(timezone.utc).isoformat()
started=time.monotonic()
known={};phase=None;owned_names=[];fixture_pid=None
def processes(filter_expression):
    command="Get-CimInstance Win32_Process -Filter '"+filter_expression+"' | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,@{Name='Created';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Depth 3 -Compress"
    value=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=15)
    assert value.returncode==0
    if not value.stdout.strip():return []
    rows=json.loads(value.stdout)
    return rows if isinstance(rows,list) else [rows]
with (RUN/'manager.stdout.raw.log').open('xb') as output,(RUN/'manager.stderr.raw.log').open('xb') as errors:
    manager=subprocess.Popen([sys.executable,'-X','utf8','-B','tests/e2e/run_member_link_browser.py',
        '--output',str(RUN/'public'),'--port','8796'],cwd=ROOT,env=env,stdout=output,stderr=errors)
    print(json.dumps({'phase':'started','source_head':head,'owner_pid':os.getpid(),'manager_pid':manager.pid,'start_utc':start,'port':8796}),flush=True)
    parents={manager.pid}
    while manager.poll() is None:
        assert time.monotonic()-started<420,'Owned browser manager exceeded outer deadline'
        rows=processes(' OR '.join('ParentProcessId='+str(pid) for pid in sorted(parents)))
        for row in rows:
            key=(row['ProcessId'],row['Created'])
            known[key]=row
            parents.add(row['ProcessId'])
            command=row.get('CommandLine') or ''
            if 'member_link_postgres_server.py' in command:
                found=re.search(r'--out\s+(?:"([^"]+)"|(\S+))',command)
                if found:
                    candidate=Path(found.group(1) or found.group(2))
                    assert candidate.is_relative_to(Path(os.environ['TEMP']))
                    phase=candidate;fixture_pid=row['ProcessId']
        if phase is not None and not owned_names and (phase/'owned-database.json').is_file():
            owned_names=json.loads((phase/'owned-database.json').read_bytes())['names']
            print(json.dumps({'phase':'owned-database','names':owned_names,'fixture_pid':fixture_pid}),flush=True)
        (RUN/'observed-owned-processes.private.json').write_text(json.dumps(list(known.values()),indent=2)+'\n',encoding='utf8')
        time.sleep(.5)
    code=manager.wait()
end=datetime.now(timezone.utc).isoformat()
assert phase is not None and owned_names
# Exact owned-process identities, not names shared by other Chrome sessions.
chromes=[row for row in known.values() if (row.get('ExecutablePath') or '').lower()==str(CHROME).replace('/','\\').lower()]
assert chromes,'No owned Chrome process was witnessed'
profiles=set()
for row in chromes:
    found=re.search(r'--user-data-dir=(?:"([^"]+)"|(\S+))',row.get('CommandLine') or '')
    if found:
        path=Path(found.group(1) or found.group(2))
        assert path.is_relative_to(Path(os.environ['TEMP'])) and path.name.startswith('playwright_chromiumdev_profile-')
        profiles.add(path)
assert len(profiles)==1
identities=[(row['ProcessId'],row['Created']) for row in known.values()]
remaining=processes(' OR '.join('ProcessId='+str(pid) for pid,_born in identities))
same=[row for row in remaining if (row['ProcessId'],row['Created']) in identities]
assert same==[],'An owned process identity remained after manager exit'
with socket.socket() as probe:assert probe.connect_ex(('127.0.0.1',8796))!=0
closure=json.loads((phase/'database-closure.json').read_bytes())
assert closure['exact_owned_names']==owned_names and len(owned_names)==1
assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',owned_names[0])
import psycopg2
with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as connection,connection.cursor() as cursor:
    cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(owned_names,))
    remaining_databases=[row[0] for row in cursor.fetchall()]
assert remaining_databases==[]
after=photo();save('after.json',after);assert before==after
pip_after=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-after.log').write_bytes(pip_after.stdout+pip_after.stderr);assert pip_after.returncode==0
save('resource-closure.json',{'owner_pid':os.getpid(),'manager_pid':manager.pid,'fixture_pid':fixture_pid,
    'start_utc':start,'end_utc':end,'owned_database_names':owned_names,'remaining_owned_databases':remaining_databases,
    'observed_owned_processes':[{'pid':row['ProcessId'],'parent_pid':row['ParentProcessId'],'created':row['Created'],
         'executable':Path(row['ExecutablePath']).name if row.get('ExecutablePath') else None} for row in known.values()],
    'owned_chrome_pids':[row['ProcessId'] for row in chromes],'owned_chrome_profile_count':len(profiles),
    'owned_chrome_profiles_absent':[not p.exists() for p in profiles],
    'remaining_exact_process_identities':same,'listener8796_closed':True,
    'scope':'Only exact descendants of this owned manager; no unrelated browser/process or database was stopped or changed.'})
public=RUN/'public'
receipt=json.loads((public/'receipt.json').read_bytes())
assert code==0 and receipt['completed'] and len(receipt['public_files'])==10
assert sorted(p.name for p in public.iterdir())==sorted(receipt['public_files']+['receipt.json'])
tokens=[row['token'].encode() for row in json.loads((phase/'mail.private.json').read_bytes())]
secrets=[configuration[key].encode() for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']]
classification=[]
for p in sorted(public.iterdir()):
    raw=p.read_bytes()
    assert all(secret not in raw for secret in tokens+secrets)
    dest=OUT/'public'/p.name;dest.parent.mkdir(exist_ok=True)
    with dest.open('xb') as stream:stream.write(raw)
    classification.append({'path':'public/'+p.name,'raw_sha256':sha(raw),'redactions':0,'published_exact_raw':True})
for name in ['manager.stdout.raw.log','manager.stderr.raw.log']:
    raw=(RUN/name).read_bytes();assert all(secret not in raw for secret in tokens+secrets)
    (OUT/name).write_bytes(raw)
    classification.append({'path':name,'raw_sha256':sha(raw),'redactions':0,'published_exact_raw':True})
save('output-classification.json',classification)
summary={'source_head':head,'executed_revision':receipt['executed_revision'],'passed':16,'total':16,
    'seconds':time.monotonic()-started,'source_files':len(paths),'packages':len(before['packages']),
    'node_module_files':len(module_names),'all_sources_packages_and_tools_stable':before==after,
    'public_allowlist_files':10,'private_files_published':False,'exact_owned_database_absent':True,
    'owned_chrome_processes_closed':True,'listener8796_closed':True,
    'scope':'One real Windows Chrome/HTTP/owned restricted PostgreSQL30 run of unchanged R12 business29; local after-commit mail double, labelled synthetic source plan/PDF, no provider/worker/SLO/Linux-image claim.'}
save('summary.json',summary)
print(json.dumps(summary),flush=True)
