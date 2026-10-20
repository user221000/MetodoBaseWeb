/* Mounted current UI with actual Api and a minimal DOM; no native layout claim. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),Module=require('node:module'),path=require('node:path');
const file=path.join(__dirname,'notifications36_state.cjs'),prefix=fs.readFileSync(file,'utf8').split('const tests=[]')[0],shared=new Module(file,module);shared.filename=file;shared.paths=module.paths;shared._compile(prefix+'\nmodule.exports={fixture,purposes,id,outbox};',file);const {fixture,purposes,outbox}=shared.exports;
const source=fs.readFileSync('web/static/js/notifications36.js','utf8'),markup=fs.readFileSync('web/templates/_notifications36_content.html','utf8'),flush=async()=>{for(let n=0;n<6;n++)await new Promise(setImmediate);};
async function mounted(options={}){
 const e=await fixture(options),nodes=new Map(),events=new Map();let storage=0;
 const document={activeElement:null,readyState:'loading',addEventListener(){},createElement:tag=>new Element(tag),createTextNode:value=>{const text=new Element('#text');text.textContent=value;return text;}};
 class Element{
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.parent=null;this.events=new Map();this.dataset={};this.disabled=false;this.hidden=false;this.checked=false;this.value='';this.attributes={};this._text='';}
  append(...nodes){for(const node of nodes){node.parent=this;this.children.push(node);}}
  replaceChildren(...nodes){for(const node of this.children){if(node.contains(document.activeElement))document.activeElement=null;node.parent=null;}this.children=[];this._text='';this.append(...nodes);}
  set textContent(value){this.replaceChildren();this._text=String(value);}get textContent(){return this._text+this.children.map(node=>node.textContent).join('');}
  set innerHTML(_){throw Error('Forbidden HTML sink');}
  setAttribute(key,value){this.attributes[key]=String(value);}
  addEventListener(name,fn){this.events.set(name,fn);}emit(name){this.events.get(name)?.({preventDefault(){}});}
  focus(){document.activeElement=this;}contains(node){return this===node||this.children.some(child=>child.contains(node));}
  querySelectorAll(selector){const tags=selector.split(',').map(tag=>tag.toUpperCase());const rows=[];function visit(node){if(tags.includes(node.tagName))rows.push(node);node.children.forEach(visit);}this.children.forEach(visit);return rows;}
 }
 const element=new Element('section');element.dataset.notificationContext=options.context||'gym';
 for(const match of markup.matchAll(/<(\w+)\b[^>]*\bdata-notification-([a-z-]+)(?:[\s>])/g)){const node=new Element(match[1]);nodes.set(match[2],node);element.append(node);}
 element.querySelector=selector=>nodes.get(selector.slice('[data-notification-'.length,-1));for(const key of['from','through'])nodes.get('metrics-form').append(nodes.get(key));const metricsButton=new Element('button');nodes.get('metrics-form').append(metricsButton);
 const sandbox={document,Date,Promise,console,addEventListener:(name,fn)=>{if(!events.has(name))events.set(name,[]);events.get(name).push(fn);}};sandbox.window=sandbox;for(const key of['localStorage','sessionStorage'])Object.defineProperty(sandbox,key,{get(){storage++;throw Error('No health/identity Storage access in UI');}});
 vm.createContext(sandbox);vm.runInContext(source,sandbox);const controller=sandbox.Notifications36.mount(element,{api:e.auth.api.notifications36});await flush();return{...e,controller,nodes,element,document,get storage(){return storage;},event:(name,value={})=>{for(const fn of events.get(name)||[])fn(value);}};
}
const tests=[],test=(name,run)=>tests.push({name,run});
test('Mounted preferences have labelled explicit checkbox/select/confirmation and remainOFF by default',async()=>{
 const e=await mounted();assert.equal(e.controller.view().phase,'ready');assert.equal(e.nodes.get('preferences').children.length,2);for(const form of e.nodes.get('preferences').children){assert.equal(form.querySelectorAll('input')[0].checked,false);assert.equal(form.querySelectorAll('input').length,2);assert.equal(form.querySelectorAll('select')[0].value,'24');assert.equal(form.querySelectorAll('button')[0].disabled,true);}assert.equal(e.server.writes.length,0);assert.match(e.nodes.get('source').textContent,/Fuente desconocida/);assert.equal(e.storage,0);
});
test('Changing controls alone never writes; submission without confirmation announces focused error',async()=>{
 const e=await mounted(),form=e.nodes.get('preferences').children[0],[enabled]=form.querySelectorAll('input');enabled.checked=true;enabled.emit('change');assert.equal(e.server.writes.length,0);form.emit('submit');await flush();assert.equal(e.server.writes.length,0);assert.equal(e.document.activeElement,e.nodes.get('status'));assert.equal(e.nodes.get('status').attributes.role,'alert');
});
test('Explicit preference submit sends one snapshot and focus moves to surviving announced status',async()=>{
 const e=await mounted(),form=e.nodes.get('preferences').children[0],[enabled,confirm]=form.querySelectorAll('input'),button=form.querySelectorAll('button')[0];enabled.checked=true;enabled.emit('change');confirm.checked=true;button.focus();form.emit('submit');await flush();assert.equal(e.server.writes.length,1);assert.equal(e.controller.view().phase,'read_required');assert.equal(e.document.activeElement,e.nodes.get('status'));assert.equal(e.nodes.get('refresh').disabled,false);assert.equal(e.server.reads.length,5);
});
test('Accepted/uncertain are inert truthful text, uncertain offers stop only',async()=>{
 const e=await mounted();e.server.outbox=[outbox(1,'gym','accepted'),outbox(2,'gym','uncertain')];await e.controller.load();const rows=e.nodes.get('outbox').children;assert.match(rows[0].textContent,/entrega no acreditada/);assert.equal(rows[0].querySelectorAll('button').length,0);assert.match(rows[1].textContent,/no reenviar/);assert.equal(rows[1].querySelectorAll('button').length,1);assert.match(rows[1].querySelectorAll('button')[0].textContent,/Detener/);
});
test('503 uncertainty enables only voluntary same-intent retry and manual query',async()=>{
 const e=await mounted();e.server.lost=true;await e.controller.savePreference(purposes[0],true,24,true);assert.equal(e.nodes.get('retry').hidden,false);assert.equal(e.nodes.get('refresh').disabled,false);assert.equal(e.nodes.get('observe').disabled,true);assert.equal(e.server.reads.length,5);e.server.lost=false;e.nodes.get('retry').emit('click');await flush();assert.equal(e.server.writes.length,2);assert.deepEqual(e.server.writes[0],e.server.writes[1]);
});
for(const name of['metodobase-session-changed','pagehide','storage'])test(name+' synchronously clears rendered own state and RAM intent without reading event values',async()=>{
 const e=await mounted({enabled:true,verified:true});e.server.lost=true;await e.controller.savePreference(purposes[0],false,24,true);e.nodes.get('observe-confirm').checked=true;e.nodes.get('from').value='2026-10-19';e.event(name,{key:'mb_session_epoch',get newValue(){throw Error('Forbidden event payload');}});assert.equal(e.controller.view().phase,'invalidated');assert.equal(e.nodes.get('preferences').children.length,0);assert.equal(e.nodes.get('metrics').textContent,'');assert.equal(e.nodes.get('retry').hidden,true);assert.equal(e.nodes.get('refresh').disabled,true);assert.equal(e.nodes.get('observe-confirm').checked,false);assert.equal(e.nodes.get('from').value,'');assert.equal(e.storage,0);
});
(async()=>{const results=[];for(const row of tests){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name,frames:error.stack?.split('\n').slice(1,4)});}}console.log(JSON.stringify({scope:'Maintained UI mounted in minimal DOM with actual Api VM and typed response doubles; no native keyboard, Chrome, axe, layout, HTTP or PostgreSQL claim.',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})();
