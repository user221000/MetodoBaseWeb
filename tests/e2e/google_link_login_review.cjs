/* Additive Google error copy; fixed VM input, no Google provider or login execution. */
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const context=vm.createContext({window:{}});vm.runInContext(fs.readFileSync(process.env.GOOGLE_LINK_LOGIN_SOURCE||'web/static/js/mfa-login.js','utf8'),context);
const cases=[['google_link_required',409,'vincul'],['google_link_conflict',409,'vincul'],['google_identity_invalid',401,'Google']];
const results=cases.map(([code,status,word])=>{try{const text=context.window.MfaLogin.message({code,status});assert.equal(typeof text,'string');assert.ok(text.normalize('NFD').replace(/\p{M}/gu,'').includes(word));return{code,passed:true};}catch(error){return{code,passed:false,class:error.name};}});
const report={scope:'Google-only error formatter VM, no login/MFA/provider execution',passed:results.filter(row=>row.passed).length,total:results.length,results};
if(process.env.GOOGLE_LINK_LOGIN_OUTPUT){assert.equal(fs.existsSync(process.env.GOOGLE_LINK_LOGIN_OUTPUT),false);fs.writeFileSync(process.env.GOOGLE_LINK_LOGIN_OUTPUT,JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify(report));if(report.passed!==report.total)process.exitCode=1;
