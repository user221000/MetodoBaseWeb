/* Own machine ACK contract; synthetic transport, no server/protocol authority claim. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(process.env.DIARY_UI_API_SOURCE||path.resolve(__dirname,'../../web/static/js/api.js'),'utf8');
function fixture(body,status=200,network=false){const values=new Map([['mb_token','synthetic-ack-access'],['mb_refresh_token','synthetic-ack-refresh'],['mb_daily_unidentified','UNIDENTIFIED {invalid']]);const context=vm.createContext({localStorage:{getItem(key){assert.notEqual(key,'mb_daily_unidentified');return values.get(key)||null;},setItem(key,value){assert.notEqual(key,'mb_daily_unidentified');values.set(key,value);},removeItem(key){assert.notEqual(key,'mb_daily_unidentified');values.delete(key);}},fetch:async()=>{if(network)throw Error('Synthetic lost response');return Response.json(body,{status});},window:{addEventListener(){},removeEventListener(){},location:{}},document:{},Blob,URL,URLSearchParams,File,FormData,setTimeout,clearTimeout});vm.runInContext(source+'\nglobalThis.api=Api;',context);return{api:context.api,values};}
const legacyMessage='Sesión cerrada. Todas las sesiones revocadas.';
const cases=[
 ['Legacy message-only remains local/unconfirmed',{message:legacyMessage},200,false,false],
 ['Empty JSON remains local/unconfirmed',{},200,false,false],
 ['Explicit negative ACK remains local/unconfirmed',{success:false},200,false,false],
 ['String true is not a machine ACK',{success:'true'},200,false,false],
 ['Number one is not a machine ACK',{success:1},200,false,false],
 ['Null body is not a machine ACK',null,200,false,false],
 ['Array body is not a machine ACK',[],200,false,false],
 ['Translated successful wording without flag is unconfirmed',{message:'Logout complete'},200,false,false],
 ['Exact boolean ACK plus existing message confirms remote close',{success:true,message:legacyMessage},200,false,true],
 ['Boolean ACK does not depend on localized message',{success:true},200,false,true],
 ['HTTP failure with a true flag cannot confirm remote close',{success:true},500,false,false],
 ['Lost POST can close locally but cannot confirm remote commit',{},200,true,false],
];
(async()=>{const results=[];for(const [name,body,status,network,expected]of cases){try{const e=fixture(body,status,network),result=await e.api.auth.logout();assert.equal(result.state,'closed_local');assert.equal(result.server_confirmed,expected);e.api.usuario.validarContexto(result.context);assert.equal(e.values.has('mb_token'),false);assert.equal(e.values.has('mb_refresh_token'),false);assert.equal(e.values.get('mb_daily_unidentified'),'UNIDENTIFIED {invalid');results.push({case:name,passed:true});}catch(error){results.push({case:name,passed:false,error:error.message});}}console.log(JSON.stringify({scope:'Synthetic machine-ACK helper cases only; no browser or backend commit proof',passed:results.filter(r=>r.passed).length,total:results.length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
