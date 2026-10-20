/* Re-expressed transport invariants: real current API, cookie/Lock doubles, no sockets. */
'use strict';
const assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {closed,world,tick}=require('./browser_harness31.cjs');
const tests=[],test=(name,run)=>tests.push({name,run});
const held=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};};
const yes=data=>Response.json(data),denied=()=>Response.json({},{status:401});
const rotation=()=>yes({token:'rotated-access',session_mode:'browser'});
const me=()=>({id:'synthetic-owner',role:'owner',tipo:'gym',session_version:0});
function assets(e){
 const downloads=[],urls=[],revoked=[];
 e.context.URL=class extends URL{static createObjectURL(blob){urls.push(blob);return'blob:synthetic-current';}static revokeObjectURL(value){revoked.push(value);}};
 e.context.document.createElement=()=>({click(){downloads.push(true);},remove(){}});e.context.document.body={appendChild(){}};
 e.context.setTimeout=(fn,delay)=>{const timer=setTimeout(fn,delay);timer.unref();return timer;};
 return{downloads,urls,revoked};
}
const ordinary=[
 ['client mutation',api=>api.clientes.actualizar('synthetic-client',{nombre:'Synthetic original'})],
 ['generation intent',api=>api.planes.generar('synthetic-client',3,'opciones','synthetic-original-key')],
 ['personal export',api=>api.usuario.exportarDatos()],
];
for(const[label,run]of ordinary)test('One legitimate refresh preserves the exact '+label+' method/body/key',async()=>{
 const e=await closed(async(url,options)=>url==='/api/auth/refresh'?rotation():options.headers.Authorization==='Bearer synthetic-access'?denied():yes({success:true}));
 assert.equal((await run(e.api)).success,true);const business=e.calls.filter(call=>call.url!=='/api/auth/refresh');
 assert.equal(business.length,2);assert.equal(business[0].url,business[1].url);assert.equal(business[0].method,business[1].method);assert.equal(business[0].body,business[1].body);assert.equal(business[0].headers['Idempotency-Key'],business[1].headers['Idempotency-Key']);
 const refresh=e.calls.filter(call=>call.url==='/api/auth/refresh');assert.equal(refresh.length,1);assert.equal(refresh[0].body,'{}');assert.equal(refresh[0].headers.Authorization,undefined);assert.equal(e.api.getToken(),'rotated-access');assert.equal(e.values.get('mb_refresh_token'),undefined);
});
test('Multipart retry preserves the same File bytes and never adds JSON Content-Type',async()=>{
 const e=await closed(async(url,options)=>url==='/api/auth/refresh'?rotation():options.headers.Authorization==='Bearer synthetic-access'?denied():yes({success:true}));
 await e.api.gym.uploadLogo(new File(['synthetic-original-bytes'],'synthetic.png',{type:'image/png'}));const uploads=e.calls.filter(c=>c.url==='/api/gym/logo');
 assert.equal(uploads.length,2);assert.equal(uploads[0].body,uploads[1].body);assert.equal(await uploads[1].body.get('file').text(),'synthetic-original-bytes');assert.ok(uploads.every(c=>!Object.keys(c.headers).some(k=>k.toLowerCase()==='content-type')));
});
test('Three concurrent401 requests share one cookie rotation and all settle',async()=>{
 const entered=held(),release=held();let refreshes=0;const e=await closed(async(url,options)=>{if(url==='/api/auth/refresh'){refreshes++;entered.resolve();await release.promise;return rotation();}return options.headers.Authorization==='Bearer synthetic-access'?denied():yes({success:true});});
 const pending=Promise.allSettled([1,2,3].map(n=>e.api.clientes.obtener('synthetic-'+n)));await entered.promise;release.resolve();const result=await pending;assert.ok(result.every(row=>row.status==='fulfilled'));assert.equal(refreshes,1);assert.equal(e.calls.length,7);
});
test('A late old401 uses an already rotated current access without another refresh',async()=>{
 const entered=held(),release=held();const e=await closed(async(url,options)=>{if(url==='/api/auth/refresh')return rotation();if(url.endsWith('/held')&&options.headers.Authorization==='Bearer synthetic-access'){entered.resolve();await release.promise;return denied();}return options.headers.Authorization==='Bearer synthetic-access'?denied():yes({success:true});});
 const pending=e.api.clientes.obtener('held');await entered.promise;await e.api.clientes.obtener('fast');release.resolve();assert.equal((await pending).success,true);assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,1);
});
test('A very late generation401 after two rotations preserves its original body and operation key',async()=>{
 let rotations=0;const entered=held(),release=held();const e=await closed(async(url,options)=>{if(url==='/api/auth/refresh')return yes({token:'rotated-'+(++rotations),session_mode:'browser'});if(url==='/api/generar-plan'&&options.headers.Authorization==='Bearer synthetic-access'){entered.resolve();await release.promise;return denied();}if(url.endsWith('/first')&&options.headers.Authorization==='Bearer synthetic-access'||url.endsWith('/second')&&options.headers.Authorization==='Bearer rotated-1')return denied();return yes({success:true});});
 const pending=e.api.planes.generar('synthetic-client',7,'opciones','synthetic-original-key');await entered.promise;await e.api.clientes.obtener('first');await e.api.clientes.obtener('second');release.resolve();await pending;
 const calls=e.calls.filter(c=>c.url==='/api/generar-plan');assert.equal(calls.length,2);assert.equal(calls[0].body,calls[1].body);assert.equal(calls[1].headers.Authorization,'Bearer rotated-2');assert.ok(calls.every(c=>c.headers['Idempotency-Key']==='synthetic-original-key'));assert.equal(rotations,2);
});
test('A rejected old retry cannot expire access from a later valid rotation',async()=>{
 let rotations=0;const entered=held(),release=held();const e=await closed(async(url,options)=>{if(url==='/api/auth/refresh')return yes({token:'rotated-'+(++rotations),session_mode:'browser'});if(url.endsWith('/held')){if(options.headers.Authorization==='Bearer synthetic-access')return denied();entered.resolve();await release.promise;return denied();}return options.headers.Authorization==='Bearer rotated-1'?denied():yes({success:true});});
 const pending=e.api.clientes.obtener('held'),result=Promise.allSettled([pending]);await entered.promise;await e.api.clientes.obtener('second');release.resolve();assert.equal((await result)[0].status,'rejected');assert.equal(e.api.getToken(),'rotated-2');assert.equal(rotations,2);
});
test('A successful held body remains usable after same-session cookie rotation',async()=>{
 const entered=held(),release=held();const e=await closed(async(url,options)=>{if(url==='/api/auth/refresh')return rotation();if(url.endsWith('/held'))return{ok:true,status:200,json:async()=>{entered.resolve();await release.promise;return{success:true};}};return options.headers.Authorization==='Bearer synthetic-access'?denied():yes({success:true});});
 const pending=e.api.clientes.obtener('held');await entered.promise;await e.api.clientes.obtener('fast');release.resolve();assert.equal((await pending).success,true);assert.equal(e.api.getToken(),'rotated-access');
});
for(const status of[200,401,500])test('External epoch fences delayed HTTP'+status+' before replay, rotation or data return',async()=>{
 const entered=held(),release=held();const e=await closed(async()=>{entered.resolve();await release.promise;return Response.json({synthetic:true},{status});});const pending=e.api.clientes.actualizar('old-scope',{nombre:'Synthetic original'});const result=Promise.allSettled([pending]);await entered.promise;e.invalidate();release.resolve();assert.equal((await result)[0].reason.code,'session_changed');assert.equal(e.calls.length,1);assert.equal(e.api.getToken(),'');assert.equal(e.world.jar.account,'B');assert.equal(e.window.location.href,'');
});
for(const mode of['network','json'])test('External epoch fences a late '+mode+' continuation',async()=>{
 const entered=held(),release=held();const e=await closed(async()=>mode==='network'?(entered.resolve(),await release.promise,Promise.reject(new TypeError('Synthetic delivery loss'))):{ok:true,status:200,json:async()=>{entered.resolve();await release.promise;return{synthetic:true};}});
 const pending=e.api.usuario.exportarDatos(),result=Promise.allSettled([pending]);await entered.promise;e.invalidate();release.resolve();assert.equal((await result)[0].reason.code,'session_changed');assert.equal(e.calls.length,1);assert.equal(e.api.getToken(),'');
});
for(const kind of['pdf','logo','upload'])test('A held '+kind+' body creates no URL or download after actor invalidation',async()=>{
 const entered=held(),release=held();const e=await closed(async url=>{if(url==='/api/auth/me')return yes(me());if(kind==='upload')return{ok:true,status:200,json:async()=>{entered.resolve();await release.promise;return{success:true};}};return{ok:true,status:200,headers:new Headers({'Content-Type':kind==='pdf'?'application/pdf':'image/png'}),blob:async()=>{entered.resolve();await release.promise;return new Blob([kind==='pdf'?'%PDF-synthetic':'synthetic-image']);}};});
 const rendered=assets(e),pending=kind==='pdf'?e.api.planes.descargarPorPlan(1):kind==='logo'?e.api.gym.getLogoBlob():e.api.gym.uploadLogo(new File(['synthetic'],'synthetic.png')),result=Promise.allSettled([pending]);await entered.promise;e.invalidate();release.resolve();assert.equal((await result)[0].reason.code,'session_changed');assert.equal(rendered.urls.length,0);assert.equal(rendered.downloads.length,0);
});
test('PDF and private logo GET/upload share one ordinary cookie refresh',async()=>{
 const e=await closed(async(url,options)=>{if(url==='/api/auth/refresh')return rotation();if(url==='/api/auth/me')return yes(me());if(options.headers.Authorization==='Bearer synthetic-access')return denied();if(url.endsWith('/pdf'))return new Response('%PDF-synthetic',{headers:{'Content-Type':'application/pdf'}});if(options.method==='POST')return yes({success:true,logo_url:'/api/gym/logo',has_private_logo:true});return new Response('synthetic-image',{headers:{'Content-Type':'image/png'}});});const rendered=assets(e);
 const results=await Promise.allSettled([e.api.planes.descargarPorPlan(1),e.api.gym.getLogoBlob(),e.api.gym.uploadLogo(new File(['synthetic'],'synthetic.png',{type:'image/png'}))]);assert.ok(results.every(row=>row.status==='fulfilled'));assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,1);assert.equal(rendered.downloads.length,1);
});
for(const mode of['network','invalid-json','401','500','503','legacy-marker'])test('Refresh '+mode+' settles a mixed queue and prevents subsequent automatic cookie traffic',async()=>{
 const entered=held(),release=held();const e=await closed(async url=>{if(url!=='/api/auth/refresh')return denied();entered.resolve();await release.promise;if(mode==='network')throw new TypeError('Synthetic loss');if(mode==='invalid-json')return new Response('<html/>');if(mode==='legacy-marker')return yes({token:'untrusted-access'});return Response.json({detail:{code:mode==='401'?'browser_session_unavailable':'browser_session_unconfirmed'}},{status:Number(mode)});});
 const pending=Promise.allSettled([e.api.clientes.crear({nombre:'Synthetic original'}),e.api.usuario.exportarDatos(),e.api.gym.uploadLogo(new File(['synthetic'],'synthetic.png'))]);await entered.promise;release.resolve();assert.ok((await pending).every(row=>row.status==='rejected'));assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,1);assert.equal(e.api.getToken(),'');const before=e.calls.length;await assert.rejects(e.api.auth.me());assert.equal(e.calls.length,before);
});
for(const[mode,body,status,expected]of[
 ['legacy-success',{success:true},200,false],['missing-mode',{success:true,server_confirmed:true},200,false],['missing-confirmed',{success:true,session_mode:'browser'},200,false],['string-confirmed',{success:true,session_mode:'browser',server_confirmed:'true'},200,false],['false-success',{success:false,session_mode:'browser',server_confirmed:true},200,false],['exact-confirmed',{success:true,session_mode:'browser',server_confirmed:true},200,true],['exact-local-only',{success:true,session_mode:'browser',server_confirmed:false},200,false],['true-flag503',{success:true,session_mode:'browser',server_confirmed:true},503,false],
])test('Browser logout '+mode+' clears RAM and honors only the exact machine ACK',async()=>{
 const e=await closed(async()=>Response.json(body,{status}));e.world.shared.set('mb_daily_unidentified','UNIDENTIFIED {invalid');const result=await e.api.auth.logout();assert.equal(result.state,'closed_local');assert.equal(result.server_confirmed,expected);assert.equal(e.api.getToken(),'');assert.equal(e.values.get('mb_refresh_token'),undefined);assert.equal(e.world.shared.get('mb_daily_unidentified'),'UNIDENTIFIED {invalid');assert.equal(e.calls[0].url,'/api/auth/browser/logout');assert.equal(e.calls[0].headers.Authorization,undefined);assert.equal(e.calls[0].body,'{}');
});
test('Session event contains no detail, identity, credential or server message fields',async()=>{
 const e=await closed();let events=0;e.window.addEventListener('metodobase-session-changed',event=>{events++;assert.ok(event instanceof Event);assert.equal(event.detail,undefined);assert.equal(event.bubbles,false);assert.equal(event.cancelable,false);for(const field of['token','refresh_token','access_token','credentials','code','message','email','nombre'])assert.equal(event[field],undefined);});e.invalidate();assert.equal(events,1);assert.equal(e.api.getToken(),'');
});
test('Actual history controller clears rows and cursor synchronously at the epoch boundary',async()=>{
 const e=await closed();let valid=true;const visible={textContent:''};e.context.PersonalPlanOperation={validPlanId:id=>Number.isInteger(id)&&id>0};vm.runInContext(fs.readFileSync(path.join(__dirname,'../../web/static/js/usuario-historial.js'),'utf8'),e.context);
 const personal={check(){assert.ok(valid);},invalidate(){valid=false;},read:async()=>({planes:[{id:7,synthetic_marker:'SYNTHETIC_PRIOR_ROW'}],next_cursor:'opaque-synthetic'})};const history=e.window.PersonalHistory.create({personal,onChange:view=>visible.textContent=view.rows.map(r=>r.synthetic_marker).join(','),onInvalidated:()=>visible.textContent=''});await history.load();assert.equal(history.view.rows.length,1);e.invalidate();assert.equal(visible.textContent,'');assert.equal(history.view.rows.length,0);assert.equal(history.view.hasMore,false);assert.equal(history.view.invalid,true);assert.equal(valid,false);
});
test('One failing session listener does not prevent sibling cleanup or restore old access',async()=>{
 const e=await closed();let cleaned=false;e.window.addEventListener('metodobase-session-changed',()=>{throw new Error('Synthetic listener fault');});e.window.addEventListener('metodobase-session-changed',()=>{cleaned=true;});e.invalidate();assert.equal(cleaned,true);assert.equal(e.api.getToken(),'');assert.equal(e.world.errors.length,1);const before=e.calls.length;await assert.rejects(e.api.auth.me());assert.equal(e.calls.length,before);
});
test('Reentrant private read during invalidation fails before network dispatch',async()=>{
 const e=await closed();let pending;e.window.addEventListener('metodobase-session-changed',()=>{pending=e.api.clientes.crear({nombre:'Synthetic reentrant'});});e.invalidate();await assert.rejects(pending,{code:'session_changed'});assert.equal(e.calls.length,0);
});
test('An ABA epoch sequence cannot revive an older in-flight payload',async()=>{
 const w=world(),t=w.tab();await t.api.session.ready;const entered=held(),release=held();t.hook(async c=>{if(c.path==='/api/clientes/held'){entered.resolve();await release.promise;return yes({synthetic:true});}});const pending=t.api.clientes.obtener('held'),result=Promise.allSettled([pending]);await entered.promise;const previous=w.shared.get('mb_session_epoch');w.shared.set('mb_session_epoch',crypto.randomUUID());t.dispatch({type:'storage',key:'mb_session_epoch'});w.shared.set('mb_session_epoch',previous);t.dispatch({type:'storage',key:'mb_session_epoch'});release.resolve();assert.equal((await result)[0].reason.code,'session_changed');assert.equal(t.api.getToken(),'');assert.equal(w.calls.filter(c=>c.path==='/api/clientes/held').length,1);
});
test('Unrelated Storage keys preserve current private context and untouched legacy bytes',async()=>{
 const e=await closed(async()=>yes(me())),context=await e.api.stats.contexto();e.world.shared.set('mb_daily_unidentified','UNIDENTIFIED {invalid');e.window.dispatchEvent({type:'storage',key:'mb_daily_unidentified'});e.api.stats.validarContexto(context);assert.ok(e.api.getToken());assert.equal(e.world.shared.get('mb_daily_unidentified'),'UNIDENTIFIED {invalid');
});
for(const phase of['before-write','after-write','ignored-write','readback'])test('Nonsecret epoch '+phase+' failure blocks new login authority and future private I/O',async()=>{
 const e=await closed(async()=>yes({token:'new-access',session_mode:'browser'}));const store=e.context.localStorage,set=store.setItem,get=store.getItem;let broken=false;
 store.setItem=(key,value)=>{if(key!=='mb_session_epoch')return set(key,value);if(phase==='before-write')throw new DOMException('Synthetic private detail','QuotaExceededError');if(phase==='ignored-write')return;set(key,value);broken=true;if(phase==='after-write')throw new DOMException('Synthetic private detail','SecurityError');};store.getItem=key=>{if(phase==='readback'&&broken&&key==='mb_session_epoch')throw new DOMException('Synthetic private detail','SecurityError');return get(key);};
 await assert.rejects(e.api.auth.registro({nombre:'Synthetic explicit signup'}),error=>{assert.equal(error.code,'session_storage_error');assert.equal(error.message.includes('Synthetic private'),false);return true;});assert.equal(e.api.getToken(),'');const before=e.calls.length;await assert.rejects(e.api.clientes.actualizar('new-scope',{nombre:'Synthetic intended actor'}));assert.equal(e.calls.length,before);assert.equal(e.calls.filter(c=>c.url==='/api/auth/registro').length,0);
});
test('A definitive401 after one retry expires only its still-current access and never loops',async()=>{
 const e=await closed(async url=>url==='/api/auth/refresh'?rotation():denied());await assert.rejects(e.api.clientes.obtener('synthetic-current'),{code:'session_expired'});assert.equal(e.api.getToken(),'');assert.equal(e.calls.length,3);assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,1);assert.equal(e.window.location.href,'/login-gym');
});
for(const mode of['success','network','json'])test('An externally invalidated held refresh '+mode+' cannot adopt access or replay any waiter',async()=>{
 const entered=held(),release=held();const e=await closed(async url=>{if(url!=='/api/auth/refresh')return denied();if(mode==='json')return{ok:true,status:200,json:async()=>{entered.resolve();await release.promise;return{token:'late-old-access',session_mode:'browser'};}};entered.resolve();await release.promise;if(mode==='network')throw new TypeError('Synthetic loss');return rotation();});
 const pending=Promise.allSettled([e.api.clientes.actualizar('synthetic-old',{nombre:'Synthetic old body'}),e.api.usuario.exportarDatos()]);await entered.promise;e.invalidate();release.resolve();const results=await pending;assert.ok(results.every(row=>row.status==='rejected'&&row.reason.code==='session_changed'));assert.equal(e.api.getToken(),'');assert.equal(e.world.jar.account,'B');assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,1);assert.equal(e.calls.filter(c=>c.url!=='/api/auth/refresh').length,2);
});
test('An invalidated mixed JSON/File/export queue never replays its old payload under another actor',async()=>{
 const entered=held(),release=held();const e=await closed(async url=>{if(url!=='/api/auth/refresh')return denied();entered.resolve();await release.promise;return rotation();});const pending=Promise.allSettled([e.api.clientes.crear({nombre:'Synthetic original'}),e.api.gym.uploadLogo(new File(['Synthetic original bytes'],'synthetic.png',{type:'image/png'})),e.api.usuario.exportarDatos()]);await entered.promise;e.invalidate();release.resolve();assert.ok((await pending).every(row=>row.status==='rejected'&&row.reason.code==='session_changed'));assert.equal(e.calls.length,4);assert.equal(e.api.getToken(),'');assert.equal(e.world.jar.account,'B');
});
for(const method of['loginGym','loginUsuario','registro'])test('Public '+method+'401 sends no Bearer, performs no refresh and never retains old RAM',async()=>{
 const e=await closed(async()=>denied());await assert.rejects(method==='registro'?e.api.auth.registro({nombre:'Synthetic signup'}):e.api.auth[method]('synthetic@example.invalid','synthetic-password'));assert.equal(e.calls.length,1);assert.equal(e.calls[0].headers.Authorization,undefined);assert.equal(e.calls[0].headers['X-MetodoBase-Browser'],'1');assert.equal(e.api.getToken(),'');assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,0);
});
for(const action of['info','accept'])test('Public invitation '+action+'401 sends no Bearer and cannot rotate or replay',async()=>{
 const e=await closed(async()=>denied());await assert.rejects(e.api.team[action]('I'.repeat(43),'synthetic-password'));assert.equal(e.calls.length,1);assert.equal(e.calls[0].headers.Authorization,undefined);assert.equal(e.calls.filter(c=>c.url==='/api/auth/refresh').length,0);assert.equal(e.api.getToken(),action==='info'?'synthetic-access':'');
});
test('A fresh explicit page can recover after an old page remains fenced by bootstrap failure',async()=>{
 const w=world(),old=w.tab();old.hook(()=>Response.json({token:'legacy-untrusted-access'}));await assert.rejects(old.api.session.ready);assert.equal(old.api.getToken(),'');const before=w.calls.length;await assert.rejects(old.api.clientes.crear({nombre:'Synthetic new intent'}));assert.equal(w.calls.length,before);const current=w.tab();await current.api.session.ready;await current.api.auth.registro({account:'B'});assert.ok(current.api.getToken().startsWith('access-B-'));assert.equal(old.api.getToken(),'');
});
test('Notifier dispatch failure cannot turn a confirmed current signup into a transport error',async()=>{
 const e=await closed(async()=>yes({token:'new-current-access',session_mode:'browser'}));e.window.dispatchEvent=()=>{throw new Error('Synthetic notifier failure');};const reply=await e.api.auth.registro({nombre:'Synthetic explicit signup'});e.api.session.check(e.api.session.accepted(reply));assert.equal(e.api.getToken(),'new-current-access');assert.ok(e.world.writes.every(row=>row.key==='mb_session_epoch'));
});
test('A reentrant second clear prevents an older expiry redirect without recursive notification',async()=>{
 const e=await closed(async url=>url==='/api/auth/refresh'?Response.json({detail:{code:'browser_session_unavailable'}},{status:401}):denied());let events=0;e.window.addEventListener('metodobase-session-changed',()=>{events++;e.api.clearTokens();});await assert.rejects(e.api.auth.me(),{code:'session_changed'});assert.equal(events,1);assert.equal(e.window.location.href,'');assert.equal(e.api.getToken(),'');
});
test('An expiry listener Storage failure removes trust before an old redirect can occur',async()=>{
 const e=await closed(async url=>url==='/api/auth/refresh'?Response.json({detail:{code:'browser_session_unavailable'}},{status:401}):denied());let pending,events=0;e.window.addEventListener('metodobase-session-changed',()=>{events++;e.context.localStorage.getItem=()=>{throw new DOMException('Synthetic private detail','SecurityError');};pending=e.api.auth.me().catch(error=>error);});await assert.rejects(e.api.auth.me(),{code:'session_storage_error'});await pending;assert.equal(events,2);assert.equal(e.window.location.href,'');assert.equal(e.api.getToken(),'');
});
test('Expiry chooses a portal without reading name, email or type from Storage',async()=>{
 const e=await closed(async url=>url==='/api/auth/refresh'?Response.json({detail:{code:'browser_session_unavailable'}},{status:401}):denied()),get=e.context.localStorage.getItem;e.context.localStorage.getItem=key=>{assert.ok(!['mb_nombre','mb_email','mb_tipo'].includes(key));return get(key);};await assert.rejects(e.api.auth.me(),{code:'session_expired'});assert.equal(e.window.location.href,'/login-gym');assert.equal(e.api.getToken(),'');
});
async function bounded(run){let timer;try{return await Promise.race([run,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Controlled scenario did not settle')),4000);})]);}finally{clearTimeout(timer);}}
(async()=>{const results=[];for(const entry of tests){try{await bounded(entry.run());results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,error_class:error.name,code:error.code||null,site:String(error.stack).split('\n').find(line=>line.trimStart().startsWith('at '))});}}const report={scope:'Current real API plus current history controller; offline cookie/WebLock/Storage/network doubles. These are replacement transport criteria, not retroactive PASS for historical JWT-Storage suites or native browser/backend acceptance.',passed:results.filter(row=>row.passed).length,total:results.length,results};console.log(JSON.stringify(report,null,2));if(report.passed!==report.total)process.exitCode=1;})().catch(()=>{process.exitCode=1;});
