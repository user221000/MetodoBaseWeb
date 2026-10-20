'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),assert=require('node:assert/strict');
const root=process.env.DETACH31_SOURCE_ROOT,filename=path.join(root,'tests/e2e/session_dom_detachment31.cjs');
const raw=fs.readFileSync(path.join(__dirname,'author-canary.raw.cjs'),'utf8'),anchor='const tests=[],test=';
assert.equal(raw.split(anchor).length,2);const prefix=raw.slice(0,raw.indexOf(anchor));
const source=new Module(filename,module);source.filename=filename;source.paths=Module._nodeModulePaths(path.dirname(filename));
source._compile(prefix+'\nmodule.exports={fixture,script,body,defer,balanced};',filename);
const {fixture,script,body,defer,balanced}=source.exports;
const tick=async()=>{for(let i=0;i<35;i++)await Promise.resolve();};
const ids=['gym-logo-section','logo-picker','logo-input','logo-reload','logo-img','logo-placeholder','logo-upload-status','logo-error','btn-guardar','cfg-nombre','cfg-direccion','cfg-ciudad','cfg-estado','cfg-telefono','cfg-web','cfg-rfc','cfg-instagram','cfg-facebook','cfg-tiktok','planes-grid','planes-loading','successMsg','errorMsg'];
function branding(){const f=fixture();for(const id of ids)f.el('input',id);return f;}
const actor={id:'synthetic-owner',role:'owner',team_gym_id:null,session_version:1,permissions:[['update','gym_profile']]};
const cases=[],test=(name,run)=>cases.push({name,run});
test('Late verified account response cannot revive permission or fetch a retired branding profile',async()=>{
 const f=branding(),gate=defer(),old=f.document.getElementById('cfg-nombre');let calls=0;
 f.sandbox.Api.auth={me:()=>gate.promise};f.sandbox.Api.gym={getProfile(){calls++;throw Error('Forbidden late profile read');}};
 f.eval(script('web/static/js/gym-branding.js'));f.change();await f.flush();gate.resolve(actor);await tick();
 assert.equal(calls,0);assert.equal(f.sandbox.GymBranding.isActive(),false);assert.equal(f.sandbox.GymBranding.canUpdate(),false);assert.equal(old.value,'');assert.equal(old.disabled,true);
});
test('Connected branding still loads its permitted account and synchronously clears authority at the boundary',async()=>{
 const f=branding();let calls=0;f.sandbox.Api.auth={me:async()=>actor};f.sandbox.Api.gym={getProfile:async()=>{calls++;return{gym_id:actor.id,has_private_logo:false,logo_url:'',nombre_negocio:'Synthetic public label'};}};
 f.eval(script('web/static/js/gym-branding.js'));await tick();const old=f.document.getElementById('cfg-nombre'),save=f.document.getElementById('btn-guardar');
 assert.equal(calls,1);assert.equal(old.value,'Synthetic public label');assert.equal(save.disabled,false);assert.equal(f.sandbox.GymBranding.canUpdate(),true);
 f.change();assert.equal(old.value,'');assert.equal(save.disabled,true);assert.equal(f.sandbox.GymBranding.canUpdate(),false);await f.flush();
});
test('A retired branding consumer cannot mutate replacement nodes with reused DOM IDs on pagehide',async()=>{
 const f=branding(),gate=defer();f.sandbox.Api.auth={me:()=>gate.promise};f.eval(script('web/static/js/gym-branding.js'));f.change();await f.flush();
 const replacement=f.el('input','cfg-nombre');replacement.value='Replacement sentinel';replacement.disabled=false;
 assert.doesNotThrow(()=>f.sandbox.dispatchEvent({type:'pagehide'}));assert.equal(replacement.value,'Replacement sentinel');assert.equal(replacement.disabled,false);await f.flush();
});
test('Retired privacy pagehide only touches owned controls, not replacement DOM with the same IDs',async()=>{
 const f=fixture(),section=f.el('section','personal-data-section'),gate=defer();for(const id of['privacy-status','privacy-error','privacy-start','privacy-next','privacy-again','privacy-restart','privacy-progress','privacy-counts','privacy-content-warning'])f.el('div',id,section);
 for(const name of['profiles','plans','measurements','purchases','generation_requests','personal_diary','member_links','progress_consents']){const node=f.el('dd','count-'+name,section);node.dataset.exportCount=name;}
 f.sandbox.Api.usuario={contexto:()=>gate.promise,validarContexto(){throw Error('Forbidden context read');}};f.eval(script('web/static/js/usuario-privacidad.js'));f.change();await f.flush();
 const replacement=f.el('section','personal-data-section'),nodes=[];for(const id of['privacy-progress','privacy-counts','privacy-content-warning']){const node=f.el('div',id,replacement);node.hidden=false;node.disabled=false;nodes.push(node);}
 assert.doesNotThrow(()=>f.sandbox.dispatchEvent({type:'pagehide'}));for(const node of nodes){assert.equal(node.hidden,false);assert.equal(node.disabled,false);}await f.flush();
});
test('Catalog failure after physical detach in ready phase cannot replace a later DOM catalog',async()=>{
 const f=fixture(),gate=defer(),old=f.el('div','catalogo-container');f.sandbox.catalogContainer=old;
 f.sandbox.nutritionPersonal={readCatalog:()=>gate.promise,view:()=>({phase:'ready'}),check(){}};
 const source=body('web/templates/usuario_perfil.html','async function loadCatalogo'),start=source.indexOf('async function loadCatalogo()'),end=balanced(source,source.indexOf('{',start));f.eval(source.slice(start,end));const pending=f.eval('loadCatalogo()');
 f.change();await f.flush();const replacement=f.el('div','catalogo-container');replacement.innerHTML='Replacement catalog sentinel';gate.reject(Error('Synthetic catalog rejection'));await pending;
 assert.equal(old.isConnected,false);assert.equal(replacement.innerHTML,'Replacement catalog sentinel');
});
test('Invalidation during catalog await permits detached callbacks but prevents late form registration',async()=>{
 const f=fixture(),catalog=defer();for(const id of['form-perfil','nutrition35-personal','btn-guardar','excluidos-tags','catalogo-container'])f.el('div',id);
 const form=f.document.getElementById('form-perfil'),save=f.document.getElementById('btn-guardar');let callbacks,phase='ready',calls=0;
 f.sandbox.Nutrition35={mount(node,options){callbacks=options;return{load:async()=>null,view:()=>({phase}),readCatalog(){calls++;return catalog.promise;},check(){if(phase!=='ready')throw Error('Context changed');}};}};
 const pending=f.eval(body('web/templates/usuario_perfil.html','async function loadCatalogo'));await tick();assert.equal(calls,1);phase='invalidated';f.change();await f.flush();
 assert.doesNotThrow(()=>callbacks.onInvalidated());assert.doesNotThrow(()=>callbacks.onView({busy:false,phase:'invalidated'}));catalog.reject(Error('Synthetic rejection'));await pending;
 assert.equal(form.isConnected,false);assert.equal(form.events.has('submit'),false);assert.equal(save.disabled,true);
});
(async()=>{const results=[];for(const item of cases){try{await item.run();results.push({case:item.name,passed:true});}catch(error){results.push({case:item.name,passed:false,error_class:error.name,frames:error.stack?.split('\n').slice(1,4)});}}
 const report={scope:'Independent minimal-DOM controls over actual source and session-shell; API awaits doubled. No Chrome, HTTP, SQL, actual session/RAM protocol or account-B adoption acceptance.',total:results.length,passed:results.filter(row=>row.passed).length,results};process.stdout.write(JSON.stringify(report,null,2)+'\n');if(report.total!==report.passed)process.exitCode=1;
})();
