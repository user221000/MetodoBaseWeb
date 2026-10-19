/* Frozen author regression: a400 can follow a durable commit; it grants no new intent. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const source=fs.readFileSync(process.argv[2] || path.join(__dirname,'../../web/static/js/usuario-plan-operacion.js'),'utf8');
const cases=[];
for(const code of [undefined,'generation_unavailable'])cases.push({name:'Durable publication then400 '+String(code),body:async()=>{
 const calls=[],published=new Map();let debit=0;const states=[],results=[];
 const Api={usuario:{contexto:async()=>({revision:1,subject:'synthetic-A',me:{id:'synthetic-A'}}),validarContexto(){},verificarContexto:async()=>{},generarPlan:async key=>{
  calls.push(key);
  if(published.has(key))return published.get(key);
  const result={plan_id:++debit,plan:{synthetic:true},tiene_pdf:true};published.set(key,result);
  throw Object.assign(new Error('Synthetic400 after durable publication'),{status:400,code});
 }}};
 const context=vm.createContext({Api,crypto,setTimeout,clearTimeout,window:{addEventListener(){}}});vm.runInContext(source,context);
 const operation=context.window.PersonalPlanOperation.create({onState:value=>states.push(value),onResult:value=>results.push(value)});
 await operation.start();await operation.generate();
 assert.equal(operation.state,'unconfirmed','Status400 or a generic worker failure code cannot prove non-publication');
 await operation.generate(true);assert.equal(calls.length,1,'Ambiguous400 cannot start another UUID');
 await operation.generate();assert.equal(calls.length,2);assert.equal(calls[0],calls[1]);assert.equal(debit,1);assert.equal(results.length,1);assert.equal(results[0].plan_id,1);assert.equal(operation.state,'completed');
}});
(async()=>{const results=[];for(const entry of cases){try{await entry.body();results.push({case:entry.name,passed:true});}catch(error){results.push({case:entry.name,passed:false,error:error.message});}}console.log(JSON.stringify({scope:'Synthetic durable-state/reply-order model only; no backend commit claim',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),passed:results.filter(row=>row.passed).length,total:results.length,results},null,2));if(results.some(row=>!row.passed))process.exitCode=1;})().catch(error=>{console.error(error.message);process.exitCode=1;});
