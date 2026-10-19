/* R25 presentation over normalized view records, not an HTTP schema or authority. */
(() => {
  'use strict';
  const labels=Object.freeze({peso_kg:'Peso',grasa_corporal_pct:'Grasa corporal',masa_magra_kg:'Masa magra'});
  const categoryLabels=Object.freeze({weight:'Peso',body_fat:'Grasa corporal',lean_mass:'Masa magra',completion:'Contadores de consumos registrados y completados'});
  function node(tag,text,className){const value=document.createElement(tag);if(text!==undefined)value.textContent=text;if(className)value.className=className;return value;}
  function civil(value){if(value===null)return'No verificada';ProgresoDatos.date(value);return value;}
  function instant(value){if(value===null)return'No disponible';if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T.*Z$/.test(value)||!Number.isFinite(Date.parse(value)))throw new Error('La fecha de registro requiere revisión.');return value+' (UTC)';}
  function figure(value,unit){return typeof value==='number'&&Number.isFinite(value)?String(value)+' '+unit:'No registrada';}
  function table(target,caption,headings){
    const wrap=node('div',undefined,'progress-table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',caption);
    const value=node('table');value.append(node('caption',caption));const head=node('thead'),row=node('tr');for(const title of headings){const th=node('th',title);th.scope='col';row.append(th);}head.append(row);const body=node('tbody');value.append(head,body);wrap.append(value);target.replaceChildren(wrap);return body;
  }
  function measurements(target,rows,{caption='Medidas registradas',withdraw=null}={}){
    if(!Array.isArray(rows))throw new Error('Las medidas requieren revisión.');
    if(!rows.length){target.replaceChildren(node('p','No hay medidas disponibles en este alcance.'));return;}
    const body=table(target,caption,['Fecha de medición','Fuente','Peso (kg)','Grasa corporal (%)','Masa magra (kg)','Fecha de registro','Estado']);
    for(const row of rows){
      const tr=node('tr');tr.append(node('td',civil(row.measuredOn)),node('td',row.sourceKind==='self_reported'?'Declarada por la persona':'Histórica: fuente no verificada'));
      for(const metric of Object.keys(labels))tr.append(node('td',figure(row.values?.[metric],ProgresoDatos.units[metric])));
      tr.append(node('td',instant(row.recordedAt)));const state=node('td',row.withdrawn?'Retirada':'Registrada');
      if(withdraw&&row.canWithdraw===true&&!row.withdrawn){const button=node('button','Retirar esta medida','secondary');button.type='button';button.addEventListener('click',()=>withdraw(row));state.append(node('p'),button);}tr.append(state);body.append(tr);
    }
  }
  function completion(target,rows,{caption='Marcas sobre consumos registrados'}={}){
    if(!Array.isArray(rows))throw new Error('Los contadores requieren revisión.');
    if(!rows.length){target.replaceChildren(node('p','No hay consumos registrados observables en este periodo. Los días ausentes no cuentan como cero.'));return;}
    const body=table(target,caption,['Fecha local','Consumos registrados','Marcados completados','Relación observada']);
    for(const row of rows){const counts=ProgresoDatos.observed(row.completed,row.registered),tr=node('tr');tr.append(node('td',civil(row.localDate)),node('td',String(counts.registered)),node('td',String(counts.completed)),node('td',counts.ratio===null?'Sin base de consumos registrados':counts.completed+' de '+counts.registered));body.append(tr);}
  }
  function trend(target,rows,metric){
    const series=ProgresoDatos.series(rows,metric);target.replaceChildren();
    if(!series.available){target.append(node('p','Se necesitan medidas declaradas en al menos dos fechas distintas para mostrar esta tendencia. La tabla conserva los datos disponibles.'));return;}
    const title=node('h3','Observaciones de '+labels[metric].toLowerCase()),description=node('p','Cada punto es una medida declarada. No se unen fechas, no se rellenan ausencias y no se interpreta el cambio clínicamente.');
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('class','progress-chart');svg.setAttribute('viewBox','0 0 640 260');svg.setAttribute('role','img');svg.setAttribute('aria-label','Observaciones de '+labels[metric].toLowerCase()+' en '+series.unit+'. Los valores y fechas completos están en la tabla de medidas.');
    const days=series.points.map(point=>ProgresoDatos.ordinal(point.date)),values=series.points.map(point=>point.value),first=Math.min(...days),last=Math.max(...days),low=Math.min(...values),high=Math.max(...values),spread=high-low||1;
    function svgNode(tag,attrs,text){const value=document.createElementNS(ns,tag);for(const[key,item]of Object.entries(attrs))value.setAttribute(key,String(item));if(text!==undefined)value.textContent=text;return value;}
    svg.append(svgNode('line',{x1:80,y1:210,x2:615,y2:210}),svgNode('line',{x1:80,y1:30,x2:80,y2:210}),svgNode('text',{x:10,y:35},String(high)+' '+series.unit),svgNode('text',{x:10,y:205},String(low)+' '+series.unit),svgNode('text',{x:80,y:240},series.points[0].date),svgNode('text',{x:615,y:240,'text-anchor':'end'},series.points.at(-1).date));
    for(let index=0;index<series.points.length;index++){const point=series.points[index],circle=svgNode('circle',{cx:80+(days[index]-first)/(last-first)*535,cy:high===low?120:200-(point.value-low)/spread*160,r:6});circle.append(svgNode('title',{},point.date+': '+point.value+' '+series.unit));svg.append(circle);}
    target.append(title,description,svg);
  }
  function scope(target,value){
    const card=node('div',undefined,'progress-card');card.append(node('p','Categorías: '+Object.keys(categoryLabels).filter(key=>value.categories[key]===true).map(key=>categoryLabels[key]).join(', ')));
    card.append(node('p','Desde '+civil(value.fromDate)+(value.throughDate===null?' · sin fecha final explícita':' hasta '+civil(value.throughDate))));
    if(value.profileLabel!==undefined&&value.profileLabel!==null)card.append(node('p','Perfil autorizado: '+value.profileLabel));target.replaceChildren(card);
  }
  function error(target,message,{focus=true}={}){target.textContent=message;target.hidden=false;if(focus)target.focus();}
  window.ProgresoVista=Object.freeze({node,civil,instant,figure,measurements,completion,trend,scope,error,labels,categoryLabels});
})();
