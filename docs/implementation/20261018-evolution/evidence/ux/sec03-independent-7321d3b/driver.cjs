'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const playwright = process.env.SEC03_PLAYWRIGHT || 'playwright-core';
const {chromium} = require(playwright);
const base = process.env.SEC03_BASE_URL || 'http://127.0.0.1:8774';
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);
const out = path.resolve(process.argv[2] || '.');
const report = {scope:'SEC03 scoped browser regression, real auth/CRUD except explicitly marked renderer doubles',
  results:[], payloads:[], pageErrors:[], externalRequestsBlocked:0};
const check = (name, details={}) => report.results.push({case:name, passed:true, ...details});
(async () => {
  fs.mkdirSync(out, {recursive:true});
  const browser = await chromium.launch({executablePath:process.env.SEC03_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1280,height:900}, serviceWorkers:'block'});
    await context.route('**/*', route => {
      if (new URL(route.request().url()).origin === new URL(base).origin) return route.continue();
      report.externalRequestsBlocked++;
      return route.abort();
    });
    for (const method of ['get','post','put','patch','delete','fetch','head']) {
      const actual = context.request[method].bind(context.request);
      context.request[method] = (url, options={}) => {
        assert.equal(new URL(url, base).origin, new URL(base).origin);
        return actual(url, {...options, maxRedirects:0});
      };
    }
    async function login(suffix) {
      const response = await context.request.post(base + '/api/auth/login', {data:{email:'drawer-'+suffix+'@example.invalid', password:'Synthetic-Drawer-Only-2026!'}});
      assert.equal(response.status(),200);
      return response.json();
    }
    const owner = await login('owner'), other = await login('other');
    const headers = {Authorization:'Bearer '+owner.token};
    const stored=[];
    for (const name of ['Synthetic <span data-sec03-name=1>Marker</span>', 'Synthetic <svg onload=&#116;&#111;&#112;[8417]=1></svg>']) {
      const response = await context.request.post(base + '/api/clientes', {headers,data:{nombre:name,edad:30,sexo:'M',peso_kg:75,estatura_cm:175,nivel_actividad:'moderada',objetivo:'mantenimiento'}});
      assert.equal(response.status(),201);
      const created = await response.json();
      const loaded = await context.request.get(base+'/api/clientes/'+created.id_cliente,{headers});
      assert.equal(loaded.status(),200);
      const client = await loaded.json();
      assert.match(client.id_cliente,/^[0-9a-f-]{36}$/);
      assert.ok(client.nombre.includes('<'));
      stored.push(client);
      report.payloads.push({input_name:name, stored_name:client.nombre, created_status:201, reload_status:200, generated_uuid:true});
    }
    check('Persisted markup remains accepted and preserved by real CRUD');
    assert.equal((await context.request.get(base+'/api/clientes')).status(),401);
    assert.equal((await context.request.get(base+'/api/clientes/'+stored[0].id_cliente,{headers:{Authorization:'Bearer '+other.token}})).status(),404);
    check('Anonymous and other-account access stay denied',{anonymous:401, other_account:404});
    await context.addInitScript(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('mb_tipo','gym');}, {token:owner.token,refresh_token:owner.refresh_token});
    const page = await context.newPage();
    page.on('pageerror',error=>report.pageErrors.push(error.name));
    const response = await page.goto(base+'/dashboard');
    const csp = response.headers()['content-security-policy'] || '';
    assert.ok(/script-src[^;]*'nonce-/.test(csp));
    assert.ok(!/script-src[^;]*'unsafe-inline'/.test(csp));
    check('Actual script CSP still requires a nonce',{nonce_present:true, unsafe_inline:false});
    await page.waitForFunction(()=>typeof abrirDrawer==='function');
    await page.evaluate(()=>abrirDrawer('sub-inactivas'));
    await page.locator('#drawer-body .drawer-client-card').first().waitFor();
    const real = await page.evaluate(()=>({
      marker_elements:document.querySelectorAll('#drawer-body [data-sec03-name],#drawer-body svg').length,
      names:[...document.querySelectorAll('#drawer-body .drawer-client-name')].map(node=>node.textContent),
      ids:[...document.querySelectorAll('#drawer-body .drawer-client-card')].map(node=>node.dataset.clienteId),
      main_feed_markup:document.querySelectorAll('#recent-activity [data-sec03-name]').length,
      javascript_marker:window[8417]===1,
    }));
    assert.equal(real.marker_elements,0);
    for(const client of stored) {
      assert.ok(real.names.includes(client.nombre));
      assert.ok(real.ids.includes(client.id_cliente));
    }
    assert.equal(real.main_feed_markup,0);
    assert.equal(real.javascript_marker,false);
    report.persistedRenderer=real;
    check('Persisted names render as literal text without span/SVG nodes');
    await page.screenshot({path:path.join(out,'dashboard-drawer-text-after.png'),fullPage:true});
    const boundary = await page.evaluate(()=>{
      const id='id" data-sec03-id="1"><svg data-sec03-id=1></svg>';
      const name='< <';
      const meta='<span data-sec03-meta=1>Value</span>';
      _renderDrawerClients([{id_cliente:id,nombre:name,edad:meta,peso_kg:meta,objetivo:meta,fecha_fin_suscripcion:'2999-01-01'}]);
      const card=document.querySelector('#drawer-body .drawer-client-card');
      let clicked=null;
      const original=abrirDetalleCliente;
      abrirDetalleCliente=value=>{clicked=value;};
      try {card.querySelector('.drawer-client-name').click();} finally {abrirDetalleCliente=original;}
      return {id, actual_id:card.dataset.clienteId, clicked,
        marker_elements:document.querySelectorAll('#drawer-body [data-sec03-id],#drawer-body [data-sec03-meta],#drawer-body svg').length,
        name:card.querySelector('.drawer-client-name').textContent,
        avatar:card.querySelector('.drawer-avatar').textContent,
        meta:card.querySelector('.drawer-client-meta').textContent,
        badge_active:!!card.querySelector('.drawer-sub-active'),
        scope:'Renderer double only: no claim HTTP accepts arbitrary IDs or nonnumeric age/weight'};
    });
    assert.equal(boundary.marker_elements,0);
    assert.equal(boundary.actual_id,boundary.id);
    assert.equal(boundary.clicked,boundary.id);
    assert.equal(boundary.name,'< <');
    assert.equal(boundary.avatar,'<<');
    assert.ok(boundary.meta.includes('<span data-sec03-meta=1>Value</span>'));
    assert.equal(boundary.badge_active,true);
    report.rendererBoundary=boundary;
    check('ID dataset, initials and metadata remain literal at renderer boundary');
    check('Delegated click preserves the exact opaque ID');
    const controls=await page.evaluate(()=>{
      _renderDrawerClients([{id_cliente:'synthetic-plain',nombre:'Ana Peña',edad:31,peso_kg:62,objetivo:'mantenimiento',fecha_fin_suscripcion:'2000-01-01'}]);
      const normal={name:document.querySelector('.drawer-client-name').textContent,avatar:document.querySelector('.drawer-avatar').textContent,
        meta:document.querySelector('.drawer-client-meta').textContent,expired:!!document.querySelector('.drawer-sub-expired')};
      _renderDrawerClients([]);
      return{normal,empty:document.querySelector('#drawer-body .drawer-empty').textContent,cards:document.querySelectorAll('#drawer-body .drawer-client-card').length};
    });
    assert.equal(controls.normal.name,'Ana Peña');
    assert.equal(controls.normal.avatar,'AP');
    assert.ok(controls.normal.meta.includes('31 años'));
    assert.ok(controls.normal.meta.includes('62 kg'));
    assert.equal(controls.normal.expired,true);
    assert.equal(controls.cards,0);
    assert.ok(controls.empty.includes('No hay clientes'));
    check('Normal labels, badges and empty state remain usable');
    const errorMessage='<span data-sec03-error=1>Synthetic error marker</span>';
    await page.evaluate(async message=>{
      const original=Api.clientes.listar;
      Api.clientes.listar=()=>Promise.reject(new Error(message));
      try {await abrirDrawer('sub-inactivas');} finally {Api.clientes.listar=original;}
    },errorMessage);
    const error=await page.evaluate(()=>({elements:document.querySelectorAll('#drawer-body [data-sec03-error]').length,text:document.querySelector('#drawer-body .drawer-empty').textContent}));
    assert.equal(error.elements,0);
    assert.equal(error.text,'Error: '+errorMessage);
    report.errorBoundary={...error,backend_attacker_control_not_established:true};
    check('Error boundary displays literal text without markup');
    await page.screenshot({path:path.join(out,'dashboard-drawer-error-after.png'),fullPage:true});
    const updatedName = 'Updated <img data-sec03-update=1 alt="literal"> & <b>Text</b>';
    assert.equal((await context.request.put(base+'/api/clientes/'+stored[0].id_cliente,{headers:{Authorization:'Bearer '+other.token},data:{nombre:'Must not replace'}})).status(),404);
    const missingCsrf = await context.request.put(base+'/api/clientes/'+stored[0].id_cliente,{data:{nombre:'Must not replace'}});
    assert.equal(missingCsrf.status(),403);assert.equal((await missingCsrf.json()).detail,'CSRF token missing');
    const unchanged = await context.request.get(base+'/api/clientes/'+stored[0].id_cliente,{headers});assert.equal((await unchanged.json()).nombre,stored[0].nombre);
    assert.equal((await context.request.put(base+'/api/clientes/'+stored[0].id_cliente,{headers,data:{nombre:updatedName}})).status(),200);
    const updated = await context.request.get(base+'/api/clientes/'+stored[0].id_cliente,{headers});
    assert.equal(updated.status(),200);const updatedClient=await updated.json();assert.ok(updatedClient.nombre.includes('<'));
    await page.evaluate(()=>abrirDrawer('sub-inactivas'));
    await page.waitForFunction(name=>[...document.querySelectorAll('.drawer-client-name')].some(el=>el.textContent===name),updatedClient.nombre);
    assert.equal(await page.locator('#drawer-body [data-sec03-update],#drawer-body img,#drawer-body b').count(),0);
    check('QA: Real update and read preserve markup as text; anonymous CSRF403 and foreign404 updates do not mutate',{independent_additional:true});
    const exactCard=page.locator('#drawer-body .drawer-client-card').filter({hasText:updatedClient.nombre});
    const detailResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clientes/'+stored[0].id_cliente && r.request().method()==='GET');
    await exactCard.click();assert.equal((await detailResponse).status(),200);
    await page.waitForFunction(name=>document.getElementById('dd-nombre').value===name,updatedClient.nombre);
    assert.equal(await page.locator('#detail-drawer-name').textContent(),updatedClient.nombre);
    assert.equal(await page.locator('#detail-drawer [data-sec03-update],#detail-drawer img,#detail-drawer b').count(),0);
    check('QA: Native click opens real detail API for the exact generated UUID and retains literal name',{independent_additional:true});
    assert.equal((await context.request.delete(base+'/api/clientes/'+stored[0].id_cliente,{headers})).status(),200);
    await page.evaluate(()=>abrirDrawer('sub-inactivas'));
    assert.ok(!(await page.locator('#drawer-body .drawer-client-card').evaluateAll(cards=>cards.map(card=>card.dataset.clienteId))).includes(stored[0].id_cliente));
    check('QA: Real soft delete removes that client from the refreshed drawer',{independent_additional:true});
    assert.deepEqual(report.pageErrors,[]);
    check('No JavaScript page errors');
    await context.close();
  } finally {await browser.close();}
  report.total=report.results.length;
  report.passed=report.results.filter(row=>row.passed).length;
  report.completed=true;
  fs.writeFileSync(path.join(out,'dashboard-drawer-security-after.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({total:report.total,passed:report.passed,results:report.results}));
})().catch(error=>{
  report.completed=false;
  report.results.push({case:'Browser regression assertion',passed:false,error:error.message});
  report.total=report.results.length;
  report.passed=report.results.filter(row=>row.passed).length;
  fs.writeFileSync(path.join(out,'dashboard-drawer-security-after.json'),JSON.stringify(report,null,2)+'\n');
  console.error(JSON.stringify({total:report.total,passed:report.passed,results:report.results}));
  process.exitCode=1;
});
