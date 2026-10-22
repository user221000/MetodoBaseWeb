/* Private fsync journal. Only enumerated group/status metadata; never values or errors. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
function createJournal({file,groups,deadlineMs=45000}){
 assert.ok(path.isAbsolute(file));assert.ok(Number.isSafeInteger(groups)&&groups>0&&groups<=64);
 assert.ok(Number.isSafeInteger(deadlineMs)&&deadlineMs>0&&deadlineMs<=120000);
 const parent=path.dirname(file);assert.ok(fs.lstatSync(parent).isDirectory());
 assert.equal(path.resolve(fs.realpathSync(parent)),path.resolve(parent));
 assert.ok(!fs.lstatSync(parent).isSymbolicLink());
 const fd=fs.openSync(file,'wx',0o600),started=process.hrtime.bigint();
 let sequence=0,completed=0,active=false,terminal=false,closed=false;
 const classes=new Set(['Error','AssertionError','TypeError','ReferenceError','SyntaxError','RangeError','TimeoutError']);
 function append(kind,group,error){
  const row={sequence:++sequence,group,kind,elapsed_ms:Number((process.hrtime.bigint()-started)/1000000n)};
  if(error)row.error_class=classes.has(error.name)?error.name:'OtherError';
  fs.writeSync(fd,JSON.stringify(row)+'\n');fs.fsyncSync(fd);
 }
 async function run(group,operation){
  assert.ok(!closed&&!terminal&&!active);assert.equal(group,completed+1);assert.ok(group<=groups);assert.equal(typeof operation,'function');
  active=true;append('START',group);let timer;
  try{
   const limit=new Promise((_,reject)=>{timer=setTimeout(()=>reject(Object.assign(new Error('Private group deadline'),{name:'TimeoutError'})),deadlineMs);});
   const result=await Promise.race([Promise.resolve().then(operation),limit]);
   append('PASS',group);completed++;return result;
  }catch(error){terminal=true;append('FAIL',group,error);throw error;}
  finally{clearTimeout(timer);active=false;}
 }
 function close(){assert.ok(!active&&!closed);fs.fsyncSync(fd);fs.closeSync(fd);closed=true;return{completed,expected:groups,terminal_failure:terminal,complete:completed===groups&&!terminal};}
 return Object.freeze({run,close});
}
module.exports={createJournal};
