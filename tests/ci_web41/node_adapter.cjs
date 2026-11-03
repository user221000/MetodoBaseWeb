/* Finite current-contract fixture adapters; original programs/assertions remain authenticated. */
'use strict';
require('../e2e/browser_offline31.cjs');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const digest=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const canonical=text=>text.replace(/\r\n/g,'\n');
const rulesPath=path.join(__dirname,'node-adapters41.json');
const raw=canonical(fs.readFileSync(rulesPath,'utf8'));
const expected='fa3bdb7cd4a561882d933dab0c0b93c27711b041d33ea8a6adace80c2aed4b24';
if(digest(raw)!==expected)throw Error('Finite Node41 adapter registry differs');
const registry=JSON.parse(raw),root=path.resolve(__dirname,'../..');
if(registry.schema!=='current41-node-explicit-adapters-v1'||registry.rules.length!==5)throw Error('Node41 adapter scope differs');
function assertions(source){
 const result=[];
 for(const match of source.matchAll(/\bassert\.[A-Za-z]+\(/g)){
  const start=source.indexOf('(',match.index);let depth=1,i=start+1,quote=null;
  for(;i<source.length&&depth;i++){
   const c=source[i];
   if(quote){if(c==='\\'){i++;continue;}if(c===quote)quote=null;continue;}
   if(c==='"'||c==="'"||c==='`'){quote=c;continue;}
   if(c==='(')depth++;else if(c===')')depth--;
  }
  if(depth)throw Error('Unbalanced finite assertion source');
  result.push(source.slice(match.index,i));
 }
 return result;
}
function adapt(source,rule){
 const before=canonical(source);
 if(digest(before)!==rule.input_compiled_canonical_lf_sha256)throw Error('Node41 compiled input differs');
 const original=canonical(fs.readFileSync(path.join(root,rule.script),'utf8'));
 if(digest(original)!==rule.original_canonical_lf_sha256)throw Error('An original Node41 program differs');
 let after=before;
 for(const replacement of rule.replacements){
  if(![1,2].includes(replacement.count)||after.split(replacement.before).length!==replacement.count+1)throw Error('Node41 exact fixture replacement differs');
  after=after.split(replacement.before).join(replacement.after);
 }
 if(digest(after)!==rule.output_compiled_canonical_lf_sha256)throw Error('Node41 compiled output differs');
 const oldAssertions=assertions(before),newAssertions=assertions(after);
 if(oldAssertions.length!==rule.assertion_count||newAssertions.length!==oldAssertions.length)throw Error('A Node41 business assertion was removed');
 const changes=oldAssertions.flatMap((item,i)=>item===newAssertions[i]?[]:[{before:item,after:newAssertions[i]}]);
 if(changes.length!==rule.allowed_assertion_changes.length||changes.some((item,i)=>item.before!==rule.allowed_assertion_changes[i].before||item.after!==rule.allowed_assertion_changes[i].after))throw Error('An unreviewed Node41 assertion change occurred');
 return {text:after,metadata:{script:rule.script,scope:registry.scope,
  original_canonical_lf_sha256:rule.original_canonical_lf_sha256,
  input_compiled_canonical_lf_sha256:digest(before),output_compiled_canonical_lf_sha256:digest(after),
  input_compiled_actual_sha256:digest(source),assertions_preserved:oldAssertions.length,
  criterion_renames:rule.criterion_renames,allowed_assertion_changes:rule.allowed_assertion_changes,
  historical_PASS_claim:false}};
}
const compile=Module.prototype._compile;
Module.prototype._compile=function(source,filename){
 const relative=path.relative(root,filename).split(path.sep).join('/');
 const rule=registry.rules.find(item=>item.script===relative);
 if(!rule)return compile.call(this,source,filename);
 const result=adapt(source,rule);
 const previous=console.log;
 console.log=(...args)=>{
  if(args.length===1){
   let value=args[0];if(typeof value==='string')try{value=JSON.parse(value);}catch{}
   if(value&&typeof value==='object'&&(Array.isArray(value.results)||Array.isArray(value.rows))){
    return previous(JSON.stringify({...value,current41_adapter:result.metadata}));
   }
  }
  return previous(...args);
 };
 if(rule.script==='tests/e2e/security_onboarding22_peer.cjs'){
  // This original peer writes its single JSON report directly. Add only the
  // adapter provenance; labels, counters, rows and pass/fail facts stay intact.
  const write=process.stdout.write;
  process.stdout.write=function(chunk,...args){
   if(typeof chunk==='string'){
    let value;try{value=JSON.parse(chunk);}catch{}
    if(value&&typeof value==='object'&&Array.isArray(value.rows)){
     chunk=JSON.stringify({...value,current41_adapter:result.metadata})+'\n';
    }
   }
   return write.call(this,chunk,...args);
  };
 }
 // Logging belongs to the loader. Execute the exact approved output bytes,
 // preserving original directive prologues and program-level strict mode.
 return compile.call(this,result.text,filename);
};
module.exports={adapt,assertions};
