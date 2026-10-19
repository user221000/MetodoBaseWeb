/* R13 uses local templates/static assets and synthetic intercepted API responses. */
const { chromium } = require('playwright-core');
const { AxeBuilder } = require('@axe-core/playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const base = process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8765';
if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base)) throw Error('Only a local synthetic server is allowed');
const out = path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux');
const report={scope:'R13 local candidate UI; synthetic API transport; no external connections',checks:[],screens:[],errors:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try {
  async function newPage(kind){
   const context=await browser.newContext({viewport:{width:390,height:844},timezoneId:'America/Mexico_City'});
   await context.route('**/*',route=>route.request().url().startsWith(base) ? route.continue() : route.abort());
   await context.addInitScript(kind=>{localStorage.setItem('mb_token','synthetic-ui-token');localStorage.setItem('mb_tipo',kind);localStorage.setItem('mb_nombre','Synthetic UI');},kind);
   const page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
   await page.route('**/api/**',route=>{
    const url=new URL(route.request().url()), endpoint=url.pathname;
    if(endpoint==='/api/auth/me') return route.fulfill({json:{role:'owner',tipo:kind,plan_features:{gestion_suscripciones:true,preferencias_alimentos:true}}});
    if(endpoint==='/api/gym/profile') return route.fulfill({json:{nombre:'Gimnasio sintético'}});
    if(endpoint==='/api/clientes' && route.request().method()==='GET') return route.fulfill({json:{total:1,clientes:[{id_cliente:'synthetic-client',nombre:'Cliente sintético',telefono:'5550000000',edad:32,peso_kg:70,objetivo:'mantenimiento',fecha_registro:'2026-10-18',total_planes_generados:1}]}});
    if(endpoint==='/api/gym/planes-suscripcion') return route.fulfill({json:{planes:[{id:1,nombre:'Mensual',duracion_dias:30,precio:100,moneda:'MXN',activo:true}]}});
    if(endpoint==='/api/alimentos/catalogo') return route.fulfill({json:{categorias:{proteinas:['pollo','huevo']}}});
    if(endpoint==='/api/usuario/historial') return route.fulfill({json:{planes:[{id:1,fecha:'2026-10-18T10:00:00',kcal_objetivo:2000,proteina_g:120,carbs_g:230,grasa_g:65,tipo_plan:'menú fijo',tiene_pdf:true}]}});
    if(endpoint==='/api/usuario/descargar-pdf') return route.fulfill({contentType:'application/pdf',body:'%PDF-1.4 synthetic browser fixture'});
    return route.fulfill({status:503,json:{detail:'Servicio sintético temporalmente no disponible.'}});
   });
   return page;
  }
  async function scan(page,label){
   await page.evaluate(()=>Promise.all(document.getAnimations().filter(a=>Number.isFinite(a.effect.getComputedTiming().endTime)).map(a=>a.finished.catch(()=>{}))));
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('.u-panel-overlay,.u-panel')).filter(el=>el.getClientRects().length).every(el=>parseFloat(getComputedStyle(el).opacity)===1));
   await page.evaluate(()=>scrollTo(0,0));
   const dimensions=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,titleTop:document.querySelector('h1')?.getBoundingClientRect().top}));
   const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
   report.screens.push({label,dimensions,violations:axe.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
   await page.screenshot({path:path.join(out,label+'.png'),fullPage:true});
  }
  const gym=await newPage('gym');
  await gym.goto(base+'/clientes');await gym.locator('.btn-editar').waitFor();
  for(const width of [320,390,768,1440]){await gym.setViewportSize({width,height:900});await scan(gym,'clients-after-'+width);}
  await gym.setViewportSize({width:390,height:844});await gym.evaluate(()=>scrollTo(0,0));
  const header=await gym.locator('h1').boundingBox(), hamburger=await gym.locator('#btn-hamburger').boundingBox();
  assert.ok(header.y>=hamburger.y+hamburger.height,'Menu must not cover the page title');
  await gym.locator('#btn-hamburger').focus();await gym.keyboard.press('Enter');
  assert.equal(await gym.locator('#btn-hamburger').getAttribute('aria-expanded'),'true');
  await gym.keyboard.press('Escape');
  assert.equal(await gym.locator('#btn-hamburger').getAttribute('aria-expanded'),'false');
  assert.equal(await gym.locator('#btn-hamburger').evaluate(el=>el===document.activeElement),true);
  report.checks.push('Gym menu reserves title space; native Enter opens it; Escape restores the trigger');
  await gym.locator('#btn-nuevo-cliente').focus();await gym.keyboard.press('Enter');
  await gym.locator('#modal-cliente').waitFor({state:'visible'});
  assert.equal(await gym.locator('#field-nombre').evaluate(el=>el===document.activeElement),true);
  await gym.locator('#modal-close').focus();await gym.keyboard.press('Shift+Tab');
  assert.equal(await gym.locator('#btn-guardar-cliente').evaluate(el=>el===document.activeElement),true);
  await scan(gym,'client-dialog-after');
  await gym.locator('#field-nombre').fill('Cliente de prueba');await gym.locator('#field-edad').fill('30');
  await gym.locator('#field-objetivo').selectOption('mantenimiento');await gym.locator('#field-peso').fill('70');
  await gym.locator('#field-estatura').fill('170');await gym.locator('#field-nivel').selectOption('leve');
  await gym.locator('#btn-guardar-cliente').click();await gym.locator('#client-form-error').waitFor({state:'visible'});
  assert.match(await gym.locator('#client-form-error').textContent(),/No se pudo guardar/);
  await gym.locator('#toggle-avanzados').click();await gym.locator('#btn-abrir-exclusiones').click();
  await gym.locator('.food-item-row').first().waitFor();await gym.locator('.food-item-row').first().focus();await gym.keyboard.press('Space');
  assert.equal(await gym.locator('.food-item-row').first().getAttribute('aria-pressed'),'true');
  await scan(gym,'client-exclusions-dialog-after');
  await gym.keyboard.press('Escape');assert.equal(await gym.locator('#btn-abrir-exclusiones').evaluate(el=>el===document.activeElement),true);
  await gym.keyboard.press('Escape');assert.equal(await gym.locator('#btn-nuevo-cliente').evaluate(el=>el===document.activeElement),true);
  report.checks.push('Client dialogs have named inputs, visible save errors, trapped focus, native exclusion buttons and nested Escape restoration');
  await gym.goto(base+'/configuracion');await gym.locator('.plan-precio-input').waitFor();
  for(const width of [320,390,768,1440]){await gym.setViewportSize({width,height:900});await scan(gym,'settings-after-'+width);}
  const user=await newPage('usuario');await user.goto(base+'/mi-historial');await user.locator('.u-pdf-btn').waitFor();
  for(const width of [320,390,768,1440]){await user.setViewportSize({width,height:900});await scan(user,'history-after-'+width);}
  await user.setViewportSize({width:320,height:844});
  await user.locator('.u-table-wrap').focus();await user.keyboard.press('End');
  await user.locator('.u-pdf-btn').focus();
  assert.ok(await user.locator('.u-pdf-btn').evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth;}),'PDF must be reachable inside viewport');
  const download=user.waitForEvent('download');await user.keyboard.press('Enter');assert.match((await download).suggestedFilename(),/plan_nutricional_1\.pdf/);
  await user.locator('.u-history-open').focus();await user.keyboard.press('Enter');
  await user.locator('#panel-progreso-overlay').waitFor({state:'visible'});
  assert.equal(await user.locator('#panel-progreso-close').evaluate(el=>el===document.activeElement),true);
  await user.locator('#cal-days button').first().focus();await user.keyboard.press('Enter');
  await user.locator('#day-detail').waitFor({state:'visible'});await scan(user,'history-calendar-after');
  await user.keyboard.press('Escape');assert.equal(await user.locator('.u-history-open').evaluate(el=>el===document.activeElement),true);
  report.checks.push('History PDF scrolls into view and downloads with Enter at 320px; native date/calendar controls trap and restore focus');
  await user.route('**/api/usuario/historial',route=>route.fulfill({contentType:'text/html',body:'<html>Unavailable</html>'}));
  await user.goto(base+'/mi-historial');await user.locator('#history-error').waitFor({state:'visible'});
  assert.equal(await user.locator('#empty-state').isVisible(),false);
  report.checks.push('A failed history response is an announced recoverable error, never an empty history');
  await gym.setViewportSize({width:390,height:844});
  for(const route of ['login-gym','login-usuario']){
   await gym.goto(base+'/'+route);await gym.locator('.pwd-toggle').focus();await gym.keyboard.press('Enter');
   assert.equal(await gym.locator('#pwdField').getAttribute('type'),'text');
   assert.equal(await gym.locator('.pwd-toggle').getAttribute('aria-label'),'Ocultar contraseña');
   await scan(gym,route+'-after-390');
  }
  fs.writeFileSync(path.join(out,'responsive-accessibility-browser.json'),JSON.stringify(report,null,2));
  assert.deepEqual(report.errors,[]);assert.ok(report.screens.every(s=>s.dimensions.scrollWidth<=s.dimensions.width),'Horizontal document overflow');
  assert.ok(report.screens.every(s=>s.violations.length===0),'Automated WCAG AA violations');
  console.log(JSON.stringify(report));
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
