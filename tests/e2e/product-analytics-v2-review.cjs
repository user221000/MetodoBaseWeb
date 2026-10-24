/* Actual analytics UI/Api in offline VMs; DOM/transport doubles, no browser or server claim. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {closed}=require('./browser_harness31.cjs');
const source=fs.readFileSync(path.join(__dirname,'../../web/static/js/product-analytics-v2.js'),'utf8');
const flush=async()=>{for(let n=0;n<8;n++)await new Promise(setImmediate);};
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};};
const counts=()=>({definition_version:'product-facts-v2',context:'gym',baseline:{event_counts_by_origin:{
  unknown:{plan_saved:1,plan_assignment_published:2,assigned_plan_http200:3},
  demo:{plan_saved:4,plan_assignment_published:5,assigned_plan_http200:6},
  customer:{plan_saved:7,plan_assignment_published:8,assigned_plan_http200:9}}}});
const origin=(value='demo',version=1)=>({origin:value,version,applies_to:'future_facts',customer_is_payment:false});
class Node {
  constructor(){this.hidden=false;this.disabled=false;this.value='';this.onclick=null;this.events=new Map();this._text='';}
  set textContent(value){this._text=String(value);}get textContent(){return this._text;}
  set innerHTML(_){throw Error('HTML sink forbidden by this DOM fixture');}
  addEventListener(name,callback){this.events.set(name,callback);}
  async emit(name){const callback=this.events.get(name);if(callback)return await callback({preventDefault(){}});}
}
function fixture({context='gym',me={tipo:'gym',role:'owner',team_gym_id:null},report=counts(),lookup=null}={}){
  const select=new Node(),save=new Node(),status=new Node(),refresh=new Node(),text=new Node(),events=new Map(),calls=[];
  const root={hidden:true,dataset:{context},querySelector:selector=>({'select':select,'button':save,'[data-origin-status]':status}[selector])};
  const metrics={dataset:{context},querySelector:selector=>({'button':refresh,'[data-product-report]':text}[selector])};
  let declared=origin();
  const Api={auth:{me:async()=>me},productAnalytics:{
    origin:async(kind,client,change)=>{calls.push({kind,client,change});if(lookup)return lookup(kind,client,change);if(change)declared=origin(change.origin,declared.version+1);return declared;},
    report:async kind=>{calls.push({report:kind});return report;}}};
  const document={readyState:'complete',querySelectorAll:selector=>selector==='[data-product-analytics]'?[metrics]:selector==='[data-product-origin]'?[root]:selector==='[data-product-report]'?[text]:[],
    querySelector:selector=>selector==='[data-product-origin][data-context="personal"]'&&context==='personal'?root:null,
    getElementById:id=>id==='client-origin'&&context==='gym'?root:null};
  const sandbox={document,Api,console};sandbox.window=sandbox;sandbox.addEventListener=(name,callback)=>events.set(name,callback);
  vm.runInContext(source,vm.createContext(sandbox),{filename:'product-analytics-v2.js'});
  return{root,select,save,status,refresh,text,calls,Api,
    open:async()=>{if(context==='gym')sandbox.ProductOrigin.showClient('synthetic-client');await flush();},
    switch:()=>events.get('metodobase-session-changed')(),report:()=>refresh.emit('click')};
}
const cases=[],test=(name,run)=>cases.push({name,run});
test('Gym owner can declare only future origin with the observed version',async()=>{
  const e=fixture();await e.open();assert.equal(e.root.hidden,false);assert.equal(e.select.disabled,false);assert.equal(e.save.hidden,false);
  e.select.value='customer';await e.save.onclick();await flush();
  const writes=e.calls.filter(row=>row.change);assert.equal(writes.length,1);
  assert.deepEqual(JSON.parse(JSON.stringify(writes[0])),{kind:'gym',client:'synthetic-client',change:{origin:'customer',expected_version:1}});
  assert.match(e.status.textContent,/hechos futuros/);assert.doesNotMatch(e.status.textContent,/pagado|cobrado/i);
});
for(const role of ['admin','nutriologo','viewer'])test('Gym team '+role+' sees provenance without edit controls',async()=>{
  const e=fixture({me:{tipo:'gym',role,team_gym_id:'synthetic-owner'}});await e.open();
  assert.equal(e.root.hidden,false);assert.equal(e.select.disabled,true);assert.equal(e.save.hidden,true);
  assert.equal(e.calls.filter(row=>row.change).length,0);assert.match(e.status.textContent,/Demostración/);
});
test('Individual provenance is writable while a gym owner in personal context is read-only',async()=>{
  const own=fixture({context:'personal',me:{tipo:'usuario',role:'viewer',team_gym_id:null}});await own.open();
  assert.equal(own.select.disabled,false);assert.equal(own.save.hidden,false);assert.equal(own.calls[0].client,null);
  const denied=fixture({context:'personal'});await denied.open();assert.equal(denied.select.disabled,true);assert.equal(denied.save.hidden,true);
});
test('Rejected provenance never exposes editable controls or raw error details',async()=>{
  const e=fixture({lookup:async()=>{throw Error('<img src=x onerror=alert(1)> PRIVATE-ID');}});await e.open();
  assert.equal(e.select.disabled,true);assert.equal(e.save.hidden,true);assert.match(e.status.textContent,/No se pudo consultar/);
  assert.doesNotMatch(e.status.textContent,/PRIVATE-ID|<img/);
});
test('Metrics render only known aggregate counts and never source IDs or HTML payloads',async()=>{
  const value=counts();value.owner_id='PRIVATE-OWNER';value.clients=[{id:'PRIVATE-CLIENT'}];value.html='<img src=x onerror=alert(1)>';
  value.baseline.event_counts_by_origin.demo.note='<script>bad()</script>';
  const e=fixture({report:value});assert.equal(e.calls.length,0);await e.report();
  assert.equal(e.text.textContent,'Sin clasificar: 1 planes guardados; 2 asignaciones; 3 primeras respuestas de plan asignado. Demostración: 4 planes guardados; 5 asignaciones; 6 primeras respuestas de plan asignado. Cliente: 7 planes guardados; 8 asignaciones; 9 primeras respuestas de plan asignado.');
  assert.doesNotMatch(e.text.textContent,/PRIVATE-|<|>|script|retención|adherencia/i);assert.equal(e.refresh.disabled,false);
});
for(const invalid of ['7',-1,1.5])test('Unconfirmed aggregate '+JSON.stringify(invalid)+' is rejected without guessed metrics',async()=>{
  const value=counts();value.baseline.event_counts_by_origin.demo.plan_saved=invalid;
  const e=fixture({report:value});await e.report();assert.match(e.text.textContent,/No se pudo confirmar/);assert.doesNotMatch(e.text.textContent,/4 planes guardados/);
});
test('Session change hides provenance and discards a late origin response',async()=>{
  const gate=deferred(),e=fixture({lookup:()=>gate.promise});e.open();await flush();e.switch();gate.resolve(origin());await flush();
  assert.equal(e.root.hidden,true);assert.equal(e.save.onclick,null);assert.equal(e.select.value,'unknown');assert.match(e.text.textContent,/La sesión cambió/);
});
test('Real Api report and origin use exact guarded relative routes and explicit mutation body',async()=>{
  const e=await closed(async(url,options)=>Response.json(url.includes('/procedencia')?origin():counts()));
  await e.api.productAnalytics.report('gym');await e.api.productAnalytics.origin('gym','synthetic-client',{origin:'demo',expected_version:0});
  assert.equal(e.calls[0].url,'/api/analytics/producto/v2?context=gym');assert.equal(e.calls[0].method,'GET');
  assert.equal(e.calls[1].url,'/api/analytics/procedencia?context=gym&client=synthetic-client');assert.equal(e.calls[1].method,'POST');
  assert.deepEqual(JSON.parse(e.calls[1].body),{origin:'demo',expected_version:0});
  const before=e.calls.length;await assert.rejects(e.api.productAnalytics.report('foreign'));
  await assert.rejects(e.api.productAnalytics.origin('personal','synthetic-client'));assert.equal(e.calls.length,before);
});
test('Real Api suppresses an old report after the account epoch changes',async()=>{
  const gate=deferred(),began=deferred();const e=await closed(async()=>{began.resolve();return gate.promise;});
  const pending=e.api.productAnalytics.report('gym');await began.promise;e.invalidate();gate.resolve(Response.json(counts()));
  await assert.rejects(pending,{code:'session_changed'});assert.equal(e.calls.length,1);
});
(async()=>{const results=[];for(const row of cases){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name});}}
  console.log(JSON.stringify({scope:'Actual product analytics UI and Api in offline VM/DOM/transport doubles; no real permissions/RLS/HTTP/browser acceptance.',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;
})().catch(error=>{console.error(error.name);process.exitCode=1;});
