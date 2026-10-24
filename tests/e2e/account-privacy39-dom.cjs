/* Actual Api/controller/session shell, connected minimal DOM and GIS SDK double. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),Module=require('node:module');
const root=process.argv[2]?path.resolve(process.argv[2]):path.resolve(__dirname,'../..');
const transport=path.join(root,'tests/e2e/account-privacy39-transport.cjs');
const pieces=fs.readFileSync(transport,'utf8').split('const results=[];');assert.equal(pieces.length,2);
const shared=new Module(transport,module);shared.filename=transport;shared.paths=module.paths;
shared._compile(pieces[0]+'\nmodule.exports={fixture,reply,receipt,endpoint};',transport);
const {fixture,reply,receipt,endpoint}=shared.exports;
const helpers=process.argv[3]?path.resolve(process.argv[3]):root;
const flush=async()=>{for(let n=0;n<12;n++)await new Promise(setImmediate);};
async function mounted({google=false,enabled=false,legacyWidget=false,mode='closed'}={}){
 const e=await fixture(),nodes=new Map(),scripts=[],provider={initial:null,render:null};let document;
 class Element{
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.parent=null;this.dataset={};this.events=new Map();this.value='';this.type='';this.checked=false;this.hidden=false;this.disabled=false;this._text='';this.attributes={};}
  append(...items){for(const item of items){item.parent=this;this.children.push(item);if(item.tagName==='SCRIPT')scripts.push(item);}}
  appendChild(item){this.append(item);return item;}
  before(item){if(this.parent){const at=this.parent.children.indexOf(this);item.parent=this.parent;this.parent.children.splice(at,0,item);}}
  contains(item){return this===item||this.children.some(child=>child.contains(item));}
  replaceChildren(...items){for(const child of this.children){child.parent=null;if(child.contains(document.activeElement))document.activeElement=null;}this.children=[];this._text='';this.append(...items);}
  set textContent(value){this.replaceChildren();this._text=String(value);}get textContent(){return this._text+this.children.map(child=>child.textContent).join('');}
  set innerHTML(_){throw Error('Unsafe HTML sink');}setAttribute(name,value){this.attributes[name]=String(value);}focus(){document.activeElement=this;}
  addEventListener(name,listener){if(!this.events.has(name))this.events.set(name,[]);this.events.get(name).push(listener);}
  emit(name){for(const listener of this.events.get(name)||[])listener({preventDefault(){}});}
  querySelector(selector){if(selector==='#mfa-account')return null;const match=/^\[data-privacy39-([a-z-]+)\]$/.exec(selector);const node=match?nodes.get(match[1]):null;return node&&this.contains(node)?node:null;}
  querySelectorAll(selector){const tags=selector.split(',').map(tag=>tag.toUpperCase()),found=[];function visit(node){if(tags.includes(node.tagName))found.push(node);node.children.forEach(visit);}this.children.forEach(visit);return found;}
 }
 const main=new Element('main'),element=new Element('section');main.append(element);
 element.dataset.googleClientId=google?'synthetic-google-client':'';element.dataset.loginUrl='/login-usuario';
 const markup=fs.readFileSync(path.join(root,'web/templates/_account_privacy39_content.html'),'utf8');
 for(const match of markup.matchAll(/<(\w+)\b([^>]*?)\bdata-privacy39-([a-z-]+)(?:[\s>])/g)){
  const node=new Element(match[1]);node.type=/type="([^"]+)"/.exec(match[2])?.[1]||'';nodes.set(match[3],node);
 }
 const form=nodes.get('close-form');element.append(form);
 for(const [name,node] of nodes){
  if(name==='close-form')continue;
  (['password','factor-fields','method','factor','confirm','google','google-cancel','google-status'].includes(name)?form:element).append(node);
 }
 nodes.get('method').value='totp';
 document={readyState:'loading',activeElement:null,head:new Element('head'),addEventListener(){},getElementById(){return null;},
  createElement:tag=>new Element(tag),
  querySelector:selector=>selector==='main'?main:selector.includes('csrf-token')?{content:'synthetic-csrf'}:
   selector==='script[nonce]'?{nonce:'synthetic-nonce'}:selector==='[data-account-security37]'&&legacyWidget?{}:null,
  querySelectorAll:selector=>selector==='main'?[main]:[]};
 e.control.hook=c=>{
  if(c.path==='/api/auth/me')return reply(200,{id:'A',tipo:'usuario',role:'viewer',team_gym_id:null,session_version:1});
  if(c.path==='/api/auth/mfa/status')return reply(200,{enabled,pending:false,recovery_codes_remaining:8,totp_period_seconds:30,challenge_lifetime_seconds:300});
  if(c.path==='/api/auth/mfa/reauth')return reply(200,{reauthentication_token:'P'.repeat(43),expires_at:new Date(Date.now()+60000).toISOString()});
  if(c.path==='/api/account/privacy/requests/'+receipt().id)return reply(200,receipt());
  if(c.path===endpoint&&mode==='blocked')return reply(200,{...receipt(),version:2});
  if(c.path===endpoint&&mode==='unconfirmed')return reply(503,{detail:{code:'privacy_commit_unconfirmed'}});
 };
 e.t.sandbox.document=document;e.t.sandbox.Api=e.t.api;
 e.t.sandbox.google={accounts:{id:{initialize:value=>{assert.equal(provider.initial,null);provider.initial=value;},renderButton:(_target,value)=>{provider.render=value;}}}};
 vm.runInContext(fs.readFileSync(path.join(helpers,'web/static/js/session-shell.js'),'utf8'),e.t.context);
 vm.runInContext(fs.readFileSync(path.join(root,'web/static/js/account-privacy39.js'),'utf8'),e.t.context);
 const controller=e.t.sandbox.AccountPrivacy39.mount(element);
 if(google&&!legacyWidget){assert.equal(scripts.length,1);scripts[0].onload();}
 async function ready(){assert(await controller.request());assert(await controller.prepareClose());await flush();}
 function fill(){nodes.get('password').value='synthetic primary password';nodes.get('confirm').checked=true;nodes.get('factor').value=enabled?'123456':'';}
 return{...e,nodes,main,element,document,provider,scripts,controller,ready,fill};
}
const results=[];
async function test(name,run){await run();results.push({name,passed:true});}
(async()=>{
 await test('mounted-view-does-not-create-request-or-close-automatically',async()=>{
  const e=await mounted();await flush();
  assert.equal(e.w.calls.filter(c=>c.path.startsWith('/api/account/privacy/')).length,0);
 });
 await test('password-receipt-survives-real-session-shell-retirement-as-minimal-main-content',async()=>{
  const e=await mounted();await e.ready();e.fill();e.nodes.get('close-form').emit('submit');await flush();
  assert.equal(e.t.api.getToken(),'');assert.equal(e.element.parent,null);assert.equal(e.nodes.get('password').value,'');
  assert.equal(e.nodes.get('factor').value,'');assert.equal(e.nodes.get('confirm').checked,false);
  assert.match(e.main.textContent,/Acceso de cuenta cerrado/);assert.match(e.main.textContent,/Comprobante de solicitud/);
  assert.match(e.main.textContent,/borrado integral de datos continúa sujeto/);assert.equal(e.document.activeElement,e.main.children[0]);
  assert.equal(e.w.calls.filter(c=>c.path===endpoint).length,1);
 });
 await test('ambiguous-receipt-survives-shell-without-server-or-integral-erasure-claim',async()=>{
  const e=await mounted({mode:'unconfirmed'});await e.ready();e.fill();e.nodes.get('close-form').emit('submit');await flush();
  assert.equal(e.t.api.getToken(),'');assert.match(e.main.textContent,/Resultado del cierre sin confirmar/);
  assert.doesNotMatch(e.main.textContent,/Comprobante de solicitud|Acceso de cuenta cerrado/);assert.equal(e.w.calls.filter(c=>c.path===endpoint).length,1);
 });
 await test('policy-blocked-response-keeps-connected-live-view-and-clears-secrets',async()=>{
  const e=await mounted({mode:'blocked'});await e.ready();const token=e.t.api.getToken();e.fill();e.nodes.get('close-form').emit('submit');await flush();
  assert.equal(e.t.api.getToken(),token);assert.equal(e.element.parent,e.main);assert.equal(e.nodes.get('password').value,'');
  assert.match(e.nodes.get('status').textContent,/cuenta continúa abierta/);assert.doesNotMatch(e.main.textContent,/Acceso de cuenta cerrado/);
 });
 await test('google-initializes-once-with-freshness-nonce-and-scoped-state',async()=>{
  const e=await mounted({google:true});assert.equal(e.scripts.length,1);assert.equal(e.scripts[0].nonce,'synthetic-nonce');
  assert.equal(e.provider.initial.auto_select,false);assert.equal(e.provider.initial.essential_claims,'auth_time, amr');
  assert.match(e.provider.initial.nonce,/^[0-9a-f-]{36}$/);assert.equal(e.provider.initial.ux_mode,'popup');
 });
 await test('google-requires-explicit-confirmation-before-any-primary-request',async()=>{
  const e=await mounted({google:true});await e.ready();e.provider.render.click_listener();
  assert.equal(e.w.calls.filter(c=>c.path==='/api/auth/mfa/reauth').length,0);assert.equal(e.nodes.get('google-cancel').hidden,true);
 });
 await test('linked-google-and-current-factor-close-once-through-existing-reauth-api',async()=>{
  const e=await mounted({google:true,enabled:true});await e.ready();e.fill();e.provider.render.click_listener();
  const state=e.provider.render.state;assert.match(state,/^privacy39-/);
  await e.provider.initial.callback({state,credential:'synthetic-linked-google'});await flush();
  const primary=e.w.calls.find(c=>c.path==='/api/auth/mfa/reauth'),closing=e.w.calls.find(c=>c.path===endpoint);
  assert.deepEqual(primary.body,{google_credential:'synthetic-linked-google'});assert.equal(closing.body.code,'123456');
  assert.equal(closing.body.confirmation,'close_account');assert.equal(e.w.calls.filter(c=>c.path===endpoint).length,1);
  assert.match(e.main.textContent,/Acceso de cuenta cerrado/);assert.equal(e.nodes.get('factor').value,'');
 });
 await test('edited-google-intent-discards-late-provider-callback-before-primary',async()=>{
  const e=await mounted({google:true});await e.ready();e.fill();e.provider.render.click_listener();const state=e.provider.render.state;
  e.nodes.get('confirm').checked=false;e.nodes.get('confirm').emit('input');
  await e.provider.initial.callback({state,credential:'synthetic-stale-provider'});await flush();
  assert.equal(e.w.calls.filter(c=>c.path==='/api/auth/mfa/reauth').length,0);
 });
 await test('wrong-google-state-cannot-adopt-another-attempt',async()=>{
  const e=await mounted({google:true});await e.ready();e.fill();e.provider.render.click_listener();
  await e.provider.initial.callback({state:'unrelated-provider-state',credential:'synthetic-wrong-provider'});await flush();
  assert.equal(e.w.calls.filter(c=>c.path==='/api/auth/mfa/reauth').length,0);assert.equal(e.nodes.get('google-cancel').hidden,false);
 });
 await test('escape-cancels-google-and-suppresses-its-late-response',async()=>{
  const e=await mounted({google:true});await e.ready();e.fill();e.provider.render.click_listener();const state=e.provider.render.state;let prevented=false;
  e.t.dispatch({type:'keydown',key:'Escape',preventDefault(){prevented=true;}});assert(prevented);
  assert.equal(e.document.activeElement,e.nodes.get('google-status'));
  await e.provider.initial.callback({state,credential:'synthetic-cancelled-provider'});await flush();
  assert.equal(e.w.calls.filter(c=>c.path==='/api/auth/mfa/reauth').length,0);
 });
 for(const event of['metodobase-session-changed','pagehide'])await test(event+'-clears-google-and-typed-dom-before-late-callback',async()=>{
  const e=await mounted({google:true});await e.ready();e.fill();e.provider.render.click_listener();const state=e.provider.render.state;
  e.t.dispatch({type:event});await flush();assert.equal(e.nodes.get('password').value,'');assert.equal(e.nodes.get('factor').value,'');
  assert.equal(e.nodes.get('confirm').checked,false);assert.equal(e.nodes.get('google').children.length,0);
  await e.provider.initial.callback({state,credential:'synthetic-late-provider'});await flush();
  assert.equal(e.w.calls.filter(c=>c.path==='/api/auth/mfa/reauth').length,0);
 });
 await test('legacy-security-widget-prevents-a-second-global-GIS-initialization',async()=>{
  const e=await mounted({google:true,legacyWidget:true});assert.equal(e.scripts.length,0);assert.equal(e.provider.initial,null);
 });
 await test('a-later-account-boundary-removes-the-old-minimal-closure-receipt',async()=>{
  const e=await mounted();await e.ready();e.fill();e.nodes.get('close-form').emit('submit');await flush();
  assert.match(e.main.textContent,/Comprobante de solicitud/);e.w.shared.set('mb_session_epoch','22222222-2222-4222-8222-222222222222');
  e.t.dispatch({type:'storage',key:'mb_session_epoch'});await flush();assert.doesNotMatch(e.main.textContent,/Comprobante de solicitud|Acceso de cuenta cerrado/);
 });
 process.stdout.write(JSON.stringify({scope:'Actual Api/controller/session shell in connected minimal DOM; GIS SDK and HTTP response doubles, no real provider, layout, native keyboard, browser or HTTP claim.',passed:results.length,total:results.length,results}));
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
