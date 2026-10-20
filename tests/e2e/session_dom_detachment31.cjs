/* Actual session-shell and affected consumer code over a connected minimal DOM.
 * Reproduces the four privately observed native TypeError call sites plus fences.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),Module=require('node:module'),assert=require('node:assert/strict');
const root=process.env.DETACH31_SOURCE_ROOT||path.resolve(__dirname,'../..');
const file=path.join(__dirname,'session_shell31.cjs'),prefix=fs.readFileSync(file,'utf8').split('const results=[];')[0],moduleFixture=new Module(file,module);moduleFixture.filename=file;moduleFixture.paths=module.paths;moduleFixture._compile(prefix+'\nmodule.exports={fixture};',file);
const framing=fs.readFileSync(path.join(__dirname,'browser_compat31.cjs'),'utf8'),{balanced}=vm.runInNewContext(framing.slice(framing.indexOf('function skipString('),framing.indexOf('const fixtureName='))+'\n({balanced})',{assert});
const defer=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return{promise,resolve,reject};};
function fixture(){
 const f=moduleFixture.exports.fixture(),prototype=Object.getPrototypeOf(f.field),oldMatches=prototype.matches;prototype.matches=function(selector){const match=/^\[data-export-count="([^"]+)"\]$/.exec(selector);return match?this.dataset?.exportCount===match[1]:oldMatches.call(this,selector);};prototype.removeAttribute=function(key){delete this[key];};
 const el=(tag,id,parent=f.main)=>{const node=f.el(tag,id,parent);node.style={};node.dataset={};return node;};
 return{...f,el,eval:source=>vm.runInContext(source,f.sandbox)};
}
function script(name){return fs.readFileSync(path.join(root,name),'utf8');}
function body(template,marker){return[...script(template).matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes(marker))[1];}
const tests=[],test=(name,run)=>tests.push({name,run});
test('Branding receives own-session boundary before shell retirement and clears RAM synchronously',async()=>{
 const f=fixture(),gate=defer();for(const id of['gym-logo-section','logo-picker','logo-input','logo-reload','logo-img','logo-placeholder','logo-upload-status','logo-error','btn-guardar','cfg-nombre','cfg-direccion','cfg-ciudad','cfg-estado','cfg-telefono','cfg-web','cfg-rfc','cfg-instagram','cfg-facebook','cfg-tiktok','planes-grid','planes-loading','successMsg','errorMsg'])f.el('input',id);
 f.sandbox.Api.auth={me:()=>gate.promise};f.sandbox.Api.gym={getProfile(){throw Error('Late I/O forbidden');}};f.eval(script('web/static/js/gym-branding.js'));assert.equal(f.sandbox.GymBranding.isActive(),true);f.change();assert.equal(f.sandbox.GymBranding.isActive(),false);await f.flush();assert.equal(f.document.getElementById('gym-logo-section'),null);
});
test('Branding pagehide after an already retired main is idempotent and does not dereference global form fields',async()=>{
 const f=fixture(),gate=defer();for(const id of['gym-logo-section','logo-picker','logo-input','logo-reload','logo-img','logo-placeholder','logo-upload-status','logo-error','btn-guardar','cfg-nombre','cfg-direccion','cfg-ciudad','cfg-estado','cfg-telefono','cfg-web','cfg-rfc','cfg-instagram','cfg-facebook','cfg-tiktok','planes-grid','planes-loading','successMsg','errorMsg'])f.el('input',id);
 f.sandbox.Api.auth={me:()=>gate.promise};f.eval(script('web/static/js/gym-branding.js'));f.change();await f.flush();assert.equal(f.document.getElementById('cfg-nombre'),null);assert.doesNotThrow(()=>f.sandbox.dispatchEvent({type:'pagehide'}));assert.equal(f.sandbox.GymBranding.isActive(),false);
});
test('Privacy pagehide after shell retirement still discards controls/cache without global DOM lookup failure',async()=>{
 const f=fixture(),section=f.el('section','personal-data-section'),gate=defer();for(const id of['privacy-status','privacy-error','privacy-start','privacy-next','privacy-again','privacy-restart','privacy-progress','privacy-counts','privacy-content-warning'])f.el('div',id,section);
 for(const name of['profiles','plans','measurements','purchases','generation_requests','personal_diary','member_links','progress_consents']){const node=f.el('dd','count-'+name,section);node.dataset.exportCount=name;}
 f.sandbox.Api.usuario={contexto:()=>gate.promise,validarContexto(){}};f.eval(script('web/static/js/usuario-privacidad.js'));f.change();await f.flush();assert.equal(f.document.getElementById('privacy-progress'),null);assert.doesNotThrow(()=>f.sandbox.dispatchEvent({type:'pagehide'}));
});
test('Settings price-list rejection after shell retirement is ignored without TypeError or replacement data',async()=>{
 const f=fixture(),gate=defer();f.el('div','planes-loading');f.sandbox.GymBranding={verifyAccount:()=>gate.promise,isActive:()=>false};const source=body('web/templates/configuracion.html','const DURACION_ICONS'),start=source.indexOf('(async () => {'),open=source.indexOf('(',start),end=balanced(source,open);const pending=f.eval(source.slice(start,end)+'()');f.change();await f.flush();gate.reject(Object.assign(Error('Changed'),{code:'session_changed'}));await pending;assert.equal(f.document.getElementById('planes-loading'),null);
});
test('Personal catalog rejection after shell retirement is ignored without TypeError or HTML reinsertion',async()=>{
 const f=fixture(),gate=defer();f.el('div','catalogo-container');f.sandbox.nutritionPersonal={readCatalog:()=>gate.promise,view:()=>({phase:'invalidated'}),check(){throw Object.assign(Error('Changed'),{code:'session_changed'});}};const source=body('web/templates/usuario_perfil.html','async function loadCatalogo'),start=source.indexOf('async function loadCatalogo()'),end=balanced(source,source.indexOf('{',start));f.eval(source.slice(start,end));const pending=f.eval('loadCatalogo()');f.change();await f.flush();gate.reject(Object.assign(Error('Changed'),{code:'session_changed'}));await pending;assert.equal(f.document.getElementById('catalogo-container'),null);
});
test('Personal initialization stops after invalidated profile load before catalog or form attachment',async()=>{
 const f=fixture(),gate=defer();for(const id of['form-perfil','nutrition35-personal','btn-guardar','excluidos-tags','catalogo-container'])f.el('div',id);let catalogCalls=0;
 f.sandbox.Nutrition35={mount(){return{load:()=>gate.promise,view:()=>({phase:'invalidated'}),readCatalog(){catalogCalls++;return Promise.reject(Object.assign(Error('Changed'),{code:'session_changed'}));}};}};const source=body('web/templates/usuario_perfil.html','async function loadCatalogo'),pending=f.eval(source);f.change();await f.flush();gate.resolve(null);await pending;assert.equal(catalogCalls,0);assert.equal(f.document.getElementById('form-perfil'),null);
});
(async()=>{const results=[];for(const row of tests){try{await row.run();results.push({case:row.name,passed:true});}catch(error){results.push({case:row.name,passed:false,error_class:error.name,frames:error.stack?.split('\n').slice(1,4)});}}console.log(JSON.stringify({scope:'Actual session-shell.js + affected source/inline functions in a connected minimal DOM. API awaits doubled; no actual Chrome/HTTP/SQL acceptance. Native observations remain separate.',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})();
