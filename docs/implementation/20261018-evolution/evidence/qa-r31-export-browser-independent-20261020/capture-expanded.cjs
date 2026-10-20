'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=process.env.QA_R31_ROOT,privateRoot=process.env.QA_R31_PRIVATE,name=process.argv[2];
assert.ok(['current33_export_context','current33_export_controls','current33_member_link_export','progress_export'].includes(name));
const file=path.join(root,'tests/e2e',name+'.cjs');let expanded=null;
class CaptureModule{constructor(){this.paths=[];}_compile(value){assert.equal(expanded,null);expanded=value;}}
vm.runInNewContext(fs.readFileSync(file,'utf8'),{require:value=>value==='node:module'?CaptureModule:require(value),__filename:file,__dirname:path.dirname(file),module:{paths:[]},process:{env:{}},console},{filename:file});
assert.equal(typeof expanded,'string');
fs.writeFileSync(path.join(privateRoot,name+'-original-expanded.cjs'),expanded);
