/* Independent layout canary: actual migrated SQLite32/auth/API/DOM, no fake access. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const phase=process.env.QA_R25_PHASE,out=process.env.QA_R25_PUBLIC,modules=process.env.QA_NODE_MODULES;
const{chromium}=require(path.join(modules,'playwright-core'));
const marker=JSON.parse(fs.readFileSync(path.join(phase,'startup.private.json'))),base=marker.origin,ids=marker.ids;
assert.equal(marker.fixture,'qa-r25-real-sqlite32');assert.equal(marker.revision,'20261019_personal_progress');assert.match(base,/^http:\/\/127\.0\.0\.1:\d+$/);
const report={source_head:process.env.QA_SOURCE_HEAD,scope:'Independent mobile legibility criterion: declared numeric value+unit and civil measurement date must remain a legible unbroken item inside a labelled keyboard-focusable table region. Actual web.main_web/SQLite32/login/measurement API; no provider, auth double or PG claim.',cases:[],pageErrors:[],complete:false};
(async()=>{let browser,context,page;
 try{
  browser=await chromium.launch({headless:true,executablePath:process.env.QA_CHROME});context=await browser.newContext({viewport:{width:320,height:900}});
  await context.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());page=await context.newPage();page.on('pageerror',error=>report.pageErrors.push({name:error.name}));
  const pairs={};for(const actor of ['gym','person']){const response=await context.request.post(base+'/api/auth/login',{data:{email:'qa-progress-'+actor+'@example.invalid',password:'Synthetic-QA-Progress-2026!'}});assert.equal(response.status(),200);pairs[actor]=await response.json();}
  const headers={Authorization:'Bearer '+pairs.person.token},contextResponse=await context.request.get(base+'/api/usuario/progreso/contexto',{headers});assert.equal(contextResponse.status(),200);const today=(await contextResponse.json()).today;
  const record=await context.request.put(base+'/api/usuario/progreso/mediciones/'+crypto.randomUUID(),{headers,data:{expected_version:0,source_profile_id:ids.profile,measured_on:today,values:{peso_kg:71.5}}});assert.equal(record.status(),200);
  for(const entry of [{actor:'person',path:'/mi-progreso',target:'#measurement-table',value:'71.5 kg',date:today},{actor:'gym',path:'/clientes/'+ids.client+'/progreso',target:'#professional-native-table',value:'88.25 kg',date:null}]){
   await page.goto(base+'/login-usuario');await page.evaluate(pair=>Api.saveTokens(pair),pairs[entry.actor]);await page.goto(base+entry.path);await page.waitForFunction(()=>!document.getElementById('progress-refresh').disabled);
   if(entry.actor==='person'){await page.locator('#progress-profile').selectOption(ids.profile);await page.waitForFunction(()=>!document.getElementById('progress-refresh').disabled);}
   await page.waitForFunction(({target,value})=>document.querySelector(target).textContent.includes(value),entry);
   for(const width of [320,390]){
    await page.setViewportSize({width,height:900});await page.locator(entry.target).scrollIntoViewIfNeeded();
    const data=await page.evaluate(({target,value,date})=>{
     const wrap=document.querySelector(target+' .progress-table-wrap'),table=wrap.querySelector('table'),cells=Array.from(table.querySelectorAll('tbody td'));
     function fragments(text){const cell=cells.find(cell=>cell.textContent.trim()===text);if(!cell)return null;const range=document.createRange();range.selectNodeContents(cell);const rects=Array.from(range.getClientRects()).filter(rect=>rect.width>0&&rect.height>0);return{fragments:rects.length,width:cell.clientWidth,text};}
     return{pageOverflow:document.documentElement.scrollWidth>innerWidth,value:fragments(value),date:date?fragments(date):null,region:{tabIndex:wrap.tabIndex,role:wrap.getAttribute('role'),label:wrap.getAttribute('aria-label'),width:wrap.clientWidth,scrollWidth:wrap.scrollWidth},tableWidth:table.clientWidth};
    },entry);
    await page.locator(entry.target+' .progress-table-wrap').focus();const beforeScroll=await page.locator(entry.target+' .progress-table-wrap').evaluate(wrap=>wrap.scrollLeft);await page.keyboard.press('ArrowRight');await page.waitForTimeout(120);const afterScroll=await page.locator(entry.target+' .progress-table-wrap').evaluate(wrap=>wrap.scrollLeft);
    const item={page:entry.actor==='person'?'personal':'professional',width,...data,keyboardRegionFocused:await page.locator(entry.target+' .progress-table-wrap').evaluate(wrap=>document.activeElement===wrap),horizontalArrowMoved:afterScroll>beforeScroll};
    item.passed=!item.pageOverflow&&item.value?.fragments===1&&(!item.date||item.date.fragments===1)&&item.region.tabIndex===0&&item.region.role==='region'&&!!item.region.label&&item.keyboardRegionFocused&&(item.region.scrollWidth<=item.region.width||item.horizontalArrowMoved);
    report.cases.push(item);await page.screenshot({path:path.join(out,`layout-${item.page}-${width}.png`),fullPage:true});
   }
  }
  report.complete=report.cases.length===4&&report.cases.every(item=>item.passed)&&report.pageErrors.length===0;
 }catch(error){report.failure_class=error.name;report.failure_locations=String(error.stack||'').split('\n').filter(line=>/^\s+at /.test(line));process.exitCode=1;}
 finally{await context?.close();await browser?.close();report.browser_close_returned=true;fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2),{flag:'wx'});if(!report.complete)process.exitCode=1;console.log(JSON.stringify({complete:report.complete,passed:report.cases.filter(row=>row.passed).length,total:report.cases.length}));}
})();
