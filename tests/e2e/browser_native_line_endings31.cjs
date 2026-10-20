/* Compile actual current companions against LF and CRLF historical RAW bytes.
 * File reads are doubled; neither historical files nor transport are executed.
 */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
const names=['mfa31_image','mfa_ui_browser','mfa_personal_browser','dashboard_followup31_browser','daily_plan31_browser','member_link31_browser','subscription','subscription_contract_review','gym_subscription'];
function compile(companion,name,eol){
 const historical=path.join(__dirname,name+'.cjs'),raw=fs.readFileSync(historical,'utf8').replace(/\r\n/g,'\n').replace(/\n/g,eol),logs=[];
 const reader={...fs,readFileSync(file,options){return path.resolve(file)===historical?options==='utf8'?raw:Buffer.from(raw):fs.readFileSync(file,options);}};
 const source=fs.readFileSync(path.join(__dirname,companion),'utf8');
 vm.runInNewContext(source,{require:id=>id==='node:fs'?reader:require(id),__dirname,module:{},process:{argv:['node',companion,...(companion==='browser_native_compat31.cjs'?[name]:[]),'--compile-only'],env:{}},console:{log:value=>logs.push(JSON.parse(value))}},{filename:companion});
 assert.equal(logs.length,1);assert.equal(logs[0].parsed,true);
 const report=logs[0].browser_session_composition||logs[0];assert.equal(report.historical_driver_sha256,digest(raw));return report;
}
const results=[];
for(const name of[...names,'mfa_http_worker']){
 const companion=name==='mfa_http_worker'?'browser_mfa_http_worker31.cjs':'browser_native_compat31.cjs';
 try{
  const lf=compile(companion,name,'\n'),crlf=compile(companion,name,'\r\n');
  assert.notEqual(lf.historical_driver_sha256,crlf.historical_driver_sha256);
  for(const key of['historical_compilation_lf_sha256','compiled_driver_sha256','assertion_calls_preserved_before_normative_changes','preserved_lifecycle_assertion_calls'])assert.equal(lf[key],crlf[key],key);
  assert.deepEqual(JSON.parse(JSON.stringify(lf.normative||[])),JSON.parse(JSON.stringify(crlf.normative||[])));
  assert.deepEqual(JSON.parse(JSON.stringify(lf.changes||[])),JSON.parse(JSON.stringify(crlf.changes||[])));
  if(name==='mfa_http_worker')assert.equal(lf.preserved_lifecycle_assertion_calls,19);
  results.push({case:name+' LF and CRLF preserve identical compiled assertions',passed:true,compilations:2});
 }catch(error){results.push({case:name+' LF and CRLF preserve identical compiled assertions',passed:false,error_class:error.name});}
}
console.log(JSON.stringify({scope:'Actual companion compilation with doubled read-only historical LF/CRLF inputs. No RPC, actual HTTP, browser or PostgreSQL execution.',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;
