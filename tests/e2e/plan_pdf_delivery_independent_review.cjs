/* Semantic checks against the real browser API and synthetic HTTP transport. */
const assert = require('node:assert/strict');
const {closed} = require('./browser_harness31.cjs');
const me = () => Response.json({id:'synthetic-person', role:'viewer', tipo:'usuario', session_version:0});
const pdf = () => new Response('%PDF-review-synthetic', {headers:{'Content-Type':'application/pdf'}});
const pending = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return {resolve, promise}; };
function popup() { return {closed:false, addresses:[], close(){this.closed=true;}, location:{replace(value){this.addresses.push(value);}, addresses:[]}}; }
function urls(e) {
  const created=[], revoked=[];
  let timer;
  e.context.setInterval = fn => {timer = fn; return 1;};
  e.context.clearInterval = () => {timer = null;};
  e.context.URL = class extends URL { static createObjectURL(blob){created.push(blob);return 'blob:private-synthetic';}
    static revokeObjectURL(url){revoked.push(url);} };
  return {created, revoked, tick:()=>timer?.()};
}

(async () => {
  const e = await closed(async url => url === '/api/auth/me' ? me() : pdf());
  const record = urls(e), win = popup();
  await e.api.usuario.abrirPlan(42, undefined, win);
  assert.deepEqual(win.location.addresses, ['blob:private-synthetic']);
  assert.equal(await record.created[0].text(), '%PDF-review-synthetic');
  assert.equal(e.calls.filter(call => call.url.includes('descargar-pdf'))[0].url, '/api/usuario/descargar-pdf?plan_id=42');
  e.invalidate();
  assert.equal(win.closed, true);
  assert.deepEqual(record.revoked, ['blob:private-synthetic']);

  const manuallyClosed = await closed(async url => url === '/api/auth/me' ? me() : pdf());
  const manualUrls = urls(manuallyClosed), manualWindow = popup();
  await manuallyClosed.api.usuario.abrirPlan(42, undefined, manualWindow);
  manualWindow.closed = true; manualUrls.tick();
  assert.deepEqual(manualUrls.revoked, ['blob:private-synthetic']);

  const bad = await closed(async url => url === '/api/auth/me' ? me() : new Response('not-a-pdf', {headers:{'Content-Type':'application/pdf'}}));
  const badUrls = urls(bad), badWindow = popup();
  await assert.rejects(bad.api.usuario.abrirPlan(42, undefined, badWindow));
  assert.equal(badUrls.created.length, 0);
  assert.throws(() => bad.api.usuario.abrirPlan(0, undefined, badWindow));

  const started = pending(), release = pending();
  const raced = await closed(async url => { if (url === '/api/auth/me') return me(); started.resolve(); await release.promise; return pdf(); });
  const raceUrls = urls(raced), raceWindow = popup();
  const operation = raced.api.usuario.abrirPlan(42, undefined, raceWindow);
  const settled = Promise.allSettled([operation]);
  await started.promise; raced.invalidate(); release.resolve();
  assert.equal((await settled)[0].status, 'rejected');
  assert.equal(raceUrls.created.length, 0);
  assert.equal(raceWindow.location.addresses.length, 0);
  console.log('Plan PDF open independent review: 5 scenarios passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
