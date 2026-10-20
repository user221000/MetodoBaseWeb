/* Independent geometry oracle. No authentication or product mutation. */
'use strict';
const assert=require('node:assert/strict');

function overlap(a,b){
 return Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
}
function assertUncovered(value){
 assert.equal(value.heading_count,1,'One actual heading must exist');
 assert.equal(value.button_count,1,'One actual mobile menu control must exist');
 assert.ok(value.heading.width>0&&value.heading.height>0,'Actual heading has geometry');
 assert.ok(value.point_in_view,'Actual heading text has a point in viewport');
 assert.equal(overlap(value.heading,value.button),0,'Mobile menu must not cover the focused/scrolled heading');
 assert.equal(value.point_hits_menu,false,'Actual heading text hit test must not resolve to menu');
 assert.equal(value.horizontal_overflow,false,'No horizontal page overflow');
}
async function inspect(page,selector){
 await page.locator(selector).scrollIntoViewIfNeeded();
 await page.locator(selector).evaluate(node=>node.scrollIntoView({block:'start',inline:'nearest',behavior:'instant'}));
 const observation=await page.evaluate(selector=>{
  const heading=document.querySelector(selector),button=document.querySelector('#btn-hamburger');
  const rect=node=>{const r=node?.getBoundingClientRect();return r?{left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}:null;};
  const box=rect(heading),menu=rect(button);let point=null;
  if(heading){const range=document.createRange();range.selectNodeContents(heading);const first=Array.from(range.getClientRects()).find(r=>r.width&&r.height&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth);if(first)point={x:Math.max(0,Math.min(innerWidth-1,(first.left+first.right)/2)),y:Math.max(0,Math.min(innerHeight-1,(first.top+first.bottom)/2))};}
  const hit=point?document.elementFromPoint(point.x,point.y):null;
  return{heading_count:document.querySelectorAll(selector).length,button_count:document.querySelectorAll('#btn-hamburger').length,heading:box,button:menu,point_in_view:!!point,point_hits_menu:!!hit&&!!button&&(hit===button||button.contains(hit)),horizontal_overflow:document.documentElement.scrollWidth>innerWidth,active_element:document.activeElement?.id||null};
 },selector);
 try{assertUncovered(observation);}catch(error){error.observation=observation;throw error;}return observation;
}
module.exports={overlap,assertUncovered,inspect};

if(require.main===module&&process.argv.includes('--self-test')){
 const good={heading_count:1,button_count:1,heading:{left:16,top:0,right:304,bottom:45,width:288,height:45},button:{left:16,top:-70,right:60,bottom:-26,width:44,height:44},point_in_view:true,point_hits_menu:false,horizontal_overflow:false};
 assertUncovered(good);
 for(const mutant of [{...good,button:{...good.button,top:16,bottom:60}},{...good,heading_count:0},{...good,point_hits_menu:true},{...good,horizontal_overflow:true}])assert.throws(()=>assertUncovered(mutant));
 console.log(JSON.stringify({positive:1,negative_controls_rejected:4,Chrome_executed:false}));
}
