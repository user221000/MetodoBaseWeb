from pathlib import Path
import ast,asyncio,hashlib,importlib.util,json,os,subprocess,sys,traceback,types
ROOT=Path('F:/mb-qa-native37-20261020');TASK=Path(__file__).resolve().parent;P=TASK/'private';P.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('native37_env_prepare',ROOT/'tests/e2e/native37_environment_qa.py');lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
PROFILE=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json');NODE=Path('C:/Program Files/nodejs/node.exe');CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe');DEPS=Path('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules')
before=lib.photograph(ROOT,TASK,'offline-before',PROFILE,NODE,CHROME,DEPS);lib.pipcheck(ROOT,TASK,'offline-before')
results=[]
def passed(name):results.append({'case':name,'passed':True})
def write(name,value):
 with (P/name).open('xb') as stream:stream.write(value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode())
for name in ['native37_postgres_server_qa_v2.py','run_native37_qa_v2.py']:
 source=(ROOT/'tests/e2e'/name).read_text();compile(source,name,'exec');passed('Python compile only '+name)
for name in ['native37_account_notifications_qa_v2.cjs']:
 value=subprocess.run([str(NODE),'--check','tests/e2e/'+name],cwd=ROOT,capture_output=True);write(name+'.syntax.stdout',value.stdout);write(name+'.syntax.stderr',value.stderr);assert value.returncode==0;passed('Node syntax only '+name)
value=subprocess.run([str(NODE),str(TASK/'observer_review.cjs')],cwd=ROOT,capture_output=True);write('observer.stdout',value.stdout);write('observer.stderr',value.stderr);assert value.returncode==0
observer=json.loads(value.stdout);assert observer['passed']==observer['total']==5;passed('Five pure Node observer/business-source controls')
def asserts(tree):return [ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.Assert)]
old_fixture=ast.parse((ROOT/'tests/e2e/native37_postgres_server_qa.py').read_text());new_fixture=ast.parse((ROOT/'tests/e2e/native37_postgres_server_qa_v2.py').read_text())
assert asserts(old_fixture)==asserts(new_fixture);passed('Every original fixture assert AST identical')
main=next(n for n in new_fixture.body if isinstance(n,ast.FunctionDef) and n.name=='main')
checkpoint=next(n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name=='shutdown_checkpoint')
observed=next(n for n in ast.walk(main) if isinstance(n,ast.ClassDef) and n.name=='ObservedServer')
diag=P/'diagnostic-pure-normal';diag.mkdir()
namespace={'asyncio':asyncio,'traceback':traceback,'sys':sys,'json':json,'diagnostic_directory':diag}
class BaseServer:
 async def shutdown(self,sockets=None):self.called=True;await asyncio.sleep(0)
namespace['uvicorn']=types.SimpleNamespace(Server=BaseServer)
exec(compile(ast.fix_missing_locations(ast.Module(body=[checkpoint,observed],type_ignores=[])),'pure-diagnostic-extract','exec'),namespace)
async def normal():
 server=namespace['ObservedServer']();await server.shutdown();assert server.called
 await asyncio.sleep(0);assert len(asyncio.all_tasks())==1
asyncio.run(normal())
assert set(x.name for x in diag.iterdir())=={'uvicorn-shutdown-enter.json','uvicorn-shutdown-returned.json'}
for path in diag.iterdir():
 value=json.loads(path.read_bytes());assert value['no_locals_SQL_params_values'] is True
 for item in value['threads']:
  assert len(item['frames'])<=8 and all(set(frame)=={'file','function','line'} for frame in item['frames'])
passed('ObservedServer retains normal shutdown and cancels only its own diagnostic monitor')
class FailingBase:
 async def shutdown(self,sockets=None):raise RuntimeError('synthetic shutdown exception')
