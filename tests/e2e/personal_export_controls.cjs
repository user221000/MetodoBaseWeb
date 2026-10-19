/* Own four pre-click regressions; reuse the unchanged17-case author fixture/assertions. */
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const source=fs.readFileSync(path.join(__dirname,'personal_export_context.cjs'),'utf8');
const marker='(async()=>{const results=[];';
if(source.split(marker).length!==2)throw Error('Unexpected author harness runner');
const additions=String.raw`
for(const phase of ['first','repeat'])for(const failure of ['replacement','storage'])test('Pre-click '+failure+' during controls invalidates '+phase+' without rejection, request or false loading status',async()=>{
 const e=await fixture();if(phase==='repeat')await e.prepare();
 const requests=e.requests.length,downloads=e.downloads.length;
 if(failure==='replacement')e.api.saveTokens(B);
 else e.eval("const nativeGet=localStorage.getItem;localStorage.getItem=key=>{if(key==='mb_token'){const error=Error('SYNTHETIC PRIVATE STORAGE');error.name='SecurityError';throw error;}return nativeGet(key);};");
 let rejected=null;try{await e.node(phase==='repeat'?'privacy-again':'privacy-start').click();}catch(error){rejected=error.name;}
 await flush();e.cleared();assert.equal(rejected,null);assert.equal(e.requests.length,requests);assert.equal(e.downloads.length,downloads);
 assert.equal(e.node('privacy-status').textContent.includes('Consultando'),false);assert.ok(e.node('privacy-status').textContent.includes('descartó'));e.intact();
});
`;
const testModule=new Module(__filename,module);testModule.filename=__filename;testModule.paths=module.paths;
testModule._compile(source.replace(marker,additions+'\n'+marker),__filename);
