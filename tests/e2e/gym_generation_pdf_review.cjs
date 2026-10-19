/* Independent exact-document proof: two real plans for the same client. */
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8769';
if (!/^http:\/\/(127\.0\.0\.1|localhost):8769$/.test(base)) throw Error('Own synthetic Clinic fixture8769 only');
const output = path.resolve(__dirname, '../../docs/implementation/20261018-evolution/evidence/ux/b2b-generation-pdf-old-new-independent.json');
const report = { scope: 'Own persisted Clinic seed; real auth/API/quota/worker/PDF for two plans of the same client; no transport/auth mocks', checks: [], pageErrors: [] };
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 320, height: 900 }, acceptDownloads: true });
    await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    const login = await context.request.post(base + '/api/auth/login', { data: { email: 'pdf-review-owner@example.invalid', password: 'Synthetic-PDF-Review-Password-2026!' } });
    assert.equal(login.status(), 200);
    const { token } = await login.json();
    assert.ok(token);
    const headers = { Authorization: 'Bearer ' + token };
    async function generate(number, type) {
      const response = await context.request.post(base + '/api/generar-plan', { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { id_cliente: 'synthetic-pdf-review-client', plan_numero: number, tipo_plan: type }, timeout: 60000 });
      assert.equal(response.status(), 200);
      const result = await response.json();
      assert.equal(result.success, true);
      return result.plan_id;
    }
    const oldId = await generate(1, 'menu_fijo');
    const newId = await generate(2, 'opciones');
    assert.notEqual(oldId, newId);
    async function pdf(id) {
      const response = await context.request.get(base + '/api/planes/' + id + '/pdf', { headers });
      assert.equal(response.status(), 200);
      assert.equal(response.headers()['referrer-policy'], 'no-referrer');
      assert.match(response.headers()['cache-control'], /no-store/);
      const body = await response.body();
      assert.equal(body.subarray(0, 5).toString(), '%PDF-');
      return body;
    }
    const oldBody = await pdf(oldId), newBody = await pdf(newId);
    assert.notEqual(hash(oldBody), hash(newBody));
    const latest = await context.request.get(base + '/api/descargar-pdf/synthetic-pdf-review-client', { headers });
    assert.equal(latest.status(), 200);
    assert.equal(hash(await latest.body()), hash(newBody), 'The legacy latest endpoint is a distinct, newer document');
    const historyResponse = await context.request.get(base + '/api/planes', { headers });
    assert.equal(historyResponse.status(), 200);
    const history = await historyResponse.json();
    assert.equal(history.total, 2);
    assert.ok(history.planes.every(plan => plan.id_cliente === 'synthetic-pdf-review-client'));
    const oldIndex = history.planes.findIndex(plan => plan.id === oldId);
    assert.ok(oldIndex >= 0);
    const page = await context.newPage();
    page.on('pageerror', error => report.pageErrors.push(error.message));
    const downloadRequests = [];
    page.on('request', request => {
      if (request.url().includes('/pdf') || request.url().includes('/descargar-pdf/')) downloadRequests.push({ path: new URL(request.url()).pathname, authorized: request.headers().authorization === 'Bearer ' + token });
    });
    await page.goto(base + '/login-gym');
    await page.evaluate(value => localStorage.setItem('mb_token', value), token);
    await page.goto(base + '/planes');
    await page.waitForFunction(() => document.querySelectorAll('#planes-tbody button').length === 2);
    const downloadStarted = page.waitForEvent('download');
    await page.locator('#planes-tbody tr').nth(oldIndex).locator('button').focus();
    await page.keyboard.press('Enter');
    const download = await downloadStarted;
    const downloaded = fs.readFileSync(await download.path());
    assert.equal(hash(downloaded), hash(oldBody));
    assert.notEqual(hash(downloaded), hash(newBody));
    assert.deepEqual(downloadRequests, [{ path: '/api/planes/' + oldId + '/pdf', authorized: true }]);
    assert.deepEqual(report.pageErrors, []);
    report.old_plan_id = oldId;
    report.new_plan_id = newId;
    report.old_pdf_sha256 = hash(oldBody);
    report.new_pdf_sha256 = hash(newBody);
    report.downloaded_pdf_sha256 = hash(downloaded);
    report.download_requests = downloadRequests;
    report.history_total = history.total;
    report.checks.push('Two actual same-client plans are persisted by real workers; the compatibility latest route returns the second PDF');
    report.checks.push('At320px Enter on the older history row downloads the first PDF by exact plan ID and Bearer, with no latest fallback');
  } finally {
    await browser.close();
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
  }
  console.log(JSON.stringify({ checks: report.checks.length, pageErrors: report.pageErrors.length }));
})().catch(error => { console.error(error); process.exitCode = 1; });
