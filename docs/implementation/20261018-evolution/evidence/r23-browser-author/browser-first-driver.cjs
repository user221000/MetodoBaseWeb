/* Real PG/auth/API browser; explicitly marked response doubles only for failure/timing. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const dependencies=process.env.FOLLOWUP_NODE_MODULES||path.resolve(__dirname,'node_modules');
const {chromium}=require(path.join(dependencies,'playwright-core'));
const base=process.env.METODOBASE_E2E_URL||'http://127.0.0.1:8795';assert.equal(base,'http://127.0.0.1:8795');
const out=path.resolve(process.argv[2]);fs.mkdirSync(out,{recursive:true});
const report={scope:'Own migrated PostgreSQL head28 + actual password login/auth/HTTP; response failures/timing explicitly doubled',results:[],screens:[],pageErrors:[],externalBlocked:0};
const passed=(name,details={})=>report.results.push({name,passed:true,...details});
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});
    await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin===base)return route.continue();report.externalBlocked++;return route.abort();});
    async function login(suffix){const response=await context.request.post(base+'/api/auth/login',{data:{email:'followup-'+suffix+'@example.invalid',password:'Synthetic-Followup-Only-2026!'}});assert.equal(response.status(),200);return response.json();}
    const owner=await login('owner'),other=await login('other');
    const headers={Authorization:'Bearer '+owner.token};
    assert.equal((await context.request.get(base+'/api/estadisticas/seguimiento')).status(),401);
    const facts=await context.request.get(base+'/api/estadisticas/seguimiento',{headers});assert.equal(facts.status(),200);
    const data=await facts.json();assert.equal(data.items.length,4);assert.equal(data.payment_evidence,'unavailable');assert.equal(data.metrics.plans_saved,1);
    assert.equal((await context.request.get(base+'/api/estadisticas/seguimiento',{headers:{Authorization:'Bearer '+other.token}})).status(),200);
    passed('Actual authenticated PostgreSQL facts and separate-account scope');
    await context.addInitScript(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('unscoped-legacy-canary','preserve-exact-bytes');},owner);
    const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.name));
    await page.goto(base+'/dashboard');await page.waitForFunction(()=>document.querySelectorAll('#followup-list .followup-item').length===4);
    assert.equal(await page.locator('#followup-list span').count(),0);
    assert.match(await page.locator('#followup-section').innerText(),/Responsable: no asignado/);
    assert.match(await page.locator('#followup-section').innerText(),/Pagos: no disponibles/);
    assert.equal(await page.locator('#followup-list a[href*="pago"]').count(),0);
    passed('Persisted names render as text; causes, responsibility and payment limitations are visible');
    for(const width of [1440,390,320]){
      await page.setViewportSize({width,height:1000});await page.locator('#followup-section').scrollIntoViewIfNeeded();
      await page.addScriptTag({content:fs.readFileSync(path.join(dependencies,'axe-core/axe.min.js'),'utf8')});
      const axe=await page.evaluate(async()=>{const r=await axe.run(document.getElementById('followup-section'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.length}));});
      assert.deepEqual(axe,[]);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      const name='followup-'+width+'.png';await page.screenshot({path:path.join(out,name),fullPage:true});report.screens.push(name);
    }
    passed('Scoped axe AA and overflow at 320/390/1440; three screens (whole-page axe not claimed)');
    await page.locator('#followup-refresh').focus();await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('#followup-refresh').disabled===false);
    assert.equal(await page.locator('#followup-list .followup-item').count(),4);
    passed('Refresh works with keyboard and retains an operable native control');
    let fail=true;await page.route('**/api/estadisticas/seguimiento?*',async route=>{
      if(fail)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:{code:'followup_unavailable',message:'Synthetic read failure'}})});return route.continue();
    });
    await page.locator('#followup-refresh').click();await page.locator('#followup-error').waitFor({state:'visible'});
    assert.equal(await page.locator('#followup-list .followup-item').count(),4);assert.match(await page.locator('#followup-error').innerText(),/no se han actualizado/);
    await page.screenshot({path:path.join(out,'followup-stale-error.png'),fullPage:true});report.screens.push('followup-stale-error.png');
    fail=false;await page.locator('#followup-refresh').click();await page.waitForFunction(()=>document.querySelector('#followup-error').hidden);
    passed('503 response double retains previous dated rows and explicit retry recovers actual API');
    await page.unroute('**/api/estadisticas/seguimiento?*');
    const corrected=await context.request.put(base+'/api/clientes/followup-client-date',{headers,data:{fecha_fin_suscripcion:'2030-01-01T00:00:00'}});assert.equal(corrected.status(),200);
    await page.locator('#followup-refresh').click();await page.waitForFunction(()=>document.querySelectorAll('#followup-list .followup-item').length===3);
    passed('Real administrative-date update changes cause without implying a payment or completed contact');
    const sync=await page.evaluate(pair=>{Api.saveTokens(pair);return{rows:document.querySelectorAll('#followup-list .followup-item').length,metrics:document.querySelector('#followup-metrics').textContent,legacy:localStorage.getItem('unscoped-legacy-canary')};},other);
    assert.equal(sync.rows,0);assert.equal(sync.metrics,'');assert.equal(sync.legacy,'preserve-exact-bytes');
    assert.equal(await page.locator('#followup-refresh').isDisabled(),true);
    passed('Actual same-document account replacement clears visible rows/counters synchronously; unrelated storage unchanged');
    const second=await context.newPage();second.on('pageerror',error=>report.pageErrors.push(error.name));let release,started;
    const gate=new Promise(resolve=>release=resolve),arrival=new Promise(resolve=>started=resolve);
    await second.route('**/api/estadisticas/seguimiento?*',async route=>{const response=await route.fetch();started();await gate;await route.fulfill({response});});
    await second.goto(base+'/dashboard');await arrival;
    await second.evaluate(pair=>Api.saveTokens(pair),other);release();
    await second.waitForFunction(()=>document.querySelector('#followup-refresh').disabled && document.querySelector('#followup-error').hidden===false);
    assert.equal(await second.locator('#followup-list .followup-item').count(),0);
    await second.screenshot({path:path.join(out,'followup-late-session.png'),fullPage:true});report.screens.push('followup-late-session.png');
    passed('Actual old-account API response held at browser transport is discarded after account replacement');
    assert.deepEqual(report.pageErrors,[]);await context.close();
  }finally{await browser.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');}
})().catch(error=>{report.failure={name:error.name,message:error.message};fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.error(error.stack);process.exitCode=1;});
