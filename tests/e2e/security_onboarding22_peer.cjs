'use strict';
// Actual dashboard + API + session shell and actual personal inline/controller.
// Transport, Cookie/WebLock, ancillary diary/nutrition and DOM are declared doubles.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const oldHelper=cp.execFileSync('git',['show','6ee27e3c:tests/e2e/security_browser31_ui_peer.cjs'],{encoding:'utf8'});
const helper=vm.runInThisContext('(function(require){'+oldHelper.split('const tests=[],test=')[0]+';return {environment,response,wait,tick};})')(require);
const {environment,response,wait,tick}=helper;
const source=fs.readFileSync('web/static/js/main.js','utf8'),shell=fs.readFileSync('web/static/js/session-shell.js','utf8');
const personalMarkup=fs.readFileSync('web/templates/usuario_mi_plan.html','utf8');
const personalSource=[...personalMarkup.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.trim());
assert.equal(personalSource.length,1);
function dom(sandbox,ids){
  const nodes=new Map(),events=[];
  function make(id){
    const classes=new Set(),listeners=new Map();
    return {id,style:{display:'none'},dataset:{},textContent:'',hidden:false,disabled:false,value:'',children:[],attributes:{},
      classList:{add(...xs){xs.forEach(x=>classes.add(x));},remove(...xs){xs.forEach(x=>classes.delete(x));},contains:x=>classes.has(x)},
      setAttribute(k,v){this.attributes[k]=String(v);},getAttribute(k){return this.attributes[k];},
      addEventListener(k,fn){if(!listeners.has(k))listeners.set(k,[]);listeners.get(k).push(fn);},
      listenerCount(k){return (listeners.get(k)||[]).length;},
      click(){if(this.disabled)return;this.onclick?.();for(const fn of listeners.get('click')||[])fn.call(this,{target:this});},
      focus(){events.push('focus');},querySelector(){return null;},querySelectorAll(){return [];},
      append(...xs){this.children.push(...xs);},appendChild(x){this.children.push(x);},before(){},
      replaceChildren(...xs){this.children=xs;this.textContent='';},closest(){return null;},remove(){nodes.delete(id);}};
  }
  for(const id of ids)nodes.set(id,make(id));
  const main=make('main');main.replaceChildren=(...xs)=>{for(const id of [...nodes.keys()])if(!id.startsWith('sb-')&&id!=='toast-container')nodes.delete(id);main.children=xs;};
  sandbox.document={readyState:'loading',addEventListener(){},getElementById:id=>nodes.get(id)||null,
    querySelector:selector=>selector==='main'?main:null,
    querySelectorAll:selector=>selector==='main'?[main]:[],createElement:tag=>make(tag)};
  return {nodes,main,events};
}
function page(){
  const storage=[],sandbox={console:{error(){}},Toast:{error(){}},counterObserver:{observe(){}},
    localStorage:{getItem(){storage.push('get');throw Error('SYNTHETIC STORAGE DENIAL');},setItem(){storage.push('set');throw Error('SYNTHETIC STORAGE DENIAL');}}};
  const d=dom(sandbox,['onboarding-section','onboarding-pct','onboarding-bar-fill','ob-step-1','ob-step-2','ob-step-3','ob-action-1','btn-generar-plan','kpi-section']);
  const context=vm.createContext(sandbox);vm.runInContext(source,context);
  return {...d,context,storage,update:value=>context.updateOnboarding(value)};
}
const facts=(client,plan)=>({onboarding:{client_registered:client,plan_saved:plan},total_clientes:900,planes_periodo:900});
function incomplete(p){for(const id of ['ob-step-1','ob-step-2']){assert.equal(p.nodes.get(id).classList.contains('completed'),false);assert.equal(p.nodes.get(id).classList.contains('current'),false);}assert.equal(p.nodes.get('onboarding-bar-fill').hidden,true);assert.equal(p.nodes.get('onboarding-bar-fill').style.width,'0%');assert.match(p.nodes.get('onboarding-pct').textContent,/confirmar/);assert.equal(p.nodes.get('onboarding-section').attributes['aria-busy'],'false');}
const tests=[],test=(name,run)=>tests.push({name,run});
const malformed=[null,{},[],{client_registered:true},{plan_saved:false},
  {client_registered:1,plan_saved:true},{client_registered:true,plan_saved:1},
  {client_registered:'false',plan_saved:false},{client_registered:true,plan_saved:'false'},
  {client_registered:null,plan_saved:false},{client_registered:false,plan_saved:true}];
