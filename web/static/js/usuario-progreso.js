/* R25 personal entry. Consent discovery/withdrawal is independent of personal-space bootstrap. */
(() => {
  'use strict';
  const root=document.getElementById('personal-progress-page');if(!root)return;
  const get=id=>document.getElementById(id),view=ProgresoVista,dto=ProgresoRespuestas;
  let controller=null,initializing=true,flowBusy=false,bootstrap=null,profiles=[],profileNext=null;
  const controlTasks=[];
  function clearPage(){bootstrap=null;profiles=[];profileNext=null;for(const section of root.querySelectorAll('.progress-section'))section.hidden=true;get('progress-date-source').textContent='';get('completion-table').replaceChildren();get('completion-status').textContent='';get('completion-query').reset();}
  function controls(){
    const active=controller?.active===true,locked=flowBusy||initializing||controller?.busy||!active;
    for(const input of root.querySelectorAll('button,input,select'))input.disabled=locked||controller?.active!==true;
    if(!active)return;
    for(const task of controlTasks){controller.check();task();controller.check();}
    get('progress-profiles-more').hidden=profileNext===null;controller.check();
  }
  const host={
    check(){controller.check();},render(task){controller.render(task);},
    onClear(task){controller.clear(task);},onControls(task){controlTasks.push(task);},
    get active(){return controller?.active===true;},get busy(){return flowBusy||initializing||controller?.busy===true;},
    async read(task,decode=value=>value){const result=await controller.run(async context=>{const raw=await task(context);controller.check();const decoded=decode(raw);controller.check();return decoded;});controller.check();return result;},
    async action(task){
      if(flowBusy||initializing||!controller?.active)return;flowBusy=true;
      try{controls();controller.check();get('progress-error').hidden=true;await task();controller.check();}
      catch(error){if(controller.active){try{controller.check();view.error(get('progress-error'),ProgresoControlador.message(error));controller.check();}catch{}}}
      finally{flowBusy=false;if(controller.active){try{controls();}catch{}}}
    },
  };
  controller=ProgresoControlador.create({api:Api.progreso||Api.vinculos,onBusy:controls,onInvalidated(error){clearPage();flowBusy=false;initializing=false;controls();get('progress-status').textContent='Se descartaron los datos de esta sesión.';view.error(get('progress-error'),ProgresoControlador.message(error));}});
  controller.clear(clearPage);
  const measures=ProgresoMedidasUI.mount(host),consents=ProgresoConsentimientosUI.mount(host);
  async function loadProfiles(reset=true){
    const position=reset?null:profileNext;if(!reset&&position===null)return;
    const result=await host.read(context=>Api.progreso.bootstrap(context,position),dto.context);host.check();if(position!==null&&result.profiles.nextAfter===position)throw Object.assign(new Error('cursor'),{code:'progress_response_unavailable'});
    host.render(()=>{const seen=new Set(reset?[]:profiles.map(row=>row.id));profiles=reset?[]:profiles;for(const row of result.profiles.items)if(!seen.has(row.id)){seen.add(row.id);profiles.push(row);}bootstrap=result;profileNext=result.profiles.nextAfter;get('progress-date-source').textContent='Fecha del servidor al consultar: '+result.today+' · '+result.timezone+'. Las fechas de medición son declaradas, no derivadas del reloj del navegador.';});
    measures.configure({...result,profiles:{...result.profiles,items:profiles}});consents.configure({...result,profiles:{...result.profiles,items:profiles}});
    host.render(()=>{get('progress-completion').hidden=false;get('completion-from').max=result.today;get('completion-through').max=result.today;if(!get('completion-from').value&&!get('completion-through').value){get('completion-from').value=ProgresoDatos.addDays(result.today,-29);get('completion-through').value=result.today;}controls();});
  }
  async function loadCompletion(){
    if(!bootstrap)return;const range=ProgresoDatos.queryRange(get('completion-from').value,get('completion-through').value,bootstrap.today);
    const result=await host.read(context=>Api.progreso.completados(context,range),dto.completion);host.check();host.render(()=>{view.completion(get('completion-table'),result.rows);get('completion-status').textContent='Periodo consultado: '+result.fromDate+' a '+result.throughDate+' · '+result.timezone+'. Sólo se cuentan snapshots registrados.';});
  }
  async function loadState(){
    host.render(()=>{get('progress-status').textContent='Consultando permisos propios y capacidades personales…';});let discovered=false;
    try{await consents.load(true);discovered=true;}catch(error){host.check();host.render(()=>view.error(get('progress-error'),ProgresoControlador.message(error),{focus:false}));}
    try{await loadProfiles(true);}catch(error){host.check();bootstrap=null;profiles=[];profileNext=null;measures.clear();consents.disablePersonal();host.render(()=>{get('progress-measurements').hidden=true;get('progress-completion').hidden=true;get('completion-table').replaceChildren();get('completion-status').textContent='';get('consent-create').hidden=true;get('progress-status').textContent=discovered?'Se consultaron tus permisos propios. Este contexto no habilita perfil, medidas ni nuevos permisos.':'No se pudo consultar el progreso. No se crearon perfiles ni permisos.';view.error(get('progress-error'),ProgresoControlador.message(error),{focus:false});});return;}
    await measures.load(true);await consents.loadLinks(true);await loadCompletion();host.render(()=>{get('progress-status').textContent='Consulta realizada. Elige un perfil explícitamente para ver o registrar sus medidas. Compartir progreso requiere una confirmación aparte.';});
  }
  get('progress-refresh').addEventListener('click',()=>host.action(loadState));get('progress-profiles-more').addEventListener('click',()=>host.action(()=>loadProfiles(false)));get('completion-query').addEventListener('submit',event=>{event.preventDefault();host.action(loadCompletion);});
  (async()=>{try{controls();if(!Api.progreso)throw Object.assign(new Error('unavailable'),{code:'progress_context_unavailable'});await controller.start();controller.check();initializing=false;await host.action(loadState);}catch(error){if(controller.active)view.error(get('progress-error'),ProgresoControlador.message(error));else if(!get('progress-error').textContent){get('progress-status').textContent='No se pudo verificar la cuenta para consultar progreso.';view.error(get('progress-error'),ProgresoControlador.message(error));}}finally{initializing=false;if(controller.active){try{controls();}catch{}}}})();
})();
