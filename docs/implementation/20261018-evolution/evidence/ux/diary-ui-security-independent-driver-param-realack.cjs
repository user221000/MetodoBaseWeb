'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=process.env.DIARY_UI_SOURCE_ROOT || 'F:/MetodoBaseWeb-diary-ui-20261019';
const out=process.env.DIARY_UI_REVIEW_OUTPUT || path.join(__dirname,'runs',String(Date.now()));
fs.mkdirSync(out,{recursive:true});
const files=['web/static/js/api.js','web/static/js/usuario-diario.js','web/static/js/usuario-privacidad.js','web/static/js/usuario-plan-operacion.js','web/templates/base_usuario.html'];
const sources=Object.fromEntries(files.map(name=>[name,fs.readFileSync(path.join(root,name),'utf8')]));
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const sourceBefore=Object.fromEntries(files.map(name=>[name,sha(fs.readFileSync(path.join(root,name)))]));
const A={token:'synthetic-independent-A',refresh_token:'synthetic-independent-refresh-A'};
const B={token:'synthetic-independent-B',refresh_token:'synthetic-independent-refresh-B'};
const meA={id:'synthetic-subject-A',tipo:'usuario',role:'viewer',team_gym_id:null,session_version:0};
const meB={...meA,id:'synthetic-subject-B'};
const legacy=new Map(['mb_daily_2026-01-01','mb_water_2026-01-01','mb_meals_2026-01-01','mb_meals_done_2026-01-01'].map((name,i)=>[name,'Synthetic unidentified bytes '+i+'\u0000{not JSON']));
const clone=value=>JSON.parse(JSON.stringify(value));
const zero=()=>({kcal:0,protein_g:0,carbs_g:0,fat_g:0});
const day=(date='2026-10-19')=>({local_date:date,today:'2026-10-19',timezone:'America/Mexico_City',version:0,water_ml:0,meals:{},totals:zero(),created_at:null,updated_at:null});
const defer=()=>{let resolve;return{promise:new Promise(r=>resolve=r),resolve:value=>resolve(value)};};
const flush=async()=>{for(let i=0;i<18;i++)await new Promise(resolve=>setImmediate(resolve));};

function fixture(){
  const values=new Map([...legacy,['mb_token',A.token],['mb_refresh_token',A.refresh_token]]),nodes=new Map(),events=new Map(),downloads=[],blobUrls=new Map(),requests=[],redirects=[];
  let api,storageHook=null,textHook=null,me=clone(meA),id=0,handler=async()=>{throw Error('Unknown synthetic endpoint');};
  class Element{
    constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.style={};this.dataset={};this.listeners=new Map();this.hidden=false;this.disabled=false;this.value='';this._text='';this.attributes={};this.classList={add(){},remove(){},toggle(){},contains(){return false;}};}
    get textContent(){return this._text+this.children.map(child=>typeof child==='string'?child:child.textContent).join('');}
    set textContent(value){this._text=String(value??'');this.children=[];textHook?.(this,this._text);}
    set innerHTML(value){throw Error('Independent DOM sentinel: dynamic HTML assignment is forbidden');}
    append(...items){this.children.push(...items);}
    appendChild(item){this.children.push(item);return item;}
    replaceChildren(...items){this._text='';this.children=[...items];}
    remove(){}
    after(item){if(item.id)nodes.set(item.id,item);}
    focus(){}
    setAttribute(name,value){this.attributes[name]=String(value);}
    getAttribute(name){return this.attributes[name];}
    closest(){return this;}
    querySelector(selector){if(selector.startsWith('[data-export-count='))return counts.get(selector.match(/"([^"]+)"/)[1]);return null;}
    querySelectorAll(selector){return [];}
    addEventListener(name,fn){const list=this.listeners.get(name)||[];list.push(fn);this.listeners.set(name,list);}
    click(){if(this.tagName==='A' && this.download){downloads.push({blob:blobUrls.get(this.href),name:this.download,credential:values.get('mb_token')});return;}return this.listeners.get('click')?.[0]?.({target:this});}
  }
  const get=id=>{if(!nodes.has(id)){const node=new Element();node.id=id;nodes.set(id,node);}return nodes.get(id);};
  const counts=new Map(['profiles','plans','measurements','purchases','generation_requests','personal_diary'].map(name=>[name,new Element('dd')]));
  const storage={getItem(key){if(legacy.has(key))throw Error('Unidentified legacy must not be read');storageHook?.('get',key);return values.get(key)||null;},setItem(key,value){if(legacy.has(key))throw Error('Legacy must not be written');storageHook?.('set',key);values.set(key,String(value));},removeItem(key){if(legacy.has(key))throw Error('Legacy must not be removed');values.delete(key);storageHook?.('remove',key);},clear(){throw Error('Storage.clear is forbidden');}};
  const window={location:{pathname:'/mi-perfil',href:'',replace(value){redirects.push(value);}},addEventListener(name,fn){const list=events.get(name)||[];list.push(fn);events.set(name,list);},removeEventListener(){},dispatchEvent(event){for(const fn of events.get(event.type)||[])fn(event);},SessionIdentity:{ready:Promise.resolve(me)}};
  const document={getElementById:get,createElement:tag=>new Element(tag),createTextNode:text=>String(text),body:new Element('body')};
  const timers=new Map();
  class LocalURL extends URL{static createObjectURL(blob){const url='blob:synthetic/'+(++id);blobUrls.set(url,blob);return url;}static revokeObjectURL(url){blobUrls.delete(url);}}
  const context=vm.createContext({localStorage:storage,window,document,SessionIdentity:window.SessionIdentity,CustomEvent:function(type,options){this.type=type;this.detail=options?.detail;},
    fetch:async(url,options)=>{requests.push({url,method:options.method,authorization:options.headers?.Authorization});if(url==='/api/auth/me')return Response.json(me);return handler(url,options);},
    File,FormData,Blob,URL:LocalURL,URLSearchParams,Date,crypto:{randomUUID:()=>`00000000-0000-4000-8000-${String(++id).padStart(12,'0')}`},setTimeout:(fn,ms)=>{timers.set(++id,{fn,ms});return id;},clearTimeout:key=>timers.delete(key)});
  vm.runInContext(sources['web/static/js/api.js']+'\nglobalThis.api=Api;',context);api=context.api;
  return{api,values,nodes,get,window,document,context,downloads,requests,redirects,counts,
    load(name){vm.runInContext(sources[name],context);},eval(code){return vm.runInContext(code,context);},setMe(value){me=clone(value);},setTransport(fn){handler=fn;},
    setStorageHook(fn){storageHook=fn;},setTextHook(fn){textHook=fn;},legacyIntact(){for(const [key,value]of legacy)assert.equal(values.get(key),value);},
    loadLogout(){const template=sources['web/templates/base_usuario.html'],start=template.indexOf('  // Logout'),end=template.indexOf('\n})();',start);assert.ok(start>0 && end>start);vm.runInContext('(function(){'+template.slice(start,end)+'})();',context);},
  };
}

