/* Bounded one-time legacy migration under Storage faults; current real API. */
'use strict';
const assert=require('node:assert/strict');
const {world}=require('./browser_harness31.cjs');
const rows=[];
async function test(name,run){try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name,code:error.code||null});}}
(async()=>{
 for(const store of['localStorage','sessionStorage'])for(const operation of['getItem','removeItem'])for(const key of(operation==='getItem'?['mb_token','mb_refresh_token']:['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo']))for(const phase of['before','after']){
  await test('Legacy '+store+' '+operation+' '+key+' '+phase+' fault prevents all auth I/O and automatic recovery',async()=>{
   let active=true,hit=0;const w=world({legacy:'synthetic-legacy-refresh',storageFault:event=>{if(active&&event.store===store&&event.operation===operation&&event.key===key&&event.phase===phase){hit++;throw new DOMException('SYNTHETIC PRIVATE STORAGE DETAIL','SecurityError');}}}),t=w.tab();
   await assert.rejects(t.api.session.ready,error=>{assert.equal(error.code,'session_storage_error');assert.equal(error.message.includes('SYNTHETIC PRIVATE'),false);return true;});assert.ok(hit>0);assert.equal(t.api.getToken(),'');assert.equal(w.calls.length,0);assert.equal(w.writes.length,0);active=false;
   await assert.rejects(t.api.clientes.actualizar('synthetic-intended-actor',{nombre:'Synthetic explicit edit'}));assert.equal(w.calls.length,0);assert.equal(t.api.getToken(),'');assert.ok(w.writes.every(entry=>entry.key==='mb_session_epoch'));
   const explicitPage=w.tab();await explicitPage.api.session.ready;assert.ok(explicitPage.api.getToken());assert.equal(t.api.getToken(),'');assert.equal(w.calls.length,1);
  });
 }
 for(const store of['localStorage','sessionStorage'])await test('Successful '+store+' migration consumes its proof once and never persists a new pair',async()=>{
  const w=world(store==='localStorage'?{legacy:'synthetic-legacy-refresh'}:{sessionLegacy:'synthetic-legacy-refresh'}),t=w.tab();await t.api.session.ready;
  assert.deepEqual(w.calls.map(call=>call.path),['/api/auth/browser/migrate']);assert.equal(w.calls[0].body.refresh_token,'synthetic-legacy-refresh');assert.ok(t.api.getToken());
  for(const key of['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo']){assert.equal(w.shared.has(key),false);assert.equal(t.sessionMap.has(key),false);}assert.ok(w.writes.every(entry=>entry.key==='mb_session_epoch'));
 });
 console.log(JSON.stringify({scope:'Actual current API bootstrap with native DOMException fault injection in both Storage doubles; no physical browser quota, durable deletion, cookie backend or cross-origin acceptance.',passed:rows.filter(row=>row.passed).length,total:rows.length,results:rows},null,2));if(rows.some(row=>!row.passed))process.exitCode=1;
})().catch(()=>{process.exitCode=1;});
