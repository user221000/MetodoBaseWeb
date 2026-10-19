/* Offline VM contracts only. This does not claim Chrome, layout or real HTTP. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname,'../..');
const tests=[];function test(name,body){tests.push({name,body});}
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
const payload=(rows=[])=>({as_of:'2026-10-19T18:00:00+00:00',window_days:30,has_more:false,
  payment_evidence:'unavailable',responsibility:'not_recorded',capabilities:{review_client:true,prepare_plan:true},
  metrics:{plans_saved:2,generation_operations_completed:1,pdf_metadata_ready:0},
  items:rows.map(id=>({id_cliente:id,nombre:'<img src=x onerror=synthetic()>',causes:['no_saved_plan'],priority:1,
    last_plan_at:null,elapsed_days:null,membership_end:null,responsible:null}))});
function fixture(read=async()=>payload(['client-a']),render=()=>{}){
  let revision=0,canonical='A',calls=0;
  const api={contexto:async()=>({revision,subject:canonical}),
    validarContexto:c=>{if(c.revision!==revision)throw Object.assign(new Error('changed'),{code:'session_changed'});},
    verificarContexto:async c=>{api.validarContexto(c);if(c.subject!==canonical)throw Object.assign(new Error('role'),{code:'session_changed'});},
    seguimiento:async(...args)=>{calls++;return read(...args);}};
  const context={window:{},document:{getElementById:()=>null},console};vm.createContext(context);
  vm.runInContext(fs.readFileSync(root+'/web/static/js/dashboard-seguimiento.js','utf8'),context);
  const controller=context.window.DashboardFollowup.create(api,s=>render(controller,s));
  return{controller,api,calls:()=>calls,replace:()=>revision++,role:()=>canonical='B'};
}
test('Confirmed empty is distinct from unavailable and never asserts payments',async()=>{
  const e=fixture(async()=>payload());await e.controller.load();assert.equal(e.controller.state.items.length,0);
  assert.ok(e.controller.state.asOf);assert.equal(e.controller.state.error,'');
});
test('Fields are projected and unsafe names remain plain strings for textContent',async()=>{
  const raw=payload(['a']);raw.items[0].notes='private';const e=fixture(async()=>raw);await e.controller.load();
  assert.equal(e.controller.state.items[0].notes,undefined);assert.match(e.controller.state.items[0].nombre,/<img/);
});
test('Duplicate clicks run only one read',async()=>{
  const gate=defer(),start=defer(),e=fixture(async()=>{start.resolve();return gate.promise;});
  const pending=e.controller.load();await start.promise;await e.controller.load();gate.resolve(payload());await pending;assert.equal(e.calls(),1);
});
test('Recoverable failure retains previous rows with a visible stale-data error and same limit retry',async()=>{
  let calls=0,limits=[];const e=fixture(async(c,limit)=>{limits.push(limit);if(++calls===2)throw new Error('offline');return payload(['a']);});
  await e.controller.load(100);await e.controller.load();assert.equal(e.controller.state.items.length,1);assert.ok(e.controller.state.error);
  await e.controller.load();assert.equal(e.controller.state.error,'');assert.deepEqual(limits,[100,100,100]);
});
for(const [name,mutate] of [['oversized rows',body=>body.items=Array.from({length:51},(_,i)=>payload([String(i)]).items[0])],
  ['unknown cause',body=>body.items[0].causes=['unpaid']],['invented responsible',body=>body.items[0].responsible='doctor'],
  ['bad metrics',body=>body.metrics.plans_saved=-1],['duplicate IDs',body=>body.items.push(body.items[0])],
  ['missing date',body=>delete body.as_of]])test('Rejects '+name+' without publishing partial data',async()=>{
    const body=payload(['a']);mutate(body);const e=fixture(async()=>body);await e.controller.load();
    assert.equal(e.controller.state.items.length,0);assert.ok(e.controller.state.error);
});
test('Changing account while read is pending discards every old field',async()=>{
  const gate=defer(),start=defer(),e=fixture(async()=>{start.resolve();return gate.promise;});
  const pending=e.controller.load();await start.promise;e.replace();gate.resolve(payload(['old']));await pending;
  assert.equal(e.controller.state.invalid,true);assert.equal(e.controller.state.items.length,0);assert.equal(e.controller.state.metrics,null);
});
test('Canonical role/team/version replacement is checked after response',async()=>{
  const e=fixture(async()=>{e.role();return payload(['old']);});await e.controller.load();assert.equal(e.controller.state.invalid,true);
});
test('A response resolved by a helper is fenced before its DTO is read',async()=>{
  const e=fixture(async()=>{e.replace();return new Proxy({},{get(){throw new Error('old DTO touched');}});});
  await e.controller.load();assert.equal(e.controller.state.invalid,true);assert.equal(e.controller.state.items.length,0);
});
test('Synchronous controls invalidation does not start a request or retain busy state',async()=>{
  const e=fixture(undefined,(controller,state)=>{if(state.busy)controller.invalidate();});
  await e.controller.load();assert.equal(e.calls(),0);assert.equal(e.controller.state.busy,false);
});
test('Storage error discards confirmed rows at the next guard',async()=>{
  const e=fixture();await e.controller.load();e.api.validarContexto=()=>{throw Object.assign(new Error('storage'),{code:'session_storage_error'});};
  await e.controller.load();assert.equal(e.controller.state.invalid,true);assert.equal(e.controller.state.items.length,0);
});
test('Explicit invalidation is synchronous and prevents retry/navigation',async()=>{
  const e=fixture();await e.controller.load();e.controller.invalidate();assert.equal(e.controller.state.items.length,0);
  await e.controller.load();await e.controller.navigate('client-a','prepare',()=>assert.fail('must not navigate'));assert.equal(e.calls(),1);
});
test('Navigation requires another canonical check, never generates by GET',async()=>{
  const e=fixture();await e.controller.load();const targets=[];
  await e.controller.navigate('client-a','prepare',url=>targets.push(url));
  assert.deepEqual(targets,['/generar-plan?id=client-a']);assert.equal(e.calls(),1);
  e.role();await e.controller.navigate('client-a','prepare',()=>assert.fail('stale navigation'));assert.equal(e.controller.state.invalid,true);
});
test('Read capability cannot become plan generation permission',async()=>{
  const value=payload(['a']);value.capabilities.prepare_plan=false;const e=fixture(async()=>value);await e.controller.load();
  await e.controller.navigate('a','prepare',()=>assert.fail('not allowed'));
  let target;await e.controller.navigate('a','review',url=>target=url);assert.equal(target,'/clientes');
});
function helper(){
  const data=new Map([['mb_token','synthetic-A'],['mb_refresh_token','synthetic-refresh-A']]),calls=[];
  const context={window:{addEventListener:()=>{}},localStorage:{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)},
    fetch:async(url,options)=>{calls.push({url,options});return{ok:true,status:200,json:async()=>url==='/api/auth/me'?{id:'A',role:'owner',tipo:'gym',session_version:0}:payload()};},
    URLSearchParams,setTimeout,clearTimeout,console};vm.createContext(context);
  vm.runInContext(fs.readFileSync(root+'/web/static/js/api.js','utf8')+'\nglobalThis.testApi=Api;',context);
  return{api:context.testApi,calls};
}
test('Shared helper uses central authenticated GET and fences a replaced account before send',async()=>{
  const e=helper(),context=await e.api.stats.contexto();await e.api.stats.seguimiento(context);
  const request=e.calls.at(-1);assert.equal(request.url,'/api/estadisticas/seguimiento?limit=50');assert.equal(request.options.headers.Authorization,'Bearer synthetic-A');
  e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-refresh-B'});const before=e.calls.length;
  assert.throws(()=>e.api.stats.seguimiento(context),error=>error.code==='session_changed');assert.equal(e.calls.length,before);
});
test('Bounds reject invalid values before transport',async()=>{
  const e=helper(),context=await e.api.stats.contexto(),before=e.calls.length;
  for(const value of [0,101,true,1.5,'50'])assert.throws(()=>e.api.stats.seguimiento(context,value));assert.equal(e.calls.length,before);
});
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({name:entry.name,passed:true});}catch(error){results.push({name:entry.name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'Offline VM only; no browser/layout/HTTP claim',passed:results.filter(r=>r.passed).length,total:results.length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
