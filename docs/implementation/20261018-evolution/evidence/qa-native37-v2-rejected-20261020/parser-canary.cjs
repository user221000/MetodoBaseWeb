'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const input=JSON.parse(fs.readFileSync(0,'utf8')),parser=require(process.argv[2]);
const results=[];
try{assert.equal(parser.sessionVersion(input.token),input.expected_session_version);results.push({case:'Actual issuer2part canonical session_version parses as integer precondition only',passed:true});}
catch(error){results.push({case:'Actual issuer2part canonical session_version parses as integer precondition only',passed:false,error_class:error.name});}
console.log(JSON.stringify({scope:'Pure test input from actual issuer/decoder; parsed claims never establish authority; no HTTP/service',total:1,passed:results.filter(r=>r.passed).length,results}));
if(results.some(r=>!r.passed))process.exitCode=1;
