/* Real login/API consumers with RAM cookie, GSI and DOM doubles; no provider login. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const harness=fs.readFileSync(path.join(__dirname,'browser_session31.cjs'),'utf8');
const boundary='const rows=[];async function test';
if(harness.split(boundary).length!==2)throw Error('Unexpected browser-session fixture boundary');
const scenarios=String.raw`
const path=require('node:path');
const loginSource=fs.readFileSync(process.env.GOOGLE_LOGIN_RECOVERY_SOURCE||path.join(__dirname,'../../web/static/js/mfa-login.js'),'utf8');
const partial=fs.readFileSync(path.join(__dirname,'../../web/templates/mfa_login_partial.html'),'utf8');
class Element {
  constructor(id){this.id=id;this.hidden=false;this.disabled=false;this.style={};this.value='';this.textContent='';this.listeners=new Map();this.controls=[];this.children=[];this.offsetWidth=320;}
  addEventListener(name,listener){this.listeners.set(name,listener);}
  async fire(name){return this.listeners.get(name)?.({target:this,currentTarget:this,preventDefault(){}});}
  querySelectorAll(){return this.controls;}
  replaceChildren(){this.children=[];}
  setAttribute(name,value){this[name]=value;}
  removeAttribute(name){delete this[name];}
  getAttribute(name){return Object.prototype.hasOwnProperty.call(this,name)?this[name]:null;}
  focus(){this.focused=true;}
}
const response=(status,body)=>({status,ok:status>=200&&status<300,headers:{get:()=>null},json:async()=>body});
const rejection=()=>response(409,{detail:{code:'google_link_required',message:'Synthetic existing-account conflict'}});
const pendingFactor=()=>response(202,{mfa_required:true,challenge:'c'.repeat(43),expires_at:'2099-10-19T18:00:00Z',methods:['totp','recovery_code'],session_mode:'browser'});
const pendingEmail=(changes={})=>response(202,{email_verification_required:true,challenge:'e'.repeat(43),expires_at:'2099-10-19T18:00:00Z',masked_email:'s***@example.invalid',session_mode:'browser',...changes});
const googleCalls=e=>e.w.calls.filter(call=>call.path==='/api/auth/google');
const emailCalls=e=>e.w.calls.filter(call=>call.path==='/api/auth/google/verify-email');
function accepted(e){e.w.jar.account='B';return response(200,{token:'access-B-9000',tipo:'gym',session_mode:'browser'});}
async function mounted(audience='gym',registration=false){
  const w=world({cookie:null}),t=w.tab();await t.api.session.ready;
  const ids=['loginForm','registroForm','btnGym','btnUsuario','campoTipo','mfa-login-title','mfa-login-email','mfa-login-email-code','mfa-login-email-target','mfa-login-email-submit','mfa-login-email-hint','mfa-login-email-feedback','mfa-login-factor','mfa-login-panel','mfa-login-status','googleBtnContainer','googleErrorMsg','mfa-login-google-help','submitBtn','errorMsg','mfa-login-code','mfa-login-recovery','mfa-login-cancel','mfa-login-method','mfa-login-destination','mfa-login-code-label','mfa-login-recovery-label','mfa-login-reopen','rememberMe'];
  const nodes=Object.fromEntries(ids.map(id=>[id,new Element(id)]));
  const form=registration?nodes.registroForm:nodes.loginForm;form.email=new Element('emailField');form.password=new Element('pwdField');
  form.confirm_password=new Element('confirm-password');form.nombre=new Element('nombre');form.apellido=new Element('apellido');
  form.nombre.value='Synthetic';form.apellido.value='Owner';nodes.campoTipo.value=audience;
  form.email.value='synthetic@example.invalid';form.password.value='synthetic-password';
  form.controls=[form.email,form.password,nodes.submitBtn];
  nodes['mfa-login-factor'].controls=[nodes['mfa-login-code'],nodes['mfa-login-recovery'],nodes['mfa-login-method']];nodes['mfa-login-email'].controls=[nodes['mfa-login-email-code']];
  nodes['mfa-login-panel'].hidden=true;nodes['mfa-login-factor'].hidden=true;nodes['mfa-login-google-help'].hidden=true;
  nodes.submitBtn.textContent='Iniciar sesión';nodes.rememberMe.checked=false;
  const scripts=[],renders=[],navigations=[];let callback,sdkConfig;
  t.sandbox.document={getElementById:id=>{assert.ok(nodes[id],'Known login control '+id);return nodes[id];},querySelector:()=>null,createElement:()=>new Element('script'),head:{appendChild:script=>scripts.push(script)}};
  t.sandbox.setInterval=()=>1;t.sandbox.clearInterval=()=>{};
  t.sandbox.location.assign=url=>navigations.push(url);t.sandbox.location.reload=()=>{};
  t.sandbox.google={accounts:{id:{initialize:options=>{sdkConfig=options;callback=options.callback;},renderButton:(_root,options)=>renders.push(options)}}};
  vm.runInContext(loginSource,t.context);
  const controller=t.sandbox.MfaLogin.mount({audience,registration,formId:registration?'registroForm':'loginForm',readAudience:()=>nodes.campoTipo.value,googleClientId:'synthetic-public-client',nonce:'synthetic-nonce'});
  await tick();assert.equal(scripts.length,1);scripts[0].onload();assert.equal(renders.length,1);
  return {w,t,nodes,form,controller,renders,navigations,sdkConfig,callback:payload=>callback(payload),click(){const rendered=renders.at(-1);rendered.click_listener();return rendered.state;}};
}
const rows=[];
async function test(name,run){try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name,message:error.message,stack_frames:error.stack?.split('\n').slice(1,7)});}}
(async()=>{
for(const registration of [false,true])await test('Basic Google '+(registration?'registration':'login')+' avoids optional Security Bundle eligibility and still requires the exact callback and email proof',async()=>{
  const audience=registration?'usuario':'gym',e=await mounted(audience,registration);
  assert.equal(e.sdkConfig.client_id,'synthetic-public-client');assert.equal(e.sdkConfig.ux_mode,'popup');assert.equal(e.sdkConfig.auto_select,false);
  assert.equal(Object.prototype.hasOwnProperty.call(e.sdkConfig,'essential_claims'),false);
  assert.equal(Object.prototype.hasOwnProperty.call(e.sdkConfig,'scope'),false);
  e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():null);
  const state=e.click();await e.callback({state:state+'-wrong',credential:'synthetic'});
  assert.equal(googleCalls(e).length,0);assert.equal(e.controller.phase,'google');
  await e.callback({state,credential:'synthetic'});
  assert.equal(googleCalls(e).length,1);assert.deepEqual(googleCalls(e)[0].body,{credential:'synthetic',tipo:audience});
  assert.equal(e.controller.phase,'email');assert.equal(emailCalls(e).length,0);
  assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);assert.equal(e.navigations.length,0);
});
for(const audience of ['gym','usuario'])for(const factor of [false,true])await test('Google '+audience+' portal follows the persisted opposite account after email'+(factor?' and personal MFA':''),async()=>{
  const e=await mounted(audience),kind=audience==='gym'?'usuario':'gym',role=kind==='gym'?'owner':'viewer';
  const finish=()=>{e.w.jar.account='B';return response(200,{token:'access-B-9000',tipo:kind,role,session_mode:'browser'});};
  e.t.hook(call=>{
    if(call.path==='/api/auth/google')return pendingEmail();
    if(call.path==='/api/auth/google/verify-email')return factor?pendingFactor():finish();
    if(call.path==='/api/auth/mfa/login/verify')return finish();
    if(call.path==='/api/auth/me')return response(200,{id:'B',tipo:kind,role,session_version:1,team_gym_id:null});
  });
  const state=e.click();await e.callback({state,credential:'synthetic-provider'});
  assert.equal(e.controller.phase,'email');assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);
  e.nodes['mfa-login-email-code'].value='123456';await e.nodes['mfa-login-email'].fire('submit');
  if(factor){
    assert.equal(e.controller.phase,'factor');assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);assert.deepEqual(e.navigations,[]);
    e.nodes['mfa-login-code'].value='123456';await e.nodes['mfa-login-factor'].fire('submit');
  }
  assert.equal(e.controller.phase,'confirmed');assert.ok(e.t.api.getToken().startsWith('access-B-'));
  assert.deepEqual(e.navigations,[kind==='gym'?'/dashboard':'/mi-plan']);
  assert.equal(googleCalls(e)[0].body.tipo,audience,'the UI never changes the persisted account type');
  assert.equal(emailCalls(e).length,1);const before=e.w.calls.length;
  await e.callback({state,credential:'synthetic-late'});assert.equal(e.w.calls.length,before);
});
for(const audience of ['gym','usuario'])await test('Discarding Google does not weaken the password portal audience '+audience,async()=>{
  const e=await mounted(audience),kind=audience==='gym'?'usuario':'gym';
  e.t.hook(call=>{
    if(call.path==='/api/auth/google')return pendingEmail();
    if(call.path==='/api/auth/login'){e.w.jar.account='B';return response(200,{token:'access-B-9000',tipo:kind,primaryMethod:'google',session_mode:'browser'});}
  });
  const state=e.click();await e.callback({state,credential:'synthetic-provider'});e.controller.cancel();
  e.form.password.value='synthetic-password';await e.form.fire('submit');
  assert.equal(e.t.api.getToken(),'');assert.deepEqual(e.navigations,[]);
  assert.equal(e.w.calls.filter(call=>call.path==='/api/auth/login').length,1);
});
await test('A verified Google code cannot invent an unsupported account portal',async()=>{
  const e=await mounted('usuario');
  e.t.hook(call=>{
    if(call.path==='/api/auth/google')return pendingEmail();
    if(call.path==='/api/auth/google/verify-email'){e.w.jar.account='B';return response(200,{token:'access-B-9000',tipo:'unsupported',session_mode:'browser'});}
  });
  const state=e.click();await e.callback({state,credential:'synthetic-provider'});
  e.nodes['mfa-login-email-code'].value='123456';await e.nodes['mfa-login-email'].fire('submit');
  assert.equal(e.t.api.getToken(),'');assert.deepEqual(e.navigations,[]);
});
await test('Retrying the persisted Google destination never repeats an already consumed email proof',async()=>{
  const e=await mounted('usuario');let destinations=0;
  e.t.hook(call=>{
    if(call.path==='/api/auth/google')return pendingEmail();
    if(call.path==='/api/auth/google/verify-email'){e.w.jar.account='B';return response(200,{token:'access-B-9000',tipo:'gym',session_mode:'browser'});}
    if(call.path==='/api/auth/me')return ++destinations===1?response(503,{detail:{code:'synthetic_destination_unavailable'}}):response(200,{id:'B',tipo:'gym',role:'owner',session_version:1,team_gym_id:null});
  });
  const state=e.click();await e.callback({state,credential:'synthetic-provider'});
  e.nodes['mfa-login-email-code'].value='123456';await e.nodes['mfa-login-email'].fire('submit');
  assert.equal(e.controller.phase,'destination_error');assert.ok(e.t.api.getToken().startsWith('access-B-'));assert.deepEqual(e.navigations,[]);
  assert.equal(await e.controller.retryDestination(),true);assert.equal(e.controller.phase,'confirmed');assert.deepEqual(e.navigations,['/dashboard']);
  assert.equal(googleCalls(e).length,1);assert.equal(emailCalls(e).length,1);
});
await test('Recovery actions remain outside the hidden factor panel with fixed local destinations',()=>{
  const help=partial.indexOf('id="mfa-login-google-help"');assert.ok(help>partial.indexOf('</section>'));
  assert.match(partial.slice(help),/href="\/auth\/reset-password"/);assert.match(partial.slice(help),/href="\/cuenta\/google"/);
  assert.match(partial.slice(help,partial.indexOf('>',help)),/\bhidden\b/);
});
for(const audience of ['gym','usuario'])await test('Existing '+audience+' Google account returns to local access without a factor or session',async()=>{
  const e=await mounted(audience);e.t.hook(call=>call.path==='/api/auth/google'?rejection():null);
  const state=e.click();await e.callback({state,credential:'synthetic-not-a-provider-token'});
  assert.equal(e.controller.phase,'primary');assert.equal(e.nodes.loginForm.hidden,false);assert.equal(e.nodes.submitBtn.disabled,false);
  assert.equal(e.nodes['mfa-login-panel'].hidden,true);assert.equal(e.nodes['mfa-login-factor'].hidden,true);assert.equal(e.nodes['mfa-login-google-help'].hidden,false);
  assert.equal(e.nodes.loginForm.password.value,'');assert.equal(e.nodes.errorMsg.style.display,'block');assert.match(e.nodes.errorMsg.textContent,/desactivado/);
  assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);assert.equal(e.navigations.length,0);
  assert.ok(e.w.writes.every(write=>write.key==='mb_session_epoch'));assert.equal(googleCalls(e).length,1);
  const before=e.w.calls.length;assert.equal(await e.controller.verify('123456'),false);assert.equal(e.w.calls.length,before);
});
await test('Unrequested and mismatched provider callbacks never dispatch authentication',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?rejection():null);
  await e.callback({state:e.renders.at(-1).state,credential:'synthetic'});assert.equal(googleCalls(e).length,0);
  const state=e.click();await e.callback({state:state+'-wrong',credential:'synthetic'});assert.equal(googleCalls(e).length,0);assert.equal(e.controller.phase,'google');
  await e.callback({state,credential:'synthetic'});assert.equal(googleCalls(e).length,1);assert.equal(e.controller.phase,'primary');
});
await test('A discarded callback cannot repeat the conflict or consume a new Google attempt',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?rejection():null);
  const old=e.click();await e.callback({state:old,credential:'synthetic'});const next=e.click();assert.notEqual(old,next);
  await e.callback({state:old,credential:'synthetic-late'});assert.equal(googleCalls(e).length,1);assert.equal(e.controller.phase,'google');
  await e.callback({state:next,credential:'synthetic-current'});assert.equal(googleCalls(e).length,2);assert.equal(e.controller.phase,'primary');
});
await test('Local password access works after the conflict and removes recovery help',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?rejection():null);
  const state=e.click();await e.callback({state,credential:'synthetic'});e.nodes.loginForm.password.value='synthetic-password';
  await e.nodes.loginForm.fire('submit');assert.equal(e.controller.phase,'confirmed');assert.equal(e.nodes['mfa-login-google-help'].hidden,true);
  assert.ok(e.t.api.getToken().startsWith('access-B-'));assert.deepEqual(e.navigations,['/dashboard']);
  const before=e.w.calls.length;await e.callback({state,credential:'synthetic-late'});assert.equal(e.w.calls.length,before);
});
await test('Google email confirmation still requires an enabled factor before any session is committed',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():call.path==='/api/auth/google/verify-email'?pendingFactor():null);
  const state=e.click();await e.callback({state,credential:'synthetic'});assert.equal(e.controller.phase,'email');
  e.nodes['mfa-login-email-code'].value='123456';await e.nodes['mfa-login-email'].fire('submit');
  assert.equal(e.controller.phase,'factor');assert.equal(e.nodes.loginForm.hidden,true);assert.equal(e.nodes['mfa-login-panel'].hidden,false);assert.equal(e.nodes['mfa-login-factor'].hidden,false);assert.equal(e.nodes['mfa-login-google-help'].hidden,true);
  assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);assert.equal(e.navigations.length,0);
  e.nodes['mfa-login-code'].value='123456';await e.nodes['mfa-login-factor'].fire('submit');assert.equal(e.controller.phase,'confirmed');assert.ok(e.t.api.getToken().startsWith('access-B-'));
  assert.equal(e.w.calls.filter(call=>call.path==='/api/auth/mfa/login/verify').length,1);
});
await test('Google email challenge reveals only the masked destination and never commits a session',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():null);
  const state=e.click();await e.callback({state,credential:'synthetic'});
  assert.equal(e.controller.phase,'email');assert.equal(e.nodes['mfa-login-email'].hidden,false);assert.equal(e.nodes['mfa-login-factor'].hidden,true);assert.equal(e.form.hidden,true);
  assert.equal(e.nodes['mfa-login-title'].textContent,'Confirma tu correo');assert.equal(e.nodes['mfa-login-email-target'].textContent,'Enviado a s***@example.invalid');
  assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);assert.equal(e.navigations.length,0);
  assert.ok(e.w.writes.every(write=>write.key==='mb_session_epoch'));
});
await test('Correct email proof commits only the acknowledgement from the verification endpoint',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():call.path==='/api/auth/google/verify-email'?accepted(e):null);
  const state=e.click();await e.callback({state,credential:'synthetic'});e.nodes['mfa-login-email-code'].value='123456';await e.nodes['mfa-login-email'].fire('submit');
  assert.equal(e.controller.phase,'confirmed');assert.equal(e.t.api.getToken(),'access-B-9000');assert.deepEqual(e.navigations,['/dashboard']);
  assert.equal(emailCalls(e).length,1);assert.deepEqual(emailCalls(e)[0].body,{challenge:'e'.repeat(43),code:'123456'});
  assert.equal(e.nodes['mfa-login-email-code'].value,'');assert.equal(e.nodes['mfa-login-email-target'].textContent,'');
  const before=e.w.calls.length;assert.equal(await e.controller.verifyEmail('123456'),false);assert.equal(e.w.calls.length,before);
});
await test('Wrong email proof stays in its own form without invoking or bypassing MFA',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():call.path==='/api/auth/google/verify-email'?response(400,{detail:{code:'google_email_code_invalid'}}):null);
  const state=e.click();await e.callback({state,credential:'synthetic'});
  assert.equal(await e.controller.verifyEmail('１２３４５６'),false);assert.equal(emailCalls(e).length,0);
  assert.equal(await e.controller.verifyEmail('123456'),false);assert.equal(emailCalls(e).length,1);assert.equal(e.controller.phase,'email');
  assert.equal(e.nodes['mfa-login-factor'].hidden,true);assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,null);
});
await test('An expired email challenge is discarded locally before verification traffic',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail({expires_at:'2020-01-01T00:00:00Z'}):null);
  const state=e.click();await e.callback({state,credential:'synthetic'});assert.equal(await e.controller.verifyEmail('123456'),false);
  assert.equal(e.controller.phase,'primary');assert.equal(emailCalls(e).length,0);assert.equal(e.t.api.getToken(),'');
});
await test('Uncertain email verification discards the proof instead of retrying it',async()=>{
  const e=await mounted();e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():call.path==='/api/auth/google/verify-email'?response(503,{detail:{code:'google_email_unconfirmed'}}):null);
  const state=e.click();await e.callback({state,credential:'synthetic'});assert.equal(await e.controller.verifyEmail('123456'),false);assert.equal(e.controller.phase,'primary');
  assert.equal(await e.controller.verifyEmail('123456'),false);assert.equal(emailCalls(e).length,1);assert.equal(e.t.api.getToken(),'');assert.equal(e.nodes['mfa-login-email-target'].textContent,'');
});
for(const invalid of ['token-before-email','mfa-before-email','extra-secret'])await test('Google start rejects '+invalid+' rather than accepting an incomplete protocol',async()=>{
  const e=await mounted();e.t.hook(call=>call.path!=='/api/auth/google'?null:invalid==='token-before-email'?response(200,{token:'access-B-9000',tipo:'gym',session_mode:'browser'}):invalid==='mfa-before-email'?pendingFactor():pendingEmail({code:'123456'}));
  const state=e.click();await e.callback({state,credential:'synthetic'});assert.equal(e.controller.phase,'primary');assert.equal(e.t.api.getToken(),'');assert.equal(e.navigations.length,0);
});
await test('Cancel during retained email verification cannot publish its late session acknowledgement',async()=>{
  const e=await mounted(),gate=deferred(),started=deferred();e.t.hook(call=>{
    if(call.path==='/api/auth/google')return pendingEmail();if(call.path==='/api/auth/google/verify-email')return {status:200,ok:true,headers:{get:()=>null},json:async()=>{started.resolve();await gate.promise;return {token:'access-B-9000',tipo:'gym',session_mode:'browser'};}};
  });
  const state=e.click();await e.callback({state,credential:'synthetic'});const verifying=e.controller.verifyEmail('123456');await started.promise;e.controller.cancel();gate.resolve();await verifying;
  assert.equal(e.controller.phase,'primary');assert.equal(e.t.api.getToken(),'');assert.equal(e.navigations.length,0);
});
await test('The view DTO never includes either email or factor challenge secrets',async()=>{
  const w=world({cookie:null}),t=w.tab();await t.api.session.ready;t.hook(call=>call.path==='/api/auth/google'?pendingEmail():call.path==='/api/auth/google/verify-email'?pendingFactor():null);
  vm.runInContext(loginSource,t.context);const views=[],controller=t.sandbox.MfaLogin.create({ready:t.api.session.ready,onView:view=>views.push(view)});
  const ticket=controller.beginGoogle();await controller.completeGoogle({credential:'synthetic'},ticket);await controller.verifyEmail('123456');
  assert.equal(controller.phase,'factor');for(const view of views){assert.equal('challenge' in view,false);assert.equal('code' in view&&view.code==='123456',false);assert.equal('credential' in view,false);}
  const publicView=JSON.stringify(views);assert.ok(!publicView.includes('e'.repeat(43))&&!publicView.includes('c'.repeat(43))&&!publicView.includes('123456'));
});
await test('Registration captures its audience at Google click and blocks concurrent password registration',async()=>{
  const e=await mounted('usuario',true);e.t.hook(call=>call.path==='/api/auth/google'?pendingEmail():call.path==='/api/auth/google/verify-email'?accepted(e):null);
  const state=e.click();assert.equal(e.nodes.btnGym.disabled,true);assert.equal(e.nodes.btnUsuario.disabled,true);e.nodes.campoTipo.value='gym';await e.callback({state,credential:'synthetic'});
  assert.equal(googleCalls(e)[0].body.tipo,'usuario');e.form.password.value=e.form.confirm_password.value='Synthetic registration password 42!';await e.form.fire('submit');assert.equal(e.w.calls.filter(call=>call.path==='/api/auth/registro').length,0);
  await e.controller.verifyEmail('123456');assert.equal(e.controller.phase,'confirmed');assert.deepEqual(e.navigations,['/configuracion']);
});
await test('Reentrant invalidation during an uncertain email result cannot restore a primary context',async()=>{
  const w=world({cookie:null}),t=w.tab();await t.api.session.ready;let armed=false;t.hook(call=>{if(call.path==='/api/auth/google')return pendingEmail();if(call.path==='/api/auth/google/verify-email'){armed=true;return response(503,{detail:{code:'google_email_unconfirmed'}});}});
  vm.runInContext(loginSource,t.context);const controller=t.sandbox.MfaLogin.create({ready:t.api.session.ready,onClear(){if(armed){armed=false;t.dispatch({type:'pagehide'});}}});
  const ticket=controller.beginGoogle();await controller.completeGoogle({credential:'synthetic'},ticket);
  assert.equal(await controller.verifyEmail('123456'),false);assert.equal(controller.phase,'invalidated');assert.equal(controller.active,false);assert.equal(t.api.getToken(),'');
  assert.equal(w.calls.filter(call=>call.path==='/api/auth/google/verify-email').length,1);
});
await test('Explicit cancel discards the Google popup and its late callback',async()=>{
  const e=await mounted();const state=e.click();await e.nodes['mfa-login-cancel'].fire('click');
  await e.callback({state,credential:'synthetic-late'});assert.equal(e.controller.phase,'primary');assert.equal(googleCalls(e).length,0);assert.equal(e.nodes['mfa-login-google-help'].hidden,true);assert.equal(e.t.api.getToken(),'');
});
await test('Leaving the page invalidates the pending Google callback',async()=>{
  const e=await mounted();const state=e.click();e.t.dispatch({type:'pagehide'});
  await e.callback({state,credential:'synthetic-late'});assert.equal(e.controller.phase,'invalidated');assert.equal(googleCalls(e).length,0);assert.equal(e.t.api.getToken(),'');
});
await test('Another tab selecting an account cannot be replaced by the old Google popup',async()=>{
  const e=await mounted(),other=e.w.tab();await other.api.session.ready;const state=e.click();
  await other.api.auth.registro({account:'C'});await tick();await e.callback({state,credential:'synthetic-late'});
  assert.equal(e.controller.phase,'invalidated');assert.equal(googleCalls(e).length,0);assert.equal(e.t.api.getToken(),'');assert.equal(e.w.jar.account,'C');assert.ok(other.api.getToken().startsWith('access-C-'));
});
await test('Reentrant invalidation while discarding proof cannot revive the old context',async()=>{
  const w=world({cookie:null}),t=w.tab();await t.api.session.ready;t.hook(call=>call.path==='/api/auth/google'?rejection():null);
  vm.runInContext(loginSource,t.context);let armed=true;
  const controller=t.sandbox.MfaLogin.create({audience:'gym',ready:t.api.session.ready,onClear(){if(armed){armed=false;t.dispatch({type:'pagehide'});}}});
  const ticket=controller.beginGoogle();assert.equal(await controller.completeGoogle({credential:'synthetic'},ticket),false);
  assert.equal(controller.phase,'invalidated');assert.equal(controller.active,false);assert.equal(t.api.getToken(),'');
  const before=w.calls.length;assert.equal(await controller.primary('password',{}),false);assert.equal(w.calls.length,before);
});
const report={scope:'Actual mfa-login.js and api.js with deterministic DOM/GSI/WebLock/HttpOnly-cookie doubles; no Google provider or real user',passed:rows.filter(row=>row.passed).length,total:rows.length,results:rows};
console.log(JSON.stringify(report,null,2));if(report.passed!==report.total)process.exitCode=1;
})();
`;
const candidate=new Module(__filename,module);candidate.filename=__filename;candidate.paths=module.paths;
candidate._compile(harness.slice(0,harness.indexOf(boundary))+scenarios,__filename);
