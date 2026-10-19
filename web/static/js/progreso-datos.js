/* Pure R25 input/presentation rules. No clinical interpretation or persistence. */
(() => {
  'use strict';
  const units=Object.freeze({peso_kg:'kg',grasa_corporal_pct:'%',masa_magra_kg:'kg'});
  const categories=['weight','body_fat','lean_mass','completion'];
  const invalid=message=>Object.assign(new Error(message),{code:'progress_invalid_input'});
  function date(value){
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))throw invalid('Elige una fecha completa.');
    const[y,m,d]=value.split('-').map(Number),leap=y%4===0&&(y%100!==0||y%400===0);
    if(y<1||m<1||m>12||d<1||d>[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][m-1])throw invalid('La fecha no existe.');
    return{year:y,month:m,day:d};
  }
  function ordinal(value){const{year:y,month:m,day:d}=date(value),before=y-1;let sum=365*before+Math.floor(before/4)-Math.floor(before/100)+Math.floor(before/400)+d;for(let month=1;month<m;month++)sum+=[31,y%4===0&&(y%100!==0||y%400===0)?29:28,31,30,31,30,31,31,30,31,30,31][month-1];return sum;}
  function addDays(value,days){
    const{year,month,day}=date(value);if(!Number.isSafeInteger(days)||Math.abs(days)>36600)throw invalid('El periodo no es válido.');
    // UTC is arithmetic over an already supplied civil date, never today's source.
    const result=new Date(0);result.setUTCFullYear(year,month-1,day+days);
    const output=String(result.getUTCFullYear()).padStart(4,'0')+'-'+String(result.getUTCMonth()+1).padStart(2,'0')+'-'+String(result.getUTCDate()).padStart(2,'0');date(output);return output;
  }
  function queryRange(from,through,today){
    date(today);if(!from&&!through)return null;if(!from||!through)throw invalid('Indica las dos fechas del periodo.');date(from);date(through);
    if(from>through)throw invalid('La fecha inicial debe ser anterior o igual a la final.');
    if(through>today)throw invalid('Las consultas no incluyen fechas futuras.');
    if(ordinal(through)-ordinal(from)+1>62)throw invalid('Consulta como máximo 62 días por periodo.');
    return{from,through};
  }
  function number(value,name){
    if(value===''||value===null||value===undefined)return null;
    if(typeof value==='string'){if(!/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(value.trim()))throw invalid('Escribe '+name+' con un número y punto decimal, sin unidades en el campo.');value=Number(value);}
    if(typeof value!=='number'||!Number.isFinite(value))throw invalid('Escribe un valor finito para '+name+'.');return value;
  }
  function measurement(input,today){
    date(today);if(typeof input.source_profile_id!=='string'||!input.source_profile_id||input.source_profile_id.length>128)throw invalid('Elige explícitamente un perfil propio.');date(input.measured_on);if(input.measured_on>today)throw invalid('La medición no puede tener una fecha futura.');
    const values={};for(const key of Object.keys(units)){const value=number(input.values?.[key],key);if(value===null)continue;
      if((key==='peso_kg'&&(value<20||value>300))||(key==='grasa_corporal_pct'&&(value<3||value>60))||(key==='masa_magra_kg'&&(value<=0||value>300)))throw invalid('El valor de '+key+' está fuera del rango técnico admitido.');values[key]=value;}
    if(!Object.keys(values).length)throw invalid('Indica al menos una medida explícita.');
    return{source_profile_id:input.source_profile_id,measured_on:input.measured_on,values};
  }
  function consent(input){
    if(!input.categories||categories.some(key=>typeof input.categories[key]!=='boolean')||Object.keys(input.categories).some(key=>!categories.includes(key))||!categories.some(key=>input.categories[key]))throw invalid('Elige al menos una categoría que quieras compartir.');
    if(typeof input.ongoing!=='boolean')throw invalid('Elige si el permiso tiene fin o es continuo.');date(input.from_date);
    if(input.ongoing){if(input.through_date!==null)throw invalid('El permiso continuo no lleva una fecha final.');}
    else{date(input.through_date);if(input.through_date<input.from_date)throw invalid('La fecha final debe ser posterior o igual a la inicial.');}
    const measures=['weight','body_fat','lean_mass'].some(key=>input.categories[key]);
    if(measures&&(typeof input.source_profile_id!=='string'||!input.source_profile_id||input.source_profile_id.length>128))throw invalid('Elige el perfil personal cuyas medidas autorizas.');
    return{source_profile_id:measures?input.source_profile_id:null,categories:{...input.categories},from_date:input.from_date,through_date:input.through_date,ongoing:input.ongoing,protocol:'progress_share_v1'};
  }
  function observed(completed,registered){
    if(!Number.isSafeInteger(completed)||!Number.isSafeInteger(registered)||completed<0||registered<0||completed>registered)throw invalid('Los contadores registrados requieren revisión.');
    return{completed,registered,ratio:registered===0?null:completed/registered};
  }
  function series(records,metric){
    if(!Object.hasOwn(units,metric)||!Array.isArray(records))throw invalid('La serie no es válida.');
    // Inputs here are normalized internal view records, not a guessed HTTP DTO.
    const points=[];for(const row of records){if(row.sourceKind!=='self_reported'||row.withdrawn===true)continue;try{date(row.measuredOn);}catch{continue;}const value=row.values?.[metric];if(typeof value!=='number'||!Number.isFinite(value))continue;points.push({key:row.key,date:row.measuredOn,value});}
    points.sort((left,right)=>left.date.localeCompare(right.date)||String(left.key).localeCompare(String(right.key)));
    return{unit:units[metric],points,available:new Set(points.map(row=>row.date)).size>=2};
  }
  window.ProgresoDatos=Object.freeze({date,ordinal,addDays,queryRange,measurement,consent,observed,series,units});
})();
