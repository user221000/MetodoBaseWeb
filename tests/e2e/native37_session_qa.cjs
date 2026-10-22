/* Own native setup utility: real primary/MFA/cookie HTTP, secrets only Node RAM. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const native=require('./browser_native_session31.cjs');
const original=path.join(__dirname,'mfa31_login.cjs'),source=fs.readFileSync(original,'utf8');
const factor=new Module(original,module);factor.filename=original;factor.paths=module.paths;
factor._compile(source+'\nmodule.exports={...module.exports,enroll,nextCode};',original);

function privateHeaders(response){
 const headers=response.headers();
 assert.ok((headers['cache-control']||'').split(',').some(part=>part.trim().toLowerCase()==='no-store'));
 assert.equal(headers['referrer-policy'],'no-referrer');
}
async function login(page,base,actor,{setup=true}={}){
 if(setup)await factor.exports.enroll(page.request,base,actor.email,actor.password);
 await page.goto(base+'/login-'+actor.audience,{waitUntil:'domcontentloaded'});await native.ready(page);
 await page.locator('#loginForm input[name=email]').fill(actor.email);
 await page.locator('#loginForm input[name=password]').fill(actor.password);
 const primary=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/auth/login'&&response.request().method()==='POST');
 await page.locator('#loginForm button[type=submit]').click();
 const first=await primary;assert.equal(first.status(),202);const challenge=await first.json();
 assert.equal(challenge.session_mode,'browser');assert.equal(Object.hasOwn(challenge,'token'),false);assert.equal(Object.hasOwn(challenge,'refresh_token'),false);
 await page.locator('#mfa-login-factor').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>Api.getToken()),'');
 await page.locator('#mfa-login-method').selectOption('recovery_code');await page.locator('#mfa-login-recovery').fill(factor.exports.nextCode(actor.email));
 const verified=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/auth/mfa/login/verify'&&response.request().method()==='POST');
 await page.locator('#mfa-login-factor button[type=submit]').click();
 const response=await verified;assert.equal(response.status(),200);const body=await response.json();
 assert.equal(body.session_mode,'browser');assert.equal(Object.hasOwn(body,'refresh_token'),false);
 await page.waitForURL(url=>[actor.audience==='gym'?'/dashboard':'/mi-plan','/equipo/inicio'].includes(url.pathname));await native.ready(page);
 const result=await page.evaluate(async()=>({access:Api.getToken(),me:await Api.auth.me(),clean:['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].every(key=>localStorage.getItem(key)===null&&sessionStorage.getItem(key)===null)}));
 assert.equal(result.clean,true);assert.equal(result.me.id,actor.id);
 assert.equal(result.me.role,actor.audience==='gym'?'owner':'viewer');assert.equal(result.me.team_gym_id,null);
 return result.access;
}
function nextFactor(actor){return factor.exports.nextCode(actor.email);}
function erase(){factor.exports.erase();}
module.exports={...native,login,nextFactor,privateHeaders,erase};
