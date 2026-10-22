'use strict';
// The VM tests never spawn Git or another host process. Two frozen read-Git
// transports return authenticated original fixture data without child I/O.
require('./browser_offline31.cjs');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sources=new Map([
 ['6ee27e3c:tests/e2e/security_browser31_ui_peer.cjs',{
  file:'security-browser31-6ee27e3c.cjs.RAW',sha256:'4c8581ac6280f67fbfb201a6cfa30ea41b72948a3cf3bd493fe1bc3d3f320602'}],
 ['08de03f3ecbbc8d8a10bac193f12efadf92312ad:tests/e2e/security_account37_boundaries_peer.cjs',{
  file:'account37-boundaries-08de03f3.cjs.RAW',sha256:'ce0c90172de301e5e39411be919ffcb8117d98c3750f0baaa28abeb1ea8a9f87'}]
]);
require('node:child_process').execFileSync=function(command,args,options){
 if(command!=='git'||!Array.isArray(args)||args.length!==2||args[0]!=='show'||!sources.has(args[1])
   ||!options||Object.keys(options).length!==1||options.encoding!=='utf8'){
  throw Error('Current web VM gate: undeclared child transport disabled');
 }
 const input=sources.get(args[1]);
 const raw=fs.readFileSync(path.join(__dirname,'../ci_web37/fixtures',input.file));
 if(crypto.createHash('sha256').update(raw).digest('hex')!==input.sha256){
  throw Error('Current web VM gate: original read-Git fixture identity differs');
 }
 return new TextDecoder('utf-8',{fatal:true}).decode(raw);
};
