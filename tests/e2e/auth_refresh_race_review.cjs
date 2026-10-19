/* Independent HTTP-client state-machine probe. All transports are in memory. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
}
function environment(fetch) {
  const values = new Map([['mb_token', 'synthetic-old-access'], ['mb_refresh_token', 'synthetic-old-refresh']]);
  const context = vm.createContext({
    localStorage: {getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key)},
    fetch, FormData, Blob, File, URL, Response, setTimeout, clearTimeout,
    window: {location: {href: ''}},
  });
  const source = fs.readFileSync(path.join(__dirname, '../../web/static/js/api.js'), 'utf8');
  vm.runInContext(source + '\nglobalThis.reviewApi = Api;', context);
  function switchAccount() {
    values.set('mb_token', 'synthetic-new-access');
    values.set('mb_refresh_token', 'synthetic-new-refresh');
  }
  return {api: context.reviewApi, values, switchAccount};
}

async function old401CannotResendUnderNewAccount() {
  const started = deferred(), release = deferred(), requests = [];
  const fixture = environment(async (url, options) => {
    requests.push({url, method: options.method, auth: options.headers.Authorization, body: options.body});
    if (url === '/api/auth/refresh') return Response.json({token: 'synthetic-refreshed-new-access', refresh_token: 'synthetic-refreshed-new-refresh'});
    if (requests.length === 1) { started.resolve(); await release.promise; return Response.json({}, {status: 401}); }
    return Response.json({success: true});
  });
  const operation = fixture.api.clientes.actualizar('old-account-client', {nombre: 'Synthetic previous account data'}).catch(() => null);
  await started.promise;
  fixture.switchAccount(); release.resolve(); await operation;
  assert.equal(requests.filter(value => value.url.startsWith('/api/clientes/')).length, 1,
    'An old request must not be repeated with credentials of the new account');
  assert.equal(requests.filter(value => value.url === '/api/auth/refresh').length, 0,
    'An old401 must not start refreshing a newly selected account');
  assert.equal(fixture.values.get('mb_token'), 'synthetic-new-access');
}

async function lateRefreshCannotReplaceNewAccount() {
  const started = deferred(), release = deferred(), requests = [];
  const fixture = environment(async (url, options) => {
    requests.push({url, method: options.method, auth: options.headers.Authorization});
    if (url === '/api/auth/refresh') {
      started.resolve(); await release.promise;
      return Response.json({token: 'synthetic-refreshed-old-access', refresh_token: 'synthetic-refreshed-old-refresh'});
    }
    if (requests.length === 1) return Response.json({}, {status: 401});
    return Response.json({success: true});
  });
  const operation = fixture.api.clientes.actualizar('old-account-client', {nombre: 'Synthetic previous account data'}).catch(() => null);
  await started.promise;
  fixture.switchAccount(); release.resolve(); await operation;
  assert.equal(fixture.values.get('mb_token'), 'synthetic-new-access', 'A late refresh must preserve the newly selected account');
  assert.equal(fixture.values.get('mb_refresh_token'), 'synthetic-new-refresh');
  assert.equal(requests.filter(value => value.url.startsWith('/api/clientes/')).length, 1);
}

(async () => {
  const results = await Promise.allSettled([old401CannotResendUnderNewAccount(), lateRefreshCannotReplaceNewAccount()]);
  const report = results.map((result, index) => ({case: index + 1, passed: result.status === 'fulfilled',
    ...(result.status === 'rejected' ? {reason: result.reason.message} : {})}));
  console.log(JSON.stringify({scope: 'In-memory transport and token state only; no browser/server/provider claim', report}, null, 2));
  if (results.some(result => result.status === 'rejected')) process.exitCode = 1;
})().catch(error => { console.error(error.message); process.exitCode = 1; });