malformed.forEach((onboarding,index)=>test('unknown facts '+index+' retire prior completion rather than infer from counts',()=>{
  const p=page();p.update(facts(true,true));p.update({total_clientes:900,planes_periodo:900,onboarding});incomplete(p);assert.deepEqual(p.storage,[]);
}));
test('whole response missing clears a previously confirmed guide',()=>{const p=page();p.update(facts(true,true));p.update(null);incomplete(p);});
test('all three coherent boolean states expose exactly the next pending step',()=>{
  const p=page();for(const [client,plan]of [[false,false],[true,false],[true,true]]){
    p.update(facts(client,plan));assert.equal(p.nodes.get('ob-step-1').classList.contains('completed'),client);
    assert.equal(p.nodes.get('ob-step-2').classList.contains('completed'),plan);
    assert.equal(p.nodes.get('ob-step-1').classList.contains('current'),!client);
    assert.equal(p.nodes.get('ob-step-2').classList.contains('current'),client&&!plan);
    assert.equal(p.nodes.get('onboarding-bar-fill').hidden,false);assert.equal(p.nodes.get('ob-step-3').classList.contains('completed'),false);
  }
});
test('repeated dashboard consultation replaces the native action handler',()=>{const p=page();let clicks=0;p.nodes.get('btn-generar-plan').click=()=>clicks++;for(let i=0;i<20;i++)p.update(facts(false,false));p.nodes.get('ob-action-1').click();assert.equal(clicks,1);assert.deepEqual(p.storage,[]);});
test('confirmed extra delivery-shaped fields cannot create a third completed step',()=>{const p=page();p.update({...facts(true,true),delivered:true,exported:true,onboarding:{client_registered:true,plan_saved:true,delivered:true,exported:true}});assert.equal(p.nodes.get('ob-step-3').classList.contains('completed'),false);assert.match(p.nodes.get('onboarding-pct').textContent,/2 de 2/);});

