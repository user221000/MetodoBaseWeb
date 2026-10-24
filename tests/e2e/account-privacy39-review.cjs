'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=process.argv[2]?path.resolve(process.argv[2]):path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'web/static/js/account-privacy39.js'),'utf8');
const context={crypto:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'},Date,console};
vm.createContext(context);vm.runInContext(source,context,{filename:'account-privacy39.js'});
const {create}=context.AccountPrivacy39;
const proof={reauthentication_token:'P'.repeat(43),expires_at:new Date(Date.now()+60000).toISOString()};
const request={id:'a'.repeat(32),version:1,state:'blocked',reason:'policy_required',account_closed:false,
 erasure_complete:false,policy:null,items:[]};
const clone=value=>JSON.parse(JSON.stringify(value));
function fixture({enabled=false,mode='closed',statusVersion=1,reauth=async()=>clone(proof)}={}){
 const calls={create:0,status:0,verify:0,reauth:0,close:0},closed=[];
 const handle={},state={live:true,foreign:false},messages=[];let controller,accepted=null,body=null;
 const api={
  async context(){return{handle,me:{id:'self',role:'viewer',session_version:0}};},
  check(value){assert.equal(value,handle);if(!state.live)throw Object.assign(Error('changed'),{code:'session_changed'});},
  async verify(value){this.check(value);calls.verify++;},
  async create(key,value){this.check(value);calls.create++;return clone(request);},
  async status(id,value){this.check(value);calls.status++;return{...clone(request),version:statusVersion};},
  async factorStatus(value){this.check(value);return{enabled,totp_period_seconds:30,challenge_lifetime_seconds:300,recovery_codes_remaining:8};},
  async reauth(primary,value){this.check(value);calls.reauth++;assert.equal(Object.keys(primary).length,1);return reauth(primary);},
  async close(id,value,token){this.check(token);calls.close++;body=clone(value);assert.equal(id,request.id);
   if(mode==='blocked')return{state:'blocked',server_confirmed:false,account_closed:false,receipt:{...clone(request),version:2}};
   state.live=false;controller.invalidate();
   accepted=Object.freeze({state:mode==='unconfirmed'?'unconfirmed':'closed',server_confirmed:mode!=='unconfirmed',
    account_closed:mode!=='unconfirmed',receipt:mode==='unconfirmed'?null:{id:request.id,state:'eligible',account_closed:true,erasure_complete:false,items:[]}});
   if(mode==='foreign')state.foreign=true;
   return accepted;
  },
  checkClosed(result){if(result!==accepted||state.foreign)throw Object.assign(Error('changed'),{code:'session_changed'});},
 };
 controller=create({api,onState:value=>messages.push(value.message),onClear:()=>{},onClosed:value=>closed.push(value)});
 return{controller,calls,closed,state,messages,get body(){return body;}};
}
async function ready(value){assert(await value.controller.request());assert(await value.controller.prepareClose());return value;}
const results=[];
async function test(name,run){await run();results.push({name,passed:true});}
(async()=>{
 await test('explicit-confirmation-precedes-primary-proof',async()=>{
  const f=await ready(fixture());assert.equal(await f.controller.close({confirm:false},{password:'synthetic-primary'}),false);
  assert.equal(f.calls.reauth,0);assert.equal(f.calls.close,0);
 });
 await test('enabled-current-factor-required-before-primary-proof',async()=>{
  const f=await ready(fixture({enabled:true}));assert.equal(await f.controller.close({confirm:true,method:'totp',factor:'123'},{password:'synthetic-primary'}),false);
  assert.equal(f.calls.reauth,0);assert.equal(f.calls.close,0);
 });
 await test('sv-plus-one-preserves-bound-receipt-without-post-close-me',async()=>{
  const f=await ready(fixture()),before=f.calls.verify;
  assert.equal(await f.controller.close({confirm:true},{password:'synthetic-primary'}),true);
  assert.equal(f.calls.verify,before);assert.equal(f.closed.length,1);assert.equal(f.closed[0].receipt.erasure_complete,false);
  assert.equal(f.controller.view().dead,true);assert.equal(f.calls.close,1);
 });
 await test('later-account-suppresses-old-closure-receipt',async()=>{
  const f=await ready(fixture({mode:'foreign'}));assert.equal(await f.controller.close({confirm:true},{password:'synthetic-primary'}),false);
  assert.equal(f.closed.length,0);assert.equal(f.calls.close,1);
 });
 await test('policy-blocked-preserves-session-and-distinguishes-erasure',async()=>{
  const f=await ready(fixture({mode:'blocked'}));assert.equal(await f.controller.close({confirm:true},{password:'synthetic-primary'}),false);
  assert(f.state.live);assert.equal(f.closed.length,0);assert.equal(f.controller.view().receipt.account_closed,false);
  assert.equal(f.controller.view().closureReady,false);assert.equal(f.calls.close,1);
 });
 await test('ambiguous-close-retires-local-session-without-retry-or-server-claim',async()=>{
  const f=await ready(fixture({mode:'unconfirmed'})),before=f.calls.verify;
  assert.equal(await f.controller.close({confirm:true},{password:'synthetic-primary'}),false);
  assert.equal(f.closed.length,1);assert.equal(f.closed[0].server_confirmed,false);assert.equal(f.closed[0].receipt,null);
  assert.equal(f.calls.close,1);assert.equal(f.calls.verify,before);
 });
 await test('account-change-during-primary-proof-prevents-close',async()=>{
  let finish;const pending=new Promise(resolve=>{finish=resolve;});
  const f=await ready(fixture({reauth:()=>pending}));const closing=f.controller.close({confirm:true},{password:'synthetic-primary'});
  f.controller.invalidate();finish(clone(proof));assert.equal(await closing,false);assert.equal(f.calls.close,0);
 });
 await test('expired-proof-never-reaches-close',async()=>{
  const f=await ready(fixture({reauth:async()=>({...proof,expires_at:'2000-01-01T00:00:00Z'})}));
  assert.equal(await f.controller.close({confirm:true},{password:'synthetic-primary'}),false);assert.equal(f.calls.close,0);
 });
 await test('current-totp-is-single-factor-and-proof-is-in-memory-only',async()=>{
  const f=await ready(fixture({enabled:true}));assert(await f.controller.close({confirm:true,method:'totp',factor:'123456'},{password:'synthetic-primary'}));
  assert.equal(f.body.code,'123456');assert.equal(f.body.recovery_code,undefined);assert.equal(f.body.reauthentication_token,'P'.repeat(43));
  assert.equal(f.body.confirmation,'close_account');assert.equal(f.body.expected_version,1);
 });
 await test('current-recovery-code-keeps-explicit-method',async()=>{
  const f=await ready(fixture({enabled:true}));assert(await f.controller.close({confirm:true,method:'recovery_code',factor:'R'.repeat(22)},{password:'synthetic-primary'}));
  assert.equal(f.body.recovery_code,'R'.repeat(22));assert.equal(f.body.code,undefined);
 });
 await test('closed-controller-cannot-request-or-close-again',async()=>{
  const f=await ready(fixture());await f.controller.close({confirm:true},{password:'synthetic-primary'});
  await f.controller.request();await f.controller.refresh();await f.controller.facts();await f.controller.close({confirm:true},{password:'synthetic-primary'});
  assert.equal(f.calls.create,1);assert.equal(f.calls.close,1);
 });
 await test('no-raw-proof-input-or-html-interpolation-in-privacy-view',async()=>{
  const template=fs.readFileSync(path.join(root,'web/templates/_account_privacy39_content.html'),'utf8');
  assert(!template.includes('reauthentication_token'));assert(!source.includes('innerHTML'));assert(template.includes('data-privacy39-confirm'));
 });
 await test('opaque-google-intent-binds-confirmation-request-and-current-factor',async()=>{
  const f=await ready(fixture({enabled:true}));const intent=f.controller.prepare({confirm:true,method:'totp',factor:'123456'});
  assert.equal(Object.keys(intent).length,0);assert(await f.controller.close(null,{google_credential:'synthetic-linked-google'},intent));
  assert.equal(f.body.code,'123456');assert.equal(f.calls.reauth,1);assert.equal(f.calls.close,1);
 });
 await test('updated-request-rejects-old-google-intent-before-primary-proof',async()=>{
  const f=await ready(fixture({statusVersion:2})),intent=f.controller.prepare({confirm:true});await f.controller.refresh();
  assert.equal(await f.controller.close(null,{google_credential:'synthetic-stale-google'},intent),false);
  assert.equal(f.calls.reauth,0);assert.equal(f.calls.close,0);
 });
 await test('google-intent-is-one-use-after-policy-blocked-response',async()=>{
  const f=await ready(fixture({mode:'blocked'})),intent=f.controller.prepare({confirm:true});
  assert.equal(await f.controller.close(null,{google_credential:'synthetic-linked-google'},intent),false);
  assert(await f.controller.prepareClose());
  assert.equal(await f.controller.close(null,{google_credential:'synthetic-replayed-google'},intent),false);
  assert.equal(f.calls.reauth,1);assert.equal(f.calls.close,1);
 });
 process.stdout.write(JSON.stringify({passed:results.length,total:results.length,results}));
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
