/* Two additive R22 native groups. Actual app/cookie/MFA/PG; no generated plan or provider. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const session=require('./native37_session_qa.cjs'),{createJournal}=require('./native37_progress_qa.cjs');
const privateRoot=process.env.QA37_PRIVATE,dependencies=process.env.METODOBASE_E2E_DEPENDENCIES;
assert.ok(privateRoot&&path.isAbsolute(privateRoot));assert.ok(dependencies&&path.isAbsolute(dependencies));
const meta=JSON.parse(fs.readFileSync(path.join(privateRoot,'metadata.private.json'),'utf8')),base=meta.origin;
assert.equal(base,'http://127.0.0.1:8802');
const out=path.join(privateRoot,'native37-r22-output');fs.mkdirSync(out);
const progress=createJournal({file:path.join(privateRoot,'native37-r22-groups.private.ndjson'),groups:2,deadlineMs:60000});
const report={scope:'R22 additive two groups; actual current37 cookie/MFA/restricted PG. No saved plan, quota spend, delivery, adoption, human5+5, global WCAG, capacity or SLO claim.',producer_witness_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(privateRoot,'startup.json'))).digest('hex'),checks:[],screens:[],pageErrors:[],complete:false,external_blocked:0};
const contexts=[];let browser;
const observer=path.join(privateRoot,'r22-page-errors.private.ndjson');fs.writeFileSync(observer,'',{flag:'wx'});
function generalApiHeaders(response){
 const headers=response.headers();
 assert.ok((headers['cache-control']||'').split(',').some(part=>part.trim().toLowerCase()==='no-store'));
 assert.equal(headers['referrer-policy'],'strict-origin-when-cross-origin');
}
function assertionObservation(error,group){
 const classes=new Set(['Error','AssertionError','TypeError','ReferenceError','SyntaxError','RangeError','TimeoutError']);
 const allowed=new Set(['native37_onboarding_r22_qa_v5.cjs','native37_session_qa.cjs','browser_native_session31.cjs','mfa31_login.cjs','native37_progress_qa.cjs']);
 const directory=path.resolve(__dirname).replace(/\\/g,'/')+'/',frames=[];
 for(const line of String(error.stack||'').replace(/\\/g,'/').split('\n').slice(1,17)){
  const match=/((?:[A-Za-z]:\/|\/)[^()\n]+?\.cjs):(\d+):(\d+)/.exec(line);
  if(!match||!match[1].startsWith(directory))continue;
  const basename=path.basename(match[1]);if(!allowed.has(basename))continue;
  frames.push({source:'tests/e2e/'+basename,line:Number(match[2]),column:Number(match[3])});if(frames.length===6)break;
 }
 return{class:classes.has(error.name)?error.name:'OtherError',group:Number.isSafeInteger(group)&&group>=1&&group<=2?group:null,frames};
}
async function check(name,run){report.current_case=name;await progress.run(report.checks.length+1,run);report.checks.push({case:name,passed:true});delete report.current_case;}
const settle=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
async function pageFor(actor){
 const ctx=await session.createContext(browser,{viewport:{width:390,height:900},timezoneId:'America/Mexico_City',reducedMotion:'reduce'});contexts.push(ctx);
 await ctx.route('**/*',route=>{if(new URL(route.request().url()).origin===base)return route.continue();report.external_blocked++;return route.abort();});
 const page=await ctx.newPage();page.on('pageerror',error=>{
  const allowed=new Set(['Error','TypeError','ReferenceError','SyntaxError','RangeError']),frames=[];
  for(const line of String(error.stack||'').split('\n').slice(1,12)){
   const match=/(https?:\/\/[^\s)]+):(\d+):(\d+)/.exec(line);if(!match)continue;
   let url;try{url=new URL(match[1]);}catch{continue;}
   if(url.origin===base&&(url.pathname.startsWith('/static/js/')||['/dashboard','/mi-plan','/mi-perfil'].includes(url.pathname)))frames.push({pathname:url.pathname,line:Number(match[2]),column:Number(match[3])});
  }
  const row={class:allowed.has(error.name)?error.name:'OtherError',group:report.checks.length+1,frames:frames.slice(0,6)};
  report.pageErrors.push({class:row.class});fs.appendFileSync(observer,JSON.stringify(row)+'\n');
 });
 await session.login(page,base,actor);return{page,ctx};
}
async function screen(page,selector,name,width){
 await page.setViewportSize({width,height:900});await page.locator(selector).scrollIntoViewIfNeeded();await settle(page);
 await page.evaluate(fs.readFileSync(path.join(dependencies,'axe-core/axe.min.js'),'utf8'));
 const value=await page.evaluate(async selector=>({overflow:document.documentElement.scrollWidth>innerWidth,violations:(await axe.run(document.querySelector(selector),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(row=>({id:row.id,targets:row.nodes.map(node=>node.target)}))}),selector);
 assert.equal(value.overflow,false);assert.deepEqual(value.violations,[]);
 await page.screenshot({path:path.join(out,name+'.png'),fullPage:false,mask:[page.locator('input'),page.locator('#mfa-account-seed'),page.locator('#mfa-account-kit')]});
 report.screens.push({name,width,selector,...value});
}
(async()=>{try{
 const{chromium}=require(path.join(dependencies,'playwright-core'));browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
 await check('R22 OWNER preparation uses persisted facts and a working explicit client action',async()=>{
  const actor=meta.onboarding_actors.gym,{page,ctx}=await pageFor(actor);
  await page.locator('#onboarding-section[aria-busy="false"]').waitFor();
  const access=await page.evaluate(()=>Api.getToken()),response=await ctx.request.get(base+'/api/estadisticas',{headers:{Authorization:'Bearer '+access}});
  assert.equal(response.status(),200);generalApiHeaders(response);const stats=await response.json();
  assert.deepEqual(stats.onboarding,{client_registered:false,plan_saved:false});
  assert.equal(await page.locator('#onboarding-pct').textContent(),'0 de 2 pasos de preparación confirmados');
  assert.equal(await page.locator('#onboarding-steps > li').count(),2);assert.equal(await page.locator('#onboarding-steps .completed').count(),0);
  assert.match(await page.locator('#onboarding-section').textContent(),/Guardar un plan no confirma su descarga, envío ni recepción/);
  assert.equal(await page.locator('#ob-action-3').getAttribute('href'),'/planes');
  const writes=[];page.on('request',request=>{if(new URL(request.url()).origin===base&&request.method()!=='GET')writes.push(new URL(request.url()).pathname);});
  for(const width of[320,390,768,1440])await screen(page,'#onboarding-section','owner-preparation-'+width,width);
  await page.locator('#ob-action-1').click();await page.locator('#modal-cliente:not(.hidden)').waitFor();
  assert.equal(await page.locator('#form-cliente').isVisible(),true);await settle(page);assert.deepEqual(writes,[]);
  await page.locator('#modal-close').click();assert.equal(await page.locator('#modal-cliente').isVisible(),false);
  assert.equal(await page.evaluate(()=>localStorage.getItem('mb_onboarding_complete')),null);
 });
 await check('R22 incomplete personal profile has a real profile navigation without generation',async()=>{
  const actor=meta.onboarding_actors.usuario,{page,ctx}=await pageFor(actor);
  const access=await page.evaluate(()=>Api.getToken()),response=await ctx.request.get(base+'/api/usuario/perfil',{headers:{Authorization:'Bearer '+access}});
  assert.equal(response.status(),200);session.privateHeaders(response);const profile=await response.json();
  for(const field of['edad','peso_kg','estatura_cm','objetivo'])assert.equal(profile[field],null);
  await page.locator('#onboarding-card').waitFor({state:'visible'});const action=page.locator('#onboarding-card a');assert.equal(await action.getAttribute('href'),'/mi-perfil');
  assert.equal(await page.locator('#quick-actions').isVisible(),false);assert.equal((await page.locator('#onboarding-card').textContent()).includes('Solo necesitamos 3 datos'),false);
  const writes=[];page.on('request',request=>{if(new URL(request.url()).origin===base&&request.method()!=='GET')writes.push(new URL(request.url()).pathname);});
  for(const width of[320,390,768,1440])await screen(page,'#onboarding-card','personal-next-action-'+width,width);
  const navigation=page.waitForResponse(reply=>new URL(reply.url()).pathname==='/mi-perfil'&&reply.request().isNavigationRequest());
  await action.click();assert.equal((await navigation).status(),200);await page.waitForURL(base+'/mi-perfil');await session.ready(page);
  await page.locator('#form-perfil').waitFor({state:'visible'});await page.waitForFunction(email=>document.querySelector('#field-email').value===email,actor.email);assert.equal(await page.locator('#field-peso').inputValue(),'');
  assert.equal(await page.locator('#field-edad').inputValue(),'');await settle(page);assert.deepEqual(writes,['/api/auth/refresh']);
  report.profile_navigation_cookie_bootstrap={count:1,excluded_from_business_writes:true,actual_cookie_refresh:true};
  assert.equal(await page.evaluate(()=>['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].every(key=>localStorage.getItem(key)===null&&sessionStorage.getItem(key)===null)),true);
 });
 assert.equal(report.checks.length,2);assert.deepEqual(report.pageErrors,[]);report.complete=true;
}catch(error){
 report.failure_class=error.name;process.exitCode=1;
 const fd=fs.openSync(path.join(privateRoot,'r22-assertion-observer.private.json'),'wx',0o600);
 try{fs.writeSync(fd,JSON.stringify(assertionObservation(error,report.checks.length+1))+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
}
finally{report.progress=progress.close();for(const ctx of contexts)await ctx.close().catch(()=>{});session.erase();await browser?.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({complete:report.complete,groups:report.checks.length,expected:2,pageErrors:report.pageErrors.length,error_class:report.failure_class||null}));}})();
