/* Focused real mounted removal canary, using only the own R24 fixture. */
const {chromium}=require('playwright-core'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const privateRoot=process.env.R24_PRIVATE,meta=JSON.parse(fs.readFileSync(path.join(privateRoot,'fixture.private.json'),'utf8'));
if(meta.origin!=='http://127.0.0.1:8800')throw Error('Own origin only');
const output=process.env.R24_REMOVE_OUTPUT;if(!output||fs.existsSync(output))throw Error('New output file required');
(async()=>{let browser;const proof={scope:'Own real auth/HTTP/diary and mounted personal removal; existing consumed publication row required',passed:false};try{
 browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});const context=await browser.newContext();await context.route('**/*',route=>new URL(route.request().url()).origin===meta.origin?route.continue():route.abort());const page=await context.newPage();page.on('dialog',dialog=>dialog.accept());
 await page.goto(meta.origin+'/login-usuario');await page.locator('#loginForm input[name=email]').fill('r24-person@example.invalid');await page.locator('#loginForm input[name=password]').fill(meta.password);await page.locator('#loginForm button[type=submit]').click();await page.waitForURL('**/mi-plan');await page.locator('#loading-plan').waitFor({state:'hidden'});await page.waitForFunction(()=>document.getElementById('diary-status').textContent.includes('Datos consultados'));
 let writes=0;page.on('request',request=>{if(request.method()==='PATCH'&&request.url().includes('/diario/'))writes++;});
 const row=page.locator('[data-diary-meal="cena"]');assert.equal(await row.count(),1);await row.locator('button[data-remove-consumed]').click();await page.waitForTimeout(250);
 proof.after=await page.evaluate(()=>({status:document.getElementById('diary-status').textContent,busy:document.getElementById('diary-section').getAttribute('aria-busy'),rowStillPresent:!!document.querySelector('[data-diary-meal="cena"]')}));proof.patchRequests=writes;
 assert.equal(writes,1,'Explicit own removal must dispatch one PATCH');await page.waitForFunction(()=>document.getElementById('diary-status').textContent==='Cambio confirmado por el servidor.');assert.equal(await row.count(),0);proof.passed=true;
 }catch(error){proof.error=error.message;process.exitCode=1;}finally{if(browser)await browser.close();fs.writeFileSync(output,JSON.stringify(proof,null,2));}console.log(JSON.stringify({passed:proof.passed,patchRequests:proof.patchRequests}));})();
