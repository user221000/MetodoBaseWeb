/* Actual Api/controller VM composition; backend persistence is a typed response double. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {closed}=require('./browser_harness31.cjs');
const ui=vm.runInNewContext(fs.readFileSync('web/static/js/notifications36.js','utf8')+'\nNotifications36;',{Date,console});
const purposes=['account_period_end','confirmed_payment_issue'],id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),stamp='2026-10-20T12:00:00Z';
const deferred=()=>{let resolve;const promise=new Promise(yes=>resolve=yes);return{promise,resolve};};
async function fixture({context='gym',verified=false,enabled=false}={}){
 const preferences=purposes.map((purpose,index)=>({id:enabled?id(index+1):null,context,purpose,channel:'email',version:enabled?1:0,enabled,interval_hours:24,updated_at:enabled?stamp:null}));
 const server={preferences,outbox:[],ledger:new Map(),writes:[],reads:[],hook:null,lost:false,replayed:false,after:null};
 const auth=await closed(async(url,options)=>{
  const u=new URL(url,'http://test.invalid'),method=options.method||'GET',body=options.body?JSON.parse(options.body):null,record={url,method,body,key:options.headers?.['Idempotency-Key']};
  if(u.pathname==='/api/auth/me')return Response.json({id:'synthetic-own',tipo:context==='gym'?'gym':'usuario',role:context==='gym'?'owner':'viewer',session_version:1,team_gym_id:null});
  assert.equal(u.searchParams.get('context'),context);if(method==='GET')server.reads.push(record);else server.writes.push(record);
  if(server.hook){const reply=await server.hook(record);if(reply)return reply;}
  if(method==='GET'){
   if(u.pathname.endsWith('/contexto'))return Response.json({context,purposes,channels:['email'],delivery_enabled:false,frequency:{minimum_hours:24,maximum_handoffs_7d:3},timezone:'America/Mexico_City'});
   if(u.pathname.endsWith('/preferencias'))return Response.json({items:server.preferences});
   if(u.pathname.endsWith('/candidatos'))return Response.json({context,observed_at:stamp,source_state:verified?'verified':'unknown',candidates:purposes.map((purpose,index)=>({purpose,eligible:verified,fact_id:verified?id(10):null,source_hash:verified?'a'.repeat(64):null,preference:server.preferences[index]}))});
   if(u.pathname.endsWith('/outbox')){const after=u.searchParams.get('after'),rows=server.outbox.filter(row=>!after||row.id>after);return Response.json({items:rows.slice(0,20),next_after:rows.length>20?rows[19].id:null});}
   if(u.pathname.endsWith('/metricas'))return Response.json({from:u.searchParams.get('from')||'2026-10-20',through:u.searchParams.get('through')||'2026-10-20',timezone:'America/Mexico_City',outbox_states:{},verified_paid_period_advances:0,attribution:'observed_facts_only_no_email_causality'});
  }
  if(server.ledger.has(record.key)){const ack=server.ledger.get(record.key);return Response.json({...ack,replayed:true,read_required:true,...(ack.outbox?{outbox:undefined,operation_result:{id:ack.outbox.id}}:{})});}
  let ack;
  if(u.pathname.includes('/preferencias/')){const purpose=u.pathname.split('/').at(-1),index=purposes.indexOf(purpose),previous=server.preferences[index];if(body.expected_version!==previous.version)return Response.json({detail:{code:'notification_conflict'}},{status:409});const value={...previous,id:id(index+1),version:previous.version+1,enabled:body.enabled,interval_hours:body.interval_hours,updated_at:stamp};server.preferences[index]=value;ack={preference:value,replayed:false,read_required:false};}
  else if(u.pathname.endsWith('/cancelar')){const value=server.outbox.find(row=>u.pathname.includes(row.id));value.state='suppressed';value.version++;value.capabilities.cancel=false;ack={outbox:value,replayed:false,read_required:false};}
  else if(u.pathname.endsWith('/outbox')){const value=outbox(30+server.outbox.length,context);server.outbox.push(value);ack={outbox:value,replayed:false,read_required:false};}
  else if(u.pathname.endsWith('/observar'))ack={observed:true,fact_id:id(10),replayed:false,read_required:true};
  else throw Error('Unconfigured notification fixture path');
  server.ledger.set(record.key,JSON.parse(JSON.stringify(ack)));if(server.lost)return Response.json({detail:{code:'notification_unconfirmed'}},{status:503});return Response.json(ack);
 });
 const controller=ui.create({api:auth.api.notifications36,context});return{server,auth,controller};
}
function outbox(number,context='gym',state='pending'){return{id:id(number),context,purpose:purposes[0],channel:'email',state,version:1,attempt_count:0,created_at:stamp,updated_at:stamp,capabilities:{cancel:['pending','leased','retry_wait','uncertain'].includes(state)}};}
const tests=[],test=(name,run)=>tests.push({name,run});
for(const context of['gym','personal'])test(context+' initial load is GET-only, defaultOFF and unknown is never payment debt',async()=>{
 const e=await fixture({context});assert.equal(await e.controller.load(),true);const view=e.controller.view();assert.equal(view.phase,'ready');assert.ok(view.preferences.every(row=>row.enabled===false&&row.version===0));assert.equal(view.candidates.source_state,'unknown');assert.equal(e.server.writes.length,0);assert.equal(e.server.reads.length,5);assert.equal(e.auth.calls.filter(row=>row.url==='/api/auth/refresh').length,0);assert.throws(()=>e.controller.queue(purposes[1],true));
});
test('Preference requires explicit confirmation, capturesCAS/body/key and ACK requires manual read',async()=>{
 const e=await fixture();await e.controller.load();assert.throws(()=>e.controller.savePreference(purposes[0],true,72,false));assert.equal(e.server.writes.length,0);await e.controller.savePreference(purposes[0],true,72,true);assert.equal(e.server.writes.length,1);const row=e.server.writes[0];assert.match(row.key,/^[0-9a-f-]{36}$/);assert.deepEqual(row.body,{expected_version:0,enabled:true,interval_hours:72,confirm:true});assert.equal(e.controller.view().phase,'read_required');assert.equal(e.server.reads.length,5);assert.equal(e.controller.view().preferences[0].enabled,false);await e.controller.load();assert.equal(e.controller.view().preferences[0].enabled,true);assert.equal(e.server.writes.length,1);
});
test('Lost durable preference ACK503 preserves exact voluntary retry without readback and ignores stale replay snapshot',async()=>{
 const e=await fixture();await e.controller.load();e.server.lost=true;await e.controller.savePreference(purposes[0],true,168,true);assert.equal(e.controller.view().retry,true);assert.equal(e.server.reads.length,5);e.server.preferences[0]={...e.server.preferences[0],version:2,enabled:false};e.server.lost=false;await e.controller.retry();assert.deepEqual(e.server.writes[0],e.server.writes[1]);assert.equal(e.controller.view().phase,'read_required');assert.equal(e.controller.view().preferences[0].version,0);assert.equal(e.server.reads.length,5);await e.controller.load();assert.equal(e.controller.view().preferences[0].version,2);assert.equal(e.controller.view().preferences[0].enabled,false);
});
test('Failed explicit read preserves pending same-intent retry RAM',async()=>{
 const e=await fixture();await e.controller.load();e.server.lost=true;await e.controller.savePreference(purposes[0],true,24,true);e.server.hook=row=>row.method==='GET'?Response.json({detail:{code:'notification_disabled'}},{status:503}):null;await e.controller.load();assert.equal(e.controller.view().retry,true);e.server.hook=null;e.server.lost=false;await e.controller.retry();assert.deepEqual(e.server.writes[0],e.server.writes[1]);
});
test('Verified source alone cannot queue without matching explicit current opt-in',async()=>{
 const e=await fixture({verified:true});await e.controller.load();assert.throws(()=>e.controller.queue(purposes[1],true));assert.equal(e.server.writes.length,0);
});
test('Queue command captures exact preference/source and retry replay never assumes present pending state',async()=>{
 const e=await fixture({verified:true,enabled:true});await e.controller.load();e.server.lost=true;await e.controller.queue(purposes[1],true);const row=e.server.writes[0];assert.equal(row.body.preference_id,id(2));assert.equal(row.body.fact_id,id(10));assert.equal(row.body.source_hash,'a'.repeat(64));assert.equal(row.body.expected_preference_version,1);e.server.lost=false;await e.controller.retry();assert.deepEqual(e.server.writes[0],e.server.writes[1]);assert.equal(e.controller.view().outbox.items.length,0);assert.equal(e.server.reads.length,5);
});
test('Outbox pages are manual20 ascending and cancellation needs exact observed version',async()=>{
 const e=await fixture();e.server.outbox=Array.from({length:21},(_,index)=>outbox(100+index));await e.controller.load();assert.equal(e.controller.view().outbox.items.length,20);assert.equal(e.server.reads.filter(row=>row.url.includes('/outbox')).length,1);await e.controller.page();assert.equal(e.controller.view().outbox.items[0].id,id(120));assert.equal(e.server.reads.filter(row=>row.url.includes('/outbox')).length,2);assert.throws(()=>e.controller.cancel(id(120),false));await e.controller.cancel(id(120),true);assert.deepEqual(e.server.writes[0].body,{expected_version:1,confirm:true});assert.equal(e.controller.view().phase,'read_required');
});
test('Accepted and uncertain labels distinguish delivery and prohibit invented resend action',()=>{
 assert.match(ui.states.accepted,/entrega no acreditada/);assert.match(ui.states.uncertain,/no reenviar/);const e=ui.outboxPage({items:[outbox(1,'gym','uncertain')],next_after:null},'gym');assert.equal(e.items[0].capabilities.cancel,true);assert.equal('resend'in e.items[0].capabilities,false);
});
for(const code of['notification_conflict','notification_source_changed','notification_frequency_limited','notification_disabled'])test(code+' never triggers automatic retry, source observation or readback',async()=>{
 const e=await fixture();await e.controller.load();e.server.hook=row=>row.method!=='GET'?Response.json({detail:{code}},{status:code==='notification_frequency_limited'?429:code==='notification_disabled'?503:409}):null;await e.controller.savePreference(purposes[0],true,24,true);assert.equal(e.server.writes.length,1);assert.equal(e.server.reads.length,5);assert.notEqual(e.controller.view().phase,'ready');
});
test('Context403 clears private projected state and never elevates ADMIN/team access',async()=>{
 const e=await fixture();e.server.hook=row=>row.url.includes('/contexto')?Response.json({detail:{code:'notification_context_forbidden'}},{status:403}):null;await e.controller.load();assert.equal(e.controller.view().preferences.length,0);assert.equal(e.controller.view().metrics,null);assert.equal(e.server.writes.length,0);
});
for(const phase of['read','write'])test('External epoch during '+phase+' discards late response and pending private state',async()=>{
 const e=await fixture(),gate=deferred(),arrival=deferred();if(phase==='write')await e.controller.load();e.server.hook=async row=>{if((phase==='write'&&row.method==='PUT')||(phase==='read'&&row.url.includes('/candidatos'))){arrival.resolve();await gate.promise;}return null;};const pending=phase==='write'?e.controller.savePreference(purposes[0],true,24,true):e.controller.load();await arrival.promise;e.auth.invalidate();gate.resolve();await pending;assert.equal(e.controller.view().phase,'invalidated');assert.equal(e.controller.view().preferences.length,0);assert.equal(e.controller.view().retry,false);assert.equal(e.auth.api.getToken(),'');
});
test('Closed namespace rejects forged operation, authority/free text and mutable caller body',async()=>{
 const e=await fixture(),api=e.auth.api.notifications36,{handle}=await api.session();const body={expected_version:0,enabled:true,interval_hours:24,confirm:true},op=api.operation('preference','gym',purposes[0],body,handle);body.enabled=false;await api.send(op);assert.equal(e.server.writes[0].body.enabled,true);assert.throws(()=>api.send({kind:'preference'}));for(const body of[{expected_version:true,enabled:true,interval_hours:24,confirm:true},{expected_version:0,enabled:true,interval_hours:25,confirm:true},{expected_version:0,enabled:true,interval_hours:24,confirm:true,gym_id:'other'}])assert.throws(()=>api.operation('preference','gym',purposes[0],body,handle));
});
test('Malformed unknown/cursor/metrics/ACK inputs fail closed',()=>{
 const pref={id:null,context:'gym',purpose:purposes[0],channel:'email',version:0,enabled:false,interval_hours:24,updated_at:null};assert.throws(()=>ui.candidates({context:'gym',source_state:'unknown',observed_at:stamp,candidates:purposes.map(purpose=>({purpose,eligible:true,fact_id:id(1),source_hash:'a'.repeat(64),preference:{...pref,purpose}}))},'gym'));assert.throws(()=>ui.outboxPage({items:[outbox(2),outbox(1)],next_after:null},'gym'));assert.throws(()=>ui.metrics({from:'2026-02-30',through:'2026-03-02',timezone:'America/Mexico_City',attribution:'observed_facts_only_no_email_causality',outbox_states:{},verified_paid_period_advances:0}));assert.throws(()=>ui.acknowledgement({replayed:true,read_required:false,preference:pref},'preference','gym'));
});
test('Default observation requires explicit confirmation and503 does not certify source or payment issue',async()=>{
 const e=await fixture();await e.controller.load();assert.throws(()=>e.controller.observe(false));e.server.hook=row=>row.url.includes('/observar')?Response.json({detail:{code:'notification_disabled'}},{status:503}):null;await e.controller.observe(true);assert.equal(e.server.writes.length,1);assert.equal(e.server.writes[0].url,'/api/notificaciones/observar?context=gym');assert.deepEqual(e.server.writes[0].body,{});assert.equal(e.controller.view().candidates.source_state,'unknown');assert.equal(e.server.reads.length,5);
});
(async()=>{const results=[];for(const row of tests){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name,code:error.code||null,frames:error.stack?.split('\n').slice(1,4)});}}console.log(JSON.stringify({scope:'Actual api.js + notifications36 controller in VM; HTTP persistence/provider/cookie/DOM responses doubled. No real HTTP/browser/PostgreSQL/delivery acceptance.',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})();
