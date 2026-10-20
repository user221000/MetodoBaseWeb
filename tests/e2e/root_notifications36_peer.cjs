/* Independent consumer negatives against the real API/controller VM seam. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),Module=require('node:module'),path=require('node:path');
const filename=path.join(__dirname,'notifications36_state.cjs');
const source=fs.readFileSync(filename,'utf8'),split='const tests=[],test=';
assert.equal(source.split(split).length,2);
const shared=new Module(filename,module);shared.filename=filename;shared.paths=module.paths;
shared._compile(source.slice(0,source.indexOf(split))+'\nmodule.exports={fixture,purposes,id,outbox,stamp};',filename);
const {fixture,purposes,outbox,stamp}=shared.exports;
const tests=[];
for(const context of ['gym','personal']){
 for(const malformed of ['delivery_enabled','duplicate_preferences','unknown_eligible','outbox_order','impossible_metrics']){
  tests.push({name:context+': '+malformed+' cannot become a writable view',async run(){
   const e=await fixture({context});
   e.server.hook=row=>{
    if(malformed==='delivery_enabled'&&row.url.includes('/contexto'))return Response.json({context,purposes,channels:['email'],delivery_enabled:true,frequency:{minimum_hours:24,maximum_handoffs_7d:3},timezone:'America/Mexico_City'});
    if(malformed==='duplicate_preferences'&&row.url.includes('/preferencias'))return Response.json({items:[e.server.preferences[0],e.server.preferences[0]]});
    if(malformed==='unknown_eligible'&&row.url.includes('/candidatos'))return Response.json({context,observed_at:stamp,source_state:'unknown',candidates:e.server.preferences.map(preference=>({purpose:preference.purpose,eligible:true,fact_id:null,source_hash:null,preference}))});
    if(malformed==='outbox_order'&&row.url.includes('/outbox'))return Response.json({items:[outbox(2,context),outbox(1,context)],next_after:null});
    if(malformed==='impossible_metrics'&&row.url.includes('/metricas'))return Response.json({from:'2026-02-30',through:'2026-03-02',timezone:'America/Mexico_City',outbox_states:{},verified_paid_period_advances:0,attribution:'observed_facts_only_no_email_causality'});
    return null;
   };
   assert.equal(await e.controller.load(),false);
   assert.equal(e.controller.view().phase,'error');
   assert.equal(e.controller.view().preferences.length,0);
   assert.equal(e.controller.view().candidates,null);
   assert.equal(e.server.writes.length,0);
   assert.throws(()=>e.controller.observe(true));
   assert.throws(()=>e.controller.queue(purposes[1],true));
   assert.equal(e.server.writes.length,0);
  }});
 }
 tests.push({name:context+': loss of eligibility clears a previously usable view',async run(){
  const e=await fixture({context,enabled:true,verified:true});
  assert.equal(await e.controller.load(),true);
  assert.equal(e.controller.view().preferences.length,2);
  e.server.hook=row=>row.url.includes('/contexto')?Response.json({detail:{code:'notification_context_forbidden'}},{status:403}):null;
  assert.equal(await e.controller.load(),false);
  const view=e.controller.view();
  assert.equal(view.preferences.length,0);assert.equal(view.candidates,null);assert.equal(view.metrics,null);assert.equal(view.outbox.items.length,0);
  assert.throws(()=>e.controller.savePreference(purposes[0],false,24,true));
  assert.equal(e.server.writes.length,0);
 }});
}
(async()=>{const results=[];for(const test of tests){try{await test.run();results.push({case:test.name,passed:true});}catch(error){results.push({case:test.name,passed:false,error_class:error.name});}}
 const passed=results.filter(row=>row.passed).length;
 console.log(JSON.stringify({scope:'Independent negatives, real Api/controller VM, response doubles. No actual HTTP, native browser, provider, PostgreSQL or delivery claim.',passed,total:results.length,results},null,2));
 if(passed!==results.length)process.exitCode=1;
})();
