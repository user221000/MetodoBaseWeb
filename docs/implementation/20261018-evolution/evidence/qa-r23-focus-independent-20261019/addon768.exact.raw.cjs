/* Independent additive768 CSSpx; actual own PG30/login/PUT/GET, no API doubles. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=process.env.QA_R23_ROOT,base='http://127.0.0.1:8795',out=path.resolve(process.argv[2]);
assert(root);assert.equal(process.env.METODOBASE_E2E_URL,base);fs.mkdirSync(out,{recursive:true});
const dependencies=process.env.FOLLOWUP_NODE_MODULES,{chromium}=require(path.join(dependencies,'playwright-core'));
const startup=JSON.parse(fs.readFileSync(process.env.FOLLOWUP_STARTUP_REPORT,'utf8'));
const report={scope:'Independent additive768 CSSpx only; one extra own PG30 UUID, preserved original8 not rerun. No API/failure/transport doubles.',results:[],screens:[],pageErrors:[],externalBlocked:0};
const snapshot=()=>Object.fromEntries(Object.keys(startup.sources).map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')]));
report.source_start=snapshot();report.startup_delta=Object.fromEntries(Object.entries(report.source_start).filter(([name,hash])=>startup.sources[name]!==hash));
const passed=(name,details={})=>report.results.push({name,passed:true,...details});
(async()=>{
  assert.equal(startup.runtime_revision,'20261019_personal_history_index');assert.equal(startup.actual_tables,30);assert.equal(startup.model_tables,29);assert.equal(startup.application_role_restricted_nonowner,true);
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
  try{
    const context=await browser.newContext({viewport:{width:768,height:1000},deviceScaleFactor:1,serviceWorkers:'block'});
    await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():(report.externalBlocked++,route.abort()));
    const login=await context.request.post(base+'/api/auth/login',{maxRedirects:0,data:{email:'followup-owner@example.invalid',password:'Synthetic-Followup-Only-2026!'}});assert.equal(login.status(),200);
    const pair=await login.json(),headers={Authorization:'Bearer '+pair.token};
    const asset=await context.request.get(base+'/static/js/api.js',{maxRedirects:0});assert.equal(asset.status(),200);assert.equal(crypto.createHash('sha256').update(await asset.body()).digest('hex'),startup.sources['web/static/js/api.js']);
    const initial=await context.request.get(base+'/api/estadisticas/seguimiento',{headers,maxRedirects:0});assert.equal(initial.status(),200);assert.equal((await initial.json()).items.length,4);
    const update=await context.request.put(base+'/api/clientes/followup-client-date',{headers,maxRedirects:0,data:{fecha_fin_suscripcion:'2030-01-01T00:00:00'}});assert.equal(update.status(),200);
    const facts=await context.request.get(base+'/api/estadisticas/seguimiento',{headers,maxRedirects:0});assert.equal(facts.status(),200);const data=await facts.json();assert.equal(data.items.length,3);assert.equal(data.payment_evidence,'unavailable');assert.equal(data.responsibility,'not_recorded');
    passed('Actual30 restricted role/source asset and fresh own PUT produce3 followup rows');
    await context.addInitScript(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);},pair);
    const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.name));
    const navigation=await page.goto(base+'/dashboard');assert.equal(navigation.status(),200);
    await page.waitForFunction(()=>document.querySelectorAll('#followup-list .followup-item').length===3);
    const geometry=await page.evaluate(()=>({innerWidth,scale:devicePixelRatio,scroll:document.documentElement.scrollWidth,root:document.getElementById('followup-section').getBoundingClientRect().toJSON(),sectionScroll:document.getElementById('followup-section').scrollWidth,sectionClient:document.getElementById('followup-section').clientWidth}));
    report.geometry=geometry;assert.equal(geometry.innerWidth,768);assert.equal(geometry.scale,1);assert.ok(geometry.scroll<=768);assert.ok(geometry.sectionScroll<=geometry.sectionClient);assert.ok(geometry.root.right<=768+.5);
    assert.match(await page.locator('#followup-section').innerText(),/Responsable: no asignado/);assert.match(await page.locator('#followup-section').innerText(),/Pagos: no disponibles/);
    await page.locator('#followup-refresh').focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>document.querySelector('#followup-refresh').disabled===false);
    assert.equal(await page.locator('#followup-list .followup-item').count(),3);assert.equal(await page.locator('#followup-refresh').evaluate(el=>document.activeElement===el),true);
    await page.locator('#followup-limit').selectOption('100');await page.locator('#followup-refresh').click();await page.waitForFunction(()=>document.querySelector('#followup-refresh').disabled===false);assert.equal(await page.locator('#followup-list .followup-item').count(),3);
    passed('Measured768 CSSpx has whole-page and section reflow; native keyboard/limit controls retain3 actual rows',geometry);
    await page.evaluate(fs.readFileSync(path.join(dependencies,'axe-core/axe.min.js'),'utf8'));
    const violations=await page.evaluate(async()=>{const result=await axe.run(document.getElementById('followup-section'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return result.violations.map(row=>({id:row.id,nodes:row.nodes.length}));});
    assert.deepEqual(violations,[]);assert.deepEqual(report.pageErrors,[]);
    const screen='followup-768.png';await page.screenshot({path:path.join(out,screen),fullPage:true});report.screens.push(screen);
    passed('Scoped section axeAA0 and768 screenshot; whole-page axe is not claimed',{violations});
    await context.close();
  }finally{await browser.close();report.source_end=snapshot();assert.deepEqual(report.source_end,report.source_start);fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');}
})().catch(error=>{report.failure={name:error.name,message:error.message};fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.error(error.stack);process.exitCode=1;});
