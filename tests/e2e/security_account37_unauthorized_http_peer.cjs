/* Independent private IPC: actual HTTP401 after persisted SV revocation. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),readline=require('node:readline'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const lines=readline.createInterface({input:process.stdin}),pending=new Map();let sequence=0,phase='bootstrap';
lines.on('line',line=>{const value=JSON.parse(line),slot=pending.get(value.id);if(slot){pending.delete(value.id);value.ok?slot.resolve(value.data):slot.reject(Error('Private IPC failure'));}});
function rpc(value){return new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});process.stdout.write(JSON.stringify({type:'request',id,...value})+'\n');});}
async function run(){
 const boot=await rpc({command:'bootstrap'}),events=new Map(),storage=new Map(),calls=[];let lock=Promise.resolve(),armed=false,revoked=false,activeHTTP=0;
 const paths={status:'/api/account/security',email:'/api/account/security/email/request',password:'/api/account/security/password'},target=paths[boot.operation];assert.ok(target);
 const sandbox={Event,TextEncoder,Date,URL,URLSearchParams,FormData,File,Blob,AbortController,setTimeout,clearTimeout,crypto:crypto.webcrypto,
  location:{origin:boot.origin,pathname:'/cuenta/seguridad',href:boot.origin+'/cuenta/seguridad'},
  document:{readyState:'loading',addEventListener(){},querySelector:()=>({content:boot.csrf})},
  navigator:{locks:{request(name,options,work){assert.equal(name,'metodobase.browser-session.v1');const next=lock.then(()=>work({name}));lock=next.catch(()=>{});return next;}}},
  localStorage:{getItem:key=>storage.get(key)||null,setItem(key,value){assert.equal(key,'mb_session_epoch');storage.set(key,value);},removeItem:key=>storage.delete(key)},
  sessionStorage:{getItem:()=>null,removeItem(){},setItem(){throw Error('Session persistence forbidden');}},
  addEventListener(name,fn){if(!events.has(name))events.set(name,[]);events.get(name).push(fn);},dispatchEvent(event){for(const listener of events.get(event.type)||[])listener(event);return true;},
  fetch:async(url,options)=>{
   activeHTTP++;try{
   if(armed&&!revoked&&url===target){revoked=true;await rpc({command:'revoke-persisted-session'});}
   const headers={...options.headers};if(headers['X-MetodoBase-Browser']==='1')headers.Origin=boot.origin;
   const reply=await rpc({command:'http',url,options:{...options,headers}});calls.push({url,status:reply.status,armed});
   return new Response(reply.body,{status:reply.status,headers:reply.headers});
   }finally{activeHTTP--;}
  }};
 sandbox.window=sandbox;const context=vm.createContext(sandbox);
 vm.runInContext(fs.readFileSync('web/static/js/api.js','utf8')+'\nglobalThis.api=Api;',context);
 vm.runInContext(fs.readFileSync('web/static/js/account-security37.js','utf8'),context);
 const api=sandbox.api;await api.session.ready;phase='actual-MFA-login';const handle=api.mfa.capture();
 const primary=await api.mfa.primaryPassword({email:boot.email,password:boot.password},handle);assert.equal(primary.mfa_required,true);
 const pair=await api.mfa.loginVerify({challenge:primary.challenge,recovery_code:boot.login_recovery},handle);api.mfa.finishLogin(pair,handle);
 const controller=sandbox.AccountSecurity37.create({api:api.accountSecurity});sandbox.addEventListener('metodobase-session-changed',()=>controller.invalidate());
 phase='initial-actual-read';assert.equal(await controller.load(),true);assert.equal(controller.view().factor.enabled,true);assert.ok(api.getToken());
 phase='persisted-SV-401';armed=true;const before=calls.length;let returned;
 if(boot.operation==='status')returned=await controller.load();
 if(boot.operation==='email')returned=await controller.requestEmail();
 if(boot.operation==='password')returned=await controller.changePassword({new_password:boot.new_password,confirm_password:boot.new_password,confirm:true,method:'recovery_code',factor:boot.change_recovery},{password:boot.password});
 while(activeHTTP)await new Promise(setImmediate);
 const view=controller.view(),targetCalls=calls.slice(before).filter(call=>call.url===target);
 const checks={actual_target_401:targetCalls.length===1&&targetCalls[0].status===401,returned_false:returned===false,
  access_retired:api.getToken()==='',actor_context_disabled:controller.active===false,email_projection_removed:view.email===null,factor_projection_removed:view.factor===null,
  no_refresh_retry:calls.filter(call=>call.url==='/api/auth/refresh').length===1,
  only_epoch_persisted:[...storage.keys()].every(key=>key==='mb_session_epoch')};
 return{passed:Object.values(checks).every(Boolean),operation:boot.operation,real_MFA_cookie:true,persisted_SV_revoked:revoked,target_HTTP_status:targetCalls[0]?.status||null,checks};
}
run().then(result=>{process.stdout.write(JSON.stringify({type:'result',...result})+'\n');lines.close();if(!result.passed)process.exitCode=1;}).catch(error=>{process.stdout.write(JSON.stringify({type:'result',passed:false,phase,error_class:error.name,code:error.code||null})+'\n');lines.close();process.exitCode=1;});
