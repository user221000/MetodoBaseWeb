'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(process.argv[2]);
const frozenFixture='F:/mb-r12-controls-s/tests/e2e/member_link_consumers.cjs';
const fixtureSource=fs.readFileSync(frozenFixture,'utf8');
const prefix=fixtureSource.slice(0,fixtureSource.indexOf('const tests=[];'));
assert(prefix.length>0);
const box={require,__dirname:path.join(root,'tests/e2e'),Blob,URLSearchParams,setImmediate,console};
vm.createContext(box);vm.runInContext(prefix+'\nglobalThis.reviewHelpers={env,flush,deferred,capabilities,row,A,B,context};',box);
const {env,flush,deferred,capabilities,row,A,B,context}=box.reviewHelpers;
const tests=[];const test=(name,run)=>tests.push([name,run]);
const staticIDs={reader:['member-links-refresh','member-links-more','member-publication-pdf','member-link-leave'],
  professional:['professional-link-refresh','link-recipient','link-issue','link-issue-retry','professional-link-more'],invitation:['invitation-inspect','invitation-accept']};
function privacy(e){
  const section=e.doc.createElement('section'),control=e.doc.createElement('button');section.id='synthetic-privacy-context';control.id='synthetic-privacy-download';
  section.append(control);(e.ids['member-links-page']||e.ids['professional-link-page']||e.doc.body).append(section);
  return control;
}
async function ready(kind){
  const e=env(kind);if(kind==='professional')e.handlers.estado=()=>({client_id:'synthetic-client',capabilities,items:[{link_id:A,status:'active',version:7,invitation_status:'consumed',publication:{id:B,version:1,source_plan_id:41}}],next_after:null});
  const foreign=privacy(e);e.load();await flush();return {e,foreign};
}
function own(e,kind){
  const list=e.ids[kind==='reader'?'member-links-list':'professional-link-items'];
  return [...staticIDs[kind].map(id=>e.ids[id]),...(list?list.querySelectorAll('button,input,select'):[])];
}
function block(e,kind){
  const held=deferred(),entered=deferred();let pending;
  if(kind==='invitation'){
    e.handlers.inspeccionar=()=>{entered.resolve();return held.promise;};pending=e.ids['invitation-inspect'].fire('click');
  }else if(kind==='reader'){
    e.handlers.listar=()=>{entered.resolve();return held.promise;};pending=e.ids['member-links-refresh'].fire('click');
  }else{
    e.handlers.estado=()=>{entered.resolve();return held.promise;};pending=e.ids['professional-link-refresh'].fire('click');
  }
  const data=kind==='invitation'?{status:'pending',version:4,expires_at:'2026-10-26T18:00:00Z',link_id:A,context,can_accept:true}:
    kind==='reader'?{items:[row],next_after:null}:{client_id:'synthetic-client',capabilities,items:[],next_after:null};
  return {pending,entered,resolve:()=>held.resolve(data),reject:()=>held.reject(Error('SYNTHETIC_PRIVATE_LATE_DETAIL'))};
}
for(const kind of ['reader','professional','invitation']){
  test(kind+': concurrent privacy state survives successful member completion',async()=>{
    const {e,foreign}=await ready(kind);foreign.disabled=true;const prior=new Map(staticIDs[kind].map(id=>[id,e.ids[id].disabled]));
    const task=block(e,kind);await task.entered.promise;
    const controls=own(e,kind);assert(controls.length>=staticIDs[kind].length);for(const control of controls)assert.equal(control.disabled,true);
    foreign.disabled=false;task.resolve();await task.pending;
    assert.equal(foreign.disabled,false);for(const [id,value]of prior)assert.equal(e.ids[id].disabled,value);
  });
  for(const rejected of [false,true])test(kind+': invalidation blocks owned controls and discards late '+(rejected?'failure':'success'),async()=>{
    const {e,foreign}=await ready(kind);const task=block(e,kind);await task.entered.promise;
    const captured=own(e,kind);foreign.disabled=false;e.emit('metodobase-session-changed',{detail:{code:'session_changed'}});
    for(const control of captured)assert.equal(control.disabled,true);
    assert.equal(foreign.disabled,false);const calls=e.calls.length;
    if(rejected)task.reject();else task.resolve();await task.pending;
    for(const control of captured)assert.equal(control.disabled,true);
    assert.equal(e.calls.length,calls);assert.equal(foreign.disabled,false);assert(!e.text().includes('SYNTHETIC_PRIVATE_LATE_DETAIL'));
    if(kind==='invitation'){assert.equal(e.ids['invitation-details'].textContent,'');assert(e.ids['invitation-accept'].hidden);}
    else if(kind==='reader'){assert.equal(e.ids['member-links-list'].textContent,'');assert(e.ids['member-publication'].hidden);}
    else{assert.equal(e.ids['professional-link-items'].textContent,'');assert(e.ids['professional-link-controls'].hidden);assert.equal(e.ids['link-recipient'].value,'');}
  });
}
for(const kind of ['reader','professional'])test(kind+': detached dynamic controls cannot invoke old capabilities after idle invalidation',async()=>{
  const {e,foreign}=await ready(kind);const list=e.ids[kind==='reader'?'member-links-list':'professional-link-items'];
  const stale=list.querySelectorAll('button,input,select');assert(stale.some(n=>n.tagName==='BUTTON'));const calls=e.calls.length;
  e.emit('storage',{key:'mb_token'});for(const id of staticIDs[kind])assert.equal(e.ids[id].disabled,true);
  assert.equal(list.textContent,'');assert.equal(foreign.disabled,false);
  for(const n of stale)if(n.tagName==='BUTTON')await n.fire('click');
  assert.equal(e.calls.length,calls);assert.equal(list.textContent,'');
});
test('ownership function is mandatory and no global selector fallback is used',async()=>{
  const {e}=await ready('reader');
  assert.throws(()=>e.box.VinculosUI.setup({status:'member-links-status',error:'member-links-error',clear(){}}),/Owned link controls/);
  e.doc.querySelectorAll=()=>{throw Error('Global selector must not be used by a member consumer');};
  await e.ids['member-links-refresh'].fire('click');
  assert.equal(e.ids['member-links-error'].hidden,true);
});
(async()=>{const results=[];for(const[name,run]of tests){try{await run();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:error.stack});}}
const result={scope:'Independent offline VM controls/lifecycle only; shared actual frozen DOM/API fixture, no browser or HTTP acceptance.',root,
fixture_sha256:crypto.createHash('sha256').update(fixtureSource).digest('hex'),total:results.length,passed:results.filter(x=>x.passed).length,results};
console.log(JSON.stringify(result,null,2));if(result.passed!==result.total)process.exitCode=1;})();
