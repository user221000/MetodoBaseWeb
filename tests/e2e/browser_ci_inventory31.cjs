/* Read historical case registrations without invoking their legacy credential fixtures. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const allowed=new Set(['auth_refresh','auth_refresh_storage','auth_refresh_security_review','personal_logout','personal_logout_ack','session_revision_events','session_expiry_fences','session_expiry_security','member_link_context']);
function inventory(name){
 assert.ok(allowed.has(name));const file=path.join(__dirname,name+'.cjs'),raw=fs.readFileSync(file,'utf8'),matches=[...raw.matchAll(/\(async\s*\(\)\s*=>/g)],last=matches.at(-1);assert.ok(last,'Historical registration boundary must be explicit');
 const prefix=raw.slice(0,last.index),candidate=new Module(file,module);candidate.filename=file;candidate.paths=module.paths;
 const previous=process.argv;try{process.argv=[process.execPath,file];candidate._compile(prefix+'\nmodule.exports=(typeof cases!=="undefined"?cases:tests).map((entry,index)=>({index:index+1,name:Array.isArray(entry)?entry[0]:entry.name,body:String(Array.isArray(entry)?entry[1]:(entry.body||entry.run))}));',file);}finally{process.argv=previous;}
 const rows=candidate.exports;assert.ok(Array.isArray(rows)&&rows.length>0);assert.equal(new Set(rows.map(row=>row.name)).size,rows.length);
 return{path:'tests/e2e/'+name+'.cjs',sha256:crypto.createHash('sha256').update(raw).digest('hex'),cases:rows};
}
module.exports={inventory};
if(require.main===module){const report={};for(const name of allowed)report[name]=inventory(name);console.log(JSON.stringify(report,null,2));}
