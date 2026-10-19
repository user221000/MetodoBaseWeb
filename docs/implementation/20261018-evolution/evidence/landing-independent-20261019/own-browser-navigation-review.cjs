/* Complete the remaining public-navigation criterion by testing the actual keyboard skip outcome. */
const {chromium}=require('playwright-core'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=process.env.METODOBASE_E2E_URL,out=process.env.METODOBASE_QA_OWN_OUTPUT;
assert.equal(new URL(base).hostname,'127.0.0.1');assert.ok(path.isAbsolute(out));fs.mkdirSync(out,{recursive:false});
const report={checks:[],screens:[],pageErrors:[],scope:'Remaining actual skip/public destination control. Native skip may set the sequential focus starting point without making the nonfocusable main active; next Tab must enter main, bypassing header.'};
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'}),context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce',serviceWorkers:'block'}),mutations=[];
 try{
  context.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))mutations.push(request.method());});
  await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.message));
  await page.goto(base+'/');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('href')),'#contenido');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('href')),'/');
  await page.goto(base+'/');await page.keyboard.press('Tab');await page.keyboard.press('Enter');await page.waitForURL(base+'/#contenido');
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  report.nativeActiveElementAfterSkip=await page.evaluate(()=>({id:document.activeElement.id,tag:document.activeElement.tagName}));
  await page.keyboard.press('Tab');
  const next=await page.evaluate(()=>({main:document.activeElement.closest('main')?.id,href:document.activeElement.getAttribute('href'),audience:document.activeElement.dataset.audience,outline:parseFloat(getComputedStyle(document.activeElement).outlineWidth)}));
  assert.equal(next.main,'contenido');assert.equal(next.href,'/registro?tipo=gym');assert.equal(next.audience,'gym');assert.ok(next.outline>=2);
  report.nextTabBypassesHeader=next;
  const links=await page.locator('a[href]').evaluateAll(elements=>[...new Set(elements.map(element=>element.getAttribute('href')))]);
  for(const href of links){if(href.startsWith('#'))assert.equal(await page.locator('[id="'+href.slice(1)+'"]').count(),1);else{const url=new URL(href,base);assert.equal(url.origin,base);assert.equal((await context.request.get(url.href,{maxRedirects:0})).status(),200);}}
  await page.locator('footer a[href="#datos-personales"]').focus();await page.keyboard.press('Enter');await page.waitForURL(base+'/#datos-personales');
  assert.equal(await page.locator('#datos-personales h2').count(),1);assert.equal((await context.request.get(base+'/landing.html',{maxRedirects:0})).status(),404);
  assert.deepEqual(mutations,[]);assert.deepEqual(report.pageErrors,[]);await page.screenshot({path:path.join(out,'privacy-keyboard-390.png'),fullPage:true});report.screens.push('privacy-keyboard-390');
  report.checks.push('Native skip bypasses header into the first main control; every public/fragment destination resolves and retired duplicate remains unavailable without writes');report.passed=true;
 }catch(error){report.passed=false;report.error=error.stack;console.error(error.stack);process.exitCode=1;}
 finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));await browser.close();}
})();
