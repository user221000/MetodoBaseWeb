/* Independent controller-composition controls only; no API/auth/network stubs used. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync(process.argv[2],'utf8');
function fixture(){
 let activeElement=null,invalidator;
 const all=[];
 function element(tag,id,parent=null){const e={tagName:tag.toUpperCase(),id,children:[],parentElement:parent,disabled:false,hidden:false,textContent:'',dataset:{},
   append(child){child.parentElement=this;this.children.push(child);},
   contains(child){for(let p=child;p;p=p.parentElement)if(p===this)return true;return false;},
   matches(selector){if(selector==='#'+this.id)return true;if(selector==='[data-export-context]')return !!this.dataset.exportContext;if(selector==='main')return this.tagName==='MAIN';if(['button','input','select'].includes(selector))return this.tagName===selector.toUpperCase();if(selector==='.link-page')return this.id==='member-links-page';if(selector==='.privacy-card')return this.id==='personal-data-section';throw Error('Unsupported native selector in independent minimal DOM: '+selector);},
   closest(selector){for(let p=this;p;p=p.parentElement)if(p.matches(selector))return p;return null;},
   querySelectorAll(selector){const wanted=selector.split(',').map(v=>v.trim());return all.filter(item=>item!==this&&this.contains(item)&&wanted.some(value=>item.matches(value)));},
   focus(){activeElement=this;},setAttribute(){},replaceChildren(){this.children=[];}};
   all.push(e);if(parent)parent.children.push(e);return e;}
 const body=element('body','body'),main=element('main','member-links-page',body),status=element('p','member-links-status',main),error=element('div','member-links-error',main);
 const privateButton=element('button','member-links-refresh',main),list=element('div','member-links-list',main),publication=element('section','member-publication',main);
 element('button','member-publication-pdf',publication);element('button','member-link-leave',publication);element('button','member-links-more',main);
 const privacy=element('section','personal-data-section',main);privacy.dataset.exportContext='recipient';const foreign=element('button','privacy-start',privacy);
 const outside=element('button','public-independent-control',body);
 const document={getElementById:id=>all.find(e=>e.id===id),querySelectorAll:selector=>body.querySelectorAll(selector)};
 const context={console,setTimeout,clearTimeout,URL,document,window:{}};
 context.MemberLinkContext={create(options){let active=true;const value={get active(){return active;},check(){if(!active)throw Object.assign(Error('changed'),{code:'session_changed'});}};invalidator=()=>{active=false;options.onInvalidated();};return value;}};
 vm.createContext(context);vm.runInContext(source,context,{filename:process.argv[2]});
 const ui=context.window.VinculosUI.setup({status:status.id,error:error.id,clear(){},controls(){}});
 return {ui,privateButton,foreign,outside,invalidate:()=>invalidator(),focus:()=>activeElement};
}
const cases=[
 ['Concurrent privacy initialization remains enabled after unrelated member operation',async()=>{
   const e=fixture();e.foreign.disabled=true;let started,release;const begun=new Promise(r=>started=r),blocked=new Promise(r=>release=r);
   const run=e.ui.run(async()=>{started();await blocked;});await begun;e.foreign.disabled=false;release();await run;
   assert.equal(e.foreign.disabled,false);assert.equal(e.privateButton.disabled,false);
 }],
 ['Member-only invalidation does not write independent privacy/public controls',async()=>{
   const e=fixture();e.foreign.disabled=false;e.outside.disabled=false;e.foreign.focus();e.invalidate();
   assert.equal(e.foreign.disabled,false);assert.equal(e.outside.disabled,false);assert.equal(e.focus(),e.foreign);
   assert.equal(e.privateButton.disabled,true);
 }],
 ['Owned member controls are blocked during operation and restored afterwards',async()=>{
   const e=fixture();let started,release;const begun=new Promise(r=>started=r),blocked=new Promise(r=>release=r);
   const run=e.ui.run(async()=>{started();await blocked;});await begun;assert.equal(e.privateButton.disabled,true);release();await run;assert.equal(e.privateButton.disabled,false);
 }],
];
(async()=>{const results=[];for(const [name,run]of cases){try{await run();results.push({case:name,passed:true});}catch(error){results.push({case:name,passed:false,error:error.message});}}
 const value={scope:'Only actual VinculosUI controls against independent nested-controller DOM, no browser/HTTP/API/security acceptance.',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),results,passed:results.filter(v=>v.passed).length,total:results.length};console.log(JSON.stringify(value,null,2));if(value.passed!==value.total)process.exitCode=1;})();
