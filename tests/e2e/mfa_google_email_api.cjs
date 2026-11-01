/* Actual exact-access API; Google/mail responses are synthetic and no provider runs. */
'use strict';
const assert=require('node:assert/strict');
const {world}=require('./browser_harness31.cjs');
const reply=(status,data)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>data});
const challenge=()=>({email_verification_required:true,challenge:'C'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString(),masked_email:'s***@example.invalid',resend_after_seconds:60});
const receipt=()=>({reauthentication_token:'R'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString()});
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};};
async function fixture(){
  const w=world(),t=w.tab(),control={hook:null};t.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
  t.hook(async call=>{if(control.hook){const value=await control.hook(call);if(value)return value;}if(call.path.endsWith('/google-email/request'))return reply(202,challenge());if(call.path.endsWith('/google-email/verify'))return reply(200,receipt());});
  await t.api.session.ready;return{w,t,control,handle:t.api.mfa.capture()};
}
const rows=[];
async function test(name,run){try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name,code:error.code||null,frames:String(error.stack).split('\n').slice(1,4)});}}
(async()=>{
  await test('Google basic request uses the browser cookie boundary and only returns a fresh mailbox challenge',async()=>{
    const e=await fixture(),value=await e.t.api.mfa.googleEmailRequest({google_credential:'synthetic-google-basic'},e.handle);
    assert.equal(value.email_verification_required,true);assert.equal(Object.hasOwn(value,'reauthentication_token'),false);
    const call=e.w.calls.find(c=>c.path.endsWith('/google-email/request'));assert.deepEqual(JSON.parse(JSON.stringify(call.body)),{google_credential:'synthetic-google-basic'});
    assert.equal(call.options.credentials,'same-origin');assert.equal(call.options.headers['X-MetodoBase-Browser'],'1');assert.ok(e.w.writes.every(row=>row.key==='mb_session_epoch'));
  });
  await test('The explicit code returns only the existing reauthentication proof, not a session or factor',async()=>{
    const e=await fixture(),value=await e.t.api.mfa.googleEmailVerify({challenge:'C'.repeat(43),code:'123456'},e.handle);
    assert.equal(value.reauthentication_token,'R'.repeat(43));assert.equal(Object.hasOwn(value,'token'),false);assert.equal(Object.hasOwn(value,'enabled'),false);
    assert.equal(e.w.calls.filter(c=>c.path.includes('/enroll')).length,0);assert.ok(e.w.writes.every(row=>row.key==='mb_session_epoch'));
  });
  for(const value of [{...challenge(),token:'forbidden'},{...challenge(),challenge:'short'},{...challenge(),expires_at:'2001-01-01T00:00:00Z'},{...challenge(),resend_after_seconds:0}])await test('Malformed Google mailbox challenge fails closed '+Object.keys(value).join(','),async()=>{
    const e=await fixture();e.control.hook=call=>call.path.endsWith('/request')?reply(202,value):null;
    await assert.rejects(e.t.api.mfa.googleEmailRequest({google_credential:'synthetic-google-basic'},e.handle),{code:'mfa_invalid_response'});
  });
  for(const value of [{...receipt(),token:'forbidden'},{...receipt(),reauthentication_token:'short'},{...receipt(),expires_at:'2001-01-01T00:00:00Z'}])await test('Malformed Google mailbox proof fails closed '+Object.keys(value).join(','),async()=>{
    const e=await fixture();e.control.hook=call=>call.path.endsWith('/verify')?reply(200,value):null;
    await assert.rejects(e.t.api.mfa.googleEmailVerify({challenge:'C'.repeat(43),code:'123456'},e.handle),{code:'mfa_invalid_response'});
  });
  await test('Request/verify must retain their exact 202/200 protocol status',async()=>{
    const e=await fixture();e.control.hook=call=>call.path.endsWith('/request')?reply(200,challenge()):call.path.endsWith('/verify')?reply(202,receipt()):null;
    await assert.rejects(e.t.api.mfa.googleEmailRequest({google_credential:'synthetic-google-basic'},e.handle),{code:'mfa_invalid_response'});
    await assert.rejects(e.t.api.mfa.googleEmailVerify({challenge:'C'.repeat(43),code:'123456'},e.handle),{code:'mfa_invalid_response'});
  });
  await test('Invalid code and arbitrary Google payload keys are rejected before any mail request',async()=>{
    const e=await fixture(),before=e.w.calls.length;
    await assert.rejects(e.t.api.mfa.googleEmailRequest({google_credential:'synthetic',email:'other@example.invalid'},e.handle),{code:'mfa_invalid_input'});
    await assert.rejects(e.t.api.mfa.googleEmailVerify({challenge:'C'.repeat(43),code:'12345'},e.handle),{code:'mfa_invalid_input'});
    assert.equal(e.w.calls.length,before);
  });
  for(const endpoint of ['request','verify'])await test('Late '+endpoint+' from account A is rejected after account B replacement',async()=>{
    const e=await fixture(),gate=deferred(),started=deferred();e.control.hook=call=>{if(call.path.endsWith('/'+endpoint)){started.resolve();return{...reply(endpoint==='request'?202:200,{}),json:async()=>{await gate.promise;return endpoint==='request'?challenge():receipt();}};}};
    const pending=endpoint==='request'?e.t.api.mfa.googleEmailRequest({google_credential:'synthetic'},e.handle):e.t.api.mfa.googleEmailVerify({challenge:'C'.repeat(43),code:'123456'},e.handle);
    await started.promise;e.w.shared.set('mb_session_epoch','22222222-2222-4222-8222-222222222222');e.t.dispatch({type:'storage',key:'mb_session_epoch'});gate.resolve();
    await assert.rejects(pending,{code:'session_changed'});
  });
  console.log(JSON.stringify({scope:'Actual Api in browser-session VM; synthetic Google and mail responses, no real send or provider',passed:rows.filter(row=>row.passed).length,total:rows.length,results:rows},null,2));if(rows.some(row=>!row.passed))process.exitCode=1;
})();
