/* Advisory severity distinction; does not replace or relax immutable V5 criteria. */
const fs=require('node:fs'),Module=require('node:module');
const s=fs.readFileSync(__dirname+'/vm_review_v5.cjs','utf8');
const marker='(async()=>{const results=[];for(const t of tests)';
if(s.split(marker).length!==2)throw Error('Unexpected immutable V5 runner');
const extra=String.raw`
for(const event of ['metodobase-session-changed','storage','pagehide'])test('ADVISORY hidden discard remains inert after '+event,async()=>{
 const e=await integratedFixture();e.widget();await flush();await chosen(e);e.emit(event,event==='storage'?{key:'mb_token'}:{});
 const button=e.map['publication-diary-discard'];assert.equal(button.hidden,true);assert.equal(e.shopping.source,null);assert.equal(e.map['publication-diary-records'].textContent,'');
 const before=objects(e).length;await button.fire('click');assert.equal(objects(e).length,before);assert.equal(e.shopping.source,null);assert.equal(e.map['publication-diary-records'].textContent,'');
});
`;
const updated=s.replace(marker,extra+'\n'+marker.replace('of tests)','of tests.filter(t=>t.name.startsWith("ADVISORY")))'));
const m=new Module(__filename,module);m.filename=__filename;m.paths=module.paths;m._compile(updated,__filename);
