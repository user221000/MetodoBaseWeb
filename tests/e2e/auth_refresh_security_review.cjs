/* Independent SEC02 security probes. VM + in-memory transport only, no sockets. */
'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const sourceFile = process.argv[2] || path.join(__dirname, '../../web/static/js/api.js');
const source = fs.readFileSync(sourceFile, 'utf8');
const A = {token: 'synthetic-access-A', refresh: 'synthetic-refresh-A'};
const A1 = {token: 'synthetic-access-A1', refresh: 'synthetic-refresh-A1'};
const A2 = {token: 'synthetic-access-A2', refresh: 'synthetic-refresh-A2'};
const B = {token: 'synthetic-access-B', refresh: 'synthetic-refresh-B'};
const ok = value => Response.json(value);
const denied = () => Response.json({}, {status: 401});
const credentials = pair => ({token: pair.token, refresh_token: pair.refresh});
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
}
async function bounded(promise) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('Auth operation did not settle')), 1500);
    })]);
  } finally { clearTimeout(timer); }
}
async function rejected(promise, expected = 'session_changed') {
  const result = await bounded(Promise.allSettled([promise]));
  assert.equal(result[0].status, 'rejected');
  assert.equal(result[0].reason.code, expected);
}
function fixture(transport) {
  const values = new Map([['mb_token', A.token], ['mb_refresh_token', A.refresh]]);
  const listeners = new Map(), requests = [], downloads = [];
  let writeFailure = null;
  const storage = {
    getItem: key => values.get(key) || null,
    setItem(key, value) {
      if (writeFailure && writeFailure(key, value)) {
        const error = new Error('Synthetic storage quota'); error.name = 'QuotaExceededError'; throw error;
      }
      values.set(key, value);
    },
    removeItem: key => values.delete(key),
  };
  const window = {
    location: {href: ''},
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
    },
    removeEventListener: (name, callback) => listeners.get(name)?.delete(callback),
  };
  const context = vm.createContext({
    localStorage: storage, FormData, Blob, File, Response, URLSearchParams,
    fetch: async (url, options) => {
      requests.push({url, method: options.method, headers: {...options.headers}, body: options.body});
      return transport(url, options);
    },
    URL: {createObjectURL() { downloads.push('url'); return 'blob:synthetic'; }, revokeObjectURL() {}},
    setTimeout(callback, delay) { const timer = setTimeout(callback, delay); timer.unref(); return timer; },
    clearTimeout, window,
    document: {body: {appendChild() {}}, createElement: () => ({click() { downloads.push('click'); }, remove() {}})},
  });
  vm.runInContext(source + '\nglobalThis.securityApi = Api;', context, {filename: 'api.js'});
  return {
    api: context.securityApi, values, requests, downloads, window,
    current: () => ({token: values.get('mb_token') || '', refresh: values.get('mb_refresh_token') || ''}),
    replace(pair, notify = false) {
      values.set('mb_token', pair.token); values.set('mb_refresh_token', pair.refresh);
      if (notify) for (const callback of listeners.get('storage') || []) callback({key: 'mb_token'});
    },
    failWriteWhen(callback) { writeFailure = callback; },
  };
}
function preserved(env, pair) {
  assert.deepEqual(env.current(), pair);
  assert.equal(env.window.location.href, '');
}
const cases = [];
function test(name, body) { cases.push({name, body}); }

for (const field of ['token', 'refresh']) test('Only ' + field + ' changes: a delayed mutation cannot refresh or replay', async () => {
  const started = deferred(), release = deferred();
  const env = fixture(async () => { started.resolve(); await release.promise; return denied(); });
  const operation = env.api.clientes.actualizar('synthetic-A-client', {nombre: 'synthetic-A-data'});
  const settled = Promise.allSettled([operation]);
  await bounded(started.promise);
  const changed = {...A, [field]: B[field]}; env.replace(changed);
  release.resolve();
  const result = await bounded(settled);
  assert.equal(result[0].reason.code, 'session_changed');
  assert.equal(env.requests.length, 1); preserved(env, changed);
});

test('Helper ABA clear/save of the identical pair invalidates its older request', async () => {
  const started = deferred(), release = deferred();
  const env = fixture(async () => { started.resolve(); await release.promise; return ok({private: 'A'}); });
  const operation = env.api.usuario.exportarDatos();
  const settled = Promise.allSettled([operation]);
  await bounded(started.promise);
  env.api.clearTokens(); env.api.saveTokens(credentials(A)); release.resolve();
  const result = await bounded(settled);
  assert.equal(result[0].reason.code, 'session_changed'); preserved(env, A);
});

