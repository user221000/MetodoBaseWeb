/* Independent combined namespace/controller probes; synthetic RAM transport. */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('web/static/js/api.js','utf8')+'\n;globalThis.PeerApi=Api;\n'+fs.readFileSync('web/static/js/nutrition35.js','utf8');
const declaration=()=>({version:1,allergies:{version:1,status:'not_reported',foods:[],other_reported:false},professional_review_requested:false});
const pause=()=>{let resolve;const promise=new Promise(yes=>{resolve=yes;});return {promise,resolve};};
function fixture(hook=()=>null){
  const values=new Map([['mb_token','synthetic-a-access'],['mb_refresh_token','synthetic-a-refresh']]),listeners=new Map(),calls=[],views=[];
  const window={location:{href:''},addEventListener:(name,fn)=>{if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(fn);},dispatchEvent:event=>{for(const fn of listeners.get(event.type)||[])fn(event);}};
  const context=vm.createContext({window,Event,TextEncoder,Date,URLSearchParams,FormData,File,Blob,WeakMap,setTimeout,clearTimeout,localStorage:{getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)},fetch:async(path,options)=>{
    calls.push({path,method:options.method,body:options.body});
    const injected=await hook(path,options,calls);if(injected)return injected;
    if(path==='/api/auth/me')return Response.json({id:'actor-a',role:'OWNER',team_gym_id:null,session_version:1});
    if(path==='/api/alimentos/catalogo')return Response.json({categorias:{source:['huevo']}});
    if(path.startsWith('/api/clientes/')&&options.method==='GET')return Response.json({id_cliente:path.split('/').pop(),restricciones_nutricionales:declaration()});
    if(options.method==='PUT')return Response.json({success:true});
    throw Error('Unexpected purpose');
  }});
  vm.runInContext(source,context);const api=context.PeerApi;
  const page=context.window.Nutrition35.create({api:api.nutrition,onView:view=>views.push(JSON.parse(JSON.stringify(view)))});
  return {api,page,calls,views,values,window};
}
const tests=[],test=(name,run)=>tests.push({name,run});
test('changed persistent subject after profile read clears facts before render',async()=>{
  let me=0;const f=fixture(path=>{if(path==='/api/auth/me'&&++me===3)return Response.json({id:'actor-b',role:'OWNER',session_version:1});});
  await f.page.load('client-a');assert.equal(f.page.view().phase,'invalidated');assert.equal(f.page.view().declaration,null);
  assert.equal(f.views.some(view=>view.declaration!==null),false);assert.equal(f.calls.some(call=>call.method==='PUT'),false);
});
test('foreign response client id fails without rendering or adopting its declaration',async()=>{
  const f=fixture((path,options)=>path.startsWith('/api/clientes/')&&options.method==='GET'?Response.json({id_cliente:'foreign',restricciones_nutricionales:declaration()}):null);
  await f.page.load('client-a');assert.equal(f.page.view().phase,'error');assert.equal(f.page.view().declaration,null);assert.throws(()=>f.page.requireAutomation());
});
test('account replacement during JSON parsing discards a late health response',async()=>{
  const gate=pause();let entered=false;
  const f=fixture((path,options)=>{if(path.startsWith('/api/clientes/')&&options.method==='GET'){entered=true;return {ok:true,status:200,headers:new Headers(),json:()=>gate.promise};}return null;});
  const pending=f.page.load('client-a');for(let i=0;i<100&&!entered;i++)await Promise.resolve();assert.equal(entered,true);
  f.api.saveTokens({token:'synthetic-b-access',refresh_token:'synthetic-b-refresh'});gate.resolve({id_cliente:'client-a',restricciones_nutricionales:declaration()});await pending;
  assert.equal(f.page.view().phase,'invalidated');assert.equal(f.page.view().declaration,null);assert.equal(f.values.get('mb_token'),'synthetic-b-access');
});
test('same access with replaced refresh pair invalidates pending reads',async()=>{
  const f=fixture();await f.page.load('client-a');f.values.set('mb_refresh_token','synthetic-replacement-refresh');
  assert.throws(()=>f.page.requireAutomation(),error=>error.code==='session_changed');assert.equal(f.page.view().declaration,null);
});
for(const status of [401,503])test('write '+status+' is single dispatch without automatic readback refresh or response-text rendering',async()=>{
  const f=fixture((path,options)=>options.method==='PUT'?Response.json({detail:{code:'unknown_sensitive_error',message:'SYNTHETIC_HEALTH_ERROR_TEXT'}},{status}):null);
  await f.page.load('client-a');const before=f.calls.length;await assert.rejects(()=>f.page.save({peso_kg:77}));
  const tail=f.calls.slice(before);assert.equal(tail.filter(call=>call.method==='PUT').length,1);assert.equal(tail.filter(call=>call.path==='/api/auth/refresh').length,0);assert.equal(tail.filter(call=>call.path.startsWith('/api/clientes/')&&call.method==='GET').length,0);
  assert.equal(f.page.view().message.includes('SYNTHETIC_HEALTH_ERROR_TEXT'),false);assert.equal(f.page.view().phase,status===401?'invalidated':'uncertain');
});
test('UTF8 byte cap prevents dispatch and does not manufacture mutation uncertainty',async()=>{
  const f=fixture();await f.page.load('client-a');const before=f.calls.length;await assert.rejects(()=>f.page.save({notas:'ñ'.repeat(17000)}));
  assert.equal(f.calls.slice(before).some(call=>call.method==='PUT'),false);assert.equal(f.page.view().phase,'ready');assert.equal(f.page.view().busy,false);
});
(async()=>{const results=[];for(const item of tests){try{await item.run();results.push({name:item.name,passed:true});}catch(error){results.push({name:item.name,passed:false,class:error.name});}}const report={scope:'Independent actual Api.nutrition plus Nutrition35 controller, synthetic RAM transport, no HTTP/browser/provider claim',total:results.length,passed:results.filter(result=>result.passed).length,results};console.log(JSON.stringify(report));if(report.passed!==report.total)process.exitCode=1;})();
