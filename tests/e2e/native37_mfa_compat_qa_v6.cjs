/* Native-driver composition. --compile-only never imports Playwright or starts I/O. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const allowed=new Set(['mfa_ui_browser','mfa_personal_browser']);
const name=process.argv[2];assert.ok(allowed.has(name),'Choose an inventoried native driver');
const file=path.join(__dirname,name+'.cjs'),rawBefore=fs.readFileSync(file,'utf8'),before=rawBefore.replace(/\r\n/g,'\n');let source=before;const changes=[],normative=[];
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
 for(const[old,next]of[["assert.equal(startup.runtime_revision,'20261019_mfa');","assert.equal(startup.runtime_revision,'20261020_nutrition_profile');"],["assert.equal(startup.model_tables,32);assert.equal(startup.actual_tables,33);","assert.equal(startup.model_tables,37);assert.equal(startup.actual_tables,38);"]]){replace(old,next,'ROOT frozen fixture35 contract; concrete revision37 ORM/38 physical inclAlembic, no permissive schema comparison.',true);normative.push({before:old,after:next,reason:'Explicit current37 producer witness required; historical31 driver is retained untouched.'});}
}
if(name==='daily_plan31_browser')replace("'Bearer '+meta.pairs.person.token","'Bearer '+currentPairs.person.token",'Use the same actor current actual login access; enrollment revoked the original bootstrap proof.');
if(name==='member_link31_browser'){
 replace("Authorization:'Bearer '+localStorage.getItem('mb_token')","Authorization:'Bearer '+Api.getToken()",'Private helper reads current access RAM only.');
 replace("async url=>{const response=await fetch(url,","async url=>{await Api.session.ready;const response=await fetch(url,",'Private helper waits cookie bootstrap.');
 for(const[old,next]of[["assert.equal(Object.keys(data.manifest.collections).length,7)","assert.equal(Object.keys(data.manifest.collections).length,8)"],["assert.deepEqual(Object.keys(data.collections).sort(),['generation_requests','measurements','member_links','personal_diary','plans','profiles','purchases'])","assert.deepEqual(Object.keys(data.collections).sort(),['generation_requests','measurements','member_links','personal_diary','plans','profiles','progress_consents','purchases'])"]]){replace(old,next,'Current R33 export includes the existing eighth progress_consents collection.',true);normative.push({before:old,after:next,reason:'Current8 dataset contract, not a removal of privacy/export checks.'});}
 replace('seven datasets','eight datasets','Current report label follows R33 dataset contract.');
}
if(['subscription','subscription_contract_review','gym_subscription'].includes(name)){
 const match=/await context\.addInitScript\(/.exec(source);assert.ok(match,'Historical explicit credential setup must exist');const start=match.index,open=source.indexOf('(',start),end=balanced(source,open),args=source.slice(open+1,end-1);let split=-1;
 for(let index=0;index<args.length;index++){const char=args[index];if(char==='"'||char==="'"||char==='`')index=skipString(args,index)-1;else if('([{'.includes(char))index=balanced(args,index)-1;else if(char===','){split=index;break;}}
 assert.ok(split>=0&&args.slice(0,split).includes('mb_token'));const pair=args.slice(split+1).trim();source=source.slice(0,start)+'await nativeSession.migrateWithIdentity(context,base,'+pair+')'+source.slice(end);
 changes.push({kind:'legacy_setup_migration',count:1,reason:'Actual legacy Node-RAM proof migrates through cookie HTTP under native WebLock; no access/refresh/type/name initialization in browser Storage.'});
}
if(name==='gym_subscription'){
 replace('json:{role,tipo:', 'json:{...nativeSession.identity(context),role,tipo:','Presentation role override retains an actual canonical id/session tuple, rather than an incomplete auth/me fixture.',true);
 replace("let role='owner', invalidState=null", "await nativeSession.mockSensitivePresentation(page);let role='owner', invalidState=null",'Explicit step-up response double only for this already intercepted billing presentation scenario; no MFA acceptance claim.',true);
 const old="await page.locator('[data-plan=\"standard\"].btn-plan').click();\n    await page.waitForFunction(()=>document.querySelector('[data-plan=\"standard\"].btn-plan').disabled===false);\n    assert.equal(requests.length,2)";
 const next="await page.locator('#btn-refresh-billing').click();await page.waitForFunction(()=>!document.querySelector('#btn-refresh-billing').disabled);await page.locator('[data-plan=\"standard\"].btn-plan').click();await page.waitForFunction(()=>document.querySelector('#billing-feedback').textContent.includes('incierto'));\n    assert.equal(requests.length,2)";
 replace(old,next,'MFA31 already requires explicit readback before retry after502 uncertainty. Original two-request/same-key/body assertions remain exact.',true);
 const mp="await page.locator('[data-plan=\"standard\"].btn-plan').click();\n    await page.waitForFunction(()=>document.querySelector('[data-plan=\"standard\"].btn-plan').disabled===false);\n    assert.equal(requests[2].endpoint";
 const mpNext="await page.locator('#btn-refresh-billing').click();await page.waitForFunction(()=>!document.querySelector('#btn-refresh-billing').disabled);await page.locator('[data-plan=\"standard\"].btn-plan').click();await page.waitForFunction(()=>document.querySelector('#billing-feedback').textContent.includes('incierto'));\n    assert.equal(requests[2].endpoint";
 replace(mp,mpNext,'Explicit readback releases the prior uncertain intention before choosing the existing separate provider/key; no automatic retry.',true);
}
if(['mfa_ui_browser','mfa_personal_browser'].includes(name)){
 const outputBefore=source,marker='const out=path.resolve(',start=source.indexOf(marker);assert.ok(start>=0);const open=source.indexOf('(',start),end=balanced(source,open),old=source.slice(start,end),initializer=source.slice(open+1,end-1);
 const next="const out=path.resolve(process.env.NATIVE31_BROWSER_OUTPUT||path.resolve("+initializer+"))";
 source=source.slice(0,start)+next+source.slice(end);assert.equal(source.replace(next,old),outputBefore,'Full output-framing inverse');changes.push({kind:'private_output_framing',count:1,reason:'NATIVE31_BROWSER_OUTPUT explicitly selects a fresh absolute target under the launcher-owned private/ACL parent. Existing no-overwrite assertions remain. Full inverse of this exact initializer is verified.',before:old,after:next});
 if(!process.argv.includes('--compile-only'))assert.ok(process.env.NATIVE31_BROWSER_OUTPUT,'Explicit private native output required before Chromium');
 if(process.env.NATIVE31_BROWSER_OUTPUT)assert.ok(path.isAbsolute(process.env.NATIVE31_BROWSER_OUTPUT),'Native output override must be absolute');
 const scopes={mfa_ui_browser:'Own loopback SQLite migrated31, actual password/auth/MFA and UI. Only named delivery/error holds and Stripe SDK boundary synthetic. No Google provider, PostgreSQL RLS or deployment claim.',mfa_personal_browser:'Focal personal UI/auth/MFA actual SQLite31/HTTP. Registration is real VIEWER. No Google/provider or PostgreSQL claim.'};
 replace(scopes[name],'Current37 fixture and actual browser cookie/MFA/HTTP/UI. Dialect, restricted role and RLS acceptance require the independent producer witness. Only explicitly named delivery/error and external SDK response doubles; no provider or deployment claim.','Historical dialect/revision scope is not retargeted silently; actual37 producer witness remains separate.',true);
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
const metadata={companion:'browser_native_compat31',historical_driver:name+'.cjs',historical_driver_sha256:digest(rawBefore),historical_compilation_lf_sha256:digest(before),compilation_eol:'CRLF is normalized to LF in memory only; historical RAW bytes and business assertion calls are retained.',compiled_driver_sha256:digest(source),session_helper_sha256:digest(fs.readFileSync(path.join(__dirname,'browser_native_session31.cjs'))),assertion_calls_preserved_before_normative_changes:oldAssertions.length,normative,changes,scope:'Native composition only. Driver outcomes and current37 producer witness govern execution acceptance; --compile-only proves parsing/inventory, never Chrome/HTTP/PG/layout. External epoch cases do not claim new actor adoption.'};
if(process.env.NATIVE31_PRODUCER_WITNESS){const witness=process.env.NATIVE31_PRODUCER_WITNESS;assert.ok(path.isAbsolute(witness)&&fs.statSync(witness).isFile()&&!fs.lstatSync(witness).isSymbolicLink());metadata.producer_witness={name:path.basename(witness),sha256:digest(fs.readFileSync(witness)),scope:'Binding only; typed producer schema/role/RLS validation belongs to the independent launcher.'};}
if(process.argv.includes('--compile-only')){new vm.Script(source,{filename:file});console.log(JSON.stringify({parsed:true,browser_session_composition:metadata},null,2));}
else{
 const reader={...fs,writeFileSync(target,value,...options){let next=value;try{const body=JSON.parse(Buffer.isBuffer(value)?value.toString('utf8'):value);if(body&&typeof body==='object'&&(Array.isArray(body.checks)||Array.isArray(body.results)||Array.isArray(body.report)||Array.isArray(body.cases))){body.browser_session_composition=metadata;next=JSON.stringify(body,null,2)+'\n';}}catch{}return fs.writeFileSync(target,next,...options);}};
 const candidate=new Module(file,module);candidate.filename=file;candidate.paths=module.paths;const load=candidate.require.bind(candidate);candidate.require=id=>id==='node:fs'?reader:load(id);
 // Keep the original driver's positional arguments after the companion/name.
 process.argv=[process.argv[0],file,...process.argv.slice(3)];candidate._compile(source,file);
}
