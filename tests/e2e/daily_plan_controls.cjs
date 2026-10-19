/* Mounted R24 consumer with a minimal DOM and in-memory transport. Not HTTP/browser evidence. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const base=path.resolve(__dirname,'../..'),clone=value=>JSON.parse(JSON.stringify(value));
const flush=async()=>{for(let n=0;n<20;n++)await Promise.resolve();};
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};};
class Element{
 constructor(tag='div',id=''){Object.assign(this,{tagName:tag.toUpperCase(),id,children:[],listeners:{},dataset:{},attributes:{},value:'',disabled:false,hidden:false,checked:false,_text:''});}
 set textContent(value){this._text=String(value);this.children=[];}get textContent(){return this._text+this.children.map(child=>child.textContent).join(' ');}
 append(child){this.children.push(child);}replaceChildren(...children){this.children=children;this._text='';}
 setAttribute(name,value){this.attributes[name]=value;}focus(){this.focused=true;}
 addEventListener(name,callback){(this.listeners[name]||=[]).push(callback);}
 all(){return this.children.flatMap(child=>[child,...child.all()]);}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
 querySelectorAll(selector){
  const parts=selector.split(' ');if(parts.length>1){const root=this.querySelector(parts[0]);return root?root.querySelectorAll(parts.slice(1).join(' ')):[];}
  return this.all().filter(item=>selector.split(',').some(part=>part[0]==='#'?item.id===part.slice(1):part==='[data-remove-consumed]'?item.dataset.removeConsumed!==undefined:item.tagName.toLowerCase()===part));
 }
 async fire(name){if(this.disabled)return;for(const callback of this.listeners[name]||[])await callback({target:this});}
}
function fixture(options={}){
 const root=new Element('section','plan-shopping'),map={},events={};
 const controls={'shopping-start':'input','shopping-end':'input','shopping-build':'button','shopping-read-recorded':'button','publication-diary-day':'input','publication-diary-meal':'select','publication-diary-save':'button','publication-diary-reload':'button','publication-diary-retry':'button','publication-diary-discard':'button'};
 const publication=new Element('section','publication-consumption');root.append(publication);map[publication.id]=publication;
 for(const id of ['shopping-status','shopping-items','shopping-recorded-items','shopping-recorded-status','shopping-meals','plan-source-label','shopping-recorded-section',...Object.keys(controls),'publication-diary-status','publication-diary-records']){
  const item=new Element(controls[id]||'div',id);map[id]=item;(id.startsWith('publication-')?publication:root).append(item);
 }
 map['publication-diary-meal'].value='desayuno';
 const calls=[],zero={kcal:0,protein_g:0,carbs_g:0,fat_g:0};let valid=true,checks=0,readSource=async()=>clone(source),readRecorded=async()=>({days:[]});
 const day={local_date:'2026-10-19',today:'2026-10-19',timezone:'America/Mexico_City',version:0,water_ml:0,meals:{},totals:zero};
 const source={key:'publication:one',label:'Synthetic exact source',link_id:'00000000-0000-0000-0000-000000000001',publication_id:'00000000-0000-0000-0000-000000000002',link_version:2,publication_version:1,
  plan:Object.fromEntries(['desayuno','almuerzo','comida','cena'].map(name=>[name,{alimentos:{huevo:25.5}}]))};
 const failure=()=>Object.assign(new Error('Context replaced'),{code:'session_changed'});
 const context={check(){checks++;options.onCheck?.(checks,()=>{valid=false;});if(!valid)throw failure();},async read(task){this.check();const value=await task();this.check();return value;}};
 const Api={usuario:{validarContexto:()=>context.check(),contexto:async()=>{calls.push('context');return{revision:1};},verificarContexto:async()=>{context.check();return{};},
  diarioHoy:async()=>{calls.push('bootstrap');return{today:day.today,timezone:day.timezone,days:[clone(day)]};},diarioDia:async()=>{calls.push('day');return clone(day);},guardarDiario:async(_date,body)=>{calls.push(clone(body));return{...clone(day),version:body.expected_version+1};}}};
 const window={addEventListener:(name,callback)=>(events[name]||=[]).push(callback)};
 const sandbox=vm.createContext({window,Api,Intl,Date,setTimeout,clearTimeout,document:{createElement:tag=>new Element(tag)}});
 for(const file of ['plan-diario-datos.js','plan-diario-ui.js','usuario-diario.js','plan-publicacion-consumo.js']){
  vm.runInContext(fs.readFileSync(path.join(base,'web/static/js',file),'utf8'),sandbox);for(const name of ['PlanDayData','PlanDayUI','PersonalDiary','PublicationConsumption'])if(window[name])sandbox[name]=window[name];
 }
 let unavailable=0;const shopping=window.PlanDayUI.mount({root,context,readSource:()=>readSource(),readRecorded:()=>readRecorded(),onSourceUnavailable:()=>unavailable++});shopping.setSource(clone(source),day.today);
 return{root,map,shopping,source,context,Api,calls,sandbox,day,
  change(){valid=false;for(const handler of events['metodobase-session-changed']||[])handler({});},
  setReader(fn){readSource=fn;},setRecorded(fn){readRecorded=fn;},get unavailable(){return unavailable;},
  widget(canRecord=true){return window.PublicationConsumption.mount({root,scope:context,shopping,canRecord});},
  choose(meal='desayuno'){return map['shopping-meals'].querySelectorAll('input').find(input=>input.dataset.meal===meal);}};
}
const tests=[];const test=(name,body)=>tests.push({name,body});
test('Opening the source selects nothing, creates no consumption, and retains real decimal grams',()=>{const e=fixture();assert.equal(e.choose().checked,false);assert.match(e.map['shopping-meals'].textContent,/25\.5 g/);assert.equal(e.calls.length,0);});
test('An explicit selection and period prepare only a shopping draft',async()=>{const e=fixture();e.choose().checked=true;await e.choose().fire('change');e.map['shopping-end'].value='2026-10-21';await e.map['shopping-build'].fire('click');assert.match(e.map['shopping-items'].textContent,/76\.5 g/);assert.match(e.map['shopping-status'].textContent,/3 días/);assert.equal(e.calls.length,0);});
test('Canonical catalog confirmation merges only equal identities, preserving selections',async()=>{const e=fixture();for(const name of ['desayuno','cena']){e.choose(name).checked=true;await e.choose(name).fire('change');}e.shopping.setCatalog(['huevo']);await e.map['shopping-build'].fire('click');assert.equal(e.map['shopping-items'].children.length,1);assert.match(e.map['shopping-items'].textContent,/51 g/);assert.equal(e.choose().checked,true);});
test('Equal unverified labels stay separate lines',async()=>{const e=fixture();for(const name of ['desayuno','cena']){e.choose(name).checked=true;await e.choose(name).fire('change');}await e.map['shopping-build'].fire('click');assert.equal(e.map['shopping-items'].children.length,2);});
test('Replacement during a retained source response clears selectors and does not render a draft',async()=>{const e=fixture(),gate=deferred();e.setReader(()=>gate.promise);const pending=e.map['shopping-build'].fire('click');e.change();gate.resolve(clone(e.source));await pending;assert.equal(e.map['shopping-items'].textContent,'');assert.equal(e.map['shopping-meals'].textContent,'');assert.equal(e.shopping.source,null);});
test('Withdrawal is visible and clears cached source rather than using an old DTO',async()=>{const e=fixture();e.setReader(async()=>{throw Object.assign(new Error('Unavailable'),{status:404});});await e.map['shopping-build'].fire('click');assert.equal(e.shopping.source,null);assert.equal(e.unavailable,1);assert.equal(e.map['shopping-items'].textContent,'');});
test('Publication replacement requires a new explicit selection',async()=>{const e=fixture();e.setReader(async()=>({...clone(e.source),key:'different-publication'}));await e.map['shopping-build'].fire('click');assert.equal(e.shopping.source,null);assert.equal(e.unavailable,1);assert.equal(e.map['shopping-meals'].textContent,'');});
test('Recorded totals use snapshots and never the displayed menu',async()=>{const e=fixture();e.setRecorded(async()=>({days:[{local_date:'2026-10-19',meals:{cena:{foods:[{food_id:'arroz',grams:17.25}],completed:false}}}]}));await e.map['shopping-read-recorded'].fire('click');assert.match(e.map['shopping-recorded-items'].textContent,/arroz.*17\.25 g/);assert.equal(e.map['shopping-items'].textContent,'');assert.equal(e.calls.length,0);});
test('A failed recorded query exposes an error instead of an empty successful list',async()=>{const e=fixture();e.setRecorded(async()=>{throw Error('Offline');});await e.map['shopping-read-recorded'].fire('click');assert.match(e.map['shopping-recorded-status'].textContent,/No se pudo consultar/);assert.equal(e.map['shopping-recorded-items'].textContent,'');});
test('A context failure inside controls cannot overwrite invalidated status or dispatch',async()=>{let armed=false;const e=fixture({onCheck(_n,invalidate){if(armed)invalidate();}});armed=true;await e.map['shopping-build'].fire('click');assert.equal(e.shopping.source,null);assert.match(e.map['shopping-status'].textContent,/cambió/);assert.equal(e.calls.length,0);});
test('Reader-only OWNER capability never requests or adopts a personal diary',async()=>{const e=fixture();e.widget(false);await flush();assert.equal(e.calls.length,0);assert.equal(e.map['publication-diary-save'].disabled,true);assert.match(e.map['publication-diary-status'].textContent,/no crea un espacio personal/);});
test('Personal context bootstrap failure leaves all diary actions disabled',async()=>{const e=fixture();e.Api.usuario.contexto=async()=>{throw Error('Unavailable');};e.widget();await flush();assert.equal(e.map['publication-diary-reload'].disabled,true);assert.equal(e.map['publication-diary-save'].disabled,true);assert.equal(e.map['publication-diary-meal'].disabled,true);assert.equal(e.calls.length,0);});
test('Publication consumption uses current exact IDs and diary CAS only after an explicit click',async()=>{const e=fixture();e.widget();await flush();assert.deepEqual(e.calls,['context','bootstrap']);e.choose().checked=true;await e.choose().fire('change');await e.map['publication-diary-save'].fire('click');const body=e.calls.find(value=>typeof value==='object');assert.equal(body.operation,'publication_meal');assert.equal(body.link_id,e.source.link_id);assert.equal(body.publication_id,e.source.publication_id);assert.equal(body.expected_link_version,2);assert.equal(body.expected_publication_version,1);assert.equal(body.expected_version,0);assert.equal(body.selections.include_fixed_menu,true);});
test('A late personal context response cannot expose old personal snapshots',async()=>{const e=fixture(),gate=deferred();e.Api.usuario.contexto=()=>gate.promise;e.widget();e.change();gate.resolve({revision:1});await flush();assert.equal(e.map['publication-diary-records'].textContent,'');assert.equal(e.calls.includes('bootstrap'),false);});
test('Two rapid publication-save actions during source validation cannot register twice',async()=>{const e=fixture(),first=deferred(),second=deferred();e.widget();await flush();e.choose().checked=true;await e.choose().fire('change');let reads=0;e.setReader(()=>++reads===1?first.promise:second.promise);const one=e.map['publication-diary-save'].fire('click'),two=e.map['publication-diary-save'].fire('click');first.resolve(clone(e.source));await one;second.resolve(clone(e.source));await two;assert.equal(e.calls.filter(value=>typeof value==='object').length,1);});
test('Publication source validation captures the clicked selection and disables day changes',async()=>{const e=fixture(),gate=deferred();e.widget();await flush();e.choose().checked=true;await e.choose().fire('change');e.setReader(()=>gate.promise);const pending=e.map['publication-diary-save'].fire('click');assert.equal(e.map['publication-diary-day'].disabled,true);e.choose().checked=false;await e.choose().fire('change');gate.resolve(clone(e.source));await pending;assert.equal(e.calls.find(value=>typeof value==='object').selections.include_fixed_menu,true);assert.equal(e.map['publication-diary-day'].disabled,false);});
test('An empty publication date restores the observed date with visible error and no write',async()=>{const e=fixture();e.widget();await flush();e.map['publication-diary-day'].value='';await e.map['publication-diary-day'].fire('change');assert.equal(e.map['publication-diary-day'].value,e.day.today);assert.match(e.map['publication-diary-status'].textContent,/No se cambió el día/);assert.equal(e.calls.filter(value=>typeof value==='object').length,0);});
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,error:error.stack});}}console.log(JSON.stringify({scope:'Minimal DOM and memory transport only; no HTTP claim',passed:results.filter(value=>value.passed).length,total:results.length,results},null,2));if(results.some(value=>!value.passed))process.exitCode=1;})();
