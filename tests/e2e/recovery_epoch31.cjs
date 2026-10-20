/* Public proof reset and a separate actual API/shell tab; offline network/DOM doubles. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto'),Module=require('node:module');
function helpers(file,marker,names){const source=fs.readFileSync(file,'utf8').split(marker)[0],mod=new Module(__filename,module);mod.filename=__filename;mod.paths=module.paths;mod._compile(source+'\nmodule.exports={'+names+'};',__filename);return mod.exports;}
const {world}=helpers('tests/e2e/browser_session31.cjs','const rows=[];','world');
const {fixture:dom}=helpers('tests/e2e/session_shell31.cjs','const results=[];','fixture');
const source=fs.readFileSync(process.env.RECOVERY31_SOURCE||'web/static/js/account-recovery.js','utf8');
async function fixture(status=200,storageDenied=false,network=false){
  const w=world(),old=w.tab();await old.api.session.ready;const d=dom();old.sandbox.document=d.document;vm.runInContext(fs.readFileSync('web/static/js/session-shell.js','utf8'),old.context);
  const nodes=new Map(),events=new Map(),calls=[],writes=[],messages=[];
  function node(id){if(!nodes.has(id))nodes.set(id,{value:'',hidden:false,disabled:false,textContent:'',events:new Map(),addEventListener(name,fn){this.events.set(name,fn);},reportValidity:()=>true,querySelector(){return node(id+'-button');}});return nodes.get(id);}
  node('recovery-password').value='Synthetic password';node('recovery-confirmation').value='Synthetic password';
  const sandbox={TextEncoder,URLSearchParams,Event,crypto:crypto.webcrypto,document:{getElementById:node},location:{hash:'#token='+'R'.repeat(43),pathname:'/auth/reset-password'},history:{replaceState(...args){assert.equal(args[2],'/auth/reset-password');}},localStorage:{setItem(key,value){assert.equal(key,'mb_session_epoch');assert.match(value,/^[0-9a-f-]{36}$/);if(storageDenied)throw Object.assign(Error('Denied'),{name:'SecurityError'});writes.push(key);w.shared.set(key,value);old.dispatch({type:'storage',key,newValue:value});},getItem(key){assert.equal(key,'mb_session_epoch');if(storageDenied)throw Object.assign(Error('Denied'),{name:'SecurityError'});return w.shared.get(key);}},BroadcastChannel:class{constructor(name){assert.equal(name,'metodobase.browser-session.v1');}postMessage(data){assert.deepEqual(Object.keys(data),['epoch']);messages.push(data);}close(){}},fetch:async(path,options)=>{calls.push({path,options});assert.equal(options.credentials,'omit');assert.equal(options.headers.Authorization,undefined);assert.equal(path,'/api/auth/password-reset/confirm');if(network)throw Error('Synthetic lost response');return{ok:status===200,status,json:async()=>status===200?{message:'Password changed'}:{detail:{message:'Unconfirmed'}}};}};
  sandbox.window=sandbox;sandbox.addEventListener=(name,fn)=>{if(!events.has(name))events.set(name,[]);events.get(name).push(fn);};sandbox.dispatchEvent=e=>{for(const fn of events.get(e.type)||[])fn(e);};
  vm.runInContext(source,vm.createContext(sandbox));
  return{old,d,calls,writes,messages,node,async confirm(){await node('recovery-confirm').events.get('submit')({preventDefault(){}});await Promise.resolve();}};
}
const results=[];async function test(name,run){try{await run();results.push({case:name,passed:true});}catch(error){results.push({case:name,passed:false,error_class:error.name,code:error.code||null});}}
(async()=>{
for(const code of [200,503])await test('Public reset'+code+' invalidates the separate current account tab without auth bootstrap',async()=>{const f=await fixture(code);await f.confirm();assert.equal(f.calls.length,1);assert.equal(f.writes.length,1);assert.equal(f.messages.length,1);assert.equal(f.old.api.getToken(),'');assert.equal(f.d.field.value,'');assert.equal(f.d.document.getElementById('old-client-name'),null);assert.equal(f.node('recovery-confirm').hidden,true);});
if(!process.env.RECOVERY31_SOURCE){
for(const code of [403,422])await test('Rejected reset'+code+' does not invalidate another account session',async()=>{const f=await fixture(code),access=f.old.api.getToken();await f.confirm();assert.equal(f.old.api.getToken(),access);assert.equal(f.writes.length,0);assert.equal(f.messages.length,0);assert.ok(f.d.document.getElementById('old-client-name'));});
await test('Denied invalidation Storage makes no claim that all tabs were notified',async()=>{const f=await fixture(200,true);await f.confirm();assert.match(f.node('recovery-status').textContent,/No se pudo avisar de forma fiable/);assert.equal(f.writes.length,0);assert.equal(f.calls.length,1);});
await test('Lost reset response after dispatch invalidates old tab without automatic retry or adoption',async()=>{const f=await fixture(200,false,true);await f.confirm();assert.equal(f.calls.length,1);assert.equal(f.old.api.getToken(),'');assert.equal(f.d.document.getElementById('old-client-name'),null);});
}
const report={scope:'Actual public account-recovery.js and separate actual api.js/session-shell.js in VM/minimalDOM; no provider/server/native-browser acceptance',passed:results.filter(row=>row.passed).length,total:results.length,results};process.stdout.write(JSON.stringify(report,null,2)+'\n');process.exitCode=report.passed===report.total?0:1;
})();
