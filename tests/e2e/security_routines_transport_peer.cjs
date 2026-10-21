/* Independent actual RAM API and catalogue transport, no browser or sockets. */
'use strict';
const assert=require('node:assert/strict');
const {world,tick}=require('./browser_harness31.cjs');
const panel=require('../../web/static/js/rutinas.js');
const rows=[];
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return{promise,resolve};};
async function test(name,run){try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name});}}
async function setup(){const w=world(),t=w.tab();await t.api.session.ready;assert.ok(t.api.getToken());return{w,t};}
(async()=>{
 for(const status of[403,422,503])await test('Confirmed '+status+' retains current access without retry',async()=>{
  const {t}=await setup(),before=t.api.getToken();let calls=0;
  await assert.rejects(panel.readCatalog(t.api,'gym',async()=>{calls++;return Response.json({detail:{code:'routine_rejected'}},{status});}),{status});
  assert.equal(calls,1);assert.equal(t.api.getToken(),before);
 });
 await test('Missing RAM access does not dispatch',async()=>{
  const w=world({cookie:null}),t=w.tab();await t.api.session.ready;let calls=0;
  await assert.rejects(panel.readCatalog(t.api,'gym',async()=>{calls++;}),{status:401});assert.equal(calls,0);
 });
 await test('401 valid JSON retires the captured current access',async()=>{
  const {t}=await setup();let calls=0;
  await assert.rejects(panel.readCatalog(t.api,'gym',async()=>{calls++;return Response.json({detail:{code:'routine_session_unavailable'}},{status:401});}));
  assert.equal(calls,1);assert.equal(t.api.getToken(),'');
 });
 await test('401 malformed body retires access before interpreting body',async()=>{
  const {t}=await setup();
  await assert.rejects(panel.readCatalog(t.api,'gym',async()=>new Response('not JSON',{status:401})));
  assert.equal(t.api.getToken(),'');
 });
 await test('401 delayed body retires access at headers',async()=>{
  const {t}=await setup(),body=deferred(),entered=deferred();
  const pending=panel.readCatalog(t.api,'gym',async()=>({status:401,ok:false,text:async()=>{entered.resolve();await body.promise;return '{}';}}));
  const drained=Promise.allSettled([pending]);await tick();await tick();
  const retired=t.api.getToken()==='';body.resolve();await drained;assert.equal(retired,true);
 });
 await test('Late old 401 cannot retire a newer same-tab account',async()=>{
  const {t}=await setup(),headers=deferred(),started=deferred();
  const pending=panel.readCatalog(t.api,'gym',async()=>{started.resolve();await headers.promise;return Response.json({detail:{}},{status:401});});
  const drained=Promise.allSettled([pending]);await started.promise;
  await t.api.auth.registro({account:'B'});const newer=t.api.getToken();assert.ok(newer);
  headers.resolve();const [outcome]=await drained;assert.equal(outcome.status,'rejected');assert.equal(outcome.reason.code,'session_changed');assert.equal(t.api.getToken(),newer);
 });
 await test('Pagehide fences a late successful body',async()=>{
  const {t}=await setup(),body=deferred(),started=deferred();
  const pending=panel.readCatalog(t.api,'gym',async()=>({status:200,ok:true,text:async()=>{started.resolve();await body.promise;return '{}';}}));
  const drained=Promise.allSettled([pending]);await started.promise;t.dispatch({type:'pagehide'});body.resolve();
  const [outcome]=await drained;assert.equal(outcome.status,'rejected');assert.equal(outcome.reason.code,'session_changed');assert.equal(t.api.getToken(),'');
 });
 const result={scope:'Actual api.js in VM plus actual catalogue transport; no HTTP/browser acceptance',passed:rows.filter(r=>r.passed).length,total:rows.length,results:rows};
 process.stdout.write(JSON.stringify(result,null,2)+'\n');process.exitCode=result.passed===result.total?0:1;
})().catch(error=>{process.stderr.write(error.name+'\n');process.exitCode=2;});
