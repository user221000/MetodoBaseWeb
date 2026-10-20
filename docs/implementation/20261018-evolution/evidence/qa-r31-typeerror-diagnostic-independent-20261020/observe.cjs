'use strict';
const fs=require('node:fs'),path=require('node:path');
const origin='http://127.0.0.1:8802';
function safePath(value){try{const url=new URL(value),known=new Set(['/','/dashboard','/configuracion','/mi-plan','/mi-perfil','/login-gym','/login-usuario']);return url.origin===origin&&(known.has(url.pathname)||/^\/static\/js\/[A-Za-z0-9_.-]{1,80}\.js$/.test(url.pathname))&&!/[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/.test(url.pathname)?url.pathname:'[opaque]';}catch{return'[opaque]';}}
function frames(stack){return String(stack||'').split('\n').slice(1,25).flatMap(line=>{const match=/(https?:\/\/[^\s)]+):(\d+):(\d+)\)?$/.exec(line.trim());return match?[{script_path:safePath(match[1]),line:Number(match[2]),column:Number(match[3])}]:[];}).slice(0,10);}
function errorRecord(error,page,phase){const known=new Set(['TypeError','ReferenceError','Error','SecurityError','SyntaxError','RangeError','DOMException']);return{event:'pageerror',error_class:known.has(error.name)?error.name:'Other',phase:/^[a-z0-9_-]{1,64}$/.test(phase||'')?phase:'other',page_path:safePath(page.url()),frames:frames(error.stack)};}
module.exports={safePath,frames,errorRecord};
if(process.env.QA_OBSERVER_UNIT!=='1'){
 const target=process.env.QA_OBSERVATION_FILE;if(!target||!path.isAbsolute(target)||!fs.existsSync(path.dirname(target)))throw Error('Explicit private observer output required');
 const file=fs.openSync(target,'wx');const write=row=>fs.writeSync(file,JSON.stringify(row)+'\n');
 write({event:'observer_started',scope:'Passive pageerror/path/line observer; no message, query, body, headers, response or credentials recorded. No route/fetch/auth override.'});
 const deps=process.env.METODOBASE_E2E_DEPENDENCIES,pw=require(path.join(deps,'playwright-core')),launch=pw.chromium.launch.bind(pw.chromium);
 pw.chromium.launch=async(...args)=>{const browser=await launch(...args),create=browser.newContext.bind(browser);browser.newContext=async(...values)=>{const context=await create(...values);context.on('page',page=>{page.on('pageerror',error=>write(errorRecord(error,page,process.env.QA_DIAGNOSTIC_PHASE)));page.on('framenavigated',frame=>{if(frame===page.mainFrame())write({event:'navigation',phase:process.env.QA_DIAGNOSTIC_PHASE||'setup',page_path:safePath(frame.url())});});});return context;};return browser;};
 process.on('exit',()=>fs.closeSync(file));
}
