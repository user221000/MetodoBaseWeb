/* Real synthetic auth, quota, generation and exact PDF. Named error cases use transport doubles. */
const {chromium}=require('playwright-core');
const {AxeBuilder}=require('@axe-core/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8769';
if(!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base))throw Error('Only an isolated loopback fixture is allowed');
const batch=process.env.METODOBASE_EVIDENCE_BATCH || new Date().toISOString().replace(/[^0-9]/g,'');
const out=path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux/b2b-generation-'+batch);
fs.mkdirSync(out,{recursive:true});
const report={scope:'Real isolated auth, SQLite, quota, worker and exact PDF; explicitly named failures use browser transport doubles; all external requests blocked',checks:[],screens:[],pageErrors:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
  await context.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());
  await context.addInitScript(()=>{window.__blobState={created:0,revoked:0};const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);URL.createObjectURL=blob=>{window.__blobState.created++;return create(blob);};URL.revokeObjectURL=url=>{window.__blobState.revoked++;return revoke(url);};});
  const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.message));
  const password='Synthetic-Generation-Password-2026!';
  async function login(suffix){const response=await context.request.post(base+'/api/auth/login',{data:{email:'generation-'+suffix+'@example.invalid',password}});assert.equal(response.status(),200);return response.json();}
  const owner=await login('owner'),other=await login('other');
  const auth={Authorization:'Bearer '+owner.token};
  await page.goto(base+'/login-gym');await page.evaluate(token=>localStorage.setItem('mb_token',token),owner.token);
  let mode='lost',postRequests=[],updates=0,realResult,heldStarted,releaseHeld;
  await page.route('**/api/clientes/synthetic-generation-client-*',async route=>{
   if(route.request().method()!=='PUT')return route.continue();
   updates++;
   if(mode==='update-error')return route.fulfill({status:422,json:{detail:'Synthetic profile update rejected'}});
   return route.continue();
  });
  await page.route('**/api/generar-plan',async route=>{
   const request=route.request();postRequests.push({body:request.postDataJSON(),key:request.headers()['idempotency-key'],authorized:request.headers().authorization==='Bearer '+owner.token});
   if(mode==='lost'){
    const response=await route.fetch();assert.equal(response.status(),200,'Real synthetic worker must publish successfully');realResult=await response.json();mode='real';return route.abort('failed');
   }
   if(mode==='real')return route.continue();
   if(mode==='html')return route.fulfill({contentType:'text/html',body:'<html>Synthetic unexpected page</html>'});
   if(mode==='malformed')return route.fulfill({json:{}});
   if(mode==='broken-meal')return route.fulfill({json:{...realResult,id_cliente:request.postDataJSON().id_cliente,tipo_plan:request.postDataJSON().tipo_plan,plan:{desayuno:null}}});
   if(mode==='unsafe-text')return route.fulfill({json:{...realResult,id_cliente:request.postDataJSON().id_cliente,tipo_plan:'opciones',plan:{desayuno:{tipo_plan:'opciones',kcal_objetivo:500,proteinas:{cantidad_objetivo:20,opciones:[{alimento:'synthetic',gramos:'<img src=x onerror="window.__unsafe=true">',equivalencia:'<svg onload="window.__unsafe=true">'}]},vegetales:[{alimento:'synthetic',gramos:'<img src=x onerror="window.__unsafe=true">'}]}}}});
   if(mode==='hold'){heldStarted();await new Promise(resolve=>releaseHeld=resolve);return route.fulfill({json:{...realResult,id_cliente:request.postDataJSON().id_cliente,tipo_plan:request.postDataJSON().tipo_plan}});}
   const errors={pending:[409,'generation_in_progress'],published:[409,'generation_result_pending'],failed:[409,'generation_failed'],gone:[410,'generation_result_unavailable'],reconciliation:[503,'generation_reconciliation_required'],conflict:[409,'idempotency_conflict']};
   const [status,code]=errors[mode];return route.fulfill({status,json:{detail:{code,message:'Synthetic '+code}}});
  });
  async function openClient(number=1){await page.goto(base+'/generar-plan?id=synthetic-generation-client-'+number);await page.locator('#step-2.active').waitFor();}
  async function generate(){await page.locator('#s2-generar').click();}
  async function recovery(){await page.locator('#s3-recovery').waitFor({state:'visible'});}
  async function scan(label,selector){await page.locator(selector).evaluate(element=>Promise.all(element.getAnimations({subtree:true}).filter(animation=>animation.effect.getTiming().iterations!==Infinity).map(animation=>animation.finished.catch(()=>{}))));const result=await new AxeBuilder({page}).include(selector).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();const dimensions=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));report.screens.push({label,dimensions,violations:result.violations.map(value=>({id:value.id,nodes:value.nodes.map(node=>({target:node.target,summary:node.failureSummary}))}))});await page.screenshot({path:path.join(out,label+'.png'),fullPage:true});}
  await openClient();await page.setViewportSize({width:320,height:900});await scan('parameters-320','#step-2');await generate();await recovery();
  assert.match(await page.locator('#s3-recovery-message').textContent(),/podría haberse generado/);
  assert.equal(postRequests.length,1);assert.equal(updates,1);assert.match(postRequests[0].key,/^[0-9a-f-]{36}$/);assert.ok(postRequests[0].authorized);
  const beforeRetry=await context.request.get(base+'/api/planes',{headers:auth});const beforeData=await beforeRetry.json();assert.equal(beforeData.total,1);
  await page.locator('#s3-retry').focus();await page.keyboard.press('Enter');await page.locator('#s3-resultado').waitFor({state:'visible'});
  assert.equal(postRequests.length,2);assert.deepEqual(postRequests[0],postRequests[1]);assert.equal(updates,1);
  const afterRetry=await context.request.get(base+'/api/planes',{headers:auth});assert.equal((await afterRetry.json()).total,1);
  const replay=await context.request.post(base+'/api/generar-plan',{headers:{...auth,'Idempotency-Key':postRequests[0].key},data:postRequests[0].body});assert.equal(replay.status(),200);assert.deepEqual(await replay.json(),realResult);
  const conflict=await context.request.post(base+'/api/generar-plan',{headers:{...auth,'Idempotency-Key':postRequests[0].key},data:{...postRequests[0].body,tipo_plan:'opciones'}});assert.equal(conflict.status(),409);assert.equal((await conflict.json()).detail.code,'idempotency_conflict');
  report.checks.push('A real generation is published and its response is lost; Enter retries the identical in-memory key and DTO, skips profile PUT, replays exact JSON and leaves one historical plan');
  let pdfRequests=[];await page.route('**/api/planes/*/pdf',route=>{pdfRequests.push({path:new URL(route.request().url()).pathname,authorized:route.request().headers().authorization==='Bearer '+owner.token});return route.continue();});
  const downloadEvent=page.waitForEvent('download');await page.locator('#s3-descargar-pdf').click();const download=await downloadEvent;assert.equal(fs.readFileSync(await download.path()).subarray(0,5).toString(),'%PDF-');
  assert.equal(pdfRequests[0].path,'/api/planes/'+realResult.plan_id+'/pdf');assert.ok(pdfRequests[0].authorized);assert.match(await page.locator('#s3-download-status').textContent(),/preparado/);
  await page.waitForFunction(()=>window.__blobState.created===window.__blobState.revoked);
  assert.equal((await context.request.get(base+'/api/planes/'+realResult.plan_id+'/pdf')).status(),401);
  assert.equal((await context.request.get(base+'/api/planes/'+realResult.plan_id+'/pdf',{headers:{Authorization:'Bearer '+other.token}})).status(),404);
  report.checks.push('Generated-plan PDF uses the exact persisted plan ID with Bearer; real missing auth is 401 and another owner gets 404; valid Blob is initiated and later revoked');
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});await scan('completed-'+width,'#step-3');}
  await page.locator('#s3-nuevo-plan-mismo').click();await page.locator('#step-2.active').waitFor();await page.locator('input[value="opciones"]').check();await generate();await recovery();
  assert.notEqual(postRequests[2].key,postRequests[0].key);assert.equal(postRequests[2].body.tipo_plan,'opciones');assert.match(await page.locator('#s3-recovery-message').textContent(),/planes disponibles/);
  const capped=await context.request.get(base+'/api/planes',{headers:auth});assert.equal((await capped.json()).total,1);
  report.checks.push('Explicit preparation of another DTO creates another key; real Free per-client quota rejects it and the historical count stays one');
  mode='update-error';await openClient(2);const postBefore=postRequests.length;await generate();await recovery();assert.equal(postRequests.length,postBefore);assert.match(await page.locator('#s3-recovery-message').textContent(),/No se envió la generación/);
  report.checks.push('A rejected profile PUT is visible and no generation POST is sent');
  mode='pending';await page.locator('#s3-retry').click();await recovery();const frozen=postRequests.at(-1);const savedUpdates=updates;
  for(const failure of ['published','reconciliation','html','malformed','broken-meal']){mode=failure;await page.locator('#s3-retry').click();await recovery();assert.deepEqual(postRequests.at(-1),frozen);assert.equal(updates,savedUpdates);assert.equal(await page.locator('#s3-resultado').isHidden(),true);}
  await page.setViewportSize({width:320,height:900});await scan('recovery-320','#step-3');
  for(const failure of ['failed','gone','conflict']){mode=failure;await openClient(2);await generate();await recovery();assert.equal(await page.locator('#s3-retry').isHidden(),true);assert.equal(await page.locator('#s3-resultado').isHidden(),true);}
  report.checks.push('Named transport doubles cover pending/published/failed/missing/conflict/reconciliation plus HTTP 200 HTML and empty JSON; recovery never shows success or silently rotates the key');
  mode='unsafe-text';await openClient(2);await page.locator('input[value="opciones"]').check();await generate();await page.locator('#s3-resultado').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>Boolean(window.__unsafe)),false);assert.match(await page.locator('#s3-comidas-container').innerText(),/<img/);assert.equal(await page.locator('#s3-comidas-container img, #s3-comidas-container svg').count(),0);
  report.checks.push('Malformed meal objects never leave partial success visible; transport-injected quantities and equivalents render as text without executing markup');
  mode='hold';await openClient(3);const started=new Promise(resolve=>heldStarted=resolve);await generate();await started;
  await page.evaluate(token=>{localStorage.setItem('mb_token',token);dispatchEvent(new StorageEvent('storage',{key:'mb_token'}));},other.token);releaseHeld();await recovery();assert.equal(await page.locator('#s3-resultado').isHidden(),true);assert.equal(await page.locator('#s3-retry').isDisabled(),true);assert.match(await page.locator('#s3-recovery-message').textContent(),/sesión cambió/);
  report.checks.push('An in-flight response after a cross-tab account/session change is discarded and the old operation cannot be retried');
  await page.evaluate(token=>localStorage.setItem('mb_token',token),owner.token);await page.goto(base+'/planes');await page.locator('#planes-tbody button').first().waitFor();
  const historyDownload=page.waitForEvent('download');await page.locator('#planes-tbody button').first().click();await historyDownload;assert.equal(pdfRequests.at(-1).path,'/api/planes/'+realResult.plan_id+'/pdf');assert.ok(pdfRequests.at(-1).authorized);
  for(const width of [320,390]){await page.setViewportSize({width,height:900});await scan('history-'+width,'.main-content');}
  let downloads=0;page.on('download',()=>downloads++);await page.route('**/api/planes/*/pdf',route=>route.fulfill({contentType:'text/html',body:'<html>Synthetic login page</html>'}));await page.locator('#planes-tbody button').first().click();await page.waitForFunction(()=>document.getElementById('planes-feedback').textContent.includes('PDF válido'));assert.equal(downloads,0);
  await page.unroute('**/api/planes/*/pdf');
  const pdfStarted=new Promise(resolve=>heldStarted=resolve);
  await page.route('**/api/planes/*/pdf',async route=>{const response=await route.fetch();heldStarted();await new Promise(resolve=>releaseHeld=resolve);return route.fulfill({response});});
  await page.locator('#planes-tbody button').first().click();await pdfStarted;const downloadsBeforeSwitch=downloads;
  await page.evaluate(token=>localStorage.setItem('mb_token',token),other.token);releaseHeld();
  await page.waitForFunction(()=>document.getElementById('planes-feedback').textContent.includes('sesión cambió'));
  assert.equal(downloads,downloadsBeforeSwitch);assert.equal(await page.locator('#planes-tbody tr').count(),0);
  report.checks.push('A valid PDF response arriving after a same-tab real account switch creates no Blob/download and discards the previous history rows');
  await page.unroute('**/api/planes/*/pdf');await page.evaluate(token=>localStorage.setItem('mb_token',token),owner.token);
  await page.route('**/api/planes?**',route=>route.fulfill({json:{}}));await page.reload();await page.locator('#planes-retry').waitFor({state:'visible'});assert.equal(await page.locator('#planes-tbody').innerText().then(text=>text.includes('Sin planes generados')),false);
  report.checks.push('History downloads the row’s exact plan with Bearer; HTTP 200 HTML never creates a PDF and an invalid history payload shows a retryable error instead of an empty portfolio');
  assert.ok(await page.evaluate(()=>Object.keys(localStorage).every(key=>['mb_token','mb_refresh_token','mb_tipo','mb_nombre','mb_email'].includes(key))));
  assert.deepEqual(report.pageErrors,[]);assert.ok(report.screens.every(screen=>!screen.violations.length),'Scoped axe findings');assert.ok(report.screens.every(screen=>screen.dimensions.scrollWidth<=screen.dimensions.width),'Horizontal overflow');
 }finally{await browser.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));}
 console.log(JSON.stringify({checks:report.checks.length,screens:report.screens.length,pageErrors:report.pageErrors.length,evidence:out}));
})().catch(error=>{console.error(error);process.exitCode=1;});
