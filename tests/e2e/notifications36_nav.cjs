/* Canonical navigation and boundary behavior with the real browser-session Api. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {closed,tick}=require('./browser_harness31.cjs');
const source=fs.readFileSync('web/static/js/notification-nav36.js','utf8');
const rows=[],test=async(name,run)=>{try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name});}};
const later=()=>{let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};};
async function mounted(identity){
 const e=await closed(),links=['gym','personal'].map(context=>({dataset:{notificationNav:context},hidden:true}));
 e.window.document={readyState:'complete',querySelectorAll:()=>links};e.window.Api=e.api;e.window.SessionIdentity={ready:identity};
 vm.runInContext(source,e.context);for(let n=0;n<5;n++)await tick();return{...e,links};
}
(async()=>{
 for(const [name,me,wanted]of[
  ['own gym OWNER',{tipo:'gym',role:'owner',team_gym_id:null},[false,true]],
  ['gym ADMIN without personal identity',{tipo:'gym',role:'admin',team_gym_id:null},[true,true]],
  ['persisted gym team member',{tipo:'gym',role:'nutriologo',team_gym_id:'synthetic-team'},[true,false]],
  ['canonical individual viewer',{tipo:'usuario',role:'viewer',team_gym_id:null},[true,false]],
  ['unknown identity role',{tipo:'usuario',role:'unknown',team_gym_id:null},[true,true]],
 ])await test(name+' exposes only its own finite navigation',async()=>{const e=await mounted(Promise.resolve(me));assert.deepEqual(e.links.map(link=>link.hidden),wanted);assert.equal(e.calls.length,0);});
 await test('Absent identity never exposes a link or performs another request',async()=>{const gate=later(),e=await mounted(gate.promise);gate.resolve(null);await tick();assert.ok(e.links.every(link=>link.hidden));assert.equal(e.calls.length,0);});
 await test('External epoch before identity resolution prevents late navigation adoption',async()=>{const gate=later(),e=await mounted(gate.promise);e.invalidate();gate.resolve({tipo:'gym',role:'owner',team_gym_id:null});await tick();assert.ok(e.links.every(link=>link.hidden));assert.equal(e.api.getToken(),'');});
 for(const event of['metodobase-session-changed','pagehide'])await test(event+' immediately hides previously visible links',async()=>{const e=await mounted(Promise.resolve({tipo:'gym',role:'owner',team_gym_id:null}));assert.equal(e.links[0].hidden,false);e.window.dispatchEvent({type:event});assert.ok(e.links.every(link=>link.hidden));});
 console.log(JSON.stringify({scope:'Real Api RAM/epoch VM with typed identity and minimal navigation DOM; no native or API-authority claim.',passed:rows.filter(row=>row.passed).length,total:rows.length,results:rows},null,2));if(rows.some(row=>!row.passed))process.exitCode=1;
})();
