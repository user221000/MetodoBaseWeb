/* Real auth guard and RAM API in VM realms; no native-browser/layout claim. */
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {world} = require('./browser_harness31.cjs');
const guard = fs.readFileSync(process.env.ROUTINES_AUTH_GUARD_SOURCE || 'web/static/js/auth-guard.js', 'utf8');
const rows = [];
async function test(name, run) {
  try { await run(); rows.push({case: name, passed: true}); }
  catch (error) { rows.push({case: name, passed: false, error: error.message}); }
}
async function guarded(path, identity = null) {
  const redirects = [];
  const document = {
    readyState: 'complete', body: {}, querySelectorAll: () => [],
    getElementById: () => null, querySelector: () => null,
  };
  const sandbox = {
    document, location: {pathname: path, replace: to => redirects.push(to)},
    Api: {
      session: {ready: Promise.resolve(), capture: () => ({}), check() {}},
      getToken: () => identity ? 'synthetic-access' : '',
      auth: {me: async () => identity},
    },
    MutationObserver: class { observe() {} }, addEventListener() {},
  };
  sandbox.window = sandbox;
  vm.runInNewContext(guard, sandbox);
  await sandbox.SessionIdentity.ready;
  return redirects;
}
(async () => {
  for (const path of ['/mis-rutinas', '/mis-rutinas/']) {
    await test('Anonymous personal routine shell selects personal login: ' + path, async () => {
      assert.deepEqual(await guarded(path), ['/login-usuario']);
    });
    await test('Owner is returned to gym from personal routine shell: ' + path, async () => {
      assert.deepEqual(await guarded(path, {tipo: 'gym', role: 'owner'}), ['/dashboard']);
    });
  }
  for (const path of ['/rutinas', '/rutinas/']) {
    await test('Anonymous gym routine shell selects gym login: ' + path, async () => {
      assert.deepEqual(await guarded(path), ['/login-gym']);
    });
    await test('Personal account is returned to its portal from gym routine shell: ' + path, async () => {
      assert.deepEqual(await guarded(path, {tipo: 'usuario', role: 'member'}), ['/mi-plan']);
    });
  }
  for (const [path, me] of [
    ['/rutinas', {tipo: 'gym', role: 'owner'}],
    ['/rutinas/', {tipo: 'usuario', role: 'viewer', team_gym_id: 'synthetic-gym'}],
    ['/mis-rutinas', {tipo: 'usuario', role: 'member'}],
    ['/mis-rutinas/', {tipo: 'usuario', role: 'viewer', team_gym_id: 'synthetic-gym'}],
  ]) await test('Valid context keeps routine navigation: ' + path + ' ' + me.role, async () => {
    assert.deepEqual(await guarded(path, me), []);
  });
  for (const path of ['/mis-rutinas', '/mis-rutinas/', '/rutinas', '/rutinas/']) {
    await test('Actual API expiration chooses context login: ' + path, async () => {
      const w = world(), tab = w.tab();
      tab.sandbox.location.pathname = path;
      await tab.api.session.ready;
      tab.hook(call => {
        if (call.path === '/api/auth/refresh') return Response.json({detail: {code: 'browser_session_unavailable'}}, {status: 401});
        return Response.json({detail: 'Expired'}, {status: 401});
      });
      await assert.rejects(tab.api.auth.me(), {code: 'session_expired'});
      assert.equal(tab.sandbox.location.href, path.startsWith('/mis-rutinas') ? '/login-usuario' : '/login-gym');
      assert.equal(tab.api.getToken(), '');
    });
  }
  const passed = rows.filter(row => row.passed).length;
  process.stdout.write(JSON.stringify({scope: 'VM auth navigation and actual RAM API expiration', passed, total: rows.length, rows}, null, 2) + '\n');
  process.exitCode = passed === rows.length ? 0 : 1;
})();