async function dashboard(){
  const world=environment(),t=world.tab();await t.api.session.ready;
  const d=dom(t.sandbox,['onboarding-section','onboarding-pct','onboarding-bar-fill','ob-step-1','ob-step-2','ob-action-1','btn-generar-plan','kpi-section','sb-total-clientes']);
  const toasts=[];t.sandbox.counterObserver={observe(){}};t.sandbox.Toast={error:message=>toasts.push(message)};
  vm.runInContext(shell,t.context);vm.runInContext(source,t.context);
  return {world,t,...d,toasts};
}
for(const boundary of ['storage','broadcast','pagehide','bfcache','epoch-only'])test('late dashboard facts cannot render across '+boundary,async()=>{
  const p=await dashboard(),entered=wait(),release=wait();
  p.t.hook(c=>c.path==='/api/estadisticas'?{status:200,ok:true,headers:{get:()=>null},json:async()=>{entered.resolve();await release.promise;return facts(true,true);}}:null);
  const pending=p.t.context.initDashboard();await entered.promise;
  if(boundary==='storage')p.t.emit({type:'storage',key:'mb_session_epoch'});
  if(boundary==='broadcast')p.t.channel.onmessage({data:{epoch:'SYNTHETIC-DIFFERENT-EPOCH'}});
  if(boundary==='pagehide')p.t.emit({type:'pagehide'});
  if(boundary==='bfcache')p.t.emit({type:'pageshow',persisted:true});
  if(boundary==='epoch-only')p.world.disk.set('mb_session_epoch','SYNTHETIC-DIFFERENT-EPOCH');
  release.resolve();await pending;await tick();
  assert.equal(p.t.api.getToken(),'');assert.equal(p.nodes.has('onboarding-section'),false);
  assert.equal(p.main.children[0].attributes.role,'status');assert.equal(p.world.calls.filter(c=>c.path==='/api/estadisticas').length,1);
});
test('Storage failure while dashboard JSON is pending discards old actor and its preparation',async()=>{
  const p=await dashboard(),entered=wait(),release=wait();p.t.hook(c=>c.path==='/api/estadisticas'?{status:200,ok:true,headers:{get:()=>null},json:async()=>{entered.resolve();await release.promise;return facts(true,true);}}:null);
  const pending=p.t.context.initDashboard();await entered.promise;p.t.sandbox.localStorage.getItem=()=>{throw Error('SYNTHETIC PRIVATE STORAGE DETAIL');};release.resolve();await pending;await tick();
  assert.equal(p.t.api.getToken(),'');assert.equal(p.nodes.has('onboarding-section'),false);assert.ok(p.toasts.every(x=>!x.includes('PRIVATE')));
});
test('failed statistics query replaces stale confirmation with unknown without storage writes',async()=>{
  const p=await dashboard();p.t.context.updateOnboarding(facts(true,true));p.t.hook(c=>c.path==='/api/estadisticas'?response({detail:{code:'statistics_unavailable',message:'SYNTHETIC PRIVATE QUERY DETAIL'}},503):null);
  const before=p.world.writes.length;await p.t.context.initDashboard();incomplete(p);assert.equal(p.world.writes.length,before);assert.ok(p.toasts.every(x=>!x.includes('PRIVATE')));assert.equal(p.world.calls.filter(c=>c.path==='/api/estadisticas').length,1);
});
test('a second tab selecting another actor removes the first guide without adopting its response',async()=>{
  const p=await dashboard(),other=p.world.tab();await other.api.session.ready;
  const entered=wait(),release=wait();p.t.hook(c=>c.path==='/api/estadisticas'?{status:200,ok:true,headers:{get:()=>null},json:async()=>{entered.resolve();await release.promise;return facts(true,true);}}:null);
  const pending=p.t.context.initDashboard();await entered.promise;await other.api.auth.registro({});release.resolve();await pending;await tick();assert.equal(p.nodes.has('onboarding-section'),false);assert.equal(p.t.api.getToken(),'');assert.match(other.api.getToken(),/^SEC-B-/);assert.equal(p.world.calls.filter(c=>c.path==='/api/estadisticas').length,1);
});

