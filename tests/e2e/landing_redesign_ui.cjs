/* Independent Chromium review of real rendered public HTML and CSP. No accounts or providers. */
'use strict';
const assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./node_modules/playwright-core');
const root=path.resolve(__dirname,'../..'),out=process.env.METODOBASE_LANDING_QA_OUTPUT,origin='http://127.0.0.1:8874';
assert.ok(out&&/^[EF]:[\\/]/i.test(out));assert.equal(fs.existsSync(path.join(out,'browser-report.json')),false);
const render=JSON.parse(fs.readFileSync(path.join(out,'render.json'),'utf8'));
const sources=Object.keys(render.sources),hashes=()=>Object.fromEntries(sources.map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')]));
const before=hashes();
assert.deepEqual(before,render.sources,'Rendered HTML and source snapshot must agree before browser starts');
const report={scope:'Real Web factory GET HTML/CSP, current local static assets and catalogue. Playwright routes intercept navigation and anonymous refresh only; no account creation, private API or payment provider.',cases:[],screens:[],pageErrors:[],cspViolations:[],externalRequests:[],unexpectedRequests:[],sourcesBefore:before};
let browser,context,page,stage='';
const storageKey='mb_landing_registration_dismissed_v1';
function headers(name){const value={...render.responses[name].headers};for(const name of['set-cookie','content-length','content-encoding'])delete value[name];return value;}
async function newPage(options={}){
 await context?.close();context=await browser.newContext({viewport:{width:options.width||390,height:options.height||1000},reducedMotion:'reduce',javaScriptEnabled:options.javaScript!==false});page=await context.newPage();
 page.on('pageerror',error=>report.pageErrors.push({stage,message:error.message}));
 await page.addInitScript(()=>{
  window.__landingCsp=[];
  document.addEventListener('securitypolicyviolation',event=>window.__landingCsp.push({directive:event.effectiveDirective,blocked:event.blockedURI}));
 });
 if(options.storageBlocked)await page.addInitScript(()=>{for(const name of['getItem','setItem','removeItem'])Storage.prototype[name]=function(){throw new DOMException('Synthetic storage denied','SecurityError');};});
 await context.route('**/*',request=>{
  const url=new URL(request.request().url()),method=request.request().method();
  if(url.origin!==origin){report.externalRequests.push(url.origin+url.pathname);return request.abort();}
  if(url.pathname==='/api/auth/refresh'&&method==='POST')return request.fulfill({status:401,contentType:'application/json',body:JSON.stringify({detail:{code:'browser_session_unavailable',message:'No active synthetic browser session'}})});
  if(method!=='GET'){report.unexpectedRequests.push({method,path:url.pathname});return request.abort();}
  if(url.pathname==='/')return request.fulfill({status:200,headers:headers('landing.html'),body:fs.readFileSync(path.join(out,'landing.html'))});
  if(url.pathname==='/registro')return request.fulfill({status:200,headers:headers('registro.html'),body:fs.readFileSync(path.join(out,'registro.html'))});
  if(url.pathname.startsWith('/static/')){
   const file=path.resolve(root,'web','.'+url.pathname);
   if(!file.startsWith(path.join(root,'web','static')+path.sep)||!fs.existsSync(file))return request.abort();
   return request.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.css')?'text/css':file.endsWith('.js')?'application/javascript':file.endsWith('.png')?'image/png':file.endsWith('.svg')?'image/svg+xml':'application/octet-stream'});
  }
  report.unexpectedRequests.push({method,path:url.pathname});return request.abort();
 });
 return page;
}
async function open(options={}){
 await newPage(options);await page.goto(origin+'/',{waitUntil:'networkidle'});
 if(options.javaScript!==false)await page.waitForFunction(()=>!document.querySelector('#demo-tabs [role=tab]').disabled);
}
async function run(name,action){stage=name;try{await action();report.cases.push({name,passed:true});}catch(error){report.cases.push({name,passed:false,error:error.message});throw error;}}
async function isPanelOpen(){return page.locator('#registration-invite-panel').isVisible();}
async function dismiss(){if(await isPanelOpen())await page.locator('#registration-invite-close').click();}
async function scan(name,width){
 await page.setViewportSize({width,height:1000});
 const nonce=render.responses['landing.html'].headers['content-security-policy'].match(/'nonce-([^']+)'/)[1];
 if(!await page.evaluate(()=>typeof axe!=='undefined')){
  await page.evaluate(({source,nonce})=>{const tag=document.createElement('script');tag.nonce=nonce;tag.textContent=source;document.head.append(tag);},{source:fs.readFileSync(path.join(__dirname,'node_modules/axe-core/axe.min.js'),'utf8'),nonce});
 }
 const data=await page.evaluate(async()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,violations:(await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(item=>({id:item.id,impact:item.impact,nodes:item.nodes.map(node=>node.target)})),csp:window.__landingCsp}));
 await page.screenshot({path:path.join(out,name+'-'+width+'.png'),fullPage:true});
 report.screens.push({name,width,fullPage:true,...data});
 assert.equal(data.overflow,false,name+' horizontal overflow');assert.deepEqual(data.violations,[],name+' whole-document axe A/AA');assert.deepEqual(data.csp,[],name+' CSP');
}
async function selected(name){
 const tab=page.locator('[data-demo-tab="'+name+'"]');
 assert.equal(await tab.getAttribute('aria-selected'),'true');
 assert.equal(await tab.getAttribute('tabindex'),'0');
 assert.equal(await page.locator('#demo-panel-'+name).isVisible(),true);
 assert.equal(await page.locator('[role=tabpanel]:visible').count(),1);
 for(const other of['clientes','plan','historial','rutinas'])if(other!==name)assert.equal(await page.locator('[data-demo-tab="'+other+'"]').getAttribute('aria-selected'),'false');
}
(async()=>{try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 await run('Invitation opens automatically without moving keyboard focus or modalizing the page',async()=>{
  await open({width:1440});const focus=await page.evaluate(()=>document.activeElement.tagName);
  await page.waitForFunction(()=>!document.getElementById('registration-invite-panel').hidden);
  assert.equal(await page.evaluate(()=>document.activeElement.tagName),focus);
  assert.equal(await page.locator('#registration-invite-toggle').getAttribute('aria-expanded'),'true');
  assert.equal(await page.locator('body').evaluate(node=>node.inert),false);
  assert.equal(await page.locator('#registration-invite-panel').getAttribute('aria-modal'),null);
 });
 await run('Closing collapses to a named pill and persists only the dismissal for this tab',async()=>{
  await page.locator('#registration-invite-close').click();assert.equal(await isPanelOpen(),false);
  assert.equal(await page.locator('#registration-invite-toggle').isVisible(),true);
  assert.equal(await page.locator('#registration-invite-toggle').getAttribute('aria-expanded'),'false');
  assert.equal(await page.evaluate(key=>sessionStorage.getItem(key),storageKey),'1');
  await page.reload({waitUntil:'networkidle'});await page.waitForTimeout(1500);
  assert.equal(await isPanelOpen(),false);await page.locator('#registration-invite-toggle').click();assert.equal(await isPanelOpen(),true);
 });
 await run('Early keyboard focus on the invitation toggle survives the automatic-open timer',async()=>{
  await open();await page.locator('#registration-invite-toggle').focus();await page.waitForTimeout(1500);
  assert.equal(await page.locator('#registration-invite-toggle').isVisible(),true);
  assert.equal(await page.locator('#registration-invite-toggle').evaluate(node=>node===document.activeElement),true);
 });
 await run('Escape respects focus scope and returns focus from the invitation to its toggle',async()=>{
  await open();await page.locator('#registration-invite-toggle').click();
  await page.locator('[href="#contenido"]').focus();await page.keyboard.press('Escape');assert.equal(await isPanelOpen(),true);
  await page.locator('#registration-invite-close').focus();await page.keyboard.press('Escape');
  assert.equal(await isPanelOpen(),false);assert.equal(await page.locator('#registration-invite-toggle').evaluate(node=>node===document.activeElement),true);
 });
 await run('Both invitation audience choices reach the real matching registration form without submission',async()=>{
  for(const tipo of['gym','usuario']){
   await open();await page.locator('#registration-invite-toggle').click();
   await page.locator('input[name="invite-audience"][value="'+tipo+'"]').check();
   assert.equal(await page.locator('#registration-invite-register').getAttribute('href'),'/registro?tipo='+tipo);
   await page.locator('#registration-invite-register').click();await page.waitForURL('**/registro?tipo='+tipo);
   assert.equal(await page.locator('#campoTipo').inputValue(),tipo);
   assert.equal(await page.locator('#linkLogin').getAttribute('href'),tipo==='gym'?'/login-gym':'/login-usuario');
  }
 });
 await run('Public CTA retains each selected subscription through the current registration/login links',async()=>{
  for(const [selector,tipo,key]of[['[data-plan="standard"]','gym','standard'],['[data-plan="gym_comercial"]','gym','gym_comercial'],['[data-plan="clinica"]','gym','clinica'],['[data-personal-plan="pro"]','usuario','pro']]){
   await open();await dismiss();await page.locator(selector+' a').click();await page.waitForURL('**/registro?tipo='+tipo+'&subscription_plan='+key);
   assert.equal(await page.locator('#campoTipo').inputValue(),tipo);
   assert.equal(await page.locator('#linkLogin').getAttribute('href'),(tipo==='gym'?'/login-gym':'/login-usuario')+'?subscription_plan='+key);
  }
 });
 await run('Four demo tabs expose only their named panel and use roving keyboard focus',async()=>{
  await open({width:1440});await dismiss();await selected('clientes');
  for(const name of['plan','historial','rutinas','clientes']){await page.locator('[data-demo-tab="'+name+'"]').click();await selected(name);}
  await page.locator('[data-demo-tab="clientes"]').focus();await page.keyboard.press('ArrowRight');await selected('plan');
  assert.equal(await page.locator('[data-demo-tab="plan"]').evaluate(node=>node===document.activeElement),true);
  await page.keyboard.press('End');await selected('rutinas');await page.keyboard.press('Home');await selected('clientes');
  await page.keyboard.press('ArrowLeft');await selected('rutinas');
 });
 await run('Explicit tour actions advance the demonstration without fetching private resources',async()=>{
  await page.locator('[data-demo-tab="clientes"]').click();
  const action=page.locator('#demo-panel-clientes [data-demo-target]').first();
  assert.equal(await action.count(),1);const target=await action.getAttribute('data-demo-target');await action.click();await selected(target);
  assert.match(await page.locator('#demo-data-label').textContent(),/datos de ejemplo/);
 });
 await run('Canonical prices and quotas remain separate for business and personal audiences',async()=>{
  await open();await dismiss();
  for(const [kind,catalog,attr]of[['business',render.catalogue.business,'data-plan'],['personal',render.catalogue.personal,'data-personal-plan']]){
   for(const [key,plan]of Object.entries(catalog)){
    const card=page.locator('['+attr+'="'+key+'"]');assert.equal(await card.count(),1);
    const price=card.locator('[data-price-centavos]');assert.equal(await price.getAttribute('data-price-centavos'),String(plan.precio_centavos));
    assert.equal(await price.getAttribute('data-currency'),plan.moneda);assert.equal(await price.getAttribute('data-period'),plan.periodo);
    for(const field of kind==='business'?['max_clientes','max_registros_diarios','max_planes_por_cliente_dia','max_planes_diarios','max_planes_mes']:['max_planes_mes'])assert.equal(await card.locator('[data-limit-field="'+field+'"]').getAttribute('data-value'),String(plan[field]));
   }
  }
 });
 await run('Skip link and native FAQ remain usable from the keyboard',async()=>{
  await open();await dismiss();await page.locator('[href="#contenido"]').focus();await page.keyboard.press('Enter');
  assert.equal(new URL(page.url()).hash,'#contenido');await page.locator('summary').first().focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('details').first().getAttribute('open'),'');await page.keyboard.press('Enter');
  assert.equal(await page.locator('details').first().getAttribute('open'),null);
 });
 await run('Existing business and personal access stay visible and reachable in the mobile header',async()=>{
  await open({width:320});
  for(const tipo of['gym','usuario']){
   const link=page.locator('header a[href="/login-'+(tipo==='gym'?'gym':'usuario')+'"]');assert.equal(await link.isVisible(),true);
   const box=await link.boundingBox();assert.ok(box.x>=0&&box.x+box.width<=320&&box.y>=0&&box.y+box.height<1000);
  }
 });
 await run('First-visit invitation and entire landing fit 320, 390, 768 and 1440 with axe A/AA and real CSP',async()=>{
  for(const width of[320,390,768,1440]){
   await open({width});await page.waitForFunction(()=>!document.getElementById('registration-invite-panel').hidden);
   const box=await page.locator('#registration-invite-panel').boundingBox();assert.ok(box.width<=width);assert.ok(box.height<750);
   await page.screenshot({path:path.join(out,'first-visit-'+width+'.png'),fullPage:false});
   report.screens.push({name:'first-visit',width,height:1000,fullPage:false});
   await dismiss();await scan('landing-full',width);
  }
 });
 await run('Low-height landscape viewports keep the compact invitation and its close button reachable',async()=>{
  for(const[width,height]of[[320,240],[390,300]]){
   await open({width,height});await page.waitForFunction(()=>!document.getElementById('registration-invite-panel').hidden);
   const panel=await page.locator('#registration-invite-panel').boundingBox(),close=await page.locator('#registration-invite-close').boundingBox();
   assert.ok(panel.y>=0&&panel.y+panel.height<=height);assert.ok(close.y>=0&&close.y+close.height<=height);
   await page.screenshot({path:path.join(out,'landscape-'+width+'x'+height+'.png'),fullPage:false});
   report.screens.push({name:'landscape',width,height,fullPage:false,panel,close});
   await page.locator('#registration-invite-close').click();assert.equal(await isPanelOpen(),false);
  }
 });
 await run('Plan and routine demonstrations stay readable on mobile and desktop without clinical promises',async()=>{
  for(const [name,width]of[['plan',390],['rutinas',1440]]){
   await page.setViewportSize({width,height:1000});await page.locator('[data-demo-tab="'+name+'"]').click();await selected(name);await scan('demo-'+name,width);
  }
  const body=(await page.locator('body').innerText()).toLowerCase();
  for(const unsupported of['100% personalizado','ilimitados en segundos','escritorio sigue soportada'])assert.equal(body.includes(unsupported),false);
 });
 await run('Storage-denied browsers retain demonstration and explicit registration controls',async()=>{
  await open({storageBlocked:true});await page.waitForFunction(()=>!document.getElementById('registration-invite-panel').hidden);
  await page.locator('#registration-invite-close').click();assert.equal(await isPanelOpen(),false);
  await page.locator('#registration-invite-toggle').click();assert.equal(await isPanelOpen(),true);
  await page.locator('[data-demo-tab="plan"]').click();await selected('plan');
 });
 await run('A fresh visit with keyboard activity does not interrupt the focused link',async()=>{
  await open();await page.locator('[href="#contenido"]').focus();await page.keyboard.press('Tab');
  const focused=await page.evaluate(()=>document.activeElement.outerHTML);await page.waitForTimeout(1500);
  assert.equal(await page.evaluate(()=>document.activeElement.outerHTML),focused);
 });
 await run('No-JavaScript visitors can read the preview, prices, FAQ and open registration',async()=>{
  await open({javaScript:false});assert.equal(await page.locator('#demo-panel-clientes').isVisible(),true);
  assert.equal(await page.locator('#registration-invite').isVisible(),false);
  assert.equal(await page.locator('[data-plan="free"]').isVisible(),true);
  await page.locator('summary').first().click();assert.equal(await page.locator('details').first().getAttribute('open'),'');
  const href=await page.locator('[data-plan="standard"] a').getAttribute('href');assert.equal(href,'/registro?tipo=gym&subscription_plan=standard');
  await page.locator('[data-plan="standard"] a').click();await page.waitForURL('**/registro?tipo=gym&subscription_plan=standard');
 });
 assert.deepEqual(report.pageErrors,[]);assert.deepEqual(report.externalRequests,[]);assert.deepEqual(report.unexpectedRequests,[]);
 report.sourcesAfter=hashes();assert.deepEqual(report.sourcesAfter,before);report.sourceStable=true;report.passed=true;
}catch(error){report.passed=false;report.failure={name:error.name,message:error.message,stack:error.stack};process.exitCode=1;}finally{
 await context?.close();await browser?.close();report.closed=true;
 fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({passed:report.passed,cases:report.cases.length,screens:report.screens.length,pageErrors:report.pageErrors.length,out,failure:report.failure||null}));
}})();

