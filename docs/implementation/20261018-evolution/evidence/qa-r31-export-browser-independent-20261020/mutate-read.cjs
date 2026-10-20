'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const native=fs.readFileSync,mode=process.env.QA_R31_MUTATION,root=process.env.QA_R31_ROOT;
const targets={credential_write:'web/static/js/api.js',drop_url_cleanup:'web/static/js/usuario-privacidad.js',consumer_throw:'web/static/js/usuario-privacidad.js',report_count:'tests/e2e/personal_export_context.cjs'};
assert.ok(Object.hasOwn(targets,mode));const target=path.resolve(root,targets[mode]);let applications=0;const versions=[];
fs.readFileSync=function(filename,...options){
  const raw=native.call(this,filename,...options);
  if(typeof filename!=='string'||path.resolve(filename)!==target)return raw;
  let text=Buffer.isBuffer(raw)?raw.toString('utf8'):raw;
  const original=text;
  if(mode==='credential_write')text+='\nlocalStorage.setItem("mb_token","synthetic-counterexample-only");\n';
  else if(mode==='consumer_throw')text='throw new Error("SYNTHETIC_QA_RUNTIME_FAILURE");\n'+text;
  else if(mode==='drop_url_cleanup'){
    const before='if(revokeNow)urls.forEach(function(_,url){release(url);});';
    assert.equal(text.split(before).length,2);text=text.replace(before,'if(false)urls.forEach(function(_,url){release(url);});');
  }else{
    const before='total:results.length,';assert.equal(text.split(before).length,2);text=text.replace(before,'total:results.length-1,');
  }
  applications++;versions.push({original_sha256:crypto.createHash('sha256').update(original).digest('hex'),mutated_sha256:crypto.createHash('sha256').update(text).digest('hex')});
  return Buffer.isBuffer(raw)?Buffer.from(text,'utf8'):text;
};
process.on('exit',()=>fs.writeFileSync(process.env.QA_R31_MUTATION_RECEIPT,JSON.stringify({mode,target_relative:targets[mode],applications,versions,disk_product_edited:false},null,2)));
