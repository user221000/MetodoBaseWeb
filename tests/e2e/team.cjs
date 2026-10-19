/* R11 browser contracts use real local pages and intercepted synthetic APIs. */
const {chromium}=require('playwright-core');
const {AxeBuilder}=require('@axe-core/playwright');
const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path');
const base=process.env.METODOBASE_E2E_URL || 'http://127.0.0.1:8765';
if(!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base))throw Error('Only a local synthetic server is allowed');
const out=path.resolve(__dirname,'../../docs/implementation/20261018-evolution/evidence/ux');
const ownerPermissions=[['read','dashboard'],['read','cliente'],['create','cliente'],['update','cliente'],['delete','cliente'],['read','plan'],['create','plan'],['read','billing'],['update','gym_profile'],['read','team'],['invite','team'],['remove','team'],['update_role','team']];
const viewerPermissions=[['read','dashboard'],['read','cliente'],['read','plan']];
const report={scope:'Local synthetic browser; no email/provider connection; no real invitations',checks:[],screens:[],errors:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844}});
  await context.route('**/*',route=>route.request().url().startsWith(base) ? route.continue() : route.abort());
  await context.addInitScript(()=>{if(!sessionStorage.getItem('synthetic-initialized')){localStorage.setItem('mb_token','synthetic-owner-token');localStorage.setItem('mb_tipo','gym');sessionStorage.setItem('synthetic-initialized','1');}});
  const page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
  let actor={id:'owner',tipo:'gym',role:'owner',nombre:'Synthetic Owner',permissions:ownerPermissions};
  const member={id:'pending',email:'professional@example.invalid',nombre:'Professional',apellido:'Synthetic',role:'viewer',role_display:'Solo lectura',activo:false,is_pending:true,invitation_status:'pending',invitation_expires_at:new Date(Date.now()+86400000).toISOString(),can_change_role:true,can_resend:true,can_remove:true};
  let team={members:[{id:'owner',email:'owner@example.invalid',nombre:'Owner',role:'owner',activo:true,invitation_status:'active'},member],total:2,pending_invitations:1,assignable_roles:['admin','nutriologo','viewer'],capabilities:{invite:true,change_roles:true,remove_members:true,revoke_preserves_identity:true}};
  const calls=[];let infoState='pending',canAccept=true,accepts=0,infoMalformed=false;
  function invitation(char='n'){return {success:true,message:'Invitación creada.',delivery_status:'not_confirmed',invitation_token:char.repeat(43),invitation_link:base+'/auth/accept-invite#token='+char.repeat(43),expires_at:new Date(Date.now()+86400000).toISOString()};}
  await page.route('**/api/**',route=>{
   const request=route.request(), endpoint=new URL(request.url()).pathname;
   calls.push({endpoint,method:request.method(),body:request.postDataJSON(),url:request.url(),authorization:request.headers().authorization || null});
   if(endpoint==='/api/auth/me')return route.fulfill({json:actor});
   if(endpoint==='/api/usuario/perfil')return route.fulfill({json:{nombre:'Personal Profile',email:'professional@example.invalid',peso_kg:73,edad:30,estatura_cm:170,sexo:'M',objetivo:'mantenimiento',nivel_actividad:'leve',alimentos_excluidos:[]}});
   if(endpoint==='/api/clientes')return route.fulfill({json:{clientes:[],total:0}});
   if(endpoint==='/api/auth/logout')return route.fulfill({json:{message:'Sesión cerrada'}});
   if(endpoint==='/api/gym/team' && request.method()==='GET')return route.fulfill({json:team});
   if(endpoint==='/api/gym/team/invite')return route.fulfill({json:invitation('n')});
   if(endpoint.endsWith('/resend-invite'))return route.fulfill({json:invitation('r')});
   if(endpoint.endsWith('/role')){member.role=request.postDataJSON().role;return route.fulfill({json:member});}
   if(endpoint==='/api/gym/team/pending' && request.method()==='DELETE'){team={...team,members:team.members.filter(row=>row.id!=='pending'),total:1,pending_invitations:0};return route.fulfill({json:{success:true,status:'revoked'}});}
   if(endpoint==='/api/auth/invite-info'){
    if(infoMalformed)return route.fulfill({contentType:'text/html',body:'<html>Unavailable</html>'});
    if(infoState==='missing')return route.fulfill({status:404,json:{detail:{code:'invitation_unavailable',message:'La invitación no está disponible.'}}});
    return route.fulfill({json:{status:infoState,is_expired:infoState==='expired',email:member.email,nombre:member.nombre,role:'viewer',role_display:'Solo lectura',gym_name:'Synthetic Gym',expires_at:new Date(Date.now()+86400000).toISOString(),membership_type:'professional',can_accept:canAccept && infoState==='pending',unavailable_reason:canAccept ? null : 'El plan actual del gimnasio no permite nuevas incorporaciones.'}});
   }
   if(endpoint==='/api/auth/accept-invite'){accepts++;actor={id:'professional',tipo:'usuario',role:'viewer',nombre:'Professional',email:member.email,team_gym_id:'owner',role_display:'Solo lectura',permissions:viewerPermissions};return route.fulfill({json:{success:true,access_token:'synthetic-member-token',refresh_token:'synthetic-member-refresh'}});}
   return route.fulfill({status:503,json:{detail:'Synthetic endpoint not configured'}});
  });
  async function scan(label){await page.evaluate(()=>Promise.all(document.getAnimations().filter(a=>Number.isFinite(a.effect.getComputedTiming().endTime)).map(a=>a.finished.catch(()=>{}))));await page.evaluate(()=>scrollTo(0,0));const dimensions=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();report.screens.push({label,dimensions,violations:axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});await page.screenshot({path:path.join(out,label+'.png'),fullPage:true});}
  await page.goto(base+'/equipo');await page.locator('#team-management').waitFor({state:'visible'});
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});await scan('team-owner-after-'+width);}
  await page.locator('#team-name').fill('New Professional');await page.locator('#team-email').fill('new@example.invalid');await page.locator('#team-role').selectOption('nutriologo');await page.locator('#team-invite-submit').click();
  await page.locator('#team-share').waitFor({state:'visible'});assert.match(await page.locator('#team-delivery').textContent(),/no está confirmada/);
  assert.deepEqual(calls.find(c=>c.endpoint==='/api/gym/team/invite').body,{nombre:'New Professional',apellido:'',email:'new@example.invalid',role:'nutriologo'});
  const roleSelect=page.getByLabel('Rol de Professional');await roleSelect.selectOption('admin');await page.getByRole('button',{name:'Guardar rol'}).click();await page.waitForFunction(()=>document.querySelector('#team-feedback').textContent.includes('Rol actualizado'));
  await page.getByRole('button',{name:'Crear enlace nuevo'}).click();await page.waitForFunction(()=>document.querySelector('#team-share-link').value.includes('r'.repeat(43)));
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Retirar acceso'}).click();await page.waitForFunction(()=>document.querySelector('#team-summary').textContent.startsWith('1 personas'));
  report.checks.push('Owner invites, changes allowed roles, rotates the link and revokes professional access with truthful delivery state');
  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/auth/accept-invite#token='+'n'.repeat(43));await page.locator('#invite-session').waitFor({state:'visible'});
  assert.equal(new URL(page.url()).hash,'');assert.equal(new URL(page.url()).search,'');assert.equal(await page.locator('#invite-form').isVisible(),false);
  const infoCall=calls.filter(c=>c.endpoint==='/api/auth/invite-info').at(-1);assert.equal(infoCall.method,'POST');assert.equal(infoCall.body.token,'n'.repeat(43));assert.ok(!infoCall.url.includes('n'.repeat(43)));assert.equal(infoCall.authorization,null);
  await page.locator('#invite-logout').click();await page.locator('#invite-form').waitFor({state:'visible'});
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});await scan('team-invitation-after-'+width);}
  assert.ok(await page.evaluate(token=>!Object.values(localStorage).includes(token) && !Object.values(sessionStorage).includes(token),'n'.repeat(43)));
  await page.locator('#invite-password').fill('SyntheticPassword123!');await page.locator('#invite-confirm').fill('DifferentPassword123!');await page.locator('#invite-submit').click();assert.match(await page.locator('#invite-feedback').textContent(),/no coinciden/);assert.equal(accepts,0);
  await page.locator('#invite-confirm').fill('SyntheticPassword123!');await page.locator('#invite-submit').click();await page.waitForURL(base+'/equipo/inicio');await page.waitForFunction(()=>document.querySelector('#professional-context').textContent.includes('Solo lectura'));
  assert.equal(accepts,1);assert.equal(await page.locator('[data-permission="read:billing"]').isHidden(),true);assert.equal(await page.locator('a[href="/equipo"]').evaluateAll(elements=>elements.every(el=>el.getClientRects().length===0)),true);
  await scan('team-viewer-home-after');
  report.checks.push('Fragment bearer stays in memory; POST info avoids query token; an existing session requires explicit logout; acceptance resolves current professional identity');
  await page.goto(base+'/mi-perfil');await page.waitForFunction(()=>document.querySelector('[data-professional-context]').hidden===false);
  assert.equal(new URL(page.url()).pathname,'/mi-perfil');await page.getByRole('link',{name:'Espacio del gimnasio'}).click();await page.waitForURL(base+'/equipo/inicio');
  await page.evaluate(()=>localStorage.setItem('mb_tipo','gym'));
  await page.goto(base+'/equipo');await page.waitForFunction(()=>document.querySelector('#team-loading').textContent.includes('no permite'));assert.equal(await page.locator('#team-management').isVisible(),false);assert.equal(await page.evaluate(()=>localStorage.getItem('mb_tipo')),'usuario');
  report.checks.push('A professional viewer switches explicitly between gym workspace and their independent personal profile; team/billing management stays forbidden');
  actor={...actor,tipo:'gym'};
  await page.goto(base+'/equipo/inicio');await page.getByRole('link',{name:'Mi perfil personal'}).waitFor({state:'visible'});
  await page.getByRole('link',{name:'Mi perfil personal'}).click();await page.waitForURL(base+'/mi-plan');await page.getByRole('link',{name:'Espacio del gimnasio'}).waitFor({state:'visible'});
  assert.equal(await page.evaluate(()=>localStorage.getItem('mb_tipo')),'gym');assert.equal(actor.role,'viewer');
  report.checks.push('Historical gym-typed professionals retain the explicit personal context link without becoming an owner');
  actor={id:'owner',tipo:'gym',role:'owner',nombre:'Synthetic Owner',permissions:ownerPermissions};
  team={...team,members:[team.members[0],{...member,activo:true,is_pending:false,invitation_status:'active',can_resend:false}],total:2,pending_invitations:0,capabilities:{...team.capabilities,invite:false},invitation_requirement:'Tu plan actual no permite nuevas incorporaciones. Puedes seguir administrando o retirando los accesos existentes.'};
  await page.goto(base+'/equipo');await page.locator('#team-management').waitFor({state:'visible'});
  assert.equal(await page.locator('#team-invite-submit').isDisabled(),true);assert.equal(await page.locator('#team-email').isDisabled(),true);assert.equal(await page.getByRole('button',{name:'Guardar rol'}).isEnabled(),true);
  await page.setViewportSize({width:320,height:900});await scan('team-plan-blocked-after-320');
  assert.equal(await page.getByRole('link',{name:'Mi perfil personal'}).isHidden(),true);
  report.checks.push('Unavailable multi-user rights disable new invitations while existing member management remains available');
  await page.evaluate(()=>{localStorage.removeItem('mb_token');localStorage.removeItem('mb_refresh_token');});
  canAccept=false;await page.goto(base+'/auth/accept-invite#token='+'b'.repeat(43));await page.waitForFunction(()=>document.querySelector('#invite-feedback').textContent.includes('no permite nuevas incorporaciones'));assert.equal(await page.locator('#invite-form').isVisible(),false);
  await page.setViewportSize({width:390,height:844});await scan('team-invitation-plan-blocked-after-390');canAccept=true;
  infoState='expired';await page.goto(base+'/auth/accept-invite?token='+'e'.repeat(43));await page.waitForFunction(()=>document.querySelector('#invite-feedback').textContent.includes('venció'));assert.equal(await page.locator('#invite-form').isVisible(),false);
  infoState='missing';await page.goto(base+'/auth/accept-invite#token='+'m'.repeat(43));await page.waitForFunction(()=>document.querySelector('#invite-feedback').textContent.includes('no está disponible'));assert.equal(await page.locator('#invite-form').isVisible(),false);
  infoMalformed=true;await page.goto(base+'/auth/accept-invite#token='+'h'.repeat(43));await page.waitForFunction(()=>document.querySelector('#invite-feedback').textContent.includes('respuesta no válida'));assert.equal(await page.locator('#invite-form').isVisible(),false);
  report.checks.push('Expired, revoked/used and malformed invitation responses cannot activate a membership; legacy query links are cleaned');
  report.publicInfoMethods=calls.filter(c=>c.endpoint==='/api/auth/invite-info').map(c=>c.method);
  fs.writeFileSync(path.join(out,'team-browser.json'),JSON.stringify(report,null,2));
  assert.deepEqual(report.errors,[]);assert.ok(report.screens.every(s=>s.dimensions.width>=s.dimensions.scrollWidth),'Horizontal overflow');assert.ok(report.screens.every(s=>!s.violations.length),'WCAG AA automated violations');
  console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
