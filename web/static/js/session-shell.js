/* Clear legacy rendered account data on a real session boundary. No storage or I/O. */
(() => {
  'use strict';
  function clear(){
    for(const id of ['sb-nombre','sb-tipo','sb-avatar','sb-total-clientes','toast-container']){const node=document.getElementById(id);if(node)node.replaceChildren();}
    for(const main of document.querySelectorAll('main')){
      // A confirmed MFA change may now render its one-time kit in this island.
      // Its owner synchronously clears old inputs, seed and kit on every boundary.
      const security=main.querySelector('#mfa-account');if(security)main.before(security);
      for(const field of main.querySelectorAll('input,textarea,select')){field.value='';if('checked'in field)field.checked=false;field.disabled=true;}
      for(const dialog of main.querySelectorAll('dialog'))if(dialog.open)dialog.close();
      const notice=document.createElement('section'),text=document.createElement('p'),link=document.createElement('a');
      notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');notice.tabIndex=-1;
      text.textContent='La sesión cambió. Los datos de esta página se descartaron. Vuelve a abrirla para consultar la cuenta actual.';
      link.href=location.pathname;link.textContent='Volver a abrir esta página';notice.append(text,link);main.replaceChildren(notice);
    }
  }
  // Let owners synchronously clear their RAM/secrets and controls first;
  // remove remaining legacy DOM in the same microtask turn before painting.
  const schedule=()=>queueMicrotask(clear);
  window.addEventListener('metodobase-session-changed',schedule);
  window.addEventListener('pagehide',schedule);
  window.addEventListener('pageshow',event=>{if(event.persisted)schedule();});
})();
