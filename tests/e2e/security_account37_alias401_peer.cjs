/* QA-28 own-account aliases: authority reads also retire a persisted401. */
'use strict';
const fs=require('node:fs'),Module=require('node:module'),assert=require('node:assert/strict');
const shared=new Module(__filename,module);shared.filename=__filename;shared.paths=module.paths;
shared._compile(fs.readFileSync('tests/e2e/security_account37_boundaries_peer.cjs','utf8').split('\nconst tests=[],test=')[0]+'\nmodule.exports={fixture,response,controller};',__filename);
const{fixture,response,controller}=shared.exports;
const aliases={context:{path:'/api/auth/me',raw:e=>e.api.context()},factorStatus:{path:'/api/auth/mfa/status',raw:e=>e.api.factorStatus(e.handle)},verify:{path:'/api/auth/me',raw:e=>e.api.verify(e.handle)}};
const tests=[],test=(name,run)=>tests.push({name,run});
for(const[name,alias]of Object.entries(aliases)){
 test(name+' API401 retires the exact own-account authority without automatic refresh',async()=>{
  const e=await fixture(),before=e.world.calls.length;e.control.hook=call=>call.path===alias.path?response({detail:{code:'account_security_identity_unavailable'}},401):null;
  await assert.rejects(alias.raw(e),error=>error.status===401||error.code==='session_changed');assert.equal(e.world.calls.length,before+1);assert.equal(e.tab.api.getToken(),'');assert.throws(()=>e.api.check(e.handle),{code:'session_changed'});
 });
 test(name+' controller401 disables the old account view and removes its projections',async()=>{
  const e=await fixture();let ui=e.ui;
  if(name==='context'){ui=controller.create({api:e.api});e.tab.sandbox.addEventListener('metodobase-session-changed',()=>ui.invalidate());}
  e.control.hook=call=>call.path===alias.path?response({detail:{code:'account_security_identity_unavailable'}},401):null;
  assert.equal(await ui.load(),false);assert.equal(e.tab.api.getToken(),'');assert.equal(ui.active,false);assert.equal(ui.view().email,null);assert.equal(ui.view().factor,null);assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/refresh').length,1);
 });
}
(async()=>{const rows=[];for(const entry of tests){try{await entry.run();rows.push({case:entry.name,passed:true});}catch(error){rows.push({case:entry.name,passed:false,error_class:error.name,code:typeof error.code==='string'?error.code:null,site:String(error.stack).split('\n').find(line=>line.trimStart().startsWith('at '))});}}process.stdout.write(JSON.stringify({scope:'Actual Api/controller, independent VM aliases; typed transport401, not an additional real HTTP claim.',passed:rows.filter(row=>row.passed).length,total:rows.length,rows},null,2)+'\n');if(rows.some(row=>!row.passed))process.exitCode=1;})();
