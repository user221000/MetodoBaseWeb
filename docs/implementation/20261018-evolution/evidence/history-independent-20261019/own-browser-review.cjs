/* Real loopback UI controls plus named duplicate/repeating-position delivery probes. */
const {chromium}=require('playwright-core'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const base=process.env.METODOBASE_E2E_URL,origin=new URL(base).origin;
assert.equal(base,origin);assert.equal(new URL(base).hostname,'127.0.0.1');
const out=process.env.METODOBASE_QA_OWN_OUTPUT;assert.ok(path.isAbsolute(out));fs.mkdirSync(out,{recursive:false});
const report={checks:[],pageErrors:[],scope:'Actual authenticated history UI; only next-page delivery duplication/nonadvancing position and response hold are doubles. No provider/PG/load claim.'};
const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};};
const check=name=>report.checks.push(name);
const exact=url=>assert.equal(new URL(url).origin,origin,'Closed loopback origin');
const digest=value=>crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});let api;
 try{
  const apiContext=await browser.newContext({serviceWorkers:'block'});api=apiContext.request;
  const login=await api.post(base+'/api/auth/login',{maxRedirects:0,data:{email:'diary-history@example.invalid',password:'Synthetic-Diary-Password-2026!'}});assert.equal(login.status(),200);const pair=await login.json();
  async function open(){const context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block'});await context.route('**/*',route=>{if(new URL(route.request().url()).origin!==origin)return route.abort();return route.continue();});const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.message));await page.goto(base+'/login-usuario');await page.evaluate(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('mb_tipo','usuario');},pair);await page.goto(base+'/mi-historial');await page.waitForFunction(()=>document.querySelectorAll('#tbody-planes tr').length===50);return{context,page};}
  async function storage(page){return digest(await page.evaluate(()=>[Object.entries(localStorage).sort(),Object.entries(sessionStorage).sort()]));}
  let view=await open(),page=view.page,started=deferred(),release=deferred(),requests=0;
  const storageBefore=await storage(page);
  page.on('request',request=>{const url=new URL(request.url());if(url.pathname==='/api/usuario/historial'&&url.search)requests++;});
  await page.route('**/api/usuario/historial?*',async route=>{exact(route.request().url());const response=await route.fetch({maxRedirects:0});assert.equal(response.status(),200);started.resolve();await release.promise;await route.fulfill({response});},{times:1});
  await page.locator('#history-more').click();await started.promise;
  assert.equal(await page.locator('#history-more').isDisabled(),true);assert.equal(await page.locator('#history-refresh').isDisabled(),true);
  await page.evaluate(()=>{for(const id of ['history-more','history-refresh','history-retry'])document.getElementById(id).dispatchEvent(new MouseEvent('click',{bubbles:true}));});
  assert.equal(requests,1);assert.equal(await page.locator('#tbody-planes tr').count(),50);
  release.resolve();await page.waitForFunction(()=>document.querySelectorAll('#tbody-planes tr').length===100);assert.equal(requests,1);assert.equal(await storage(page),storageBefore);await view.context.close();
  check('Pending real page disables all controls and synthetic repeated control events dispatch only one request, preserving visible rows and storage');

  view=await open();page=view.page;let failedPosition;
  await page.route('**/api/usuario/historial?*',async route=>{exact(route.request().url());failedPosition=route.request().url();const response=await route.fetch({maxRedirects:0});assert.equal(response.status(),200);const body=await response.json();body.next_cursor=new URL(failedPosition).searchParams.get('cursor');await route.fulfill({response,json:body});},{times:1});
  await page.locator('#history-more').click();await page.locator('#history-error').waitFor({state:'visible'});assert.equal(await page.locator('#tbody-planes tr').count(),50);assert.equal(await page.locator('#history-retry').isVisible(),true);
  let retryPosition;page.on('request',request=>{if(request.url().includes('/api/usuario/historial?'))retryPosition=request.url();});
  await page.locator('#history-retry').click();await page.waitForFunction(()=>document.querySelectorAll('#tbody-planes tr').length===100);assert.equal(retryPosition,failedPosition);await view.context.close();
  check('Nonadvancing position delivery cannot publish a partial page; actual retry retains50 rows and uses the exact prior position');

  view=await open();page=view.page;const beforeDedupe=await storage(page);
  await page.route('**/api/usuario/historial?*',async route=>{exact(route.request().url());const response=await route.fetch({maxRedirects:0});assert.equal(response.status(),200);const body=await response.json();assert.equal(body.planes.length,50);body.planes[1]={...body.planes[0]};await route.fulfill({response,json:body});},{times:1});
  await page.locator('#history-more').click();await page.waitForFunction(()=>document.querySelectorAll('#tbody-planes tr').length===99);assert.match(await page.locator('#history-status').textContent(),/99 planes consultados/);
  await page.locator('#history-more').click();await page.waitForFunction(()=>document.querySelectorAll('#tbody-planes tr').length===106);assert.equal(await page.locator('#history-more').isVisible(),false);assert.equal(await storage(page),beforeDedupe);await page.screenshot({path:path.join(out,'dedupe-390.png'),fullPage:true});await view.context.close();
  check('Duplicate-ID delivery appends49 unique rows and exhausts once at106 while all browser storage remains byte-equivalent');
  assert.deepEqual(report.pageErrors,[]);report.passed=true;
 }catch(error){report.passed=false;report.error=error.stack;process.exitCode=1;console.error(error.stack);}
 finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));await browser.close();}
})();
