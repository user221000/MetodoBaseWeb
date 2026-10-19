/* Independent UI contract review. Only a loopback synthetic app is allowed. */
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8766';
if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base)) throw Error('Expected an isolated loopback app');
const out = path.resolve(__dirname, '../../docs/implementation/20261018-evolution/evidence/ux');

(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true});
  const report = {scope: 'Synthetic browser auth plus malformed subscription transport; no payment/provider', cases: []};
  try {
    const context = await browser.newContext({viewport: {width: 390, height: 844}});
    await context.route('**/*', route => route.request().url().startsWith(base + '/') ? route.continue() : route.abort());
    const registration = await context.request.post(base + '/api/auth/registro', {data: {
      email: 'qa-contract-' + Date.now() + '@example.invalid', password: 'Synthetic-Contract-Password-2026!', nombre: 'Synthetic QA', tipo: 'usuario'
    }});
    assert.ok(registration.ok());
    const tokens = await registration.json();
    await context.addInitScript(tokens => {
      localStorage.setItem('mb_token', tokens.access_token);
      localStorage.setItem('mb_refresh_token', tokens.refresh_token || '');
      localStorage.setItem('mb_tipo', 'usuario');
    }, tokens);
    const page = await context.newPage();
    await page.route('**/api/usuario/billing-config', route => route.fulfill({json: {checkout_supported: true, mercadopago_configured: false}}));
    for (const [name, response] of [
      ['HTTP 200 HTML', {status: 200, contentType: 'text/html', body: '<html>Unexpected proxy response</html>'}],
      ['HTTP 200 empty object', {status: 200, json: {}}]
    ]) {
      await page.route('**/api/usuario/suscripcion', route => route.fulfill(response));
      await page.goto(base + '/mi-suscripcion');
      await page.waitForFunction(() => !document.querySelector('#subscription-feedback').hidden || document.querySelector('#sub-plan-name').textContent === 'Starter');
      const state = await page.evaluate(() => ({plan: document.querySelector('#sub-plan-name').textContent,
        feedback: document.querySelector('#subscription-feedback').textContent,
        errorVisible: !document.querySelector('#subscription-feedback').hidden,
        disabled: document.querySelector('#btn-pro').disabled}));
      report.cases.push({name, ...state});
      assert.equal(state.errorVisible, true, name + ': protocol error must be visible');
      assert.equal(state.plan, 'Por confirmar', name + ': response cannot fabricate Starter');
      assert.equal(state.disabled, true, name + ': do not start checkout from unknown state');
      await page.unroute('**/api/usuario/suscripcion');
    }
    console.log(JSON.stringify(report));
  } finally {
    fs.mkdirSync(out, {recursive: true});
    fs.writeFileSync(path.join(out, 'subscription-contract-review.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