test('A mixed JSON/upload/export queue cannot retry any A payload under B credentials', async () => {
  const refreshStarted = deferred(), release = deferred();
  const env = fixture(async url => {
    if (url !== '/api/auth/refresh') return denied();
    refreshStarted.resolve(); await release.promise; return ok(credentials(A1));
  });
  const operations = [env.api.clientes.crear({nombre: 'synthetic-private-A'}),
    env.api.gym.uploadLogo(new File(['synthetic-A-image'], 'A.png', {type: 'image/png'})),
    env.api.usuario.exportarDatos()];
  const settled = Promise.allSettled(operations);
  await bounded(refreshStarted.promise); env.replace(B); release.resolve();
  const result = await bounded(settled);
  assert.ok(result.every(item => item.status === 'rejected' && item.reason.code === 'session_changed'));
  assert.equal(env.requests.length, 4);
  assert.equal(env.requests.filter(item => item.url === '/api/auth/refresh').length, 1);
  assert.ok(env.requests.every(item => item.headers.Authorization !== 'Bearer ' + B.token));
  preserved(env, B);
});

test('A very late A401 after two valid rotations retries once with A2 and the original operation', async () => {
  const started = deferred(), release = deferred(); let count = 0;
  const env = fixture(async (url, options) => {
    if (url === '/api/auth/refresh') return ok(credentials(++count === 1 ? A1 : A2));
    if (url === '/api/generar-plan' && options.headers.Authorization === 'Bearer ' + A.token) {
      started.resolve(); await release.promise; return denied();
    }
    if (url.includes('/force-first') && options.headers.Authorization === 'Bearer ' + A.token) return denied();
    if (url.includes('/force-second') && options.headers.Authorization === 'Bearer ' + A1.token) return denied();
    return ok({success: true});
  });
  const held = env.api.planes.generar('synthetic-A-client', 7, 'opciones', 'synthetic-original-key');
  const heldResult = Promise.allSettled([held]);
  await bounded(started.promise); await env.api.clientes.obtener('force-first');
  await env.api.clientes.obtener('force-second'); release.resolve();
  assert.equal((await bounded(heldResult))[0].status, 'fulfilled');
  const generated = env.requests.filter(item => item.url === '/api/generar-plan');
  assert.equal(generated.length, 2); assert.equal(generated[0].body, generated[1].body);
  assert.equal(generated[1].headers.Authorization, 'Bearer ' + A2.token);
  assert.ok(generated.every(item => item.headers['Idempotency-Key'] === 'synthetic-original-key'));
  assert.equal(count, 2); preserved(env, A2);
});

test('A retry401 arriving after a second valid rotation cannot expire A2', async () => {
  const retryStarted = deferred(), release = deferred(); let rotations = 0;
  const env = fixture(async (url, options) => {
    if (url === '/api/auth/refresh') return ok(credentials(++rotations === 1 ? A1 : A2));
    if (url.endsWith('/old')) {
      if (options.headers.Authorization === 'Bearer ' + A.token) return denied();
      retryStarted.resolve(); await release.promise; return denied();
    }
    return options.headers.Authorization === 'Bearer ' + A1.token ? denied() : ok({success: true});
  });
  const old = env.api.clientes.obtener('old'); const settled = Promise.allSettled([old]);
  await bounded(retryStarted.promise); await env.api.clientes.obtener('new'); release.resolve();
  assert.equal((await bounded(settled))[0].status, 'rejected');
  preserved(env, A2); assert.equal(rotations, 2);
});

for (const action of ['info', 'accept']) test('Public invitation ' + action + ' never sends Bearer or refreshes an unauthorized response', async () => {
  const env = fixture(async () => denied());
  const result = await bounded(Promise.allSettled([env.api.team[action]('synthetic-invite', 'synthetic-password')]));
  assert.equal(result[0].status, 'rejected');
  assert.equal(env.requests.length, 1); assert.equal(env.requests[0].headers.Authorization, undefined);
  preserved(env, A);
});

