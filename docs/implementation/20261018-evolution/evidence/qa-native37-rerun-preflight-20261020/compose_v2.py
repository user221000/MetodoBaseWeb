from pathlib import Path
import hashlib,json
ROOT=Path('F:/mb-qa-native37-20261020');HERE=Path(__file__).resolve().parent
def sha(blob):return hashlib.sha256(blob).hexdigest()
def replacement(source,old,new):
    assert source.count(old)==1,old[:80]
    return source.replace(old,new)
old_driver=(ROOT/'tests/e2e/native37_account_notifications_qa.cjs').read_text(encoding='utf-8')
driver=replacement(old_driver,".textContent.includes('No se confirmó')",".textContent.includes('El resultado es incierto')")
old_track="async function trackedPage(ctx){const page=await ctx.newPage();page.on('pageerror',error=>report.pageErrors.push({class:error.name}));return page;}"
new_track="""// Additive private observer. No error message, full URL, query, hash, bearer or DOM values.
const observerPath=path.join(privateRoot,'page-errors-observer.private.ndjson');
fs.writeFileSync(observerPath,'',{flag:'wx'});
const observerScripts=new Set(fs.readdirSync(path.join(__dirname,'../../web/static/js')).filter(name=>name.endsWith('.js')).map(name=>'/static/js/'+name));
const observerPages=new Set(['/recordatorios','/mis-recordatorios','/cuenta/seguridad','/mi-seguridad','/configuracion','/mi-perfil','/login-gym','/login-usuario','/auth/verify-email']);
function errorObservation(error,base,allowedScripts,allowedPages,currentCase){
 const classes=new Set(['Error','TypeError','ReferenceError','SyntaxError','RangeError','URIError','EvalError']);
 const frames=[];for(const line of String(error.stack||'').split('\\n').slice(1,20)){
  const match=/(https?:\\/\\/[^\\s)]+):(\\d+):(\\d+)/.exec(line);if(!match)continue;
  let url;try{url=new URL(match[1]);}catch{continue;}
  if(url.origin!==base||(!allowedScripts.has(url.pathname)&&!allowedPages.has(url.pathname)))continue;
  const row={pathname:url.pathname,line:Number(match[2]),column:Number(match[3])};
  if(Number.isSafeInteger(row.line)&&row.line>0&&Number.isSafeInteger(row.column)&&row.column>0)frames.push(row);
  if(frames.length===8)break;
 }
 return {class:classes.has(error.name)?error.name:'OtherError',case:currentCase||null,frames};
}
async function trackedPage(ctx){const page=await ctx.newPage();page.on('pageerror',error=>{report.pageErrors.push({class:error.name});fs.appendFileSync(observerPath,JSON.stringify(errorObservation(error,base,observerScripts,observerPages,report.current_case))+'\\n');});return page;}"""
driver=replacement(driver,old_track,new_track)
assert driver.replace(new_track,old_track).replace(".textContent.includes('El resultado es incierto')",".textContent.includes('No se confirmó')")==old_driver
newpath=ROOT/'tests/e2e/native37_account_notifications_qa_v2.cjs';assert not newpath.exists();newpath.write_bytes(driver.encode())

old_fixture=(ROOT/'tests/e2e/native37_postgres_server_qa.py').read_text(encoding='utf-8')
fixture=old_fixture
old_server='''            server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=args.port,
                log_level="warning", access_log=False))'''
new_server='''            # Private shutdown observation only. No query/params/locals or forced cancellation.
            import asyncio
            import traceback
            diagnostic_directory = private / "shutdown-diagnostics"
            diagnostic_directory.mkdir(exist_ok=False)
            def shutdown_checkpoint(stage):
                tasks = []
                try:
                    current = asyncio.current_task()
                    for task in list(asyncio.all_tasks())[:80]:
                        frames = [{"file": frame.f_code.co_filename, "function": frame.f_code.co_name,
                            "line": frame.f_lineno} for frame in task.get_stack(limit=8)]
                        tasks.append({"task_identity": id(task), "current_diagnostic_task": task is current,
                            "done": task.done(), "cancelled": task.cancelled(), "frames": frames})
                except RuntimeError:
                    pass  # Watcher/main outside the ASGI loop still records bounded thread frames.
                threads = [{"thread_identity": identifier,
                    "frames": [{"file": item.filename, "function": item.name, "line": item.lineno}
                        for item in traceback.extract_stack(frame, limit=8)]}
                    for identifier, frame in list(sys._current_frames().items())[:80]]
                path = diagnostic_directory / (stage + ".json")
                with path.open("xb") as receipt:
                    receipt.write((json.dumps({"stage": stage, "tasks": tasks, "threads": threads,
                        "private_frame_metadata_only": True, "no_locals_SQL_params_values": True}) + "\\n").encode())
            class ObservedServer(uvicorn.Server):
                async def shutdown(self, sockets=None):
                    shutdown_checkpoint("uvicorn-shutdown-enter")
                    async def observe_pending_shutdown():
                        for seconds in (1, 4, 10, 15):
                            await asyncio.sleep(seconds)
                            shutdown_checkpoint("uvicorn-shutdown-pending-" + str(seconds))
                    observation = asyncio.create_task(observe_pending_shutdown())
                    try:
                        await super().shutdown(sockets=sockets)
                        shutdown_checkpoint("uvicorn-shutdown-returned")
                    finally:
                        observation.cancel()
                        try:
                            await observation
                        except asyncio.CancelledError:
                            pass
            server = ObservedServer(uvicorn.Config(create_app(), host="127.0.0.1", port=args.port,
                log_level="warning", access_log=False))'''
