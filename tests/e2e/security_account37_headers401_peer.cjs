/* QA-28 readable401 authority must not depend on receiving an error body. */
'use strict';
const fs=require('node:fs'),Module=require('node:module'),assert=require('node:assert/strict');
const shared=new Module(__filename,module);shared.filename=__filename;shared.paths=module.paths;
shared._compile(fs.readFileSync('tests/e2e/security_account37_boundaries_peer.cjs','utf8').split('\nconst tests=[],test=')[0]+'\nmodule.exports={fixture,response,passwordBody};',__filename);
const{fixture,response,passwordBody}=shared.exports;
const flush=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate);};
const tests=[],test=(name,run)=>tests.push({name,run});
const operations={context:{path:'/api/auth/me',run:e=>e.api.context()},verify:{path:'/api/auth/me',run:e=>e.api.verify(e.handle)},factorStatus:{path:'/api/auth/mfa/status',run:e=>e.api.factorStatus(e.handle)},status:{path:'/api/account/security',run:e=>e.api.status(e.handle)},email:{path:'/api/account/security/email/request',run:e=>e.api.requestEmail(e.handle)},password:{path:'/api/account/security/password',run:e=>e.api.changePassword(passwordBody(),e.handle)}};
for(const[name,operation]of Object.entries(operations))test(name+' retires exact access at known401 headers before the stalled JSON error body',async()=>{
 const e=await fixture();let release,headersDelivered=false,bodyRead=false;const blocked=new Promise(resolve=>{release=resolve;});
 e.control.hook=call=>{if(call.path!==operation.path)return null;headersDelivered=true;return{...response({},401),json:async()=>{bodyRead=true;await blocked;return{detail:{code:'account_security_identity_unavailable'}};}};};
 const before=e.world.calls.length,pending=Promise.allSettled([operation.run(e)]);await flush();
 const beforeBody={headers:headersDelivered,retired:e.tab.api.getToken()==='',body_read:bodyRead};
 release();await pending;
 assert.equal(beforeBody.headers,true);assert.equal(e.world.calls.length,before+1);assert.equal(beforeBody.retired,true,'Known401 authority was retained while its private error body stalled');
});
(async()=>{const rows=[];for(const entry of tests){try{await entry.run();rows.push({case:entry.name,passed:true});}catch(error){rows.push({case:entry.name,passed:false,error_class:error.name,code:typeof error.code==='string'?error.code:null,site:String(error.stack).split('\n').find(line=>line.trimStart().startsWith('at '))});}}process.stdout.write(JSON.stringify({scope:'Actual current Api in independent VM. Headers are delivered; error body is explicitly blocked, then drained. No native/backend/provider claim.',passed:rows.filter(row=>row.passed).length,total:rows.length,rows},null,2)+'\n');if(rows.some(row=>!row.passed))process.exitCode=1;})();
