/* Controlled DOM focus and real controller promises; no browser/layout claim. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.env.FOLLOWUP_FOCUS_SOURCE||path.resolve(__dirname,'../../web/static/js/dashboard-seguimiento.js'),'utf8');
const tests=[];const test=(name,body)=>tests.push({name,body});
function environment(){
  const listeners=new Map(),events=new Map();let document;
  class Element{
    constructor(){this.handlers=new Map();this.attributes={};this.isConnected=true;this.value='50';this._disabled=false;}
    set disabled(value){this._disabled=value;if(value&&document.activeElement===this)document.activeElement=document.body;}
    get disabled(){return this._disabled;}
    setAttribute(name,value){this.attributes[name]=value;}
    addEventListener(name,handler){this.handlers.set(name,handler);}
    append(){} replaceChildren(){}
    focus(){document.activeElement=this;for(const handler of listeners.get('focusin')||[])handler({target:this});}
  }
  const nodes=Object.fromEntries(['followup-section','followup-status','followup-error','followup-list','followup-metrics','followup-refresh','followup-limit'].map(name=>[name,new Element()]));
  document={body:new Element(),activeElement:null,getElementById:name=>nodes[name],createElement:()=>new Element(),
    addEventListener(name,handler){if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(handler);},
    removeEventListener(name,handler){listeners.get(name)?.delete(handler);}};
  document.activeElement=document.body;
  const body={items:[],has_more:false,as_of:'2026-10-19T12:00:00Z',window_days:30,payment_evidence:'unavailable',responsibility:'not_recorded',capabilities:{prepare_plan:true,review_client:true},metrics:{plans_saved:0,generation_operations_completed:0,pdf_metadata_ready:0}};
  let release=null,arrival=null,held=false;
  const stats={contexto:async()=>({actor:'synthetic'}),validarContexto(){},verificarContexto:async()=>{},
    seguimiento:async()=>{if(held){arrival();await new Promise(resolve=>release=resolve);}return body;}};
  const window={addEventListener(name,handler){events.set(name,handler);}};
  const context={window,document,Api:{stats},location:{assign(){}},console,Date,Error,Object,Number,Set};vm.createContext(context);vm.runInContext(source,context);
  const settle=async()=>{for(let index=0;index<30;index++){await Promise.resolve();if(!nodes['followup-refresh'].disabled)return;}throw new Error('Controller did not settle');};
  return{nodes,document,events,settle,pointerDown(){for(const handler of listeners.get('pointerdown')||[])handler({target:document.body});},async start(){await settle();held=true;const started=new Promise(resolve=>arrival=resolve);nodes['followup-refresh'].focus();const promise=nodes['followup-refresh'].handlers.get('click')();await started;return{promise,release:()=>release()};}};
}
test('Refresh returns focus after native disable and successful pending read',async()=>{
  const e=environment(),pending=await e.start();assert.equal(e.document.activeElement,e.document.body);
  pending.release();await pending.promise;assert.equal(e.document.activeElement,e.nodes['followup-refresh']);
});
test('Refresh never steals a different control focus chosen during the read',async()=>{
  const e=environment(),pending=await e.start();const other={};e.document.activeElement=other;
  pending.release();await pending.promise;assert.equal(e.document.activeElement,other);
});
test('A deliberate body click during the read prevents later focus restoration',async()=>{
  const e=environment(),pending=await e.start();e.pointerDown();
  pending.release();await pending.promise;assert.equal(e.document.activeElement,e.document.body);
});
test('Session invalidation prevents old refresh focus restoration',async()=>{
  const e=environment(),pending=await e.start();e.events.get('metodobase-session-changed')();
  pending.release();await pending.promise;assert.equal(e.document.activeElement,e.document.body);assert.equal(e.nodes['followup-refresh'].disabled,true);
});
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({name:entry.name,passed:true});}catch(error){results.push({name:entry.name,passed:false,error:error.stack});}}
  console.log(JSON.stringify({scope:'Offline controlled DOM only; no Chrome/PG/layout claim',total:results.length,passed:results.filter(row=>row.passed).length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})();
