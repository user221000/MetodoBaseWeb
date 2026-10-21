/* New actual SaaS/SQLite37 browser acceptance. --compile-only starts no I/O. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),Module=require('node:module');
const {spawnSync}=require('node:child_process');
const widths=Object.freeze([320,390,768,1440]);
const scenarios=Object.freeze([['owner','gym','/rutinas'],['personal','personal','/mis-rutinas'],['viewer','gym','/rutinas'],['viewer','personal','/mis-rutinas']]);
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
if(process.argv.includes('--compile-only')){
 process.stdout.write(JSON.stringify({scope:'Driver compilation/finite plan only; no Playwright, HTTP, SQL, Chrome or server',widths,scenarios:scenarios.length,planned_scoped_captures:16,actual_browser_started:false})+'\n');
}else{
 main().catch(error=>{process.stderr.write(error.name+'\n');process.exitCode=1;});
}
async function main(){
 assert.ok(process.argv.includes('--run'),'Explicit --run and a separate Root lease are required');
 const fixture=path.resolve(process.env.ROUTINES37_FIXTURE_PRIVATE||'');
 const ackPath=process.env.ROUTINES37_ROOT_ACK;
 assert.ok(path.isAbsolute(fixture)&&path.basename(fixture).startsWith('metodobase-test-routines37-'));
 const metadata=JSON.parse(fs.readFileSync(path.join(fixture,'metadata.private.json'))),base=metadata.origin;
 assert.equal(base,'http://127.0.0.1:8812');assert.match(metadata.source_commit,/^[0-9a-f]{40}$/);
 const self=hash(fs.readFileSync(__filename)),server=hash(fs.readFileSync(path.join(__dirname,'security_routines37_server_peer.py')));
 const dependencies=path.resolve(process.env.ROUTINES37_NODE_DEPS||'F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules');
 const chrome=path.resolve(process.env.ROUTINES37_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe');
 function lease(){
  const value=JSON.parse(fs.readFileSync(ackPath,'utf8')),until=Date.parse(value.expires_at_UTC),remaining=until-Date.now();
  assert.equal(value.approved,true);assert.equal(value.scope,'routines37-saas-sqlite-native-exclusive-v1');
  assert.equal(value.source_commit,metadata.source_commit);assert.equal(value.private_directory,fixture);
  assert.equal(value.fixture_sha256,server);assert.equal(value.driver_sha256,self);assert.equal(value.port,8812);
  assert.equal(value.node_dependencies_directory,dependencies);assert.equal(value.chrome_executable,chrome);
  assert.equal(value.chrome_executable_sha256,hash(fs.readFileSync(chrome)));
  assert.ok(Number.isFinite(until)&&remaining>0&&remaining<=4*3600000,'Root native lease must remain finite before the next phase');
 }
 lease();
 const out=path.join(fixture,'browser');assert.equal(fs.existsSync(out),false);fs.mkdirSync(out,{mode:0o700});
 const {chromium}=require(path.join(dependencies,'playwright-core'));
 const nativeSession=require('./browser_native_session31.cjs');
 // Export only existing pure fixture ports. Original enrollment/assertions are unchanged.
 const original=path.join(__dirname,'mfa31_login.cjs'),authSource=fs.readFileSync(original,'utf8');
 const authModule=new Module(original,module);authModule.filename=original;authModule.paths=module.paths;
 authModule._compile(authSource+'\nmodule.exports={...module.exports,enroll,nextCode};',original);
 const auth=authModule.exports;
 const report={scope:'New SaaS current37 SQLite, real HTTP/password/MFA/cookies/RAM and native DOM/layout; no PG/RLS/provider claim',source_commit:metadata.source_commit,driver_sha256:self,checks:[],captures:[],pageErrors:[],complete:false};
 const write=(name,value)=>fs.writeFileSync(path.join(out,name),JSON.stringify(value,null,2));
 let browser;const contexts=[];
 async function step(name,run){lease();await run();report.checks.push({case:name,passed:true});process.stdout.write(JSON.stringify({progress:report.checks.length,case:name})+'\n');}
 async function context(){
  const value=await nativeSession.createContext(browser,{viewport:{width:390,height:900},timezoneId:'America/Mexico_City',reducedMotion:'reduce'});
  contexts.push(value);await value.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());return value;
 }
 async function login(page,key){
  const actor=metadata.actors[key];await auth.enroll(page.request,base,actor.email,actor.password);
  await page.goto(base+'/login-'+actor.audience,{waitUntil:'domcontentloaded'});await nativeSession.ready(page);
  await page.locator('#loginForm [name=email]').fill(actor.email);await page.locator('#loginForm [name=password]').fill(actor.password);
  const primary=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login'&&r.request().method()==='POST');
  await page.locator('#loginForm [name=password]').press('Enter');const response=await primary;assert.equal(response.status(),202);
  const challenge=await response.json();assert.equal(challenge.session_mode,'browser');assert.equal(Object.hasOwn(challenge,'token'),false);assert.equal(Object.hasOwn(challenge,'refresh_token'),false);
  await page.locator('#mfa-login-factor').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>Api.getToken()),'');
  await page.locator('#mfa-login-method').selectOption('recovery_code');await page.locator('#mfa-login-recovery').fill(auth.nextCode(actor.email));
  const verified=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/mfa/login/verify'&&r.request().method()==='POST');
  await page.locator('#mfa-login-factor button[type=submit]').click();const final=await verified;assert.equal(final.status(),200);
  const body=await final.json();assert.equal(body.session_mode,'browser');assert.equal(Object.hasOwn(body,'refresh_token'),false);
  await page.waitForURL(url=>['/dashboard','/mi-plan','/equipo/inicio'].includes(url.pathname));await nativeSession.ready(page);
  const identity=await page.evaluate(async()=>({id:(await Api.auth.me()).id,access:!!Api.getToken(),clean:['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].every(key=>localStorage.getItem(key)===null&&sessionStorage.getItem(key)===null)}));
  assert.equal(identity.id,actor.id);assert.equal(identity.access,true);assert.equal(identity.clean,true);
 }
 async function catalogue(page,route,scope){
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/rutinas/catalogo'&&new URL(r.url()).searchParams.get('context')===scope);
  await page.goto(base+route,{waitUntil:'domcontentloaded'});const reply=await pending;assert.equal(reply.status(),200);
  assert.equal(reply.headers()['cache-control'],'no-store');assert.equal(reply.headers()['referrer-policy'],'no-referrer');
  const data=await reply.json();assert.equal(data.scope,scope);assert.deepEqual(data.program.sessions.map(s=>s.exercises.length),[4,4,5]);
  await page.locator('[data-routine-content]').waitFor({state:'visible'});assert.equal(await page.locator('[data-routine-sessions] details').count(),13);
 }
 async function capture(page,name,width){
  await page.setViewportSize({width,height:900});
  await page.evaluate(source=>{if(!window.axe){const script=document.createElement('script');script.nonce=document.querySelector('script[nonce]').nonce;script.textContent=source;document.head.append(script);}},fs.readFileSync(path.join(dependencies,'axe-core/axe.min.js'),'utf8'));
  const value=await page.evaluate(async()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,
   axe:(await axe.run(document.querySelector('[data-routines]'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(row=>({id:row.id,impact:row.impact,targets:row.nodes.map(node=>node.target)})),
   sessions:document.querySelectorAll('[data-routine-sessions] > section').length,exercises:document.querySelectorAll('[data-routine-sessions] details').length}));
  write(name+'.json',value);await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});report.captures.push({name,width,...value});
  assert.equal(value.overflow,false,name+' overflow');assert.deepEqual(value.axe,[],name+' scoped axe');assert.equal(value.sessions,3);assert.equal(value.exercises,13);
 }
 async function menu(page){
  await page.setViewportSize({width:390,height:900});const button=page.locator('#btn-hamburger');await button.focus();
  assert.equal(await button.getAttribute('aria-expanded'),'false');await page.keyboard.press('Enter');assert.equal(await button.getAttribute('aria-expanded'),'true');
  assert.equal(await page.evaluate(()=>!!document.activeElement.closest('#main-sidebar')),true);await page.keyboard.press('Escape');
  assert.equal(await button.getAttribute('aria-expanded'),'false');assert.equal(await page.evaluate(()=>document.activeElement.id),'btn-hamburger');
  // A collapsed off-canvas menu must not retain invisible keyboard stops.
  await page.evaluate(()=>document.activeElement.blur());
  for(let n=0;n<16;n++){
   await page.keyboard.press('Tab');const hiddenNavigation=await page.evaluate(()=>!!document.activeElement.closest('#main-sidebar')&&!document.getElementById('main-sidebar').classList.contains('open'));
   assert.equal(hiddenNavigation,false,'Collapsed navigation must not receive hidden focus');
  }
 }
 async function interactions(page){
  const inputs=page.locator('[data-routine-days] input');for(let i=0;i<7;i++)await inputs.nth(i).setChecked([0,2,6].includes(i));
  assert.equal(await page.locator('[data-routine-week-summary] li').count(),0);await page.locator('[data-routine-default]').click();assert.equal(await page.locator('[data-routine-week-summary] li').count(),3);
  const details=page.locator('[data-routine-sessions] details').first();await details.locator('summary').focus();await page.keyboard.press('Enter');assert.equal(await details.getAttribute('open'),'');
  await page.keyboard.press('Enter');assert.equal(await details.getAttribute('open'),null);
  const start=page.locator('[data-routine-timer-start]');await start.focus();await page.keyboard.press('Enter');await page.waitForTimeout(1200);await start.click();
  const paused=await page.locator('[data-routine-clock]').textContent();await page.waitForTimeout(1100);assert.equal(await page.locator('[data-routine-clock]').textContent(),paused);
  await page.locator('[data-routine-timer-reset]').click();assert.equal(await page.locator('[data-routine-clock]').textContent(),'01:30');
  assert.equal(await page.locator('[data-routine-clock]').getAttribute('role'),'timer');assert.equal(await page.locator('[data-routine-clock]').getAttribute('aria-live'),'off');
 }
 async function print(page,name){
  const states=await page.locator('[data-routine-sessions] details').evaluateAll(nodes=>nodes.map(node=>node.open));
  await page.evaluate(()=>window.addEventListener('beforeprint',()=>{window.__peerPrintSnapshot={allOpen:Array.from(document.querySelectorAll('[data-routine-sessions] details')).every(n=>n.open),sessions:document.querySelectorAll('[data-routine-sessions] > section').length,sources:document.querySelectorAll('[data-routine-sources] a').length};},{once:true}));
  await page.emulateMedia({media:'print'});await page.pdf({path:path.join(out,name+'.pdf'),format:'A4',printBackground:false});
  const result=await page.evaluate(()=>window.__peerPrintSnapshot);assert.deepEqual(result,{allOpen:true,sessions:3,sources:3});
  assert.equal(await page.locator('#main-sidebar').isVisible(),false);await page.emulateMedia({media:'screen'});
  assert.deepEqual(await page.locator('[data-routine-sessions] details').evaluateAll(nodes=>nodes.map(node=>node.open)),states);write(name+'.json',result);
 }
 try{
  lease();browser=await chromium.launch({headless:true,executablePath:chrome});
  const pages=new Map();
  for(const key of['owner','personal','viewer']){
   const ctx=await context(),page=await ctx.newPage();page.on('pageerror',error=>report.pageErrors.push(error.name));pages.set(key,{ctx,page});
   await step(key+' actual redesigned form Enter/password/MFA/browser login',()=>login(page,key));
  }
  for(const[key,scope,route]of scenarios){
   const {page}=pages.get(key);await step(key+' '+scope+' actual catalogue and cookie bootstrap',()=>catalogue(page,route,scope));
   for(const width of widths)await step(key+' '+scope+' scoped axe/overflow '+width,()=>capture(page,key+'-'+scope+'-'+width,width));
   await step(key+' '+scope+' menu keyboard/focus',()=>menu(page));
   await step(key+' '+scope+' week/details/timer',()=>interactions(page));
   if(key!=='viewer')await step(key+' all-three-session print PDF',()=>print(page,key+'-print'));
  }
  await step('Team viewer remains read-only while both catalogues are available',async()=>{
   const {page}=pages.get('viewer');const me=await page.evaluate(async()=>Api.auth.me());assert.equal(me.role,'viewer');assert.ok(me.team_gym_id);
   assert.equal(me.permissions.some(row=>row[1]==='cliente'&&row[0]!=='read'),false);
  });
  await step('Actual personal denial403 preserves current RAM actor',async()=>{
   const {page}=pages.get('personal');const value=await page.evaluate(async()=>{const before=Api.getToken();try{await RoutinePanel.readCatalog(Api,'gym');return{rejected:false};}catch(error){return{rejected:error.status===403,same:Api.getToken()===before};}});assert.deepEqual(value,{rejected:true,same:true});
  });
  await step('Explicit real accountB login invalidates old A without adoption',async()=>{
   const {ctx,page}=pages.get('personal'),other=await ctx.newPage();await login(other,'personal_b');
   await page.waitForFunction(()=>Api.getToken()==='');assert.equal(await page.evaluate(()=>document.querySelectorAll('[data-routine-sessions] details').length),0);
   assert.equal(await other.evaluate(async()=> (await Api.auth.me()).id),metadata.actors.personal_b.id);await other.close();
  });
  await step('Persisted real SV revocation401 retires current RAM before catalogue retry',async()=>{
   const {page}=pages.get('owner');lease();const python=process.env.ROUTINES37_PYTHON;assert.ok(path.isAbsolute(python));
   const changed=spawnSync(python,['-B','-X','utf8',path.join(__dirname,'security_routines37_server_peer.py'),'--source',metadata.source_commit,'--private',fixture,'--lease-ack',ackPath,'--retire','owner'],{encoding:'utf8',windowsHide:true});
   fs.writeFileSync(path.join(out,'retire.stdout.private.json'),changed.stdout||'');fs.writeFileSync(path.join(out,'retire.stderr.private.log'),changed.stderr||'');assert.equal(changed.status,0);
   const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/rutinas/catalogo');
   const transport=page.evaluate(async()=>{try{await RoutinePanel.readCatalog(Api,'gym');return'accepted';}catch(error){return error.code;}});
   const [reply,code]=await Promise.all([response,transport]);assert.equal(reply.status(),401);assert.equal(code,'session_changed');
   await page.waitForFunction(()=>Api.getToken()==='');assert.equal(await page.locator('[data-routine-sessions] details').count(),0);
  });
  assert.deepEqual(report.pageErrors,[]);report.complete=true;
 }catch(error){report.failure_class=error.name;report.failure_location=String(error.stack||'').split('\n').filter(line=>/^\s+at /.test(line)).slice(0,4);process.exitCode=1;}
 finally{
  auth.erase();for(const ctx of contexts)await ctx.close();await browser?.close();write('report.private.json',report);
  process.stdout.write(JSON.stringify({complete:report.complete,checks:report.checks.length,captures:report.captures.length,pageErrors:report.pageErrors.length,own_browser_closed:true})+'\n');
 }
}
