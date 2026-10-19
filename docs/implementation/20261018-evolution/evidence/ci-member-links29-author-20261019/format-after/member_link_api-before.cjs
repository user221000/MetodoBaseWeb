'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.resolve(__dirname,'../../web/static/js/api.js'),'utf8');
const A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222';
const me={id:'synthetic-account',tipo:'gym',role:'owner',team_gym_id:null,session_version:1};
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};
function env(){
  const stored=new Map([['mb_token','synthetic-a'],['mb_refresh_token','synthetic-ra']]),calls=[];
  const box={Blob,URLSearchParams,setTimeout,clearTimeout,console,
    localStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},
    location:{href:''},addEventListener:()=>{},
    fetch:async(url,options)=>{calls.push({url,options});return url==='/api/auth/me'?{ok:true,status:200,json:async()=>({...me})}:box.reply(url,options);},
    reply:async()=>({ok:true,status:200,json:async()=>({synthetic:true})}),
  };box.window=box;vm.createContext(box);vm.runInContext(source+'\nglobalThis.api=Api;',box);
  return {box,api:box.api,calls};
}
const cases=[];const test=(n,f)=>cases.push([n,f]);
const checks=[
  ['issue','POST','/api/clientes/synthetic-client/vinculacion/invitaciones',{recipient_email:'synthetic@example.invalid',request_key:A},(a,c)=>a.emitir('synthetic-client','synthetic@example.invalid',A,c)],
  ['rotate','POST',`/api/clientes/synthetic-client/vinculacion/invitaciones/${A}/reenviar`,{expected_version:7},(a,c)=>a.rotar('synthetic-client',A,7,c)],
  ['professional revoke','DELETE',`/api/clientes/synthetic-client/vinculacion/${A}`,{expected_version:7},(a,c)=>a.revocar('synthetic-client',A,7,c)],
  ['publish','POST',`/api/clientes/synthetic-client/vinculacion/${A}/publicaciones`,{plan_id:41,expected_link_version:7,expected_publication_version:0,expected_publication_id:null},(a,c)=>a.publicar('synthetic-client',A,41,7,0,null,c)],
  ['withdraw','DELETE',`/api/clientes/synthetic-client/vinculacion/${A}/publicaciones/${B}`,{expected_version:3},(a,c)=>a.retirar('synthetic-client',A,B,3,c)],
  ['inspect','POST','/api/usuario/vinculaciones/invitacion',{token:'S'.repeat(43)},(a,c)=>a.inspeccionar('S'.repeat(43),c)],
  ['explicit accept','POST','/api/usuario/vinculaciones/aceptar',{token:'S'.repeat(43),expected_version:4,confirm:true},(a,c)=>a.aceptar('S'.repeat(43),4,c)],
  ['own unlink','DELETE',`/api/usuario/vinculos/${A}`,{expected_version:7},(a,c)=>a.desvincular(A,7,c)],
];
for(const [name,method,url,body,fn]of checks)test(name+' uses exact contract body and current Bearer',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();await fn(e.api.vinculos,c);const sent=e.calls.at(-1);
  assert.equal(sent.url,url);assert.equal(sent.options.method,method);assert.equal(sent.options.headers.Authorization,'Bearer synthetic-a');assert.deepEqual(JSON.parse(sent.options.body),body);
  assert(!sent.url.includes('token='));
});
test('list continuation preserves the opaque UUID and limits one page to100',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();await e.api.vinculos.listar(c,B.toUpperCase());assert.equal(e.calls.at(-1).url,`/api/usuario/vinculos?limit=100&after=${B.toUpperCase()}`);
});
test('invalid cursor cannot become a path or query parameter',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();assert.throws(()=>e.api.vinculos.listar(c,'https://invalid.example/'));assert.equal(e.calls.length,1);
});
test('changed local account blocks old-resource mutation before fetch',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();e.api.saveTokens({token:'synthetic-b',refresh_token:'synthetic-rb'});
  assert.throws(()=>e.api.vinculos.revocar('synthetic-client',A,7,c),x=>x.code==='session_changed');assert.equal(e.calls.length,1);
});
test('publication CAS fields never derive a guessed next version',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();await e.api.vinculos.publicar('synthetic-client',A,41,17,29,B,c);
  assert.deepEqual(JSON.parse(e.calls.at(-1).options.body),{plan_id:41,expected_link_version:17,expected_publication_version:29,expected_publication_id:B});
});
for(const [id,v]of [[null,1],[B,0],[undefined,0]])test('Publication ID/version pair must be explicit and consistent: '+String(id)+'/'+v,async()=>{
 const e=env(),c=await e.api.vinculos.contexto();assert.throws(()=>e.api.vinculos.publicar('synthetic-client',A,41,17,v,id,c));assert.equal(e.calls.length,1);
});
function pdfReply(chunks,{mime='application/pdf',length=null,onRead}={}){
  let index=0,cancelled=false,released=false;
  return {ok:true,status:200,headers:{get:n=>n==='Content-Type'?mime:n==='Content-Length'?length:null},
    body:{getReader:()=>({read:async()=>{onRead?.();return index<chunks.length?{done:false,value:chunks[index++]}:{done:true};},cancel:async()=>{cancelled=true;},releaseLock:()=>{released=true;}})},get cancelled(){return cancelled;},get released(){return released;}};
}
test('PDF reads only exact link/publication URL and returns a validated bounded Blob',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();const response=pdfReply([new TextEncoder().encode('%PDF-synthetic')]);e.box.reply=async()=>response;
  const blob=await e.api.vinculos.pdf(A,B,c);assert.equal(await blob.text(),'%PDF-synthetic');
  const sent=e.calls.find(x=>x.url.endsWith('/pdf'));assert.equal(sent.url,`/api/usuario/vinculos/${A}/publicaciones/${B}/pdf`);assert.equal(sent.options.headers.Authorization,'Bearer synthetic-a');assert(response.released);
});
for(const [name,reply]of [
  ['HTML',()=>pdfReply([new TextEncoder().encode('<html>')],{mime:'text/html'})],
  ['wrong signature',()=>pdfReply([new TextEncoder().encode('<html>')])],
  ['empty',()=>pdfReply([])],
  ['oversize header',()=>pdfReply([],{length:'67108865'})],
  ['oversize stream',()=>pdfReply([{byteLength:67108865}])],
])test(name+' is rejected without returning a download',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();e.box.reply=async()=>reply();await assert.rejects(e.api.vinculos.pdf(A,B,c));
});
test('new account while waiting for a PDF chunk cancels the old reader',async()=>{
  const e=env(),c=await e.api.vinculos.contexto(),held=deferred(),entered=deferred();let cancelled=false;
  e.box.reply=async()=>({ok:true,status:200,headers:{get:n=>n==='Content-Type'?'application/pdf':null},body:{getReader:()=>({read:()=>{entered.resolve();return held.promise;},cancel:async()=>{cancelled=true;},releaseLock:()=>{}})}});
  const pending=e.api.vinculos.pdf(A,B,c);await entered.promise;e.api.saveTokens({token:'synthetic-b',refresh_token:'synthetic-rb'});held.resolve({done:false,value:new TextEncoder().encode('%PDF-synthetic')});
  await assert.rejects(pending,x=>x.code==='session_changed');assert(cancelled);
});
test('retired exact publication404 has no latest or professional fallback',async()=>{
  const e=env(),c=await e.api.vinculos.contexto();e.box.reply=async()=>({ok:false,status:404});await assert.rejects(e.api.vinculos.pdf(A,B,c),x=>x.status===404);
  assert.equal(e.calls.filter(x=>x.url.endsWith('/pdf')).length,1);assert(!e.calls.some(x=>x.url.includes('/api/planes/')||x.url.includes('descargar-pdf')));
});
(async()=>{const results=[];for(const [name,fn]of cases){try{await fn();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:error.stack});}}console.log(JSON.stringify({scope:'Offline actual API helper, synthetic transport/Storage/streams',passed:results.filter(x=>x.passed).length,total:results.length,results},null,2));if(results.some(x=>!x.passed))process.exitCode=1;})();
