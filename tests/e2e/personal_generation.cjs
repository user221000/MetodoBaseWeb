/* Own worktree: real auth/profile/quota/worker/object/PDF APIs. Named delivery faults only. */
const {chromium}=require('playwright-core'), assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path'), crypto=require('node:crypto');
const base=process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8773';
if(!/^http:\/\/(127\.0\.0\.1|localhost):8773$/.test(base))throw Error('Dedicated personal fixture8773 only');
const out=path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux/personal-plan-ui-browser-'+(process.env.METODOBASE_EVIDENCE_BATCH || new Date().toISOString().replace(/[^0-9]/g,'')));
fs.mkdirSync(out,{recursive:true});
const report={scope:'Real temporary SQLite/auth/quota/core worker/private object/PDF on the isolated personal UI worktree. Delivery loss/holds and explicitly named structured status responses are browser transport doubles; no providers.',checks:[],screens:[],pageErrors:[]};
const check=(name,data={})=>report.checks.push({name,...data});
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function deferred(){let resolve;const promise=new Promise(done=>resolve=done);return{promise,resolve};}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const api=await browser.newContext(); const pairs={};
 const auth=pair=>({Authorization:'Bearer '+pair.token});
 const json=async response=>{assert.equal(response.status(),200,await response.text());return response.json();};
 try {
  let healthy=false;
  for(let count=0;count<40 && !healthy;count++){try{healthy=(await api.request.get(base+'/health/ready',{timeout:1000})).status()===200;}catch{}if(!healthy)await new Promise(done=>setTimeout(done,250));}
  assert.equal(healthy,true,'Own fixture must become ready before authentication');
  for(const suffix of ['owner','other','quota','failure','member'])pairs[suffix]=await json(await api.request.post(base+'/api/auth/login',{data:{email:'personal-'+suffix+'@example.invalid',password:'Synthetic-Personal-Password-2026!'}}));
  async function open(suffix,route='/mi-plan',invalidAccess=false){
   const context=await browser.newContext({acceptDownloads:true,viewport:{width:390,height:844}});
   await context.route('**/*',request=>request.request().url().startsWith(base)?request.continue():request.abort());
   await context.addInitScript(({pair,invalidAccess})=>{localStorage.setItem('mb_token',invalidAccess?'synthetic-expired-access':pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('mb_tipo','usuario');}, {pair:pairs[suffix],invalidAccess});
   const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.message));
   return{page,context,go:()=>page.goto(base+route)};
  }
  async function ready(page){await page.locator('#loading-plan').waitFor({state:'hidden'});await page.locator('#btn-generar').waitFor({state:'visible'});assert.equal(await page.locator('#btn-generar').isEnabled(),true);}
  async function completed(page){await page.waitForFunction(()=>document.getElementById('personal-operation-message').textContent.startsWith('Tu plan está listo.'));}
  async function used(suffix){return (await json(await api.request.get(base+'/api/usuario/suscripcion',{headers:auth(pairs[suffix])}))).planes_usados;}
  async function pdf(suffix,id){const response=await api.request.get(base+'/api/usuario/descargar-pdf?plan_id='+id,{headers:auth(pairs[suffix])});assert.equal(response.status(),200);const bytes=await response.body();assert.equal(bytes.subarray(0,5).toString(),'%PDF-');assert.equal(response.headers()['cache-control'],'no-store');return bytes;}
  async function scan(page,name,width=390){await page.setViewportSize({width,height:844});await page.evaluate(source=>{const script=document.createElement('script');script.nonce=document.querySelector('script[nonce]').nonce;script.textContent=source;document.head.append(script);},fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));const result=await page.evaluate(async()=>({overflow:document.documentElement.scrollWidth>innerWidth,axe:(await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(row=>({id:row.id,nodes:row.nodes.map(node=>node.target)}))}));fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(result,null,2));assert.deepEqual(result.axe,[],name+' axe');assert.equal(result.overflow,false,name+' overflow');await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});report.screens.push(name);}

  // Actual signed refresh, shared during boot, before the operation is established.
  let view=await open('owner','/mi-plan',true), page=view.page, refreshes=0;
  await page.route('**/api/auth/refresh',route=>{refreshes++;return route.continue();});
  await view.go();await ready(page);assert.equal(refreshes,1);
  pairs.owner=await page.evaluate(()=>({token:localStorage.getItem('mb_token'),refresh_token:localStorage.getItem('mb_refresh_token')}));
  check('Real invalid-access401 is refreshed once during personal initialization; own rotation preserves context');
  await scan(page,'empty-320',320);

  // First real worker result is committed, then delivery is deliberately lost.
  const firstStarted=deferred(), releaseFirst=deferred();let calls=0,firstKey,firstResult;
  await page.route('**/api/usuario/generar-plan',async route=>{
   calls++;const key=route.request().headers()['idempotency-key'];assert.match(key,/^[0-9a-f-]{36}$/i);
   if(calls===1){firstKey=key;const response=await route.fetch({timeout:120000});firstResult=await json(response);firstStarted.resolve();await releaseFirst.promise;return route.abort('failed');}
   assert.equal(key,firstKey,'Lost-response retry must use the same key');return route.continue();
  });
  await page.evaluate(()=>{document.getElementById('btn-generar').click();document.getElementById('btn-generar').click();});
  await firstStarted.promise;assert.equal(calls,1);assert.equal(await used('owner'),1);releaseFirst.resolve();
  await page.locator('#personal-operation-retry').waitFor({state:'visible'});assert.equal(await page.locator('#personal-operation-new').isVisible(),false);
  assert.equal(await page.locator('#context-bar').isVisible(),false,'An unconfirmed first operation must not claim an active plan');
  await scan(page,'unknown-390');await page.locator('#personal-operation-retry').focus();await page.keyboard.press('Enter');await completed(page);
  assert.equal(calls,2);assert.equal(await used('owner'),1);
  assert.equal((await json(await api.request.get(base+'/api/usuario/mi-plan',{headers:auth(pairs.owner)}))).plan_id,firstResult.plan_id);
  check('Double click sends one real generation; a lost committed response replays the same key/result and consumes one credit',{calls,credit:1});
  await page.unroute('**/api/usuario/generar-plan');
  await scan(page,'completed-390');

  // Later plan exists, but the displayed first result must still download its own PDF.
  const firstPdf=await pdf('owner',firstResult.plan_id);
  const later=await json(await api.request.post(base+'/api/usuario/generar-plan',{headers:{...auth(pairs.owner),'Idempotency-Key':crypto.randomUUID()}}));
  assert.notEqual(later.plan_id,firstResult.plan_id);
  const downloadPromise=page.waitForEvent('download');await page.locator('#btn-descargar-pdf').click();const download=await downloadPromise;
  assert.equal(hash(fs.readFileSync(await download.path())),hash(firstPdf));
  assert.equal(await used('owner'),2);
  check('Displayed plan downloads its exact persisted PDF after a newer plan exists, with real Bearer/object bytes');
  await page.locator('#personal-operation-new').click();await completed(page);assert.equal(await used('owner'),3);
  const newest=await json(await api.request.get(base+'/api/usuario/mi-plan',{headers:auth(pairs.owner)}));assert.notEqual(newest.plan_id,later.plan_id);
  check('Explicit next intention uses a fresh UUID and consumes exactly one additional confirmed credit');
  await scan(page,'completed-1440',1440);await view.context.close();

  view=await open('quota');page=view.page;await view.go();await ready(page);await page.locator('#btn-generar').click();
  await page.waitForFunction(()=>document.getElementById('personal-operation-message').textContent.includes('disponibles de este mes'));
  assert.equal(await page.locator('#personal-operation-new').isVisible(),false);assert.equal(await page.locator('#personal-operation-retry').isVisible(),false);
  assert.equal((await json(await api.request.get(base+'/api/usuario/historial',{headers:auth(pairs.quota)}))).planes.length,0);
  check('Actual exhausted personal quota returns a readable structured error and cannot create or blindly retry a new operation');await scan(page,'quota-320',320);await view.context.close();

  // Real strict exclusion failure, reserve+compensate once, then explicit new intent.
  const foods=await json(await api.request.get(base+'/api/usuario/catalogo-alimentos',{headers:auth(pairs.failure)}));
  await json(await api.request.put(base+'/api/usuario/perfil',{headers:auth(pairs.failure),data:{alimentos_excluidos:foods.proteina}}));
  view=await open('failure');page=view.page;await view.go();await ready(page);const keys=[];
  page.on('request',request=>{if(request.url()===base+'/api/usuario/generar-plan')keys.push(request.headers()['idempotency-key']);});
  await page.locator('#btn-generar').click();await page.locator('#personal-operation-retry').waitFor({state:'visible'});
  assert.equal(await page.locator('#personal-operation-new').isVisible(),false);
  await page.locator('#personal-operation-retry').click();await page.locator('#personal-operation-new').waitFor({state:'visible'});
  assert.ok((await page.locator('#personal-operation-message').textContent()).includes('no pudo completarse'));
  assert.equal(await used('failure'),0);
  await json(await api.request.put(base+'/api/usuario/perfil',{headers:auth(pairs.failure),data:{alimentos_excluidos:[]}}));
  await page.locator('#personal-operation-new').click();await completed(page);assert.equal(keys.length,3);assert.equal(keys[0],keys[1]);assert.notEqual(keys[1],keys[2]);assert.equal(await used('failure'),1);
  check('Real impossible exclusions retain the UUID until replay confirms released failure; after profile repair an explicit new UUID succeeds');await view.context.close();

  view=await open('other');page=view.page;await view.go();await ready(page);let publishedKey,publishedId,postCount=0;
  await page.route('**/api/usuario/generar-plan',async route=>{
   postCount++;const key=route.request().headers()['idempotency-key'];
   if(postCount===1){publishedKey=key;const response=await route.fetch({timeout:120000});publishedId=(await json(response)).plan_id;return route.fulfill({status:400,json:{detail:{code:'generation_unavailable',message:'Synthetic400 delivered after a real durable commit'}}});}
   assert.equal(key,publishedKey);return route.continue();
  });
  await page.locator('#btn-generar').click();await page.locator('#personal-operation-retry').waitFor({state:'visible'});assert.equal(await page.locator('#personal-operation-new').isVisible(),false);assert.equal(await used('other'),1);
  await page.locator('#personal-operation-retry').click();await completed(page);assert.equal(postCount,2);assert.equal(await used('other'),1);assert.equal((await json(await api.request.get(base+'/api/usuario/mi-plan',{headers:auth(pairs.other)}))).plan_id,publishedId);
  check('Named400 delivery after a real durable publication preserves UUID and replays the exact plan without a second credit');await view.context.close();

  // A profile delivery must not leave old values or touch separate legacy activity keys.
  view=await open('owner');page=view.page;const profileStarted=deferred(),releaseProfile=deferred();
  await page.addInitScript(()=>localStorage.setItem('mb_daily_2000-01-01','synthetic-legacy-activity-marker'));
  await page.route('**/api/usuario/perfil',async route=>{const response=await route.fetch();assert.equal(response.status(),200);profileStarted.resolve();await releaseProfile.promise;return route.fulfill({response});});
  await view.go();await profileStarted.promise;await page.evaluate(pair=>Api.saveTokens(pair),pairs.other);releaseProfile.resolve();
  await page.waitForFunction(()=>document.getElementById('personal-operation-message').textContent.includes('sesión cambió'));
  assert.equal(await page.locator('#kpi-kcal').textContent(),'');assert.equal(await page.locator('#saludo').textContent(),'Mi plan');
  assert.equal(await page.evaluate(()=>localStorage.getItem('mb_daily_2000-01-01')),'synthetic-legacy-activity-marker');
  check('Late real personal profile is discarded and sensitive DOM cleared while unrelated legacy activity stays untouched');await view.context.close();

  // Old successful generation delivered after a real account replacement.
  view=await open('owner');page=view.page;await view.go();await ready(page);const started=deferred(),release=deferred();
  await page.route('**/api/usuario/generar-plan',async route=>{const response=await route.fetch({timeout:120000});assert.equal(response.status(),200);started.resolve();await release.promise;return route.fulfill({response});});
  await page.locator('#btn-generar').click();await started.promise;await page.evaluate(pair=>Api.saveTokens(pair),pairs.other);release.resolve();
  await page.waitForFunction(()=>document.getElementById('personal-operation-message').textContent.includes('sesión cambió'));
  assert.equal(await page.locator('#meals-container').textContent(),'');assert.equal(await page.locator('#btn-descargar-pdf').isVisible(),false);
  assert.equal(await page.evaluate(()=>localStorage.getItem('mb_token')),pairs.other.token);
  check('A real committed old generation delivered late cannot render private data or overwrite a newly selected account');await view.context.close();

  // A historical PDF response and history JSON cannot reach another account.
  view=await open('owner','/mi-historial');page=view.page;await view.go();await page.locator('#tbody-planes tr').first().waitFor();await scan(page,'history-768',768);
  let downloadEvent=page.waitForEvent('download');await page.locator('[data-plan-id="'+firstResult.plan_id+'"]').click();assert.equal(hash(fs.readFileSync(await (await downloadEvent).path())),hash(firstPdf));
  check('History downloads an older exact plan ID instead of latest');
  const heldPdf=deferred(),releasePdf=deferred();let staleDownloads=0;page.on('download',()=>staleDownloads++);
  await page.route('**/api/usuario/descargar-pdf?*',async route=>{const response=await route.fetch();assert.equal(response.status(),200);heldPdf.resolve();await releasePdf.promise;return route.fulfill({response});});
  await page.locator('[data-plan-id="'+firstResult.plan_id+'"]').click();await heldPdf.promise;await page.evaluate(pair=>Api.saveTokens(pair),pairs.other);releasePdf.resolve();
  await page.locator('#history-error').waitFor({state:'visible'});await page.waitForTimeout(100);assert.equal(staleDownloads,0);assert.equal(await page.locator('#tbody-planes').textContent(),'');await view.context.close();
  check('A real old PDF delivery after account replacement creates no Blob download and clears previous history');

  view=await open('owner','/mi-historial');page=view.page;const heldHistory=deferred(),releaseHistory=deferred();
  await page.route('**/api/usuario/historial',async route=>{const response=await route.fetch();assert.equal(response.status(),200);heldHistory.resolve();await releaseHistory.promise;return route.fulfill({response});});
  await view.go();await heldHistory.promise;await page.evaluate(pair=>Api.saveTokens(pair),pairs.other);releaseHistory.resolve();await page.locator('#history-error').waitFor({state:'visible'});assert.equal(await page.locator('#tbody-planes').textContent(),'');await view.context.close();
  check('Late real history JSON is discarded after account replacement');

  // Legacy professional member keeps their own personal plan and PDF subject.
  view=await open('member');page=view.page;await view.go();await ready(page);await page.locator('#btn-generar').click();await completed(page);
  const memberPlan=await json(await api.request.get(base+'/api/usuario/mi-plan',{headers:auth(pairs.member)}));
  const foreign=await api.request.get(base+'/api/usuario/descargar-pdf?plan_id='+firstResult.plan_id,{headers:auth(pairs.member)});assert.equal(foreign.status(),404);
  downloadEvent=page.waitForEvent('download');await page.locator('#btn-descargar-pdf').click();assert.equal(hash(fs.readFileSync(await (await downloadEvent).path())),hash(await pdf('member',memberPlan.plan_id)));
  check('Legacy gym-type team member generates and downloads under own personal subject; foreign owner plan is404');await view.context.close();

  // Only these two responses are fabricated: safely bounded presentation checks.
  for(const [code,status] of [['generation_in_progress',409],['generation_reconciliation_required',503]]){
   view=await open('other');page=view.page;await view.go();await ready(page);const seen=[];
   await page.route('**/api/usuario/generar-plan',route=>{seen.push(route.request().headers()['idempotency-key']);return route.fulfill({status,json:{detail:{code,message:'Synthetic structured transport state'}}});});
   await page.locator('#btn-generar').click();await page.locator('#personal-operation-retry').waitFor({state:'visible'});await page.locator('#personal-operation-retry').click();await page.locator('#personal-operation-retry').waitFor({state:'visible'});assert.equal(seen.length,2);assert.equal(seen[0],seen[1]);assert.equal(await page.locator('#personal-operation-new').isVisible(),false);await scan(page,code+'-320',320);await view.context.close();
   check('Named browser response double '+code+' keeps same UUID and exposes history/retry without a blind new generation');
  }
  assert.deepEqual(report.pageErrors,[]);
 }finally{await api.close();await browser.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));}
 console.log(JSON.stringify({groups:report.checks.length,screens:report.screens.length,pageErrors:report.pageErrors.length,evidence:out}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
