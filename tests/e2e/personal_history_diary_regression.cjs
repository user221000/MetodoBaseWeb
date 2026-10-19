/* Keep the original17 diary assertions; adapt only its two dedicated origin literals. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const original=path.join(__dirname,'personal_diary.cjs'),bytes=fs.readFileSync(original),source=bytes.toString('utf8');
assert.equal(source.split('http://127.0.0.1:8776').length-1,2);
const adapted=source.replaceAll('http://127.0.0.1:8776','http://127.0.0.1:8780');
process.env.METODOBASE_E2E_URL='http://127.0.0.1:8780';
process.env.METODOBASE_EVIDENCE_BATCH||='history-regression-'+Date.now();
const out=path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux/diary-ui-browser-'+process.env.METODOBASE_EVIDENCE_BATCH);fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(path.join(out,'executed-diary-driver.cjs'),adapted);
fs.writeFileSync(path.join(out,'driver-source.json'),JSON.stringify({scope:'Only two origin literals adapted in memory; original source unchanged. All17 assertions retained.',original_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),executed_sha256:crypto.createHash('sha256').update(adapted).digest('hex'),origin:'http://127.0.0.1:8780'},null,2));
const compiled=new Module(original,module);compiled.filename=original;compiled.paths=module.paths;compiled._compile(adapted,original);
