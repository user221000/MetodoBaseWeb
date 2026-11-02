/* Actual exported Api, deterministic browser session and provider wire only. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..');
process.env.BROWSER31_SOURCE=process.env.BROWSER31_SOURCE||path.join(root,'web/static/js/api.js');
const {world}=require('./browser_harness31.cjs');
const rows=[];
const reply=(status,data)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>data});
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};};
const payPaths=new Set(['/api/billing/checkout','/api/billing/stripe/subscribe','/api/billing/confirm-subscription','/api/billing/portal','/api/billing/mp/preference','/api/usuario/checkout']);
async function fixture({verified=true,enrolled=false}={}){
  const w=world(),t=w.tab(),state={verified,enrolled,hook:null,steps:[],ui:[],payments:[],mail:[]};
  t.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
  t.hook(async call=>{
    if(state.hook){const value=await state.hook(call);if(value)return value;}
    if(call.path==='/api/billing/email-verification/request'){
      state.mail.push(call);return reply(200,state.verified?{email_verification_required:false,email_verified:true}:
        {email_verification_required:true,challenge:'C'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString(),masked_email:'s***@example.invalid',resend_after_seconds:60});
    }
    if(call.path==='/api/billing/email-verification/verify'){
      assert.equal(call.body.code,'123456');state.mail.push(call);return reply(200,{verification_token:'V'.repeat(43),expires_in_seconds:300});
    }
    if(call.path==='/api/auth/mfa/step-up'){
      state.steps.push(call);
      if(!state.enrolled)return reply(403,{detail:{code:'mfa_enrollment_required',message:'Synthetic factor enrollment blocker'}});
      const action=call.body.path.includes('/mp/')?'billing.mp':call.body.path.endsWith('/portal')?'billing.portal':call.body.path.endsWith('confirm-subscription')?'billing.confirm':call.body.path.endsWith('subscribe')?'billing.subscribe':'billing.checkout';
      return reply(200,{grant:'G'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString(),action,method:call.body.method,path:call.body.path,single_use:true});
    }
    if(payPaths.has(call.path)){
      state.payments.push(call);return reply(200,{url:call.path.endsWith('/portal')?'https://billing.stripe.com/synthetic':'https://checkout.stripe.com/synthetic',status:'pending'});
    }
  });
  t.sandbox.MfaUI={async authorize(operation){state.ui.push(operation);throw Object.assign(Error('Synthetic enrollment prompt'),{code:'mfa_enrollment_required'});}};
  t.sandbox.BillingEmailVerification={async authorize(action,plan,handle,initial){
    const proof=await t.api.billingEmail.verify(action,plan,initial.challenge,'123456',handle);return proof.verification_token;
  }};
  await t.api.session.ready;
  return{w,t,state};
}
function noFactor(e){assert.equal(e.state.steps.length,0);assert.equal(e.state.ui.length,0);}
function requestOnly(e,target){assert.equal(e.state.payments.length,1);assert.equal(e.state.payments[0].path,target);assert.equal(e.state.payments[0].options.headers['X-MFA-Grant'],undefined);}
async function limited(run){let timer;try{return await Promise.race([run(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Case timeout')),3000);})]);}finally{clearTimeout(timer);}}
async function test(name,run){try{await limited(run);rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name,code:error.code||null,message:error.message});}}
(async()=>{
  for(const plan of['standard','gym_comercial','clinica']){
    await test('Unenrolled owner starts '+plan+' checkout without an application factor',async()=>{
      const e=await fixture(),value=await e.t.api.billing.checkout(plan,'owned-'+plan);
      noFactor(e);requestOnly(e,'/api/billing/checkout');e.t.api.billingEmail.checkResult(value);
      const c=e.state.payments[0];assert.equal(c.options.headers['Idempotency-Key'],'owned-'+plan);assert.deepEqual(c.body,{plan,success_url:'/suscripciones?result=success',cancel_url:'/suscripciones?result=canceled'});
      assert.equal(c.options.cache,'no-store');assert.equal(c.options.referrerPolicy,'no-referrer');assert.equal(c.options.headers['X-Billing-Email-Grant'],undefined);
    });
    await test('Unenrolled owner starts '+plan+' Elements subscription without an application factor',async()=>{
      const e=await fixture(),value=await e.t.api.billing.stripeSubscribe(plan,'pm_synthetic','elements-'+plan);
      noFactor(e);requestOnly(e,'/api/billing/stripe/subscribe');e.t.api.billingEmail.checkResult(value);
      assert.deepEqual(e.state.payments[0].body,{plan,payment_method_id:'pm_synthetic'});
    });
  }
  await test('Existing Stripe owner opens its management portal without enrollment',async()=>{
    const e=await fixture(),value=await e.t.api.billing.portal();noFactor(e);requestOnly(e,'/api/billing/portal');
    assert.deepEqual(e.state.payments[0].body,{return_url:'/suscripciones'});assert.equal(e.state.payments[0].options.headers['Idempotency-Key'],undefined);e.t.api.billingEmail.checkResult(value);
  });
  await test('Unenrolled owner confirms a subscription on the current exact access',async()=>{
    const e=await fixture();await e.t.api.billing.confirmSubscription('sub_synthetic');noFactor(e);requestOnly(e,'/api/billing/confirm-subscription');
    const c=e.state.payments[0];assert.deepEqual(c.body,{subscription_id:'sub_synthetic'});assert.equal(c.options.cache,'no-store');assert.equal(e.state.mail.length,0);
  });
  await test('Enrolled owner is not asked for a second account proof when buying Stripe',async()=>{
    const e=await fixture({enrolled:true});await e.t.api.billing.checkout('standard','enrolled-owner-key');noFactor(e);requestOnly(e,'/api/billing/checkout');
  });
  await test('Unverified contact still completes the existing mailbox proof before Stripe',async()=>{
    const e=await fixture({verified:false});await e.t.api.billing.checkout('clinica','mailbox-owner-key');noFactor(e);requestOnly(e,'/api/billing/checkout');
    assert.equal(e.state.mail.length,2);assert.equal(e.state.payments[0].options.headers['X-Billing-Email-Grant'],'V'.repeat(43));
    const order=e.w.calls.map(c=>c.path);assert.ok(order.indexOf('/api/billing/email-verification/verify')<order.indexOf('/api/billing/checkout'));
    assert.ok(e.w.writes.every(row=>row.key==='mb_session_epoch'));
  });
  await test('Individual checkout retains its existing factor-free flow',async()=>{
    const e=await fixture();await e.t.api.usuario.checkout('personal-owner-key');noFactor(e);requestOnly(e,'/api/usuario/checkout');
  });
  await test('Mercado Pago still requires the existing account factor',async()=>{
    const e=await fixture();await assert.rejects(e.t.api.billing.mpPreference('standard','mp-owner-key'),{code:'mfa_enrollment_required'});
    assert.equal(e.state.steps.length,1);assert.equal(e.state.ui.length,1);assert.equal(e.state.payments.length,0);
  });
  await test('Mercado Pago with a valid existing grant keeps its exact DTO and key',async()=>{
    const e=await fixture({enrolled:true});await e.t.api.billing.mpPreference('standard','mp-owner-key');
    assert.equal(e.state.steps.length,1);assert.equal(e.state.ui.length,0);assert.equal(e.state.payments.length,1);
    assert.equal(e.state.payments[0].options.headers['X-MFA-Grant'],'G'.repeat(43));assert.equal(e.state.payments[0].options.headers['Idempotency-Key'],'mp-owner-key');
  });
  await test('Team security still asks for an account factor',async()=>{
    const e=await fixture();await assert.rejects(e.t.api.mfa.perform('DELETE','/api/gym/team/member',{}),{code:'mfa_enrollment_required'});
    assert.equal(e.state.steps.length,1);assert.equal(e.state.ui.length,1);assert.equal(e.state.payments.length,0);
  });
  await test('Malformed confirmed-contact response cannot start a payment',async()=>{
    const e=await fixture();e.state.hook=c=>c.path.endsWith('/email-verification/request')?reply(200,{email_verification_required:false}):null;
    await assert.rejects(e.t.api.billing.checkout('standard','malformed-key'),{code:'billing_email_invalid_response'});assert.equal(e.state.payments.length,0);noFactor(e);
  });
  await test('Canceled contact dialog never reaches Stripe or enrollment',async()=>{
    const e=await fixture({verified:false});e.t.sandbox.BillingEmailVerification.authorize=async()=>{throw Object.assign(Error('Synthetic cancellation'),{code:'billing_email_cancelled'});};
    await assert.rejects(e.t.api.billing.checkout('standard','cancel-key'),error=>error.code==='billing_email_cancelled'&&error.paymentNotStarted===true);assert.equal(e.state.payments.length,0);noFactor(e);
  });
  await test('Account replacement during mailbox admission blocks checkout',async()=>{
    const e=await fixture(),gate=deferred(),started=deferred();
    e.state.hook=c=>{if(c.path.endsWith('/email-verification/request')){started.resolve();return{...reply(200,{}),json:async()=>{await gate.promise;return{email_verification_required:false,email_verified:true};}};}};
    const pending=e.t.api.billing.checkout('standard','changed-key');await started.promise;e.w.shared.set('mb_session_epoch',crypto.randomUUID());e.t.dispatch({type:'storage',key:'mb_session_epoch'});gate.resolve();
    await assert.rejects(pending,{code:'session_changed'});assert.equal(e.state.payments.length,0);noFactor(e);
  });
  await test('Pagehide during mailbox verification cannot deliver a payment',async()=>{
    const e=await fixture({verified:false}),gate=deferred(),started=deferred();
    e.state.hook=c=>{if(c.path.endsWith('/email-verification/verify')){started.resolve();return{...reply(200,{}),json:async()=>{await gate.promise;return{verification_token:'V'.repeat(43),expires_in_seconds:300};}};}};
    const pending=e.t.api.billing.checkout('standard','hidden-key');await started.promise;e.t.dispatch({type:'pagehide'});gate.resolve();
    await assert.rejects(pending,{code:'session_changed'});assert.equal(e.state.payments.length,0);noFactor(e);
  });
  for(const [label,invoke,target]of[
    ['checkout',api=>api.billing.checkout('standard','auth-key'),'/api/billing/checkout'],
    ['confirmation',api=>api.billing.confirmSubscription('sub_synthetic'),'/api/billing/confirm-subscription']])await test('Stripe '+label+'401 is not refreshed or automatically replayed',async()=>{
      const e=await fixture(),before=e.w.calls.filter(c=>c.path.endsWith('/refresh')).length;let attempts=0;
      e.state.hook=c=>{if(c.path===target){attempts++;return reply(401,{detail:{code:'identity_unavailable'}});}};
      await assert.rejects(invoke(e.t.api),{code:'identity_unavailable'});assert.equal(attempts,1);assert.equal(e.w.calls.filter(c=>c.path.endsWith('/refresh')).length,before);noFactor(e);
    });
  await test('An uncertain Stripe payment is sent once and an explicit retry keeps the caller key',async()=>{
    const e=await fixture();let attempts=0;e.state.hook=c=>{if(c.path==='/api/billing/checkout'){attempts++;if(attempts===1)throw Error('Synthetic network uncertainty');}};
    await assert.rejects(e.t.api.billing.checkout('standard','same-owned-key'));assert.equal(attempts,1);
    await e.t.api.billing.checkout('standard','same-owned-key');assert.equal(attempts,2);
    assert.deepEqual(e.w.calls.filter(c=>c.path==='/api/billing/checkout').map(c=>c.options.headers['Idempotency-Key']),['same-owned-key','same-owned-key']);noFactor(e);
  });
  await test('A late Stripe response cannot authorize redirect after another account wins',async()=>{
    const e=await fixture(),value=await e.t.api.billing.portal();e.w.shared.set('mb_session_epoch',crypto.randomUUID());e.t.dispatch({type:'storage',key:'mb_session_epoch'});
    assert.throws(()=>e.t.api.billingEmail.checkResult(value),{code:'session_changed'});noFactor(e);
  });
  const report={scope:'Actual exported Api with synthetic in-memory browser session, contact and provider transports; not live provider acceptance',completed:true,
    source_sha256:crypto.createHash('sha256').update(fs.readFileSync(process.env.BROWSER31_SOURCE)).digest('hex'),passed:rows.filter(r=>r.passed).length,total:rows.length,results:rows};
  process.stdout.write(JSON.stringify(report,null,2)+'\n');if(report.passed!==report.total||report.total!==22)process.exitCode=1;
})().catch(error=>{process.stderr.write(JSON.stringify({fatal:error.name,code:error.code||null})+'\n');process.exitCode=1;});
