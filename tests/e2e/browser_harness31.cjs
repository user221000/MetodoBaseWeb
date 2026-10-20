/* Shared current browser fixture. Legacy values is a RAM observer, never Storage. */
'use strict';
const fs=require('node:fs'),Module=require('node:module'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const file=require('node:path').join(__dirname,'browser_session31.cjs'),prefix=fs.readFileSync(file,'utf8').split('const rows=[];')[0];
const shared=new Module(file,module);shared.filename=file;shared.paths=module.paths;shared._compile(prefix+'\nmodule.exports={world,tick};',file);
const {world,tick}=shared.exports;
async function closed(transport=async(_url,options)=>Response.json({ack:true,operation:{request_key:options.headers['Idempotency-Key']}}),access='synthetic-access'){
  const w=world(),t=w.tab(),calls=[];let boot=true;
  t.sandbox.location.href='';
  t.hook(async call=>{
    if(boot)return Response.json({token:access,session_mode:'browser'});
    calls.push({url:call.path,...call.options});
    let response=await transport(call.path,call.options);
    if(call.path.startsWith('/api/auth/')&&call.options.method==='POST'&&typeof response.json==='function'){
      let data;try{data=await (response.clone?response.clone():response).json();}catch{return response;}
      if(response.status===202&&data.mfa_required===true){data={...data,session_mode:'browser'};w.jar.account=null;}
      else if(response.status===200&&(typeof data.token==='string'||typeof data.access_token==='string')){data={...data,token:data.token||data.access_token,session_mode:'browser'};delete data.refresh_token;}
      else return response;
      response=Response.json(data,{status:response.status,headers:response.headers});
    }
    return response;
  });
  await t.api.session.ready;boot=false;
  const values={get(key){if(key==='mb_token')return t.api.getToken()||undefined;if(key==='mb_refresh_token')return undefined;return w.shared.get(key);},has(key){return this.get(key)!==undefined;}};
  function invalidate(){const epoch=crypto.randomUUID();w.shared.set('mb_session_epoch',epoch);w.jar.account='B';t.dispatch({type:'storage',key:'mb_session_epoch',newValue:epoch});}
  async function dispatched(){for(let attempt=0;attempt<10&&!calls.length;attempt++)await tick();assert.ok(calls.length>0,'The controlled request must start before its external boundary');}
  return{api:t.api,calls,values,window:t.sandbox,context:t.context,world:w,invalidate,dispatched};
}
module.exports={closed,world,tick};
