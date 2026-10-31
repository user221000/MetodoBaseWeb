/* Real form handlers/controller/Api; native constraint success is an explicit DOM double. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),Module=require('node:module');
const {TextEncoder}=require('node:util');
const root=path.join(__dirname,'../..'),read=name=>fs.readFileSync(path.join(root,name),'utf8');
function declaredMinimum(template,id){
  const input=new RegExp('<input\\b[^>]*\\bid="'+id+'"[^>]*>','i').exec(read(template));
  assert.ok(input,'actual password input exists');assert.match(input[0],/\bminlength="15"/);
}
const flush=async()=>{for(let n=0;n<8;n++)await new Promise(setImmediate);};
const samples=[['12 BMP','x'.repeat(12),false],['14 BMP','x'.repeat(14),false],
  ['14 astral','\u{1F600}'.repeat(14),false],['15 BMP','x'.repeat(15),true],['15 astral','\u{1F600}'.repeat(15),true]];
class Node {
  constructor(){this.value='';this.hidden=false;this.disabled=false;this.textContent='';this.style={};this.events=new Map();this.button=null;this.validityCalls=0;}
  addEventListener(name,callback){this.events.set(name,callback);}
  setAttribute(name,value){this[name]=String(value);}
  removeAttribute(name){delete this[name];}
  async emit(name){return await this.events.get(name)?.({target:this,preventDefault(){}});}
  querySelector(selector){assert.equal(selector,'button');return this.button;}
  reportValidity(){this.validityCalls++;return true;} // Deliberately allow native minlength; the real Unicode guard must decide.
  focus(){this.focused=true;}
}
function dom(){
  const nodes=new Map(),events=new Map(),destinations=[];
  const get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
  const document={readyState:'loading',getElementById:get,querySelectorAll:()=>[],addEventListener(){}};
  const location={hash:'#token='+'A'.repeat(43),search:'',pathname:'/synthetic',replace:to=>destinations.push(to)};
  const sandbox={document,location,history:{replaceState(){}},URLSearchParams,TextEncoder,console,
    crypto:{randomUUID:require('node:crypto').randomUUID},Event:class{constructor(type){this.type=type;}},
    BroadcastChannel:class{postMessage(){}close(){}},localStorage:{values:new Map(),setItem(k,v){this.values.set(k,v);},getItem(k){return this.values.get(k);}}};
  sandbox.window=sandbox;sandbox.addEventListener=(name,callback)=>events.set(name,callback);
  sandbox.dispatchEvent=event=>events.get(event.type)?.(event);
  return{get,nodes,sandbox,context:vm.createContext(sandbox),destinations};
}
async function register(password){
  declaredMinimum('web/templates/registro.html','pwdField');
  const d=dom(),calls=[],form=d.get('registroForm');
  for(const [key,id] of Object.entries({password:'pwdField',confirm_password:'confirm-password',email:'email',nombre:'nombre',apellido:'apellido',tipo:'campoTipo'}))form[key]=d.get(id);
  form.password.value=form.confirm_password.value=password;form.email.value='synthetic@example.invalid';form.nombre.value='Synthetic';
  form.tipo.value='usuario';form.querySelectorAll=()=>[form.password,form.confirm_password,form.email,d.get('submitBtn')];
  for(const id of ['mfa-login-factor','mfa-login-email'])d.get(id).querySelectorAll=()=>[];
  d.sandbox.document.querySelector=()=>null;d.sandbox.setInterval=()=>1;d.sandbox.clearInterval=()=>{};
  d.sandbox.location.assign=to=>d.destinations.push(to);
  d.sandbox.Api={session:{ready:Promise.resolve()},mfa:{capture:()=>({}),check(){},finishLogin:()=>({}),
    context:async()=>({me:{tipo:'usuario'},handle:{}}),registerPassword:async value=>{calls.push({...value});return{tipo:'usuario'};}}};
  assert.match(read('web/templates/registro.html'),/MfaLogin\.mount\(\{formId:"registroForm",registration:true/,'actual registration uses the shared mount');
  vm.runInContext(read('web/static/js/mfa-login.js'),d.context,{filename:'mfa-login.js'});
  d.sandbox.MfaLogin.mount({formId:'registroForm',registration:true,readAudience:()=>form.tipo.value,googleClientId:''});
  await flush();
  await form.emit('submit');return{calls,feedback:d.get('errorMsg').textContent,destinations:d.destinations};
}
async function invite(password){
  declaredMinimum('web/templates/accept_invite.html','invite-password');
  const d=dom(),calls=[],form=d.get('invite-form');d.get('invite-password').value=d.get('invite-confirm').value=password;
  d.sandbox.Api={getToken:()=>'',session:{ready:Promise.resolve(),capture:()=>({}),check(){},accepted:()=>({})},
    team:{info:async()=>({status:'pending',email:'synthetic@example.invalid',gym_name:'Synthetic',can_accept:true,
      role:'viewer',membership_type:'professional',is_expired:false,expires_at:'2099-01-01T00:00:00Z'}),
      accept:async(token,value)=>{calls.push({token,password:value});return{success:true,session_mode:'browser',token:'synthetic-access',access_token:'synthetic-access'};}},
    auth:{me:async()=>({team_gym_id:'synthetic-owner',role:'viewer'})}};
  vm.runInContext(read('web/static/js/accept-invite.js'),d.context,{filename:'accept-invite.js'});await flush();
  assert.equal(form.hidden,false);await form.emit('submit');return{calls,feedback:d.get('invite-feedback').textContent,destinations:d.destinations};
}
async function recovery(password){
  declaredMinimum('web/templates/account_recovery.html','recovery-password');
  const d=dom(),calls=[],form=d.get('recovery-confirm');form.button=new Node();d.get('recovery-request').button=new Node();
  d.get('recovery-password').value=d.get('recovery-confirmation').value=password;
  d.sandbox.fetch=async(url,options)=>{calls.push({url,...JSON.parse(options.body)});return{ok:true,status:200,json:async()=>({message:'Synthetic password accepted'})};};
  vm.runInContext(read('web/static/js/account-recovery.js'),d.context,{filename:'account-recovery.js'});
  await form.emit('submit');assert.equal(form.validityCalls,1,'native validation was not the rejection oracle');
  return{calls,feedback:d.get('recovery-status').textContent,closed:form.hidden};
}
async function account(password){
  const d=dom(),calls=[];
  vm.runInContext(read('web/static/js/account-security37.js'),d.context,{filename:'account-security37.js'});
  const api={context:async()=>({handle:{}}),check(){},verify:async()=>{},
    status:async()=>({email_verified:false,email_verified_at:null,verification_lifetime_seconds:1800,password_change_reauthentication:'primary_and_current_factor_if_enabled'}),
    factorStatus:async()=>({enabled:false,pending:false,recovery_codes_remaining:0,totp_period_seconds:30,challenge_lifetime_seconds:300}),
    reauth:async()=>{calls.push({reauth:true});return{reauthentication_token:'A'.repeat(43),expires_at:'2099-01-01T00:00:00Z'};},
    changePassword:async value=>{calls.push({password:value.new_password,confirmation:value.confirm_password});return{server_confirmed:true};},checkClosed(){}};
  const controller=d.sandbox.AccountSecurity37.create({api});assert.equal(await controller.load(),true);
  const result=await controller.changePassword({new_password:password,confirm_password:password,confirm:true},{password:'synthetic current primary'});
  return{calls:calls.filter(row=>!row.reauth),reauth:calls.filter(row=>row.reauth).length,feedback:controller.view().message,result};
}
// Reuse the same authenticated RAM/cookie/WebLock fixture as the original account
// suite. Compile ONLY its declared fixture prefix, without its original test run.
function accountApiFixture(){
  const file=path.join(__dirname,'account_security37_transport.cjs'),source=fs.readFileSync(file,'utf8'),delimiter='const rows=[]';
  assert.equal(source.split(delimiter).length,2,'original fixture prefix boundary differs');
  const shared=new Module(file,module);shared.filename=file;shared.paths=module.paths;
  shared._compile(source.split(delimiter)[0]+'\nmodule.exports={fixture};',file);return shared.exports.fixture();
}
const cases=[],test=(name,run)=>cases.push({name,run});
for(const [form,run] of Object.entries({registration:register,invitation:invite,recovery,account_security:account})){
  for(const [label,password,accepted] of samples)test(form+' '+label+' preserves the Unicode point minimum before dispatch',async()=>{
    if(label==='14 astral'){assert.equal(password.length,28);assert.equal(Array.from(password).length,14);assert.ok(password.length>=15,'native UTF16 minlength can pass');}
    const result=await run(password);assert.equal(result.calls.length,accepted?1:0);
    if(accepted){
      assert.equal(result.calls[0].password||result.calls[0].new_password,password);
      if(form==='registration')assert.deepEqual(result.destinations,['/mi-plan']);
      if(form==='invitation')assert.deepEqual(result.destinations,['/equipo/inicio']);
      if(form==='recovery'){assert.equal(result.closed,true);assert.equal(result.feedback,'Synthetic password accepted');}
      if(form==='account_security'){assert.equal(result.reauth,1);assert.equal(result.result,true);}
    }
    else{assert.match(result.feedback,/15/);if(form==='account_security')assert.equal(result.reauth,0);}
  });
}
for(const [label,password,accepted] of samples)test('Real Api password '+label+' is checked before I/O without changing a valid15',async()=>{
  const e=await accountApiFixture(),before=e.w.calls.length;
  const value={reauthentication_token:'A'.repeat(43),new_password:password,confirm_password:password};
  if(!accepted){await assert.rejects(e.api.changePassword(value,e.handle),{code:'account_security_invalid_input'});assert.equal(e.w.calls.length,before);}
  else{const result=await e.api.changePassword(value,e.handle);const sent=e.w.calls.slice(before).filter(row=>row.path.endsWith('/password'));
    assert.equal(sent.length,1);assert.equal(sent[0].body.new_password,password);assert.equal(result.server_confirmed,true);}
});
(async()=>{const results=[];for(const row of cases){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name});}}
  console.log(JSON.stringify({scope:'Actual four form/controller paths and Api in offline VM/minimal DOM; reportValidity=true is a declared native constraint double, no HTTP/DB/Chrome claim.',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;
})().catch(error=>{console.error(error.name);process.exitCode=1;});
