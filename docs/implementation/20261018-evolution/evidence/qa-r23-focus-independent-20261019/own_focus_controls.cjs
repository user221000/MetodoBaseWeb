/* Independent intent, detached control and listener-lifecycle probes; DOM VM only. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=process.env.QA_FOCUS_ROOT;assert(root);
const source=fs.readFileSync(path.join(root,'web/static/js/dashboard-seguimiento.js'),'utf8');
const author=fs.readFileSync(path.join(root,'tests/e2e/dashboard_followup_focus.cjs'),'utf8');
const a=author.indexOf('function environment(){'),b=author.indexOf("test('Refresh returns focus");assert(a>0&&b>a);
let fixture=author.slice(a,b);
const marker='return{nodes,document,events,settle,pointerDown()';assert.equal(fixture.split(marker).length,2);
fixture=fixture.replace(marker,"return{nodes,document,events,settle,keydown(){for(const handler of listeners.get('keydown')||[])handler({key:'Tab',target:document.body});},focusRoundTrip(){const other={};document.activeElement=other;for(const handler of listeners.get('focusin')||[])handler({target:other});document.activeElement=document.body;},listenerCount(){return [...listeners.values()].reduce((n,s)=>n+s.size,0);},pointerDown()");
assert.equal(fixture.split('async start()').length,2);fixture=fixture.replace('async start()','async start(focus=true)');
assert.equal(fixture.split("nodes['followup-refresh'].focus();").length,2);fixture=fixture.replace("nodes['followup-refresh'].focus();","if(focus)nodes['followup-refresh'].focus();");
const environment=new Function('source','vm','assert',fixture+';return environment;')(source,vm,assert);
const cases=[];function test(name,body){cases.push({name,body});}
test('Keyboard intent while a request is pending prevents old focus restoration',async()=>{
  const e=environment(),pending=await e.start();e.keydown();pending.release();await pending.promise;
  assert.equal(e.document.activeElement,e.document.body);assert.equal(e.listenerCount(),0);
});
test('Moving to another control and back to body cannot be mistaken for native blur',async()=>{
  const e=environment(),pending=await e.start();e.focusRoundTrip();pending.release();await pending.promise;
  assert.equal(e.document.activeElement,e.document.body);assert.equal(e.listenerCount(),0);
});
test('A detached refresh element cannot receive restored focus',async()=>{
  const e=environment(),pending=await e.start();e.nodes['followup-refresh'].isConnected=false;pending.release();await pending.promise;
  assert.equal(e.document.activeElement,e.document.body);assert.equal(e.listenerCount(),0);
});
test('Programmatic click without originating focus cannot move focus into refresh',async()=>{
  const e=environment(),pending=await e.start(false);pending.release();await pending.promise;
  assert.equal(e.document.activeElement,e.document.body);assert.equal(e.listenerCount(),0);
});
test('Storage invalidation disables the old control and removes all pending focus listeners',async()=>{
  const e=environment(),pending=await e.start();e.events.get('storage')({key:'mb_token'});pending.release();await pending.promise;
  assert.equal(e.document.activeElement,e.document.body);assert.equal(e.nodes['followup-refresh'].disabled,true);assert.equal(e.listenerCount(),0);
});
test('Two completed refresh cycles restore originating focus and leave no document listener',async()=>{
  const e=environment();for(let i=0;i<2;i++){const pending=await e.start();assert.equal(e.listenerCount(),3);pending.release();await pending.promise;assert.equal(e.document.activeElement,e.nodes['followup-refresh']);assert.equal(e.listenerCount(),0);}
});
(async()=>{const results=[];for(const entry of cases){try{await entry.body();results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,reason:error.message});}}
console.log(JSON.stringify({scope:'Independent controlled DOM VM only; no Chrome/native-layout/PG claim',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})();
