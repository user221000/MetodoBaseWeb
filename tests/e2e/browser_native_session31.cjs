/* Explicit setup/coordination for native browser tests. No product auth override. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const original=path.join(__dirname,'mfa31_login.cjs'),legacySource=fs.readFileSync(original,'utf8');
const legacy=new Module(original,module);legacy.filename=original;legacy.paths=module.paths;
legacy._compile(legacySource+'\nmodule.exports={...module.exports,enroll,nextCode};',original);
const lockName='metodobase.browser-session.v1';
const identities=new WeakMap();
function fixtureOrigin(origin){assert.equal(new URL(origin).origin,origin);assert.ok(/^https?:\/\/(?:127\.0\.0\.1|localhost):\d+$/.test(origin),'Native fixture must use an explicit loopback origin');}
async function ready(page){return page.evaluate(async()=>{await Api.session.ready;return{authenticated:!!Api.getToken()};});}
async function installStorageGuard(context){
 await context.addInitScript(()=>{
  const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].includes(key))throw new Error('Credential or identity Storage write forbidden by current browser fixture');return original.call(this,key,value);};
 });
}
async function createContext(browser,options){const context=await browser.newContext(options);await installStorageGuard(context);return context;}
async function invalidate(page){
 // This models an external completed boundary/public reset, not a new actor ACK.
 await page.evaluate(()=>{const epoch=crypto.randomUUID();localStorage.setItem('mb_session_epoch',epoch);if(typeof BroadcastChannel==='function'){const channel=new BroadcastChannel('metodobase.browser-session.v1');channel.postMessage({epoch});channel.close();}dispatchEvent(new StorageEvent('storage',{key:'mb_session_epoch',newValue:epoch}));});
}
async function migrate(context,origin,pair){
 fixtureOrigin(origin);assert.equal(typeof pair.refresh_token,'string');assert.ok(pair.refresh_token.length>0&&pair.refresh_token.length<=8192);
 const setup=await context.newPage();
 try{
  await setup.goto(origin+'/',{waitUntil:'domcontentloaded'});
  const result=await setup.evaluate(async({proof,lockName})=>{
   if(!navigator.locks?.request)throw new Error('Native fixture requires Web Locks');
   return navigator.locks.request(lockName,{mode:'exclusive'},async()=>{
    const epoch=crypto.randomUUID();localStorage.setItem('mb_session_epoch',epoch);if(typeof BroadcastChannel==='function'){const channel=new BroadcastChannel(lockName);channel.postMessage({epoch});channel.close();}
    const response=await fetch('/api/auth/browser/migrate',{method:'POST',headers:{'Content-Type':'application/json','X-MetodoBase-Browser':'1'},body:JSON.stringify({refresh_token:proof}),credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});
    const body=await response.json();if(response.status!==200||body.session_mode!=='browser'||typeof body.token!=='string'||Object.hasOwn(body,'refresh_token'))throw new Error('Native fixture migration was not confirmed');return{status:response.status,browser:true};
   });
  },{proof:pair.refresh_token,lockName});
  assert.deepEqual(result,{status:200,browser:true});
 }finally{await setup.close();}
}
async function migrateWithIdentity(context,origin,pair){
 fixtureOrigin(origin);const response=await context.request.get(origin+'/api/auth/me',{headers:{Authorization:'Bearer '+pair.token}});assert.equal(response.status(),200);const me=await response.json();assert.equal(typeof me.id,'string');identities.set(context,me);await migrate(context,origin,pair);
}
function identity(context){const me=identities.get(context);assert.ok(me,'Explicit real setup identity required before presentation overrides');return{...me};}
async function mockSensitivePresentation(page){
 // Only for drivers whose sensitive business HTTP is already intercepted.
 // Actual MFA/auth acceptance uses the separate current35 real fixture drivers.
 await page.route('**/api/auth/mfa/step-up',async route=>{
  const body=route.request().postDataJSON(),method=body.method,target=body.path;
  const rules=[['POST','/api/billing/checkout','billing.checkout'],['POST','/api/billing/portal','billing.portal'],['POST','/api/billing/mp/preference','billing.mp'],['POST','/api/gym/team/invite','team.invite']];
  let action=rules.find(row=>row[0]===method&&row[1]===target)?.[2];
  if(!action&&method==='POST'&&/^\/api\/gym\/team\/[^/]+\/resend-invite$/.test(target))action='team.resend';
  if(!action&&method==='PATCH'&&/^\/api\/gym\/team\/[^/]+\/role$/.test(target))action='team.role';
  if(!action&&method==='DELETE'&&/^\/api\/gym\/team\/[^/]+$/.test(target))action='team.remove';
  if(!action)return route.fallback();
  return route.fulfill({json:{grant:'g'.repeat(43),expires_at:'2099-10-19T18:00:00Z',single_use:true,action,method,path:target},headers:{'Cache-Control':'no-store','Referrer-Policy':'no-referrer'}});
 });
}
async function formLogin(page,base,email,password,audience){
 await legacy.exports.enroll(page.request,base,email,password);
 await page.goto(base+'/login-'+audience,{waitUntil:'domcontentloaded'});await ready(page);
 await page.locator('#loginForm input[name=email]').fill(email);await page.locator('#loginForm input[name=password]').fill(password);
 const primary=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login'&&r.request().method()==='POST');
 await page.locator('#loginForm button[type=submit]').click();const initial=await primary;assert.equal(initial.status(),202);const challenge=await initial.json();assert.equal(challenge.session_mode,'browser');assert.equal(Object.hasOwn(challenge,'token'),false);assert.equal(Object.hasOwn(challenge,'refresh_token'),false);
 await page.locator('#mfa-login-factor').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>Api.getToken()),'');
 await page.locator('#mfa-login-method').selectOption('recovery_code');await page.locator('#mfa-login-recovery').fill(legacy.exports.nextCode(email));
 const verified=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/mfa/login/verify'&&r.request().method()==='POST');
 await page.locator('#mfa-login-factor button[type=submit]').click();const response=await verified;assert.equal(response.status(),200);const data=await response.json();assert.equal(data.session_mode,'browser');assert.equal(Object.hasOwn(data,'refresh_token'),false);
 await page.waitForURL(url=>[audience==='gym'?'/dashboard':'/mi-plan','/equipo/inicio'].includes(url.pathname));await ready(page);
 const state=await page.evaluate(()=>({access:Api.getToken(),clean:['mb_token','mb_refresh_token','mb_nombre','mb_email','mb_tipo'].every(key=>localStorage.getItem(key)===null&&sessionStorage.getItem(key)===null)}));assert.ok(state.access);assert.equal(state.clean,true);
 // Destination bootstrap may rotate access; callers retain only this RAM access.
 return{...data,token:state.access};
}
module.exports={ready,installStorageGuard,createContext,invalidate,migrate,migrateWithIdentity,identity,mockSensitivePresentation,formLogin,apiLogin:legacy.exports.apiLogin,erase:legacy.exports.erase};
