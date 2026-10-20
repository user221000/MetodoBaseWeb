/* Current browser transport companion for the preserved private ASGI/UI bridge. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),assert=require('node:assert/strict'),vm=require('node:vm');
const file=path.join(__dirname,'mfa_http_worker.cjs'),original=fs.readFileSync(file,'utf8');
const framing=fs.readFileSync(path.join(__dirname,'browser_compat31.cjs'),'utf8');
const {balanced}=vm.runInNewContext(framing.slice(framing.indexOf('function skipString('),framing.indexOf('const fixtureName='))+'\n({balanced})',{assert});
let source=original;
const start=source.indexOf(" const boot=await rpc({command:'bootstrap'})"),end=source.indexOf(' let seed=null',start);assert.ok(start>0&&end>start);
const setup=String.raw` const boot=await rpc({command:'bootstrap'}),values=new Map([['mb_token',boot.pair.token],['mb_refresh_token',boot.pair.refresh_token]]),listeners=new Map(),counts={};
 assert.equal(typeof boot.origin,'string');const origin=new URL(boot.origin).origin;assert.equal(origin,boot.origin);
 let lockTail=Promise.resolve();const storage={getItem:key=>values.get(key)||null,setItem(key,value){assert.ok(!['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].includes(key));values.set(key,String(value));},removeItem:key=>values.delete(key)};
 const window={localStorage:storage,sessionStorage:{getItem:()=>null,setItem(){throw Error('No session persistence');},removeItem(){}},addEventListener:(name,fn)=>{if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(fn);},removeEventListener:(name,fn)=>listeners.get(name)?.delete(fn),dispatchEvent:event=>{for(const fn of listeners.get(event.type)||[])fn(event);return true;},location:{origin,pathname:'/configuracion',href:''}};
 const locks={request(name,options,callback){assert.equal(name,'metodobase.browser-session.v1');const pending=lockTail.then(()=>callback({name}));lockTail=pending.catch(()=>{});return pending;}};
 const context=vm.createContext({window,Event,Date,WeakMap,URL,URLSearchParams,FormData,File,Blob,TextEncoder,AbortController,crypto:require('node:crypto').webcrypto,navigator:{locks},location:window.location,setTimeout,clearTimeout,localStorage:storage,
  fetch:async(url,options)=>{const headers={...options.headers};if(headers['X-MetodoBase-Browser']==='1')headers.Origin=origin;const reply=await rpc({command:'http',url,options:{...options,headers}});counts[reply.status]=(counts[reply.status]||0)+1;lastStatus=reply.status;lastCode=null;if(reply.status>=400){try{const code=JSON.parse(reply.body).detail?.code;if(typeof code==='string'&&/^(?:mfa_|browser_)[a-z_]+$/.test(code))lastCode=code;}catch{}}return new Response(reply.body,{status:reply.status,headers:reply.headers});}});
 for(const name of ['api.js','mfa-login.js','mfa-ui.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../../web/static/js',name),'utf8'),context);
 const api=vm.runInContext('Api',context);await api.session.ready;assert.ok(api.getToken());assert.equal(values.has('mb_token'),false);assert.equal(values.has('mb_refresh_token'),false);
 function externalInvalidate(){const next=require('node:crypto').randomUUID();values.set('mb_session_epoch',next);window.dispatchEvent(Object.assign(new Event('storage'),{key:'mb_session_epoch',newValue:next}));}
`;
source=source.slice(0,start)+setup+source.slice(end);
const late="const original=api.mfa.confirm;api.mfa.confirm=async(...args)=>{const reply=await original(...args);api.saveTokens(boot.other);return reply;};\n  await account.confirm(code);assert.equal(kitShown,0);assert.equal(values.get('mb_token'),boot.other.token);const verified=await api.mfa.context();assert.equal(verified.me.id,boot.other_id);assert.equal(account.active,false);";
const current="const original=api.mfa.confirm;api.mfa.confirm=async(...args)=>{const reply=await original(...args);externalInvalidate();return reply;};\n  await account.confirm(code);assert.equal(kitShown,0);assert.equal(api.getToken(),'');await assert.rejects(api.mfa.context(),{code:'session_changed'});const independent=await rpc({command:'http',url:'/api/auth/me',options:{method:'GET',headers:{Authorization:'Bearer '+boot.other.token}}});assert.equal(independent.status,200);const verified=JSON.parse(independent.body);assert.equal(verified.id,boot.other_id);assert.equal(account.active,false);";
assert.equal(source.split(late).length,2);source=source.replace(late,current);
// Preserve every lifecycle/business assertion. Only late-ACK adoption is superseded.
function assertions(value){return[...value.matchAll(/\bassert\.[A-Za-z]+\(/g)].map(match=>value.slice(match.index,balanced(value,value.indexOf('(',match.index))));}
const lifecycleBefore=assertions(original.slice(end).replace(late,'')),lifecycleAfter=assertions(source.slice(source.indexOf(' let seed=null')).replace(current,''));assert.deepEqual(lifecycleAfter,lifecycleBefore);
if(process.argv.includes('--compile-only')){new vm.Script(source,{filename:file});console.log(JSON.stringify({scope:'Companion compilation and preserved lifecycle assertion inventory only; actual backend HTTP not executed',preserved_lifecycle_assertion_calls:lifecycleBefore.length,late_ack:'Old tab stays RAM-empty; independent existing actor proof is verified without adopting it.',parsed:true}));}
else{const candidate=new Module(file,module);candidate.filename=file;candidate.paths=module.paths;candidate._compile(source,file);}
