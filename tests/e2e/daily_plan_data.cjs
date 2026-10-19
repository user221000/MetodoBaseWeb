/* Pure R24 quantities and source selections. No browser/network/clinical claims. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=path.resolve(__dirname,'../../web/static/js/plan-diario-datos.js'),context={window:{}};
vm.createContext(context);if(fs.existsSync(source))vm.runInContext(fs.readFileSync(source,'utf8'),context);
const model=context.window.PlanDayData,tests=[];const test=(name,body)=>tests.push({name,body});
const option=(id,grams)=>({alimento:id,gramos:grams,equivalencia:'2 cucharadas (texto que no se convierte)'});
const meal=()=>({tipo_plan:'opciones',proteinas:{opciones:[option('pollo',.25),option('pescado',75)]},carbohidratos:{opciones:[option('arroz',30)]},grasas:{opciones:[]},vegetales:[option('brocoli',12.5)]});
const plan=()=>Object.fromEntries(['desayuno','almuerzo','comida','cena'].map(name=>[name,meal()]));
test('Four real meals preserve decimal grams and equivalence labels',()=>{
  const result=model.menu(plan(),['pollo','arroz','brocoli']);assert.equal(result.length,4);
  assert.equal(result[0].groups.proteinas[0].grams,.25);assert.equal(result[0].groups.proteinas[0].unit,'g');assert.match(result[0].groups.proteinas[0].equivalence,/cucharadas/);
});
test('Opening a menu never selects or records anything',()=>assert.equal(model.select(model.menu(plan(),['pollo']),{}).length,0));
test('Only explicitly selected options and vegetables enter a draft',()=>{
  const rows=model.select(model.menu(plan(),['pollo','arroz','brocoli']),{desayuno:{proteinas:0,include_vegetables:true}});
  assert.equal(rows.length,2);assert.equal(rows[0].food_id,'pollo');assert.equal(rows[1].food_id,'brocoli');
});
test('Repetition is an explicit inclusive date period, using quantity not equivalence text',()=>{
  const rows=model.select(model.menu(plan(),['pollo']),{desayuno:{proteinas:0}}),result=model.shopping(rows,'2026-10-19','2026-10-21');
  assert.equal(result.days,3);assert.equal(result.items[0].grams,.75);assert.equal(result.items[0].unit,'g');assert.equal(result.start,'2026-10-19');
});
test('Equal canonical IDs merge across meals; different IDs do not',()=>{
  const rows=model.select(model.menu(plan(),['pollo','arroz']),{desayuno:{proteinas:0},cena:{proteinas:0,carbohidratos:0}}),r=model.shopping(rows,'2026-10-19','2026-10-19');
  assert.equal(r.items.length,2);assert.equal(r.items.find(row=>row.food_id==='pollo').grams,.5);
});
test('Unverified labels remain separate lines even when equal',()=>{
  const rows=model.select(model.menu(plan()),{desayuno:{proteinas:0},cena:{proteinas:0}}),r=model.shopping(rows,'2026-10-19','2026-10-19');
  assert.equal(r.items.length,2);assert.equal(r.items[0].food_id,null);
});
for(const value of ['30 g',NaN,Infinity,-1,0,null,true])test('Ambiguous or invalid grams never become a zero portion: '+String(value),()=>{
  const p=plan();p.desayuno.proteinas.opciones[0].gramos=value;const r=model.menu(p,['pollo']);assert.equal(r[0].available,false);
  assert.throws(()=>model.select(r,{desayuno:{proteinas:0}}));
});
test('Fixed canonical numeric menu needs an explicit complete-menu choice',()=>{
  const p=plan();p.desayuno={alimentos:{pollo:25.5,arroz:50}};const menu=model.menu(p,['pollo','arroz']);
  assert.equal(model.select(menu,{}).length,0);const rows=model.select(menu,{desayuno:{include_fixed_menu:true}});assert.equal(rows.length,2);assert.equal(rows[0].grams,25.5);
  assert.throws(()=>model.select(menu,{desayuno:{include_fixed_menu:true,proteinas:0}}));
});
test('Free-form legacy recipes are unavailable instead of parsed into food quantities',()=>{
  const p=plan();p.cena={alimentos:{'Plato a gusto':'una porción'}};assert.equal(model.menu(p)[3].available,false);
});
for(const pair of [['2026-02-30','2026-03-01'],['2026-10-21','2026-10-19'],['2026-01-01','2026-03-04'],['today','today']])test('Date range rejected: '+pair.join('/'),()=>assert.throws(()=>model.shopping([],pair[0],pair[1])));
test('Existing 62-day calendar transfer bound is accepted, without a commercial limit',()=>assert.equal(model.shopping([],'2026-01-01','2026-03-03').days,62));
test('Recorded list sums consumed snapshots only, regardless of completed checkbox',()=>{
  const value={days:[{local_date:'2026-10-19',meals:{desayuno:{completed:false,source_plan_id:1,foods:[{food_id:'pollo',grams:5}]}}},{local_date:'2026-10-20',meals:{cena:{completed:true,source_plan_id:2,foods:[{food_id:'pollo',grams:7}]}}}]};
  const result=model.recorded(value);assert.equal(result.items[0].grams,12);assert.equal(result.items[0].unit,'g');assert.equal(result.recordedMeals,2);
});
test('Missing meals are visible as absent data, never fake empty successes',()=>{const p=plan();delete p.comida;assert.equal(model.menu(p)[2].available,false);});
test('Out-of-range selected index never silently substitutes another option',()=>assert.throws(()=>model.select(model.menu(plan()),{desayuno:{proteinas:99}})));
(async()=>{const results=[];for(const entry of tests){try{await entry.body();results.push({name:entry.name,passed:true});}catch(error){results.push({name:entry.name,passed:false,error:error.message});}}
console.log(JSON.stringify({scope:'Pure quantities/selections only, no substitutions or clinical authority',passed:results.filter(r=>r.passed).length,total:results.length,results},null,2));if(results.some(r=>!r.passed))process.exitCode=1;})();