fixture=replacement(fixture,old_server,new_server)
patches=[
 ('                        server.should_exit = True\n','                        shutdown_checkpoint("stop-file-detected")\n                        server.should_exit = True\n'),
 ('                server.run()\n','                server.run()\n                shutdown_checkpoint("server-run-returned")\n'),
 ('                watcher_done.set()\n','                shutdown_checkpoint("fixture-finalizer-enter")\n                watcher_done.set()\n'),
 ('                runtime = None\n','                runtime = None\n                shutdown_checkpoint("fixture-runtime-disposed")\n'),
 ('        closed = True\n','        closed = True\n        shutdown_checkpoint("owned-context-closed")\n')]
for old,new in patches:fixture=replacement(fixture,old,new)
inverse=fixture
for old,new in reversed(patches):inverse=replacement(inverse,new,old)
inverse=replacement(inverse,new_server,old_server);assert inverse==old_fixture
fixturepath=ROOT/'tests/e2e/native37_postgres_server_qa_v2.py';assert not fixturepath.exists();fixturepath.write_bytes(fixture.encode())

old_launcher=(ROOT/'tests/e2e/run_native37_qa.py').read_text(encoding='utf-8')
launcher=old_launcher.replace('native37_postgres_server_qa.py','native37_postgres_server_qa_v2.py').replace('native37_account_notifications_qa','native37_account_notifications_qa_v2')
launcher=replacement(launcher,'server=None;server_result=None;failure=None;server_identity=None;produced=None','server=None;server_result=None;failure=None;server_identity=None;produced=None;stop_timeout=False')
old_timeout='''                raise
        server_out.close();server_err.close()
    final=inventory('after');'''
new_timeout='''                stop_timeout=True
        server_out.close();server_err.close()
    if stop_timeout:
        inventory('retained-after-timeout')
        retained=fingerprint_snapshot('retained-after-timeout',lib);lib.pipcheck(ROOT,TASK,'retained-after-timeout')
        stable={key:before[key]==retained[key] for key in before}
        assert all(stable.values())
        put('phase-retained-timeout-summary.json',{'verdict':'REJECTED','normal_server_exit':False,
            'server_stop_timeout':True,'manual_cleanup_required':True,'owned_resource_retained':True,
            'no_termination_DROP_cancellation_performed':True,'reports':reports,'stable':stable})
        print(json.dumps({'phase':'REJECTED_retained_own_server_timeout','no_automatic_retry':True}),flush=True)
        return 1
    assert server_result==0, 'Fixture must exit zero; no native acceptance with finalizer failure'
    close=json.loads((P/'close.json').read_bytes())
    assert close['normal_owned_context_closed'] is True
    final=inventory('after');'''
launcher=replacement(launcher,old_timeout,new_timeout)
launcherpath=ROOT/'tests/e2e/run_native37_qa_v2.py';assert not launcherpath.exists();launcherpath.write_bytes(launcher.encode())
inverse_launcher=launcher.replace(new_timeout,old_timeout).replace('server=None;server_result=None;failure=None;server_identity=None;produced=None;stop_timeout=False','server=None;server_result=None;failure=None;server_identity=None;produced=None').replace('native37_postgres_server_qa_v2.py','native37_postgres_server_qa.py').replace('native37_account_notifications_qa_v2','native37_account_notifications_qa')
assert inverse_launcher==old_launcher
receipt={'new_files':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in [newpath,fixturepath,launcherpath]},
 'driver_full_inverse_exact_normalized_EOL':True,'fixture_full_inverse_exact_normalized_EOL':True,'launcher_full_inverse_exact_normalized_EOL':True,
 'original_RAWs_unchanged':{name:sha((ROOT/name).read_bytes()) for name in ['tests/e2e/native37_account_notifications_qa.cjs','tests/e2e/native37_postgres_server_qa.py','tests/e2e/run_native37_qa.py']},
 'changes':'New derivative files only: one unreached literal wait; additive bounded private page-error observation; shutdown stage/task/thread frames without runtime/cancellation policy change; launcher retains rejected timeout with source photo and requires zero exit plus close receipt.'}
(HERE/'composition-receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
