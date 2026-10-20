'use strict';
/* Parse actual rendered scripts without executing providers or browser I/O. */
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));let count=0;
for(const match of input.html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)){
  if(/\bsrc\s*=/.test(match[1])||/\btype\s*=\s*["']application\/json/.test(match[1]))continue;
  new vm.Script(match[2],{filename:input.route+':inline-'+(++count)});
}
process.stdout.write(JSON.stringify({parsed:true,inline_scripts:count}));
