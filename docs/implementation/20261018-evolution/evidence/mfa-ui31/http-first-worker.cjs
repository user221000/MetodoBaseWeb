/* Private IPC bridge to in-process ASGI, never a public endpoint or report of secrets. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),readline=require('node:readline'),assert=require('node:assert/strict');
let sequence=0;const waiting=new Map(),lines=readline.createInterface({input:process.stdin});
lines.on('line',line=>{const value=JSON.parse(line),item=waiting.get(value.id);if(!item)return;waiting.delete(value.id);value.ok?item.resolve(value.data):item.reject(Error('Private bridge failure'));});
const rpc=value=>new Promise((resolve,reject)=>{const id=++sequence;waiting.set(id,{resolve,reject});process.stdout.write(JSON.stringify({type:'request',id,...value})+'\n');});
async function run(){
 const boot=await rpc({command:'bootstrap'}),values=new Map(),listeners=new Map(),counts={};
 const window={addEventListener:(name,fn)=>{if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(fn);},removeEventListener:(name,fn)=>listeners.get(name)?.delete(fn),dispatchEvent:event=>{for(const fn of listeners.get(event.type)||[])fn(event);return true;},location:{}};
 const context=vm.createContext({window,Event,Date,WeakMap,URLSearchParams,FormData,File,Blob,setTimeout,clearTimeout,
  localStorage:{getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)},
  fetch:async(url,options)=>{const reply=await rpc({command:'http',url,options});counts[reply.status]=(counts[reply.status]||0)+1;return new Response(reply.body,{status:reply.status,headers:reply.headers});}});
 for(const name of ['api.js','mfa-login.js','mfa-ui.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../../web/static/js',name),'utf8'),context);
 const api=vm.runInContext('Api',context);api.saveTokens(boot.pair);
 let seed=null,codes=null,kitShown=0,closed=null;
 const account=window.MfaUI.createAccount({onClear(){seed=null;},onSeed(value){seed=value;},onKit(values,handle){api.mfa.check(handle);codes=values.slice();closed=handle;kitShown++;},onClosedError(){}});
 await account.load();assert.equal(account.enabled,false);await account.mutate('enroll',{password:boot.password},{});assert.ok(seed);const code=await rpc({command:'totp',seed});
 if(boot.scenario==='late-ack'){
  const original=api.mfa.confirm;api.mfa.confirm=async(...args)=>{const reply=await original(...args);api.saveTokens(boot.other);return reply;};
  await account.confirm(code);assert.equal(kitShown,0);assert.equal(values.get('mb_token'),boot.other.token);const verified=await api.mfa.context();assert.equal(verified.me.id,boot.other_id);assert.equal(account.active,false);
  return{scenario:boot.scenario,passed:true,status_counts:counts,kit_shown:false,new_identity_preserved:true};
 }
 await account.confirm(code);assert.equal(kitShown,1);assert.equal(values.has('mb_token'),false);assert.equal(values.has('mb_refresh_token'),false);api.mfa.check(closed);assert.equal(codes.length,8);
 const login=window.MfaLogin.create({audience:'gym',onAuthenticated:handle=>api.mfa.verify(handle)});
 await login.primary('password',{email:boot.email,password:boot.password});assert.equal(login.phase,'factor');assert.equal(values.has('mb_token'),false);
 await login.verify(codes[0]);assert.equal(login.phase,'confirmed');const current=await api.mfa.context();assert.equal(current.me.id,boot.actor_id);const state=await api.mfa.status(current.handle);assert.equal(state.enabled,true);assert.equal(state.recovery_codes_remaining,7);
 const portal=await api.billing.portal();assert.equal(portal.url,'https://billing.stripe.com/synthetic-no-provider');
 const management=window.MfaUI.createAccount({onClear(){},onKit(values,handle){api.mfa.check(handle);codes=values.slice();closed=handle;kitShown++;},onClosedError(){}});
 await management.load();assert.equal(management.enabled,true);await management.mutate('regenerate',{password:boot.password},{recovery_code:codes[1]});assert.equal(kitShown,2);assert.equal(values.has('mb_token'),false);api.mfa.check(closed);
 const reentry=window.MfaLogin.create({audience:'gym',onAuthenticated:handle=>api.mfa.verify(handle)});await reentry.primary('password',{email:boot.email,password:boot.password});await reentry.verify(codes[0]);assert.equal(reentry.phase,'confirmed');
 let revoked=false;const security=window.MfaUI.createAccount({onClear(){},onClosed(handle){api.mfa.check(handle);revoked=true;},onClosedError(){}});await security.load();await security.mutate('revoke',{password:boot.password},{recovery_code:codes[1]});assert.equal(revoked,true);assert.equal(values.has('mb_token'),false);
 codes.fill('');seed=null;return{scenario:boot.scenario,passed:true,status_counts:counts,kit_generations:kitShown,local_closed:true};
}
let timeout;Promise.race([run(),new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('Private bridge timeout')),45000);})]).then(result=>{clearTimeout(timeout);process.stdout.write(JSON.stringify({type:'result',...result})+'\n');lines.close();},error=>{clearTimeout(timeout);process.stdout.write(JSON.stringify({type:'result',passed:false,error_class:error.name})+'\n');lines.close();process.exitCode=1;});
