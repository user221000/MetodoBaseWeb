/* Actual first-party form/auth/DB. Mail acceptance is synthetic, not delivery. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright-core');
const base = 'http://127.0.0.1:8784';
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const context = await browser.newContext({viewport:{width:390,height:844}});
  const errors = [],requests = [],violations = [];
  await context.route('**/*',route => route.request().url().startsWith(base) ? route.continue() : route.abort());
  const page = await context.newPage();
  page.on('pageerror',error => errors.push(error.name));
  page.on('request',request => requests.push({url:request.url(),authorization:Boolean(request.headers().authorization)}));
  await page.addInitScript(() => document.addEventListener('securitypolicyviolation',event => window.__recoveryCspViolation=true));
  const response = await page.goto(base+'/auth/reset-password#token='+'b'.repeat(43));
  assert.equal(response.status(),200);
  assert.equal(response.headers()['referrer-policy'],'no-referrer');
  assert.equal(response.headers()['cache-control'],'no-store');
  assert(!response.headers()['content-security-policy'].includes('https:'));
  await page.locator('#recovery-confirm').waitFor({state:'visible'});
  assert.equal(page.url(),base+'/auth/reset-password');
  assert.equal(await page.evaluate(() => localStorage.length+sessionStorage.length),0);
  await page.locator('#recovery-password').fill('SyntheticNewPassword456');
  await page.locator('#recovery-confirmation').fill('SyntheticNewPassword456');
  await page.locator('#recovery-confirm button').click();
  await page.waitForFunction(() => document.querySelector('#recovery-status').textContent.includes('actualizada'));
  assert.equal(await page.locator('#recovery-password').inputValue(),'');
  assert.equal(await page.locator('#recovery-confirmation').inputValue(),'');
  assert.equal(await page.evaluate(() => localStorage.length+sessionStorage.length),0);
  assert.equal((await context.request.get(base+'/api/auth/me')).status(),401);
  assert.equal((await context.request.post(base+'/api/auth/login',{data:{email:'recovery-browser@example.invalid',password:'SyntheticOldPassword123'}})).status(),401);
  const login = await context.request.post(base+'/api/auth/login',{data:{email:'recovery-browser@example.invalid',password:'SyntheticNewPassword456'}});
  assert.equal(login.status(),200);
  await page.goto(base+'/auth/reset-password');
  await page.locator('#recovery-request').waitFor({state:'visible'});
  await page.locator('#recovery-email').fill('unknown-browser@example.invalid');
  await page.locator('#recovery-request button').click();
  await page.waitForFunction(() => document.querySelector('#recovery-status').textContent.includes('Si la cuenta'));
  assert.equal(await page.evaluate(() => Boolean(window.__recoveryCspViolation)),false);
  for(const request of requests) {
    assert(!request.url.includes('#') && !request.url.includes('token='));
    assert.equal(request.authorization,false);
  }
  assert.deepEqual(errors,[]);
  const report={scope:'Own temporary SQLite, actual form/auth/DB, synthetic mail acceptance; no delivery claim',
    checks:['fragment removed before submit','first-party JS/CSS under closed CSP','no browser token storage',
      'password changed through real API','old credential rejected and new credential works','no automatic login',
      'request acknowledgement does not enumerate','no bearer in request URLs or Authorization','no CSP or JS failure'],
    requests:requests.length};
  const output=path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/backend-recovery-browser.json');
  fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({checks:report.checks.length,passed:true}));
  await browser.close();
})().catch(error => {console.error(error.name+': '+error.message);process.exit(1);});
