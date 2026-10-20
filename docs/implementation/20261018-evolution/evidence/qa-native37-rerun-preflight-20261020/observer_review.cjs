'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root='F:/mb-qa-native37-20261020',source=fs.readFileSync(path.join(root,'tests/e2e/native37_account_notifications_qa_v2.cjs'),'utf8');
const framing=fs.readFileSync(path.join(root,'tests/e2e/browser_compat31.cjs'),'utf8');
const{balanced}=vm.runInNewContext(framing.slice(framing.indexOf('function skipString('),framing.indexOf('const fixtureName='))+'\n({balanced})',{assert});
const start=source.indexOf('function errorObservation('),parameters=source.indexOf('(',start),parameterEnd=balanced(source,parameters),body=source.indexOf('{',parameterEnd),end=balanced(source,body);
const observe=vm.runInNewContext(source.slice(start,end)+'\nerrorObservation;',{URL,Set,Number,String});
const base='http://127.0.0.1:8802',scripts=new Set(['/static/js/notifications36.js']),pages=new Set(['/recordatorios']);
const results=[],test=(name,run)=>{run();results.push({case:name,passed:true});};
test('Observer keeps bounded same-origin pathname/line only and never message/query/hash',()=>{
 const value=observe({name:'TypeError',message:'PRIVATE_MESSAGE_SENTINEL',stack:'TypeError: PRIVATE_MESSAGE_SENTINEL\n    at mount (http://127.0.0.1:8802/static/js/notifications36.js?proof=PRIVATE_QUERY_SENTINEL#PRIVATE_FRAGMENT_SENTINEL:102:9)'},base,scripts,pages,'own-case');
 const wire=JSON.stringify(value);assert.equal(value.class,'TypeError');assert.equal(value.frames.length,1);assert.equal(value.frames[0].pathname,'/static/js/notifications36.js');assert.equal(value.frames[0].line,102);assert.equal(value.frames[0].column,9);
 for(const fragment of['PRIVATE_MESSAGE_SENTINEL','PRIVATE_QUERY_SENTINEL','PRIVATE_FRAGMENT_SENTINEL','http:','?proof='])assert.equal(wire.includes(fragment),false);
});
test('Observer rejects foreign origin, unlisted pathname and opaque non-URL frames',()=>{
 const value=observe({name:'Error',stack:'Error\n at x (https://foreign.invalid/static/js/notifications36.js:1:2)\n at y (http://127.0.0.1:8802/private/opaque:3:4)\n at local (C:/private/opaque.js:5:6)'},base,scripts,pages,null);assert.equal(value.frames.length,0);
});
test('Observer caps stack metadata at eight frames and serializes no arbitrary error name',()=>{
 const value=observe({name:'PRIVATE_NAME_SENTINEL',stack:'hidden\n'+Array(12).fill(' at x (http://127.0.0.1:8802/recordatorios:2:3)').join('\n')},base,scripts,pages,null);assert.equal(value.class,'OtherError');assert.equal(value.frames.length,8);assert.equal(JSON.stringify(value).includes('PRIVATE_NAME_SENTINEL'),false);
});
test('Observer accepts absent stack and rejects nonpositive line metadata',()=>{
 assert.equal(observe({name:'TypeError'},base,scripts,pages,null).frames.length,0);assert.equal(observe({name:'Error',stack:'Error\n at x (http://127.0.0.1:8802/recordatorios:0:2)'},base,scripts,pages,null).frames.length,0);
});
test('All original business assertion calls and final pageErrors oracle remain exact',()=>{
 const old=fs.readFileSync(path.join(root,'tests/e2e/native37_account_notifications_qa.cjs'),'utf8');
 const assertions=text=>[...text.matchAll(/\bassert\.[A-Za-z]+\(/g)].map(match=>text.slice(match.index,balanced(text,text.indexOf('(',match.index))));
 assert.deepEqual(assertions(source),assertions(old));assert.ok(source.includes('assert.deepEqual(report.pageErrors,[])'));
 assert.equal(source.match(/\.textContent\.includes\('El resultado es incierto'\)/g).length,1);
});
console.log(JSON.stringify({scope:'Pure observer and assertion-source controls only, no Chrome/HTTP/PG',total:results.length,passed:results.length,results}));
