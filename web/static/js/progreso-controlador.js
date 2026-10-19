/* Lifecycle for R25 consumers. No DTO, token, operation key or health data in Storage. */
(() => {
  'use strict';
  const changed=()=>Object.assign(new Error('La sesión o el alcance cambió. Vuelve a consultar desde tu cuenta.'),{code:'session_changed'});
  const messages=Object.freeze({
    progress_context_requires_review:'Este contexto requiere revisión. No se ha adoptado ningún perfil.',
    progress_permission_denied:'Tu cuenta no tiene permiso para esta consulta.',
    progress_source_unavailable:'Esta fuente no está disponible en el contexto actual.',
    progress_version_conflict:'El registro cambió en otra sesión. Consulta su estado antes de confirmar otra acción.',
    progress_consent_unavailable:'Este permiso no está disponible. Consulta tus permisos propios para revisar una retirada.',
    progress_scope_changed:'El vínculo o el alcance cambió. Vuelve a consultar y revisa una nueva confirmación.',
    progress_source_requires_review:'Los datos de origen requieren revisión. No se muestran cifras sustitutas.',
    progress_unconfirmed:'No se confirmó el resultado del guardado. Consulta el estado actual antes de intentar otra acción.',
    progress_busy:'Otra operación está en curso. Consulta el estado antes de volver a confirmar.',
    progress_volume_limit:'La consulta supera el volumen permitido. Reduce el periodo.',
    progress_operation_pending:'Consulta el resultado del registro pendiente. No se ha preparado otra clave ni se reenviará automáticamente.',
    session_changed:'La sesión cambió. Se descartaron los datos de esta página.',
    session_storage_error:'No se pudo verificar la sesión en este navegador. Los datos se descartaron.',
    session_expired:'La sesión finalizó. Vuelve a entrar a tu cuenta.',
  });
  function message(error){return messages[error?.code]||(error?.code==='progress_invalid_input'?error.message:'No se pudo completar la consulta. Conserva el borrador sólo en esta página y consulta el estado antes de volver a confirmar.');}
  function create({api,onInvalidated=()=>{},onBusy=()=>{}}={}){
    let busy=false,epoch=0,closed=false;
    const cleanups=new Set();
    const context=MemberLinkContext.create({api:api||Api.vinculos,onInvalidated(error){closed=true;epoch++;busy=false;for(const clear of cleanups){try{clear();}catch{}}onInvalidated(error);}});
    function check(ticket=epoch){if(closed||ticket!==epoch)throw changed();context.check();}
    function clear(task){cleanups.add(task);return()=>cleanups.delete(task);}
    // Controls can synchronously invalidate a session; always check again afterwards.
    function controls(){onBusy(busy);check();}
    async function run(task){
      check();if(busy)throw Object.assign(new Error('Hay otra operación en curso.'),{code:'progress_busy'});
      busy=true;const ticket=epoch;
      try{controls();const result=await context.read(task);check(ticket);return result;}
      finally{busy=false;if(!closed&&ticket===epoch){controls();}}
    }
    return Object.freeze({
      start:()=>context.start(),check,clear,run,
      render(task){check();context.render(task);check();},
      scope:task=>context.scope(task),
      invalidate:error=>context.invalidate(error),
      get busy(){return busy;},get active(){return !closed&&context.active;},
    });
  }
  window.ProgresoControlador=Object.freeze({create,message});
})();