faildir=P/'diagnostic-pure-failure';faildir.mkdir();namespace['uvicorn']=types.SimpleNamespace(Server=FailingBase);namespace['diagnostic_directory']=faildir
exec(compile(ast.fix_missing_locations(ast.Module(body=[observed],type_ignores=[])),'pure-diagnostic-error-extract','exec'),namespace)
async def failing():
 try:await namespace['ObservedServer']().shutdown()
 except RuntimeError:pass
 else:raise AssertionError('Original shutdown failure must propagate')
 await asyncio.sleep(0);assert len(asyncio.all_tasks())==1
asyncio.run(failing());passed('ObservedServer propagates original shutdown error without leaked monitor task')

launcher=ast.parse((ROOT/'tests/e2e/run_native37_qa_v2.py').read_text());launchmain=next(n for n in launcher.body if isinstance(n,ast.FunctionDef) and n.name=='main')
guard_index=next(i for i,n in enumerate(launchmain.body) if isinstance(n,ast.Assert) and ast.unparse(n.test)=='server_result == 0')
guard=launchmain.body[guard_index:guard_index+3]
guard_root=P/'close-guard';guard_root.mkdir();close=guard_root/'close.json'
for exit_code,closed,accepted in [(0,True,True),(1,True,False),(0,False,False),(0,None,False)]:
 if closed is not None:close.write_text(json.dumps({'normal_owned_context_closed':closed}))
 elif close.exists():close.unlink()
 try:exec(compile(ast.fix_missing_locations(ast.Module(body=guard,type_ignores=[])),'actual-launcher-close-guard','exec'),{'server_result':exit_code,'json':json,'P':guard_root})
 except (AssertionError,FileNotFoundError):actual=False
 else:actual=True
 assert actual is accepted
passed('Actual launcher guard rejects nonzero exit, false close and missing close; positive requires both')
branch=next(n for n in launchmain.body if isinstance(n,ast.If) and ast.unparse(n.test)=='stop_timeout')
probe=ast.FunctionDef(name='probe_timeout',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[branch,ast.Return(value=ast.Constant(0))],decorator_list=[])
events=[]
namespace={'stop_timeout':True,'before':{'head':'same'},'lib':types.SimpleNamespace(pipcheck=lambda *a:events.append('pipcheck')),
 'ROOT':ROOT,'TASK':TASK,'reports':[],'inventory':lambda *a:events.append('inventory'),
 'fingerprint_snapshot':lambda *a:{'head':'same'},'put':lambda name,value:events.append((name,value)),
 'print':lambda *a,**kw:None,'json':json}
exec(compile(ast.fix_missing_locations(ast.Module(body=[probe],type_ignores=[])),'actual-launcher-timeout-branch','exec'),namespace)
assert namespace['probe_timeout']()==1
receipt=next(value for name,value in events if isinstance(name,str) and name=='phase-retained-timeout-summary.json') if False else [event[1] for event in events if isinstance(event,tuple)][0]
assert receipt['verdict']=='REJECTED' and receipt['owned_resource_retained'] is True and receipt['normal_server_exit'] is False
assert receipt['no_termination_DROP_cancellation_performed'] is True
passed('Actual timeout branch preserves photo/retention and returns REJECTED without termination or DROP')
after=lib.photograph(ROOT,TASK,'offline-after',PROFILE,NODE,CHROME,DEPS);lib.pipcheck(ROOT,TASK,'offline-after')
stable={key:before[key]==after[key] for key in before};assert all(stable.values())
write('offline-summary.json',{'scope':'Pure syntax/source/observer/close-guard tests only. No service, PG, Chrome, load or runtime shutdown reproduction.',
 'results':results,'passed':len(results),'total':len(results),'Node_observer_subcases':5,'stable':stable,
 'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),
 'Node_files':len(before['node_files']),'pip_before':0,'pip_after':0,'all_services_not_started':True})
print(json.dumps({'passed':len(results),'total':len(results),'Node_observer_subcases':5,'all_fields_stable':True,
 'source_files':len(before['source']),'packages':len(before['packages']),'installed_files':len(before['installed']),'Node_files':len(before['node_files']),'pip':0}))
