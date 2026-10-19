/* Additional real keyboard, reduced-motion and public-destination checks; no form submission. */
const {chromium}=require('playwright-core'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=process.env.METODOBASE_E2E_URL;assert.equal(new URL(base).hostname,'127.0.0.1');
const out=process.env.METODOBASE_QA_OWN_OUTPUT;assert.ok(path.isAbsolute(out));fs.mkdirSync(out,{recursive:false});
const report={checks:[],screens:[],pageErrors:[],scope:'Actual unauthenticated public pages, keyboard focus and reduced-motion CSS. No registration, purchase or provider submission.'};
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'}),context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce',serviceWorkers:'block'});const mutations=[];
 try{
  context.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))mutations.push(request.method());});
  await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.message));
  for(const [audience,kind]of [['gym','gym'],['individual','usuario']]){
   await page.goto(base+'/');await page.keyboard.press('Tab');
   const link=page.locator('.hero [data-audience="'+audience+'"]');await link.focus();
   const focus=await link.evaluate(element=>{const style=getComputedStyle(element);return{active:document.activeElement===element,visible:element.matches(':focus-visible'),width:parseFloat(style.outlineWidth),style:style.outlineStyle};});
   assert.equal(focus.active,true);assert.equal(focus.visible,true);assert.ok(focus.width>=2);assert.notEqual(focus.style,'none');
   await page.keyboard.press('Enter');await page.waitForURL(base+'/registro?tipo='+kind);
   assert.equal(await page.locator('#campoTipo').inputValue(),kind);
   assert.equal(await page.locator('#linkLogin').getAttribute('href'),kind==='gym'?'/login-gym':'/login-usuario');
   const selected=page.locator(kind==='gym'?'#btnGym':'#btnUsuario');assert.equal(await selected.getAttribute('type'),'button');assert.ok((await selected.innerText()).trim());
   assert.ok((await selected.getAttribute('class')).includes(kind==='gym'?'active-gym':'active-usuario'));
  }
  report.checks.push('Both audience links expose a visible keyboard focus ring and Enter selects the matching real registration mode and login destination');
  await page.goto(base+'/');assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),true);
  await page.waitForFunction(()=>getComputedStyle(document.documentElement).scrollBehavior==='auto');
  await page.emulateMedia({reducedMotion:'no-preference'});await page.waitForFunction(()=>getComputedStyle(document.documentElement).scrollBehavior==='smooth');
  await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>getComputedStyle(document.documentElement).scrollBehavior==='auto');
  report.checks.push('Reduced-motion preference changes actual document scrolling from smooth to auto without replacing the landing content');
  await page.goto(base+'/');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('href')),'#contenido');
  await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'contenido');
  const links=await page.locator('a[href]').evaluateAll(elements=>[...new Set(elements.map(element=>element.getAttribute('href')))]);
  for(const href of links){if(href.startsWith('#'))assert.equal(await page.locator('[id="'+href.slice(1)+'"]').count(),1);else{const url=new URL(href,base);assert.equal(url.origin,base);const response=await context.request.get(url.href,{maxRedirects:0});assert.equal(response.status(),200);}}
  const privacy=page.locator('footer a[href="#datos-personales"]');await privacy.focus();await page.keyboard.press('Enter');assert.equal(new URL(page.url()).hash,'#datos-personales');assert.equal(await page.locator('#datos-personales h2').count(),1);
  assert.equal((await context.request.get(base+'/landing.html',{maxRedirects:0})).status(),404);
  assert.deepEqual(mutations,[]);assert.deepEqual(report.pageErrors,[]);
  await page.screenshot({path:path.join(out,'privacy-keyboard-390.png'),fullPage:true});report.screens.push('privacy-keyboard-390');
  report.checks.push('Skip link transfers keyboard focus, every public/fragment destination resolves, privacy navigation works and retired duplicate stays unavailable without writes');report.passed=true;
 }catch(error){report.passed=false;report.error=error.stack;console.error(error.stack);process.exitCode=1;}
 finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));await browser.close();}
})();
