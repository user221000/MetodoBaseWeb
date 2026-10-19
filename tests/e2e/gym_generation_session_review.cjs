/* Independent review: real persisted create, response held across account switch. */
const { chromium } = require('playwright-core');
const { AxeBuilder } = require('@axe-core/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8769';
if (!/^http:\/\/(127\.0\.0\.1|localhost):8769$/.test(base)) throw Error('Synthetic fixture8769 only');
const batch = process.env.METODOBASE_EVIDENCE_BATCH || 'before';
if (!/^[a-z0-9-]+$/.test(batch)) throw Error('Invalid evidence batch');
const out = path.resolve(__dirname, '../../docs/implementation/20261018-evolution/evidence/ux/b2b-generation-session-review-' + batch + '.json');
const report = { scope: 'Real isolated auth/API creation; only delivery of the real POST response is held', checks: [], pageErrors: [] };
(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 320, height: 900 } });
    context.setDefaultTimeout(10000);
    await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    async function login(suffix) {
      const response = await context.request.post(base + '/api/auth/login', { data: { email: 'generation-' + suffix + '@example.invalid', password: 'Synthetic-Generation-Password-2026!' } });
      assert.equal(response.status(), 200);
      return response.json();
    }
    const owner = await login('owner'), other = await login('other');
    const page = await context.newPage();
    page.on('pageerror', error => report.pageErrors.push(error.message));
    await page.goto(base + '/login-gym');
    await page.evaluate(token => localStorage.setItem('mb_token', token), owner.token);
    await page.goto(base + '/generar-plan');
    await page.locator('#s1-btn-nuevo').click();
    await page.locator('#n-nombre').fill('Synthetic Stale Identity Canary');
    await page.locator('#n-edad').fill('30');
    await page.locator('#n-sexo').selectOption('M');
    await page.locator('#n-peso').fill('75');
    await page.locator('#n-estatura').fill('175');
    await page.locator('#n-objetivo').selectOption('mantenimiento');
    await page.locator('#n-nivel').selectOption('moderada');
    const accessibility = await new AxeBuilder({ page }).include('#modal-nuevo-cliente').withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    report.modal_axe = accessibility.violations.map(issue => ({ id: issue.id, nodes: issue.nodes.map(node => node.target) }));
    report.modal_overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    let release;
    let created;
    const held = new Promise(resolve => created = resolve);
    await page.route('**/api/clientes', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      const response = await route.fetch();
      report.create_status = response.status();
      assert.equal(response.status(), 201);
      report.persisted_before_switch = true;
      created();
      await new Promise(resolve => release = resolve);
      return route.fulfill({ response });
    });
    try {
      await page.locator('#s1-registrar').click({ trial: true, timeout: 1500 });
      report.register_click_actionable = true;
    } catch {
      report.register_click_actionable = false;
    }
    await page.locator('#s1-registrar').focus();
    await page.keyboard.press('Enter');
    await Promise.race([held, new Promise((_, reject) => setTimeout(() => reject(Error('Creation did not reach the held real response')), 15000))]);
    await page.evaluate(token => {
      localStorage.setItem('mb_token', token);
      dispatchEvent(new StorageEvent('storage', { key: 'mb_token' }));
    }, other.token);
    release();
    await page.waitForFunction(() => document.querySelector('#s2-nombre').textContent || document.querySelector('#s3-recovery-message').textContent.includes('sesión cambió'));
    await page.waitForTimeout(700);
    report.selected_name_after_switch = await page.locator('#s2-nombre').textContent();
    report.step_two_active_after_switch = await page.locator('#step-2').evaluate(element => element.classList.contains('active'));
    report.modal_active_after_switch = await page.locator('#modal-nuevo-cliente').evaluate(element => element.classList.contains('active'));
    report.modal_name_after_switch = await page.locator('#n-nombre').inputValue();
    report.old_operation_retry_disabled = await page.locator('#s3-retry').isDisabled();
    assert.equal(report.selected_name_after_switch, '', 'A late response for the previous identity must not repopulate the selected client');
    assert.equal(report.step_two_active_after_switch, false);
    assert.equal(report.modal_active_after_switch, false, 'Identity invalidation must close the previous client form');
    assert.equal(report.modal_name_after_switch, '');
    assert.equal(report.register_click_actionable, true, 'The modal backdrop must allow the visible Register button to be clicked');
    assert.deepEqual(report.modal_axe, []);
    assert.equal(report.modal_overflow, false);
    assert.deepEqual(report.pageErrors, []);
    report.checks.push('Account switch discards a real delayed creation response, closes and clears the old identity form');
    await page.unroute('**/api/clientes');
    await page.goto(base + '/generar-plan');
    await page.locator('#s1-btn-nuevo').click();
    await page.locator('#n-nombre').fill('Synthetic Current Identity');
    await page.locator('#n-edad').fill('30');
    await page.locator('#n-sexo').selectOption('M');
    await page.locator('#n-peso').fill('75');
    await page.locator('#n-estatura').fill('175');
    await page.locator('#n-objetivo').selectOption('mantenimiento');
    await page.locator('#n-nivel').selectOption('moderada');
    const currentCreated = page.waitForResponse(response => response.request().method() === 'POST' && response.url() === base + '/api/clientes');
    await page.locator('#s1-registrar').click();
    const currentResponse = await currentCreated;
    assert.equal(currentResponse.status(), 201);
    const currentBody = await currentResponse.json();
    await page.locator('#step-2.active').waitFor();
    assert.equal(await page.locator('#s2-nombre').textContent(), 'Synthetic Current Identity');
    assert.equal(await page.locator('#modal-nuevo-cliente').evaluate(element => element.classList.contains('active')), false);
    assert.equal((await context.request.get(base + '/api/clientes/' + currentBody.id_cliente, { headers: { Authorization: 'Bearer ' + other.token } })).status(), 200);
    assert.equal((await context.request.get(base + '/api/clientes/' + currentBody.id_cliente, { headers: { Authorization: 'Bearer ' + owner.token } })).status(), 404);
    report.checks.push('The current identity can then create and select its own real client by mouse; the prior owner cannot read it');
  } finally {
    await browser.close();
    fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
