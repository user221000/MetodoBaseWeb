/* Actual Api transports; synthetic cookie/WebLock/server wire, no browser-header claim. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const source=process.env.BROWSER31_SOURCE||path.join(__dirname,'../../web/static/js/api.js');
process.env.BROWSER31_SOURCE=source;
const {world}=require('./browser_harness31.cjs');
const rows=[];
const reply=(status,data)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>data});
const expiry=()=>new Date(Date.now()+300000).toISOString();
const user={id:'A',tipo:'gym',role:'owner',session_version:1};
const signedIn=()=>({token:'synthetic-access-B',session_mode:'browser',tipo:'gym'});
const last=(w,url)=>{const result=w.calls.filter(call=>call.path===url).at(-1);assert.ok(result,'The real Api must dispatch the expected route');return result;};
function checkPost(call,{authenticated=false,csrf=false}={}){
  assert.equal(call.options.method,'POST');
  assert.equal(call.options.referrerPolicy,'strict-origin');
  assert.equal(call.options.mode,'same-origin');
  assert.equal(call.options.credentials,'same-origin');
  assert.equal(call.options.redirect,'error');
  assert.equal(call.options.cache,'no-store');
  assert.equal(call.options.headers['X-MetodoBase-Browser'],'1');
  assert.equal(call.options.headers['Content-Type'],'application/json');
  assert.equal(call.options.headers.Accept,'application/json');
  assert.equal(Object.keys(call.options.headers).some(name=>['origin','referer'].includes(name.toLowerCase())),false);
  assert.equal(call.held,1,'Cookie-capable I/O must remain inside the shared Web Lock');
  assert.equal(typeof call.options.body,'string');
  assert.ok(call.body&&typeof call.body==='object');
  if(authenticated)assert.match(call.options.headers.Authorization,/^Bearer /);
  else assert.equal(call.options.headers.Authorization,undefined);
  if(csrf)assert.equal(call.options.headers['X-CSRF-Token'],'synthetic-csrf');
}
function checkPersistence(w){
  assert.ok(w.writes.every(value=>value.key==='mb_session_epoch'));
  assert.equal(w.maxHeld,1);
}
async function fixture(options={}){
  const w=world(options),t=w.tab();
  t.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
  await t.api.session.ready;
  return{w,t,api:t.api};
}
function accountRoutes(custom){return call=>call.path==='/api/auth/me'?reply(200,user):custom(call);}
async function test(name,run){
  try{await run();rows.push({case:name,passed:true});}
  catch(error){rows.push({case:name,passed:false,error_class:error.name,code:error.code||null,frames:error.stack?.split('\n').slice(1,5)});}
}
(async()=>{
  await test('Anonymous bootstrap preserves strict-origin with the exact unavailable-session401',async()=>{
    const e=await fixture({cookie:null});
    assert.equal(e.w.calls.length,1);assert.deepEqual(last(e.w,'/api/auth/refresh').body,{});
    checkPost(last(e.w,'/api/auth/refresh'));assert.equal(e.api.getToken(),'');checkPersistence(e.w);
  });
  await test('Legacy migration preserves the same locked transport without persisting its credential again',async()=>{
    const e=await fixture({cookie:null,legacy:'synthetic-legacy-refresh'});
    const call=last(e.w,'/api/auth/browser/migrate');checkPost(call);
    assert.deepEqual(call.body,{refresh_token:'synthetic-legacy-refresh'});
    for(const key of['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'])assert.equal(e.w.shared.has(key),false);
    checkPersistence(e.w);
  });
  for(const [name,method,url,payload]of[
    ['password login','primaryPassword','/api/auth/login',{email:'synthetic@example.invalid',password:'Synthetic password!'}],
    ['manual registration','registerPassword','/api/auth/registro',{email:'synthetic@example.invalid',nombre:'Synthetic',tipo:'gym',password:'Synthetic password!'}],
  ])await test(name+' keeps the real browser transport and commits only its acknowledged result',async()=>{
    const e=await fixture({cookie:null}),handle=e.api.mfa.capture();
    const result=await e.api.mfa[method](payload,handle);assert.equal(e.api.getToken(),'');
    checkPost(last(e.w,url));assert.deepEqual(last(e.w,url).body,payload);
    e.api.mfa.finishLogin(result,handle);assert.ok(e.api.getToken());checkPersistence(e.w);
  });
  await test('Invitation acceptance uses the same strict-origin cookie transport',async()=>{
    const e=await fixture({cookie:null});
    await e.api.team.accept('A'.repeat(43),'Synthetic password!');checkPost(last(e.w,'/api/auth/accept-invite'));
    assert.ok(e.api.getToken());checkPersistence(e.w);
  });
  await test('Google then mailbox then existing MFA use strict-origin without granting early access',async()=>{
    const e=await fixture({cookie:null}),handle=e.api.mfa.capture();
    e.t.hook(call=>{
      if(call.path==='/api/auth/google')return reply(202,{email_verification_required:true,challenge:'C'.repeat(43),expires_at:expiry(),masked_email:'s***@example.invalid',session_mode:'browser'});
      if(call.path==='/api/auth/google/verify-email')return reply(202,{mfa_required:true,challenge:'F'.repeat(43),expires_at:expiry(),methods:['totp','recovery_code'],session_mode:'browser'});
      if(call.path==='/api/auth/mfa/login/verify')return reply(200,signedIn());
    });
    const email=await e.api.mfa.primaryGoogle({credential:'synthetic-google-id-token',tipo:'gym'},handle);
    assert.equal(e.api.getToken(),'');assert.equal(email.email_verification_required,true);
    const factor=await e.api.mfa.loginGoogleEmailVerify({challenge:email.challenge,code:'123456'},handle);
    assert.equal(e.api.getToken(),'');assert.equal(factor.mfa_required,true);
    const result=await e.api.mfa.loginVerify({challenge:factor.challenge,code:'123456'},handle);
    assert.equal(e.api.getToken(),'');
    for(const url of['/api/auth/google','/api/auth/google/verify-email','/api/auth/mfa/login/verify'])checkPost(last(e.w,url));
    e.api.mfa.finishLogin(result,handle);assert.equal(e.api.getToken(),'synthetic-access-B');checkPersistence(e.w);
  });
  await test('Ordinary401 refresh retains strict-origin under the lock and does not change the epoch',async()=>{
    const e=await fixture(),epoch=e.w.shared.get('mb_session_epoch');let first=true;
    e.t.hook(call=>{if(call.path==='/api/auth/me'&&first){first=false;return reply(401,{detail:'Synthetic expired access'});}});
    await e.api.auth.me();const rotations=e.w.calls.filter(call=>call.path==='/api/auth/refresh');
    assert.equal(rotations.length,2);for(const call of rotations)checkPost(call);
    assert.equal(e.w.shared.get('mb_session_epoch'),epoch);checkPersistence(e.w);
  });
  await test('Authenticated security email POST keeps bearer, CSRF and strict-origin',async()=>{
    const e=await fixture();
    e.t.hook(accountRoutes(call=>call.path==='/api/account/security/email/request'?reply(200,{email_verified:true,delivery:'not_required'}):null));
    const {handle}=await e.api.accountSecurity.context();await e.api.accountSecurity.requestEmail(handle);
    checkPost(last(e.w,'/api/account/security/email/request'),{authenticated:true,csrf:true});checkPersistence(e.w);
  });
  await test('Password security POST keeps strict-origin and the explicit RAM revocation result',async()=>{
    const e=await fixture();
    e.t.hook(accountRoutes(call=>call.path==='/api/account/security/password'?reply(200,{code:'account_password_changed',reauthenticate:true,sessions_revoked:true}):null));
    const {handle}=await e.api.accountSecurity.context();
    const result=await e.api.accountSecurity.changePassword({reauthentication_token:'R'.repeat(43),new_password:'Synthetic changed password!',confirm_password:'Synthetic changed password!'},handle);
    checkPost(last(e.w,'/api/account/security/password'),{authenticated:true,csrf:true});
    assert.equal(result.state,'changed');assert.equal(result.server_confirmed,true);assert.equal(e.api.getToken(),'');checkPersistence(e.w);
  });
  await test('Authenticated Google email reauthentication stays distinct from public login with strict-origin',async()=>{
    const e=await fixture();
    e.t.hook(accountRoutes(call=>{
      if(call.path==='/api/auth/mfa/google-email/request')return reply(202,{email_verification_required:true,challenge:'C'.repeat(43),expires_at:expiry(),masked_email:'s***@example.invalid',resend_after_seconds:60});
      if(call.path==='/api/auth/mfa/google-email/verify'||call.path==='/api/auth/mfa/reauth')return reply(200,{reauthentication_token:'R'.repeat(43),expires_at:expiry()});
    }));
    const {handle}=await e.api.mfa.context();await e.api.mfa.reauth({password:'Synthetic current password!'},handle);
    const email=await e.api.mfa.googleEmailRequest({google_credential:'synthetic-google-id-token'},handle);
    await e.api.mfa.googleEmailVerify({challenge:email.challenge,code:'123456'},handle);
    for(const url of['/api/auth/mfa/reauth','/api/auth/mfa/google-email/request','/api/auth/mfa/google-email/verify'])checkPost(last(e.w,url),{authenticated:true});
    assert.ok(e.api.getToken());checkPersistence(e.w);
  });
  await test('Privacy request uses the same protected account POST policy',async()=>{
    const e=await fixture();
    e.t.hook(accountRoutes(call=>call.path==='/api/account/privacy/requests'?reply(200,{id:'a'.repeat(32),version:1,state:'blocked',reason:'policy_required',account_closed:false,erasure_complete:false,policy:null,items:[]}):null));
    const {handle}=await e.api.accountPrivacy.context();await e.api.accountPrivacy.create('11111111-1111-4111-8111-111111111111',handle);
    checkPost(last(e.w,'/api/account/privacy/requests'),{authenticated:true,csrf:true});checkPersistence(e.w);
  });
  const report={scope:'Actual Api exported methods with deterministic RAM storage, cookie, WebLock and server-response doubles. Checks fetch options and absence of forged Origin/Referer; real browser-generated headers, WebKit and backend admission require separate QA.',source_sha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),passed:rows.filter(row=>row.passed).length,total:rows.length,results:rows};
  process.stdout.write(JSON.stringify(report,null,2)+'\n');process.exitCode=report.passed===report.total?0:1;
})().catch(error=>{process.stdout.write(JSON.stringify({scope:'Origin transport fixture',passed:false,error_class:error.name}));process.exitCode=1;});
