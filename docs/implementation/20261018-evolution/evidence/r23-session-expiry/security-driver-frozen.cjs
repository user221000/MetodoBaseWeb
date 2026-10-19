'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=process.env.SESSION_EVENT_REVIEW_ROOT || 'F:/mb-event-sec';
const source=fs.readFileSync(process.argv[2] || path.join(root,'web/static/js/api.js'),'utf8');
const tests=[];const test=(name,body)=>tests.push({name,body});
const pair=n=>({token:'synthetic-access-'+n,refresh_token:'synthetic-refresh-'+n});
function env(fetcher){
  const target=new EventTarget(),values=new Map([['mb_token',pair('A').token],['mb_refresh_token',pair('A').refresh_token]]);
  target.location={href:'/protected-synthetic'};
  let badRead=false,badWrite=false;const sent=[];
  const context={window:target,Event,EventTarget,Response,Blob,FormData,URL,setTimeout,clearTimeout,console,
    localStorage:{getItem(k){if(badRead)throw new DOMException('SYNTHETIC_STORAGE','SecurityError');return values.get(k)||null;},
      setItem(k,v){if(badWrite && k==='mb_refresh_token')throw new DOMException('SYNTHETIC_STORAGE','QuotaExceededError');values.set(k,v);},removeItem:k=>values.delete(k)},
    fetch:async(u,o)=>{sent.push({url:u,options:o});return fetcher?fetcher(u,o,sent.length):Response.json({success:true});}};
  vm.createContext(context);vm.runInContext(source+'\nglobalThis.reviewApi=Api;',context);
  return {api:context.reviewApi,target,values,context,sent,failRead:v=>badRead=v,failWrite:v=>badWrite=v};
}
function isPair(e,n){assert.equal(e.values.get('mb_token'),pair(n).token);assert.equal(e.values.get('mb_refresh_token'),pair(n).refresh_token);}

test('Event has no detail credential fields or synthetic token in serialized own data',()=>{
  const e=env();let count=0;
  e.target.addEventListener('metodobase-session-changed',event=>{
    count++;assert.ok(event instanceof Event);assert.equal(event.detail,undefined);assert.equal(event.bubbles,false);assert.equal(event.cancelable,false);
    for(const key of ['token','refresh_token','access_token','credentials','code','message'])assert.equal(event[key],undefined);
    assert.ok(!JSON.stringify(event).includes('synthetic-access-'));isPair(e,'B');
  });
  e.api.saveTokens(pair('B'));assert.equal(count,1);
});

test('Actual PersonalHistory consumer clears loaded rows cursor and visible text before saveTokens returns',async()=>{
  const e=env();let valid=true;const visible={textContent:''};
  e.context.PersonalPlanOperation={validPlanId:id=>Number.isInteger(id)&&id>0};
  vm.runInContext(fs.readFileSync(path.join(root,'web/static/js/usuario-historial.js'),'utf8'),e.context);
  const personal={check(){assert.ok(valid);},invalidate(){valid=false;},read:async()=>({planes:[{id:7,synthetic_marker:'PRIOR_ACCOUNT'}],next_cursor:'opaque-synthetic'})};
  const history=e.target.PersonalHistory.create({personal,onChange:view=>visible.textContent=view.rows.map(r=>r.synthetic_marker).join(','),onInvalidated:()=>visible.textContent=''});
  await history.load();assert.equal(visible.textContent,'PRIOR_ACCOUNT');assert.equal(history.view.rows.length,1);
  e.api.saveTokens(pair('B'));
  assert.equal(visible.textContent,'');assert.equal(history.view.rows.length,0);assert.equal(history.view.hasMore,false);assert.equal(history.view.invalid,true);assert.equal(valid,false);
});

