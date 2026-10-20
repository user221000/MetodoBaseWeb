/* Independent account37 timing, privacy and GIS intent boundaries. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),Module=require('node:module'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const parent=new Module(__filename,module);parent.filename=__filename;parent.paths=module.paths;
parent._compile(fs.readFileSync('tests/e2e/security_account37_unauthorized_peer.cjs','utf8').split('\nconst tests=[],test=')[0]+'\nmodule.exports={environment,response,controller,input,passwordBody};',__filename);
const{environment,response,controller,input,passwordBody}=parent.exports;
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return{promise,resolve};};
const tick=()=>new Promise(setImmediate),flush=async()=>{for(let i=0;i<12;i++)await tick();};
const ack={code:'account_password_changed',reauthenticate:true,sessions_revoked:true};
async function fixture(){
 const world=environment(),tab=world.tab(),control={hook:null};tab.sandbox.document.querySelector=()=>({content:'synthetic-csrf'});
 tab.hook(async call=>{if(control.hook){const result=await control.hook(call);if(result)return result;}
  if(call.path==='/api/account/security')return response({email_verified:false,email_verified_at:null,verification_lifetime_seconds:1800,password_change_reauthentication:'primary_and_current_factor_if_enabled'});
  if(call.path==='/api/auth/mfa/status')return response({enabled:false,pending:false,recovery_codes_remaining:0,totp_period_seconds:30,challenge_lifetime_seconds:300});
  if(call.path==='/api/auth/mfa/reauth')return response({reauthentication_token:'A'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString()});
  if(call.path==='/api/account/security/email/request')return response({email_verified:false,delivery:'provider_accepted',expires_in_seconds:1800});
  if(call.path==='/api/account/security/password')return response(ack);return null;
 });
 await tab.api.session.ready;const{handle}=await tab.api.accountSecurity.context();const ui=controller.create({api:tab.api.accountSecurity});tab.sandbox.addEventListener('metodobase-session-changed',()=>ui.invalidate());assert.equal(await ui.load(),true);
 return{world,tab,control,ui,handle,api:tab.api.accountSecurity};
}
const tests=[],test=(name,run)=>tests.push({name,run});
test('Shared lock spans the full password JSON ACK and fences an already queued refresh',async()=>{
 const e=await fixture(),gate=deferred(),began=deferred();e.control.hook=call=>call.path.endsWith('/password')?{...response({}),json:async()=>{began.resolve();await gate.promise;return ack;}}:call.path==='/api/auth/me'?response({},401):null;
 const changing=e.api.changePassword(passwordBody(),e.handle);await began.promise;const renewing=e.tab.api.auth.me();const outcomes=Promise.allSettled([changing,renewing]);await tick();assert.equal(e.world.held,1);assert.ok(e.tab.api.getToken());assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/refresh').length,1);
 gate.resolve();const results=await outcomes;assert.equal(results[0].status,'fulfilled');assert.equal(results[1].reason.code,'session_changed');assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/refresh').length,1);assert.equal(e.world.maxHeld,1);assert.equal(e.tab.api.getToken(),'');
});
test('Password intent is captured before a different cookie action releases the shared lock',async()=>{
 const e=await fixture(),gate=deferred(),began=deferred();e.control.hook=call=>call.path.endsWith('/email/request')?{...response({}),json:async()=>{began.resolve();await gate.promise;return{email_verified:true,delivery:'not_required'};}}:null;
 const first=e.api.requestEmail(e.handle);await began.promise;const body=passwordBody(),expected=body.new_password;const second=e.api.changePassword(body,e.handle);for(const key of Object.keys(body))body[key]=null;assert.equal(e.world.calls.filter(call=>call.path.endsWith('/password')).length,0);gate.resolve();await first;await second;assert.equal(e.world.calls.find(call=>call.path.endsWith('/password')).body.new_password,expected);
});
test('Controller captures primary and new password before awaiting primary identity proof',async()=>{
 const e=await fixture(),gate=deferred(),began=deferred();e.control.hook=call=>call.path==='/api/auth/mfa/reauth'?{...response({}),json:async()=>{began.resolve();await gate.promise;return{reauthentication_token:'A'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString()};}}:null;
 const intent=input(),primary={password:'Synthetic primary before await'},expected=intent.new_password,pending=e.ui.changePassword(intent,primary);await began.promise;intent.new_password='Changed after capture';intent.confirm_password=intent.new_password;primary.password='Changed primary after capture';gate.resolve();assert.equal(await pending,true);assert.equal(e.world.calls.find(call=>call.path==='/api/auth/mfa/reauth').body.password,'Synthetic primary before await');assert.equal(e.world.calls.find(call=>call.path.endsWith('/password')).body.new_password,expected);
});
for(const path of['/api/account/security','/api/account/security/email/request','/api/account/security/password'])test('A late401 from '+path+' cannot overwrite a later identity boundary',async()=>{
 const e=await fixture(),gate=deferred(),began=deferred();e.control.hook=call=>call.path===path?{...response({},401),json:async()=>{began.resolve();await gate.promise;return{detail:{code:'account_security_identity_unavailable'}};}}:null;
 const old=path.endsWith('/password')?e.api.changePassword(passwordBody(),e.handle):path.endsWith('/request')?e.api.requestEmail(e.handle):e.api.status(e.handle);const oldResult=Promise.allSettled([old]);await began.promise;
 if(path==='/api/account/security'){
  const handle=e.tab.api.mfa.capture(),reply=await e.tab.api.mfa.primaryPassword({},handle);e.tab.api.mfa.finishLogin(reply,handle);const fresh=e.tab.api.getToken();assert.match(fresh,/^SEC-B-/);gate.resolve();await oldResult;assert.equal(e.tab.api.getToken(),fresh);
 }else{
  // Cookie-writing calls share the lock, so a native external boundary can
  // arrive first but a queued local login cannot overtake the old response.
  const external=crypto.randomUUID();e.world.disk.set('mb_session_epoch',external);e.tab.emit({type:'storage',key:'mb_session_epoch'});gate.resolve();await oldResult;assert.equal(e.world.disk.get('mb_session_epoch'),external);assert.equal(e.tab.api.getToken(),'');
 }
});
test('Wrong current primary password401 remains correctable and never dispatches password change',async()=>{
 const e=await fixture(),access=e.tab.api.getToken();e.control.hook=call=>call.path==='/api/auth/mfa/reauth'?response({detail:{code:'mfa_primary_reauthentication_required'}},401):null;
 assert.equal(await e.ui.changePassword(input(),{password:'Synthetic wrong primary'}),false);assert.equal(e.tab.api.getToken(),access);assert.equal(e.ui.active,true);assert.equal(e.world.calls.filter(call=>call.path.endsWith('/account/security/password')).length,0);
});
test('Storage denial after committed password has no usable access and no fabricated closure',async()=>{
 const e=await fixture();e.tab.sandbox.localStorage.setItem=()=>{throw new DOMException('PRIVATE_STORAGE_SENTINEL','QuotaExceededError');};let caught;try{await e.api.changePassword(passwordBody(),e.handle);}catch(error){caught=error;}assert.equal(caught?.code,'session_storage_error');assert.ok(!caught.message.includes('PRIVATE_STORAGE_SENTINEL'));assert.equal(e.tab.api.getToken(),'');assert.equal(e.world.calls.filter(call=>call.path.endsWith('/password')).length,1);
});
for(const failure of['network','invalid-json','invalid-ACK'])test('Password '+failure+' is one uncertain local closure without a server revocation claim',async()=>{
 const e=await fixture();e.control.hook=call=>{if(!call.path.endsWith('/password'))return null;if(failure==='network')throw Error('PRIVATE_TRANSPORT_SENTINEL');if(failure==='invalid-json')return{...response({}),json:async()=>{throw Error('PRIVATE_PARSE_SENTINEL');}};return response({...ack,token:'PRIVATE_UNEXPECTED_BEARER'});};
 const result=await e.api.changePassword(passwordBody(),e.handle);assert.equal(result.state,'unconfirmed');assert.equal(result.server_confirmed,false);assert.equal(e.tab.api.getToken(),'');assert.equal(e.world.calls.filter(call=>call.path.endsWith('/password')).length,1);e.api.checkClosed(result);assert.ok(!JSON.stringify(result).includes('PRIVATE_'));
});
test('Unexpected private server message and fields never become public controller text',async()=>{
 const e=await fixture();e.control.hook=call=>call.path.endsWith('/email/request')?response({detail:{code:'unknown_private_backend_code',message:'PRIVATE_SERVER_MESSAGE_SENTINEL',fields:['PRIVATE_SERVER_FIELD']}},503):null;
 assert.equal(await e.ui.requestEmail(),false);assert.equal(e.ui.view().phase,'unconfirmed');assert.ok(!JSON.stringify(e.ui.view()).includes('PRIVATE_'));assert.ok(e.world.writes.every(write=>write.key==='mb_session_epoch'));assert.equal(e.tab.sessionDisk.size,0);assert.ok(e.world.messages.every(message=>Object.keys(message).join(',')==='epoch'));
});
async function dom(){
 const e=await fixture(),nodes=new Map(),sdk={initial:null,render:null},scripts=[];let document;
 class Element{
  constructor(tag){this.tagName=tag.toUpperCase();this.dataset={};this.children=[];this.events=new Map();this.value='';this.checked=false;this.type='';this.attributes={};this.text='';}
  append(...items){for(const item of items){this.children.push(item);item.parent=this;if(item.tagName==='SCRIPT')scripts.push(item);}}appendChild(item){this.append(item);return item;}
  replaceChildren(...items){this.children=[];this.text='';this.append(...items);}set textContent(value){this.replaceChildren();this.text=String(value);}get textContent(){return this.text+this.children.map(child=>child.textContent).join('');}set innerHTML(value){throw Error('Unsafe DOM sink');}
  addEventListener(name,fn){this.events.set(name,fn);}emit(name){this.events.get(name)?.({preventDefault(){}});}focus(){document.activeElement=this;}setAttribute(name,value){this.attributes[name]=value;}
  querySelector(selector){return nodes.get(selector.slice('[data-account37-'.length,-1));}querySelectorAll(selector){return[...nodes.values()].filter(node=>selector.split(',').includes(node.tagName.toLowerCase()));}
 }
 const main=new Element('main'),root=new Element('section');root.dataset={loginUrl:'/login-gym',googleClientId:'synthetic-independent-google-client'};main.append(root);
 const markup=fs.readFileSync('web/templates/_account_security37_content.html','utf8');
 for(const match of markup.matchAll(/<(\w+)\b([^>]*?)\bdata-account37-([a-z-]+)(?:[\s>])/g)){const node=new Element(match[1]),tag=markup.slice(match.index,markup.indexOf('>',match.index)+1);node.type=/type="([^"]+)"/.exec(tag)?.[1]||'';nodes.set(match[3],node);root.append(node);}nodes.get('method').value='totp';
 document={readyState:'loading',head:new Element('head'),addEventListener(){},querySelectorAll:()=>[],createElement:tag=>new Element(tag),querySelector:selector=>selector==='main'?main:selector==='script[nonce]'?{nonce:'synthetic-finite-csp-nonce'}:{content:'synthetic-csrf'}};
 e.tab.sandbox.document=document;e.tab.sandbox.Api=e.tab.api;e.tab.sandbox.google={accounts:{id:{initialize:value=>sdk.initial=value,renderButton:(target,value)=>sdk.render=value}}};
 vm.runInContext(fs.readFileSync('web/static/js/account-security37.js','utf8'),e.tab.context);const ui=e.tab.sandbox.AccountSecurity37.mount(root,{api:e.api});await flush();assert.equal(ui.view().phase,'ready');assert.equal(scripts.length,1);scripts[0].onload();
 function fill(){nodes.get('new').value='Synthetic independent Google password37!';nodes.get('confirm').value=nodes.get('new').value;nodes.get('explicit').checked=true;}
 return{...e,nodes,sdk,scripts,ui,main,fill};
}
test('GIS SDK receives per-view nonce and captured same-attempt state',async()=>{
 const a=await dom(),b=await dom();assert.notEqual(a.sdk.initial.nonce,b.sdk.initial.nonce);assert.match(a.sdk.initial.nonce,/^[0-9a-f-]{36}$/);assert.equal(a.scripts[0].nonce,'synthetic-finite-csp-nonce');assert.equal(a.sdk.initial.essential_claims,'auth_time, amr');assert.equal(a.sdk.initial.auto_select,false);assert.notEqual(a.sdk.render.state,b.sdk.render.state);
});
test('Canceled GIS state cannot adopt the credential of a fresh provider attempt',async()=>{
 const e=await dom();e.fill();e.sdk.render.click_listener();const stale=e.sdk.render.state;e.nodes.get('google-cancel').emit('click');assert.notEqual(e.sdk.render.state,stale);e.fill();e.sdk.render.click_listener();await e.sdk.initial.callback({state:stale,credential:'PRIVATE_STALE_GOOGLE'});await flush();assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/mfa/reauth').length,0);assert.equal(e.nodes.get('google-cancel').hidden,false);
});
test('Changing the bound form after Google click rejects its late callback',async()=>{
 const e=await dom();e.fill();e.sdk.render.click_listener();const stale=e.sdk.render.state;e.nodes.get('new').value='Edited independent password37!';e.nodes.get('new').emit('input');await e.sdk.initial.callback({state:stale,credential:'PRIVATE_EDITED_GOOGLE'});await flush();assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/mfa/reauth').length,0);
});
test('GIS same-state callback replay cannot send a second primary or password request',async()=>{
 const e=await dom(),gate=deferred(),began=deferred();e.control.hook=call=>call.path==='/api/auth/mfa/reauth'?{...response({}),json:async()=>{began.resolve();await gate.promise;return{reauthentication_token:'A'.repeat(43),expires_at:new Date(Date.now()+300000).toISOString()};}}:null;
 e.fill();e.sdk.render.click_listener();const state=e.sdk.render.state,first=e.sdk.initial.callback({state,credential:'synthetic-independent-linked-google'});await began.promise;await e.sdk.initial.callback({state,credential:'synthetic-independent-linked-google'});assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/mfa/reauth').length,1);gate.resolve();await first;await flush();assert.equal(e.world.calls.filter(call=>call.path.endsWith('/account/security/password')).length,1);
});
for(const type of['pagehide','metodobase-session-changed'])test(type+' erases pending GIS intent and secret DOM before a delayed provider callback',async()=>{
 const e=await dom();e.fill();e.sdk.render.click_listener();const state=e.sdk.render.state;e.tab.emit({type});await e.sdk.initial.callback({state,credential:'PRIVATE_LATE_GOOGLE'});await flush();assert.equal(e.nodes.get('new').value,'');assert.equal(e.nodes.get('explicit').checked,false);assert.equal(e.ui.active,false);assert.equal(e.world.calls.filter(call=>call.path==='/api/auth/mfa/reauth').length,0);
});
(async()=>{const rows=[];for(const entry of tests){try{await entry.run();rows.push({case:entry.name,passed:true});}catch(error){rows.push({case:entry.name,passed:false,error_class:error.name,code:typeof error.code==='string'?error.code:null,site:String(error.stack).split('\n').find(line=>line.trimStart().startsWith('at '))});}}process.stdout.write(JSON.stringify({scope:'Actual Api/controller in independent VM and minimal DOM; transport, WebLock, Storage and GIS are doubles. No native/real-provider claim.',passed:rows.filter(row=>row.passed).length,total:rows.length,rows},null,2)+'\n');if(rows.some(row=>!row.passed))process.exitCode=1;})();
