/* Actual rendered markup/CSS, static account states. Only original menu handlers run. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),deps=process.env.METODOBASE_E2E_DEPENDENCIES;
const render=process.env.METODOBASE_VISUAL_RENDER,output=process.env.METODOBASE_VISUAL_OUTPUT;
assert.ok(render&&output&&path.isAbsolute(render)&&path.isAbsolute(output)&&!fs.existsSync(output));
const meta=JSON.parse(fs.readFileSync(path.join(render,'render.json'),'utf8')),baseline=meta.baseline;
const getSource=name=>baseline?cp.execFileSync('git',['show',meta.base+':'+name],{cwd:root}):fs.readFileSync(path.join(root,name));
const digest=data=>crypto.createHash('sha256').update(data).digest('hex');
const report={scope:'Static Jinja rendered source/CSS and original menu handlers only; no auth/API/provider/SQL acceptance',baseline,cases:[],pageErrors:[],external:[],complete:false};
fs.mkdirSync(output);let browser;
(async()=>{try{
 const {chromium}=require(path.join(deps,'playwright-core'));
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),page=await context.newPage();
 page.on('pageerror',error=>report.pageErrors.push(error.name));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.origin!=='http://127.0.0.1:8818'){report.external.push(url.origin);return route.abort();}
  const name=decodeURIComponent(url.pathname);
  if(name.startsWith('/static/')){
   const relative='web'+name;if(name.includes('..'))return route.abort();
   try{return route.fulfill({body:getSource(relative),contentType:name.endsWith('.css')?'text/css':name.endsWith('.svg')?'image/svg+xml':name.endsWith('.png')?'image/png':'application/octet-stream'});}catch{return route.fulfill({status:404,body:''});}
  }
  const file=path.join(render,path.basename(name)+'.html');
  if(!fs.existsSync(file))return route.abort();
  let html=fs.readFileSync(file,'utf8').replace(/<script\b[\s\S]*?<\/script>/gi,'');
  return route.fulfill({body:html,contentType:'text/html'});
 });
 const axefile=path.join(deps,'axe-core','axe.min.js');
 const baselineShots=new Set(['dashboard-1440','usuario_mi_plan-390','landing-390','login_gym-1440']);
 const afterShots=new Set([...baselineShots,'dashboard-390','landing-1440','login_usuario-390','clientes-390','suscripciones-1440','usuario_perfil-390','equipo-1440','cuenta_seguridad37-390','recordatorios-390','usuario_progreso-390']);
 const requested=process.env.METODOBASE_VISUAL_CASES?.split(',');
 if(requested)assert.ok(requested.length&&requested.every(name=>meta.cases.some(row=>row.case===name)));
 const variants=baseline?meta.cases.filter(row=>['dashboard','usuario_mi_plan','landing','login_gym'].includes(row.case)):meta.cases.filter(row=>!requested||requested.includes(row.case));
 for(const entry of variants)for(const width of baseline?[390,1440]:[320,390,768,1440]){
  await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:8818/'+entry.case,{waitUntil:'networkidle'});
  const key=entry.case+'-'+width;let menu={tested:false};
  if(await page.locator('#btn-hamburger').count()){
   const personal=await page.locator('body.mb-app--personal').count()||entry.case.startsWith('usuario_');
   const base=getSource('web/templates/'+(personal?'base_usuario.html':'base.html')).toString('utf8');
   const begin=base.indexOf('// Hamburger menu'),end=base.indexOf(personal?'// Logout':'// Read-only count',begin);
   assert.ok(begin>=0&&end>begin);await page.evaluate(source=>{(0,eval)('(()=>{'+source+'})()');},base.slice(begin,end));
   if(width<=768){await page.locator('#btn-hamburger').focus();const focus=await page.locator('#btn-hamburger').evaluate(node=>getComputedStyle(node).outlineStyle);await page.keyboard.press('Enter');const opened=await page.locator('#btn-hamburger').getAttribute('aria-expanded');await page.keyboard.press('Escape');menu={tested:true,opened:opened==='true',closed:await page.locator('#btn-hamburger').getAttribute('aria-expanded')==='false',focus_visible:focus!=='none'};}
  }
  await page.addScriptTag({path:axefile});
  const geometry=await page.evaluate(()=>({document_overflow:document.documentElement.scrollWidth>innerWidth+1,body_width:document.body.getBoundingClientRect().width,viewport:innerWidth,canvas_background:getComputedStyle(document.documentElement).backgroundColor,canvas_dark:getComputedStyle(document.documentElement).backgroundColor==='rgb(12, 17, 23)',heading:document.querySelector('h1')?.getBoundingClientRect().toJSON(),menu:document.querySelector('#btn-hamburger')?.getBoundingClientRect().toJSON()}));
  const axe=await page.evaluate(async()=>{const result=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return result.violations.map(row=>({id:row.id,impact:row.impact,nodes:row.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));});
  const row={case:entry.case,width,geometry,menu,axe,passed:!geometry.document_overflow&&(baseline||geometry.canvas_dark)&&(!menu.tested||(menu.opened&&menu.closed&&menu.focus_visible))&&axe.length===0};report.cases.push(row);
  if((baseline?baselineShots:afterShots).has(key)){await page.screenshot({path:path.join(output,key+'.png'),fullPage:false});}
 }
 report.complete=true;
}catch(error){report.failure={class:error.name,message:String(error.message).slice(0,300)};process.exitCode=1;}finally{
 await browser?.close();report.browser_closed=true;fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({complete:report.complete,passed:report.cases.filter(row=>row.passed).length,total:report.cases.length,pageErrors:report.pageErrors.length,overflow:report.cases.filter(row=>row.geometry.document_overflow).map(row=>row.case+'-'+row.width),violations:[...new Set(report.cases.flatMap(row=>row.axe.map(v=>v.id)))],browser_closed:true}));
}})();
