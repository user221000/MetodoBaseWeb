/* Actual allowlisted registration copy; no account/provider traffic. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({window:{}});
vm.runInContext(fs.readFileSync('web/static/js/mfa-login.js','utf8'),context);
const untrusted='untrusted@example.invalid';
const result=context.window.MfaLogin.message({code:'registration_invalid',status:400,message:untrusted,detail:untrusted});
for(const word of ['cuenta','correo','nombre','contraseña'])assert.ok(result.includes(word));
assert.ok(!result.includes(untrusted));assert.ok(!/registrad|existe/i.test(result));
console.log(JSON.stringify({scope:'Actual registration message formatter; no login or provider',passed:1,total:1}));