const complete={id:'A',nombre:'Synthetic peer personal',tipo:'usuario',role:'owner',team_gym_id:null,session_version:1,peso_kg:70,estatura_cm:170,edad:30,objetivo:'mantenimiento',restricciones_nutricionales:{}};
async function personal(profile=complete,hook=null){
  const world=environment(),t=world.tab();await t.api.session.ready;
  const ids=[...personalMarkup.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);const d=dom(t.sandbox,[...ids,'sb-nombre','sb-avatar']);
  const ancillary=[];t.sandbox.PersonalDiary={mountPlan:()=>({async bootstrap(){ancillary.push('diary bootstrap double');},invalidate(){ancillary.push('diary invalidated');}})};
  t.sandbox.PlanDayUI={mount:()=>({invalidate(){ancillary.push('shopping invalidated');}})};
  t.sandbox.Nutrition35={renderSummary(){},assertAutomated(){},error:code=>Object.assign(new Error(code),{code})};
  t.hook(c=>{const out=hook?.(c);if(out)return out;if(c.path==='/api/auth/me')return response({...profile});if(c.path==='/api/usuario/perfil')return response({...profile});if(c.path==='/api/usuario/mi-plan')return response({plan:{}});return null;});
  vm.runInContext(fs.readFileSync('web/static/js/usuario-plan-operacion.js','utf8'),t.context);
  const pending=vm.runInContext(personalSource[0],t.context);return {world,t,...d,ancillary,pending};
}
for(const field of ['peso_kg','estatura_cm','edad','objetivo'])test('personal missing '+field+' exposes profile only using the actual controller/API',async()=>{
  const p=await personal({...complete,[field]:null});await p.pending;
  assert.equal(p.nodes.get('onboarding-card').style.display,'flex');assert.equal(p.nodes.get('quick-actions').style.display,'none');
  assert.equal(p.world.calls.some(c=>c.path==='/api/usuario/mi-plan'),false);assert.equal(p.world.calls.some(c=>c.options.method&&c.options.method!=='GET'&&c.path!=='/api/auth/refresh'),false);
  assert.equal(p.nodes.get('btn-generar').listenerCount('click'),0);assert.match(personalMarkup,/<a href="\/mi-perfil"[^>]*>Configurar mi plan/);
});
test('complete personal profile preserves explicit readers and wires controls without generating',async()=>{
  const p=await personal();await p.pending;assert.notEqual(p.nodes.get('onboarding-card').style.display,'flex');assert.equal(p.nodes.get('quick-actions').style.display,'');assert.equal(p.nodes.get('btn-generar').listenerCount('click'),1);assert.equal(p.world.calls.filter(c=>c.path==='/api/usuario/mi-plan').length,1);assert.ok(p.world.calls.every(c=>c.path==='/api/auth/refresh'||c.options.method==='GET'));
});
for(const boundary of ['pagehide','storage','subject-version'])test('late incomplete personal profile cannot reopen guide after '+boundary,async()=>{
  const entered=wait(),release=wait();let version=1;
  const p=await personal({...complete,peso_kg:null},c=>{
    if(c.path==='/api/auth/me')return response({...complete,peso_kg:null,session_version:version});
    if(c.path==='/api/usuario/perfil')return {status:200,ok:true,headers:{get:()=>null},json:async()=>{entered.resolve();await release.promise;return {...complete,peso_kg:null};}};
    return null;
  });await entered.promise;
  if(boundary==='subject-version')version=2;else p.t.emit({type:boundary,key:'mb_session_epoch'});
  release.resolve();await p.pending;assert.equal(p.nodes.get('onboarding-card').style.display,'none');assert.equal(p.nodes.get('quick-actions').style.display,'none');assert.equal(p.world.calls.some(c=>c.path==='/api/usuario/mi-plan'),false);assert.equal(p.world.calls.some(c=>c.path==='/api/usuario/generar-plan'),false);
});
test('personal copy does not promise three fields and keeps the real profile link',()=>{assert.doesNotMatch(personalMarkup,/Solo necesitamos 3 datos/);assert.match(personalMarkup,/Completa los campos requeridos/);assert.match(personalMarkup,/<a href="\/mi-perfil"[^>]*>Configurar mi plan/);});

(async()=>{const rows=[];for(const entry of tests){try{await entry.run();rows.push({case:entry.name,passed:true});}catch(error){rows.push({case:entry.name,passed:false,error_class:error.name,code:typeof error.code==='string'?error.code:null,site:String(error.stack).split('\n').find(line=>line.trimStart().startsWith('at '))});}}process.stdout.write(JSON.stringify({scope:'Actual dashboard/API/session shell and personal inline/controller in VM; minimal DOM, ancillary and transport/Cookie/WebLock doubles. No native browser, HTTP or human usability acceptance.',total:rows.length,passed:rows.filter(x=>x.passed).length,rows},null,2)+'\n');if(rows.some(x=>!x.passed))process.exitCode=1;})().catch(()=>{process.exitCode=1;});
