/* Companion execution: unchanged legacy files, explicit browser harness/wire framing. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const allowed=new Set(['followup_tasks_api','nutrition35_api','google_link_api','mfa_api','mfa_state','mfa_consumers','mfa_prompt','personal_diary_api','personal_history','dashboard_followup','member_link_api','member_link_context','personal_logout_ack']);
const name=process.argv[2];assert.ok(allowed.has(name),'Choose an inventoried compatibility companion');
const file=path.join(__dirname,name+'.cjs'),raw=fs.readFileSync(file,'utf8');let before=raw;
const dependencies=[];
if(['mfa_state','mfa_consumers','mfa_prompt'].includes(name)){
  const dependency=fs.readFileSync(path.join(__dirname,'mfa_api.cjs'),'utf8'),prefix=dependency.split('const tests=[];')[0];
  dependencies.push({path:'mfa_api.cjs',sha256:crypto.createHash('sha256').update(dependency).digest('hex')});
  if(name==='mfa_state'){
    const marker='const scenarios=String.raw`',start=raw.indexOf(marker)+marker.length,end=raw.lastIndexOf('`;');
    assert.ok(start>=marker.length&&end>start);before=prefix+raw.slice(start,end);
  }else before=prefix+(name==='mfa_consumers'?"\nconst root=process.env.MFA_CONSUMER_SOURCE_ROOT||path.join(__dirname,'../..');\n":'\n')+raw.slice(raw.indexOf('class Element'));
}
let text=before;
const changes=[];
function skipString(s,i){const quote=s[i++];while(i<s.length){if(s[i]==='\\'){i+=2;continue;}if(s[i++]===quote)return i;}throw Error('Unterminated fixed fixture string');}
function balanced(s,start){const pairs={'(':')','{':'}','[':']'},stack=[pairs[s[start]]];assert.ok(stack[0]);let i=start+1;
  while(i<s.length){const c=s[i];if(c==='"'||c==="'"||c==='`'){i=skipString(s,i);continue;}if(c==='/'&&s[i+1]==='/'){i=s.indexOf('\n',i);if(i<0)throw Error('Unclosed fixture comment');continue;}if(c==='/'&&s[i+1]==='*'){i=s.indexOf('*/',i+2)+2;assert.ok(i>1);continue;}
    if(c==='/'&&/[=(:,![{;?]/.test(s.slice(0,i).trimEnd().at(-1)||'=')){i++;let cls=false;while(i<s.length){if(s[i]==='\\'){i+=2;continue;}if(s[i]==='[')cls=true;if(s[i]===']')cls=false;if(s[i++]==='/'&&!cls)break;}while(/[a-z]/i.test(s[i]||'')&&i<s.length)i++;continue;}
    if(pairs[c])stack.push(pairs[c]);else if(c===stack.at(-1)){stack.pop();if(!stack.length)return i+1;}i++;
  }throw Error('Unbalanced fixed fixture');
}
const fixtureName=['personal_history','dashboard_followup'].includes(name)?'helper':name==='member_link_api'?'env':name==='member_link_context'?'environment':'fixture';
const start=text.indexOf('function '+fixtureName+'(');assert.ok(start>=0);const parameters=text.indexOf('(',start),paramsEnd=balanced(text,parameters),bodyStart=text.indexOf('{',paramsEnd),end=balanced(text,bodyStart);
const access=(name.startsWith('mfa_')||name==='google_link_api')?'old.token':"'synthetic-access'";
let fixtureCode="async function fixture(transport){return require('./browser_harness31.cjs').closed(transport,"+access+");}";
if(name==='personal_diary_api')fixtureCode="async function fixture(){return require('./browser_harness31.cjs').closed(async url=>Response.json(url==='/api/auth/me'?{id:'synthetic-person',tipo:'usuario',role:'viewer',session_version:1}:{success:true}),'synthetic-helper-access');}";
if(name==='personal_history')fixtureCode="async function helper(){return require('./browser_harness31.cjs').closed(async url=>Response.json(url==='/api/auth/me'?{id:'synthetic-person',tipo:'usuario',role:'viewer',session_version:0}:page([])));}";
if(name==='dashboard_followup')fixtureCode="async function helper(){const e=await require('./browser_harness31.cjs').closed(async url=>Response.json(url==='/api/auth/me'?{id:'A',role:'owner',tipo:'gym',session_version:0}:payload()),'synthetic-A');return{...e,get calls(){return e.calls.map(({url,...options})=>({url,options}));}};}";
if(name==='member_link_api')fixtureCode="async function env(){let box;const e=await require('./browser_harness31.cjs').closed(async(url,options)=>url==='/api/auth/me'?Response.json({...me}):box.reply(url,options),'synthetic-a');box=e.context;box.reply=async()=>Response.json({synthetic:true});return{...e,box,get calls(){return e.calls.map(({url,...options})=>({url,options}));}};}";
if(name==='member_link_context')fixtureCode="async function environment(me=identity()){let box,failed=false;const e=await require('./browser_harness31.cjs').closed(async(url,options)=>url==='/api/auth/registro'?Response.json({token:'synthetic-access-b',session_mode:'browser'}):box.transport(url,options),'synthetic-access-a');box=e.context;box.me=me;box.transport=async()=>Response.json({...box.me});const get=box.localStorage.getItem;box.localStorage.getItem=key=>{if(failed)throw new DOMException('Synthetic Storage failure','SecurityError');return get(key);};vm.runInContext(contextSource,box);return{...e,box,stored:e.world.shared,get calls(){return e.calls.map(({url,...options})=>({url,options}));},emit:(name,event={})=>box.dispatchEvent({type:name,...event}),storageFailure:value=>{failed=value;},context:options=>box.MemberLinkContext.create(options)};}";
if(name==='personal_logout_ack'){
  fixtureCode="async function fixture(body,status=200,network=false){const reply=body?.success===true?{...body,session_mode:'browser',server_confirmed:true}:body;const e=await require('./browser_harness31.cjs').closed(async()=>{if(network)throw new TypeError('Synthetic lost response');return Response.json(reply,{status});},'synthetic-ack-access');e.world.shared.set('mb_daily_unidentified','UNIDENTIFIED {invalid');const storage=e.context.localStorage,get=storage.getItem,set=storage.setItem,remove=storage.removeItem;storage.getItem=key=>{assert.notEqual(key,'mb_daily_unidentified');return get(key);};storage.setItem=(key,value)=>{assert.notEqual(key,'mb_daily_unidentified');set(key,value);};storage.removeItem=key=>{assert.notEqual(key,'mb_daily_unidentified');remove(key);};return e;}";
  changes.push({kind:'wire_fixture',effect:'The two intended positive logout machine ACKs carry the current exact session_mode and server_confirmed flags. All malformed-body/status and uncertainty assertions stay unchanged; strict absent-marker counterexamples run in browser_session31.'});
  text=text.replace('const e=fixture(body,status,network)','const e=await fixture(body,status,network)');
}
text=text.slice(0,start)+fixtureCode+text.slice(end);
changes.push({kind:'fixture',effect:'Await current cookie bootstrap; exclude bootstrap from business call log; expose RAM observer under legacy values getter; no credential Storage writes.'});
const helper=name==='mfa_state'?'stateFixture':['mfa_consumers','mfa_prompt'].includes(name)?'mounted':null;
if(helper){
  assert.equal(text.split('function '+helper+'(').length,2);text=text.replace('function '+helper+'(','async function '+helper+'(');
  if(name==='mfa_consumers'){
    assert.equal(text.split('navigator:{clipboard:').length,2);text=text.replace('navigator:{clipboard:','navigator:{...e.context.navigator,clipboard:');
    changes.push({kind:'platform_fixture',effect:'Preserve navigator.locks while adding the clipboard test double.'});
  }
}
// Only test callbacks are made async. Synchronous assertion callbacks stay intact.
const insertions=[];
for(const match of text.matchAll(/\btest\(/g)){
  let i=match.index+5,depth=0;
  for(;i<text.length;i++){const c=text[i];if(c==='"'||c==="'"||c==='`'){i=skipString(text,i)-1;continue;}if('([{'.includes(c))depth++;if(')]}'.includes(c)){if(!depth)break;depth--;}if(c===','&&!depth){const rest=text.slice(i+1),m=/^\s*\(\)\s*=>/.exec(rest);if(m)insertions.push(i+1+rest.indexOf('('));break;}}
}
for(const position of insertions.reverse())text=text.slice(0,position)+'async '+text.slice(position);
const calls=[];
const callPattern=new RegExp('\\b(?:'+fixtureName+(helper?'|'+helper:'')+')\\(','g');
for(const match of text.matchAll(callPattern)){if(text.slice(Math.max(0,match.index-9),match.index)==='function '||text.slice(Math.max(0,match.index-6),match.index)==='await ')continue;const end=balanced(text,text.indexOf('(',match.index));calls.push([match.index,end]);}
for(const [a,b]of calls.reverse())text=text.slice(0,a)+'(await '+text.slice(a,b)+')'+text.slice(b);
changes.push({kind:'async_framing',fixture_calls:calls.length,test_callbacks:insertions.length,effect:'Business assertions unchanged; handles are captured only after the mandatory async bootstrap.'});
// Re-express synchronous credential injection as an external completed boundary.
// Only expectations about adoption/persistence change; DTO and business checks stay.
const ranges=[];
for(const match of text.matchAll(/\btest\(/g)){const end=balanced(text,text.indexOf('(',match.index));if(/,\s*async\s*\(\)\s*=>/.test(text.slice(match.index,end)))ranges.push([match.index,end]);}
for(const [a,b]of ranges.reverse()){
  let part=text.slice(a,b);const label=part.slice(0,part.indexOf('async'));
  if(name==='member_link_context'&&label.includes('explicit new login rejects')){
    const call="env.api.saveTokens({token:'synthetic-access-b',refresh_token:'synthetic-refresh-b'});";assert.equal(part.split(call).length,2);part=part.replace(call,'await env.api.auth.registro({});');
    changes.push({kind:'explicit_login_framing',case:label,effect:'A new same-tab context requires a real current browser auth ACK, never fabricated credential injection.'});
  }
  if(name==='mfa_state'&&label.includes('Cancelling a retained primary')){
    assert.equal(part.split('e.login.cancel();').length,2);part=part.replace('e.login.cancel();','await e.dispatched();e.login.cancel();');
    changes.push({kind:'dispatch_barrier',case:label,effect:'Cancel the primary after its controlled HTTP request starts, retaining the original late200 scenario across async bootstrap.'});
  }
  if(name==='mfa_prompt'&&label.includes('A missing lazy UI module')){
    assert.equal(part.split('let error;').length,2);part=part.replace('let error;','delete e.context.document;let error;');
    changes.push({kind:'platform_fixture',case:label,effect:'Keep the original absent-document lazy-module scenario; the shared browser fixture otherwise supplies a document.'});
  }
  if(name==='mfa_api'&&label.includes('Reentrant session replacement during login commit')){
    const old="(await fixture(async()=>Response.json({}))),handle=e.api.mfa.capture();";
    const next="(await fixture(async()=>Response.json({...pair('synthetic-new'),tipo:'gym'}))),handle=e.api.mfa.capture(),confirmed=await e.api.mfa.primaryPassword({},handle);";
    assert.equal(part.split(old).length,2);part=part.replace(old,next);
    const oldArgument="e.api.mfa.finishLogin(pair('synthetic-new'),handle)";assert.equal(part.split(oldArgument).length,2);part=part.replace(oldArgument,'e.api.mfa.finishLogin(confirmed,handle)');
    changes.push({kind:'ack_argument_framing',case:label,effect:'Finish consumes a real current primary ACK; a fabricated token pair is not cookie authority.'});
  }
  const boundary=/\b([a-zA-Z_]\w*)\.api\.saveTokens\(/g,found=[];
  for(const match of part.matchAll(boundary)){const end=balanced(part,part.indexOf('(',match.index));found.push({start:match.index,end:part[end]===';'?end+1:end,owner:match[1]});}
  for(const entry of found.reverse()){
    const since=part.slice(0,entry.start),nested=since.includes('addEventListener(')||name==='mfa_state',wait=/\bpending\s*=/.test(since)&&!nested?'await '+entry.owner+'.dispatched();':'';
    changes.push({kind:'external_boundary',case:label,legacy_call:part.slice(entry.start,entry.end),wait_for_observed_request:!!wait});
    part=part.slice(0,entry.start)+wait+entry.owner+'.invalidate();'+part.slice(entry.end);
  }
  if(found.length)part=part.replace(/assert\.equal\(([a-zA-Z_]\w*)\.values\.get\('mb_token'\),other\.token\)/g,(matched,owner)=>{const next="assert.equal("+owner+".api.getToken(),'')";changes.push({kind:'superseded_transport_assertion',case:label,before:matched,after:next,reason:'Another tab invalidates RAM; this tab never adopts another account token.'});return next;});
  if((name==='mfa_api'&&(label.includes('Public ')||label.includes('Public Google202')||label.includes('public202 carrying credentials')))||(name==='mfa_state'&&['Password202','Cancelling a retained primary','A lost verification503','Google202'].some(value=>label.includes(value)))){
    part=part.replace(/assert\.equal\(e\.values\.get\('mb_token'\),old\.token\)/g,matched=>{const next="assert.equal(e.api.getToken(),'')";changes.push({kind:'superseded_transport_assertion',case:label,before:matched,after:next,reason:'A primary attempt, including202/failed validation, clears access RAM and never adopts the previous cookie.'});return next;});
  }
  if(name==='mfa_state'&&label.includes('Partial Storage removal after valid ACK')){
    const previous="const remove=e.context.localStorage.removeItem;e.context.localStorage.removeItem=key=>{if(key==='mb_refresh_token'){const error=Error('Synthetic storage failure');error.name='SecurityError';throw error;}remove(key);};";
    const replacement="const write=e.context.localStorage.setItem;e.context.localStorage.setItem=(key,value)=>{if(key==='mb_session_epoch')throw new DOMException('Synthetic storage failure','SecurityError');write(key,value);};";
    assert.equal(part.split(previous).length,2);part=part.replace(previous,replacement);
    changes.push({kind:'persistence_fault_framing',case:label,effect:'Deny the actual nonsecret epoch write after ACK; credential removal is no longer a persistence step. Kit and closure assertions are unchanged.'});
  }
  text=text.slice(0,a)+part+text.slice(b);
}
function assertions(source){return [...source.matchAll(/\bassert\.[A-Za-z]+\(/g)].map(match=>source.slice(match.index,balanced(source,source.indexOf('(',match.index))));}
const oldAssertions=assertions(before),newAssertions=assertions(text);
assert.equal(oldAssertions.length,newAssertions.length,'No business assertion may be deleted');
const differences=oldAssertions.flatMap((old,i)=>old===newAssertions[i]?[]:[{before:old,after:newAssertions[i]}]);
for(const difference of differences){
  const explicit=changes.some(row=>row.kind==='superseded_transport_assertion'&&row.before===difference.before&&row.after===difference.after);
  const boundary=changes.some(row=>row.kind==='external_boundary'&&difference.before.includes(row.legacy_call)&&difference.after.includes('.invalidate();'));
  const ack=changes.some(row=>row.kind==='ack_argument_framing')&&difference.before.includes('mfa.finishLogin(')&&difference.after.includes('mfa.finishLogin(confirmed,handle)');
  assert.ok(explicit||boundary||ack,'Only inventoried transport/ACK framing may change');
}
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
const metadata={companion:'browser_compat31',legacy_source:name+'.cjs',legacy_source_sha256:digest(raw),dependencies,compiled_browser_sha256:digest(text),assertion_calls_preserved:oldAssertions.length,changed_transport_assertions:differences,changes,scope:'Actual current api.js with WebLock/cookie/Storage doubles and legacy business assertions. RAM observer is not persisted Storage. No HTTP/native-browser acceptance.'};
if(process.env.BROWSER31_DEBUG_SITE==='1')text=text.replaceAll('error_class:error.name','error_class:error.name,error_site:String(error.stack).split("\\n").find(line=>line.trimStart().startsWith("at "))');
if(process.env.BROWSER31_DEBUG_SOURCE)fs.writeFileSync(process.env.BROWSER31_DEBUG_SOURCE,text);
const originalLog=console.log;
console.log=(...args)=>{if(args.length===1){let value=args[0];if(typeof value==='string')try{value=JSON.parse(value);}catch{}if(value&&typeof value==='object'&&Number.isInteger(value.total)){process.stdout.write(JSON.stringify({...value,browser_compatibility:metadata},null,2)+'\n');return;}}originalLog(...args);};
const candidate=new Module(file,module);candidate.filename=file;candidate.paths=module.paths;candidate._compile(text,file);
