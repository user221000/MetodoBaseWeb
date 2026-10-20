/* Actual UI controller receives real HTTP DTOs; returns a body for explicit HTTP application. */
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');let input='';process.stdin.setEncoding('utf8');process.stdin.on('data',chunk=>{input+=chunk;assert.ok(input.length<524288);});
process.stdin.on('end',async()=>{try{const v=JSON.parse(input);if(v.mode==='parse_html'){let count=0;for(const match of v.html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)){if(/\bsrc\s*=|application\/ld\+json/.test(match[1]))continue;new vm.Script(match[2]);count++;}console.log(JSON.stringify({passed:true,inline_scripts:count}));return;}
  const sandbox=vm.createContext({Date});vm.runInContext(fs.readFileSync('web/static/js/nutrition35.js','utf8'),sandbox);const N=sandbox.Nutrition35,handle=Object.freeze({revision:1});let sent=null;
  const read=async()=>{if(v.read_status&&v.read_status!==200)throw Object.assign(Error('Synthetic HTTP rejection'),{status:v.read_status,code:v.read_code});return v.profile;};
  const api={check:h=>assert.equal(h,handle),session:async()=>({handle}),verify:async h=>assert.equal(h,handle),catalog:async()=>v.catalog,personalCatalog:async()=>v.catalog,client:read,personal:read,update:async(_id,body)=>{sent=body;return {success:true};},savePersonal:async body=>{sent=body;return {message:'Perfil actualizado correctamente'};}};
  const page=N.create({api,kind:v.kind});await page.load(v.kind==='personal'?null:v.profile.id_cliente||'synthetic-invalid');
  if(v.mode==='weight'){await page.save({peso_kg:76,restricciones_nutricionales:v.profile.restricciones_nutricionales});assert.equal(Object.hasOwn(sent,'restricciones_nutricionales'),false);}
  if(v.mode==='report'){page.edit(true);page.change('status','reported');page.change('other',true);await page.save({},true);assert.equal(sent.restricciones_nutricionales.allergies.status,'reported');}
  let blocked=false;try{page.requireAutomation();}catch{blocked=true;}
  console.log(JSON.stringify({passed:true,phase:page.view().phase,blocked,body:sent}));
}catch(e){console.error(JSON.stringify({class:e.name,message:e.message}));process.exitCode=1;}});
