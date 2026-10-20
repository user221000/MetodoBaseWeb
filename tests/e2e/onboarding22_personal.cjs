'use strict';
// Execute the actual personal-plan inline script; dependencies/DOM are declared doubles.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const markup=fs.readFileSync('web/templates/usuario_mi_plan.html','utf8');
const scripts=Array.from(markup.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g),m=>m[1]).filter(s=>s.trim());
assert.equal(scripts.length,1);
async function exercise(profile){
 const nodes=new Map(),reads=[],writes=[];
 function node(id){if(!nodes.has(id))nodes.set(id,{style:{display:'none'},textContent:'',hidden:false,disabled:false,addEventListener(){},focus(){},replaceChildren(){}});return nodes.get(id);}
 const personal={active:true,state:'idle',check(){assert.equal(this.active,true);},async start(){return profile;},async read(run){return run({});},invalidate(){this.active=false;},generate(){writes.push('generation');}};
 const context=vm.createContext({document:{getElementById:node,querySelector:()=>node('main'),querySelectorAll:()=>[]},PersonalPlanOperation:{create:()=>personal},PersonalDiary:{mountPlan:()=>({async bootstrap(){}})},PlanDayUI:{mount:()=>({})},Nutrition35:{renderSummary(){},assertAutomated(){},error:code=>new Error(code)},Api:{usuario:{async perfil(){reads.push('profile');return profile;},async miPlan(){reads.push('plan');throw Error('declared plan-read boundary');}}}});
 await vm.runInContext(scripts[0],context);
 return{nodes,reads,writes};
}
const complete={nombre:'Synthetic',peso_kg:70,estatura_cm:170,edad:30,objetivo:'mantenimiento',restricciones_nutricionales:{}};
(async()=>{
const results=[];
for(const field of ['peso_kg','edad']){
 try{const p=await exercise({...complete,[field]:null});assert.equal(p.nodes.get('onboarding-card').style.display,'flex');assert.equal(p.nodes.get('quick-actions').style.display,'none');assert.deepEqual(p.reads,['profile']);assert.deepEqual(p.writes,[]);assert.match(markup,/<a href="\/mi-perfil"[^>]*>Configurar mi plan/);results.push({case:field+' missing leaves only the working profile action',passed:true});}
 catch(error){results.push({case:field+' missing leaves only the working profile action',passed:false,error_class:error.name});}
}
try{const p=await exercise(complete);assert.deepEqual(p.reads,['profile','plan']);assert.deepEqual(p.writes,[]);assert.notEqual(p.nodes.get('onboarding-card')?.style.display,'flex');results.push({case:'complete profile reaches the existing explicit plan reader without generation',passed:true});}
catch(error){results.push({case:'complete profile reaches the existing explicit plan reader without generation',passed:false,error_class:error.name});}
const report={scope:'Actual personal inline script with declared operation/diary/nutrition/transport and minimal DOM doubles; no authentication, HTTP, browser or usability acceptance',passed:results.filter(x=>x.passed).length,total:results.length,results};
console.log(JSON.stringify(report));if(report.passed!==report.total)process.exitCode=1;
})();
