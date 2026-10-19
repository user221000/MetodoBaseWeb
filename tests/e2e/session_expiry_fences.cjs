/* Additional offline expiry continuations; independent security driver stays unchanged. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../../web/static/js/api.js'),'utf8');
const tests=[];const test=(name,body)=>tests.push({name,body});
function fixture(){
  const values=new Map([['mb_token','synthetic-A']]),window=new EventTarget();window.location={href:''};
  let onLoginRead=()=>{},failedRead=false,fetches=0;
  const context={Event,window,Response,Blob,FormData,URL,setTimeout,clearTimeout,console,
    localStorage:{getItem:key=>{if(failedRead)throw new DOMException('synthetic','SecurityError');if(key==='mb_tipo')onLoginRead();return values.get(key)||null;},setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},
    fetch:async()=>{fetches++;return Response.json({}, {status:401});}};
  vm.createContext(context);vm.runInContext(source+'\nglobalThis.testApi=Api;',context);
  return{api:context.testApi,values,window,fetches:()=>fetches,onLoginRead:callback=>onLoginRead=callback,failRead:()=>failedRead=true};
}
test('A replacement triggered by login-type read is fenced before redirect',async()=>{
  const e=fixture();let once=true;e.onLoginRead(()=>{if(once){once=false;e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});}});
  await assert.rejects(e.api.auth.me(),error=>error.code==='session_changed');assert.equal(e.window.location.href,'');
  assert.equal(e.values.get('mb_token'),'synthetic-B');assert.equal(e.values.get('mb_refresh_token'),'synthetic-RB');assert.equal(e.fetches(),1);
});
test('A second explicit empty revision is not confused with the clear initiated by old expiry',async()=>{
  const e=fixture();let notifications=0;e.window.addEventListener('metodobase-session-changed',()=>{notifications++;e.api.clearTokens();});
  await assert.rejects(e.api.auth.me(),error=>error.code==='session_changed');assert.equal(e.window.location.href,'');assert.equal(notifications,1);assert.equal(e.values.size,0);
});
test('A listener Storage failure removes trust and prevents the old redirect',async()=>{
  const e=fixture();const reads=[];e.window.addEventListener('metodobase-session-changed',()=>{e.failRead();reads.push(e.api.auth.me().catch(error=>error));});
  await assert.rejects(e.api.auth.me(),error=>error.code==='session_storage_error');await Promise.all(reads);
  assert.equal(e.window.location.href,'');assert.equal(e.fetches(),1);
});
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({name:entry.name,passed:true});}catch(error){results.push({name:entry.name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'VM only; no app/Chrome/providers',passed:results.filter(r=>r.passed).length,total:results.length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