function exportPage(account=meA.id,records=[],after=null){return{format_version:1,exported_at:'2026-10-19T12:00:00+00:00',account:{id:account},
  personal_subscription:null,canonical_subscription:null,scope:{consistency:'live_keyset_pages',coverage:'account_and_persisted_personal_space',personal_space:true,professional_membership:false,page_size:100,excluded_categories:['credentials_and_tokens']},
  ...Object.fromEntries(['profiles','plans','measurements','purchases','generation_requests','personal_diary'].map(name=>[name,{records:name==='personal_diary'?records:[],next_after:name==='personal_diary'?after:null}]))};}
const diaryRecord=(date='2026-10-19')=>({id:'10000000-0000-4000-8000-000000000001',local_date:date,water_ml:789,meals:{},version:1});
async function privacyFixture(){const env=fixture();env.load('web/static/js/usuario-privacidad.js');await flush();return env;}
const cases=[],observations=[];
function test(name,run){cases.push({name,run});}

for(const response of [{success:false},{}])test('Logout does not claim server revocation for '+JSON.stringify(response),async()=>{
  const env=fixture();env.setTransport(async()=>Response.json(response));const result=await env.api.auth.logout();
  observations.push({case:'logout_response_shape',response,state:result.state,server_confirmed:result.server_confirmed});
  assert.equal(result.state,'closed_local');assert.equal(result.server_confirmed,false);env.legacyIntact();
});
test('New B during first credential removal survives helper and handler',async()=>{
  const env=fixture();env.setTransport(async()=>Response.json({message:'Sesión cerrada. Todas las sesiones revocadas.'}));env.loadLogout();let switched=false;
  env.setStorageHook((operation,key)=>{if(!switched && operation==='remove' && key==='mb_token'){switched=true;env.api.saveTokens(B);}});
  await env.get('btn-logout').click();assert.equal(env.values.get('mb_token'),B.token);assert.equal(env.values.get('mb_refresh_token'),B.refresh_token);assert.equal(env.redirects.length,0);
  env.setStorageHook(null);env.setMe(meB);assert.equal((await env.api.auth.me()).id,meB.id);env.legacyIntact();
});
test('B reentry during success notice is checked again before redirect',async()=>{
  const env=fixture();env.setTransport(async()=>Response.json({message:'Sesión cerrada. Todas las sesiones revocadas.'}));env.loadLogout();let switched=false;
  env.setTextHook((node,text)=>{if(!switched && text==='Sesión cerrada en este navegador.'){switched=true;env.api.saveTokens(B);}});
  await env.get('btn-logout').click();assert.equal(switched,true);assert.equal(env.values.get('mb_token'),B.token);assert.equal(env.redirects.length,0);env.legacyIntact();
});
test('Same account role or session-version change invalidates canonical personal context',async()=>{
  for(const next of [{...meA,role:'owner'},{...meA,session_version:1}]){const env=fixture(),personal=await env.api.usuario.contexto();env.setMe(next);
    await assert.rejects(env.api.usuario.verificarContexto(personal),error=>error.code==='session_changed');env.legacyIntact();}
});
test('Private export A response after same-tab B replacement is never downloaded',async()=>{
  const env=await privacyFixture();env.setTransport(async()=>Response.json(exportPage(meA.id,[diaryRecord()])));
  env.eval(`const originalExport=Api.usuario.exportarDatos;Api.usuario.exportarDatos=async(...args)=>{const result=await originalExport(...args);Api.saveTokens(${JSON.stringify(B)});return result;};`);
  env.get('privacy-start').click();await flush();
  const data=env.downloads[0] ? JSON.parse(await env.downloads[0].blob.text()) : null;
  observations.push({case:'export_A_after_B',downloads:env.downloads.length,current_is_B:env.values.get('mb_token')===B.token,download_account:data?.account?.id||null});
  assert.equal(env.values.get('mb_token'),B.token);assert.equal(env.downloads.length,0);env.legacyIntact();
});
test('Private export reacts to explicit session-change event by discarding prepared file',async()=>{
  const env=await privacyFixture();env.setTransport(async()=>Response.json(exportPage(meA.id,[diaryRecord()])));
  env.get('privacy-start').click();await flush();assert.equal(env.downloads.length,1);
  env.window.dispatchEvent({type:'metodobase-session-changed',detail:{code:'session_storage_error',message:'Synthetic session unavailable'}});
  observations.push({case:'export_session_event',repeat_button_hidden:env.get('privacy-again').hidden,diary_count:env.counts.get('personal_diary').textContent});
  assert.equal(env.get('privacy-again').hidden,true);assert.equal(env.counts.get('personal_diary').textContent,'0');env.legacyIntact();
});
test('Diary export date cursor rejects repeated exclusive boundary without producing new file',async()=>{
  const env=await privacyFixture();let part=0;
  env.setTransport(async()=>Response.json(exportPage(meA.id,[diaryRecord('2026-10-18')],part++===0?'2026-10-18':null)));
  env.get('privacy-start').click();await flush();assert.equal(env.downloads.length,1);
  env.get('privacy-next').click();await flush();assert.equal(env.downloads.length,1);assert.equal(env.get('privacy-error').hidden,false);env.legacyIntact();
});
test('Diary read after helper-to-consumer B switch clears state before view',async()=>{
  const env=fixture();env.setTransport(async()=>Response.json({today:'2026-10-19',timezone:'America/Mexico_City',days:[day()]}));
  env.load('web/static/js/usuario-plan-operacion.js');env.load('web/static/js/usuario-diario.js');
  env.eval(`globalThis.views=[];globalThis.personal=window.PersonalPlanOperation.create();`);await env.context.personal.start();
  env.eval(`const originalToday=Api.usuario.diarioHoy;Api.usuario.diarioHoy=async(...args)=>{const result=await originalToday(...args);Api.saveTokens(${JSON.stringify(B)});return result;};globalThis.diary=window.PersonalDiary.create({personal,onView:day=>views.push(day)});`);
  await env.context.diary.bootstrap();assert.equal(env.context.diary.day,null);assert.equal(env.context.diary.state,'invalidated');assert.equal(env.context.views.length,0);env.legacyIntact();
});
test('Malformed diary read never exposes preceding snapshot or invalidates a replacement account',async()=>{
  const env=fixture();let malformed=false;env.setTransport(async()=>Response.json({today:'2026-10-19',timezone:'America/Mexico_City',days:[malformed?{...day(),totals:{kcal:999}}:day()]}));
  env.load('web/static/js/usuario-plan-operacion.js');env.load('web/static/js/usuario-diario.js');
  env.eval('globalThis.personal=window.PersonalPlanOperation.create();');await env.context.personal.start();
  env.eval('globalThis.views=[];globalThis.diary=window.PersonalDiary.create({personal,onView:value=>views.push(value)});');await env.context.diary.bootstrap();
  malformed=true;await env.context.diary.bootstrap();assert.equal(env.context.diary.day,null);assert.equal(env.context.diary.state,'error');assert.equal(env.context.personal.active,true);env.legacyIntact();
});

(async()=>{
  const results=[];
  for(const entry of cases){try{await entry.run();results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,error:error.message});}}
  const sourceAfter=Object.fromEntries(files.map(name=>[name,sha(fs.readFileSync(path.join(root,name)))]));assert.deepEqual(sourceAfter,sourceBefore);
  const record={scope:'Independent VM Storage/transport/DOM doubles only, exact UI606f3c6; no browser/network/backend/PG claim',
    sourceBefore,sourceAfter,sources_stable:true,driver_sha256:sha(fs.readFileSync(__filename)),total:results.length,passed:results.filter(row=>row.passed).length,results,observations};
  fs.writeFileSync(path.join(out,'results-before.json'),JSON.stringify(record,null,2)+'\n');
  console.log(JSON.stringify(record,null,2));if(record.passed!==record.total)process.exitCode=1;
})().catch(error=>{console.error(error.stack);process.exitCode=2;});
