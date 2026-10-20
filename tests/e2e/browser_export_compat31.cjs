/* Explicit current-browser composition of preserved export business assertions. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),Module=require('node:module'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const allowed={current33_export_context:17,current33_export_controls:21,current33_member_link_export:32,progress_export:38};
const name=process.argv[2];assert.ok(Object.hasOwn(allowed,name),'Choose an inventoried export companion');
const file=path.join(__dirname,name+'.cjs'),raw=fs.readFileSync(file,'utf8');let expanded=null;
class CaptureModule{constructor(){this.paths=module.paths;}_compile(source){assert.equal(expanded,null);expanded=source;}}
const dependencies=[];
const reader={...fs,readFileSync(filename,...options){const value=fs.readFileSync(filename,...options);dependencies.push({path:path.relative(__dirname,filename),sha256:crypto.createHash('sha256').update(value).digest('hex')});return value;}};
vm.runInNewContext(raw,{require:value=>value==='node:module'?CaptureModule:value==='node:fs'?reader:require(value),
  __filename:file,__dirname,module:{paths:module.paths},process:{env:{}},console},{filename:file});
assert.equal(typeof expanded,'string');
const framing=fs.readFileSync(path.join(__dirname,'browser_compat31.cjs'),'utf8');
const parser=framing.slice(framing.indexOf('function skipString('),framing.indexOf('const fixtureName='));
const {balanced}=vm.runInNewContext(parser+'\n({balanced})',{assert});
function assertionCalls(source){return [...source.matchAll(/\bassert\.[A-Za-z]+\(/g)].map(match=>source.slice(match.index,balanced(source,source.indexOf('(',match.index))));}
const originalAssertions=assertionCalls(expanded),start=expanded.indexOf('async function fixture('),body=expanded.indexOf('{',balanced(expanded,expanded.indexOf('(',start))),end=balanced(expanded,body);
assert.ok(start>=0&&end>start);
const fixture=String.raw`async function fixture(options={}){
 const nodes=new Map(),counts=new Map(),urls=new Map(),downloads=[],requests=[];let me={...identity},api,id=0,blobCount=0,hook=null,failNextMe=false,transport=async()=>Response.json(page());
 class Node{constructor(tag='div'){this.tagName=tag;this.children=[];this.style={};this.dataset={};this.handlers=new Map();this.hidden=false;this.disabled=false;this._text='';}get textContent(){return this._text;}set textContent(value){this._text=String(value);this.children=[];hook?.('text',this);}setAttribute(){}focus(){}append(...items){this.children.push(...items);}appendChild(item){this.children.push(item);hook?.('append',item);}remove(){}addEventListener(type,fn){this.handlers.set(type,fn);}querySelector(selector){return counts.get(selector.match(/"([^"]+)"/)?.[1])||null;}click(){if(this.tagName==='a'){downloads.push(urls.get(this.href));hook?.('click',this);}else return this.handlers.get('click')?.();}}
 const node=name=>{if(!nodes.has(name)){const value=new Node();value.id=name;nodes.set(name,value);}return nodes.get(name);};for(const name of names){const value=new Node('dd');value.dataset.exportCount=name;counts.set(name,value);}
 class LocalBlob extends Blob{constructor(...args){super(...args);blobCount++;hook?.('blob',this);}}
 class LocalURL extends URL{static createObjectURL(blob){const url='blob:synthetic-export/'+(++id);urls.set(url,blob);hook?.('url',url);return url;}static revokeObjectURL(url){urls.delete(url);}}
 const e=await require('./browser_harness31.cjs').closed(async(url,options)=>{requests.push({url,...options});if(url==='/api/auth/me'){if(failNextMe){failNextMe=false;return Response.json({},{status:401});}return Response.json(me);}if(url==='/api/auth/refresh')return Response.json({token:'synthetic-export-A2',session_mode:'browser'});return transport(url,options);},A.token);
 const context=e.context;api=e.api;for(const[key,value]of legacy)e.world.shared.set(key,value);
 const storage=context.localStorage,get=storage.getItem,set=storage.setItem,remove=storage.removeItem;
 storage.getItem=key=>{if(legacy.has(key))throw Error('Forbidden unidentified legacy read');return get(key);};storage.setItem=(key,value)=>{assert.ok(!legacy.has(key));set(key,value);};storage.removeItem=key=>{assert.ok(!legacy.has(key));remove(key);};storage.clear=()=>{throw Error('Forbidden clear');};
 const values={get:key=>key==='mb_token'?api.getToken()||undefined:key==='mb_refresh_token'?undefined:e.world.shared.get(key),keys:()=>e.world.shared.keys()};
 context.document={getElementById:node,createElement:tag=>new Node(tag),body:new Node('body')};context.Blob=LocalBlob;context.URL=LocalURL;context.SessionIdentity={ready:Promise.resolve()};context.__browserInvalidate=e.invalidate;
 if(options.recipient)node('personal-data-section').dataset.exportContext='recipient';if(options.owner)me={...identity,tipo:'gym',role:'owner'};
 vm.runInContext(source,context);await flush();assert.equal(node('privacy-start').disabled,false,'Canonical initial context must enable explicit export');
 return{api,node,counts,downloads,urls,requests,values,context,invalidate:e.invalidate,eval:code=>vm.runInContext(code,context),setMe(value){me={...value};},setHook(value){hook=value;},setTransport(fn){transport=fn;},rotate(){failNextMe=true;},event(type,detail){context.dispatchEvent({type,detail,key:type==='storage'?null:undefined});},get blobCount(){return blobCount;},async prepare(){node('privacy-start').click();await flush();},intact(){for(const[key,value]of legacy)assert.equal(e.world.shared.get(key),value);assert.ok(e.world.writes.every(value=>value.key==='mb_session_epoch'));assert.equal(e.world.shared.has('mb_token'),false);assert.equal(e.world.shared.has('mb_refresh_token'),false);},cleared(){assert.equal(node('privacy-again').hidden,true);assert.equal(node('privacy-next').hidden,true);for(const count of counts.values())assert.equal(count.textContent,'0');assert.equal(urls.size,0);assert.equal(node('privacy-start').disabled,true);}};
}`;
let compiled=expanded.slice(0,start)+fixture+expanded.slice(end);
const originalCases=expanded.slice(end),changes=[];
const substitutions=[
 ['Api.saveTokens(','__browserInvalidate(','External completed account boundary invalidates RAM synchronously; no forged cookie ACK.'],
 ['e.api.saveTokens(','e.invalidate(','External completed account boundary invalidates RAM synchronously.'],
 ["[...legacy.keys(),'mb_token','mb_refresh_token'].sort()","[...legacy.keys(),'mb_session_epoch'].sort()",'Only the nonsecret epoch persists; credential absence is additionally asserted in intact().'],
 ["if(key==='mb_token'){const error=Error('SYNTHETIC PRIVATE STORAGE')","if(key==='mb_session_epoch'){const error=Error('SYNTHETIC PRIVATE STORAGE')",'Deny the actual persistent session fence, rather than a credential key no longer read.'],
];
for(const[before,after,reason]of substitutions){const count=compiled.split(before).length-1;if(count){compiled=compiled.split(before).join(after);changes.push({before,after,count,reason});}}
const newCases=compiled.slice(compiled.indexOf('const cases=[];')),oldChecks=assertionCalls(originalCases),newChecks=assertionCalls(newCases);
assert.equal(oldChecks.length,newChecks.length,'Every original business assertion remains present');
const differences=oldChecks.flatMap((before,i)=>before===newChecks[i]?[]:[{before,after:newChecks[i]}]);
for(const difference of differences)assert.equal(difference.after,difference.before.replace("[...legacy.keys(),'mb_token','mb_refresh_token'].sort()","[...legacy.keys(),'mb_session_epoch'].sort()"),'Only the explicit credential-persistence contract is superseded');
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
const metadata={companion:'browser_export_compat31',wrapper:name,wrapper_sha256:digest(raw),dependencies,
 expanded_source_sha256:digest(expanded),compiled_source_sha256:digest(compiled),original_assertion_calls:originalAssertions.length,
 business_assertions_preserved:oldChecks.length,changed_transport_assertions:differences,changes,
 expected_cases:allowed[name],scope:'Actual current API and export consumer with VM DOM/Blob/Storage/Lock/cookie doubles. RAM observer is not Storage; no native browser, server, or PG acceptance.'};
const output=console.log;
console.log=(...args)=>{if(args.length===1){let value=args[0];if(typeof value==='string')try{value=JSON.parse(value);}catch{}if(value&&typeof value==='object'&&Number.isInteger(value.total)){assert.equal(value.total,allowed[name]);process.stdout.write(JSON.stringify({...value,browser_compatibility:metadata},null,2)+'\n');return;}}output(...args);};
if(process.env.BROWSER31_EXPORT_DEBUG_SOURCE)fs.writeFileSync(process.env.BROWSER31_EXPORT_DEBUG_SOURCE,compiled);
const candidate=new Module(file,module);candidate.filename=file;candidate.paths=module.paths;candidate._compile(compiled,file);
