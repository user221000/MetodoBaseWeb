/* Classic-script lexical Api + mounted minimal DOM. Typed transport doubles, no browser/API acceptance. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),Module=require('node:module'),path=require('node:path');
const fixtureFile=path.join(__dirname,'notifications36_state.cjs'),fixtureSource=fs.readFileSync(fixtureFile,'utf8'),split='const tests=[],test=';
assert.equal(fixtureSource.split(split).length,2);
const shared=new Module(fixtureFile,module);shared.filename=fixtureFile;shared.paths=module.paths;
shared._compile(fixtureSource.slice(0,fixtureSource.indexOf(split))+'\nmodule.exports={fixture,purposes};',fixtureFile);
const{fixture,purposes}=shared.exports,source=fs.readFileSync('web/static/js/notifications36.js','utf8'),markup=fs.readFileSync('web/templates/_notifications36_content.html','utf8');
const flush=async()=>{for(let n=0;n<12;n++)await new Promise(setImmediate);};

async function environment(context,readyState){
 const e=await fixture({context}),nodes=new Map(),listeners=new Map();
 const document={activeElement:null,readyState,addEventListener(name,fn,options){listeners.set(name,{fn,once:!!options?.once});},createElement:tag=>new Element(tag),createTextNode:value=>{const result=new Element('#text');result.textContent=value;return result;}};
 class Element{
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.parent=null;this.events=new Map();this.dataset={};this.disabled=false;this.hidden=false;this.checked=false;this.value='';this.attributes={};this._text='';}
  append(...items){for(const item of items){item.parent=this;this.children.push(item);}}
  replaceChildren(...items){for(const item of this.children){if(item.contains(document.activeElement))document.activeElement=null;item.parent=null;}this.children=[];this._text='';this.append(...items);}
  set textContent(value){this.replaceChildren();this._text=String(value);}get textContent(){return this._text+this.children.map(item=>item.textContent).join('');}
  set innerHTML(_){throw Error('HTML sink forbidden');}
  setAttribute(name,value){this.attributes[name]=String(value);}
  addEventListener(name,fn){this.events.set(name,fn);}
  focus(){document.activeElement=this;}contains(item){return item===this||this.children.some(child=>child.contains(item));}
  querySelectorAll(selector){const wanted=selector.split(',').map(tag=>tag.toUpperCase()),result=[];function visit(node){if(wanted.includes(node.tagName))result.push(node);node.children.forEach(visit);}this.children.forEach(visit);return result;}
 }
 const element=new Element('section');element.dataset.notificationContext=context;
 for(const match of markup.matchAll(/<(\w+)\b[^>]*\bdata-notification-([a-z-]+)(?:[\s>])/g)){const node=new Element(match[1]);assert.equal(nodes.has(match[2]),false);nodes.set(match[2],node);element.append(node);}
 element.querySelector=selector=>nodes.get(selector.slice('[data-notification-'.length,-1));
 for(const key of['from','through'])nodes.get('metrics-form').append(nodes.get(key));nodes.get('metrics-form').append(new Element('button'));
 document.querySelector=selector=>{assert.equal(selector,'[data-notifications36]');return element;};
 e.auth.window.document=document;
 assert.equal(vm.runInContext('typeof Api',e.auth.context),'object');
 assert.equal(vm.runInContext('Api.notifications36 === globalThis.api.notifications36',e.auth.context),true);
 assert.equal('Api' in e.auth.window,false); // Do not repair the page by fabricating window.Api.
 return{...e,element,nodes,document,listeners};
}

const tests=[],test=(name,run)=>tests.push({name,run});
for(const context of['gym','personal'])for(const mode of['default-call','DOMContentLoaded','ready-complete'])test(context+' '+mode+' uses lexical Api without an injected API option',async()=>{
 const e=await environment(context,mode==='ready-complete'?'complete':'loading');
 vm.runInContext(source,e.auth.context);let controller;
 if(mode==='default-call')controller=vm.runInContext("Notifications36.mount(document.querySelector('[data-notifications36]'))",e.auth.context);
 else if(mode==='DOMContentLoaded'){
  assert.equal(e.server.reads.length,0);const listener=e.listeners.get('DOMContentLoaded');assert.ok(listener);assert.equal(listener.once,true);e.listeners.delete('DOMContentLoaded');listener.fn();
 }
 await flush();
 assert.equal('Api' in e.auth.window,false);
 if(controller)assert.equal(controller.view().phase,'ready');
 assert.equal(e.nodes.get('preferences').children.length,2);
 assert.equal(e.nodes.get('preferences').querySelectorAll('input').length,4);
 assert.match(e.nodes.get('status').textContent,/Estado consultado/);
 assert.equal(e.nodes.get('refresh').disabled,false);
 assert.equal(e.server.reads.length,5);assert.equal(e.server.writes.length,0);
 for(const row of e.server.reads){assert.equal(row.method,'GET');assert.equal(new URL(row.url,'https://example.invalid').searchParams.get('context'),context);}
 assert.equal(e.auth.calls.filter(row=>row.url==='/api/auth/refresh').length,0);
});

for(const context of['gym','personal'])test(context+' actual closed API rejects invalid context and coerced CAS before transport',async()=>{
 const e=await fixture({context}),api=e.auth.api.notifications36,session=await api.session(),initial=e.auth.calls.length;
 for(const key of['session','check','verify','context','preferences','candidates','outbox','metrics','operation','send','discard'])assert.equal(typeof api[key],'function');
 assert.equal('request' in api,false);
 await assert.rejects(()=>api.context('other',session.handle));
 assert.throws(()=>api.operation('preference',context,purposes[0],{expected_version:true,enabled:true,interval_hours:24,confirm:true},session.handle));
 assert.throws(()=>api.operation('preference',context,purposes[0],{expected_version:0,enabled:true,interval_hours:24,confirm:true,actor:'forbidden'},session.handle));
 assert.equal(e.auth.calls.length,initial);assert.equal('Api' in e.auth.window,false);
});

(async()=>{
 const results=[];for(const row of tests){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name});}}
 const report={scope:'Actual classic lexical Api and notifications36 in one VM, minimal DOM and typed transport doubles. No Chrome, HTTP, PostgreSQL, provider or native-layout acceptance.',passed:results.filter(row=>row.passed).length,total:results.length,results};
 console.log(JSON.stringify(report));if(report.passed!==report.total)process.exitCode=1;
})();
