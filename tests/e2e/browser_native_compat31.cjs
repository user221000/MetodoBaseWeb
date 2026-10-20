/* Native-driver composition. --compile-only never imports Playwright or starts I/O. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const allowed=new Set(['mfa31_image','mfa_ui_browser','mfa_personal_browser','dashboard_followup31_browser','daily_plan31_browser','member_link31_browser']);
const name=process.argv[2];assert.ok(allowed.has(name),'Choose an inventoried native driver');
const file=path.join(__dirname,name+'.cjs'),before=fs.readFileSync(file,'utf8');let source=before;const changes=[],normative=[];
const framing=fs.readFileSync(path.join(__dirname,'browser_compat31.cjs'),'utf8');
const{balanced,skipString}=vm.runInNewContext(framing.slice(framing.indexOf('function skipString('),framing.indexOf('const fixtureName='))+'\n({balanced,skipString})',{assert});
function replace(old,next,kind,required=false){const count=source.split(old).length-1;if(required)assert.equal(count,1,'Explicit native framing drift');if(count){source=source.split(old).join(next);changes.push({kind,count,reason:kind});}return count;}
replace("require('./mfa31_login.cjs')","require('./browser_native_session31.cjs')",'Actual MFA enrollment/factors retained; form login waits current browser bootstrap and uses no credential Storage.');
replace('await browser.newContext(','await nativeSession.createContext(browser,','Every new browser context rejects credential/identity Storage writes.');
const boundary="(()=>{const epoch=crypto.randomUUID();localStorage.setItem('mb_session_epoch',epoch);if(typeof BroadcastChannel==='function'){const channel=new BroadcastChannel('metodobase.browser-session.v1');channel.postMessage({epoch});channel.close();}dispatchEvent(new StorageEvent('storage',{key:'mb_session_epoch',newValue:epoch}));})()";
replace('Api.saveTokens(pair)',boundary,'External epoch invalidates the receiving tab synchronously; no fabricated cookie ACK or actor adoption.');
if(name==='mfa_ui_browser'){
 replace('Api.clearTokens()',boundary,'Public setup boundary remains usable after old tab invalidation; next explicit login opens a fresh page.');
 const old="assert.equal(await page.evaluate(async()=> (await Api.auth.me()).id),'synthetic-mfa-ui-other');";
 const next="assert.equal(await page.evaluate(async()=>{try{await Api.auth.me();return 'unexpected_authenticated';}catch(error){return error.code;}}),'session_changed');const preservedB=await context.request.get(base+'/api/auth/me',{headers:{Authorization:'Bearer '+pairB.token}});assert.equal(preservedB.status(),200);assert.equal((await preservedB.json()).id,'synthetic-mfa-ui-other');";
 replace(old,next,'Late confirm cannot adopt B into old tab; independent actual B Bearer proves B survived.',true);normative.push({before:old,after:next,reason:'R31 forbids automatic adoption by an invalidated tab; preserve B authority and no old kit separately.'});
 replace("if(key==='mb_token'){const error=Error('Synthetic storage fault')","if(key==='mb_session_epoch'){const error=Error('Synthetic storage fault')",'Deny the current nonsecret persistent fence instead of the retired credential read.');
 replace("new StorageEvent('storage',{key:'mb_token'})","new StorageEvent('storage',{key:'mb_session_epoch'})",'Actual epoch Storage boundary.');
}
if(name==='dashboard_followup31_browser'){
 const old="await context.addInitScript(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('unscoped-legacy-canary','preserve-exact-bytes');},owner);";
 const next="await nativeSession.migrate(context,base,owner);await context.addInitScript(()=>{localStorage.setItem('unscoped-legacy-canary','preserve-exact-bytes');});";
 replace(old,next,'Setup legacy proof migrates once under actual origin WebLock/cookie HTTP; only unrelated legacy canary is stored.',true);
 for(const[old,next]of[["assert.equal(startup.runtime_revision,'20261019_mfa');","assert.equal(startup.runtime_revision,'20261020_nutrition_profile');"],["assert.equal(startup.model_tables,32);assert.equal(startup.actual_tables,33);","assert.equal(startup.model_tables,37);assert.equal(startup.actual_tables,38);"]]){replace(old,next,'ROOT frozen fixture35 contract; concrete revision37 ORM/38 physical inclAlembic, no permissive schema comparison.',true);normative.push({before:old,after:next,reason:'Explicit current35 producer witness required; historical31 driver is retained untouched.'});}
}
if(name==='daily_plan31_browser')replace("'Bearer '+meta.pairs.person.token","'Bearer '+currentPairs.person.token",'Use the same actor current actual login access; enrollment revoked the original bootstrap proof.');
if(name==='member_link31_browser'){
 replace("Authorization:'Bearer '+localStorage.getItem('mb_token')","Authorization:'Bearer '+Api.getToken()",'Private helper reads current access RAM only.');
 replace("async url=>{const response=await fetch(url,","async url=>{await Api.session.ready;const response=await fetch(url,",'Private helper waits cookie bootstrap.');
 for(const[old,next]of[["assert.equal(Object.keys(data.manifest.collections).length,7)","assert.equal(Object.keys(data.manifest.collections).length,8)"],["assert.deepEqual(Object.keys(data.collections).sort(),['generation_requests','measurements','member_links','personal_diary','plans','profiles','purchases'])","assert.deepEqual(Object.keys(data.collections).sort(),['generation_requests','measurements','member_links','personal_diary','plans','profiles','progress_consents','purchases'])"]]){replace(old,next,'Current R33 export includes the existing eighth progress_consents collection.',true);normative.push({before:old,after:next,reason:'Current8 dataset contract, not a removal of privacy/export checks.'});}
 replace('seven datasets','eight datasets','Current report label follows R33 dataset contract.');
}
// An invalidation callback no longer receives the unused legacy pair via DevTools.
const evaluateRanges=[];
for(const match of source.matchAll(/\b[A-Za-z_]\w*\.evaluate\(/g)){
 const open=source.indexOf('(',match.index),end=balanced(source,open),args=source.slice(open+1,end-1);let split=-1;
 for(let index=0;index<args.length;index++){const char=args[index];if(char==='"'||char==="'"||char==='`')index=skipString(args,index)-1;else if('([{'.includes(char))index=balanced(args,index)-1;else if(char===','){split=index;break;}}
 if(split>=0){const callback=args.slice(0,split);if(callback.includes(boundary)&&/^\s*pair\s*=>/.test(callback)&&!(/\bpair\b/.test(callback.replace(boundary,'').replace(/^\s*pair\s*=>/,''))))evaluateRanges.push([match.index,end,source.slice(match.index,open+1)+callback.replace(/^\s*pair\s*=>/,'()=>')+')']);}
}
for(const[start,end,replacement]of evaluateRanges.reverse())source=source.slice(0,start)+replacement+source.slice(end);
if(evaluateRanges.length)changes.push({kind:'argument_framing',count:evaluateRanges.length,reason:'The external-epoch callback receives no unused credential pair; private proof stays in Node fixture RAM.'});
// Assertion comparison reverses only explicit normative changes; all others survive byte-exact.
function assertions(text){return[...text.matchAll(/\bassert\.[A-Za-z]+\(/g)].map(match=>text.slice(match.index,balanced(text,text.indexOf('(',match.index))));}
let inverse=source;for(const row of[...normative].reverse()){assert.equal(inverse.split(row.after).length,2);inverse=inverse.replace(row.after,row.before);}
const oldAssertions=assertions(before),keptAssertions=assertions(inverse);assert.deepEqual(keptAssertions,oldAssertions,'Every business assertion call outside explicit transport/schema/dataset obligations is identical');
source="'use strict';\nconst nativeSession=require('./browser_native_session31.cjs');\n"+source;
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
const metadata={companion:'browser_native_compat31',historical_driver:name+'.cjs',historical_driver_sha256:digest(before),compiled_driver_sha256:digest(source),session_helper_sha256:digest(fs.readFileSync(path.join(__dirname,'browser_native_session31.cjs'))),assertion_calls_preserved_before_normative_changes:oldAssertions.length,normative,changes,scope:'Native composition only. Driver outcomes and current35 producer witness govern execution acceptance; --compile-only proves parsing/inventory, never Chrome/HTTP/PG/layout. External epoch cases do not claim new actor adoption.'};
if(process.argv.includes('--compile-only')){new vm.Script(source,{filename:file});console.log(JSON.stringify({parsed:true,browser_session_composition:metadata},null,2));}
else{
 const reader={...fs,writeFileSync(target,value,...options){let next=value;try{const body=JSON.parse(Buffer.isBuffer(value)?value.toString('utf8'):value);if(body&&typeof body==='object'&&(Array.isArray(body.checks)||Array.isArray(body.results)||Array.isArray(body.report))){body.browser_session_composition=metadata;next=JSON.stringify(body,null,2)+'\n';}}catch{}return fs.writeFileSync(target,next,...options);}};
 const candidate=new Module(file,module);candidate.filename=file;candidate.paths=module.paths;const load=candidate.require.bind(candidate);candidate.require=id=>id==='node:fs'?reader:load(id);
 // Keep the original driver's positional arguments after the companion/name.
 process.argv=[process.argv[0],file,...process.argv.slice(3)];candidate._compile(source,file);
}
