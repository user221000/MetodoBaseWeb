/* Explicit clock companion: original immutable assertions, delay headers401. */
'use strict';
const fs=require('node:fs'),Module=require('node:module'),assert=require('node:assert/strict'),cp=require('node:child_process'),crypto=require('node:crypto');
const name='tests/e2e/security_account37_boundaries_peer.cjs',original=fs.readFileSync(name,'utf8');
const frozen=cp.execFileSync('git',['show','08de03f3ecbbc8d8a10bac193f12efadf92312ad:'+name],{encoding:'utf8'});assert.equal(original,frozen);
const old="e.control.hook=call=>call.path===path?{...response({},401),json:async()=>{began.resolve();await gate.promise;return{detail:{code:'account_security_identity_unavailable'}};}}:null;";
const revised="e.control.hook=async call=>{if(call.path!==path)return null;began.resolve();await gate.promise;return response({detail:{code:'account_security_identity_unavailable'}},401);};";
assert.equal(original.split(old).length,2);const candidate=original.replace(old,revised);assert.equal(candidate.replace(revised,old),original);
// This single timing-only fixture replacement executes in the three path cases;
// every test name, scheduling action and actor/epoch/assertion byte is unchanged.
const child=new Module(__filename,module);child.filename=__filename;child.paths=module.paths;
child._compile(candidate.replace("scope:'Actual Api/controller in independent VM and minimal DOM; transport, WebLock, Storage and GIS are doubles. No native/real-provider claim.'","scope:'Explicit headers401 companion:15 original cases plus3 unchanged actor/epoch assertions with transport delay replacing JSON delay. VM/minimal DOM doubles; no native/provider claim.'"),__filename);
void crypto;
