/* Native EventTarget VM; no browser, providers, app imports or token output. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.env.SESSION_REVISION_API_SOURCE || path.resolve(__dirname,'../../web/static/js/api.js'),'utf8');
const tests=[];const test=(name,body)=>tests.push({name,body});
function environment(options={}){
  const values=new Map([['mb_token','synthetic-A'],['mb_refresh_token','synthetic-RA']]);
  const target=new EventTarget();let failRead=false,failWrite=false,events=0;
  const visible={textContent:'Private prior-account row'};
  target.addEventListener('metodobase-session-changed',event=>{assert.equal(event.detail,undefined);events++;visible.textContent='';});
  const context={window:target,Event,EventTarget,Response,Blob,FormData,URL,setTimeout,clearTimeout,console,
    localStorage:{getItem:key=>{if(failRead)throw new DOMException('synthetic','SecurityError');return values.get(key)||null;},
      setItem:(key,value)=>{if(failWrite && key==='mb_refresh_token')throw new DOMException('synthetic','QuotaExceededError');values.set(key,value);},
      removeItem:key=>{if(failWrite && key==='mb_refresh_token')throw new DOMException('synthetic','SecurityError');values.delete(key);}},
    fetch:options.fetch||(async()=>Response.json({success:true}))};
  vm.createContext(context);vm.runInContext(source+'\nglobalThis.testApi=Api;',context);
  return{api:context.testApi,values,target,visible,events:()=>events,readFailure:()=>failRead=true,writeFailure:()=>failWrite=true};
}
test('saveTokens B clears already visible data synchronously without await or interaction',()=>{
  const e=environment();e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});
  assert.equal(e.visible.textContent,'');assert.equal(e.events(),1);assert.equal(e.values.get('mb_refresh_token'),'synthetic-RB');
});
test('clearTokens clears visible data after the complete empty pair',()=>{
  const e=environment();let sawComplete=false;e.target.addEventListener('metodobase-session-changed',()=>{sawComplete=!e.values.has('mb_token')&&!e.values.has('mb_refresh_token');});
  e.api.clearTokens();assert.equal(e.visible.textContent,'');assert.equal(e.events(),1);assert.equal(sawComplete,true);
});
test('Successful save notifies only after both values are stored',()=>{
  const e=environment();e.target.addEventListener('metodobase-session-changed',()=>{
    assert.equal(e.values.get('mb_token'),'synthetic-B');assert.equal(e.values.get('mb_refresh_token'),'synthetic-RB');
  });e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});assert.equal(e.events(),1);
});
test('Partial write failure invalidates immediately and cannot become a trusted refresh source',async()=>{
  let fetches=0;const e=environment({fetch:async()=>{fetches++;return Response.json({success:true});}});e.writeFailure();
  assert.throws(()=>e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'}),error=>error.code==='session_storage_error');
  assert.equal(e.visible.textContent,'');assert.ok(e.events()>=1);
  await assert.rejects(e.api.auth.me(),error=>error.code==='session_storage_error');assert.equal(fetches,0);
});
test('Storage read failure invalidates immediately before any network await',async()=>{
  const e=environment();e.readFailure();const request=e.api.auth.me();assert.equal(e.visible.textContent,'');
  await assert.rejects(request,error=>error.code==='session_storage_error');assert.ok(e.events()>=1);
});
test('Detected external pair mutation emits synchronously at the next snapshot',async()=>{
  const e=environment();e.values.set('mb_token','synthetic-B');e.values.set('mb_refresh_token','synthetic-RB');
  const request=e.api.auth.me();assert.equal(e.visible.textContent,'');await request;assert.equal(e.events(),1);
});
test('Native Storage event invalidates while unrelated keys do not',()=>{
  const e=environment();const unrelated=new Event('storage');Object.defineProperty(unrelated,'key',{value:'legacy-water'});e.target.dispatchEvent(unrelated);assert.equal(e.events(),0);
  const storage=new Event('storage');Object.defineProperty(storage,'key',{value:'mb_token'});e.target.dispatchEvent(storage);assert.equal(e.visible.textContent,'');assert.equal(e.events(),1);
});
test('A successful same-revision refresh does not invalidate visible current-session data',async()=>{
  let sent=0;const e=environment({fetch:async url=>{
    if(url==='/api/auth/refresh')return Response.json({token:'synthetic-rotated',refresh_token:'synthetic-rotated-R'});
    if(++sent===1)return Response.json({}, {status:401});return Response.json({success:true});
  }});await e.api.auth.me();assert.equal(e.events(),0);assert.equal(e.visible.textContent,'Private prior-account row');
});
test('Reentrant listener read observes consolidated state and does not recurse',async()=>{
  const e=environment();const requests=[];e.target.addEventListener('metodobase-session-changed',()=>requests.push(e.api.auth.me()));
  e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});await Promise.all(requests);assert.equal(e.events(),1);
});
test('Explicit reentrant complete recovery wins without recursive notification or clobber',()=>{
  const e=environment();e.target.addEventListener('metodobase-session-changed',()=>e.api.saveTokens({token:'synthetic-C',refresh_token:'synthetic-RC'}));
  e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});assert.equal(e.events(),1);
  assert.equal(e.values.get('mb_token'),'synthetic-C');assert.equal(e.values.get('mb_refresh_token'),'synthetic-RC');
});
test('Notifier dispatch failure cannot turn a completed save into a transport error',()=>{
  const e=environment();e.target.dispatchEvent=()=>{throw new Error('synthetic listener infrastructure');};
  e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});assert.equal(e.values.get('mb_refresh_token'),'synthetic-RB');
});
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({name:entry.name,passed:true});}catch(error){results.push({name:entry.name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'Native EventTarget in offline VM; no browser/layout claim',passed:results.filter(r=>r.passed).length,total:results.length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
