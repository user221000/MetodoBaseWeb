/* Real history share handler in a synthetic browser with two distinct plans. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../web/templates/planes.html'),'utf8');
const start=html.indexOf("shareButton.addEventListener('click', async () => {");
const end=html.indexOf("\n          tr.querySelector('td:last-child')",start);
assert.ok(start>0&&end>start);
const handler=html.slice(start,end);
function deferred(){let resolve;const promise=new Promise(done=>{resolve=done});return{resolve,promise};}
function fixture(options={}){
 let session=1, pending=options.pending, requests=[],shares=[];
 const feedback={textContent:''}, navigator={
  canShare:options.unsupported?undefined:()=>!options.cannotShare,
  share:options.unsupported?undefined:async input=>{shares.push(input);if(options.cancel)throw Object.assign(Error(),{name:'AbortError'});}
 };
 const Api={session:{capture:()=>session,check:value=>{if(value!==session)throw Error('changed')}},
  planes:{obtenerPdfPorPlan:async id=>{requests.push(id);if(pending&&id===1)await pending;return new Blob(['%PDF-plan-'+id],{type:'application/pdf'});}}};
 const buttons=[1,2].map(()=>({textContent:'WhatsApp',disabled:false,addEventListener(_,fn){this.click=fn;}}));
 const context=vm.createContext({navigator,Api,File,feedback,verifyAccount:async()=>{}});
 vm.runInContext(`let sessionChanged=false,requestEpoch=1,shareSerial=0,preparedShare=null;
 function clearPreparedShare(){shareSerial++;if(preparedShare)preparedShare.button.textContent='WhatsApp';preparedShare=null;}
 function wire(p,shareButton,epoch){${handler}}
 globalThis.bind=(id,button)=>wire({id},button,1);
 globalThis.invalidate=()=>{sessionChanged=true;requestEpoch++;clearPreparedShare()};
 globalThis.paginate=()=>{requestEpoch++;clearPreparedShare()};`,context);
 buttons.forEach((button,i)=>context.bind(i+1,button));
 return {buttons,requests,shares,feedback,invalidate:()=>context.invalidate(),paginate:()=>context.paginate(),changeSession:()=>session++};
}
(async()=>{
 const f=fixture();await f.buttons[0].click();assert.deepEqual(f.requests,[1]);assert.equal(f.shares.length,0);
 const action=f.buttons[0].click();assert.equal(f.shares.length,1,'share starts during activation');await action;
 assert.equal(await f.shares[0].files[0].text(),'%PDF-plan-1');
 const race=deferred(),r=fixture({pending:race.promise});const old=r.buttons[0].click();await Promise.resolve();await Promise.resolve();
 await r.buttons[1].click();race.resolve();await old;await r.buttons[1].click();
 assert.equal(r.shares.length,1);assert.equal(await r.shares[0].files[0].text(),'%PDF-plan-2');
 const s=fixture();await s.buttons[0].click();s.changeSession();await s.buttons[0].click();assert.equal(s.shares.length,0);
 const page=fixture();await page.buttons[0].click();page.paginate();await page.buttons[0].click();assert.equal(page.shares.length,0);
 const cancelled=fixture({cancel:true});await cancelled.buttons[0].click();await cancelled.buttons[0].click();assert.match(cancelled.feedback.textContent,/canceló/);
 for(const option of [{unsupported:true},{cannotShare:true}]){const x=fixture(option);await x.buttons[0].click();assert.equal(x.shares.length,0);assert.match(x.feedback.textContent,/Descarga/);}
 console.log('Plan history share independent review: 7 scenarios passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
