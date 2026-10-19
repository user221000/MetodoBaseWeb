/* R25 professional shell. Roles or URL parameters never grant access locally. */
(() => {
  'use strict';
  const root=document.getElementById('professional-progress-page');if(!root)return;
  const status=document.getElementById('progress-status'),error=document.getElementById('progress-error'),refresh=document.getElementById('progress-refresh');
  function clear(){for(const section of root.querySelectorAll('.progress-section'))section.hidden=true;for(const form of root.querySelectorAll('form'))form.reset();for(const id of ['professional-native-table','professional-scope','professional-shared-measurements','professional-shared-completion','progress-date-source'])document.getElementById(id).replaceChildren();const select=document.getElementById('professional-link');while(select.options.length>1)select.remove(1);select.value='';}
  let controller;
  async function start(){
    if(controller?.active)return;error.hidden=true;
    if(!Api.progreso){status.textContent='La consulta profesional de progreso no está disponible en esta versión.';ProgresoVista.error(error,'No se recibieron datos. Esta pantalla no concede acceso por rol ni por el identificador de la URL.',{focus:false});return;}
    controller=ProgresoControlador.create({onInvalidated(cause){clear();refresh.disabled=true;status.textContent='Se descartaron los datos de esta sesión.';ProgresoVista.error(error,ProgresoControlador.message(cause));},onBusy(value){refresh.disabled=value;}});controller.clear(clear);
    try{await controller.start();controller.check();status.textContent='Cuenta verificada. Consulta profesional pendiente de composición API32.';}
    catch(cause){if(!controller.active)return;ProgresoVista.error(error,ProgresoControlador.message(cause));}
  }
  refresh.addEventListener('click',start);start();
})();
