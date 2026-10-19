/* R25 entry point. API32 composition is required; absent routes never become empty data. */
(() => {
  'use strict';
  const root=document.getElementById('personal-progress-page');if(!root)return;
  const status=document.getElementById('progress-status'),error=document.getElementById('progress-error'),refresh=document.getElementById('progress-refresh');
  function clear(){
    for(const section of root.querySelectorAll('.progress-section'))section.hidden=true;
    for(const form of root.querySelectorAll('form'))form.reset();
    for(const id of ['measurement-table','measurement-trend','completion-table','consent-list','consent-recipient','progress-date-source'])document.getElementById(id).replaceChildren();
    for(const id of ['progress-profile','consent-profile','consent-link']){const select=document.getElementById(id);while(select.options.length>1)select.remove(1);select.value='';}
  }
  let controller;
  function unavailable(){status.textContent='La consulta de progreso no está disponible en esta versión.';ProgresoVista.error(error,'No se recibieron datos de progreso. No se han creado medidas, perfiles ni permisos.',{focus:false});}
  async function start(){
    if(controller?.active)return;error.hidden=true;
    if(!Api.progreso){unavailable();return;}
    controller=ProgresoControlador.create({onInvalidated(cause){clear();refresh.disabled=true;status.textContent='Se descartaron los datos de esta sesión.';ProgresoVista.error(error,ProgresoControlador.message(cause));},onBusy(value){refresh.disabled=value;}});
    controller.clear(clear);
    try{await controller.start();controller.check();status.textContent='Cuenta verificada. Consulta de progreso pendiente de composición API32.';}
    catch(cause){if(!controller.active)return;ProgresoVista.error(error,ProgresoControlador.message(cause));}
  }
  refresh.addEventListener('click',start);start();
})();
