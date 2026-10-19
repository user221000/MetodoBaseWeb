/* Final public handoff metadata only. Does not mutate the frozen UI or scanner seal. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const prefix='docs/implementation/20261018-evolution/evidence/progress-retirement-ui/';
const frozen=JSON.parse(fs.readFileSync(prefix+'freeze.json','utf8'));
const hash=body=>crypto.createHash('sha256').update(body).digest('hex');
for(const[name,value]of Object.entries(frozen.sources)){
  assert.equal(hash(fs.readFileSync(name)),value.raw_sha256);
  assert.equal(hash(execFileSync('git',['show',':'+name])),value.git_lf_sha256);
}
for(const[name,value]of Object.entries(frozen.protected_unchanged))assert.equal(hash(fs.readFileSync(name)),value);
function walk(directory){return fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);}
const proofs=Object.fromEntries(walk(prefix).filter(name=>!name.endsWith('final-source.json')).map(name=>[name.replaceAll('\\','/'),hash(fs.readFileSync(name))]));
const result={
  base:frozen.base,author_seal_sha256:hash(fs.readFileSync(prefix+'freeze.json')),
  sources:frozen.sources,protected_unchanged:frozen.protected_unchanged,proofs,
  checks:{controller_vm:'36/36 synthetic',mounted_dom_vm:'9/9 synthetic',ssr:'8/8 synthetic factories; original4canary assertions unchanged',scanner_source_exact:13,scanner_changed_files:0,scanner_findings_in_13_source_files:0,global_scanner_exit:1,own_proof_fingerprints_verified:2,other_existing_findings:31562,inverse_raw_exact:true,source_raw_zip_verified:true},
  backend_candidate:'fcfb55e5849e0e20b568be8729dcc1b8c6b1762e',backend_composed:false,wire_sha256:frozen.wire_sha256,
  pending:['Backend composition and independent security/QA','Actual purpose-only HTTP and browser320/390/768/1440/keyboard/axe','Global inherited scanner triage'],
  post_scan_artifacts:['classify_scan.py','secret-scan-summary.json','finish.cjs','final-source.json'],
  verification_exceptions:[{file:prefix+'change.patch',check:'git diff --cached --check',reason:'Six blank context lines in the preserved unified patch contain its mandatory leading context space. Preserve the exact reversible proof; all other staged paths pass the same check.'}],
  classification:frozen.classification,
};
fs.writeFileSync(prefix+'final-source.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({final_source_sha256:hash(fs.readFileSync(prefix+'final-source.json')),product_sha256:frozen.sources['web/static/js/retiro-consentimientos.js'].raw_sha256,proofs:Object.keys(proofs).length}));
