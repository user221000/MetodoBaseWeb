/* Affected-table accessibility/reflow only; no re-attribution of prior14 groups. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const phase=process.env.QA_R25_PHASE,out=process.env.QA_R25_PUBLIC,modules=process.env.QA_NODE_MODULES;
const{chromium}=require(path.join(modules,'playwright-core'));
const marker=JSON.parse(fs.readFileSync(path.join(phase,'startup.private.json'))),base=marker.origin,ids=marker.ids;
assert.equal(marker.fixture,'qa-r25-real-sqlite32');assert.equal(marker.revision,'20261019_personal_progress');assert.match(base,/^http:\/\/127\.0\.0\.1:\d+$/);
const report={source_head:process.env.QA_SOURCE_HEAD,scope:'Eight actual affected-table main views at320/390/768/1440. Real migrated SQLite32 and password auth; real API setup populates measurement, accepted link, exact consent and1/1 completed diary so CSS is examined on personal/professional/native/shared/count tables. These are fresh layout/axe observations, not replay or acceptance of the prior14 business groups. No provider/PG/clinical/SLO claim.',views:[],pageErrors:[],complete:false};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{let browser,context,page;
 try{
  browser=await chromium.launch({headless:true,executablePath:process.env.QA_CHROME});context=await browser.newContext({viewport:{width:320,height:900}});
  await context.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push({name:error.name}));
  const json=async response=>{assert.equal(response.status(),200,'Actual setup HTTP failed');return response.json();};
  const pairs={};for(const actor of ['gym','person'])pairs[actor]=await json(await context.request.post(base+'/api/auth/login',{data:{email:'qa-progress-'+actor+'@example.invalid',password:'Synthetic-QA-Progress-2026!'}}));
  const person={Authorization:'Bearer '+pairs.person.token},gym={Authorization:'Bearer '+pairs.gym.token};
  const today=(await json(await context.request.get(base+'/api/usuario/progreso/contexto',{headers:person}))).today;
  await json(await context.request.put(base+'/api/usuario/progreso/mediciones/'+crypto.randomUUID(),{headers:person,data:{expected_version:0,source_profile_id:ids.profile,measured_on:today,values:{peso_kg:71.5}}}));
  const invite=await context.request.post(base+'/api/clientes/'+ids.client+'/vinculacion/invitaciones',{headers:gym,data:{recipient_email:'qa-progress-person@example.invalid',request_key:crypto.randomUUID()}});assert.equal(invite.status(),202);const link=(await invite.json()).link_id;
  const mailPath=path.join(phase,'mail.private.jsonl');let token=null;
  for(let index=0;index<100&&!token;index++){try{const lines=fs.readFileSync(mailPath,'utf8');if(lines.endsWith('\n'))token=JSON.parse(lines.trim().split('\n').at(-1)).html.match(/#token=([A-Za-z0-9_-]{43})/)[1];}catch{}if(!token)await delay(50);}assert.ok(token);
  await json(await context.request.post(base+'/api/usuario/vinculaciones/aceptar',{headers:person,data:{token,expected_version:1,confirm:true}}));
  await json(await context.request.put(base+'/api/usuario/vinculos/'+link+'/progreso/consentimiento',{headers:person,data:{expected_consent_id:null,expected_version:0,expected_link_version:2,event:'grant',protocol:'progress_share_v1',source_profile_id:ids.profile,categories:{weight:true,body_fat:false,lean_mass:false,completion:true},from_date:today,through_date:today,ongoing:false}}));
  const day=base+'/api/usuario/diario/'+today;
  await json(await context.request.patch(day,{headers:person,data:{operation:'meal',expected_version:0,source_plan_id:ids.plan,meal:'desayuno',selections:{include_fixed_menu:true}}}));
  await json(await context.request.patch(day,{headers:person,data:{operation:'completion',expected_version:1,meal:'desayuno',completed:true}}));
  for(const entry of [{actor:'person',route:'/mi-progreso',root:'#personal-progress-page'},{actor:'gym',route:'/clientes/'+ids.client+'/progreso',root:'#professional-progress-page'}]){
   await page.goto(base+'/login-usuario');await page.evaluate(pair=>Api.saveTokens(pair),pairs[entry.actor]);await page.goto(base+entry.route);await page.waitForFunction(()=>!document.getElementById('progress-refresh').disabled);
   if(entry.actor==='person'){await page.locator('#progress-profile').selectOption(ids.profile);await page.waitForFunction(()=>!document.getElementById('progress-refresh').disabled);await page.waitForFunction(()=>document.querySelector('#measurement-table').textContent.includes('71.5 kg'));}
   else{await page.locator('#professional-link').selectOption(link);await page.waitForFunction(()=>!document.getElementById('progress-refresh').disabled);await page.locator('#professional-query').waitFor({state:'visible'});await page.locator('#professional-query button').click();await page.waitForFunction(()=>document.getElementById('professional-shared-status').textContent.includes('Lectura autorizada'));assert.match(await page.locator('#professional-shared-measurements').textContent(),/71\.5 kg/);}
   await page.evaluate(fs.readFileSync(path.join(modules,'axe-core/axe.min.js'),'utf8'));
   for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});
    const value=await page.evaluate(async root=>{
     const parent=document.querySelector(root),tables=Array.from(parent.querySelectorAll('.progress-table-wrap')).filter(wrap=>wrap.getClientRects().length);
     const regions=tables.map(wrap=>({label:wrap.getAttribute('aria-label'),role:wrap.getAttribute('role'),tabIndex:wrap.tabIndex,width:wrap.clientWidth,scrollWidth:wrap.scrollWidth,
      observedTokens:Array.from(wrap.querySelectorAll('tbody td')).filter(cell=>/^(?:\d+(?:\.\d+)? (?:kg|percent)|\d{4}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2}T[^\s]+ \(UTC\))$/.test(cell.textContent.trim())).map(cell=>{const range=document.createRange();range.selectNodeContents(cell);return{text:cell.textContent.trim(),fragments:Array.from(range.getClientRects()).filter(rect=>rect.width&&rect.height).length};})}));
     return{overflow:document.documentElement.scrollWidth>innerWidth,documentWidth:document.documentElement.scrollWidth,viewport:innerWidth,regions,
      violations:(await axe.run(parent,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(row=>({id:row.id,impact:row.impact,targets:row.nodes.map(node=>node.target)}))};
    },entry.root);
    const name=(entry.actor==='person'?'personal':'professional')+'-affected-'+width;
    fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(value,null,2),{flag:'wx'});await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});report.views.push({name,page:entry.actor==='person'?'personal':'professional',width,root:entry.root,...value});
    assert.equal(value.overflow,false);assert.deepEqual(value.violations,[]);assert.ok(value.regions.length>=2);assert.ok(value.regions.every(region=>region.role==='region'&&region.tabIndex===0&&!!region.label&&region.observedTokens.every(token=>token.fragments===1)));
   }
  }
  assert.deepEqual(report.pageErrors,[]);assert.equal(report.views.length,8);report.complete=true;
 }catch(error){report.failure_class=error.name;report.failure_locations=String(error.stack||'').split('\n').filter(line=>/^\s+at /.test(line));fs.writeFileSync(path.join(phase,'failure.private.json'),JSON.stringify({message:error.message,stack:error.stack}),{flag:'wx'});process.exitCode=1;}
 finally{await context?.close();await browser?.close();report.browser_close_returned=true;fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2),{flag:'wx'});if(!report.complete)process.exitCode=1;console.log(JSON.stringify({complete:report.complete,views:report.views.length,pageErrors:report.pageErrors.length}));}
})();
