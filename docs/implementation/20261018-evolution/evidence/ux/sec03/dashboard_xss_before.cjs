'use strict';
const {chromium}=require('F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules/playwright-core');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base='http://127.0.0.1:8774',out=__dirname;
const report={scope:'Own detached 2f8b7f9 application, real signed auth + CRUD + SQLite + browser/CSP; error renderer uses explicitly injected Error boundary only; no external network',checks:[],payloads:[],externalRequestsBlocked:0,pageErrors:[],cspInlineBlocks:0};
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1280,height:900},serviceWorkers:'block'});
  await context.route('**/*',route=>{if(route.request().url().startsWith(base+'/'))return route.continue();report.externalRequestsBlocked++;return route.abort();});
  const password='Synthetic-Drawer-Only-2026!';
  async function login(suffix){const res=await context.request.post(base+'/api/auth/login',{data:{email:'drawer-'+suffix+'@example.invalid',password}});assert.equal(res.status(),200);return res.json();}
  const owner=await login('owner'),other=await login('other');
  const headers={Authorization:'Bearer '+owner.token};
  const names=['Synthetic <span data-sec03-name=1>Marker</span>','Synthetic <svg onload=&#116;&#111;&#112;[8417]=1></svg>'];
  const stored=[];
  for(const name of names){
   const response=await context.request.post(base+'/api/clientes',{headers,data:{nombre:name,edad:30,sexo:'M',peso_kg:75,estatura_cm:175,nivel_actividad:'moderada',objetivo:'mantenimiento'}});
   assert.equal(response.status(),201,'Markup fixture must be accepted by actual CRUD');
   const created=await response.json();
   const loaded=await context.request.get(base+'/api/clientes/'+created.id_cliente,{headers});assert.equal(loaded.status(),200);
   const client=await loaded.json();stored.push(client);
   report.payloads.push({input_name:name,stored_name:client.nombre,created_status:response.status(),reload_status:loaded.status(),generated_id_is_uuid:/^[0-9a-f-]{36}$/.test(client.id_cliente),contains_markup_after_roundtrip:client.nombre.includes('<')});
  }
  const forbidden=await context.request.get(base+'/api/clientes/'+stored[0].id_cliente,{headers:{Authorization:'Bearer '+other.token}});
  assert.equal(forbidden.status(),404);
  const unauth=await context.request.get(base+'/api/clientes');assert.equal(unauth.status(),401);
  report.checks.push({case:'Real auth/CRUD scope controls',passed:true,anonymous_status:401,other_account_status:404});
  await context.addInitScript(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('mb_tipo','gym');},{token:owner.token,refresh_token:owner.refresh_token});
  const page=await context.newPage();
  page.on('pageerror',error=>report.pageErrors.push(error.name));
  page.on('console',message=>{if(/inline event handler.*Content Security Policy|Executing inline event handler/.test(message.text()))report.cspInlineBlocks++;});
  const documentResponse=await page.goto(base+'/dashboard');
  const csp=documentResponse.headers()['content-security-policy']||'';
  report.csp={present:!!csp,script_has_nonce:/script-src[^;]*'nonce-/.test(csp),script_allows_unsafe_inline:/script-src[^;]*'unsafe-inline'/.test(csp)};
  await page.waitForFunction(()=>typeof abrirDrawer==='function');
  await page.evaluate(()=>abrirDrawer('sub-inactivas'));
  await page.locator('#drawer-body [data-sec03-name]').waitFor();
  report.svgLoadProbe=await page.evaluate(async()=>{const svg=document.querySelector('#drawer-body .drawer-client-name svg');const result=new Promise(resolve=>{document.addEventListener('securitypolicyviolation',()=>resolve('csp_blocked'),{once:true});setTimeout(()=>resolve('no_violation_observed'),350);});svg.dispatchEvent(new Event('load'));return{synthetic_load_event:true,result:await result,marker:window[8417]===1};});
  report.storedHtml={marker_element_count:await page.locator('#drawer-body [data-sec03-name]').count(),svg_element_count:await page.locator('#drawer-body .drawer-client-name svg').count(),javascript_marker:await page.evaluate(()=>window[8417]===1),main_feed_marker_count:await page.locator('#recent-activity [data-sec03-name]').count()};
  assert.equal(report.storedHtml.marker_element_count,1);
  assert.equal(report.storedHtml.javascript_marker,false);
  assert.ok(report.cspInlineBlocks>0 || report.svgLoadProbe.result==='csp_blocked','Real CSP should block this inline SVG handler');
  report.checks.push({case:'Persisted name interpreted as HTML by drawer; simple JavaScript handler blocked by actual CSP',passed:true,security_boundary_passed:false});
  await page.screenshot({path:path.join(out,'dashboard-drawer-html-before.png'),fullPage:true});
  const captured=await page.evaluate(()=>({
   nameMarkup:document.querySelector('#drawer-body [data-sec03-name]')?.outerHTML,
   cardIdIsUuid:/^[0-9a-f-]{36}$/.test(document.querySelector('#drawer-body [data-cliente-id]')?.dataset.clienteId||''),
  }));
  report.dom=captured;
  await page.evaluate(async()=>{
   const original=Api.clientes.listar;
   Api.clientes.listar=()=>Promise.reject(new Error('<span data-sec03-error=1>Synthetic error marker</span>'));
   try{await abrirDrawer('sub-inactivas');}finally{Api.clientes.listar=original;}
  });
  const errorMarkers=await page.locator('#drawer-body [data-sec03-error]').count();
  report.errorBoundary={injected_error_message:'<span data-sec03-error=1>Synthetic error marker</span>',dom_marker_count:errorMarkers,backend_attacker_control_not_established:true};
  assert.equal(errorMarkers,1);
  report.checks.push({case:'Error-message sink interprets named synthetic Error as HTML',passed:true,security_boundary_passed:false,scope:'Runtime Error boundary override, not a proved backend reflection path'});
  await page.screenshot({path:path.join(out,'dashboard-drawer-error-before.png'),fullPage:true});
  await context.close();
 }finally{await browser.close();}
 report.completed=true;
 fs.writeFileSync(path.join(out,'dashboard-xss-before.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({completed:true,checks:report.checks,storedHtml:report.storedHtml,errorBoundary:report.errorBoundary,csp:report.csp,cspInlineBlocks:report.cspInlineBlocks,pageErrors:report.pageErrors},null,2));
})().catch(error=>{report.completed=false;report.failure=error.message;fs.writeFileSync(path.join(out,'dashboard-xss-before.json'),JSON.stringify(report,null,2)+'\n');console.error(error.name+': '+error.message);process.exitCode=1;});
