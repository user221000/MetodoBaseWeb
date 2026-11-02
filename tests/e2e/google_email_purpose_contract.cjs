/* Actual Api + MfaLogin composition. Synthetic wire/provider only; no real mailbox or account. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..');
process.env.BROWSER31_SOURCE=process.env.BROWSER31_SOURCE||path.join(root,'web/static/js/api.js');
const loginPath=process.env.GOOGLE_EMAIL_LOGIN_SOURCE||path.join(root,'web/static/js/mfa-login.js');
const {world}=require('./browser_harness31.cjs');
const loginSource=fs.readFileSync(loginPath,'utf8'),rows=[];
const reply=(status,data)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>data});
const expiry=()=>new Date(Date.now()+300000).toISOString();
const pendingEmail=()=>({email_verification_required:true,challenge:'C'.repeat(43),expires_at:expiry(),masked_email:'s***@example.invalid',session_mode:'browser'});
const pendingFactor=()=>({mfa_required:true,challenge:'F'.repeat(43),expires_at:expiry(),methods:['totp','recovery_code'],session_mode:'browser'});
const securityReceipt=()=>({reauthentication_token:'R'.repeat(43),expires_at:expiry()});
async function limited(run){let timer;try{return await Promise.race([run(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Object.assign(Error('Case did not settle'),{code:'test_timeout'})),3000);})]);}finally{clearTimeout(timer);}}
async function fixture({tipo='gym',factor=false,invalidFirst=false,security=false,loginReceipt=null}={}){
  const w=world({cookie:security?'A':null}),t=w.tab();
  t.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
  await t.api.session.ready;
  let verified=false,attempts=0,authenticated=0;
  const signedIn=()=>{w.jar.account='B';return reply(200,{token:'access-B-9000',tipo,role:tipo==='gym'?'owner':'viewer',session_mode:'browser'});};
  t.hook(call=>{
    if(call.path==='/api/auth/google')return reply(202,pendingEmail());
    if(call.path==='/api/auth/google/verify-email'){
      attempts++;
      if(invalidFirst&&attempts===1)return reply(400,{detail:{code:'google_email_code_invalid',message:'Synthetic wrong code'}});
      verified=true;
      return loginReceipt?reply(200,loginReceipt()):factor?reply(202,pendingFactor()):signedIn();
    }
    if(call.path==='/api/auth/mfa/login/verify')return signedIn();
    if(call.path==='/api/auth/mfa/google-email/verify')return security?reply(200,securityReceipt()):reply(403,{detail:{code:'browser_protocol_invalid',message:'Protected security operation'}});
    if(call.path==='/api/auth/me')return reply(200,{id:'B',tipo,role:tipo==='gym'?'owner':'viewer',session_version:1,team_gym_id:null});
  });
  vm.runInContext(loginSource,t.context);
  const controller=t.sandbox.MfaLogin.create({audience:tipo,ready:t.api.session.ready,onAuthenticated:async()=>{
    const {me}=await t.api.mfa.context();assert.equal(me.tipo,tipo);authenticated++;
  }});
  return {w,t,controller,get verified(){return verified;},get authenticated(){return authenticated;},get attempts(){return attempts;}};
}
async function test(name,body){let state;try{await limited(async()=>{state=await body();});rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name,code:error.code||null,message:error.message,...(state||{})});}}
async function google(e){assert.equal(await e.controller.primary('google',{credential:'synthetic-google-basic',tipo:'gym'}),true);assert.equal(e.controller.phase,'email');assert.equal(e.t.api.getToken(),'');}
(async()=>{
  for(const tipo of['gym','usuario'])for(const factor of[false,true])await test('Public Google '+tipo+' email proof uses only the login endpoint'+(factor?' before the existing MFA challenge':''),async()=>{
    const e=await fixture({tipo,factor});await google(e);
    const accepted=await e.controller.verifyEmail('123456');
    const actual=e.w.calls.filter(call=>call.path.endsWith('/verify-email')||call.path.endsWith('/google-email/verify')).map(call=>call.path);
    assert.deepEqual(actual,['/api/auth/google/verify-email'],'Mailbox login code must not enter the protected security endpoint');
    assert.equal(accepted,true);
    if(factor){assert.equal(e.controller.phase,'factor');assert.equal(e.t.api.getToken(),'');assert.equal(e.authenticated,0);assert.equal(await e.controller.verify('654321'),true);}
    assert.equal(e.controller.phase,'confirmed');assert.equal(e.authenticated,1);assert.equal(e.verified,true);
    const call=e.w.calls.find(call=>call.path==='/api/auth/google/verify-email');
    assert.equal(call.options.credentials,'same-origin');assert.equal(call.options.headers['X-MetodoBase-Browser'],'1');
    assert.equal(call.options.headers.Authorization,undefined);assert.equal(typeof call.body.code,'string');
    const requests=e.w.calls.length;assert.equal(await e.controller.verifyEmail('123456'),false);assert.equal(e.w.calls.length,requests,'Confirmed login does not replay email proof');
    assert.ok(e.w.writes.every(row=>row.key==='mb_session_epoch'),'No account credentials or proof in Storage');
  });
  await test('Invalid mailbox code retains the login challenge for a deliberate retry',async()=>{
    const e=await fixture({invalidFirst:true});await google(e);assert.equal(await e.controller.verifyEmail('000000'),false);
    assert.equal(e.controller.phase,'email');assert.equal(e.authenticated,0);assert.equal(await e.controller.verifyEmail('123456'),true);assert.equal(e.attempts,2);assert.equal(e.authenticated,1);
  });
  await test('Login and account-security commands remain distinct on the actual exported Api',async()=>{
    const e=await fixture({security:true});assert.equal(typeof e.t.api.mfa.loginGoogleEmailVerify,'function');assert.equal(typeof e.t.api.mfa.googleEmailVerify,'function');
    assert.notEqual(e.t.api.mfa.loginGoogleEmailVerify,e.t.api.mfa.googleEmailVerify);
    const access=e.t.api.getToken(),handle=e.t.api.mfa.capture(),receipt=await e.t.api.mfa.googleEmailVerify({challenge:'C'.repeat(43),code:'123456'},handle);
    assert.equal(receipt.reauthentication_token,'R'.repeat(43));assert.equal(e.t.api.getToken(),access);assert.equal(e.authenticated,0);
    const call=e.w.calls.find(call=>call.path==='/api/auth/mfa/google-email/verify');assert.ok(call.options.headers.Authorization.startsWith('Bearer '));
    assert.equal(e.w.calls.filter(call=>call.path==='/api/auth/google/verify-email').length,0);
  });
  await test('An account-security proof cannot masquerade as a public login receipt',async()=>{
    const e=await fixture({loginReceipt:securityReceipt});await google(e);assert.equal(await e.controller.verifyEmail('123456'),false);
    assert.equal(e.authenticated,0);assert.equal(e.t.api.getToken(),'');assert.notEqual(e.controller.phase,'confirmed');
  });
  const report={scope:'Actual exported api.js and actual MfaLogin state machine in the same browser-session VM. Deterministic cookie/WebLock/provider wire, not real HTTP, Redis, Google or inbox.',
    passed:rows.filter(row=>row.passed).length,total:rows.length,completed:true,
    sources:{api:crypto.createHash('sha256').update(fs.readFileSync(process.env.BROWSER31_SOURCE)).digest('hex'),login:crypto.createHash('sha256').update(loginSource).digest('hex')},results:rows};
  process.stdout.write(JSON.stringify(report,null,2)+'\n');if(report.total!==7||report.passed!==7)process.exitCode=1;
})().catch(error=>{process.stderr.write(JSON.stringify({fatal:error.name,code:error.code||null})+'\n');process.exitCode=1;});
