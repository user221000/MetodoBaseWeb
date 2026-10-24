/* Actual Api in two VM realms; controlled fetch/cookie/WebLock, no HTTP claim. */
'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const root=process.argv[2]?path.resolve(process.argv[2]):path.resolve(__dirname,'../..');
const helpers=process.argv[3]?path.resolve(process.argv[3]):root;
const previous=process.env.BROWSER31_SOURCE;
let world,tick;
try{
 process.env.BROWSER31_SOURCE=path.join(root,'web/static/js/api.js');
 ({world,tick}=require(path.join(helpers,'tests/e2e/browser_harness31.cjs')));
}finally{
 if(previous===undefined)delete process.env.BROWSER31_SOURCE;else process.env.BROWSER31_SOURCE=previous;
}
const id='a'.repeat(32),key='11111111-1111-4111-8111-111111111111';
const endpoint='/api/account/privacy/requests/'+id+'/close-account';
const body=()=>({expected_version:1,confirmation:'close_account',reauthentication_token:'P'.repeat(43)});
const receipt=(closed=false)=>({id,version:closed?2:1,state:closed?'eligible':'blocked',reason:closed?null:'policy_required',
 account_closed:closed,erasure_complete:false,policy:null,items:[],...(closed?{sessions_revoked:true,state_available:'authorized_operator_only_after_closure'}:{})});
