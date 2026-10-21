/* Executable component DOM ports; actual RAM API. No browser/layout claim. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {world,tick}=require('./browser_harness31.cjs');
const dto=JSON.parse(fs.readFileSync(process.env.ROUTINE_CATALOG_FIXTURE,'utf8'));
const source=fs.readFileSync('web/static/js/rutinas.js','utf8'),rows=[];
class Element{
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.listeners=new Map();this.attributes={};this.hidden=false;this.disabled=false;this.open=false;this.value='90';this._text='';}
 set textContent(value){this._text=String(value);this.children=[];}
 get textContent(){return this._text+this.children.map(node=>node.textContent).join('');}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this._text='';this.children=[...nodes];}
 setAttribute(key,value){this.attributes[key]=String(value);}
 addEventListener(name,fn){this.listeners.set(name,fn);}
 fire(name){this.listeners.get(name)?.({target:this});}
 focus(){this.focused=true;}
 descendants(){return this.children.flatMap(node=>[node,...node.descendants()]);}
 querySelectorAll(selector){return this.descendants().filter(node=>selector==='details'?node.tagName==='DETAILS':selector==='input'?node.tagName==='INPUT':selector==='input:checked'?node.tagName==='INPUT'&&node.checked:false);}
}
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return{promise,resolve};};
async function settle(){for(let n=0;n<4;n++)await tick();}
async function setup(value=structuredClone(dto),hook=null){
 const w=world(),t=w.tab();await t.api.session.ready;
 const nodes=new Map(),panel=new Element();panel.dataset={scope:'gym'};
 panel.querySelector=selector=>{if(!nodes.has(selector)){const node=new Element();nodes.set(selector,node);panel.append(node);}return nodes.get(selector);};
 const get=name=>panel.querySelector('[data-routine-'+name+']');get('content').hidden=true;
 const intervals=new Map();let clock=0,next=0,prints=0;
 t.sandbox.document={readyState:'complete',querySelector:()=>null,createElement:tag=>new Element(tag)};
 t.sandbox.performance={now:()=>clock};t.sandbox.setInterval=fn=>{intervals.set(++next,fn);return next;};t.sandbox.clearInterval=id=>intervals.delete(id);t.sandbox.print=()=>prints++;
 let requests=0;t.hook(call=>{assert.equal(call.path,'/api/rutinas/catalogo?context=gym');requests++;return hook?hook(call,requests):Response.json(value);});
 vm.runInContext(source,t.context);t.sandbox.RoutinePanel.mount(panel);await settle();
 return{w,t,panel,get,intervals,requests:()=>requests,prints:()=>prints,advance(ms){clock+=ms;for(const fn of[...intervals.values()])fn();}};
}
async function test(name,run){try{await run();rows.push({case:name,passed:true});}catch(error){rows.push({case:name,passed:false,error_class:error.name});}}
(async()=>{
 await test('Positive lexical const Api mount renders actual 4/4/5 catalogue',async()=>{
  const x=await setup();assert.equal(Object.hasOwn(x.t.sandbox,'Api'),false);assert.equal(x.get('content').hidden,false);
  const sessions=x.get('sessions').children;assert.equal(sessions.length,3);assert.deepEqual(sessions.map(s=>s.querySelectorAll('details').length),[4,4,5]);assert.equal(x.requests(),1);
  assert.equal(x.get('days').querySelectorAll('input').length,7);assert.equal(x.get('week-summary').children.length,3);
 });
 await test('Server text is rendered with textContent rather than HTML interpretation',async()=>{
  const value=structuredClone(dto),payload='<img src=x onerror=untrusted()>';
  value.program.sessions[0].exercises[0].name=payload;value.program.summary=payload;
  const x=await setup(value);assert.equal(x.get('summary').textContent,payload);assert.equal(x.panel.descendants().filter(n=>n.tagName==='IMG').length,0);
  assert.ok(x.get('sessions').textContent.includes(payload));
 });
 await test('Native detail state opens for print and exactly restores',async()=>{
  const x=await setup(),details=x.get('sessions').querySelectorAll('details');details[2].open=true;
  const before=details.map(n=>n.open);x.t.dispatch({type:'beforeprint'});assert.ok(details.every(n=>n.open));
  x.t.dispatch({type:'afterprint'});assert.deepEqual(details.map(n=>n.open),before);x.get('print').fire('click');assert.equal(x.prints(),1);
 });
 await test('Invalid circular week has no fabricated session assignment',async()=>{
  const x=await setup(),inputs=x.get('days').querySelectorAll('input');
  for(const input of inputs)input.checked=[0,2,6].includes(Number(input.value));inputs[6].fire('change');assert.equal(x.get('week-summary').children.length,0);
  x.get('default').fire('click');assert.equal(x.get('week-summary').children.length,3);
  assert.deepEqual(inputs.filter(n=>n.checked).map(n=>Number(n.value)),[0,2,4]);
 });
 await test('Timer pause/resume/reset owns at most one interval',async()=>{
  const x=await setup();x.get('timer-start').fire('click');assert.equal(x.intervals.size,1);x.advance(20500);assert.equal(x.get('clock').textContent,'01:10');
  x.get('timer-start').fire('click');assert.equal(x.intervals.size,0);x.advance(30000);assert.equal(x.get('clock').textContent,'01:10');
  x.get('timer-start').fire('click');assert.equal(x.intervals.size,1);x.get('timer-reset').fire('click');assert.equal(x.intervals.size,0);assert.equal(x.get('clock').textContent,'01:30');
 });
 await test('Completed timer stops interval without exercise history',async()=>{
  const x=await setup();x.get('timer-start').fire('click');x.advance(90001);assert.equal(x.get('clock').textContent,'00:00');assert.equal(x.intervals.size,0);
  assert.equal(x.requests(),1);assert.ok(x.w.writes.every(row=>row.key==='mb_session_epoch'));
 });
 for(const event of['pagehide','metodobase-session-changed'])await test(event+' hides content, removes exercises and stops timer',async()=>{
  const x=await setup();x.get('timer-start').fire('click');x.t.dispatch({type:event});assert.equal(x.intervals.size,0);assert.equal(x.get('content').hidden,true);assert.equal(x.get('sessions').children.length,0);assert.equal(x.get('reload').disabled,true);
 });
 await test('Persisted pageshow prevents restored stale component',async()=>{
  const x=await setup();x.t.dispatch({type:'pageshow',persisted:true});assert.equal(x.get('content').hidden,true);assert.equal(x.get('sessions').children.length,0);
 });
 await test('Unknown malformed catalogue never renders a partial programme',async()=>{
  const value=structuredClone(dto);value.program.sessions[1].exercises[0].id=value.program.sessions[0].exercises[0].id;
  const x=await setup(value);assert.equal(x.get('content').hidden,true);assert.equal(x.get('sessions').children.length,0);assert.equal(x.get('recovery').hidden,false);
 });
 await test('Session boundary during response body rejects late DOM rendering',async()=>{
  const body=deferred(),entered=deferred();const x=await setup(dto,()=>({status:200,ok:true,text:async()=>{entered.resolve();await body.promise;return JSON.stringify(dto);}}));
  await entered.promise;x.t.dispatch({type:'pagehide'});body.resolve();await settle();assert.equal(x.get('content').hidden,true);assert.equal(x.get('sessions').children.length,0);
 });
 await test('Current 401 hides catalogue, retires real RAM access and makes no retry',async()=>{
  const x=await setup(dto,()=>Response.json({detail:{code:'routine_session_unavailable'}},{status:401}));
  assert.equal(x.t.api.getToken(),'');assert.equal(x.get('content').hidden,true);assert.equal(x.get('sessions').children.length,0);assert.equal(x.requests(),1);assert.equal(x.get('reload').disabled,true);
 });
 const result={scope:'Actual component and RAM API with executable DOM/clock/network ports; no browser or layout acceptance',passed:rows.filter(r=>r.passed).length,total:rows.length,results:rows};
 process.stdout.write(JSON.stringify(result,null,2)+'\n');process.exitCode=result.passed===result.total?0:1;
})().catch(error=>{process.stderr.write(error.name+'\n');process.exitCode=2;});
