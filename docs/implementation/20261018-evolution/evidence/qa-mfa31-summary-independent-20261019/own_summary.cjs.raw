/* Independent mounted actual-account rendering canaries, RAM HTTP only. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const ROOT=process.env.MFA_SUMMARY_REVIEW_ROOT||'F:/mb-mfa31-qa-20261019',base=path.join(ROOT,'tests/e2e');
const raw=fs.readFileSync(path.join(base,'mfa_api.cjs'),'utf8'),marker='const tests=[];';assert.equal(raw.split(marker).length,2);
const scenarios=String.raw`
class Element {
 constructor(tag='div'){this.tagName=tag.toLowerCase();this.children=[];this._text='';this.listeners=new Map();this.value='';this.hidden=false;this.disabled=false;this.inert=false;this.options=[];}
 set textContent(value){this._text=String(value);this.children=[];}get textContent(){return this._text+this.children.map(x=>x.textContent).join(' ');}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=[...items];this._text='';}addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,[]);this.listeners.get(name).push(fn);}focus(){this.focused=true;}setAttribute(name,value){this[name]=String(value);}remove(){}
}
const kitCodes=()=>Array.from({length:8},(_,i)=>String(i).padStart(2,'0')+'R'.repeat(20));
function mounted(enabled){
 const ack={confirm:false,regenerate:false,revoke:false};
 const e=fixture(async(url,options)=>{
  if(url==='/api/auth/me')return Response.json({id:'synthetic-actor',tipo:'gym',role:'owner',team_gym_id:null,session_version:1});
  if(url==='/api/auth/mfa/status')return Response.json({enabled,pending:false,recovery_codes_remaining:enabled?8:0,methods:['totp','recovery_code'],required_for_privileged_actions:true,totp_period_seconds:30,challenge_lifetime_seconds:300});
  if(url==='/api/auth/mfa/reauth')return Response.json({reauthentication_token:'p'.repeat(43),expires_at:'2099-10-19T18:00:00Z'});
  if(url==='/api/auth/mfa/enroll')return Response.json({enrollment_id:'e'.repeat(32),secret:'A'.repeat(32),otpauth_uri:'otpauth://totp/synthetic',shown_once:true,expires_at:'2099-10-19T18:00:00Z'});
  if(url==='/api/auth/mfa/enroll/confirm'){ack.confirm=true;return Response.json({success:true,enabled:true,shown_once:true,reauthenticate:true,recovery_codes:kitCodes()});}
  if(url==='/api/auth/mfa/recovery-codes/regenerate'){ack.regenerate=true;return Response.json({success:true,shown_once:true,reauthenticate:true,recovery_codes:kitCodes()});}
  if(url==='/api/auth/mfa/revoke'){ack.revoke=true;return Response.json({success:true,enabled:false,reauthenticate:true});}
  throw Error('Unexpected synthetic transport route');
 });
 const root=new Element('section'),nodes=new Map();
 const ids=['mfa-account-primary','mfa-account-status','mfa-account-seed','mfa-account-confirm','mfa-account-kit','mfa-account-google-cancel','mfa-account-google','mfa-account-submit','mfa-account-summary','mfa-account-existing-factor','mfa-account-action','mfa-account-method','mfa-account-factor','mfa-account-password','mfa-account-new-code','mfa-account-refresh','mfa-account-discard','mfa-account-google-status'];
 for(const id of ids){const item=new Element(id.includes('password')||id.includes('factor')&&!id.includes('existing')||id.includes('new-code')?'input':id==='mfa-account-action'||id==='mfa-account-method'?'select':['mfa-account-submit','mfa-account-refresh','mfa-account-discard','mfa-account-google-cancel'].includes(id)?'button':'div');item.id=id;nodes.set(id,item);}
 nodes.get('mfa-account-action').options=['enroll','regenerate','revoke'].map(value=>({value,disabled:false}));
 root.querySelector=selector=>nodes.get(selector.slice(1));root.querySelectorAll=selector=>[...nodes.values()].filter(item=>selector.split(',').includes(item.tagName));
 e.context.document={getElementById:id=>id==='mfa-account'?root:null,createElement:tag=>new Element(tag)};
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../../web/static/js/mfa-ui.js'),'utf8'),e.context);
 const controller=e.window.MfaUI.mountAccount({loginUrl:'/login-gym',googleClientId:null});return{...e,root,nodes,controller,ack};
}
async function settled(e){for(let i=0;i<20&&!e.nodes.get('mfa-account-status').textContent.includes('Estado actualizado');i++)await new Promise(resolve=>setImmediate(resolve));assert.match(e.nodes.get('mfa-account-summary').textContent,/códigos de recuperación disponibles/);}
const tests=[];const test=(name,body)=>tests.push({name,body});
for(const action of ['confirm','regenerate','revoke'])test('Mounted '+action+' ACK closes its session and removes the previously current MFA summary',async()=>{
 const e=mounted(action!=='confirm');await settled(e);const summary=e.nodes.get('mfa-account-summary'),previous=summary.textContent;assert.equal(e.values.get('mb_token'),old.token);
 if(action==='confirm'){assert.equal(await e.controller.mutate('enroll',{password:'synthetic'},{}),true);assert.equal(await e.controller.confirm('123456'),true);}else assert.equal(await e.controller.mutate(action,{password:'synthetic'},{recovery_code:'R'.repeat(22)}),true);
 assert.equal(e.ack[action],true);assert.equal(e.values.has('mb_token'),false);assert.equal(e.values.has('mb_refresh_token'),false);
 if(action==='revoke'){assert.equal(e.nodes.get('mfa-account-kit').textContent.includes('R'.repeat(20)),false);assert.match(e.nodes.get('mfa-account-status').textContent,/desactivada/);}else{const kit=e.nodes.get('mfa-account-kit');assert.equal(kit.children.find(child=>child.tagName==='ol').children.length,8);assert.match(e.nodes.get('mfa-account-status').textContent,/Cambio confirmado/);}
 assert.notEqual(summary.textContent,previous,'A confirmed change and closed session cannot retain the prior queried state as the current MFA summary');
 assert.equal(e.calls.filter(call=>call.url==='/api/auth/me').length,1,'No read of old actor after confirmed local close');
});
(async()=>{const results=[];for(const item of tests){try{await item.body();results.push({case:item.name,passed:true});}catch(error){results.push({case:item.name,passed:false,error_class:error.name,criterion:error.message==='A confirmed change and closed session cannot retain the prior queried state as the current MFA summary'?'prior-summary-not-retained':'earlier-control'});}}console.log(JSON.stringify({scope:'Actual MfaUI.mountAccount and actual central api.js. Minimal DOM/explicit RAM HTTP only; not a second browser/PG/provider claim.',total:results.length,passed:results.filter(x=>x.passed).length,results},null,2));if(results.some(x=>!x.passed))process.exitCode=1;})();
`;
const candidate=new Module(path.join(base,'qa_mfa_summary_independent.cjs'),module);candidate.filename=path.join(base,'qa_mfa_summary_independent.cjs');candidate.paths=module.paths;candidate._compile(raw.slice(0,raw.indexOf(marker))+scenarios,candidate.filename);