test('Native listener exception leaves committed state and remaining listeners usable',async()=>{
  const e=env();let observed=false,reported=0;
  const caught=()=>reported++;process.on('uncaughtException',caught);
  try{
    e.target.addEventListener('metodobase-session-changed',()=>{throw new Error('SYNTHETIC_LISTENER_FAILURE');});
    e.target.addEventListener('metodobase-session-changed',()=>{observed=true;isPair(e,'B');});
    e.api.saveTokens(pair('B'));assert.equal(observed,true);await new Promise(resolve=>setImmediate(resolve));assert.equal(reported,1);
    await e.api.auth.me();assert.equal(e.sent.length,1);assert.equal(e.sent[0].options.headers.Authorization,'Bearer '+pair('B').token);
  }finally{process.removeListener('uncaughtException',caught);}
});

test('Reentrant full recovery during partial Storage failure preserves C and blocks the failed old operation',async()=>{
  const e=env();let events=0;e.failWrite(true);
  e.target.addEventListener('metodobase-session-changed',()=>{events++;e.failWrite(false);e.api.saveTokens(pair('C'));});
  assert.throws(()=>e.api.saveTokens(pair('B')),x=>x.code==='session_storage_error');isPair(e,'C');assert.equal(events,1);
  await e.api.auth.me();assert.equal(e.sent.length,1);assert.equal(e.sent[0].options.headers.Authorization,'Bearer '+pair('C').token);
});

test('Reentrant read failure cannot dispatch an authenticated DTO from an untrusted pair',async()=>{
  const e=env();let events=0,reentry;
  e.target.addEventListener('metodobase-session-changed',()=>{events++;e.failRead(true);reentry=e.api.auth.me();});
  e.api.saveTokens(pair('B'));await assert.rejects(reentry,x=>x.code==='session_storage_error');assert.equal(events,1);assert.equal(e.sent.length,0);
  e.failRead(false);await assert.rejects(e.api.auth.me(),x=>x.code==='session_storage_error');assert.equal(e.sent.length,0);
});

test('Logout listener recovery leaves B active and reports session_changed instead of closed_local',async()=>{
  const e=env();let events=0;
  e.target.addEventListener('metodobase-session-changed',()=>{events++;e.api.saveTokens(pair('B'));});
  const answer=await e.api.auth.logout();assert.equal(answer.state,'session_changed');assert.equal(answer.server_confirmed,false);isPair(e,'B');assert.equal(events,1);assert.equal(e.target.location.href,'/protected-synthetic');
});

test('Refresh failure emits exactly one invalidation when no listener replaces the expired session',async()=>{
  const e=env(()=>Response.json({}, {status:401}));let events=0;
  e.target.addEventListener('metodobase-session-changed',()=>events++);
  await assert.rejects(e.api.auth.me(),x=>x.code==='session_expired');assert.equal(events,1);assert.equal(e.values.has('mb_token'),false);assert.equal(e.values.has('mb_refresh_token'),false);assert.equal(e.target.location.href,'/login-gym');
});

for(const mode of ['no refresh credential','refresh rejected','rotated access still rejected']){
  test('Expired A must not redirect B recovered synchronously by listener: '+mode,async()=>{
    const e=env(url=>url==='/api/auth/refresh' && mode==='rotated access still rejected'?Response.json(pair('ROTATED')):Response.json({}, {status:401}));
    if(mode==='no refresh credential')e.values.delete('mb_refresh_token');
    let recoveries=0;
    e.target.addEventListener('metodobase-session-changed',()=>{
      if(!e.values.get('mb_token')&&!e.values.get('mb_refresh_token')){recoveries++;e.api.saveTokens(pair('B'));}
    });
    let failure;try{await e.api.auth.me();}catch(error){failure=error;}
    assert.equal(recoveries,1);isPair(e,'B');
    assert.equal(e.target.location.href,'/protected-synthetic','stale expiry redirected a newer recovered session');
    assert.equal(failure?.code,'session_changed');
    assert.ok(e.sent.every(x=>x.options.headers.Authorization!=='Bearer '+pair('B').token));
  });
}

(async()=>{const results=[];for(const t of tests){try{await t.body();results.push({name:t.name,passed:true});}catch(error){results.push({name:t.name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'Offline native EventTarget/VM, actual history controller with synthetic data; no browser or real account',total:results.length,passed:results.filter(x=>x.passed).length,results},null,2));if(results.some(x=>!x.passed))process.exitCode=1;
})();
