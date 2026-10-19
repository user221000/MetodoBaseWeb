/* Real browser/auth/API with one explicitly injected native Storage write failure. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright-core');

const base = process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8772';
if (!/^http:\/\/(127\.0\.0\.1|localhost):8772$/.test(base)) throw Error('Own synthetic fixture 8772 only');
const batch = process.env.METODOBASE_EVIDENCE_BATCH || new Date().toISOString().replace(/[^0-9]/g, '');
const output = path.resolve(__dirname, '../../docs/implementation/20261018-evolution/evidence/ux',
  'auth-refresh-storage-browser-' + batch);
fs.mkdirSync(output, {recursive: true});
const report = {
  scope: 'Real browser and synthetic auth/API; only Storage.setItem(refreshB) throws an explicit DOMException after native accessB writes. Fetch is observed and forwarded unchanged. No native quota exhaustion, reload durability or cross-tab atomicity claim.',
  checks: [], pageErrors: [],
};

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
  });
  try {
    const context = await browser.newContext();
    await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    async function login(suffix) {
      const response = await context.request.post(base + '/api/auth/login', {data: {
        email: 'branding-' + suffix + '@example.invalid', password: 'Synthetic-Branding-Password-2026!',
      }});
      assert.equal(response.status(), 200);
      return response.json();
    }
    const owner = await login('owner');
    const other = await login('other');
    const originalClientResponse = await context.request.get(base + '/api/clientes/synthetic-branding-client', {
      headers: {Authorization: 'Bearer ' + owner.token},
    });
    assert.equal(originalClientResponse.status(), 200);
    const originalClient = await originalClientResponse.json();
    const page = await context.newPage();
    const apiRequests = [];
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('request', request => {
      if (request.url().startsWith(base + '/api/')) apiRequests.push({
        path: new URL(request.url()).pathname, method: request.method(),
        bearerAttached: Boolean(request.headers().authorization),
      });
    });
    await page.goto(base + '/login-gym');
    await page.addScriptTag({url: base + '/static/js/api.js'});
    const injected = await page.evaluate(async ({owner, other}) => {
      const originalFetch = window.fetch;
      window.__qaNativeFetch = originalFetch;
      window.__qaFetchCalls = 0;
      window.fetch = function (...args) {
        window.__qaFetchCalls += 1;
        return Reflect.apply(originalFetch, this, args);
      };
      Api.saveTokens(owner);
      const me = await Api.auth.me();
      const nativeSet = Storage.prototype.setItem;
      let observedAccessBeforeFault = false;
      let captured = null;
      Storage.prototype.setItem = function (key, value) {
        if (this === localStorage && key === 'mb_refresh_token' && value === other.refresh_token) {
          observedAccessBeforeFault = localStorage.getItem('mb_token') === other.token
            && localStorage.getItem('mb_refresh_token') === owner.refresh_token;
          throw new DOMException('Synthetic explicit refresh-key write failure', 'QuotaExceededError');
        }
        return Reflect.apply(nativeSet, this, [key, value]);
      };
      try { Api.saveTokens(other); }
      catch (error) { captured = {code: error.code, name: error.name, causeName: error.cause?.name}; }
      finally { Storage.prototype.setItem = nativeSet; }
      return {
        initialSubject: me.id, captured, observedAccessBeforeFault,
        nativeSetterRestored: Storage.prototype.setItem === nativeSet,
        partialPairPreserved: localStorage.getItem('mb_token') === other.token
          && localStorage.getItem('mb_refresh_token') === owner.refresh_token,
      };
    }, {owner, other});
    assert.equal(injected.initialSubject, 'synthetic-branding-owner');
    assert.deepEqual(injected.captured, {
      code: 'session_storage_error', name: 'QuotaExceededError', causeName: 'QuotaExceededError',
    });
    assert.ok(injected.observedAccessBeforeFault && injected.partialPairPreserved && injected.nativeSetterRestored);
    report.checks.push('Native accessB is written before the named refreshB DOMException; the native setter is restored and the partial B-access/A-refresh pair is retained');

    const wireBefore = apiRequests.length;
    const blocked = await page.evaluate(async ({owner, other}) => {
      const before = window.__qaFetchCalls;
      const operations = [
        () => Api.clientes.actualizar('synthetic-branding-client', {nombre: 'Synthetic forbidden B DTO'}),
        () => Api.clientes.obtener('synthetic-branding-client'),
        () => Api.auth.me(),
        () => Api.usuario.exportarDatos(),
        () => Api.auth.logout(),
      ];
      const results = await Promise.allSettled(operations.map(operation => Promise.resolve().then(operation)));
      return {
        rejectedCodes: results.map(result => result.status === 'rejected' ? result.reason.code : 'unexpected_success'),
        fetchCalls: window.__qaFetchCalls - before,
        pairUnchanged: localStorage.getItem('mb_token') === other.token
          && localStorage.getItem('mb_refresh_token') === owner.refresh_token,
      };
    }, {owner, other});
    assert.deepEqual(blocked.rejectedCodes, Array(5).fill('session_storage_error'));
    assert.equal(blocked.fetchCalls, 0);
    assert.equal(apiRequests.length, wireBefore);
    assert.ok(blocked.pairUnchanged);
    const unchanged = await context.request.get(base + '/api/clientes/synthetic-branding-client', {
      headers: {Authorization: 'Bearer ' + owner.token},
    });
    assert.equal(unchanged.status(), 200);
    assert.equal((await unchanged.json()).nombre, originalClient.nombre);
    report.blocked = {consumers: 5, fetchCalls: 0, wireRequests: 0, partialPairPreserved: true};
    report.checks.push('With the Storage fault removed, PUT/read/me/export/logout reject before fetch or refresh, retain the partial pair and leave the real persisted client unchanged');

    const recovery = await page.evaluate(async () => {
      Api.clearTokens();
      const cleared = localStorage.getItem('mb_token') === null && localStorage.getItem('mb_refresh_token') === null;
      const data = await Api.auth.loginGym('branding-other@example.invalid', 'Synthetic-Branding-Password-2026!');
      const me = await Api.auth.me();
      const exported = await Api.usuario.exportarDatos();
      const pairMatchesLogin = localStorage.getItem('mb_token') === data.token
        && localStorage.getItem('mb_refresh_token') === data.refresh_token;
      window.fetch = window.__qaNativeFetch;
      delete window.__qaNativeFetch;
      delete window.__qaFetchCalls;
      return {cleared, pairMatchesLogin, subject: me.id, exportSubject: exported.account.id};
    });
    assert.deepEqual(recovery, {cleared: true, pairMatchesLogin: true,
      subject: 'synthetic-branding-other', exportSubject: 'synthetic-branding-other'});
    assert.equal(apiRequests.filter(request => request.path === '/api/auth/refresh').length, 0);
    const loginRequest = apiRequests.find(request => request.path === '/api/auth/login');
    assert.ok(loginRequest && !loginRequest.bearerAttached);
    report.recovery = {completeClear: true, realLogin: true, consistentPair: true, authenticatedScopeMatches: true};
    report.checks.push('A complete explicit clear followed by real public login restores a consistent pair and authenticated me/export in the intended account, without refresh');
    assert.deepEqual(report.pageErrors, []);
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  }
  console.log(JSON.stringify({checks: report.checks.length, pageErrors: report.pageErrors.length, evidence: output}));
})().catch(error => { console.error(error.message); process.exitCode = 1; });
