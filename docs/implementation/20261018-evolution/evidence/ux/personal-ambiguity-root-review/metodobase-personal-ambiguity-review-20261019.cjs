const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const vm = require('node:vm');
const path = require('node:path');

const sourcePath = process.argv[2];
const output = process.argv[3];
if (!sourcePath || !output) throw new Error('Usage: review.cjs controller-path output-json');
const body = fs.readFileSync(sourcePath);
const digest = crypto.createHash('sha256').update(body).digest('hex');
const saved = output.replace(/\.json$/, '-controller-' + digest.slice(0, 12) + '.js');
if (!fs.existsSync(saved)) fs.writeFileSync(saved, body, {flag:'wx'});
async function runCase(code, confirmReleased) {
  const calls = [], keys = [], states = [];
  let sequence = 0;
  const session = {revision:17};
  const context = {
    window: {addEventListener(){}},
    crypto: {randomUUID:() => { const key = 'intent-' + (++sequence); keys.push(key); return key; }},
    setTimeout, clearTimeout, Error, Set,
    Api: {usuario: {
      contexto: async () => ({me:{id:'synthetic-personal'}, session}),
      validarContexto: candidate => assert.equal(candidate.session, session),
      verificarContexto: async candidate => assert.equal(candidate.session, session),
      generarPlan: async key => {
        calls.push(key);
        if (calls.length === 1) throw Object.assign(new Error('No se confirmó el resultado.'), {status:400, ...(code ? {code} : {})});
        if (confirmReleased && calls.length === 2) throw Object.assign(new Error('La reserva fue liberada.'), {status:409, code:'generation_failed'});
        return {plan_id:901, plan:{desayuno:{foods:[]}}, tiene_pdf:true};
      },
    }},
  };
  vm.createContext(context);
  vm.runInContext(body.toString('utf8'), context, {filename:'usuario-plan-operacion.js'});
  const operation = context.window.PersonalPlanOperation.create({onState: value => states.push(value.state)});
  await operation.start();
  await operation.generate();
  const countAfterAmbiguous = calls.length;
  await operation.generate(true);
  assert.equal(calls.length, countAfterAmbiguous, 'A 400 response alone cannot establish an unpublished request or start a new intent');
  assert.equal(keys.length, 1, 'Ambiguous response must retain the original key');
  await operation.generate();
  assert.equal(calls[1], calls[0], 'A lookup/retry after ambiguity must use the same request key');
  if (confirmReleased) {
    assert.equal(operation.state, 'failed', 'A replay confirming released may permit a new intent');
    await operation.generate(true);
    assert.equal(calls.length, 3);
    assert.notEqual(calls[2], calls[0], 'Only the explicit new intent after confirmed release uses a new key');
  } else {
    assert.equal(operation.state, 'completed');
    assert.equal(keys.length, 1);
  }
  return {calls:calls.length, keys:keys.length, states};
}
(async () => {
  const cases = [];
  for (const code of [null, 'generation_unavailable']) {
    for (const confirmReleased of [false, true]) {
      const name = (code || 'untyped_400') + (confirmReleased ? '_confirmed_release_control' : '_published_replay');
      try { cases.push({name, passed:true, ...await runCase(code, confirmReleased)}); }
      catch (error) { cases.push({name, passed:false, failure: error.message}); }
    }
  }
  const report = {scope:'Independent controller VM: ambiguous 400 must retain identity until same-key replay establishes released. Synthetic API; separate real worker/browser evidence required.',
    source_sha256:digest, saved_source:path.basename(saved), total:cases.length,
    passed:cases.filter(item => item.passed).length, cases};
  fs.writeFileSync(output, JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({source_sha256:digest,total:report.total,passed:report.passed}));
  process.exitCode = report.passed === report.total ? 0 : 1;
})();
