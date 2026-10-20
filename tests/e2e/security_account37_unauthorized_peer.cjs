/* Independent account37 actor-retirement canaries; actual Api/controller, no author harness. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),Module=require('node:module'),assert=require('node:assert/strict'),cp=require('node:child_process');
const original=cp.execFileSync('git',['show','6ee27e3c:tests/e2e/security_browser31_ui_peer.cjs'],{encoding:'utf8'});
const prefix=original.split('const tests=[],test=')[0];
assert.ok(prefix.includes('function environment(')&&!prefix.includes('test(\''));
const shared=new Module(__filename,module);shared.filename=__filename;shared.paths=module.paths;shared._compile(prefix+'\nmodule.exports={environment,response};',__filename);
const{environment,response}=shared.exports;
const controller=vm.runInNewContext(fs.readFileSync('web/static/js/account-security37.js','utf8')+'\nAccountSecurity37;',{TextEncoder,Date});
const input=()=>({new_password:'Synthetic independent password 37!',confirm_password:'Synthetic independent password 37!',confirm:true,method:'totp',factor:'123456'});
const passwordBody=()=>({new_password:'Synthetic independent password 37!',confirm_password:'Synthetic independent password 37!',reauthentication_token:'A'.repeat(43)});
async function mounted(){
 const world=environment(),tab=world.tab();let failure=null;
 tab.hook(call=>{if(failure&&call.path===failure.path)return response({detail:{code:'account_security_identity_unavailable',message:'Synthetic persisted identity unavailable'}},failure.status);
  if(call.path==='/api/account/security')return response({email_verified:false,email_verified_at:null,verification_lifetime_seconds:1800,password_change_reauthentication:'primary_and_current_factor_if_enabled'});
  if(call.path==='/api/auth/mfa/status')return response({enabled:false,pending:false,recovery_codes_remaining:0,totp_period_seconds:30,challenge_lifetime_seconds:300});
  if(call.path==='/api/auth/mfa/reauth')return response({reauthentication_token:'A'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString()});
  return null;
 });
 await tab.api.session.ready;const{handle}=await tab.api.accountSecurity.context();
 const ui=controller.create({api:tab.api.accountSecurity});tab.sandbox.addEventListener('metodobase-session-changed',()=>ui.invalidate());assert.equal(await ui.load(),true);
 return{world,tab,handle,ui,deny(path,status){failure={path,status};}};
}
const operations={status:{path:'/api/account/security',raw:e=>e.tab.api.accountSecurity.status(e.handle),ui:e=>e.ui.load()},email:{path:'/api/account/security/email/request',raw:e=>e.tab.api.accountSecurity.requestEmail(e.handle),ui:e=>e.ui.requestEmail()},password:{path:'/api/account/security/password',raw:e=>e.tab.api.accountSecurity.changePassword(passwordBody(),e.handle),ui:e=>e.ui.changePassword(input(),{password:'Synthetic primary password'})}};
const tests=[],test=(name,run)=>tests.push({name,run});
for(const[name,operation]of Object.entries(operations)){
 test(name+' API persisted401 retires RAM access without any refresh or replay',async()=>{const e=await mounted(),before=e.world.calls.length;e.deny(operation.path,401);await assert.rejects(operation.raw(e),error=>error.status===401||error.code==='session_changed');assert.equal(e.world.calls.length,before+1);assert.equal(e.tab.api.getToken(),'');assert.throws(()=>e.tab.api.accountSecurity.check(e.handle),{code:'session_changed'});});
 test(name+' controller persisted401 removes actor projections and disables its old context',async()=>{const e=await mounted(),before=e.world.calls.length;e.deny(operation.path,401);assert.equal(await operation.ui(e),false);assert.equal(e.world.calls.length,before+(name==='password'?2:name==='status'?2:1));assert.equal(e.tab.api.getToken(),'');assert.equal(e.ui.view().email,null);assert.equal(e.ui.view().factor,null);assert.equal(e.ui.active,false);});
 for(const status of[403,422])test(name+' confirmed'+status+' preserves the access without a server revocation claim',async()=>{const e=await mounted(),before=e.world.calls.length,access=e.tab.api.getToken();e.deny(operation.path,status);assert.equal(await operation.ui(e),false);assert.equal(e.tab.api.getToken(),access);assert.equal(e.ui.active,true);assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/refresh').length,1);assert.equal(e.world.calls.length,before+(name==='password'?2:name==='status'?2:1));});
}
(async()=>{const rows=[];for(const entry of tests){try{await entry.run();rows.push({case:entry.name,passed:true});}catch(error){rows.push({case:entry.name,passed:false,error_class:error.name,code:typeof error.code==='string'?error.code:null,site:String(error.stack).split('\n').find(line=>line.trimStart().startsWith('at '))});}}process.stdout.write(JSON.stringify({scope:'Actual current Api/controller in independent VM fixture. Persisted401 is a typed double here; real HTTP bridge is separate.',passed:rows.filter(row=>row.passed).length,total:rows.length,rows},null,2)+'\n');if(rows.some(row=>!row.passed))process.exitCode=1;})();
