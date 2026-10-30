/* Synthetic semantic checks for the plan-generation share control. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../../web/templates/generar-plan.html'), 'utf8');
const start = html.indexOf('// Prepare the actual PDF before invoking');
const end = html.indexOf('// Regenerar / volver', start);
assert.ok(start > 0 && end > start);
const source = html.slice(start, end);

function fixture(options = {}) {
  let listener, session = 1, fetches = 0;
  const calls = [];
  const elements = {
    's3-whatsapp': {disabled: false, textContent: '', addEventListener(type, fn) { assert.equal(type, 'click'); listener = fn; }},
    's3-download-status': {textContent: ''},
  };
  const navigator = {
    canShare: options.unsupported ? undefined : input => { assert.equal(input.files[0].type, 'application/pdf'); return !options.cannotShare; },
    share: options.unsupported ? undefined : async input => {
      calls.push(input);
      if (options.cancel) throw Object.assign(new Error('cancel'), {name: 'AbortError'});
    },
  };
  const pdf = new Blob(['%PDF-independent-synthetic'], {type:'application/pdf'});
  const api = {
    planes: {obtenerPdfPorPlan: async id => { fetches++; assert.equal(id, 42); if (options.pending) await options.pending; return pdf; }},
    session: {capture: () => session, check: value => { if (value !== session) throw new Error('changed'); }},
  };
  const sandbox = {navigator, document: {getElementById: id => elements[id]}, Api: api, File, Error,
    externalVerify: async () => { if (options.verify) await options.verify(); }};
  const prefix = `let _cliente_sel={id:'synthetic'}, _plan_result={plan_id:42}, _generationSessionDiscarded=false,
    _generationEpoch=0, _shareFile=null, _sharePlan=null, _shareSession=null;
    async function verifyGenerationAccount(epoch){if(_generationSessionDiscarded||epoch!==_generationEpoch)throw Error('changed');
      await externalVerify();if(_generationSessionDiscarded||epoch!==_generationEpoch)throw Error('changed');}`;
  const suffix = `globalThis.controls={replacePlan(){_plan_result={plan_id:99}}, invalidate(){_generationEpoch++;_generationSessionDiscarded=true;clearSharePreparation()}, clearSharePreparation,
    get prepared(){return !!_shareFile}};`;
  vm.runInNewContext(prefix + source + suffix, sandbox);
  return {click: () => listener(), calls, elements, controls:sandbox.controls,
    changeSession: () => { session++; }, get fetches() { return fetches; }};
}

(async () => {
  const normal = fixture();
  await normal.click();
  assert.equal(normal.fetches, 1);
  assert.equal(normal.calls.length, 0, 'first click only prepares the file');
  assert.equal(normal.controls.prepared, true);
  const pending = normal.click();
  assert.equal(normal.calls.length, 1, 'share is invoked before the event handler yields');
  assert.equal(normal.calls[0].files[0].name, 'plan-alimenticio.pdf');
  assert.equal(await normal.calls[0].files[0].text(), '%PDF-independent-synthetic');
  assert.equal(normal.calls[0].title, 'Plan alimenticio');
  await pending;
  assert.equal(normal.controls.prepared, false);

  for (const options of [{unsupported:true}, {cannotShare:true}]) {
    const f = fixture(options); await f.click();
    assert.equal(f.calls.length, 0); assert.equal(f.controls.prepared, false);
    assert.match(f.elements['s3-download-status'].textContent, /descarga|Descarga/);
  }
  const cancelled = fixture({cancel:true}); await cancelled.click(); await cancelled.click();
  assert.equal(cancelled.controls.prepared, false);
  assert.match(cancelled.elements['s3-download-status'].textContent, /canceló/);

  const changed = fixture(); await changed.click(); changed.changeSession(); await changed.click();
  assert.equal(changed.calls.length, 0); assert.equal(changed.controls.prepared, false);
  const changedPlan = fixture(); await changedPlan.click(); changedPlan.controls.replacePlan();
  await changedPlan.click(); assert.equal(changedPlan.calls.length, 0);
  let release; const held = new Promise(resolve => { release = resolve; });
  const invalidated = fixture({pending:held}); const first = invalidated.click();
  await Promise.resolve(); await Promise.resolve(); invalidated.controls.invalidate(); release(); await first;
  assert.equal(invalidated.calls.length, 0); assert.equal(invalidated.controls.prepared, false);
  console.log('Plan share independent review: 7 scenarios passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
