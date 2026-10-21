/* Actual RAM API and routine transport. No HTTP/backend/browser claim. */
'use strict';
const assert = require('node:assert/strict');
const {world} = require('./browser_harness31.cjs');
const panel = require('../../web/static/js/rutinas.js');
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise, resolve}; };
(async () => {
  // Refresh deliberately retains the revision. An old rejected credential must
  // therefore be compared as well as the account/session snapshot.
  const w = world(), tab = w.tab();
  await tab.api.session.ready;
  const before = tab.api.session.capture(), oldAccess = tab.api.getToken();
  const headers = deferred(), started = deferred();
  let bodies = 0;
  const pending = panel.readCatalog(tab.api, 'gym', async () => {
    started.resolve(); await headers.promise;
    return {status: 401, ok: false, text: async () => { bodies++; return '{}'; }};
  });
  const drained = Promise.allSettled([pending]);
  await started.promise;
  let requests = 0;
  tab.hook(call => call.path === '/api/auth/me' ? Response.json({}, {status: requests++ === 0 ? 401 : 200}) : null);
  await tab.api.auth.me();
  const freshAccess = tab.api.getToken();
  assert.notEqual(freshAccess, oldAccess);
  assert.equal(tab.api.session.capture().revision, before.revision);
  headers.resolve();
  const [result] = await drained;
  assert.equal(result.status, 'rejected');
  assert.equal(result.reason.code, 'session_changed');
  assert.equal(tab.api.getToken(), freshAccess);
  assert.equal(bodies, 0);

  const other = w.tab(); await other.api.session.ready;
  const otherAccess = other.api.getToken(), epoch = w.shared.get('mb_session_epoch');
  await assert.rejects(panel.readCatalog(tab.api, 'gym', async () => {
    return {status: 401, ok: false, text: async () => { throw Error('401 body must not be read'); }};
  }), {code: 'session_changed'});
  assert.equal(tab.api.getToken(), '');
  assert.equal(other.api.getToken(), otherAccess);
  assert.equal(w.shared.get('mb_session_epoch'), epoch);
  process.stdout.write(JSON.stringify({passed: 2, total: 2, scope: 'same-revision rotated access and local-only 401 retirement'}) + '\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
