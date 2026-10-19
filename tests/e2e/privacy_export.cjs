/* Real synthetic auth/scope/pages. Only negative export responses use transport doubles. */
const {chromium}=require('playwright-core');
const {AxeBuilder}=require('@axe-core/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8768';
if(!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base))throw Error('Only a local synthetic server is allowed');
const batch=process.env.METODOBASE_EVIDENCE_BATCH;
const out=path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux',batch?'privacy-export-'+batch:'');
fs.mkdirSync(out,{recursive:true});
const report={scope:'Real synthetic app, own SQLite and real auth/scope/export API; only explicitly named error responses are intercepted; all external connections blocked',checks:[],screens:[],pageErrors:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
  await context.route('**/*',route=>route.request().url().startsWith(base) ? route.continue() : route.abort());
  await context.addInitScript(()=>{
   window.__privacyUrls={created:[],revoked:[]};
   const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);
   URL.createObjectURL=function(blob){const url=create(blob);window.__privacyUrls.created.push(url);return url;};
   URL.revokeObjectURL=function(url){window.__privacyUrls.revoked.push(url);return revoke(url);};
  });
  const page=await context.newPage(),downloads=[],requests=[];page.on('download',value=>downloads.push(value));page.on('pageerror',error=>report.pageErrors.push(error.message));
  const password='Synthetic-Export-Password-2026!';
  async function login(email){const response=await context.request.post(base+'/api/auth/login',{data:{email,password}});assert.ok(response.ok(),'Synthetic real login failed');const result=await response.json();assert.equal(typeof result.token,'string');return result;}
  const personal=await login('export-personal@example.invalid');
  assert.equal((await context.request.get(base+'/api/usuario/privacidad/exportar')).status(),401);
  await page.goto(base+'/login-usuario');await page.evaluate(token=>localStorage.setItem('mb_token',token),personal.token);
  let mode='real',releaseHeld,heldStarted;
  await page.route('**/api/usuario/privacidad/exportar**',async route=>{
   const request=route.request();requests.push({query:Object.fromEntries(new URL(request.url()).searchParams),authenticated:request.headers().authorization==='Bearer '+personal.token});
   if(mode==='real')return route.continue();
   if(mode==='html')return route.fulfill({contentType:'text/html',body:'<html>Synthetic unexpected page</html>'});
   if(mode==='malformed')return route.fulfill({json:{}});
   if(mode==='failure')return route.fulfill({status:503,json:{detail:{message:'No se pudo preparar esta parte. Intenta de nuevo.'}}});
   const response=await route.fetch(),data=await response.json();
   if(mode==='hold'){heldStarted();await new Promise(resolve=>{releaseHeld=resolve;});}
   if(mode==='cycle')data.plans.next_after=Number(new URL(request.url()).searchParams.get('after_plan'));
   if(mode==='scope')data.account.id='synthetic-export-other';
   return route.fulfill({response,json:data});
  });
  async function ready(){await page.waitForFunction(()=>!document.getElementById('privacy-start').disabled && document.getElementById('privacy-status').textContent.includes('Descarga tus datos'));}
  async function download(button,keyboard=false){const awaited=page.waitForEvent('download');if(keyboard){await button.focus();await page.keyboard.press('Enter');}else await button.click();const value=await awaited;assert.match(value.suggestedFilename(),/^metodobase-datos-personales-.*-parte-\d{3}\.json$/);return JSON.parse(fs.readFileSync(await value.path(),'utf8'));}
  async function errorAfter(button){const count=downloads.length;await button.click();await page.locator('#privacy-error').waitFor({state:'visible'});assert.equal(downloads.length,count);assert.ok(!(await page.locator('#privacy-status').textContent()).includes('todas las partes'));}
  async function scan(label){await page.locator('#personal-data-section').scrollIntoViewIfNeeded();const result=await new AxeBuilder({page}).include('#personal-data-section').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();const dimensions=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));report.screens.push({label,dimensions,violations:result.violations.map(value=>({id:value.id,nodes:value.nodes.map(node=>({target:node.target,summary:node.failureSummary}))}))});await page.locator('#personal-data-section').screenshot({path:path.join(out,label+'.png')});}
  await page.goto(base+'/mi-perfil');await ready();
  const first=await download(page.locator('#privacy-start'),true);
  assert.equal(first.manifest.part,1);assert.equal(first.manifest.all_available_pages_prepared,false);assert.equal(first.account.id,'synthetic-export-personal');
  assert.equal(first.collections.profiles.records.length,1);assert.equal(first.collections.plans.records.length,100);assert.equal(first.collections.measurements.records.length,2);
  assert.match(await page.locator('#privacy-status').textContent(),/Quedan registros/);assert.equal(await page.locator('#privacy-next').isVisible(),true);
  const second=await download(page.locator('#privacy-next'));
  assert.equal(second.account,null);assert.equal(second.manifest.part,2);assert.equal(second.manifest.all_available_pages_prepared,false);
  assert.equal(Object.hasOwn(second.collections,'profiles'),false);assert.equal(Object.hasOwn(second.collections,'measurements'),false);
  assert.equal(second.manifest.collections.profiles.status,'included_in_previous_parts');
  assert.equal(second.collections.purchases.records.length,2);assert.equal(second.collections.generation_requests.records.length,1);
  assert.equal(requests[1].query.after_purchase,'00000063-ABCD-4000-8000-000000000063');assert.equal(requests[1].query.after_generation,'00000063-BCDE-4000-8000-000000000063');
  assert.ok(!Object.hasOwn(requests[1].query,'after_profile'));assert.ok(!Object.hasOwn(requests[1].query,'after_measurement'));
  const third=await download(page.locator('#privacy-next'));
  assert.equal(third.manifest.part,3);assert.equal(third.manifest.all_available_pages_prepared,true);assert.equal(third.manifest.parts_total,3);
  assert.deepEqual(Object.keys(third.collections),['plans']);assert.equal(third.collections.plans.records.length,5);
  assert.deepEqual(Object.keys(requests[2].query).sort(),['after_plan','limit']);
  const parts=[first,second,third],counts={profiles:1,plans:205,measurements:2,purchases:102,generation_requests:101};
  for(const [name,total] of Object.entries(counts)){const records=parts.flatMap(part=>part.collections[name]?.records || []);assert.equal(records.length,total);assert.equal(new Set(records.map(record=>record.id)).size,total);assert.equal(third.manifest.collections[name].records_prepared,total);}
  assert.equal(third.manifest.plans_requiring_content_review,1);assert.equal(await page.locator('#privacy-content-warning').isVisible(),true);
  assert.equal(third.manifest.consistency,'live_keyset_pages');assert.equal(third.scope.coverage,'account_and_persisted_personal_space');assert.ok(third.scope.excluded_categories.includes('professional_portfolio'));
  assert.ok(parts.every(part=>!JSON.stringify(part).includes('PROFESSIONAL PORTFOLIO PRIVATE') && !JSON.stringify(part).includes('OTHER ACCOUNT PRIVATE')));
  assert.ok(requests.every(request=>request.authenticated));assert.ok(!/after_|ABCD|BCDE/.test(await page.locator('#personal-data-section').innerText()));
  report.checks.push('Historical professional exports only their real personal scope in three explicitly numbered parts; completed collections and first-part account/subscription metadata are not repeated');
  report.checks.push('Uppercase UUID continuation values survive exactly; final manifest counts 1 profile, 205 unique plans, 2 measurements, 102 purchases and 101 generation requests');
  await page.waitForFunction(()=>window.__privacyUrls.created.every(url=>window.__privacyUrls.revoked.includes(url)));
  const repeated=await download(page.locator('#privacy-again'));assert.deepEqual(repeated,third);assert.equal(await page.locator('[data-export-count="plans"]').textContent(),'205');
  assert.ok(await page.evaluate(()=>Object.keys(localStorage).every(key=>['mb_token','mb_refresh_token','mb_tipo','mb_nombre','mb_email'].includes(key))));
  report.checks.push('Blob downloads are initiated before status advances; URLs are revoked after a margin, re-download keeps counts stable, and export payload/cursors never enter localStorage');
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});await scan('privacy-export-complete-'+width);}
  report.checks.push('Native Enter starts export; status/errors are announced and new export controls pass scoped axe AA and responsive checks');
  mode='malformed';await errorAfter(page.locator('#privacy-start'));await page.setViewportSize({width:390,height:844});await scan('privacy-export-error-390');
  mode='html';await errorAfter(page.locator('#privacy-start'));mode='failure';await errorAfter(page.locator('#privacy-start'));
  mode='real';await download(page.locator('#privacy-start'));mode='cycle';await errorAfter(page.locator('#privacy-next'));
  assert.match(await page.locator('#privacy-status').textContent(),/Se mantiene la parte preparada/);assert.equal(await page.locator('[data-export-count="plans"]').textContent(),'100');
  mode='real';const retried=await download(page.locator('#privacy-next'));assert.equal(retried.manifest.part,2);
  report.checks.push('HTTP 503, HTTP 200 HTML, incomplete payload and a non-progressing page never generate a file or claim completion; retry resumes the same part');
  mode='scope';await errorAfter(page.locator('#privacy-next'));assert.equal(await page.locator('#privacy-counts').isHidden(),true);
  mode='real';await download(page.locator('#privacy-start'));
  const other=await login('export-other@example.invalid');await page.evaluate(token=>localStorage.setItem('mb_token',token),other.token);
  const callsBefore=requests.length;await errorAfter(page.locator('#privacy-next'));assert.equal(requests.length,callsBefore);assert.match(await page.locator('#privacy-error').textContent(),/cuenta cambió/);
  assert.equal(await page.locator('#privacy-counts').isHidden(),true);
  report.checks.push('A mismatched export identity or a real account switch discards the in-memory continuation/file; no next export request is made for the old account');
  const personalAgain=await login('export-personal@example.invalid');await page.evaluate(token=>localStorage.setItem('mb_token',token),personalAgain.token);
  const started=new Promise(resolve=>{heldStarted=resolve;});mode='hold';const heldCount=downloads.length;
  await page.locator('#privacy-start').click();await started;
  await page.evaluate(token=>{localStorage.setItem('mb_token',token);dispatchEvent(new StorageEvent('storage',{key:'mb_token'}));},other.token);releaseHeld();
  await page.locator('#privacy-error').waitFor({state:'visible'});assert.equal(downloads.length,heldCount);assert.equal(await page.locator('#privacy-counts').isHidden(),true);mode='real';
  report.checks.push('An already authenticated export response arriving after a cross-tab session change is discarded without creating a Blob download');
  const owner=await login('export-owner@example.invalid');const ownerResponse=await context.request.get(base+'/api/usuario/privacidad/exportar',{headers:{Authorization:'Bearer '+owner.token}});assert.equal(ownerResponse.status(),200);const ownerData=await ownerResponse.json();assert.equal(ownerData.scope.personal_space,false);assert.equal(ownerData.profiles.records.length,0);assert.equal(ownerData.plans.records.length,0);
  const logout=await context.request.post(base+'/api/auth/logout',{headers:{Authorization:'Bearer '+other.token}});assert.equal(logout.status(),200);
  const countBefore=downloads.length;await page.locator('#privacy-start').click();await page.waitForURL(/\/login-(usuario|gym)$/);assert.equal(downloads.length,countBefore);
  report.checks.push('Real unauthenticated export is 401; a gym owner receives account-only data; a revoked real session redirects to login without a download');
  assert.deepEqual(report.pageErrors,[]);assert.ok(report.screens.every(value=>!value.violations.length),'New export section has axe violations');assert.ok(report.screens.every(value=>value.dimensions.width>=value.dimensions.scrollWidth),'Page has horizontal overflow');
  report.downloadsPrepared=downloads.length;report.scopeOfAxe='#personal-data-section only; unrelated legacy profile UI is outside this new control gate';
  fs.writeFileSync(path.join(out,'privacy-export-browser.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
