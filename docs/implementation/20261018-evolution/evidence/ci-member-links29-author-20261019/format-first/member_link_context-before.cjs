/* Offline VM tests: actual Api context plus R12 lifecycle; no HTTP/browser claim. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const apiSource = fs.readFileSync(path.join(root, 'web/static/js/api.js'), 'utf8');
const contextSource = fs.readFileSync(path.join(root, 'web/static/js/vinculos-contexto.js'), 'utf8');
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return {promise,resolve,reject}; };
const identity = (overrides={}) => ({id:'synthetic-account-a',tipo:'usuario',role:'viewer',team_gym_id:null,session_version:1,...overrides});
function environment(me=identity()) {
  const stored = new Map([['mb_token','synthetic-access-a'],['mb_refresh_token','synthetic-refresh-a']]);
  const listeners = new Map(), calls = [];
  let storageFailure = false;
  const box = {console,URLSearchParams,setTimeout,clearTimeout,
    localStorage:{getItem:key => { if(storageFailure) throw Object.assign(new Error('Synthetic Storage failure'),{name:'SecurityError'}); return stored.get(key)||null; }, setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},
    location:{href:'',pathname:'/mis-vinculos'},
    addEventListener:(name,fn) => { if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(fn); },
    fetch:async (url,options) => { calls.push({url,options});return box.transport(url,options); },
    transport:async () => ({ok:true,status:200,json:async()=>({...box.me})}),
    me,
  };
  box.window=box;vm.createContext(box);
  vm.runInContext(apiSource+'\nglobalThis.api=Api;',box);
  vm.runInContext(contextSource,box);
  return {box,api:box.api,calls,stored,
    emit:(name,event={})=>{for(const fn of listeners.get(name)||[])fn(event);},
    storageFailure:value=>{storageFailure=value;},
    context:options=>box.MemberLinkContext.create(options),
  };
}
const cases = [];
function test(name,fn) { cases.push([name,fn]); }
const rejectsCode = (promise,code) => assert.rejects(promise,error=>error.code===code);

for(const [label,me] of [
  ['personal VIEWER',identity()],
  ['professional OWNER receiving a link',identity({tipo:'gym',role:'owner'})],
  ['historical gym member',identity({tipo:'gym',role:'viewer',team_gym_id:'synthetic-parent'})],
]) test(label+' uses only canonical auth/me context',async()=>{
  const env=environment(me), c=await env.api.vinculos.contexto();
  assert.equal(c.me.id,me.id);assert.deepEqual(JSON.parse(c.subject),[me.id,me.tipo,me.role,me.team_gym_id,me.session_version]);
  assert(Object.isFrozen(c)&&Object.isFrozen(c.me));
  assert.deepEqual(env.calls.map(x=>x.url),['/api/auth/me']);
});
test('ambiguous OWNER is not normalized or given a personal profile by the helper',async()=>{
  const env=environment(identity({role:'owner'}));const c=await env.api.vinculos.contexto();
  assert.equal(c.me.tipo,'usuario');assert.equal(c.me.role,'owner');
  assert.deepEqual(env.calls.map(x=>x.url),['/api/auth/me']);
  assert.equal(c.me.capabilities,undefined);
});
test('malformed canonical identity is rejected before consumers',async()=>{
  const env=environment(identity({session_version:'1'}));await rejectsCode(env.api.vinculos.contexto(),'session_changed');
});
for(const [name,value] of [['id','synthetic-account-b'],['role','admin'],['team_gym_id','synthetic-new-parent'],['session_version',2],['tipo','gym']]) {
  test('canonical '+name+' change invalidates the captured resource context',async()=>{
    const env=environment();const c=await env.api.vinculos.contexto();env.box.me=identity({[name]:value});
    await rejectsCode(env.api.vinculos.verificarContexto(c),'session_changed');
  });
}
test('late successful auth/me response cannot adopt account B',async()=>{
  const env=environment(), held=deferred();env.box.transport=()=>held.promise;
  const pending=env.api.vinculos.contexto();env.api.saveTokens({token:'synthetic-access-b',refresh_token:'synthetic-refresh-b'});
  held.resolve({ok:true,status:200,json:async()=>identity()});await rejectsCode(pending,'session_changed');
});
test('account change while parsing auth/me is fenced',async()=>{
  const env=environment(), parsing=deferred(), entered=deferred();
  env.box.transport=async()=>({ok:true,status:200,json:()=>{entered.resolve();return parsing.promise;}});
  const pending=env.api.vinculos.contexto();await entered.promise;
  env.api.saveTokens({token:'synthetic-access-b',refresh_token:'synthetic-refresh-b'});parsing.resolve(identity());
  await rejectsCode(pending,'session_changed');
});
test('same-session refresh still allows canonical context verification',async()=>{
  const env=environment();let first=true;
  env.box.transport=async url=>{
    if(url==='/api/auth/refresh')return {ok:true,status:200,json:async()=>({token:'synthetic-access-rotated',refresh_token:'synthetic-refresh-rotated'})};
    if(first){first=false;return {ok:false,status:401,json:async()=>({})};}
    return {ok:true,status:200,json:async()=>identity()};
  };
  const c=await env.api.vinculos.contexto();await env.api.vinculos.verificarContexto(c);
  assert.equal(env.calls.filter(x=>x.url==='/api/auth/refresh').length,1);assert.equal(c.revision,0);
});
test('Storage failure prevents context I/O without touching unrelated keys',async()=>{
  const env=environment();env.stored.set('mb_daily','synthetic-unattributed-legacy');env.storageFailure(true);
  await rejectsCode(env.api.vinculos.contexto(),'session_storage_error');assert.equal(env.calls.length,0);
  assert.equal(env.stored.get('mb_daily'),'synthetic-unattributed-legacy');
});
test('explicit new login rejects the prior context and allows a fresh context',async()=>{
  const env=environment(), old=await env.api.vinculos.contexto();
  env.api.saveTokens({token:'synthetic-access-b',refresh_token:'synthetic-refresh-b'});env.box.me=identity({id:'synthetic-account-b'});
  assert.throws(()=>env.api.vinculos.validarContexto(old),error=>error.code==='session_changed');
  const current=await env.api.vinculos.contexto();assert.equal(current.me.id,'synthetic-account-b');
});
test('pending resource result is discarded and all private scopes clear on account change',async()=>{
  const env=environment(), held=deferred(), entered=deferred();let cleared=0;
  const ctx=env.context({onInvalidated:()=>cleared++});await ctx.start();
  const a=ctx.scope(()=>cleared++),b=ctx.scope(()=>cleared++);
  const pending=a.read(async()=>{entered.resolve();return held.promise;});await entered.promise;
  env.api.saveTokens({token:'synthetic-access-b',refresh_token:'synthetic-refresh-b'});
  held.resolve({private_marker:'synthetic-old-menu'});await rejectsCode(pending,'session_changed');
  assert.equal(ctx.active,false);assert.equal(cleared,3);assert.throws(()=>b.check());
});
for(const [name,event] of [
  ['storage',{key:'mb_token'}],['storage',{key:null}],
  ['metodobase-session-changed',{detail:{code:'session_storage_error'}}],['pagehide',{}],
]) test(name+' synchronously clears resource scopes',async()=>{
  const env=environment();let cleared=false;const ctx=env.context();await ctx.start();ctx.scope(()=>{cleared=true;});
  env.emit(name,event);assert.equal(cleared,true);assert.equal(ctx.active,false);
});
test('unrelated Storage event does not adopt or delete legacy data',async()=>{
  const env=environment();env.stored.set('mb_meals','synthetic-legacy-bytes');const ctx=env.context();await ctx.start();
  env.emit('storage',{key:'mb_meals'});ctx.check();assert.equal(env.stored.get('mb_meals'),'synthetic-legacy-bytes');
});
test('switching a selected link cancels only its resource scope',async()=>{
  const env=environment(), ctx=env.context();await ctx.start();const held=deferred(), entered=deferred();
  const old=ctx.scope();const pending=old.read(async()=>{entered.resolve();return held.promise;});await entered.promise;
  old.invalidate();held.resolve({old:true});await rejectsCode(pending,'member_context_changed');
  ctx.check();assert.equal(ctx.active,true);const next=ctx.scope();assert.equal((await next.read(async()=>({current:true}))).current,true);
});
test('controls invalidating synchronously cannot continue rendering private data',async()=>{
  const env=environment();let sensitive='synthetic-menu',after=false;
  const ctx=env.context({onInvalidated:()=>{sensitive='';}});await ctx.start();
  assert.throws(()=>ctx.render(()=>{env.api.saveTokens({token:'synthetic-access-b',refresh_token:'synthetic-refresh-b'});}),e=>e.code==='session_changed');
  try {ctx.render(()=>{after=true;});}catch{}
  assert.equal(after,false);assert.equal(sensitive,'');
});
test('canonical SV change after resource response prevents a return to the view',async()=>{
  const env=environment(),ctx=env.context();await ctx.start();
  await rejectsCode(ctx.read(async()=>{env.box.me=identity({session_version:2});return {old:true};}),'session_changed');
  assert.equal(ctx.active,false);
});
test('late failed resource response also verifies the session before reporting an error',async()=>{
  const env=environment(),ctx=env.context();await ctx.start();
  await rejectsCode(ctx.read(async()=>{env.box.me=identity({role:'admin'});throw new Error('Synthetic old failure');}),'session_changed');
});
test('one failing cleanup callback cannot leave sibling scopes active',async()=>{
  const env=environment(),ctx=env.context();await ctx.start();let cleared=false;
  ctx.scope(()=>{throw new Error('Synthetic consumer cleanup');});const sibling=ctx.scope(()=>{cleared=true;});
  env.emit('pagehide');assert.equal(cleared,true);assert.throws(()=>sibling.check());
});

(async()=>{
  const results=[];
  for(const [name,fn] of cases){try{await fn();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'Offline VM with actual Api and new lifecycle; all transports/Storage synthetic',passed:results.filter(x=>x.passed).length,total:results.length,results},null,2));
  if(results.some(x=>!x.passed))process.exitCode=1;
})();
