/* Pure controller/transport contracts; no browser, sockets, provider or storage. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const panel=require(path.join(root,'web/static/js/rutinas.js'));
let count=0;
function test(name,run){run();count++;console.log('PASS '+name);}
test('nonconsecutive week includes Sunday/Monday boundary',()=>{
 assert.equal(panel.validWeek([0,2,4]),true);assert.equal(panel.validWeek([1,3,5]),true);
 assert.equal(panel.validWeek([2,4,6]),true);assert.equal(panel.validWeek([0,2,6]),false);
 assert.equal(panel.validWeek([0,1,4]),false);assert.equal(panel.validWeek([0,0,4]),false);
 assert.equal(panel.validWeek([0,2]),false);assert.equal(panel.validWeek([0,2,4,6]),false);
 assert.equal(panel.validWeek([0,2,'4']),false);assert.equal(panel.validWeek([0,2,7]),false);
});
test('week is chronological and does not mutate selection',()=>{
 const selected=[4,0,2];assert.deepEqual(panel.week(selected,['L','M','X','J','V','S','D']),[
 {day:0,label:'L',session:'push'},{day:2,label:'X',session:'pull'},{day:4,label:'V',session:'legs'}]);
 assert.deepEqual(selected,[4,0,2]);assert.equal(panel.week([0,1,2],[]),null);
});
test('timer start/pause/resume uses elapsed time without recording exercise',()=>{
 let at=1000;const timer=panel.createTimer(()=>at);
 assert.deepEqual(timer.read(),{duration:90,remaining:90,running:false});
 timer.toggle();at+=20500;assert.equal(timer.read().remaining,70);
 timer.toggle();at+=60000;assert.equal(timer.read().remaining,70);
 timer.toggle();at+=70000;assert.deepEqual(timer.read(),{duration:90,remaining:0,running:false});
 assert.equal(timer.toggle().remaining,90);
});
test('timer reset clears running state and rejects fabricated duration',()=>{
 let at=0;const timer=panel.createTimer(()=>at);timer.toggle();at=5000;
 assert.deepEqual(timer.reset(60),{duration:60,remaining:60,running:false});
 assert.deepEqual(timer.reset(120),{duration:120,remaining:120,running:false});
 assert.throws(()=>timer.reset(999),RangeError);assert.throws(()=>timer.reset('60'),RangeError);
});
const fixture=process.env.ROUTINE_CATALOG_FIXTURE;
assert.ok(fixture,'Pass the actual Python catalogue fixture via ROUTINE_CATALOG_FIXTURE');
const dto=JSON.parse(fs.readFileSync(fixture,'utf8'));
test('actual catalogue validates and keeps all three sessions',()=>{
 assert.equal(panel.validate(dto,'gym').sessions.length,3);
 const other=structuredClone(dto);other.scope='personal';assert.equal(panel.validate(other,'personal').sessions[0].id,'push');
});
test('invalid catalogue cannot partially render unsafe/fabricated content',()=>{
 for(const mutate of[
  v=>v.version=2,v=>v.scope='personal',v=>v.program.sessions.reverse(),
  v=>v.program.sessions[0].exercises[0].rest_seconds=1,
  v=>v.program.sessions[0].exercises[0].sets.maximum=99,
  v=>v.program.sources[0].url='javascript:alert(1)',
  v=>v.program.schedule.default_days=[0,1,4],
 ]){const value=structuredClone(dto);mutate(value);assert.throws(()=>panel.validate(value,'gym'));}
});
async function transport(){
 let revision=1,calls=[],ready=false;
 const api={session:{ready:Promise.resolve().then(()=>{ready=true;}),capture:()=>({revision}),check:c=>{if(c.revision!==revision)throw Object.assign(Error('changed'),{code:'session_changed'});}},getToken:()=>{assert.equal(ready,true);return 'synthetic-token-in-RAM';}};
 const fetcher=async(url,options)=>{calls.push({url,options});return{ok:true,status:200,text:async()=>JSON.stringify(dto)};};
 assert.equal((await panel.readCatalog(api,'gym',fetcher)).id,'ppl-basico-v1');
 assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/rutinas/catalogo?context=gym');
 assert.equal(calls[0].options.credentials,'omit');assert.equal(calls[0].options.method,'GET');
 assert.equal(calls[0].options.redirect,'error');assert.equal(calls[0].options.cache,'no-store');
 assert.equal(calls[0].options.headers.Authorization,'Bearer synthetic-token-in-RAM');
 assert.equal(Object.hasOwn(calls[0].options,'body'),false);count++;console.log('PASS real bootstrap API transport contract');
 await assert.rejects(panel.readCatalog(api,'gym',async()=>{revision++;return{ok:true,status:200,text:async()=>JSON.stringify(dto)};}),{code:'session_changed'});
 count++;console.log('PASS session change rejects response without retry');
 let failures=0;await assert.rejects(panel.readCatalog(api,'gym',async()=>{failures++;return{ok:false,status:403,text:async()=>JSON.stringify({detail:{code:'routine_context_forbidden'}})};}),{status:403,code:'routine_context_forbidden'});
 assert.equal(failures,1);count++;console.log('PASS forbidden response is not replayed or refreshed');
 await assert.rejects(panel.readCatalog({...api,getToken:()=>''},'gym',async()=>{throw Error('must not fetch');}),{status:401});
 count++;console.log('PASS missing RAM access makes no catalogue request');
 for(const readyState of['complete','loading']){
  const nodes=new Map(),events=new Map();let bootstraps=0;
  const getNode=selector=>{if(!nodes.has(selector))nodes.set(selector,{textContent:'',hidden:false,disabled:false,value:'90',addEventListener(){},replaceChildren(){}});return nodes.get(selector);};
  const shell={dataset:{scope:'personal'},querySelector:getNode};
  const sandbox={console,TextEncoder,performance,setInterval,clearInterval,fetch:()=>{throw Error('Missing access must not fetch');},addEventListener(){},document:{readyState,querySelector:()=>shell,addEventListener:(name,fn)=>events.set(name,fn)}};
  sandbox.window=sandbox;vm.createContext(sandbox);
  // This is the real api.js export shape: a lexical const, not window.Api.
  sandbox.fixtureBootstrap=()=>{bootstraps++;};
  vm.runInContext("const Api={session:{ready:Promise.resolve(),capture(){fixtureBootstrap();return{};},check(){}},getToken(){return '';}};",sandbox);
  assert.equal(Object.hasOwn(sandbox,'Api'),false);
  vm.runInContext(fs.readFileSync(path.join(root,'web/static/js/rutinas.js'),'utf8'),sandbox);
  if(readyState==='loading'){assert.equal(bootstraps,0);events.get('DOMContentLoaded')();}
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(bootstraps,1);assert.equal(getNode('[data-routine-status]').textContent,'Inicia sesión para consultar las rutinas.');
  count++;console.log('PASS actual lexical Api bootstrap '+readyState);
 }
 // The browser lifecycle installs clear/invalidate hooks; no storage or raw
 // HTML interpolation API exists in this component.
 const source=fs.readFileSync(path.join(root,'web/static/js/rutinas.js'),'utf8');
 assert.ok(source.includes("root.addEventListener('metodobase-session-changed',invalidate)"));
 assert.ok(source.includes("root.addEventListener('pagehide',invalidate)"));
 assert.equal(/localStorage|sessionStorage|innerHTML|document\.cookie/.test(source),false);
 new vm.Script(source);count++;console.log('PASS component has no storage/cookie/HTML interpolation or syntax error');
 console.log(JSON.stringify({passed:count,total:count,scope:'pure Node VM and real catalogue transport contract; no browser'}));
}
transport().catch(error=>{console.error(error);process.exitCode=1;});
