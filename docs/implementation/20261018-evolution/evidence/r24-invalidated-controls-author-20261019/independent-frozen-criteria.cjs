/* Independent criteria; author's minimal DOM fixture reused with coordinate/event hooks only. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),crypto=require('node:crypto');
const root=path.resolve(process.env.R24_REVIEW_ROOT||'F:/mb-r24-sec');
const fixturePath=path.join(root,'tests/e2e/daily_plan_controls.cjs');
const raw=fs.readFileSync(fixturePath,'utf8').replace('n<20;n++','n<200;n++'), marker='const tests=[];';
if(raw.split(marker).length!==2)throw Error('Unexpected frozen fixture');
const prefix=raw.split(marker)[0].replace("path.resolve(__dirname,'../..')",JSON.stringify(root))
 .replace('return{root,map,shopping,source,context,Api,calls,sandbox,day,','return{root,map,shopping,source,context,Api,calls,sandbox,day, emit(name,event={}){for(const handler of events[name]||[])handler(event);},');
const extra=String.raw`

async function integratedFixture(options={}){
 const e=fixture(options), oldCheck=e.context.check.bind(e.context);let mounted;
 e.Api.vinculos={contexto:async()=>({revision:1,me:{id:'synthetic-person'}}),validarContexto:oldCheck,verificarContexto:async()=>{oldCheck();}};
 vm.runInContext(fs.readFileSync(path.join(base,'web/static/js/vinculos-contexto.js'),'utf8'),e.sandbox);
 const actual=e.sandbox.window.MemberLinkContext.create();await actual.start();
 const scoped=actual.scope(()=>{e.shopping.invalidate();mounted?.invalidate();});
 e.context.check=()=>scoped.check();e.context.read=task=>scoped.read(task);
 const original=e.widget;e.widget=(...args)=>(mounted=original(...args));
 return e;
}

const tests=[],test=(name,run)=>tests.push({name,run});
const objects=e=>e.calls.filter(v=>typeof v==='object');
async function chosen(e){e.choose().checked=true;await e.choose().fire('change');}
function clean(e){assert.equal(e.shopping.source,null);for(const id of ['shopping-items','shopping-meals','shopping-recorded-items','publication-diary-records'])assert.equal(e.map[id].textContent,'');assert.equal(e.map['publication-diary-day'].value,'');for(const control of e.root.querySelectorAll('input,button,select'))assert.equal(control.disabled,true,control.id);}
for(const [event,arg] of [['metodobase-session-changed',{}],['storage',{key:'mb_token'}],['storage',{key:null}],['pagehide',{}]])test('Immediate RAM/DOM discard and no stale continuation: '+event+JSON.stringify(arg),async()=>{
 const e=await integratedFixture(),gate=deferred();e.widget();await flush();await chosen(e);await e.map['shopping-build'].fire('click');assert.ok(e.map['shopping-items'].textContent);
 e.setReader(()=>gate.promise);const task=e.map['publication-diary-save'].fire('click');e.emit(event,arg);clean(e);gate.resolve(clone(e.source));await task;clean(e);assert.equal(objects(e).length,0);
});
test('An unrelated storage key preserves current explicit source',async()=>{const e=await integratedFixture();e.widget();await flush();e.emit('storage',{key:'unrelated-synthetic-key'});assert.notEqual(e.shopping.source,null);assert.equal(e.map['publication-diary-save'].disabled,false);});
test('Unconfirmed commit cannot automatically repeat; reconsult remains explicit',async()=>{
 const e=await integratedFixture();e.widget();await flush();await chosen(e);let mutations=0;e.Api.usuario.guardarDiario=async()=>{mutations++;throw Object.assign(Error('synthetic loss'),{status:503,code:'diary_save_unconfirmed'});};
 await e.map['publication-diary-save'].fire('click');await flush();assert.equal(mutations,1);assert.match(e.map['publication-diary-status'].textContent,/Puede haberse guardado/);assert.equal(e.map['publication-diary-save'].disabled,true);assert.equal(e.map['publication-diary-retry'].disabled,true);
 await e.map['publication-diary-reload'].fire('click');await flush();assert.equal(mutations,1);assert.equal(e.map['publication-diary-retry'].disabled,false);
 e.setReader(async()=>({...clone(e.source),key:'replacement'}));await e.map['publication-diary-retry'].fire('click');assert.equal(mutations,1);assert.equal(e.shopping.source,null);
});
test('CAS conflict requires reconsult and blocks another ordinary save',async()=>{
 const e=await integratedFixture();e.widget();await flush();await chosen(e);let writes=0;e.Api.usuario.guardarDiario=async()=>{writes++;throw Object.assign(Error('conflict'),{status:409,code:'diary_version_conflict'});};
 await e.map['publication-diary-save'].fire('click');await e.map['publication-diary-save'].fire('click');assert.equal(writes,1);assert.match(e.map['publication-diary-status'].textContent,/otro dispositivo/);assert.equal(e.map['publication-diary-retry'].disabled,true);
});
test('Late confirmed PATCH after session replacement cannot restore diary or controls',async()=>{
 const e=await integratedFixture(),gate=deferred();e.widget();await flush();await chosen(e);let writes=0;e.Api.usuario.guardarDiario=async()=>{writes++;return gate.promise;};const pending=e.map['publication-diary-save'].fire('click');await flush();assert.equal(writes,1);e.change();gate.resolve({...clone(e.day),version:1});await pending;clean(e);assert.equal(writes,1);
});
test('Future day never obtains a writable publication button',async()=>{const e=await integratedFixture();e.widget();await flush();e.Api.usuario.diarioDia=async()=>({...clone(e.day),local_date:'2026-10-20'});e.map['publication-diary-day'].value='2026-10-20';await e.map['publication-diary-day'].fire('change');assert.equal(e.map['publication-diary-save'].disabled,true);assert.equal(objects(e).length,0);});
test('Changed observed personal version while source read is retained blocks write',async()=>{
 const e=await integratedFixture(),gate=deferred();e.widget();await flush();await chosen(e);e.setReader(()=>gate.promise);const task=e.map['publication-diary-save'].fire('click');e.Api.usuario.diarioDia=async()=>({...clone(e.day),version:3});
 // Disabled DOM cannot perform a second day action during source validation.
 assert.equal(e.map['publication-diary-day'].disabled,true);await e.map['publication-diary-day'].fire('change');gate.resolve(clone(e.source));await task;assert.equal(objects(e).length,1);assert.equal(objects(e)[0].expected_version,0);
});
test('Consumption records only enums/indexes as attributes, never source IDs or DTO',async()=>{
 const e=await integratedFixture();e.widget();await flush();await chosen(e);await e.map['shopping-build'].fire('click');const attrs=JSON.stringify(e.root.all().map(n=>({dataset:n.dataset,attributes:n.attributes,value:n.tagName==='INPUT'&&n.type!=='date'?n.value:undefined})));
 assert.equal(attrs.includes(e.source.link_id),false);assert.equal(attrs.includes(e.source.publication_id),false);assert.equal(attrs.includes('huevo'),false);
});
test('Untrusted labels render literal text, without a markup assignment sink',async()=>{
 const e=await integratedFixture(),marker='<img src=x onerror=syntheticMarker()>',source=clone(e.source);source.plan.desayuno.alimentos={[marker]:12.25};e.shopping.setSource(source,e.day.today);assert.ok(e.map['shopping-meals'].textContent.includes(marker));assert.equal(e.root.all().some(n=>n.tagName==='IMG'),false);
});
test('No persistent API available to new consumer modules',async()=>{
 const e=await integratedFixture();let touched=0;const denied=new Proxy({}, {get(){touched++;throw Error('Storage forbidden');}});e.sandbox.localStorage=denied;e.sandbox.sessionStorage=denied;e.widget();await flush();await chosen(e);await e.map['shopping-build'].fire('click');await e.map['publication-diary-save'].fire('click');assert.equal(touched,0);
});
test('Unconfirmed catalog labels cannot merge despite identical spelling',async()=>{const e=await integratedFixture(),menu=e.sandbox.PlanDayData.menu(e.source.plan,[]),selected=e.sandbox.PlanDayData.select(menu,{desayuno:{include_fixed_menu:true},cena:{include_fixed_menu:true}}),list=e.sandbox.PlanDayData.shopping(selected,'2026-10-19','2026-10-19');assert.equal(list.items.length,2);assert.equal(list.items[0].food_id,null);});
test('Bounded period uses exact leap-day arithmetic and rejects 63 days',async()=>{const d=(await integratedFixture()).sandbox.PlanDayData;assert.equal(d.shopping([],'2024-02-28','2024-03-01').days,3);assert.throws(()=>d.shopping([],'2026-10-19','2026-12-20'));assert.throws(()=>d.shopping([],'2026-02-29','2026-03-01'));});
test('Finite positive grams remain mandatory before multiplication or aggregation',async()=>{const d=(await integratedFixture()).sandbox.PlanDayData;for(const grams of [true,'4',Infinity,NaN,0,-1])assert.throws(()=>d.shopping([{grams,unit:'g',food_id:'huevo'}],'2026-10-19','2026-10-19'));assert.throws(()=>d.shopping([{grams:Number.MAX_VALUE,unit:'g',food_id:'huevo'}],'2026-10-19','2026-10-20'));});
(async()=>{const results=[];for(const t of tests){try{await t.run();results.push({case:t.name,passed:true});}catch(e){results.push({case:t.name,passed:false,error:e.stack});}}console.log(JSON.stringify({scope:'Own minimal DOM/VM criteria, memory transport; no HTTP/browser claim',total:results.length,passed:results.filter(r=>r.passed).length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
`;
const m=new Module(__filename,module);m.filename=__filename;m.paths=module.paths;m._compile(prefix+'\n'+extra,__filename);
