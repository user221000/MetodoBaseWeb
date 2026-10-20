'use strict';
// Own mounted DOM oracles; actual classic api.js through unchanged shared fixture.
// Transport and DOM are doubles. No HTTP, browser or PG acceptance.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),Module=require('node:module');
const root=process.env.QA_REVIEW_ROOT;assert.ok(path.isAbsolute(root));process.chdir(root);
const fixtureFile=path.join(root,'tests/e2e/notifications36_state.cjs'),raw=fs.readFileSync(fixtureFile,'utf8');
const split='const tests=[],test=';assert.equal(raw.split(split).length,2);
const shared=new Module(fixtureFile,module);shared.filename=fixtureFile;shared.paths=module.paths;
shared._compile(raw.slice(0,raw.indexOf(split))+'\nmodule.exports={fixture};',fixtureFile);
const {fixture}=shared.exports,source=fs.readFileSync('web/static/js/notifications36.js','utf8'),markup=fs.readFileSync('web/templates/_notifications36_content.html','utf8');
const tick=()=>new Promise(setImmediate),flush=async()=>{for(let i=0;i<15;i++)await tick();};
const deferred=()=>{let resolve;return {promise:new Promise(yes=>resolve=yes),resolve};};
async function environment(context,missing=false){
 const e=await fixture({context}),nodes=new Map();
 const document={activeElement:null,readyState:'complete',createElement:tag=>new El(tag),createTextNode:text=>{const n=new El('#text');n.textContent=text;return n;}};
 class El{
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.events=new Map();this.parent=null;this.dataset={};this.hidden=false;this.disabled=false;this.value='';this.checked=false;this.attrs={};this.text='';}
  append(...items){for(const n of items){n.parent=this;this.children.push(n);}}
  replaceChildren(...items){for(const n of this.children){if(n.contains(document.activeElement))document.activeElement=null;n.parent=null;}this.children=[];this.text='';this.append(...items);}
  set textContent(v){this.replaceChildren();this.text=String(v);}get textContent(){return this.text+this.children.map(n=>n.textContent).join('');}
  set innerHTML(_v){throw Error('HTML sink prohibited');}
  setAttribute(k,v){this.attrs[k]=String(v);}addEventListener(k,fn){this.events.set(k,fn);}
  contains(n){return n===this||this.children.some(c=>c.contains(n));}focus(){document.activeElement=this;}
  querySelectorAll(selector){const tags=selector.split(',').map(s=>s.toUpperCase()),items=[];function walk(n){for(const c of n.children){if(tags.includes(c.tagName))items.push(c);walk(c);}}walk(this);return items;}
 }
 const section=new El('section');section.dataset.notificationContext=context;
 for(const match of markup.matchAll(/<(\w+)\b[^>]*\bdata-notification-([a-z-]+)(?:[\s>])/g)){
  assert.equal(nodes.has(match[2]),false);const n=new El(match[1]);nodes.set(match[2],n);section.append(n);
 }
 section.querySelector=s=>nodes.get(s.slice('[data-notification-'.length,-1));
 for(const k of ['from','through'])nodes.get('metrics-form').append(nodes.get(k));nodes.get('metrics-form').append(new El('button'));
 document.querySelector=s=>{assert.equal(s,'[data-notifications36]');return missing?null:section;};
 e.auth.window.document=document;assert.equal(vm.runInContext('typeof Api',e.auth.context),'object');
 assert.equal('Api' in e.auth.window,false); // No window alias and no options.api injection.
 return {...e,nodes,section,document};
}
const cases=[],test=(name,run)=>cases.push({name,run});
for(const role of ['gym','personal']){
 test(role+' pagehide while source GET pending clears mounted DOM and RAM; late reply cannot restore it',async()=>{
  const e=await environment(role),gate=deferred(),arrived=deferred();
  e.server.hook=async row=>{if(row.url.includes('/candidatos')){arrived.resolve();await gate.promise;}return null;};
  vm.runInContext(source,e.auth.context);
  await Promise.race([arrived.promise,new Promise((_,reject)=>setTimeout(()=>reject(Error('Pending source not reached')),1000))]);
  e.auth.window.dispatchEvent(new Event('pagehide'));gate.resolve();await flush();
  assert.equal(e.nodes.get('preferences').children.length,0);assert.match(e.nodes.get('status').textContent,/sesión cambió/);
  assert.equal(e.nodes.get('refresh').disabled,true);assert.equal(e.auth.api.getToken(),'');
  assert.equal(e.server.writes.length,0);assert.equal(e.server.reads.length,5);assert.equal('Api' in e.auth.window,false);
 });
 test(role+' external epoch after ready clears displayed preferences and disabled refresh cannot dispatch again',async()=>{
  const e=await environment(role);vm.runInContext(source,e.auth.context);await flush();
  assert.equal(e.nodes.get('preferences').children.length,2);assert.equal(e.server.reads.length,5);
  e.auth.invalidate();await flush();assert.equal(e.nodes.get('preferences').children.length,0);
  assert.equal(e.nodes.get('refresh').disabled,true);assert.equal(e.auth.api.getToken(),'');
  e.nodes.get('refresh').events.get('click')();await flush();assert.equal(e.server.reads.length,5);
  assert.equal(e.server.writes.length,0);assert.equal('Api' in e.auth.window,false);
 });
 test(role+' page with no notifications mount remains inert and leaves Api only lexical',async()=>{
  const e=await environment(role,true);vm.runInContext(source,e.auth.context);await flush();
  assert.equal(e.server.reads.length,0);assert.equal(e.server.writes.length,0);assert.equal('Api' in e.auth.window,false);
 });
}
(async()=>{const results=[];for(const row of cases){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name});}}
 console.log(JSON.stringify({scope:'Own6 DOM/session oracles; unchanged fixture supplies actual lexical Api, synthetic DOM/typed transport only',total:results.length,passed:results.filter(r=>r.passed).length,results}));
 if(results.some(r=>!r.passed))process.exitCode=1;
})();
