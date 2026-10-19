/* Base28 pages/auth HTTP. Every R12 resource response below is a declared transport double. */
const {chromium}=require('playwright-core'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:8782',root=path.resolve(__dirname,'../..');
const out=path.join(root,'docs/implementation/20261018-evolution/evidence/r12-ui/browser-synthetic-'+Date.now());fs.mkdirSync(out,{recursive:true});
const A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222';
const report={scope:'Real base28 HTML/static/auth HTTP with own temporary SQLite ORM fixture. All R12 resource API/menu/PDF/receipt responses are browser transport doubles, not backend29, real worker, email proof or authorization acceptance.',checks:[],screens:[],pageErrors:[]};
const check=name=>{report.checks.push(name);console.log(name);};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const context=await browser.newContext({acceptDownloads:true,reducedMotion:'reduce'}),api=context.request;const calls=[];let issued=false,published=false,holding=null,holdEntered=null;
 const memberContext={kind:'gym_member',link_id:A,gym_name:'Gimnasio de demostración',client_display_name:'Destinatario sintético'};
 const caps={issue_invitation:true,rotate_invitation:true,revoke_link:true,publish_plan:true,withdraw_publication:true};
 const food=Object.fromEntries(['desayuno','almuerzo','comida','cena'].map(k=>[k,{kcal_objetivo:100,kcal_real:100,alimentos:{'Alimento sintético <img src=x>':100}}]));
 const reader={context:memberContext,link:{status:'active',version:7},capabilities:{read_published_plan:true,download_published_pdf:true,revoke_link:true,share_personal_diary:false,read_shared_progress:false},publication:{id:B,version:3,source_plan_id:41,published_at:'2026-10-19T18:00:00Z',plan_schema_version:1,plan:food,meta:{kcal_objetivo:400}}};
 await context.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url());if(url.origin!==base)return route.abort();
  if(!(url.pathname.includes('/vinculacion')||url.pathname.startsWith('/api/usuario/vinculos')))return route.continue();
  if(!url.pathname.startsWith('/api/'))return route.continue();
  calls.push({path:url.pathname,method:request.method(),body:request.postDataJSON()});
  const finish=data=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data),headers:{'Cache-Control':'no-store','Referrer-Policy':'no-referrer'}});
  if(url.pathname==='/api/usuario/vinculaciones/invitacion')return finish({status:'pending',version:4,expires_at:'2026-10-26T18:00:00Z',link_id:A,context:memberContext,can_accept:true});
  if(url.pathname==='/api/usuario/vinculaciones/aceptar')return finish({link_id:A,status:'active',version:7,context:memberContext});
  if(url.pathname==='/api/usuario/vinculos')return finish({items:[{context:memberContext,link_id:A,status:'active',version:7,capabilities:{read_published_plan:true,revoke_link:true}}],next_after:null});
  if(url.pathname.endsWith('/plan')){if(holding){holdEntered?.();await holding;}return finish(reader);}
  if(url.pathname.endsWith('/pdf'))return route.fulfill({status:200,contentType:'application/pdf',body:Buffer.from('%PDF-1.4\n% synthetic browser transport double\n%%EOF'),headers:{'Cache-Control':'no-store'}});
  if(url.pathname.endsWith('/invitaciones')){issued=true;return route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({invitation_id:B,link_id:A,status:'pending',link_status:'pending',version:1,link_version:1,expires_at:'2026-10-26T18:00:00Z',delivery_status:'not_confirmed'})});}
  if(url.pathname.endsWith('/publicaciones')){published=true;return finish({publication_id:B,link_id:A,source_plan_id:41,version:3});}
  return finish({client_id:'synthetic-client',capabilities:caps,items:issued?[{link_id:A,status:'pending',version:7,invitation_id:B,invitation_status:'pending',invitation_version:4,expires_at:'2026-10-26T18:00:00Z',publication:published?{id:B,version:3,source_plan_id:41}:null}]:[],next_after:null});
 });
 let page;
 async function register(tipo){const response=await api.post(base+'/api/auth/registro',{data:{email:`r12-ui-${tipo}-${Date.now()}@example.invalid`,nombre:'Synthetic '+tipo,password:'Synthetic-R12-UI-Password-2026!',tipo}});assert.equal(response.status(),200);return response.json();}
 async function open(pair,url,width=390){
  if(page)await page.close();page=await context.newPage();page.on('pageerror',e=>report.pageErrors.push(e.message));page.on('dialog',d=>d.accept());
  await page.setViewportSize({width,height:844});await page.goto(base+'/login-usuario');await page.evaluate(pair=>{localStorage.setItem('mb_token',pair.token);localStorage.setItem('mb_refresh_token',pair.refresh_token);localStorage.setItem('mb_daily','synthetic-unattributed-legacy');},pair);
  const response=await page.goto(base+url);assert.equal(response.status(),200);return response;
 }
 async function scan(name,response){
  const nonce=response.headers()['content-security-policy'].match(/'nonce-([^']+)'/)[1];
  await page.evaluate(({code,nonce})=>{const script=document.createElement('script');script.nonce=nonce;script.textContent=code;document.head.append(script);},{code:fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'),nonce});
  const result=await page.evaluate(async()=>({overflow:document.documentElement.scrollWidth>innerWidth,violations:(await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations}));
  fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(result,null,2));assert.deepEqual(result.violations,[],name+' axe');assert.equal(result.overflow,false);await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});report.screens.push(name);
 }
 try{
  const personal=await register('usuario'),owner=await register('gym');
  let response=await open(personal,'/auth/accept-client-link#token='+'S'.repeat(43));assert.equal(new URL(page.url()).hash,'');assert.equal(calls.length,0);
  await page.locator('#invitation-inspect').click();await page.locator('#invitation-accept').waitFor({state:'visible'});assert.equal(calls.filter(c=>c.path.endsWith('/aceptar')).length,0);await scan('invitation-390',response);
  await page.locator('#invitation-accept').focus();await page.keyboard.press('Enter');await page.locator('#invitation-open-links').waitFor({state:'visible'});
  assert.equal(await page.evaluate(()=>Object.values(localStorage).some(value=>value.includes('S'.repeat(43)))),false);check('Real personal registration/auth; synthetic inspection requires a click, fragment is removed, and keyboard acceptance is separate with no bearer in Storage');
  response=await open(owner,'/clientes/synthetic-client/vinculacion?plan_id=41',1440);await page.locator('#link-invite-form').waitFor({state:'visible'});await scan('professional-empty-1440',response);
  await page.locator('#link-recipient').fill('synthetic-recipient@example.invalid');await page.locator('#link-issue').click();await page.waitForFunction(()=>document.querySelector('#professional-link-status').textContent.includes('entrega del correo sin confirmar'));
  assert.equal(calls.filter(c=>c.path.endsWith('/publicaciones')).length,0);await page.setViewportSize({width:320,height:844});await scan('professional-pending-320',response);
  await page.getByRole('button',{name:'Publicar este plan',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#professional-link-items').textContent.includes('Plan publicado: 41'));
  const publish=calls.find(c=>c.path.endsWith('/publicaciones'));assert.equal(publish.body.plan_id,41);assert.equal(publish.body.expected_link_version,7);assert.equal(publish.body.expected_publication_version,0);assert.equal(publish.body.expected_publication_id,null);check('Real gym OWNER registration/auth with synthetic R12 capabilities; issuing does not claim delivery and publication only happens on explicit confirmation with observed CAS');
  response=await open(personal,'/mis-vinculos',1440);await page.getByRole('button',{name:'Consultar plan de este vínculo'}).click();await page.locator('#member-publication').waitFor({state:'visible'});assert.equal(await page.locator('#member-publication-meals img').count(),0);await scan('reader-1440',response);
  await page.setViewportSize({width:320,height:844});await scan('reader-320',response);const download=page.waitForEvent('download');await page.locator('#member-publication-pdf').click();await download;
  assert.equal(calls.filter(c=>c.path.endsWith('/pdf')).at(-1).path,`/api/usuario/vinculos/${A}/publicaciones/${B}/pdf`);check('Synthetic published menu is literal text, isolated from personal diary actions, and the synthetic PDF uses the exact link/publication reader');
  let release;holding=new Promise(r=>{release=r;});const entered=new Promise(r=>{holdEntered=r;});await page.locator('#member-links-refresh').click();await page.getByRole('button',{name:'Consultar plan de este vínculo'}).click();
  await entered;await page.evaluate(pair=>Api.saveTokens(pair),owner);release();holding=null;
  await page.waitForFunction(()=>document.querySelector('#member-publication-meals').textContent===''&&document.querySelector('#member-links-list').textContent==='');
  assert.equal(await page.evaluate(()=>localStorage.getItem('mb_daily')),'synthetic-unattributed-legacy');assert.deepEqual(report.pageErrors,[]);check('Real account replacement during synthetic delayed plan response clears prior private DOM and preserves legacy bytes without adopting the new account');report.passed=true;
 }catch(error){report.passed=false;report.error=error.stack;console.error(error.stack);process.exitCode=1;}
 finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));await browser.close();}
})();