const reply=(status,data)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>data});
const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return{promise,resolve};};
async function fixture(){
 const w=world(),t=w.tab(),control={hook:null};
 t.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
 t.hook(async call=>{
  if(control.hook){const answer=await control.hook(call);if(answer)return answer;}
  if(call.path==='/api/account/privacy/requests')return reply(200,receipt());
  if(call.path===endpoint)return reply(200,receipt(true));
 });
 await t.api.session.ready;const {handle}=await t.api.accountPrivacy.context();
 return{w,t,control,handle,api:t.api.accountPrivacy};
}
const results=[];
async function test(name,run){await run();results.push({name,passed:true});}
(async()=>{
 await test('request-is-exact-access-idempotent-browser-csrf-under-shared-lock',async()=>{
  const e=await fixture(),access=e.t.api.getToken(),before=e.w.calls.length;
  const value=await e.api.create(key,e.handle);assert.equal(value.account_closed,false);
  assert.equal(e.w.calls.length,before+1);const c=e.w.calls.at(-1);
  assert.equal(c.path,'/api/account/privacy/requests');assert.deepEqual(c.body,{idempotency_key:key,intent:'erase_personal_data'});
  assert.equal(c.held,1);assert.equal(c.options.headers.Authorization,'Bearer '+access);
  assert.equal(c.options.headers['X-MetodoBase-Browser'],'1');assert.equal(c.options.headers['X-CSRF-Token'],'synthetic-csrf');
  assert.equal(c.options.credentials,'same-origin');assert.equal(c.options.mode,'same-origin');assert.equal(c.options.redirect,'error');
 });
 await test('close-captures-intent-before-lock-and-preserves-bound-receipt-without-me',async()=>{
  const e=await fixture(),gate=deferred(),began=deferred();
  e.control.hook=c=>c.path==='/api/account/privacy/requests'?{...reply(200,{}),json:async()=>{began.resolve();await gate.promise;return receipt();}}:null;
  const first=e.api.create(key,e.handle);await began.promise;
  const before=e.w.calls.length,input={...body(),code:'123456'},pending=e.api.close(id,input,e.handle);input.expected_version=71;input.code='654321';input.reauthentication_token='Q'.repeat(43);
  gate.resolve();await first;const result=await pending;
  assert.equal(e.w.calls.length,before+1);const c=e.w.calls.at(-1);
  assert.equal(c.path,endpoint);assert.equal(c.body.expected_version,1);assert.equal(c.body.code,'123456');assert.equal(c.body.reauthentication_token,'P'.repeat(43));
  assert.equal(c.held,1);assert.equal(e.w.maxHeld,1);assert.equal(e.t.api.getToken(),'');
  assert.equal(result.server_confirmed,true);assert.equal(result.account_closed,true);assert.equal(result.receipt.erasure_complete,false);
  assert.equal(Object.hasOwn(result.receipt,'policy'),false);assert.equal(Object.hasOwn(result.receipt,'version'),false);e.api.checkClosed(result);
 });
 await test('closed-boundary-retires-other-tab-access-and-stores-only-epoch',async()=>{
  const e=await fixture(),other=e.w.tab();await other.api.session.ready;
  const before=e.w.calls.length,result=await e.api.close(id,body(),e.handle);await tick();
  assert.equal(e.w.calls.length,before+1);assert.equal(e.t.api.getToken(),'');assert.equal(other.api.getToken(),'');
  assert(e.w.writes.every(row=>row.key==='mb_session_epoch'));e.api.checkClosed(result);
 });
 await test('policy-blocked-response-keeps-live-access-without-claiming-closure',async()=>{
  const e=await fixture(),token=e.t.api.getToken(),before=e.w.calls.length;
  e.control.hook=c=>c.path===endpoint?reply(200,{...receipt(),version:2}):null;
  const result=await e.api.close(id,body(),e.handle);assert.equal(result.state,'blocked');assert.equal(result.server_confirmed,false);
  assert.equal(result.account_closed,false);assert.equal(e.t.api.getToken(),token);assert.equal(e.w.calls.length,before+1);
  assert.throws(()=>e.api.checkClosed(result),{code:'session_changed'});
 });
 for(const status of[403,409,422,429])await test('confirmed-close-rejection-'+status+'-keeps-access-and-does-not-retry',async()=>{
  const e=await fixture(),token=e.t.api.getToken(),before=e.w.calls.length;
  e.control.hook=c=>c.path===endpoint?reply(status,{detail:{code:'privacy_rejected'}}):null;
  await assert.rejects(e.api.close(id,body(),e.handle),error=>error.status===status&&error.code==='privacy_rejected');
  assert.equal(e.t.api.getToken(),token);assert.equal(e.w.calls.length,before+1);
 });
 await test('current-access-401-retires-session-without-a-closure-receipt',async()=>{
  const e=await fixture(),before=e.w.calls.length;e.control.hook=c=>c.path===endpoint?reply(401,{detail:'synthetic expired access'}):null;
  await assert.rejects(e.api.close(id,body(),e.handle),{code:'session_changed'});
  assert.equal(e.t.api.getToken(),'');assert.equal(e.w.calls.length,before+1);
 });
 for(const mode of['503','network','invalid-json','invalid-closure-receipt'])await test('ambiguous-close-'+mode+'-retires-access-once-without-server-claim',async()=>{
  const e=await fixture(),before=e.w.calls.length;
  e.control.hook=c=>{
   if(c.path!==endpoint)return null;if(mode==='network')throw Error('synthetic network failure');
   if(mode==='invalid-json')return{...reply(200,{}),json:async()=>{throw SyntaxError('synthetic invalid JSON');}};
   if(mode==='invalid-closure-receipt')return reply(200,{...receipt(true),sessions_revoked:false});
   return reply(503,{detail:{code:'privacy_unconfirmed'}});
  };
  const result=await e.api.close(id,body(),e.handle);assert.equal(result.state,'unconfirmed');assert.equal(result.server_confirmed,false);
  assert.equal(result.account_closed,false);assert.equal(result.receipt,null);assert.equal(e.t.api.getToken(),'');
  assert.equal(e.w.calls.length,before+1);e.api.checkClosed(result);
 });
 await test('late-close-response-cannot-clear-or-confirm-a-later-account',async()=>{
  const e=await fixture(),gate=deferred(),began=deferred();
  e.control.hook=c=>c.path===endpoint?{...reply(200,{}),json:async()=>{began.resolve();await gate.promise;return receipt(true);}}:null;
  const pending=e.api.close(id,body(),e.handle);await began.promise;
  const epoch='22222222-2222-4222-8222-222222222222';e.w.shared.set('mb_session_epoch',epoch);e.w.jar.account='B';
  e.t.dispatch({type:'storage',key:'mb_session_epoch'});gate.resolve();
  await assert.rejects(pending,{code:'session_changed'});assert.equal(e.w.shared.get('mb_session_epoch'),epoch);
  const other=e.w.tab();await other.api.session.ready;assert(other.api.getToken().startsWith('access-B-'));
 });
 await test('receipt-is-unforgeable-and-suppressed-by-a-later-epoch',async()=>{
  const e=await fixture(),result=await e.api.close(id,body(),e.handle);
  assert.throws(()=>e.api.checkClosed({...result}),{code:'session_changed'});
  e.w.shared.set('mb_session_epoch','33333333-3333-4333-8333-333333333333');e.t.dispatch({type:'storage',key:'mb_session_epoch'});
  assert.throws(()=>e.api.checkClosed(result),{code:'session_changed'});
 });
 await test('invalid-close-input-never-performs-io',async()=>{
  const e=await fixture(),before=e.w.calls.length;
  for(const value of[{...body(),unexpected:true},{...body(),confirmation:false},{...body(),expected_version:0},
   {...body(),reauthentication_token:'bad'},{...body(),code:'123456',recovery_code:'R'.repeat(22)},{...body(),code:123456}])
   await assert.rejects(e.api.close(id,value,e.handle),{code:'privacy_invalid_input'});
  await assert.rejects(e.api.close('foreign',body(),e.handle),{code:'privacy_invalid_input'});assert.equal(e.w.calls.length,before);
 });
 await test('receipt-contract-rejects-unknown-fields-duplicate-categories-and-invalid-policy',async()=>{
  const e=await fixture(),token=e.t.api.getToken();let value=null;
  e.control.hook=c=>c.path==='/api/account/privacy/requests/'+id?reply(200,value):null;
  const item={category:'personal_diary_days',status:'pending',reason:'synthetic_basis',deleted_rows:0};
  for(value of[{...receipt(),extra:'unexpected'},{...receipt(),items:[item,item]},
   {...receipt(),policy:{id:'synthetic_policy',version:1,digest:'bad'}},{...receipt(),id:123}]){
   const before=e.w.calls.length;await assert.rejects(e.api.status(id,e.handle),{code:'privacy_invalid_response'});
   assert.equal(e.w.calls.length,before+1);assert.equal(e.t.api.getToken(),token);
  }
 });
 await test('denied-epoch-publication-clears-local-access-without-false-receipt',async()=>{
  const e=await fixture(),before=e.w.calls.length;e.t.sandbox.localStorage.setItem=()=>{throw new DOMException('synthetic denied epoch','QuotaExceededError');};
  await assert.rejects(e.api.close(id,body(),e.handle),{code:'session_storage_error'});
  assert.equal(e.t.api.getToken(),'');assert.equal(e.w.calls.length,before+1);
 });
 await test('pagehide-suppresses-pending-closure-ack-without-a-second-request',async()=>{
  const e=await fixture(),gate=deferred(),began=deferred(),before=e.w.calls.length;
  e.control.hook=c=>c.path===endpoint?{...reply(200,{}),json:async()=>{began.resolve();await gate.promise;return receipt(true);}}:null;
  const pending=e.api.close(id,body(),e.handle);await began.promise;e.t.dispatch({type:'pagehide'});gate.resolve();
  await assert.rejects(pending,{code:'session_changed'});assert.equal(e.w.calls.length,before+1);assert.equal(e.t.api.getToken(),'');
 });
 process.stdout.write(JSON.stringify({scope:'Actual Api, VM realms and fetch/cookie/WebLock doubles; no HTTP or native browser claim.',passed:results.length,total:results.length,results}));
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
