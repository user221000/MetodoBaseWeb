'use strict';
// Actual dashboard script in a VM; minimal DOM, no browser/layout acceptance.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/static/js/main.js','utf8');
function page({oldComplete=false,storageUnavailable=false}={}){
 const nodes=new Map(),storage=[];
 for(const id of ['onboarding-section','onboarding-pct','onboarding-bar-fill','ob-step-1','ob-step-2','ob-step-3','ob-action-1','btn-generar-plan']){
  const classes=new Set();nodes.set(id,{style:{},textContent:'',hidden:false,attributes:{},classList:{add(...v){v.forEach(x=>classes.add(x));},remove(...v){v.forEach(x=>classes.delete(x));},contains(v){return classes.has(v);}},setAttribute(k,v){this.attributes[k]=String(v);},addEventListener(){},click(){}});
 }
 const context=vm.createContext({document:{readyState:'loading',addEventListener(){},getElementById:id=>nodes.get(id)||null},localStorage:{getItem(key){storage.push(['get',key]);if(storageUnavailable)throw Error('Storage unavailable');return oldComplete?'1':null;},setItem(key,value){storage.push(['set',key,value]);if(storageUnavailable)throw Error('Storage unavailable');}}});
 vm.runInContext(source,context);
 return{nodes,storage,update:stats=>context.updateOnboarding(stats),done:id=>nodes.get('ob-step-'+id).classList.contains('completed')};
}
const facts=(client,plan,period=plan?1:0)=>({total_clientes:client?1:0,planes_periodo:period,onboarding:{client_registered:client,plan_saved:plan}});
const cases=[
 ['saved plan never proves export or delivery',()=>{const p=page();p.update(facts(true,true));assert.equal(p.done(3),false);}],
 ['another account legacy completion cannot hide the guide',()=>{const p=page({oldComplete:true});p.update(facts(true,true));assert.equal(p.nodes.get('onboarding-section').style.display,'block');assert.deepEqual(p.storage,[]);}],
 ['unavailable Storage cannot break confirmed server facts',()=>{const p=page({storageUnavailable:true});assert.doesNotThrow(()=>p.update(facts(true,true)));assert.equal(p.done(2),true);}],
 ['confirmed empty remains incomplete',()=>{const p=page();p.update(facts(false,false));assert.equal(p.done(1),false);assert.equal(p.done(2),false);assert.equal(p.nodes.get('onboarding-section').style.display,'block');}],
 ['client without a saved plan remains at the next action',()=>{const p=page();p.update(facts(true,false));assert.equal(p.done(1),true);assert.equal(p.done(2),false);}],
 ['persisted plan resumes outside the statistics period',()=>{const p=page();p.update(facts(true,true,0));assert.equal(p.done(2),true);}],
 ['untyped or absent facts do not turn aggregate counts into completion',()=>{const p=page();for(const onboarding of [undefined,{client_registered:'true',plan_saved:1}]){p.update({total_clientes:50,planes_periodo:50,onboarding});assert.equal(p.done(1),false);assert.equal(p.done(2),false);assert.match(p.nodes.get('onboarding-pct').textContent,/consultar|confirmar/i);}}],
];
const results=cases.map(([name,run])=>{try{run();return{name,passed:true};}catch(error){return{name,passed:false,error_class:error.name};}});
const report={scope:'Actual main.js in VM with minimal DOM; no HTTP, PostgreSQL, Chrome or human usability acceptance',passed:results.filter(x=>x.passed).length,total:results.length,results};
console.log(JSON.stringify(report));if(report.passed!==report.total)process.exitCode=1;
