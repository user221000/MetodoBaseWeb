from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
R=Path('F:/mb-qa-native37-20261020');T=Path(__file__).resolve().parent;P=T/'private'
NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe');DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
RESOURCE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-followup34-author-native-mfa35-dom-qa-20261020/launch.py')
SNAPSHOT=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-nutrition35-saas-20261020/phase.py')
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
lib=load('snapshot37',SNAPSHOT);lib.ROOT=R;lib.TASK=T;lib.PRIVATE=P
res=load('resources37',RESOURCE);res.ROOT=R;res.TASK=T;res.P=P

def photo(label):
 data=lib.snapshot(label);data.update(Node_sha256=sha(NODE.read_bytes()),Chrome_sha256=sha(CHROME.read_bytes()),Python_base_sha256=sha(Path(sys._base_executable).read_bytes()),resource_helper_sha256=sha(RESOURCE.read_bytes()),snapshot_helper_sha256=sha(SNAPSHOT.read_bytes()),Node_files={p.relative_to(DEPS).as_posix():sha(p.read_bytes()) for p in sorted(DEPS.rglob('*')) if p.is_file()})
 (P/(label+'-full.json')).write_bytes((json.dumps(data,indent=2)+'\n').encode());return data

def main():
 assert not (T/'geometry-before-summary.json').exists()
 before=photo('geometry-before');lib.pipcheck('geometry-before')
 initial=res.inventory('geometry-before');inventories=[initial]
 ram=[]
 for i in range(2):
  command="$x=Get-CimInstance Win32_OperatingSystem; [pscustomobject]@{utc=[DateTime]::UtcNow.ToString('o');physical_GiB=[math]::Round($x.FreePhysicalMemory/1MB,3);virtual_GiB=[math]::Round($x.FreeVirtualMemory/1MB,3)} | ConvertTo-Json -Compress"
  raw=subprocess.check_output(['powershell','-NoProfile','-Command',command]);(P/('geometry-RAM-'+str(i)+'.json')).write_bytes(raw);row=json.loads(raw);assert row['physical_GiB']>=2.4;ram.append(row)
  if i==0:time.sleep(2)
 env=dict(os.environ,TEMP=str(P),TMP=str(P),METODOBASE_E2E_DEPENDENCIES=str(DEPS),CHROME_PATH=str(CHROME),QA37_GEOMETRY_OUTPUT=str(P/'geometry-before-output'))
 with (P/'geometry-before.stdout').open('xb') as out,(P/'geometry-before.stderr').open('xb') as err:
  child=subprocess.Popen([str(NODE),'tests/e2e/mobile_heading37_geometry.cjs'],cwd=R,env=env,stdout=out,stderr=err)
  birth=res.birth(child.pid);assert birth
  (P/'geometry-Node-identity.json').write_text(json.dumps({'pid':child.pid,'birth':birth}),encoding='utf-8')
  i=0
  while child.poll() is None:
   inventories.append(res.inventory('geometry-live-'+str(i)));i+=1
   if i>30:raise TimeoutError('Geometry diagnostic unexpectedly exceeds bounded lifecycle')
   time.sleep(.5)
  result=child.wait()
 final=res.inventory('geometry-after');inventories.append(final)
 owned,rejected=res.own_chrome_rows(inventories,{child.pid:birth})
 statuses=[res.status(row['pid'],row['birth']) for row in owned]+[res.status(child.pid,birth)]
 old={(r['ProcessId'],r['birth']) for r in initial['processes'] if r['Name'].lower() in {'chrome.exe','msedge.exe'} and r['birth'] is not None}
 current={(r['ProcessId'],r['birth']) for r in final['processes'] if r['Name'].lower() in {'chrome.exe','msedge.exe'} and r['birth'] is not None}
 assert old==current
 listeners=lambda value:{(r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in value['listeners']}
 assert listeners(initial)==listeners(final)
 report=json.loads((P/'geometry-before-output/report.json').read_bytes());assert report['complete'] and len(report['cases'])==16 and report['pageErrors']==[] and report['external']==[]
 assert result==(1 if any(not row['passed'] for row in report['cases']) else 0)
 after=photo('geometry-after');lib.pipcheck('geometry-after');quiet={k:before[k]==after[k] for k in before};assert all(quiet.values())
 value={'source_head':before['head'],'scope':'Synthetic inert real CSS/markup geometry only; no app/auth/SQL','exit_code':result,'cases':len(report['cases']),'passed':sum(row['passed'] for row in report['cases']),'failed':sum(not row['passed'] for row in report['cases']),'pageErrors':0,'RAM':ram,'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'Node_files':len(before['Node_files']),'quiet':quiet,'pip':[0,0],'own_process_statuses':statuses,'rejected_generation_attributions':rejected,'foreign_browsers_and8776_preserved':True,'no_listener_opened':True,'SQL_or_PG_used':False,'lease_Chrome_released':True}
 (T/'geometry-before-summary.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:value[k] for k in ['source_head','cases','passed','failed','source_files','packages','installed_files','Node_files','quiet','pip','lease_Chrome_released']}))
if __name__=='__main__':main()
