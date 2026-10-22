'use strict';
// Test-side format observation only. This does NOT verify a signature or establish authority.
// All real authorization oracles remain HTTP/auth/MFA/cookie checks in the native driver.
function sessionVersion(token){
 const invalid=()=>new TypeError('Unexpected private test token format');
 if(typeof token!=='string'||!token||token.length>8192)throw invalid();
 const parts=token.split('.');
 if(parts.length!==2||! /^[A-Za-z0-9_-]+$/.test(parts[0])||!/^[a-f0-9]{64}$/.test(parts[1]))throw invalid();
 let value;
 try{
  const bytes=Buffer.from(parts[0],'base64url');
  if(bytes.toString('base64url')!==parts[0])throw invalid();
  value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 }catch{throw invalid();}
 if(!value||typeof value!=='object'||Array.isArray(value)||!Object.hasOwn(value,'sv')||!Number.isSafeInteger(value.sv)||value.sv<0)throw invalid();
 return value.sv;
}
module.exports=Object.freeze({sessionVersion});
