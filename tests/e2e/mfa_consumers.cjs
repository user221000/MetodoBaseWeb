/* Mounted consumers and the real API instance; synthetic transports only, not HTTP31. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),Module=require('node:module');
const prefix=fs.readFileSync(path.join(__dirname,'mfa_api.cjs'),'utf8').split('const tests=[];')[0];
const shared=new Module(__filename,module);shared.filename=__filename;shared.paths=module.paths;shared._compile(prefix+'\nmodule.exports={fixture,pair,old,other};',__filename);
const {fixture,other}=shared.exports,root=process.env.MFA_CONSUMER_SOURCE_ROOT||path.join(__dirname,'../..');
class Element{
 constructor(tag='div',id=''){this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.checked=false;this.dataset={};this.listeners={};this.classList={toggle(){}};this.style={};}
 append(...items){this.children.push(...items);return this;}appendChild(item){this.append(item);return item;}replaceChildren(...items){this.children=items;this.textContent='';}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}async fire(name,event={}){for(const fn of this.listeners[name]||[])await fn({preventDefault(){},target:this,...event});}
 reset(){for(const item of Object.values(this.fields||{}))item.value='';}focus(){}select(){}scrollIntoView(){}
}
const tick=async()=>{for(let index=0;index<25;index++)await new Promise(resolve=>setImmediate(resolve));};
const held=()=>{let resolve;const promise=new Promise(yes=>resolve=yes);return{promise,resolve};};
const me={id:'synthetic-owner',tipo:'gym',role:'owner',session_version:0,permissions:[['read','team'],['invite','team'],['update_role','team'],['remove','team']]};
const team=()=>({members:[{id:'synthetic-member',nombre:'Canary',apellido:'Member',email:'member@example.invalid',role:'viewer',invitation_status:'active',can_change_role:true,can_resend:true,can_remove:true}],assignable_roles:['admin','viewer'],capabilities:{invite:true,revoke_preserves_identity:true},total:1,pending_invitations:0});
const sub=()=>({status:'none',plan:null,provider:null,max_clientes:10});
function mounted(kind,transport){
 const e=fixture(async(url,options)=>url==='/api/auth/me'?Response.json(me):transport(url,options)),nodes=new Map(),redirects=[];
 const get=id=>{if(!nodes.has(id))nodes.set(id,new Element('div',id));return nodes.get(id);};
 const form=get('team-invite-form');form.fields=Object.fromEntries(['nombre','apellido','email','role'].map(name=>[name,new Element('input',name)]));form.elements={namedItem:name=>form.fields[name]};
 const plans=['standard','gym_comercial','clinica'].map(plan=>{const item=new Element('button');item.dataset.plan=plan;return item;});
 const providers=['stripe','mercadopago'].map(value=>{const item=new Element('input');item.value=value;item.checked=value==='stripe';return item;});
 const document={getElementById:id=>id==='professional-context'?null:get(id),createElement:tag=>new Element(tag),
  querySelector:selector=>selector.includes('billing-provider')?providers.find(item=>item.checked):null,
  querySelectorAll:selector=>selector==='.btn-plan'?plans:selector.includes('billing-provider')?providers:selector.includes('team-invite-form')?Object.values(form.fields):selector.includes('team-management')?[...Object.values(form.fields),get('team-refresh')]:[]};
 const location={origin:'http://127.0.0.1:8802',search:'',assign:value=>redirects.push(value),replace:value=>redirects.push(value)};
 Object.assign(e.context,{document,location,URL,history:{replaceState(){}},navigator:{clipboard:{writeText:async()=>{}}},confirm:()=>true,crypto:{randomUUID:()=> 'synthetic-idempotency-key'}});
 e.window.location=location;vm.runInContext(fs.readFileSync(path.join(root,'web/static/js',kind==='team'?'equipo.js':'gym-suscripcion.js'),'utf8'),e.context);
 return{...e,nodes,get,form,plans,providers,redirects};
}
const tests=[],test=(name,body)=>tests.push({name,body});
test('Team data and invitation inputs clear synchronously on an in-document account change',async()=>{
 const e=mounted('team',async()=>Response.json(team()));await tick();assert.equal(e.get('team-members').children.length,1);e.form.fields.email.value='old@example.invalid';e.get('team-share-link').value='synthetic-private-link';e.api.saveTokens(other);
 assert.equal(e.get('team-members').children.length,0);assert.equal(e.form.fields.email.value,'');assert.equal(e.get('team-share-link').value,'');assert.equal(e.get('team-management').hidden,true);
});
test('A held team mutation never repaints its link or account data after replacement',async()=>{
 const gate=held(),e=mounted('team',async url=>url==='/api/gym/team'?Response.json(team()):url.includes('step-up')?Response.json({grant:'g'.repeat(43),expires_at:'2099-10-19T18:00:00Z',action:'team.invite',method:'POST',path:'/api/gym/team/invite',single_use:true}):gate.promise);await tick();
 Object.assign(e.form.fields.nombre,{value:'Synthetic'});e.form.fields.email.value='synthetic@example.invalid';e.form.fields.role.value='viewer';e.form.fire('submit');await tick();e.api.saveTokens(other);
 gate.resolve(Response.json({success:true,delivery_status:'not_confirmed',invitation_link:'http://127.0.0.1:8802/auth/accept-invite#token='+'t'.repeat(43),expires_at:'2099-10-19T18:00:00Z'}));await tick();
 assert.equal(e.get('team-share-link').value,'');assert.equal(e.get('team-members').children.length,0);assert.equal(e.get('team-share').hidden,true);
});
test('The observed team invitation DTO stays fixed while canonical verification is pending',async()=>{
 const e=mounted('team',async url=>url==='/api/gym/team'?Response.json(team()):url.includes('step-up')?Response.json({detail:{code:'mfa_action_forbidden'}},{status:403}):Response.json({}));await tick();
 e.form.fields.nombre.value='First';e.form.fields.email.value='first@example.invalid';e.form.fields.role.value='viewer';e.form.fire('submit');e.form.fields.nombre.value='Later';await tick();
 const request=e.calls.find(call=>call.url.includes('step-up'));assert.equal(JSON.parse(request.body).body.nombre,'First');
});
test('Team ambiguous mutation blocks another intent until explicit readback',async()=>{
 const e=mounted('team',async url=>url==='/api/gym/team'?Response.json(team()):url.includes('step-up')?Response.json({grant:'g'.repeat(43),expires_at:'2099-10-19T18:00:00Z',action:'team.invite',method:'POST',path:'/api/gym/team/invite',single_use:true}):Promise.reject(new TypeError('Synthetic lost response')));await tick();e.form.fields.nombre.value='Synthetic';e.form.fields.email.value='synthetic@example.invalid';e.form.fields.role.value='viewer';e.form.fire('submit');await tick();
 const before=e.calls.filter(call=>call.url.includes('step-up')).length;e.form.fire('submit');await tick();assert.equal(e.calls.filter(call=>call.url.includes('step-up')).length,before);assert.match(e.get('team-feedback').textContent,/incierto/);await e.get('team-refresh').fire('click');await tick();assert.equal(e.form.fields.email.disabled,false);
});
function billingTransport(url){return Response.json(url.endsWith('/subscription')?sub():url.endsWith('/config')?{stripe_configured:true,mercadopago_configured:false,plans:{}}:{payments:[{created_at:'2026-10-19',amount_cents:100,currency:'MXN',status:'Canary',plan:'standard'}]});}
test('Billing payments and controls clear synchronously on account replacement',async()=>{const e=mounted('billing',async url=>billingTransport(url));await tick();assert.equal(e.get('payments-tbody').children.length,1);e.api.saveTokens(other);assert.equal(e.get('payments-tbody').children.length,0);assert.equal(e.get('sub-plan-name').textContent,'Por confirmar');assert.equal(e.plans[0].disabled,true);});
test('A held checkout cannot navigate a new account to its old provider session',async()=>{
 const gate=held(),e=mounted('billing',async url=>url.includes('step-up')?Response.json({grant:'g'.repeat(43),expires_at:'2099-10-19T18:00:00Z',action:'billing.checkout',method:'POST',path:'/api/billing/checkout',single_use:true}):url.endsWith('/checkout')?gate.promise:billingTransport(url));await tick();e.plans[0].fire('click');await tick();e.api.saveTokens(other);gate.resolve(Response.json({url:'https://checkout.stripe.com/synthetic'}));await tick();assert.deepEqual(e.redirects,[]);assert.equal(e.get('payments-tbody').children.length,0);
});
test('Billing ambiguous checkout conserves the original key across explicit readback and retry',async()=>{
 let count=0;const e=mounted('billing',async url=>url.includes('step-up')?Response.json({grant:'g'.repeat(43),expires_at:'2099-10-19T18:00:00Z',action:'billing.checkout',method:'POST',path:'/api/billing/checkout',single_use:true}):url.endsWith('/checkout')?(++count===1?Promise.reject(new TypeError('Synthetic timeout')):Response.json({url:'https://checkout.stripe.com/synthetic'})):billingTransport(url));await tick();e.plans[0].fire('click');await tick();assert.equal(e.plans[0].disabled,true);e.plans[0].fire('click');await tick();assert.equal(count,1);await e.get('btn-refresh-billing').fire('click');await tick();e.plans[0].fire('click');await tick();const requests=e.calls.filter(call=>call.url.endsWith('/checkout'));assert.equal(requests.length,2);assert.equal(requests[0].headers['Idempotency-Key'],requests[1].headers['Idempotency-Key']);assert.equal(e.redirects.length,1);
});
test('Storage faults clear already displayed team data without a new click',async()=>{
 const e=mounted('team',async()=>Response.json(team()));await tick();e.context.localStorage.getItem=()=>{throw new Error('Synthetic SecurityError');};e.window.dispatchEvent(Object.assign(new Event('storage'),{key:'mb_token'}));assert.equal(e.get('team-members').children.length,0);assert.equal(e.get('team-management').hidden,true);
});
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,error_class:error.name});}}console.log(JSON.stringify({scope:'Mounted team/billing consumers with actual API and RAM transport; no HTTP31/browser/provider claim',passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})();
