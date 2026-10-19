'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=process.env.R23_REVIEW_ROOT||'F:/mb-follow-sec';
const tests=[];const test=(name,body)=>tests.push({name,body});
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
const body=()=>({as_of:'2026-10-19T18:00:00Z',window_days:30,has_more:false,payment_evidence:'unavailable',responsibility:'not_recorded',capabilities:{review_client:true,prepare_plan:true},metrics:{plans_saved:1,generation_operations_completed:0,pdf_metadata_ready:0},items:[{id_cliente:'synthetic-client',nombre:'<img src=x onerror=SYNTHETIC()>',causes:['no_saved_plan'],priority:1,last_plan_at:null,elapsed_days:null,membership_end:null,responsible:null}]});
class Element{
  constructor(tag='div'){this.tag=tag;this.attrs={};this.children=[];this.textContent='';this.hidden=false;this.disabled=false;this.value='50';this.listeners={};}
  set innerHTML(_){throw new Error('Product attempted HTML interpolation');}
  setAttribute(k,v){this.attrs[k]=v;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];}
  addEventListener(type,fn){(this.listeners[type]||=[]).push(fn);}
  async click(){for(const fn of this.listeners.click||[])await fn(new Event('click'));}
  get allText(){return this.textContent+this.children.map(n=>n.allText||'').join('');}
  buttons(){return this.children.flatMap(n=>n.tag==='button'?[n]:n.buttons());}
}
function fixture(){
  const ids=['followup-section','followup-status','followup-error','followup-list','followup-metrics','followup-refresh','followup-limit'];
  const nodes=Object.fromEntries(ids.map(id=>[id,new Element()])),target=new EventTarget(),values=new Map([['mb_token','synthetic-A'],['mb_refresh_token','synthetic-RA']]);
  const me={id:'A',role:'owner',team_gym_id:null,session_version:0,tipo:'gym'},navigations=[];let hold=null;const sent=[];
  const context={window:target,Event,Response,Blob,FormData,URL,URLSearchParams,setTimeout,clearTimeout,
    location:{assign:uri=>navigations.push(uri)},document:{getElementById:id=>nodes[id]||null,createElement:tag=>new Element(tag)},
    localStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},
    fetch:async(u,o)=>{sent.push({url:u,options:o});if(u==='/api/auth/me')return Response.json({...me});if(u.startsWith('/api/estadisticas/seguimiento'))return hold?hold.promise:Response.json(body());throw new Error('Unexpected VM transport');}};
  vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'web/static/js/api.js'),'utf8')+'\nglobalThis.reviewApi=Api;',context);
  vm.runInContext(fs.readFileSync(path.join(root,'web/static/js/dashboard-seguimiento.js'),'utf8'),context);
  return{api:context.reviewApi,target,nodes,me,sent,navigations,hold:g=>hold=g};
}
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setImmediate(r));}assert.fail('Bounded VM state was not reached');}
async function loaded(e){await until(()=>e.nodes['followup-list'].children.length===1 && e.nodes['followup-section'].attrs['aria-busy']==='false');assert.equal(e.nodes['followup-error'].hidden,true);assert.ok(e.nodes['followup-list'].allText.includes('<img src=x onerror=SYNTHETIC()>'));}
for(const [field,value] of [['id','B'],['role','viewer'],['team_gym_id','B'],['session_version',1]]){
  test('Actual API helper + mounted renderer block navigation and erase data after canonical '+field+' change',async()=>{
    const e=fixture();await loaded(e);const buttons=e.nodes['followup-list'].buttons();assert.equal(buttons.length,2);e.me[field]=value;
    await buttons[1].click();assert.deepEqual(e.navigations,[]);assert.equal(e.nodes['followup-list'].children.length,0);assert.equal(e.nodes['followup-metrics'].children.length,0);assert.equal(e.nodes['followup-refresh'].disabled,true);assert.equal(e.nodes['followup-limit'].disabled,true);
  });
}
test('Native same-document saveTokens synchronously clears mounted actual R23 DOM and capabilities',async()=>{
  const e=fixture();await loaded(e);const previous=e.nodes['followup-list'].buttons();
  e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});
  assert.equal(e.nodes['followup-list'].children.length,0);assert.equal(e.nodes['followup-metrics'].children.length,0);assert.equal(e.nodes['followup-refresh'].disabled,true);assert.equal(e.nodes['followup-limit'].disabled,true);
  const requests=e.sent.length;await previous[1].click();await e.nodes['followup-refresh'].click();assert.equal(e.sent.length,requests);assert.deepEqual(e.navigations,[]);
});
test('Held real-helper response after saveTokens never reads old JSON or resurrects mounted R23 rows',async()=>{
  const e=fixture();await loaded(e);const gate=deferred();e.hold(gate);let touched=0;
  const before=e.sent.filter(x=>x.url.startsWith('/api/estadisticas/seguimiento')).length;
  const pending=e.nodes['followup-refresh'].click();await until(()=>e.sent.filter(x=>x.url.startsWith('/api/estadisticas/seguimiento')).length===before+1);
  e.api.saveTokens({token:'synthetic-B',refresh_token:'synthetic-RB'});
  gate.resolve({ok:true,status:200,json:async()=>{touched++;return body();}});await pending;
  assert.equal(touched,0);assert.equal(e.nodes['followup-list'].children.length,0);assert.equal(e.nodes['followup-metrics'].children.length,0);assert.equal(e.nodes['followup-refresh'].disabled,true);assert.deepEqual(e.navigations,[]);
});
(async()=>{const results=[];for(const t of tests){try{await t.body();results.push({name:t.name,passed:true});}catch(error){results.push({name:t.name,passed:false,error:error.stack});}}console.log(JSON.stringify({scope:'Offline VM native EventTarget, actual API helper and R23 renderer, minimal DOM double; no Chrome/layout',total:results.length,passed:results.filter(x=>x.passed).length,results},null,2));if(results.some(x=>!x.passed))process.exitCode=1;})();
