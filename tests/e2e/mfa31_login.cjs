/* Current31 fixture login: actual persisted enrollment, TOTP and recovery.
 * Factors live only in this driver's RAM, never reports, storage or stdout.
 */
'use strict';
const assert=require('node:assert/strict'),crypto=require('node:crypto');
const factors=new Map();
function totp(secret){let bits=0,value=0;const bytes=[];for(const char of secret){const digit='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'.indexOf(char);assert(digit>=0);value=(value<<5)|digit;bits+=5;if(bits>=8){bits-=8;bytes.push((value>>>bits)&255);}}const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));const hash=crypto.createHmac('sha1',Buffer.from(bytes)).update(counter).digest(),offset=hash[19]&15;return String((hash.readUInt32BE(offset)&0x7fffffff)%1000000).padStart(6,'0');}
async function checked(request,url,data,headers,status=200){const response=await request.post(url,{data,headers});assert.equal(response.status(),status,'Real current31 MFA protocol status');return response.json();}
async function enroll(request,base,email,password){
 if(factors.has(email))return;
 const primary=await checked(request,base+'/api/auth/login',{email,password}),headers={Authorization:'Bearer '+primary.token};
 assert.equal(typeof primary.token,'string');
 const proof=await checked(request,base+'/api/auth/mfa/reauth',{password},headers);
 const pending=await checked(request,base+'/api/auth/mfa/enroll',{reauthentication_token:proof.reauthentication_token},headers);
 const complete=await checked(request,base+'/api/auth/mfa/enroll/confirm',{enrollment_id:pending.enrollment_id,code:totp(pending.secret)},headers);
 assert.equal(complete.recovery_codes.length,8);assert.equal(new Set(complete.recovery_codes).size,8);
 assert.equal((await request.get(base+'/api/auth/me',{headers})).status(),401,'Enrollment invalidates primary pair');
 factors.set(email,complete.recovery_codes.slice());
}
function nextCode(email){const codes=factors.get(email);assert(codes?.length>0,'Private fixture factor budget exhausted');return codes.shift();}
async function apiLogin(request,base,email,password){
 await enroll(request,base,email,password);
 const challenge=await checked(request,base+'/api/auth/login',{email,password},undefined,202);assert(!('token'in challenge));
 const pair=await checked(request,base+'/api/auth/mfa/login/verify',{challenge:challenge.challenge,recovery_code:nextCode(email)});
 assert.equal(typeof pair.token,'string');assert.equal(typeof pair.refresh_token,'string');return pair;
}
async function formLogin(page,base,email,password,audience){
 await enroll(page.request,base,email,password);
 await page.goto(base+'/login-'+audience,{waitUntil:'domcontentloaded'});
 await page.locator('#loginForm input[name=email]').fill(email);await page.locator('#loginForm input[name=password]').fill(password);
 const primary=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login'&&r.request().method()==='POST');
 await page.locator('#loginForm button[type=submit]').click();assert.equal((await primary).status(),202);
 await page.locator('#mfa-login-factor').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>localStorage.getItem('mb_token')),null);
 await page.locator('#mfa-login-method').selectOption('recovery_code');await page.locator('#mfa-login-recovery').fill(nextCode(email));
 const verified=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/mfa/login/verify'&&r.request().method()==='POST');
 await page.locator('#mfa-login-factor button[type=submit]').click();const response=await verified;assert.equal(response.status(),200);
 const pair=await response.json();await page.waitForURL(audience==='gym'?'**/dashboard':'**/mi-plan');
 assert.equal(await page.evaluate(()=>localStorage.getItem('mb_token')),pair.token);return pair;
}
function erase(){for(const values of factors.values())values.fill('');factors.clear();}
module.exports={apiLogin,formLogin,erase};
