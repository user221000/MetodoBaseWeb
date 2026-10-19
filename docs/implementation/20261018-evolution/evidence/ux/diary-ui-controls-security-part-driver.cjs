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
  return{api,blobUrls,timers,values,nodes,get,window,document,context,downloads,requests,redirects,counts,
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
async function prepareMore(env){env.setTransport(async()=>Response.json(exportPage(meA.id,[diaryRecord()],'2026-10-19')));env.get('privacy-start').click();await flush();assert.equal(env.downloads.length,1);assert.equal(env.get('privacy-next').hidden,false);}
for(const [prepared,button]of [[false,'privacy-start'],[true,'privacy-next']]){
 for(const mode of ['account','storage'])test((prepared?'Next part':'First part')+' preserves invalidation status after controls detects '+mode,async()=>{
  const env=await privacyFixture();if(prepared)await prepareMore(env);
  const before=env.requests.length,downloads=env.downloads.length;
  if(mode==='account'){env.api.saveTokens(B);env.setMe(meB);}
  else env.setStorageHook((operation,key)=>{if(operation==='get'&&key==='mb_token'){const error=Error('SYNTHETIC_PRIVATE_PART_STORAGE');error.name='SecurityError';throw error;}});
  const statusWrites=[];env.setTextHook((node,text)=>{if(node.id==='privacy-status')statusWrites.push(text);});
  env.get(button).click();await flush();
  assert.equal(env.requests.length,before);assert.equal(env.downloads.length,downloads);assert.equal(env.blobUrls.size,0);
  assert.equal(env.get('privacy-start').disabled,true);assert.equal(env.get('privacy-next').disabled,true);assert.equal(env.get('privacy-again').hidden,true);
  assert.equal(env.get('privacy-error').hidden,false);assert.ok(!env.get('privacy-error').textContent.includes('SYNTHETIC_PRIVATE_PART_STORAGE'));
  assert.ok(env.get('privacy-status').textContent.includes('no se pudo confirmar'));
  assert.ok(statusWrites.every(text=>!text.startsWith('Consultando')),'a closed context must not resume the consulting status');
  for(const node of env.counts.values())assert.equal(node.textContent,'0');env.legacyIntact();
  observations.push({button,mode,statusWrites,new_requests:env.requests.length-before,new_downloads:env.downloads.length-downloads,cache_urls:env.blobUrls.size});
 });
}
(async()=>{const results=[];for(const entry of cases){try{await entry.run();results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,error:error.message});}}
 const sourceAfter=Object.fromEntries(files.map(name=>[name,sha(fs.readFileSync(path.join(root,name)))]));assert.deepEqual(sourceAfter,sourceBefore);
 const record={scope:'Independent part(true)/part(false) guard probes with real UI/API code and synthetic VM DOM/Storage/transport; no browser or network claim',sourceBefore,sourceAfter,sources_stable:true,driver_sha256:sha(fs.readFileSync(__filename)),total:results.length,passed:results.filter(row=>row.passed).length,results,observations};
 fs.writeFileSync(path.join(out,'part-probes.json'),JSON.stringify(record,null,2)+'\n');console.log(JSON.stringify(record,null,2));if(record.passed!==record.total)process.exitCode=1;
})().catch(error=>{console.error(error.stack);process.exitCode=2;});
