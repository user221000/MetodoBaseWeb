/* Executes the exact first inline bootstrap before any network/style consumer. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const template=fs.readFileSync(path.resolve(__dirname,'../../web/templates/accept_client_link.html'),'utf8');
const bootstrap=template.match(/<script nonce="\{\{ request.state.csp_nonce \}\}">([\s\S]*?)<\/script>/)[1];
const token='S'.repeat(43),cases=[];
function test(name,fn){cases.push([name,fn]);}
function run(hash,search='',historyFailure=false){
  const events={},calls=[],location={pathname:'/auth/accept-client-link',hash,search};
  const box={location,addEventListener:(name,fn)=>{events[name]=fn;},
    history:{replaceState:(state,title,url)=>{calls.push({state,title,url});if(historyFailure)throw new Error('Synthetic history failure');location.hash='';location.search='';}},
    fetch:()=>{throw new Error('Bootstrap must not issue I/O');},
    localStorage:{getItem:()=>{throw new Error('No Storage');},setItem:()=>{throw new Error('No Storage');}},
    sessionStorage:{setItem:()=>{throw new Error('No Storage');}},console:{log:()=>{throw new Error('No logs');}},
  };box.window=box;vm.createContext(box);vm.runInContext(bootstrap,box);return {box,events,calls,location};
}
test('valid bearer is removed from URL before the first own asset and can only be taken once',()=>{
  const env=run('#token='+token),take=env.box.takeClientLinkInvitation;
  assert.equal(env.location.hash,'');assert.equal(env.location.search,'');assert.equal(env.calls[0].url,'/auth/accept-client-link');assert.equal(env.calls[0].state,null);
  assert.equal(env.box.token,undefined);assert.equal(env.box.takeClientLinkInvitation().token,token);assert.equal(env.box.takeClientLinkInvitation,undefined);
  assert.equal(take().token,null);
  assert(template.indexOf('<script nonce=')<template.indexOf('<link rel="stylesheet"'));assert(template.indexOf('<script nonce=')<template.indexOf('<script src='));
});
for(const [name,value] of [['missing',''],['too short','#token=S'],['digest as bearer','#token='+'a'.repeat(64)],['duplicate','#token='+token+'&token='+token],['extra property','#token='+token+'&gym=synthetic'],['encoded','#token='+('%53'.repeat(43))],['unicode','#token='+'ñ'.repeat(43)],['wrong key','#invitation='+token]]){
  test(name+' fragment is rejected without I/O or token persistence',()=>{
    const env=run(value),result=env.box.takeClientLinkInvitation();assert.equal(result.token,null);assert.equal(result.state,value?'invalid':'missing');assert.equal(env.location.hash,'');
  });
}
test('query bearer is rejected and cleaned without fallback',()=>{
  const env=run('#token='+token,'?token='+token);const result=env.box.takeClientLinkInvitation();
  assert.equal(result.token,null);assert.equal(result.state,'invalid');assert.equal(env.location.search,'');
});
test('failed URL cleanup discards the bearer and reports no usable invitation',()=>{
  const env=run('#token='+token,'',true);const result=env.box.takeClientLinkInvitation();assert.equal(result.token,null);assert.equal(result.state,'unavailable');
});
test('pagehide clears the token even if the consumer has not loaded',()=>{
  const env=run('#token='+token);env.events.pagehide();assert.equal(env.box.takeClientLinkInvitation().token,null);
});
test('session change clears the token before the resource consumer has loaded',()=>{
  const env=run('#token='+token);env.events['metodobase-session-changed']({detail:{code:'session_storage_error'}});
  assert.equal(env.box.takeClientLinkInvitation().token,null);
});
test('credential Storage event clears the token without reading Storage',()=>{
  const env=run('#token='+token);env.events.storage({key:'mb_token'});assert.equal(env.box.takeClientLinkInvitation().token,null);
});
test('login and registration links carry no token or return destination and cannot accept',()=>{
  const hrefs=[...template.matchAll(/href="([^"]+)"/g)].map(x=>x[1]);
  for(const expected of ['/login-usuario','/login-gym','/registro?tipo=usuario'])assert(hrefs.includes(expected));
  assert(hrefs.every(x=>!x.includes('token=')&&!x.includes('return_to')));
  assert(!bootstrap.includes('aceptar'));assert(!bootstrap.includes('fetch('));
});
(async()=>{
  const results=[];for(const [name,fn]of cases){try{await fn();results.push({case:name,passed:true});}catch(error){results.push({case:name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'Exact template bootstrap in offline VM, no API/browser claim',passed:results.filter(x=>x.passed).length,total:results.length,results},null,2));
  if(results.some(x=>!x.passed))process.exitCode=1;
})();
