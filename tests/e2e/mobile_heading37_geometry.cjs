/* CSS/markup geometry reproduction only; synthetic inert DOM, no app/auth/SQL. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const{inspect}=require('./mobile_heading37_qa.cjs');
const root=path.resolve(__dirname,'../..'),deps=process.env.METODOBASE_E2E_DEPENDENCIES;
const output=process.env.QA37_GEOMETRY_OUTPUT;assert.ok(output&&path.isAbsolute(output)&&!fs.existsSync(output));
const files=['web/templates/base.html','web/templates/base_usuario.html','web/templates/_account_security37_content.html','web/templates/_notifications36_content.html','web/templates/mfa_account_partial.html','web/static/css/styles.css','web/static/css/styles-usuario.css','web/static/css/account-security37.css','web/static/css/notifications36.css','web/static/css/mfa.css'];
const raw=Object.fromEntries(files.map(name=>[name,fs.readFileSync(path.join(root,name),'utf8')]));
const hashes=Object.fromEntries(files.map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')]));
const report={scope:'Synthetic inert DOM containing frozen product CSS/markup. Only heading/mobile-menu geometry; no authentication, business API, PostgreSQL or full UI claim.',sources:hashes,cases:[],pageErrors:[],external:[],complete:false};
fs.mkdirSync(output);let browser;
(async()=>{try{
 const{chromium}=require(path.join(deps,'playwright-core'));browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
 const context=await browser.newContext({viewport:{width:320,height:900},reducedMotion:'reduce'});
 await context.route('**/*',route=>{report.external.push({blocked:true});return route.abort();});
 const page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push(error.name));
 for(const role of['gym','personal'])for(const view of['account','notifications','mfa','kit'])for(const width of[320,390]){
  const base=raw['web/templates/'+(role==='gym'?'base.html':'base_usuario.html')];
  const button=base.match(/<button[^>]*id="btn-hamburger"[^>]*>[\s\S]*?<\/button>/)[0];
  const mainClass=role==='gym'?'main-content':'u-main';let content,selector;
  if(view==='account'){content=raw['web/templates/_account_security37_content.html'];selector='#account37-title';}
  else if(view==='notifications'){content=raw['web/templates/_notifications36_content.html'].replace(/\{% if notification_context == 'gym' %\} de gimnasio\{% endif %\}/g,role==='gym'?' de gimnasio':'');selector='#notifications-title';}
  else{content=raw['web/templates/mfa_account_partial.html'];selector='#mfa-account-title';if(view==='kit')content=content.replace('<div id="mfa-account-kit"></div>','<div id="mfa-account-kit"><h3>Guarda tu kit de recuperación</h3><p>Representación geométrica sin códigos.</p></div>');}
  const styles=['web/static/css/'+(role==='gym'?'styles.css':'styles-usuario.css'),'web/static/css/account-security37.css','web/static/css/notifications36.css','web/static/css/mfa.css'].map(name=>'<style>'+raw[name]+'</style>').join('');
  const main=view==='kit'?content+'<main class="'+mainClass+'"></main>':'<main class="'+mainClass+'">'+content+'</main>';
  await page.setViewportSize({width,height:900});await page.setContent('<!doctype html><html lang="es"><head><meta charset="utf-8">'+styles+'</head><body>'+button+main+'<div style="height:180vh" aria-hidden="true"></div></body></html>');
  await page.locator(selector).evaluate(node=>{node.tabIndex=-1;node.focus();});
  const row={case:role+'-'+view+'-'+width,role,view,width,passed:false};
  try{row.observation=await inspect(page,selector);row.passed=true;}catch(error){row.error_class=error.name;row.observation=error.observation||null;}
  await page.screenshot({path:path.join(output,row.case+'.png'),fullPage:false});report.cases.push(row);
 }
 assert.deepEqual(report.pageErrors,[]);report.complete=true;if(report.cases.some(row=>!row.passed))process.exitCode=1;
}catch(error){report.failure_class=error.name;process.exitCode=1;}finally{await browser?.close();fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({complete:report.complete,passed:report.cases.filter(x=>x.passed).length,total:report.cases.length,pageErrors:report.pageErrors.length,synthetic_geometry_only:true}));}})();
