'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[2],'utf8');
const tests=[];const test=(name,body)=>tests.push({name,body});
function fixture(){
  const values=new Map([['mb_token','synthetic-A']]),window=new EventTarget();window.location={href:'/protected-synthetic'};
  let onType=()=>{},badWrite=false,fetches=0;
  const context={window,Event,Response,Blob,FormData,URL,setTimeout,clearTimeout,
    localStorage:{getItem(k){if(k==='mb_tipo')onType();return values.get(k)||null;},setItem(k,v){if(badWrite&&k==='mb_refresh_token')throw new DOMException('SYNTHETIC','QuotaExceededError');values.set(k,v);},removeItem:k=>values.delete(k)},
    fetch:async()=>{fetches++;return Response.json({}, {status:401});}};
  vm.createContext(context);vm.runInContext(source+'\nglobalThis.reviewApi=Api;',context);
  return{api:context.reviewApi,values,window,onType:fn=>onType=fn,badWrite:()=>badWrite=true,fetches:()=>fetches};
}
test('Second guard detects raw replacement during login URL read without writing or sending B',async()=>{
  const e=fixture();e.onType(()=>{e.values.set('mb_token','synthetic-B');e.values.set('mb_refresh_token','synthetic-RB');});
  await assert.rejects(e.api.auth.me(),x=>x.code==='session_changed');assert.equal(e.window.location.href,'/protected-synthetic');assert.equal(e.fetches(),1);assert.equal(e.values.get('mb_token'),'synthetic-B');assert.equal(e.values.get('mb_refresh_token'),'synthetic-RB');
});
test('Second guard distinguishes later explicit empty revision from the expired clear',async()=>{
  const e=fixture();e.onType(()=>e.api.clearTokens());
  await assert.rejects(e.api.auth.me(),x=>x.code==='session_changed');assert.equal(e.window.location.href,'/protected-synthetic');assert.equal(e.values.size,0);assert.equal(e.fetches(),1);
});
test('Second guard blocks partial failed replacement during login URL read without compensating writes',async()=>{
  const e=fixture();let oldFailure;e.onType(()=>{e.badWrite();try{e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});}catch(error){oldFailure=error;}});
  await assert.rejects(e.api.auth.me(),x=>x.code==='session_storage_error');assert.equal(oldFailure.code,'session_storage_error');assert.equal(e.window.location.href,'/protected-synthetic');assert.equal(e.fetches(),1);assert.equal(e.values.get('mb_token'),'synthetic-B');assert.equal(e.values.has('mb_refresh_token'),false);
});
test('First guard rejects B then explicit clear even when final pair is empty and trusted',async()=>{
  const e=fixture();let events=0;e.window.addEventListener('metodobase-session-changed',()=>{events++;e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});e.api.clearTokens();});
  await assert.rejects(e.api.auth.me(),x=>x.code==='session_changed');assert.equal(e.window.location.href,'/protected-synthetic');assert.equal(e.values.size,0);assert.equal(events,1);assert.equal(e.fetches(),1);
});
(async()=>{const results=[];for(const t of tests){try{await t.body();results.push({name:t.name,passed:true});}catch(error){results.push({name:t.name,passed:false,error:error.stack});}}console.log(JSON.stringify({total:results.length,passed:results.filter(r=>r.passed).length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
