/* Reuse21 unchanged consumer/controls assertions with API29's additive DTO fixture.
 * New cases exercise seventh-dataset pages, budgets and recipient OWNER context.
 */
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
let source=fs.readFileSync(path.join(__dirname,'personal_export_context.cjs'),'utf8');
const replaceOnce=(from,to)=>{if(source.split(from).length!==2)throw Error('Historical fixture marker changed');source=source.replace(from,to);};
replaceOnce("'personal_diary','member_links'];","'personal_diary','member_links','progress_consents'];");
replaceOnce("coverage:'account_persisted_personal_space_and_active_member_link_metadata'","progress_consents:'own_append_only_scope_metadata',coverage:'account_persisted_personal_space_active_member_links_and_own_progress_consents'");
replaceOnce('async function fixture(){','async function fixture(options={}){');
replaceOnce("vm.runInContext(apiSource+'\\nglobalThis.api=Api;',context);", "if(options.recipient)node('personal-data-section').dataset.exportContext='recipient';if(options.owner)me={...identity,tipo:'gym',role:'owner'};vm.runInContext(apiSource+'\\nglobalThis.api=Api;',context);");
const controls=fs.readFileSync(path.join(__dirname,'personal_export_controls.cjs'),'utf8').match(/const additions=String.raw`([\s\S]*?)`;/)[1];
const additions=String.raw`
const LINK_A='10000000-0000-4000-8000-00000000000A',LINK_B='20000000-0000-4000-8000-00000000000B';
function linked(id=LINK_A){return{id,status:'active',version:2,gym_name:'Synthetic gym',client_display_name:'Synthetic recipient',accepted_at:'2026-10-19T12:00:00Z',publication:null};}
test('Seventh dataset keeps a stable uppercase cursor and filters finished collections from part2',async()=>{
 const e=await fixture();e.setTransport(async url=>{const second=new URL(url,'http://testserver').searchParams.get('after_member_link')===LINK_A;const d=page();d.member_links={records:[linked(second?LINK_B:LINK_A)],next_after:second?null:LINK_A};return Response.json(d);});
 await e.prepare();assert.equal(e.downloads.length,1);assert.equal(e.counts.get('member_links').textContent,'1');assert.equal(e.node('privacy-next').hidden,false);
 e.node('privacy-next').click();await flush();assert.equal(e.downloads.length,2);const file=JSON.parse(await e.downloads[1].text());assert.deepEqual(Object.keys(file.collections),['member_links']);assert.equal(file.collections.member_links.records[0].id,LINK_B);assert.equal(file.manifest.all_available_pages_prepared,true);assert.equal(file.manifest.collections.personal_diary.status,'included_in_previous_parts');
 assert(e.requests.some(row=>row.url.includes('after_member_link='+LINK_A)));e.intact();
});
test('Recipient OWNER exports only own active metadata without adopting six personal collections',async()=>{
 const e=await fixture({recipient:true,owner:true});e.setTransport(async()=>{const d=page();for(const name of names)d[name]={records:[],next_after:null};d.member_links.records=[linked()];d.scope.personal_space=false;return Response.json(d);});await e.prepare();assert.equal(e.downloads.length,1);const file=JSON.parse(await e.downloads[0].text());assert.equal(file.collections.member_links.records.length,1);for(const name of names.filter(n=>n!=='member_links'))assert.deepEqual(file.collections[name].records,[]);assert.equal(file.scope.personal_space,false);assert.equal(file.scope.member_links,'active_recipient_metadata_only');e.intact();
});
test('Missing seventh dataset fails the whole page without claiming completion',async()=>{
 const e=await fixture();e.setTransport(async()=>{const d=page();delete d.member_links;return Response.json(d);});await e.prepare();assert.equal(e.downloads.length,0);assert.equal(e.node('privacy-error').hidden,false);assert(!e.node('privacy-status').textContent.includes('todas las partes'));
});
for(const [field,bad] of [['status',{...linked(),status:'revoked'}],['recipient_user_id',{...linked(),recipient_user_id:'synthetic-foreign'}],['publication',{...linked(),publication:{id:LINK_B,version:1,published_at:'2026-10-19T12:00:00Z',object_key:'must-not-export'}}]])test('Non-contract or revoked member metadata is rejected entirely: '+field,async()=>{
 const e=await fixture();e.setTransport(async()=>{const d=page();d.member_links.records=[bad];return Response.json(d);});await e.prepare();assert.equal(e.downloads.length,0);assert.equal(e.node('privacy-error').hidden,false);e.intact();
});
test('Oversize member section is rejected before constructing an export Blob',async()=>{
 const e=await fixture();e.setTransport(async()=>{const d=page();d.member_links.records=[{...linked(),gym_name:'S'.repeat(131073)}];return Response.json(d);});await e.prepare();assert.equal(e.downloads.length,0);assert.equal(e.blobCount,0);
});
test('Owner personal payload in recipient context fails closed instead of adopting it',async()=>{
 const e=await fixture({recipient:true,owner:true});e.setTransport(async()=>{const d=page();d.scope.personal_space=false;return Response.json(d);});await e.prepare();assert.equal(e.downloads.length,0);assert.equal(e.node('privacy-error').hidden,false);
});
test('Recipient OWNER never adopts personal_space true or a personal portfolio from an inconsistent DTO',async()=>{
 const e=await fixture({recipient:true,owner:true});e.setTransport(async()=>Response.json(page()));await e.prepare();assert.equal(e.downloads.length,0);assert.equal(e.blobCount,0);assert.equal(e.node('privacy-error').hidden,false);
});
test('A failed seventh-dataset continuation preserves prepared counts and retries its same cursor',async()=>{
 const e=await fixture();let continuation=0;e.setTransport(async url=>{const d=page();if(!new URL(url,'http://testserver').searchParams.has('after_member_link'))d.member_links={records:[linked()],next_after:LINK_A};else{continuation++;d.member_links={records:[continuation===1?{...linked(LINK_B),recipient_user_id:'must-not-export'}:linked(LINK_B)],next_after:null};}return Response.json(d);});await e.prepare();e.node('privacy-next').click();await flush();assert.equal(e.downloads.length,1);assert.equal(e.counts.get('member_links').textContent,'1');assert.equal(e.node('privacy-again').hidden,false);e.node('privacy-next').click();await flush();assert.equal(e.downloads.length,2);assert.equal(e.counts.get('member_links').textContent,'2');assert.equal(e.requests.filter(row=>row.url.includes('after_member_link='+LINK_A)).length,2);
});
test('Total UTF8 response budget is enforced without producing a partial file',async()=>{
 const e=await fixture();e.setTransport(async()=>{const d=page();d.account.synthetic_padding='😀'.repeat(266241);return Response.json(d);});await e.prepare();assert.equal(e.downloads.length,0);assert.equal(e.blobCount,0);assert.equal(e.node('privacy-error').hidden,false);
});
`;
const marker='(async()=>{const results=[];';if(source.split(marker).length!==2)throw Error('Historical runner changed');
const testModule=new Module(__filename,module);testModule.filename=__filename;testModule.paths=module.paths;
testModule._compile(source.replace(marker,controls+'\n'+additions+'\n'+marker),__filename);
