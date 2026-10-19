/* Actual consumers with a small DOM and fixed APIv1 doubles. No browser/HTTP claim. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const flush=async()=>{for(let i=0;i<12;i++)await new Promise(setImmediate);};
const capabilities={issue_invitation:true,rotate_invitation:true,revoke_link:true,publish_plan:true,withdraw_publication:true};
const context={kind:'gym_member',link_id:A,gym_name:'Synthetic gym',client_display_name:'Synthetic member'};
const row={link_id:A,status:'active',version:7,context,capabilities:{read_published_plan:true,revoke_link:true}};
const fixed=()=>Object.fromEntries(['desayuno','almuerzo','comida','cena'].map(k=>[k,{kcal_objetivo:100,kcal_real:100,alimentos:{'Literal <img src=x onerror=alert(1)>':100}}]));
class Element{
  constructor(tag,doc){this.tagName=tag.toUpperCase();this.doc=doc;this.children=[];this.listeners={};this.hidden=false;this.disabled=false;this.dataset={};this.value='';this._text='';}
  set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  set innerHTML(_){throw new Error('Consumer must not insert JSON as HTML');}
  append(...nodes){for(const x of nodes){x.parent=this;this.children.push(x);}}appendChild(x){this.append(x);}
  replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
  setAttribute(k,v){this[k]=String(v);}getAttribute(k){return this[k]??null;}
  addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
  async fire(name){const event={preventDefault(){},currentTarget:this,target:this};for(const fn of this.listeners[name]||[])await fn(event);await flush();}
  click(){if(this.tagName==='A')this.doc.downloads.push({href:this.href,name:this.download});else return this.fire('click');}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}
  focus(){this.doc.activeElement=this;}reportValidity(){return this.value.includes('@');}
  querySelectorAll(selector){const out=[];for(const x of this.children){if(selector==='[data-mutation]'&&x.dataset.mutation)out.push(x);out.push(...x.querySelectorAll(selector));}return out;}
}
function env(kind){
  const template={invitation:'accept_client_link.html',professional:'cliente_vinculacion.html',reader:'usuario_vinculos.html'}[kind];
  const markup=fs.readFileSync(path.join(root,'web/templates',template),'utf8'),ids={},events={},calls=[],urls=[],revoked=[];
  const doc={downloads:[],createElement(tag){return new Element(tag,doc);},getElementById:id=>ids[id],querySelectorAll(selector){const tags=selector.split(',').map(s=>s.toUpperCase());const out=[];const walk=x=>{if(tags.includes(x.tagName))out.push(x);for(const c of x.children)walk(c);};walk(doc.body);return out;}};
  doc.body=new Element('body',doc);
  for(const match of markup.matchAll(/<([a-z]+)\b([^>]*?\sid="([^"]+)"[^>]*)>/g)){
    const element=new Element(match[1],doc);element.id=match[3];element.hidden=/\bhidden\b/.test(match[2]);ids[element.id]=element;doc.body.append(element);
  }
  if(ids['professional-link-page'])ids['professional-link-page'].dataset.clientId='synthetic-client';
  const e={doc,ids,calls,urls,revoked,revision:0,handlers:{},keyCount:0};
  const me={id:'synthetic-a',tipo:'usuario',role:'viewer',team_gym_id:null,session_version:1};
  const api={contexto:async()=>({revision:e.revision,subject:'synthetic-a',me}),validarContexto:c=>{if(c.revision!==e.revision)throw Object.assign(new Error('Synthetic session switch'),{code:'session_changed'});},verificarContexto:async c=>api.validarContexto(c)};
  const defaults={estado:{client_id:'synthetic-client',capabilities,items:[],next_after:null},listar:{items:[row],next_after:null},plan:{context,link:{status:'active',version:7},capabilities:{read_published_plan:true,download_published_pdf:true,revoke_link:true},publication:{id:B,version:3,source_plan_id:41,plan_schema_version:1,plan:fixed(),meta:{kcal_objetivo:400},published_at:'2026-10-19T18:00:00Z'}},inspeccionar:{status:'pending',version:4,expires_at:'2026-10-26T18:00:00Z',link_id:A,context,can_accept:true},aceptar:{link_id:A,status:'active',version:7,context},emitir:{invitation_id:B,link_id:A,status:'pending',link_status:'pending',version:1,link_version:1,expires_at:'2026-10-26T18:00:00Z',delivery_status:'not_confirmed'},pdf:new Blob(['%PDF-synthetic'],{type:'application/pdf'})};
  for(const name of ['estado','listar','plan','inspeccionar','aceptar','emitir','rotar','revocar','publicar','retirar','desvincular','pdf'])api[name]=async(...args)=>{calls.push({name,args});return e.handlers[name]?e.handlers[name](...args):defaults[name];};
  const box={document:doc,Api:{vinculos:api},Blob,URLSearchParams,console,location:{search:''},
    URL:{createObjectURL:()=>{const value='blob:synthetic-'+urls.length;urls.push(value);e.onURL?.();return value;},revokeObjectURL:u=>revoked.push(u)},
    crypto:{randomUUID:()=>{e.keyCount++;return '33333333-3333-4333-8333-'+String(e.keyCount).padStart(12,'0');}},
    addEventListener:(name,fn)=>{(events[name]??=[]).push(fn);},setTimeout:()=>1,clearTimeout:()=>{},confirm:()=>true,
    takeClientLinkInvitation:()=>({token:'S'.repeat(43),state:'ready'}),
  };box.window=box;vm.createContext(box);
  const consumer={invitation:'vinculos-invitacion.js',professional:'vinculos-profesional.js',reader:'vinculos-lectura.js'}[kind];
  e.load=()=>{for(const p of ['vinculos-contexto.js','vinculos-ui.js',consumer])vm.runInContext(fs.readFileSync(path.join(root,'web/static/js',p),'utf8'),box);};
  e.emit=(name,event={})=>{for(const fn of events[name]||[])fn(event);};e.text=()=>doc.body.textContent;e.box=box;
  return e;
}
const tests=[];const test=(n,f)=>tests.push([n,f]);
test('opening invitation never inspects or accepts; inspection does not consume',async()=>{
  const e=env('invitation');e.load();await flush();assert.equal(e.calls.length,0);
  await e.ids['invitation-inspect'].fire('click');assert.deepEqual(e.calls.map(x=>x.name),['inspeccionar']);assert.equal(e.ids['invitation-accept'].hidden,false);
  await e.ids['invitation-accept'].fire('click');assert.equal(e.calls.filter(x=>x.name==='aceptar').length,1);assert.equal(e.calls.at(-1).args[1],4);assert.equal(e.ids['invitation-open-links'].hidden,false);
});
test('late inspection after account change does not render the old identity or offer acceptance',async()=>{
  const e=env('invitation'),held=deferred(),entered=deferred();e.handlers.inspeccionar=()=>{entered.resolve();return held.promise;};e.load();
  const pending=e.ids['invitation-inspect'].fire('click');await entered.promise;e.revision++;held.resolve({status:'pending',version:4,link_id:A,context,can_accept:true});await pending;
  assert.equal(e.ids['invitation-details'].textContent,'');assert(e.ids['invitation-accept'].hidden);assert(!e.text().includes('Synthetic gym'));
});
test('lost acceptance ACK requires reinspection/list and never autoaccepts again',async()=>{
  const e=env('invitation');e.handlers.aceptar=()=>{throw new Error('Synthetic lost response');};e.load();await e.ids['invitation-inspect'].fire('click');await e.ids['invitation-accept'].fire('click');
  assert(e.ids['invitation-accept'].hidden);assert.equal(e.calls.filter(x=>x.name==='aceptar').length,1);assert(e.ids['invitation-error'].textContent.includes('No se pudo confirmar'));
});
test('professional issue lost response retains exactly the same email/key and blocks edits',async()=>{
  const e=env('professional');let first=true;e.handlers.emitir=()=>{if(first){first=false;throw new Error('Synthetic lost ACK');}return {invitation_id:B,link_id:A,status:'pending',delivery_status:'not_confirmed'};};e.load();await flush();
  e.ids['link-recipient'].value='synthetic@example.invalid';await e.ids['link-invite-form'].fire('submit');
  assert(e.ids['link-recipient'].disabled);assert.equal(e.ids['link-issue-retry'].hidden,false);await e.ids['link-issue-retry'].fire('click');
  const calls=e.calls.filter(x=>x.name==='emitir');assert.equal(calls.length,2);assert.equal(calls[0].args[1],calls[1].args[1]);assert.equal(calls[0].args[2],calls[1].args[2]);assert.equal(e.keyCount,1);
  assert(e.ids['professional-link-status'].textContent.includes('entrega del correo sin confirmar'));
});
test('two issue clicks while pending create only one operation',async()=>{
  const e=env('professional'),held=deferred(),entered=deferred();e.handlers.emitir=()=>{entered.resolve();return held.promise;};e.load();await flush();e.ids['link-recipient'].value='synthetic@example.invalid';
  const pending=e.ids['link-invite-form'].fire('submit');await entered.promise;await e.ids['link-invite-form'].fire('submit');
  held.resolve({invitation_id:B,link_id:A,status:'pending',delivery_status:'not_confirmed'});await pending;assert.equal(e.calls.filter(x=>x.name==='emitir').length,1);assert.equal(e.keyCount,1);
});
test('account replacement before form submit clears the draft and cannot issue under the new account',async()=>{
  const e=env('professional');e.load();await flush();e.ids['link-recipient'].value='synthetic-old-recipient@example.invalid';e.revision++;
  e.ids['link-recipient'].reportValidity=()=>{throw new Error('Old private draft must not be inspected after replacement');};
  await e.ids['link-invite-form'].fire('submit');assert.equal(e.calls.filter(x=>x.name==='emitir').length,0);assert.equal(e.ids['link-recipient'].value,'');assert(e.ids['professional-link-controls'].hidden);
});
test('professional capabilities hide invitation form and produce no mutation on load',async()=>{
  const e=env('professional');e.handlers.estado=()=>({client_id:'synthetic-client',capabilities:Object.fromEntries(Object.keys(capabilities).map(k=>[k,false])),items:[],next_after:null});e.load();await flush();
  assert(e.ids['link-invite-form'].hidden);assert.deepEqual(e.calls.map(x=>x.name),['estado']);
});
test('publication choices never publish automatically and use observed CAS versions',async()=>{
  const e=env('professional');e.handlers.estado=()=>({client_id:'synthetic-client',capabilities,items:[{link_id:A,status:'active',version:17,invitation_status:'consumed',publication:{id:B,version:29,source_plan_id:41}}],next_after:null});
  e.handlers.publicar=()=>({publication_id:B,link_id:A,source_plan_id:42});e.load();await flush();assert(!e.calls.some(x=>x.name==='publicar'));
  const card=e.ids['professional-link-items'];const buttons=card.querySelectorAll('[data-mutation]');const publish=buttons.find(x=>x.textContent==='Reemplazar el plan publicado');
  const walk=x=>[x,...x.children.flatMap(walk)];walk(card).find(x=>x.tagName==='INPUT').value='42';await publish.fire('click');
  const sent=e.calls.find(x=>x.name==='publicar');assert.equal(sent.args[2],42);assert.equal(sent.args[3],17);assert.equal(sent.args[4],29);
});
test('reader selection is literal, explicit and has no personal diary writes',async()=>{
  const e=env('reader');e.load();await flush();assert.deepEqual(e.calls.map(x=>x.name),['listar']);
  await e.ids['member-links-list'].children[0].children.find(x=>x.tagName==='BUTTON').fire('click');
  assert(e.ids['member-publication-meals'].textContent.includes('Literal <img src=x onerror=alert(1)>'));assert(!e.calls.some(x=>x.name.includes('diario')));
  await e.ids['member-publication-pdf'].fire('click');const sent=e.calls.find(x=>x.name==='pdf');assert.equal(sent.args[0],A);assert.equal(sent.args[1],B);assert.equal(e.doc.downloads.length,1);
});
test('PDF resolved just before account switch produces neither BlobURL nor download',async()=>{
  const e=env('reader');e.handlers.pdf=async()=>{e.revision++;return new Blob(['%PDF-old']);};e.load();await flush();await e.ids['member-links-list'].children[0].children.find(x=>x.tagName==='BUTTON').fire('click');
  await e.ids['member-publication-pdf'].fire('click');assert.equal(e.urls.length,0);assert.equal(e.doc.downloads.length,0);assert.equal(e.ids['member-publication-meals'].textContent,'');
});
test('session event clears prepared menu and revokes its temporary URL synchronously',async()=>{
  const e=env('reader');e.load();await flush();await e.ids['member-links-list'].children[0].children.find(x=>x.tagName==='BUTTON').fire('click');await e.ids['member-publication-pdf'].fire('click');
  e.emit('metodobase-session-changed',{detail:{code:'session_storage_error'}});assert.equal(e.ids['member-publication-meals'].textContent,'');assert.equal(e.ids['member-links-list'].textContent,'');assert.equal(e.revoked.length,1);
});
test('list page error preserves prior rows and reuses the same continuation on retry',async()=>{
  const e=env('reader');let first=true;e.handlers.listar=(_c,after)=>{if(!after)return {items:[row],next_after:B};if(first){first=false;throw new Error('Synthetic query error');}return {items:[],next_after:null};};e.load();await flush();
  await e.ids['member-links-more'].fire('click');assert(e.ids['member-links-list'].textContent.includes('Synthetic gym'));await e.ids['member-links-more'].fire('click');const calls=e.calls.filter(x=>x.name==='listar');assert.equal(calls[1].args[1],B);assert.equal(calls[2].args[1],B);
});
test('revoked exact PDF surfaces error without invoking a fallback or downloading',async()=>{
  const e=env('reader');e.handlers.pdf=()=>{throw Object.assign(new Error('SYNTHETIC PRIVATE SQL DO NOT ECHO'),{status:404});};e.load();await flush();await e.ids['member-links-list'].children[0].children.find(x=>x.tagName==='BUTTON').fire('click');await e.ids['member-publication-pdf'].fire('click');
  assert.equal(e.doc.downloads.length,0);assert(!e.text().includes('SYNTHETIC PRIVATE SQL'));assert.equal(e.calls.filter(x=>x.name==='pdf').length,1);
});
test('known own consent can be withdrawn even when the publication becomes unavailable',async()=>{
  const e=env('reader');e.handlers.plan=()=>{throw Object.assign(new Error('Synthetic inactive source'),{status:404});};e.handlers.desvincular=()=>({link_id:A,status:'revoked',version:8});e.load();await flush();
  const card=e.ids['member-links-list'].children[0];await card.children.find(x=>x.textContent==='Consultar plan de este vínculo').fire('click');
  await card.children.find(x=>x.textContent==='Desvincularme de este vínculo').fire('click');const sent=e.calls.find(x=>x.name==='desvincular');assert.equal(sent.args[0],A);assert.equal(sent.args[1],7);
});
test('lost unlink ACK disables further mutations until an explicit status query',async()=>{
  const e=env('reader');e.handlers.desvincular=()=>{throw new Error('Synthetic lost ACK');};e.load();await flush();const button=e.ids['member-links-list'].children[0].children.find(x=>x.textContent==='Desvincularme de este vínculo');
  await button.fire('click');assert(button.disabled);assert.equal(e.calls.filter(x=>x.name==='desvincular').length,1);
  await e.ids['member-links-refresh'].fire('click');assert.equal(e.ids['member-links-list'].children[0].children.find(x=>x.textContent==='Desvincularme de este vínculo').disabled,false);
});
(async()=>{const results=[];for(const[name,fn]of tests){try{await fn();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:error.stack});}}console.log(JSON.stringify({scope:'Offline actual consumers and minimal DOM with fixed APIv1 doubles',passed:results.filter(x=>x.passed).length,total:results.length,results},null,2));if(results.some(x=>!x.passed))process.exitCode=1;})();
