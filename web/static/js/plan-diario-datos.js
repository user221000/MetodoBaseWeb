/* Source quantities only: no text parsing, nutritional substitutions or persistence. */
(() => {
  'use strict';
  const names=['desayuno','almuerzo','comida','cena'];
  const groups=['proteinas','carbohidratos','grasas'];
  const invalid=()=>new Error('No se pudieron verificar las porciones de esta fuente.');
  function food(raw,known,origin) {
    if(!raw || typeof raw.alimento!=='string' || !raw.alimento || raw.alimento.length>200 ||
        typeof raw.gramos!=='number' || !Number.isFinite(raw.gramos) || raw.gramos<=0 ||
        (raw.equivalencia!=null && (typeof raw.equivalencia!=='string' || raw.equivalencia.length>500)))throw invalid();
    return {food_id:known.has(raw.alimento)?raw.alimento:null,label:raw.alimento,grams:raw.gramos,unit:'g',
      equivalence:raw.equivalencia??null,origin};
  }
  function menu(plan,knownIds=[]) {
    const known=new Set(knownIds);
    return names.map(name=>{
      try {
        const raw=plan?.[name];if(!raw || typeof raw!=='object' || Array.isArray(raw))throw invalid();
        const options=raw.tipo_plan==='opciones' || !!raw.proteinas;
        if(options){
          const result={name,available:true,kind:'options',groups:{},vegetables:[]};
          for(const group of groups){
            const rows=raw[group]?.opciones;if(!Array.isArray(rows) || rows.length>256)throw invalid();
            result.groups[group]=rows.map((row,index)=>food(row,known,{meal:name,group,index}));
          }
          if(!Array.isArray(raw.vegetales) || raw.vegetales.length>32)throw invalid();
          result.vegetables=raw.vegetales.map((row,index)=>food(row,known,{meal:name,group:'vegetales',index}));
          return result;
        }
        if(!raw.alimentos || typeof raw.alimentos!=='object' || Array.isArray(raw.alimentos))throw invalid();
        const rows=Object.entries(raw.alimentos);if(rows.length>32)throw invalid();
        return {name,available:true,kind:'fixed',foods:rows.map(([alimento,gramos],index)=>food({alimento,gramos},known,{meal:name,group:'fixed',index}))};
      }catch{return{name,available:false,reason:'No hay porciones estructuradas verificables para esta comida.'};}
    });
  }
  function select(meals,selections) {
    const result=[];
    for(const entry of meals){
      const chosen=selections[entry.name];if(!chosen)continue;if(!entry.available)throw invalid();
      if(entry.kind==='fixed'){
        if(Object.keys(chosen).some(key=>!['include_fixed_menu'].includes(key)))throw invalid();
        if(chosen.include_fixed_menu===true)result.push(...entry.foods);
        else if(chosen.include_fixed_menu!==false)throw invalid();
      }else{
        for(const group of groups){
          const index=chosen[group];if(index==null)continue;
          if(!Number.isSafeInteger(index) || index<0 || !entry.groups[group][index])throw invalid();
          result.push(entry.groups[group][index]);
        }
        if(chosen.include_vegetables===true)result.push(...entry.vegetables);
        else if(chosen.include_vegetables!=null && chosen.include_vegetables!==false)throw invalid();
        if(Object.keys(chosen).some(key=>!groups.includes(key) && key!=='include_vegetables'))throw invalid();
      }
    }
    if(Object.keys(selections).some(name=>!names.includes(name)))throw invalid();
    return result.map(row=>({...row,origin:{...row.origin}}));
  }
  function ordinal(value){
    if(typeof value!=='string' || !/^\d{4}-\d{2}-\d{2}$/.test(value))throw invalid();
    const [y,m,d]=value.split('-').map(Number),leap=y%4===0&&(y%100!==0||y%400===0);
    if(y<1 || m<1 || m>12 || d<1 || d>[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][m-1])throw invalid();
    const date=new Date(0);date.setUTCFullYear(y,m-1,d);date.setUTCHours(0,0,0,0);return date.getTime()/86400000;
  }
  function sum(rows,multiplier=1){
    const items=[],known=new Map();
    for(const row of rows){
      if(row.unit!=='g' || typeof row.grams!=='number' || !Number.isFinite(row.grams) || row.grams<=0)throw invalid();
      const quantity=row.grams*multiplier;if(!Number.isFinite(quantity))throw invalid();
      const key=row.food_id?row.food_id+'\u0000g':null;
      const target=key?known.get(key):null;
      if(target){target.grams+=quantity;if(!Number.isFinite(target.grams))throw invalid();}
      else{const item={food_id:row.food_id??null,label:row.label,grams:quantity,unit:'g'};items.push(item);if(key)known.set(key,item);}
    }
    return items;
  }
  function shopping(rows,start,end){
    const days=ordinal(end)-ordinal(start)+1;
    // Technical transfer/iteration bound reused from the existing diary calendar.
    if(days<1 || days>62)throw new Error('Elige un periodo de hasta 62 días.');
    return{start,end,days,items:sum(rows,days),kind:'unregistered_shopping_draft'};
  }
  function recorded(calendar){
    if(!calendar || !Array.isArray(calendar.days) || calendar.days.length>62)throw invalid();
    const rows=[];let recordedMeals=0,previous='';
    for(const day of calendar.days){
      ordinal(day.local_date);if(day.local_date<=previous || !day.meals || typeof day.meals!=='object')throw invalid();previous=day.local_date;
      for(const [name,meal]of Object.entries(day.meals)){
        if(!names.includes(name) || !Array.isArray(meal.foods) || meal.foods.length>32)throw invalid();recordedMeals++;
        for(const row of meal.foods){if(typeof row.food_id!=='string' || !row.food_id || row.food_id.length>200)throw invalid();
          rows.push({food_id:row.food_id,label:row.food_id,grams:row.grams,unit:'g'});}
      }
    }
    return{items:sum(rows),recordedMeals,kind:'recorded_consumption'};
  }
  window.PlanDayData=Object.freeze({menu,select,shopping,recorded,ordinal,names:Object.freeze(names)});
})();
