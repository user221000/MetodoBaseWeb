/* Actual Api in browser-session VM; all mail/payment responses are synthetic. */
'use strict';
const assert=require('node:assert/strict');
const {world,tick}=require('./browser_harness31.cjs');
const reply=(status,data)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>data});
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};};
const challenge=()=>({email_verification_required:true,challenge:'C'.repeat(43),expires_at:new Date(Date.now()+600000).toISOString(),masked_email:'s***@example.invalid',resend_after_seconds:60});
const verification=()=>({verification_token:'V'.repeat(43),expires_in_seconds:300});
const paths=new Set(['/api/billing/checkout','/api/billing/stripe/subscribe','/api/billing/mp/preference','/api/billing/portal','/api/usuario/checkout','/api/usuario/stripe-subscribe','/api/usuario/mp-preference','/api/usuario/billing-portal']);
async function fixture(){
  const w=world(),t=w.tab(),control={hook:null,uiCalls:[],payments:[],codeVerified:false,emailVerified:false,heldUI:null};
  t.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
  t.hook(async call=>{
    if(control.hook){const result=await control.hook(call);if(result)return result;}
    if(call.path==='/api/billing/email-verification/request')return reply(200,control.emailVerified?{email_verification_required:false,email_verified:true}:challenge());
    if(call.path==='/api/billing/email-verification/verify'){control.codeVerified=true;assert.equal(call.body.code,'123456');return reply(200,verification());}
    if(call.path==='/api/auth/mfa/step-up'){
      const action=call.body.path.endsWith('/checkout')?'billing.checkout':call.body.path.endsWith('/subscribe')?'billing.subscribe':call.body.path.endsWith('/portal')?'billing.portal':'billing.mp';
      return reply(200,{grant:'G'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString(),action,method:call.body.method,path:call.body.path,single_use:true});
    }
    if(paths.has(call.path)){
      assert.equal(control.codeVerified||control.emailVerified,true,'No payment port before mailbox confirmation');
      assert.equal(call.options.headers['X-Billing-Email-Grant'],control.emailVerified?undefined:'V'.repeat(43));
      control.payments.push(call);return reply(200,{url:'https://checkout.stripe.com/synthetic',redirect_url:'https://www.mercadopago.com.mx/synthetic'});
    }
  });
  await t.api.session.ready;
  t.sandbox.BillingEmailVerification={async authorize(action,plan,handle,initial){
    control.uiCalls.push({action,plan});
    if(control.heldUI)return control.heldUI.promise;
    const value=initial||await t.api.billingEmail.begin(action,plan,handle);
    const proof=await t.api.billingEmail.verify(action,plan,value.challenge,'123456',handle);
    return proof.verification_token;
  }};
  return {w,t,control};
}
const rows=[];
async function test(name,run){try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_type:error.name,code:error.code||null,frames:error.stack?.split('\n').slice(1,5)});}}
const cases=[
  ['gym_stripe_checkout','standard','/api/billing/checkout',api=>api.billing.checkout('standard','owned-checkout-key'),true],
  ['gym_stripe_subscribe','gym_comercial','/api/billing/stripe/subscribe',api=>api.billing.stripeSubscribe('gym_comercial','pm_synthetic','owned-elements-key'),true],
  ['gym_mp_preference','clinica','/api/billing/mp/preference',api=>api.billing.mpPreference('clinica','owned-mp-key'),true],
  ['gym_stripe_portal','manage','/api/billing/portal',api=>api.billing.portal(),true],
  ['personal_stripe_checkout','pro','/api/usuario/checkout',api=>api.usuario.checkout('owned-personal-key'),false],
  ['personal_stripe_subscribe','pro','/api/usuario/stripe-subscribe',api=>api.usuario.stripeSubscribe('pro','pm_synthetic','owned-personal-elements-key'),false],
  ['personal_mp_preference','pro','/api/usuario/mp-preference',api=>api.usuario.mpPreference('pro','owned-personal-mp-key'),false],
  ['personal_stripe_portal','manage','/api/usuario/billing-portal',api=>api.usuario.portal(),false],
];
(async()=>{
  for(const [action,plan,path,invoke,mfa] of cases)await test(action+' verifies mailbox before this exact payment capability',async()=>{
    const e=await fixture(),value=await invoke(e.t.api);
    assert.deepEqual(e.control.uiCalls,[{action,plan}]);assert.equal(e.control.payments.length,1);
    const payment=e.control.payments[0];assert.equal(payment.path,path);
    assert.equal(!!payment.options.headers['X-MFA-Grant'],mfa);
    assert.equal(Object.hasOwn(payment.body,'verification_token'),false);assert.equal(Object.hasOwn(payment.body,'code'),false);
    assert.equal(payment.options.cache,'no-store');assert.equal(payment.options.referrerPolicy,'no-referrer');
    e.t.api.billingEmail.checkResult(value);assert.throws(()=>e.t.api.billingEmail.checkResult({...value}),{code:'session_changed'});
    const order=e.w.calls.map(call=>call.path);assert.ok(order.indexOf('/api/billing/email-verification/verify')<order.indexOf(path));
    assert.ok(e.w.writes.every(row=>row.key==='mb_session_epoch'));
    assert.equal(e.w.calls.filter(call=>call.path.endsWith('/email-verification/request')).length,1);
  });
  for(const [action,plan,path,invoke,mfa] of cases)await test(action+' reuses server-confirmed current mailbox without modal or email header',async()=>{
    const e=await fixture();e.control.emailVerified=true;e.t.sandbox.BillingEmailVerification=null;
    const value=await invoke(e.t.api);assert.equal(e.control.uiCalls.length,0);assert.equal(e.control.payments.length,1);
    assert.equal(e.control.payments[0].path,path);assert.equal(!!e.control.payments[0].options.headers['X-MFA-Grant'],mfa);
    assert.equal(Object.hasOwn(e.control.payments[0].options.headers,'X-Billing-Email-Grant'),false);
    assert.equal(e.w.calls.filter(call=>call.path.endsWith('/email-verification/request')).length,1);
    assert.equal(e.w.calls.filter(call=>call.path.endsWith('/email-verification/verify')).length,0);
    e.t.api.billingEmail.checkResult(value);
  });
  for(const malformed of [{email_verification_required:false},{email_verification_required:false,email_verified:false},{email_verification_required:false,email_verified:true,challenge:'C'.repeat(43)},{email_verification_required:false,email_verified:true,verification_token:'V'.repeat(43)}])await test('Malformed already-confirmed mailbox response fails closed '+Object.keys(malformed).join(','),async()=>{
    const e=await fixture();e.control.hook=call=>call.path.endsWith('/email-verification/request')?reply(200,malformed):null;
    await assert.rejects(e.t.api.usuario.checkout('owned-key'),{code:'billing_email_invalid_response'});assert.equal(e.control.payments.length,0);assert.equal(e.control.uiCalls.length,0);
  });
  await test('A modal cannot manufacture an already-confirmed mailbox receipt',async()=>{
    const e=await fixture();e.t.sandbox.BillingEmailVerification.authorize=async()=>({email_verification_required:false,email_verified:true});
    await assert.rejects(e.t.api.billing.checkout('standard','owned-key'),{code:'billing_email_invalid_proof'});assert.equal(e.control.payments.length,0);
  });
  await test('An already-confirmed mailbox reply from account A cannot pay after account B replaces it',async()=>{
    const e=await fixture(),gate=deferred(),started=deferred();e.control.emailVerified=true;
    e.control.hook=call=>{if(call.path.endsWith('/email-verification/request')){started.resolve();return{...reply(200,{}),json:async()=>{await gate.promise;return{email_verification_required:false,email_verified:true};}};}};
    const pending=e.t.api.usuario.checkout('owned-key');await started.promise;
    e.w.shared.set('mb_session_epoch','22222222-2222-4222-8222-222222222222');e.t.dispatch({type:'storage',key:'mb_session_epoch'});gate.resolve();
    await assert.rejects(pending,{code:'session_changed'});assert.equal(e.control.payments.length,0);assert.equal(e.control.uiCalls.length,0);
  });
  await test('A cancelled mailbox dialog never requests MFA or payment',async()=>{
    const e=await fixture();e.t.sandbox.BillingEmailVerification.authorize=async()=>{throw Object.assign(Error('Synthetic cancel'),{code:'billing_email_cancelled'});};
    await assert.rejects(e.t.api.billing.checkout('standard','owned-key'),error=>error.code==='billing_email_cancelled'&&error.paymentNotStarted===true);
    assert.equal(e.control.payments.length,0);assert.equal(e.w.calls.filter(c=>c.path.includes('step-up')).length,0);
  });
  await test('Unavailable mail returns without a payment attempt or automatic retry',async()=>{
    const e=await fixture();e.control.hook=c=>c.path.endsWith('/email-verification/request')?reply(503,{detail:{code:'billing_email_unavailable',message:'Synthetic mail unavailable'}}):null;
    const before=e.w.calls.length;await assert.rejects(e.t.api.usuario.checkout('owned-key'),e=>e.code==='billing_email_unavailable'&&e.paymentNotStarted===true);
    assert.equal(e.control.payments.length,0);assert.equal(e.w.calls.slice(before).filter(c=>c.path.endsWith('/request')).length,1);
  });
  for(const malformed of [{...challenge(),token:'forbidden'}, {...challenge(),challenge:'short'}, {...challenge(),expires_at:'2001-01-01T00:00:00Z'}, {...challenge(),resend_after_seconds:0}])await test('Malformed mailbox challenge fails closed '+Object.keys(malformed).join(','),async()=>{
    const e=await fixture();e.control.hook=c=>c.path.endsWith('/email-verification/request')?reply(200,malformed):null;
    await assert.rejects(e.t.api.usuario.checkout('owned-key'),{code:'billing_email_invalid_response'});assert.equal(e.control.payments.length,0);
  });
  for(const malformed of [{...verification(),token:'forbidden'}, {...verification(),verification_token:'short'}, {...verification(),expires_in_seconds:600}])await test('Malformed mailbox grant fails closed '+Object.keys(malformed).join(','),async()=>{
    const e=await fixture();e.control.hook=c=>c.path.endsWith('/email-verification/verify')?reply(200,malformed):null;
    await assert.rejects(e.t.api.usuario.checkout('owned-key'),{code:'billing_email_invalid_response'});assert.equal(e.control.payments.length,0);
  });
  await test('Account replacement during code delivery discards its late response',async()=>{
    const e=await fixture(),gate=deferred(),started=deferred();
    e.control.hook=c=>{if(c.path.endsWith('/email-verification/request')){started.resolve();return{...reply(200,{}),json:async()=>{await gate.promise;return challenge();}};}};
    const pending=e.t.api.usuario.checkout('owned-key');await started.promise;
    e.w.shared.set('mb_session_epoch','22222222-2222-4222-8222-222222222222');e.t.dispatch({type:'storage',key:'mb_session_epoch'});gate.resolve();
    await assert.rejects(pending,{code:'session_changed'});assert.equal(e.control.payments.length,0);assert.equal(e.w.calls.filter(c=>c.path.endsWith('/verify')).length,0);
  });
  await test('Pagehide during mailbox confirmation cannot deliver a payment capability',async()=>{
    const e=await fixture(),gate=deferred(),started=deferred();
    e.control.hook=c=>{if(c.path.endsWith('/email-verification/verify')){started.resolve();return{...reply(200,{}),json:async()=>{await gate.promise;return verification();}};}};
    const pending=e.t.api.billing.checkout('standard','owned-key');await started.promise;e.t.dispatch({type:'pagehide'});gate.resolve();
    await assert.rejects(pending,{code:'session_changed'});assert.equal(e.control.payments.length,0);
  });
  await test('Mailbox401 remains on one exact access without cookie refresh',async()=>{
    const e=await fixture(),refreshes=e.w.calls.filter(c=>c.path.endsWith('/refresh')).length;
    e.control.hook=c=>c.path.endsWith('/email-verification/verify')?reply(401,{detail:{code:'billing_email_identity_changed'}}):null;
    await assert.rejects(e.t.api.usuario.checkout('owned-key'),{code:'billing_email_identity_changed'});
    assert.equal(e.w.calls.filter(c=>c.path.endsWith('/refresh')).length,refreshes);assert.equal(e.control.payments.length,0);
  });
  await test('Uncertain payment response is sent once and never automatically replayed',async()=>{
    const e=await fixture();let attempts=0;e.control.hook=c=>{if(c.path==='/api/usuario/checkout'){attempts++;throw Error('Synthetic network uncertainty');}};
    await assert.rejects(e.t.api.usuario.checkout('owned-key'));assert.equal(attempts,1);
    assert.equal(e.w.calls.filter(c=>c.path.endsWith('/email-verification/request')).length,1);
  });
  await test('Existing MFA factor interaction keeps original DTO, key and mailbox grant separate',async()=>{
    const e=await fixture();let factors=0;e.control.hook=c=>{if(c.path==='/api/auth/mfa/step-up' && factors++===0)return reply(403,{detail:{code:'mfa_fresh_verification_required'}});};
    e.t.sandbox.MfaUI={authorize:operation=>e.t.api.mfa.grant(operation,{code:'654321'})};
    await e.t.api.billing.checkout('standard','owned-mfa-key');
    const steps=e.w.calls.filter(c=>c.path==='/api/auth/mfa/step-up');assert.equal(steps.length,2);assert.equal(steps[1].body.code,'654321');
    const payment=e.control.payments[0];assert.equal(payment.options.headers['Idempotency-Key'],'owned-mfa-key');assert.equal(Object.hasOwn(payment.body,'code'),false);
    assert.equal(e.w.calls.filter(c=>c.path.endsWith('/email-verification/verify')).length,1);
  });
  await test('A successful response from an older account cannot redirect the replacement',async()=>{
    const e=await fixture(),value=await e.t.api.usuario.checkout('owned-key');
    e.w.shared.set('mb_session_epoch','33333333-3333-4333-8333-333333333333');e.t.dispatch({type:'storage',key:'mb_session_epoch'});
    assert.throws(()=>e.t.api.billingEmail.checkResult(value),{code:'session_changed'});
  });
  await test('Caller cannot inject arbitrary payment headers or an unregistered email permit',async()=>{
    const e=await fixture(),before=e.w.calls.length;
    await assert.rejects(e.t.api.mfa.perform('POST','/api/billing/portal',{return_url:'/suscripciones'},null,{proof:'V'.repeat(43)}),{code:'billing_email_invalid_proof'});
    assert.equal(e.w.calls.length,before);
  });
  await test('Input is rejected locally before requesting another mailbox code',async()=>{
    const e=await fixture(),{handle}=await e.t.api.mfa.context(),before=e.w.calls.length;
    await assert.rejects(e.t.api.billingEmail.begin('personal_stripe_checkout','clinica',handle),{code:'billing_email_invalid_input'});
    await assert.rejects(e.t.api.billingEmail.verify('personal_stripe_checkout','pro','C'.repeat(43),'12345',handle),{code:'billing_email_invalid_input'});
    assert.equal(e.w.calls.length,before);
  });
  console.log(JSON.stringify({scope:'Actual Api in browser-session VM with synthetic mail/MFA/payment transports; no real provider calls',passed:rows.filter(r=>r.passed).length,total:rows.length,results:rows},null,2));
  if(rows.some(row=>!row.passed))process.exitCode=1;
})();
