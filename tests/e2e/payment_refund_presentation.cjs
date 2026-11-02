/* Actual SSR, Api and billing controllers. Every request is fulfilled locally. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('playwright-core');
const {AxeBuilder}=require('@axe-core/playwright');
const repo=path.resolve(process.env.METODOBASE_REFUND_REPO||path.join(__dirname,'../..'));
const out=path.resolve(process.env.METODOBASE_REFUND_EVIDENCE||'');
if(!/^[EF]:[\\/]/i.test(out))throw Error('Evidence must remain on E/F');
const mode=process.argv[2],revision=process.argv[3]||mode;
if(!['red','green'].includes(mode)||!/^[-a-z0-9]{1,32}$/.test(revision))throw Error('Expected red/green and unique receipt name');
const origin='http://127.0.0.1:8823';
const sourceFiles=['web/static/js/api.js','web/static/js/gym-suscripcion.js','web/static/js/usuario-suscripcion.js','web/templates/suscripciones.html','web/templates/usuario_suscripcion.html','web/templates/base.html','web/templates/base_usuario.html','web/static/css/subscription.css','web/static/css/payment-history.css','web/static/js/payment-history.js','web/static/js/auth-guard.js','web/static/js/session-shell.js','web/static/css/styles.css','web/static/css/styles-usuario.css','web/static/css/workspace.css'];
const hash=file=>fs.existsSync(file)?crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'):null;
const pins=()=>Object.fromEntries(sourceFiles.map(file=>[file,hash(path.join(repo,file))]));
const before=pins(),results=[];
const common={created_at:'2026-11-02T02:00:00Z',amount_cents:15900,currency:'mxn',plan:'standard'};
const variants={
  paid:{...common,status:'succeeded',refund_amount_cents:0,net_amount_cents:15900,refund_observed_at:'2026-11-02T02:01:00Z'},
  partial:{...common,status:'partially_refunded',refund_amount_cents:3900,net_amount_cents:12000,refund_observed_at:'2026-11-02T03:01:00Z'},
  full:{...common,status:'refunded',refund_amount_cents:15900,net_amount_cents:0,refund_observed_at:'2026-11-02T04:01:00Z'},
  legacy:{...common,status:'succeeded'},
};
const cases=['gym','usuario'].flatMap(audience=>Object.keys(variants).map(variant=>({audience,variant,width:390})));
if(mode==='green'){
  for(const audience of ['gym','usuario']){
    for(const width of [320,1440])cases.push({audience,variant:'partial',width});
    cases.push({audience,variant:'malformed',width:390});
    cases.push({audience,variant:'nullable',width:390});
    cases.push({audience,variant:'cumulative',width:390});
    cases.push({audience,variant:'retry',width:390});
    cases.push({audience,variant:'replacement',width:390});
  }
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  for(const spec of cases){
   const context=await browser.newContext({viewport:{width:spec.width,height:950}}),page=await context.newPage();
   const observations={requests:[],external:[],errors:[],consoleErrors:[]};
   let paymentAttempt=0,release,pending=false;
   const gate=new Promise(done=>release=done);
   page.on('pageerror',error=>observations.errors.push(error.message));
   page.on('console',message=>{if(message.type()==='error')observations.consoleErrors.push(message.text());});
   await context.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.origin!==origin){observations.external.push(url.hostname);return route.abort();}
    const entry=spec.audience==='gym'?'/suscripciones':'/mi-suscripcion';
    if(url.pathname===entry)return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(out,spec.audience+'.html'),'utf8')});
    if(url.pathname.startsWith('/static/')){
     const file=path.resolve(repo,'web',url.pathname.slice(1));
     if(!file.startsWith(path.resolve(repo,'web','static')+path.sep))return route.abort();
     return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:'Absent fixture asset'});
    }
    observations.requests.push({method:req.method(),path:url.pathname});
    const json=value=>route.fulfill({json:value});
    if(url.pathname==='/api/auth/refresh')return json({token:'fixture-access',session_mode:'browser'});
    if(url.pathname==='/api/auth/me')return json({id:'isolated-actor',tipo:spec.audience,role:'owner',session_version:1,team_gym_id:null,nombre:'Cuenta de demostración',permissions:[['read','billing'],['read','dashboard']]});
    if(url.pathname==='/api/clientes')return json({total:0,clientes:[]});
    if(url.pathname==='/api/billing/config')return json({stripe_configured:true,mercadopago_configured:false,plans:{standard:{precio_mxn:159},gym_comercial:{precio_mxn:479},clinica:{precio_mxn:979}}});
    if(url.pathname==='/api/usuario/billing-config')return json({checkout_supported:true,mercadopago_configured:false});
    if(url.pathname==='/api/billing/subscription')return json({status:'active',plan:'standard',provider:'stripe',max_clientes:25,current_period_end:1794960000});
    if(url.pathname==='/api/usuario/suscripcion')return json({status:'active',plan:'pro',provider:'stripe',planes_usados:2,max_planes:5,planes_restantes:3,period_end:'2026-11-18T00:00:00Z',cancel_at_period_end:false});
    if(url.pathname.endsWith('/payments')){
     paymentAttempt++;
     if(spec.variant==='replacement'){pending=true;await gate;}
     if(spec.variant==='retry'&&paymentAttempt===1)return route.fulfill({status:503,json:{detail:{code:'temporary_failure',message:'Historial temporalmente no disponible.'}}});
     let payment=variants[spec.variant]||variants.partial;
     if(spec.audience==='usuario')payment={...payment,plan:'pro'};
     if(spec.variant==='malformed')payment={...payment,refund_amount_cents:20000,net_amount_cents:-4100,status:'<img src=x onerror=alert(1)>',plan:'<script>alert(1)</script>'};
     if(spec.variant==='nullable')payment={...payment,status:'succeeded',refund_amount_cents:null,net_amount_cents:null,refund_observed_at:null};
     if(spec.variant==='cumulative'&&paymentAttempt>1)payment={...payment,refund_amount_cents:7800,net_amount_cents:8100};
     return json({payments:[payment]});
    }
    return json({});
   });
   const name=[spec.audience,spec.variant,spec.width].join('-');
   try{
    await page.goto(origin+(spec.audience==='gym'?'/suscripciones':'/mi-suscripcion'));
    await page.waitForFunction(()=>['Standard','Pro'].includes(document.querySelector('#sub-plan-name').textContent));
    const body=page.locator('#payments-tbody');
    if(spec.variant==='replacement'){
     for(let i=0;i<100&&!pending;i++)await new Promise(done=>setTimeout(done,10));
     assert.equal(pending,true,'History request started');
     await page.evaluate(()=>{const next=crypto.randomUUID();localStorage.setItem('mb_session_epoch',next);window.dispatchEvent(new StorageEvent('storage',{key:'mb_session_epoch',newValue:next}));});
     release();await page.waitForFunction(()=>!document.querySelector('#payments-state')||document.querySelector('#payments-state').textContent.includes('sesión anterior'));
     assert.equal(await body.locator('tr').count(),0);
    }else{
     if(spec.variant==='retry'){
      await page.waitForFunction(()=>document.querySelector('#payments-state').textContent.includes('No pudimos'));
      await page.locator(spec.audience==='gym'?'#btn-refresh-billing':'#btn-refresh-subscription').click();
     }
     if(mode==='green'||spec.audience==='gym')await body.locator('tr').waitFor();
     const text=await body.count()?await body.innerText():'';
     assert.match(text,/Original/,'Original amount labelled');
     assert.match(text,/Devuelto/,'Refund amount labelled');
     assert.match(text,/Importe tras devolución/,'Post-refund amount labelled');
     const expected={paid:'Pagado',partial:'Devolución parcial',full:'Devolución completa',legacy:'Pagado',nullable:'Pagado',cumulative:'Devolución parcial',malformed:'Estado por confirmar',retry:'Devolución parcial'};
     assert.ok(text.includes(expected[spec.variant]),'Spanish payment status');
     if(['legacy','nullable','malformed'].includes(spec.variant)){
      assert.equal((text.match(/Sin dato confirmado/g)||[]).length,2,'Unknown refund and resulting amount remain unknown');
     }else{
      const amounts=await body.locator('.billing-payment-value').allTextContents();
      const value=variants[spec.variant]||variants.partial;
      const format=cents=>new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(cents/100);
      assert.deepEqual(amounts,[format(value.amount_cents),format(value.refund_amount_cents),format(value.net_amount_cents)]);
     }
     assert.equal(await body.locator('script,img').count(),0,'No provider-controlled HTML');
     assert.equal(await page.locator('#sub-plan-name').textContent(),spec.audience==='gym'?'Standard':'Pro','History presentation does not change entitlement');
     if(spec.variant==='cumulative'){
      const period=await page.locator('#sub-renewal').textContent();
      await page.locator(spec.audience==='gym'?'#btn-refresh-billing':'#btn-refresh-subscription').click();
      await page.waitForFunction(()=>document.querySelector('#payments-tbody').textContent.includes('81.00'));
      assert.match(await body.innerText(),/78.00/);
      assert.equal(await page.locator('#sub-renewal').textContent(),period,'A later partial refund does not slide paid period');
     }
     if(mode==='green'&&spec.variant==='partial'){
      const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
      observations.axe=axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}));
      assert.deepEqual(observations.axe,[],'Automated WCAG A/AA');
      await page.screenshot({path:path.join(out,revision+'-'+name+'.png'),fullPage:true});
     }
    }
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Viewport overflow');
    assert.deepEqual(observations.errors,[]);assert.deepEqual(observations.external,[]);
    assert.equal(observations.requests.some(r=>r.method==='POST'&&r.path!=='/api/auth/refresh'),false,'Read-only history never initiates purchase, factor or email');
    results.push({case:name,passed:true,...observations});
   }catch(error){results.push({case:name,passed:false,message:error.message,...observations});}
   finally{release();await context.close();}
  }
 }finally{await browser.close();}
 assert.deepEqual(pins(),before,'Sources changed during browser gate');
 const passed=mode==='red'?results.length===8&&results.every(r=>!r.passed&&r.errors.length===0&&r.external.length===0):results.every(r=>r.passed);
 const report={mode,revision,passed,cases:results.length,scope:'Actual Jinja SSR, Api and JS controllers; Chromium; all requests locally intercepted. No HTTP app, DB, provider, mailbox, account or charge.',source_stable:true,sources:before,browser_closed:true,results};
 const target=path.join(out,revision+'-browser-report.json');if(fs.existsSync(target))throw Error('Never overwrite evidence');
 fs.writeFileSync(target,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({mode,passed,cases:results.length,failed:results.filter(r=>!r.passed).map(r=>({case:r.case,message:r.message}))}));
 if(!passed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
