/* Aggregate observations and explicit future data provenance. No browser telemetry. */
(() => {
  'use strict';
  const labels={unknown:'Sin clasificar',demo:'Demostración',customer:'Cliente'};
  let revision=0;
  function status(root,text){root.querySelector('[data-origin-status]').textContent=text;}
  function validOrigin(value){return value&&Object.hasOwn(labels,value.origin)&&Number.isSafeInteger(value.version)&&value.version>=0&&value.applies_to==='future_facts'&&value.customer_is_payment===false;}

  async function showOrigin(root,client=null) {
    const own=++revision,context=root.dataset.context;
    const select=root.querySelector('select'),button=root.querySelector('button');
    root.hidden=false;select.disabled=true;button.hidden=true;
    status(root,'Consultando la procedencia…');
    try {
      const me=await Api.auth.me();
      const result=await Api.productAnalytics.origin(context,client);
      if(own!==revision)return;
      if(!validOrigin(result))throw new Error('Respuesta no confirmada');
      const mayWrite=context==='personal'?me.role!=='owner':me.tipo==='gym'&&me.role==='owner'&&!me.team_gym_id;
      select.value=result.origin;select.disabled=!mayWrite;button.hidden=!mayWrite;
      status(root,labels[result.origin]+'. Una nueva declaración se aplica sólo a hechos futuros.');
      button.onclick=async()=>{
        if(own!==revision)return;
        button.disabled=true;
        try{
          const saved=await Api.productAnalytics.origin(context,client,{origin:select.value,expected_version:result.version});
          if(own!==revision)return;
          if(!validOrigin(saved))throw new Error('Declaración no confirmada');
          await showOrigin(root,client);
        }catch{
          if(own===revision){status(root,'No se pudo confirmar el cambio. Vuelve a abrir los datos antes de reintentar.');select.disabled=true;button.hidden=true;}
        }finally{button.disabled=false;}
      };
    }catch{if(own===revision)status(root,'No se pudo consultar la procedencia en este contexto.');}
  }

  async function report(root){
    const text=root.querySelector('[data-product-report]'),button=root.querySelector('button');
    button.disabled=true; text.textContent='Consultando hechos observados…';
    try{
      const value=await Api.productAnalytics.report(root.dataset.context);
      if(value?.definition_version!=='product-facts-v2'||value.context!==root.dataset.context)throw new Error('Respuesta no confirmada');
      const counts=value.baseline?.event_counts_by_origin;
      const lines=Object.keys(labels).map(origin=>{
        const row=counts?.[origin];
        if(!row||!['plan_saved','plan_assignment_published','assigned_plan_http200'].every(k=>Number.isSafeInteger(row[k])&&row[k]>=0))throw new Error('Conteos no confirmados');
        return labels[origin]+': '+row.plan_saved+' planes guardados; '+row.plan_assignment_published+' asignaciones; '+row.assigned_plan_http200+' primeras respuestas de plan asignado.';
      });
      text.textContent=lines.join(' ');
    }catch{text.textContent='No se pudo confirmar esta consulta. Los datos anteriores no se reconstruyen.';}
    finally{button.disabled=false;}
  }

  function boot(){
    document.querySelectorAll('[data-product-analytics]').forEach(root=>{root.querySelector('button').addEventListener('click',()=>report(root));});
    const personal=document.querySelector('[data-product-origin][data-context="personal"]');
    if(personal)showOrigin(personal);
  }
  window.ProductOrigin=Object.freeze({showClient:client=>{const root=document.getElementById('client-origin');if(root)showOrigin(root,client);}});
  window.addEventListener('metodobase-session-changed',()=>{
    ++revision;
    document.querySelectorAll('[data-product-origin]').forEach(root=>{root.hidden=true;root.querySelector('select').value='unknown';root.querySelector('button').onclick=null;});
    document.querySelectorAll('[data-product-report]').forEach(node=>{node.textContent='La sesión cambió. Vuelve a abrir la página.';});
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
