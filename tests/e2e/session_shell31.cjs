/* Real shell/MFA kit code in a minimal DOM. No layout/native-browser claim. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const shell=fs.readFileSync(process.env.SHELL31_SOURCE||'web/static/js/session-shell.js','utf8');
const mfa=fs.readFileSync('web/static/js/mfa-ui.js','utf8');
function fixture(){
  const listeners=new Map();let revision=1;
  class Element{
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.parentNode=null;this.attributes={};this._text='';this.value='';this.checked=false;this.disabled=false;this.open=false;this.events=new Map();}
    get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}set textContent(value){this.replaceChildren();this._text=String(value);}
    append(...nodes){for(const node of nodes){if(node.parentNode)node.parentNode.children.splice(node.parentNode.children.indexOf(node),1);node.parentNode=this;this.children.push(node);}}
    replaceChildren(...nodes){for(const child of this.children)child.parentNode=null;this.children=[];this._text='';this.append(...nodes);}
    before(node){assert.ok(this.parentNode);if(node.parentNode)node.parentNode.children.splice(node.parentNode.children.indexOf(node),1);const parent=this.parentNode;node.parentNode=parent;parent.children.splice(parent.children.indexOf(this),0,node);}
    matches(selector){return selector.startsWith('#')?this.id===selector.slice(1):this.tagName===selector.toUpperCase();}
    querySelectorAll(selector){const terms=selector.split(',').map(t=>t.trim()),found=[];const visit=node=>{for(const child of node.children){if(terms.some(term=>child.matches(term)))found.push(child);visit(child);}};visit(this);return found;}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    setAttribute(key,value){this.attributes[key]=String(value);}
    addEventListener(type,fn){this.events.set(type,fn);}focus(){document.activeElement=this;}close(){this.open=false;}
    get isConnected(){let current=this;while(current){if(current===document.body)return true;current=current.parentNode;}return false;}
  }
  const document={body:new Element('body'),createElement:tag=>new Element(tag),getElementById(id){return this.body.querySelector('#'+id);},querySelectorAll(selector){return this.body.querySelectorAll(selector);},get cookie(){throw Error('No cookie API');}};
  const el=(tag,id,parent)=>{const item=document.createElement(tag);item.id=id;if(parent)parent.append(item);return item;};
  const main=el('main','main',document.body),field=el('input','old-profile',main);field.value='Synthetic private field';const name=el('p','old-client-name',main);name.textContent='Synthetic private name';el('p','sb-nombre',document.body).textContent='Synthetic private name';
  const sandbox={document,location:{pathname:'/clientes'},queueMicrotask,Event,Api:{mfa:{check(context){if(context.revision!==revision)throw Object.assign(Error('Changed'),{code:'session_changed'});}}},localStorage:{getItem(){throw Error('No Storage read');},setItem(){throw Error('No Storage write');}},fetch(){throw Error('No I/O');}};
  sandbox.window=sandbox;sandbox.addEventListener=(type,fn)=>{if(!listeners.has(type))listeners.set(type,[]);listeners.get(type).push(fn);};sandbox.removeEventListener=(type,fn)=>listeners.set(type,(listeners.get(type)||[]).filter(v=>v!==fn));sandbox.dispatchEvent=event=>{for(const fn of [...(listeners.get(event.type)||[])])fn(event);};
  const context=vm.createContext(sandbox);vm.runInContext(shell,context);vm.runInContext(mfa,context);
  return{sandbox,document,main,field,name,el,change(){revision++;sandbox.dispatchEvent({type:'metodobase-session-changed'});return{revision};},get revision(){return revision;},flush:()=>Promise.resolve()};
}
const results=[];async function test(name,run){try{await run();results.push({case:name,passed:true});}catch(error){results.push({case:name,passed:false,error_class:error.name,code:error.code||null});}}
(async()=>{
await test('Switch discards the same synthetic name and profile controls before another paint',async()=>{const f=fixture();f.change();await f.flush();assert.equal(f.document.getElementById('old-client-name'),null);assert.equal(f.field.value,'');assert.equal(f.field.disabled,true);assert.equal(f.document.getElementById('sb-nombre').textContent,'');assert.equal(f.main.querySelectorAll('input').length,0);assert.equal(f.main.querySelectorAll('a').length,1);});
if(!process.env.SHELL31_SOURCE){
await test('Owners clear secrets synchronously while their controls are still connected',async()=>{const f=fixture();let connected=false;f.sandbox.addEventListener('metodobase-session-changed',()=>{connected=f.field.isConnected;f.field.value='';});f.change();assert.equal(connected,true);await f.flush();assert.equal(f.field.isConnected,false);});
await test('Confirmed own security close keeps only the fresh one-time MFA kit connected',async()=>{const f=fixture(),island=f.el('section','mfa-account',f.main),seed=f.el('p','seed',island),kit=f.el('div','kit',island);seed.textContent='Synthetic seed';f.sandbox.addEventListener('metodobase-session-changed',()=>{seed.replaceChildren();kit.replaceChildren();});const closed=f.change();f.sandbox.MfaUI.kit(kit,Array.from({length:8},(_,i)=>'synthetic-code-'+i),closed,'/login-gym');await f.flush();assert.equal(island.parentNode,f.document.body);assert.equal(kit.isConnected,true);assert.equal(kit.querySelectorAll('li').length,8);assert.equal(seed.textContent,'');assert.equal(f.document.getElementById('old-profile'),null);});
await test('External switch clears the actual shown-once MFA kit and rejects the old context',async()=>{const f=fixture(),island=f.el('section','mfa-account',f.main),kit=f.el('div','kit',island);const old={revision:f.revision};f.sandbox.MfaUI.kit(kit,Array.from({length:8},(_,i)=>'synthetic-code-'+i),old,'/login-gym');f.change();assert.equal(kit.textContent,'');await f.flush();assert.equal(kit.querySelectorAll('li').length,0);assert.throws(()=>f.sandbox.MfaUI.kit(kit,[],old,'/login-gym'),{code:'session_changed'});assert.equal(kit.textContent,'');});
await test('Pagehide clears remaining legacy DOM without storage or network',async()=>{const f=fixture();f.sandbox.dispatchEvent({type:'pagehide'});await f.flush();assert.equal(f.field.value,'');assert.equal(f.document.getElementById('old-client-name'),null);});
await test('A restored page cannot display the prior account fields',async()=>{const f=fixture();f.sandbox.dispatchEvent({type:'pageshow',persisted:true});await f.flush();assert.equal(f.document.getElementById('old-profile'),null);assert.equal(f.document.getElementById('old-client-name'),null);});
}
const report={scope:'Actual session-shell.js and MFA shown-once kit in minimal DOM; synthetic value assertions only, no values in output, no native browser acceptance',passed:results.filter(r=>r.passed).length,total:results.length,results};process.stdout.write(JSON.stringify(report,null,2)+'\n');process.exitCode=report.passed===report.total?0:1;
})();