test('Multipart retry reuses the original bytes without adding JSON Content-Type', async () => {
  const env = fixture(async (url, options) => {
    if (url === '/api/auth/refresh') return ok(credentials(A1));
    return options.headers.Authorization === 'Bearer ' + A.token ? denied() : ok({success: true});
  });
  await env.api.gym.uploadLogo(new File(['synthetic-byte-payload'], 'synthetic.png', {type: 'image/png'}));
  const uploads = env.requests.filter(item => item.url === '/api/gym/logo');
  assert.equal(uploads.length, 2); assert.equal(uploads[0].body, uploads[1].body);
  assert.equal(await uploads[1].body.get('file').text(), 'synthetic-byte-payload');
  assert.ok(uploads.every(item => !Object.keys(item.headers).some(key => key.toLowerCase() === 'content-type')));
  preserved(env, A1);
});

test('Late network failure of A is classified as session_changed and preserves B', async () => {
  const started = deferred(), release = deferred();
  const env = fixture(async () => { started.resolve(); await release.promise; throw new TypeError('Synthetic fetch failure'); });
  const operation = env.api.clientes.eliminar('synthetic-A'); const settled = Promise.allSettled([operation]);
  await bounded(started.promise); env.replace(B); release.resolve();
  assert.equal((await bounded(settled))[0].reason.code, 'session_changed');
  assert.equal(env.requests.length, 1); preserved(env, B);
});

test('Logout waiting on A refresh cannot clear B or send its logout with B credentials', async () => {
  const started = deferred(), release = deferred();
  const env = fixture(async url => {
    if (url === '/api/auth/refresh') { started.resolve(); await release.promise; return ok(credentials(A1)); }
    return denied();
  });
  const operation = env.api.auth.logout();
  await bounded(started.promise); env.replace(B); release.resolve(); await bounded(operation);
  assert.equal(env.requests.filter(item => item.url === '/api/auth/logout').length, 1);
  assert.ok(env.requests.every(item => item.headers.Authorization !== 'Bearer ' + B.token));
  preserved(env, B);
});

test('Invalid refresh credentials settle a mixed queue and a fresh explicit B login restores transport', async () => {
  const started = deferred(), release = deferred(); let recovered = false, rotations = 0;
  const env = fixture(async (url, options) => {
    if (recovered) return ok({success: true});
    if (url === '/api/auth/refresh') {
      rotations++; started.resolve(); await release.promise; return ok({token: A1.token});
    }
    return denied();
  });
  const settled = Promise.allSettled([env.api.clientes.obtener('A'), env.api.usuario.exportarDatos(),
    env.api.gym.uploadLogo(new File(['A'], 'A.png', {type: 'image/png'}))]);
  await bounded(started.promise); release.resolve();
  assert.ok((await bounded(settled)).every(item => item.status === 'rejected'));
  assert.equal(rotations, 1); assert.deepEqual(env.current(), {token: '', refresh: ''});
  env.api.saveTokens(credentials(B)); recovered = true; env.window.location.href = '';
  assert.equal((await bounded(env.api.clientes.obtener('B'))).success, true);
  preserved(env, B);
});

test('A partial explicit token save must not later replay a B mutation using the old A refresh authority', async () => {
  const env = fixture(async (url, options) => {
    if (url === '/api/auth/refresh') {
      assert.equal(JSON.parse(options.body).refresh_token, A.refresh);
      return ok(credentials(A1));
    }
    return [A.token, A1.token].some(token => options.headers.Authorization === 'Bearer ' + token)
      ? ok({success: true, scope: 'A'}) : denied();
  });
  env.failWriteWhen((key, value) => key === 'mb_refresh_token' && value === B.refresh);
  assert.throws(() => env.api.saveTokens(credentials(B)), {name: 'QuotaExceededError'});
  env.failWriteWhen(null);
  const result = await bounded(Promise.allSettled([
    env.api.clientes.actualizar('synthetic-B-client', {nombre: 'synthetic-B-data'})]));
  assert.equal(env.requests.filter(item => item.url.startsWith('/api/clientes/') &&
    [A.token, A1.token].some(token => item.headers.Authorization === 'Bearer ' + token)).length, 0,
  'A failed two-key save cannot be accepted as a new rotation source and replay B data under A');
  assert.equal(result[0].status, 'rejected');
});

(async () => {
  const results = [];
  for (const entry of cases) {
    try { await bounded(entry.body()); results.push({case: entry.name, passed: true}); }
    catch (error) { results.push({case: entry.name, passed: false, reason: error.message}); }
  }
  console.log(JSON.stringify({scope: 'Independent in-memory SEC02 probes; no browser, backend, signature, provider or cross-tab atomicity claim',
    source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
    passed: results.filter(item => item.passed).length, total: results.length, results}, null, 2));
  if (results.some(item => !item.passed)) process.exitCode = 1;
})().catch(error => { console.error(error.message); process.exitCode = 1; });
