/* Actual current image HTTP/browser with persisted PG MFA; no API doubles. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const deps=process.env.METODOBASE_E2E_DEPENDENCIES||path.join(__dirname,'node_modules');
const {chromium,request}=require(path.join(deps,'playwright-core'));
const mfa=require('./mfa31_login.cjs'),base='http://127.0.0.1:8765';
assert.equal(process.env.METODOBASE_E2E_URL,base);
const output=path.resolve(process.argv[2]);assert(!fs.existsSync(output));
const report={scope:'Actual current container entrypoint/PG/HTTP/browser MFA; no providers, test Settings and local storage',checks:[],pageErrors:[],complete:false};
(async()=>{let browser,http;try{
 http=await request.newContext({baseURL:base});
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
 for(const audience of ['usuario','gym']){
  const email='image31-'+crypto.randomUUID()+'@example.invalid',password='Synthetic-Image31-Password-2026!';
  const registered=await http.post('/api/auth/registro',{data:{email,password,nombre:'Synthetic image31',tipo:audience}});
  assert.equal(registered.status(),200);report.checks.push('Actual '+audience+' registration');
  const context=await browser.newContext({serviceWorkers:'block'});
  await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.name));
  const pair=await mfa.formLogin(page,base,email,password,audience);report.checks.push('Actual '+audience+' enrollment/TOTP/password202/recovery200');
  const state=await http.get('/api/auth/mfa/status',{headers:{Authorization:'Bearer '+pair.token}});
  assert.equal(state.status(),200);const value=await state.json();assert.equal(value.enabled,true);assert.equal(value.recovery_codes_remaining,7);
  const me=await http.get('/api/auth/me',{headers:{Authorization:'Bearer '+pair.token}});assert.equal(me.status(),200);
  const identity=await me.json();assert.equal(identity.role,audience==='usuario'?'viewer':'owner');
  report.checks.push('Actual '+audience+' persisted MFA status and canonical role');
  await context.close();
 }
 assert.deepEqual(report.pageErrors,[]);report.complete=true;
}catch(error){report.failure_class=error.name;process.exitCode=1;}
finally{mfa.erase();await http?.dispose();await browser?.close();report.total=report.checks.length;report.passed=report.complete?report.total:0;fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');}
assert.equal(report.complete,true);assert.equal(report.total,6);})().catch(()=>{process.exitCode=1;});
