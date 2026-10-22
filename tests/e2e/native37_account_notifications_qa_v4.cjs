/* Independent native37: real app/auth/MFA/cookie/PG; named transport/SDK doubles only. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const session=require('./native37_session_qa.cjs'),geometry=require('./mobile_heading37_qa.cjs');
const tokenFraming=require('./native37_token_framing_qa.cjs');
const {createJournal}=require('./native37_progress_qa.cjs');
const privateRoot=process.env.QA37_PRIVATE,dependencies=process.env.METODOBASE_E2E_DEPENDENCIES;
assert.ok(privateRoot&&path.isAbsolute(privateRoot));
const meta=JSON.parse(fs.readFileSync(path.join(privateRoot,'metadata.private.json'),'utf8'));
const base=meta.origin;assert.equal(base,'http://127.0.0.1:8802');
const out=path.join(privateRoot,'native37-own-output');assert.ok(!fs.existsSync(out));fs.mkdirSync(out);
const report={scope:'Independent native current37 web account/notifications. Real restricted PG/auth/MFA/cookie. Only named real-response delivery holds/loss and GIS SDK local double; no provider delivery, Actions, Linux, capacity or SLO.',producer_witness_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(privateRoot,'startup.json'))).digest('hex'),checks:[],screens:[],pageErrors:[],external_blocked:0,SDK_local_responses:0,complete:false};
const releases=[],contexts=[],states={};let browser;
const readFile=name=>JSON.parse(fs.readFileSync(name,'utf8'));
const progress=createJournal({file:path.join(privateRoot,'native37-groups.private.ndjson'),groups:18,deadlineMs:45000});
async function check(name,run){report.current_case=name;await progress.run(report.checks.length+1,run);report.checks.push({case:name,passed:true});delete report.current_case;}
function requests(page){const calls=[];page.on('request',request=>{const url=new URL(request.url());if(url.origin===base)calls.push({path:url.pathname,method:request.method(),key:request.headers()['idempotency-key']||null,body:request.method()==='PUT'?request.postData():null});});return calls;}
const count=(calls,path_,method)=>calls.filter(row=>row.path===path_&&(!method||row.method===method)).length;
const settle=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
function held(){let resolve;const promise=new Promise(yes=>resolve=yes);releases.push(resolve);return{promise,resolve};}
async function context(){
 const value=await session.createContext(browser,{viewport:{width:390,height:900},timezoneId:'America/Mexico_City',reducedMotion:'reduce',acceptDownloads:true});contexts.push(value);
 await value.addInitScript(()=>{const active=new Set();let created=0;const make=URL.createObjectURL.bind(URL),drop=URL.revokeObjectURL.bind(URL);URL.createObjectURL=blob=>{const url=make(blob);active.add(url);created++;return url;};URL.revokeObjectURL=url=>{active.delete(url);return drop(url);};window.__qa37ObjectURLCounts=()=>({created,active:active.size});});
 await value.route('**/*',async route=>{
  const url=new URL(route.request().url());if(url.origin===base)return route.continue();
  if(url.origin==='https://accounts.google.com'&&url.pathname==='/gsi/client'){
   report.SDK_local_responses++;return route.fulfill({status:200,contentType:'application/javascript',body:"window.__qaGIS37={callback:null,buttons:[]};window.google={accounts:{id:{initialize(options){window.__qaGIS37.callback=options.callback;},renderButton(target,options){const button=document.createElement('button');button.type='button';button.textContent='Google (doble local)';button.onclick=()=>options.click_listener();target.append(button);window.__qaGIS37.buttons.push(options.state);}}}};"});
  }
  report.external_blocked++;return route.abort();
 });return value;
}
// Additive private observer. No error message, full URL, query, hash, bearer or DOM values.
const observerPath=path.join(privateRoot,'page-errors-observer.private.ndjson');
fs.writeFileSync(observerPath,'',{flag:'wx'});
const observerScripts=new Set(fs.readdirSync(path.join(__dirname,'../../web/static/js')).filter(name=>name.endsWith('.js')).map(name=>'/static/js/'+name));
const observerPages=new Set(['/recordatorios','/mis-recordatorios','/cuenta/seguridad','/mi-seguridad','/configuracion','/mi-perfil','/login-gym','/login-usuario','/auth/verify-email']);
function errorObservation(error,base,allowedScripts,allowedPages,currentCase){
 const classes=new Set(['Error','TypeError','ReferenceError','SyntaxError','RangeError','URIError','EvalError']);
 const frames=[];for(const line of String(error.stack||'').split('\n').slice(1,20)){
  const match=/(https?:\/\/[^\s)]+):(\d+):(\d+)/.exec(line);if(!match)continue;
  let url;try{url=new URL(match[1]);}catch{continue;}
  if(url.origin!==base||(!allowedScripts.has(url.pathname)&&!allowedPages.has(url.pathname)))continue;
  const row={pathname:url.pathname,line:Number(match[2]),column:Number(match[3])};
  if(Number.isSafeInteger(row.line)&&row.line>0&&Number.isSafeInteger(row.column)&&row.column>0)frames.push(row);
  if(frames.length===8)break;
 }
 return {class:classes.has(error.name)?error.name:'OtherError',case:currentCase||null,frames};
}
async function trackedPage(ctx){const page=await ctx.newPage();page.on('pageerror',error=>{report.pageErrors.push({class:error.name});fs.appendFileSync(observerPath,JSON.stringify(errorObservation(error,base,observerScripts,observerPages,report.current_case))+'\n');});return page;}
async function notifications(state){await state.page.goto(base+(state.actor.audience==='gym'?'/recordatorios':'/mis-recordatorios'));await state.page.waitForFunction(()=>document.querySelector('[data-notification-status]').textContent.includes('Estado consultado.'));}
async function account(state){await state.page.goto(base+(state.actor.audience==='gym'?'/cuenta/seguridad':'/mi-seguridad'));await state.page.waitForFunction(()=>!document.querySelector('[data-account37-submit]').disabled);}
async function refreshNotifications(state){await state.page.locator('[data-notification-refresh]').click();await state.page.waitForFunction(()=>document.querySelector('[data-notification-status]').textContent.includes('Estado consultado.'));}
async function preference(state,index,enabled){
 const form=state.page.locator('[data-notification-preferences] form').nth(index);
 const boxes=form.locator('input[type=checkbox]');await boxes.nth(0).setChecked(enabled);await boxes.nth(1).check();
 const response=state.page.waitForResponse(r=>new URL(r.url()).pathname.startsWith('/api/notificaciones/preferencias/')&&r.request().method()==='PUT');
 await form.locator('button[type=submit]').click();return response;
}
async function passwordForm(state,newPassword){
 await state.page.locator('[data-account37-current]').fill(state.actor.password);
 await state.page.locator('[data-account37-new]').fill(newPassword);await state.page.locator('[data-account37-confirm]').fill(newPassword);
 await state.page.locator('[data-account37-method]').selectOption('recovery_code');await state.page.locator('[data-account37-proof]').fill(session.nextFactor(state.actor));await state.page.locator('[data-account37-explicit]').check();
}
async function screen(state,name,selector,width){
 const page=state.page;await page.setViewportSize({width,height:900});await page.locator(selector).scrollIntoViewIfNeeded();
 await page.evaluate(fs.readFileSync(path.join(dependencies,'axe-core/axe.min.js'),'utf8'));
 const result=await page.evaluate(async selector=>({overflow:document.documentElement.scrollWidth>innerWidth,violations:(await axe.run(document.querySelector(selector),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(item=>({id:item.id,targets:item.nodes.map(node=>node.target)}))}),selector);
 assert.equal(result.overflow,false);assert.deepEqual(result.violations,[]);
 await page.screenshot({path:path.join(out,name+'.png'),fullPage:false,mask:[page.locator('input'),page.locator('#mfa-account-seed'),page.locator('#mfa-account-kit')]});report.screens.push({name,width,scoped_selector:selector,...result});
}

(async()=>{try{
 const{chromium}=require(path.join(dependencies,'playwright-core'));browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
 for(const audience of['gym','usuario']){
  const ctx=await context(),page=await trackedPage(ctx),actor=meta.actors[audience+'_a'],state={ctx,page,actor,calls:requests(page)};states[audience]=state;
  await session.login(page,base,actor);
  await check(audience+'-notification-own-navigation-and-inert-source',async()=>{
   await notifications(state);const before=state.calls.filter(row=>row.method!=='GET').length;
   assert.equal(await page.locator('[data-notification-context]').getAttribute('data-notification-context'),audience==='gym'?'gym':'personal');
   assert.match(await page.locator('.notification-notice').textContent(),/envíos están desactivados/);
   assert.equal(await page.locator('[data-notification-queue] button:enabled').count(),0);await settle(page);assert.equal(state.calls.filter(row=>row.method!=='GET').length,before);
   const access=await page.evaluate(()=>Api.getToken());const response=await ctx.request.get(base+'/api/notificaciones/contexto?context='+(audience==='gym'?'personal':'gym'),{headers:{Authorization:'Bearer '+access}});assert.equal(response.status(),403);session.privateHeaders(response);
  });
  await check(audience+'-preference-is-explicit-then-manual-read',async()=>{
   const before=count(state.calls,'/api/notificaciones/preferencias/account_period_end','PUT');
   const response=await preference(state,0,true);assert.equal(response.status(),200);session.privateHeaders(response);
   await page.waitForFunction(()=>document.querySelector('[data-notification-status]').textContent.includes('servidor reconoció'));
   await settle(page);assert.equal(count(state.calls,'/api/notificaciones/preferencias/account_period_end','PUT'),before+1);
   await refreshNotifications(state);assert.match(await page.locator('[data-notification-preferences] form').first().textContent(),/activada.*Versión 1/);
  });
  await check(audience+'-metrics-and-disabled-provider-remain-explicit',async()=>{
   const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/notificaciones/observar');
   await page.locator('[data-notification-observe-confirm]').check();await page.locator('[data-notification-observe]').click();
   const denied=await response;assert.equal(denied.status(),503);session.privateHeaders(denied);
   await page.waitForFunction(()=>!document.querySelector('[data-notification-refresh]').disabled);await refreshNotifications(state);
   assert.equal(await page.locator('[data-notification-outbox] .notification-card').count(),0);
   assert.match(await page.locator('[data-notification-metrics]').textContent(),/hechos|Avances/);
  });
  await check(audience+'-public-contact-fragment-requires-explicit-confirmation',async()=>{
   await account(state);const initial=await page.evaluate(async()=>({me:await Api.auth.me(),access:Api.getToken()}));assert.ok(Number.isInteger(tokenFraming.sessionVersion(initial.access)));
   const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/security/email/request');await page.locator('[data-account37-email-request]').click();
   const issued=await response;assert.equal(issued.status(),200);session.privateHeaders(issued);assert.deepEqual(Object.keys(await issued.json()).sort(),['delivery','email_verified','expires_in_seconds']);
   const packets=fs.readdirSync(meta.mail_directory).filter(name=>name.startsWith('packet-')).map(name=>readFile(path.join(meta.mail_directory,name))).filter(row=>row.recipient===actor.email);assert.equal(packets.length,1);
   const link=new URL(packets[0].link);assert.equal(link.origin,base);assert.equal(link.pathname,'/auth/verify-email');assert.equal(link.search,'');assert.match(new URLSearchParams(link.hash.slice(1)).get('token'),/^[A-Za-z0-9_-]{43}$/);
   const anonymous=await context(),publicPage=await trackedPage(anonymous),calls=requests(publicPage);const shell=await publicPage.goto(link.toString());assert.equal(shell.status(),200);session.privateHeaders(shell);
   await publicPage.locator('#confirm-email:enabled').waitFor();assert.equal(new URL(publicPage.url()).hash,'');assert.equal(calls.filter(row=>row.method==='POST').length,0);
   assert.equal(await publicPage.evaluate(()=>typeof Api),'undefined');assert.equal((await anonymous.cookies()).some(row=>row.name==='mb_refresh_dev'),false);
   const confirmation=publicPage.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/security/email/confirm');await publicPage.locator('#confirm-email').click();const confirmed=await confirmation;assert.equal(confirmed.status(),200);session.privateHeaders(confirmed);assert.deepEqual(await confirmed.json(),{code:'account_email_confirmed',email_verified:true});await publicPage.getByText('Correo confirmado. Puedes volver a tu cuenta.',{exact:true}).waitFor();
   assert.equal(calls.filter(row=>row.path.includes('/auth/')).length,1);assert.equal((await anonymous.cookies()).some(row=>row.name==='mb_refresh_dev'),false);await anonymous.close();
   assert.equal(await page.evaluate(()=>Api.getToken()),initial.access);const current=await page.evaluate(async()=>Api.auth.me());assert.equal(current.id,initial.me.id);assert.equal(current.role,initial.me.role);assert.equal(current.team_gym_id,initial.me.team_gym_id);
   await page.locator('[data-account37-refresh]').click();await page.waitForFunction(()=>document.querySelector('[data-account37-email]').textContent.includes('contacto confirmado'));
  });
  await check(audience+'-password-current-MFA-revokes-persisted-authority-and-relogin',async()=>{
   await account(state);const oldAccess=await page.evaluate(()=>Api.getToken()),oldRefresh=(await ctx.cookies()).find(row=>row.name==='mb_refresh_dev');assert.ok(oldRefresh?.httpOnly);
   await passwordForm(state,actor.new_password);const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/security/password');await page.locator('[data-account37-submit]').click();const changed=await response;assert.equal(changed.status(),200);session.privateHeaders(changed);
   await page.getByText('La contraseña cambió y se cerraron las sesiones anteriores.',{exact:false}).waitFor();assert.equal(await page.evaluate(()=>Api.getToken()),'');assert.equal(await page.locator('[data-account37-form]').count(),0);
   assert.equal((await ctx.request.get(base+'/api/auth/me',{headers:{Authorization:'Bearer '+oldAccess}})).status(),401);
   assert.equal((await ctx.request.post(base+'/api/auth/refresh',{data:{refresh_token:oldRefresh.value}})).status(),401);
   actor.password=actor.new_password;await session.login(page,base,actor,{setup:false});
  });
 }
 await check('lost-preference-ACK-is-not-auto-replayed-and-explicit-retry-retains-key',async()=>{
  const state=states.gym;await notifications(state);let first=true;const attempts=[];
  await state.page.route(/\/api\/notificaciones\/preferencias\/confirmed_payment_issue(?:\?|$)/,async route=>{
   attempts.push({key:route.request().headers()['idempotency-key'],body:route.request().postData()});
   if(first){first=false;const response=await route.fetch();assert.equal(response.status(),200);return route.abort();}return route.continue();
  });
  const form=state.page.locator('[data-notification-preferences] form').nth(1);await form.locator('input[type=checkbox]').nth(0).check();await form.locator('input[type=checkbox]').nth(1).check();await form.locator('button[type=submit]').click();
  await state.page.locator('[data-notification-retry]:not([hidden]):enabled').waitFor();await settle(state.page);assert.equal(attempts.length,1);
  const reply=state.page.waitForResponse(r=>new URL(r.url()).pathname==='/api/notificaciones/preferencias/confirmed_payment_issue');await state.page.locator('[data-notification-retry]').click();assert.equal((await reply).status(),200);
  await state.page.waitForFunction(()=>document.querySelector('[data-notification-status]').textContent.includes('servidor reconoció'));assert.equal(attempts.length,2);assert.deepEqual(attempts[1],attempts[0]);
  await state.page.unroute(/\/api\/notificaciones\/preferencias\/confirmed_payment_issue(?:\?|$)/);await refreshNotifications(state);
  assert.match(await state.page.locator('[data-notification-preferences] form').nth(1).textContent(),/activada.*Versión 1/);
 });
 await check('late-preference-ACK-cannot-render-after-another-real-cookie-login',async()=>{
  const state=states.usuario;await notifications(state);const arrived=held(),release=held();
  await state.page.route(/\/api\/notificaciones\/preferencias\/account_period_end(?:\?|$)/,async route=>{const response=await route.fetch();assert.equal(response.status(),200);arrived.resolve();await release.promise;await route.fulfill({response});});
  const form=state.page.locator('[data-notification-preferences] form').first();await form.locator('input[type=checkbox]').nth(0).uncheck();await form.locator('input[type=checkbox]').nth(1).check();await form.locator('button[type=submit]').click();await arrived.promise;
  const newPage=await trackedPage(state.ctx);await session.login(newPage,base,meta.actors.usuario_b);release.resolve();await settle(newPage);
  assert.equal(await state.page.evaluate(()=>Api.getToken()),'');assert.equal(await state.page.getByText('El servidor reconoció la operación.',{exact:false}).count(),0);
  assert.equal((await newPage.evaluate(async()=>Api.auth.me())).id,meta.actors.usuario_b.id);await state.page.unroute(/\/api\/notificaciones\/preferencias\/account_period_end(?:\?|$)/);
 });
 let lateState;
 await check('late-password-ACK-revokes-A-but-never-clears-or-adopts-real-B',async()=>{
  const actor=meta.actors.gym_b,page=await trackedPage(states.gym.ctx);lateState={ctx:states.gym.ctx,page,actor,calls:requests(page)};await session.login(page,base,actor);await account(lateState);
  const oldAccess=await page.evaluate(()=>Api.getToken()),arrived=held(),release=held();let writes=0;
  await page.route('**/api/account/security/password',async route=>{writes++;const response=await route.fetch();assert.equal(response.status(),200);arrived.resolve();await release.promise;await route.fulfill({response});});
  await passwordForm(lateState,actor.new_password);await page.locator('[data-account37-submit]').click();await arrived.promise;actor.password=actor.new_password;
  // The cookie WebLock remains held through A's JSON; cooperating B must wait.
  const epochBefore=await page.evaluate(()=>localStorage.getItem('mb_session_epoch'));
  const other=await trackedPage(lateState.ctx),otherCalls=requests(other);
  await other.goto(base+'/login-usuario',{waitUntil:'domcontentloaded'});
  const bReady=other.evaluate(async()=>{window.__qa37BReady='pending';try{await Api.session.ready;window.__qa37BReady='fulfilled';return{state:'fulfilled'};}catch(error){window.__qa37BReady='rejected';return{state:'rejected',code:error.code||null};}}).catch(error=>({state:'evaluation_rejected',error_class:error.name}));
  await other.waitForFunction(async()=>{const state=await navigator.locks.query();return state.pending.some(row=>row.name==='metodobase.browser-session.v1');});
  await settle(other);assert.equal(await other.evaluate(()=>__qa37BReady),'pending');
  assert.equal(otherCalls.filter(row=>row.path.startsWith('/api/auth/')).length,0);
  assert.notEqual(await page.evaluate(()=>Api.getToken()),'');
  assert.equal(await page.evaluate(()=>localStorage.getItem('mb_session_epoch')),epochBefore);
  release.resolve();await page.waitForFunction(()=>Api.getToken()==='');
  assert.deepEqual(await bReady,{state:'rejected',code:'session_changed'});
  assert.notEqual(await page.evaluate(()=>localStorage.getItem('mb_session_epoch')),epochBefore);
  assert.equal(otherCalls.filter(row=>row.path.startsWith('/api/auth/')).length,0);
  const otherAccess=await session.login(other,base,meta.actors.usuario_b,{setup:false});await settle(other);
  assert.equal(writes,1);assert.equal(await page.evaluate(()=>Api.getToken()),'');assert.equal(await page.getByText('La contraseña cambió y se cerraron las sesiones anteriores.',{exact:false}).count(),0);
  const current=await lateState.ctx.request.get(base+'/api/auth/me',{headers:{Authorization:'Bearer '+otherAccess}});assert.equal(current.status(),200);assert.equal((await current.json()).id,meta.actors.usuario_b.id);
  assert.equal((await lateState.ctx.request.get(base+'/api/auth/me',{headers:{Authorization:'Bearer '+oldAccess}})).status(),401);await page.unroute('**/api/account/security/password');
 });
 await check('lost-contact-ACK-does-not-auto-resend-or-return-purpose-proof',async()=>{
  const page=await trackedPage(lateState.ctx);lateState.page=page;lateState.calls=requests(page);await session.login(page,base,lateState.actor,{setup:false});await account(lateState);let attempts=0;
  await page.route('**/api/account/security/email/request',async route=>{attempts++;const response=await route.fetch();assert.equal(response.status(),200);assert.deepEqual(Object.keys(await response.json()).sort(),['delivery','email_verified','expires_in_seconds']);await route.abort();});
  await page.locator('[data-account37-email-request]').click();await page.waitForFunction(()=>document.querySelector('[data-account37-status]').textContent.includes('El resultado es incierto'));
  await settle(page);assert.equal(attempts,1);assert.equal(await page.locator('[data-account37-email-request]').isDisabled(),true);
  assert.equal(fs.readdirSync(meta.mail_directory).filter(name=>name.startsWith('packet-')).map(name=>readFile(path.join(meta.mail_directory,name))).filter(row=>row.recipient===lateState.actor.email).length,1);
  await page.unroute('**/api/account/security/email/request');await page.locator('[data-account37-refresh]').click();await page.waitForFunction(()=>!document.querySelector('[data-account37-submit]').disabled);
 });
 await check('declared-GIS-SDK-double-cancel-and-edits-fence-stale-callbacks',async()=>{
  const {page,calls}=lateState;await account(lateState);await page.getByRole('button',{name:'Google (doble local)',exact:true}).waitFor();
  await page.locator('[data-account37-new]').fill(lateState.actor.new_password);await page.locator('[data-account37-confirm]').fill(lateState.actor.new_password);await page.locator('[data-account37-method]').selectOption('recovery_code');await page.locator('[data-account37-proof]').fill('G'.repeat(22));await page.locator('[data-account37-explicit]').check();
  const before=count(calls,'/api/auth/mfa/reauth','POST');await page.getByRole('button',{name:'Google (doble local)',exact:true}).click();const oldState=await page.evaluate(()=>__qaGIS37.buttons.at(-1));await page.locator('[data-account37-google-cancel]').click();
  await page.evaluate(state=>__qaGIS37.callback({credential:'synthetic-rejected-no-provider',state}),oldState);await settle(page);assert.equal(count(calls,'/api/auth/mfa/reauth','POST'),before);
  await page.getByRole('button',{name:'Google (doble local)',exact:true}).click();const editedState=await page.evaluate(()=>__qaGIS37.buttons.at(-1));await page.locator('[data-account37-new]').fill(lateState.actor.new_password+'edit');
  await page.evaluate(state=>__qaGIS37.callback({credential:'synthetic-rejected-no-provider',state}),editedState);await settle(page);assert.equal(count(calls,'/api/auth/mfa/reauth','POST'),before);
 });
 await check('real-navigation-pagehide-and-back-do-not-restore-private-inputs-or-submit',async()=>{
  const {page,calls}=lateState,before=count(calls,'/api/account/security/password','POST');
  await page.locator('[data-account37-current]').fill(lateState.actor.password);await page.goto(base+'/recordatorios');await page.goBack({waitUntil:'domcontentloaded'});await settle(page);
  const values=await page.locator('[data-account-security37] input').evaluateAll(nodes=>nodes.map(node=>node.value));assert.ok(values.every(value=>value===''));
  assert.equal(count(calls,'/api/account/security/password','POST'),before);assert.equal(await page.evaluate(()=>['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].every(key=>localStorage.getItem(key)===null&&sessionStorage.getItem(key)===null)),true);
 });
 await check('real-personal-export-has-own-account-and-clears-DOM-and-ObjectURLs-on-B',async()=>{
  const state=states.usuario,page=await trackedPage(state.ctx);await session.login(page,base,state.actor,{setup:false});await page.goto(base+'/mi-perfil');await page.locator('#privacy-start:enabled').waitFor();
  const downloaded=page.waitForEvent('download');await page.locator('#privacy-start').click();const download=await downloaded,file=path.join(out,'export.private.json');await download.saveAs(file);
  const data=readFile(file);assert.equal(data.account.id,state.actor.id);const encoded=JSON.stringify(data);for(const actor of Object.values(meta.actors))if(actor.id!==state.actor.id)assert.equal(encoded.includes(actor.id),false);
  for(const forbidden of['password_hash','email_verification_hash','reauthentication_token','otpauth_uri'])assert.equal(encoded.includes(forbidden),false);
  assert.ok((await page.evaluate(()=>__qa37ObjectURLCounts())).created>0);
  const other=await trackedPage(state.ctx);await session.login(other,base,meta.actors.usuario_b,{setup:false});await settle(other);
  assert.equal(await page.evaluate(()=>Api.getToken()),'');assert.equal((await page.evaluate(()=>__qa37ObjectURLCounts())).active,0);assert.equal(await page.locator('#privacy-start').count(),0);
 });
 await check('actual-both-role-reflow-heading-hit-tests-and-scoped-AA',async()=>{
  for(const audience of['gym','usuario']){
   const state=states[audience];state.page=await trackedPage(state.ctx);await session.login(state.page,base,state.actor,{setup:false});await account(state);
   for(const width of[320,390,768,1440]){await screen(state,audience+'-account-'+width,'[data-account-security37]',width);if(width<=390)await geometry.inspect(state.page,'#account37-title');}
   await notifications(state);for(const width of[320,390]){await screen(state,audience+'-notifications-'+width,'[data-notifications36]',width);await geometry.inspect(state.page,'#notifications-title');}
  }
 });
 assert.equal(report.checks.length,18);assert.deepEqual(report.pageErrors,[]);report.complete=true;
}catch(error){report.failure_class=error.name;report.failure_locations=String(error.stack||'').split('\n').filter(line=>/^\s+at /.test(line)).slice(0,6);process.exitCode=1;}
finally{report.progress=progress.close();releases.forEach(resolve=>resolve());for(const value of contexts)await value.close().catch(()=>{});session.erase();await browser?.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({complete:report.complete,groups:report.checks.length,expected:18,pageErrors:report.pageErrors.length,error_class:report.failure_class||null,own_browser_closed:true}));}})();
