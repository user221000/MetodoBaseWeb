/* Explicit privacy requests and bounded own-fact pages. Account data stays in RAM. */
(function(root){
 'use strict';
 const labels={personal_diary_days:'Diario personal',personal_client_progress:'Mediciones personales',account_and_credentials:'Cuenta y seguridad',personal_and_professional_records:'Perfiles y planes',links_and_append_only_history:'Vínculos e historial',billing_and_legal_records:'Cobros y obligaciones',notifications_and_audit:'Avisos y registros',private_objects:'Archivos privados',external_backups_and_processors:'Respaldos y proveedores'};
 const states={pending:'Pendiente',deleted:'Eliminado en esta categoría',retained_by_policy:'Retenido según política',blocked:'Requiere revisión',pending_confirmation:'Confirmación externa pendiente',failed:'Ejecución sin confirmar'};
 const itemText=item=>(labels[item.category]||'Categoría por revisar')+': '+(states[item.status]||'Estado por revisar');
 function create({api,onState=()=>{},onClear=()=>{},onClosed=()=>{}}){
  let handle=null,receipt=null,after=null,busy=false,dead=false,epoch=0,key=null,factor=null;
  const providerCaptures=new WeakMap();
  const view=()=>({busy,dead,receipt,hasMore:after!==null,closureReady:factor!==null,factorEnabled:factor?.enabled===true});
  function emit(message){onState({...view(),message});}
  function invalidate(){dead=true;epoch++;handle=null;receipt=null;after=null;key=null;factor=null;busy=false;onClear();emit('La sesión cambió. Se retiraron los datos de esta vista.');}
  async function run(operation){
   if(dead||busy)return null;
   const ticket=epoch;busy=true;emit('Consultando tu solicitud…');
   try{
    if(!handle){const result=await api.context();if(dead||ticket!==epoch)return null;handle=result.handle;}
    api.check(handle);const result=await operation(handle);api.check(handle);
    await api.verify(handle);api.check(handle);
    if(dead||ticket!==epoch)return null;
    return result;
   }catch(error){
    if(dead||ticket!==epoch)return null;
    if(error?.status===401||['session_changed','session_storage_error'].includes(error?.code)){invalidate();return null;}
    emit(error?.status===403||error?.status===409?'Este espacio requiere una revisión autorizada.':'No se confirmó la operación. Consulta el estado manualmente; no repetiremos la solicitud automáticamente.');return null;
   }finally{if(!dead&&ticket===epoch){busy=false;onState(view());}}
  }
  async function request(){
   if(key===null)key=root.crypto.randomUUID();
   const result=await run(context=>api.create(key,context));
   if(result&&!dead){receipt=result;emit(result.account_closed?'La cuenta está cerrada. La disposición por categorías conserva su estado indicado.':'Solicitud registrada. La cuenta continúa abierta y el borrado sigue pendiente de revisión.');}
   return result;
  }
  async function refresh(){
   if(!receipt)return null;
   const result=await run(context=>api.status(receipt.id,context));
   if(result&&!dead){receipt=result;emit('Estado de la solicitud actualizado. Las categorías retenidas o bloqueadas siguen pendientes.');}
   return result;
  }
  async function facts(next=false){
   const cursor=next?after:null;if(next&&cursor===null)return null;
   const result=await run(context=>api.facts(cursor,context));
   if(result&&!dead){after=result.next_after;emit('Página de hechos personales preparada. La descarga contiene sólo esta página.');}
   return result;
  }
  async function prepareClose(){
   if(!receipt)return false;onClear();factor=null;
   const value=await run(context=>api.factorStatus(context));
   if(!value||dead)return false;
   if(typeof value.enabled!=='boolean'||value.totp_period_seconds!==30||value.challenge_lifetime_seconds!==300||!Number.isInteger(value.recovery_codes_remaining)||value.recovery_codes_remaining<0||value.recovery_codes_remaining>8){emit('No se pudo validar el factor actual. Consulta el estado antes de continuar.');return false;}
   factor={enabled:value.enabled};emit('Confirma el cierre de acceso. El borrado integral sigue sujeto al estado de cada categoría.');return true;
  }
  function capture(value){
   if(!value||value.confirm!==true)throw Error('confirmation');
   const captured={expected_version:receipt.version,confirmation:'close_account'};
   if(factor.enabled){
    if(value.method==='totp'&&/^\d{6}$/.test(value.factor))captured.code=value.factor;
    else if(value.method==='recovery_code'&&/^[A-Za-z0-9_-]{22}$/.test(value.factor))captured.recovery_code=value.factor;
    else throw Error('factor');
   }
   return captured;
  }
  function prepare(value){
   if(dead||busy||!receipt||factor===null)throw Error('not_ready');api.check(handle);
   const captured=capture(value),intent=Object.freeze({});
   providerCaptures.set(intent,{captured,epoch,handle,id:receipt.id,version:receipt.version});return intent;
  }
  async function close(value,primary,intent=null){
   if(dead||busy||!receipt||factor===null)return false;
   let captured=null;const ticket=epoch,id=receipt.id,version=receipt.version;
   try{
    api.check(handle);
    if(intent!==null){
     const prepared=providerCaptures.get(intent);providerCaptures.delete(intent);intent=null;
     if(!prepared||prepared.epoch!==epoch||prepared.handle!==handle||prepared.id!==id||prepared.version!==version)throw Error('stale_intent');
     captured={...prepared.captured};
    }else captured=capture(value);
    if(!primary||Object.keys(primary).length!==1||!['password','google_credential'].some(name=>typeof primary[name]==='string'&&primary[name].length>0&&primary[name].length<=(name==='password'?128:16384)))throw Error('invalid');
    value=null;primary={...primary};busy=true;onClear();emit('Verificando tu identidad para solicitar el cierre…');
    let pending=api.reauth(primary,handle);primary=null;let proof=await pending;pending=null;
    if(dead||ticket!==epoch)return false;api.check(handle);
    if(!proof||typeof proof.reauthentication_token!=='string'||!/^[A-Za-z0-9_-]{43}$/.test(proof.reauthentication_token)||typeof proof.expires_at!=='string'||!Number.isFinite(Date.parse(proof.expires_at))||Date.parse(proof.expires_at)<=Date.now())throw Error('proof');
    const body={...captured,reauthentication_token:proof.reauthentication_token};captured=null;proof=null;
    const closing=api.close(id,body,handle);for(const name of Object.keys(body))body[name]=null;
    const result=await closing;
    if(result?.state==='blocked'){
     if(dead||ticket!==epoch)return false;api.check(handle);receipt=result.receipt;factor=null;busy=false;onClear();
     emit('La cuenta continúa abierta. La política o las obligaciones pendientes requieren revisión antes de cerrar el acceso.');return false;
    }
    // Success SV+1 invalidates the old handle deliberately. Its receipt is
    // authenticated by the local closed boundary, without another /me call.
    api.checkClosed(result);dead=true;epoch++;handle=null;factor=null;busy=false;receipt=result.receipt;key=null;after=null;onClear();
    onClosed(result);return result.server_confirmed;
   }catch(error){
    primary=null;captured=null;value=null;onClear();if(dead||ticket!==epoch)return false;busy=false;factor=null;
    if(error?.status===401||['session_changed','session_storage_error'].includes(error?.code)){invalidate();return false;}
    emit(error?.status===409?'El estado cambió. Consulta la solicitud antes de confirmar de nuevo.':error?.status===400||error?.status===422?'Revisa tu identidad, la confirmación y el factor vigente. La operación no se repetirá automáticamente.':'No se confirmó el cierre. No repetiremos la operación automáticamente.');return false;
   }finally{primary=null;captured=null;value=null;intent=null;}
  }
  return{request,refresh,facts,prepareClose,prepare,close,invalidate,view};
 }
 function mount(element){
  const status=element.querySelector('[data-privacy39-status]'),items=element.querySelector('[data-privacy39-items]');
  const buttons=Array.from(element.querySelectorAll('button')),form=element.querySelector('[data-privacy39-close-form]');
  const api=Api.accountPrivacy,google=element.querySelector('[data-privacy39-google]'),googleCancel=element.querySelector('[data-privacy39-google-cancel]'),googleStatus=element.querySelector('[data-privacy39-google-status]');
  let terminalResult=null,terminalNode=null,provider=null,providerEpoch=0,renderGoogle=null;
  const clear=()=>{for(const input of form.querySelectorAll('input')){input.value='';if(input.type==='checkbox')input.checked=false;}
   provider=null;providerEpoch++;googleCancel.hidden=true;google.inert=false;};
  function terminal(result){
   api.checkClosed(result);const main=document.querySelector('main');if(!main)return;
   const section=document.createElement('section'),title=document.createElement('h3'),text=document.createElement('p');
   section.setAttribute('role','status');section.setAttribute('aria-live','polite');section.tabIndex=-1;
   title.textContent=result.server_confirmed?'Acceso de cuenta cerrado':'Resultado del cierre sin confirmar';
   text.textContent=result.server_confirmed?'El servidor confirmó el cierre de acceso y la revocación de las sesiones anteriores. El borrado integral de datos continúa sujeto al estado de cada categoría.':'Se retiró la sesión local. No se confirmó el cierre en el servidor y no se repetirá automáticamente. Solicita una revisión autorizada antes de intentar otra operación.';
   section.append(title,text);
   if(result.receipt){const id=document.createElement('p');id.textContent='Comprobante de solicitud: '+result.receipt.id;section.append(id);
    const list=document.createElement('ul');for(const item of result.receipt.items){const row=document.createElement('li');row.textContent=itemText(item);list.append(row);}section.append(list);}
   const login=document.createElement('a');login.href=element.dataset.loginUrl||'/login-usuario';login.textContent='Ir a iniciar sesión';section.append(login);
   api.checkClosed(result);terminalResult=result;terminalNode=section;main.replaceChildren(section);section.focus();
  }
  const controller=create({api,onClear:clear,onClosed:terminal,onState(value){
   if(terminalResult)return;
   if(value.message)status.textContent=value.message;
   for(const button of buttons)button.disabled=value.busy||value.dead;
   element.querySelector('[data-privacy39-refresh]').disabled=value.busy||value.dead||!value.receipt;
   element.querySelector('[data-privacy39-next]').disabled=value.busy||value.dead||!value.hasMore;
   element.querySelector('[data-privacy39-prepare-close]').disabled=value.busy||value.dead||!value.receipt;
   form.hidden=value.dead||!value.closureReady;
   form.querySelector('[data-privacy39-factor-fields]').hidden=!value.factorEnabled;
   google.hidden=!value.closureReady||!element.dataset.googleClientId;google.inert=value.busy||provider!==null;
   for(const input of form.querySelectorAll('input,select'))input.disabled=value.busy||value.dead;
   items.replaceChildren();
   for(const item of value.receipt?.items||[]){const row=document.createElement('li');row.textContent=itemText(item);items.append(row);}
  }});
  element.querySelector('[data-privacy39-request]').addEventListener('click',()=>controller.request());
  element.querySelector('[data-privacy39-refresh]').addEventListener('click',()=>controller.refresh());
  element.querySelector('[data-privacy39-prepare-close]').addEventListener('click',()=>controller.prepareClose());
  const intent=()=>({confirm:form.querySelector('[data-privacy39-confirm]').checked,
   method:form.querySelector('[data-privacy39-method]').value,factor:form.querySelector('[data-privacy39-factor]').value.trim()});
  form.addEventListener('submit',event=>{event.preventDefault();controller.close(intent(),{password:form.querySelector('[data-privacy39-password]').value});});
  form.querySelector('[data-privacy39-method]').addEventListener('change',()=>{const input=form.querySelector('[data-privacy39-factor]');input.value='';
   input.maxLength=form.querySelector('[data-privacy39-method]').value==='totp'?6:22;input.inputMode=form.querySelector('[data-privacy39-method]').value==='totp'?'numeric':'text';});
  for(const field of form.querySelectorAll('input,select'))field.addEventListener('input',()=>{
   provider=null;providerEpoch++;google.inert=false;googleCancel.hidden=true;if(renderGoogle&&!controller.view().dead)renderGoogle();
  });
  function cancelProvider(){
   if(!provider)return;provider=null;providerEpoch++;google.inert=false;googleCancel.hidden=true;
   googleStatus.textContent='Verificación con Google descartada. No se solicitó el cierre.';
   if(renderGoogle&&!controller.view().dead)renderGoogle();googleStatus.tabIndex=-1;googleStatus.focus();
  }
  googleCancel.addEventListener('click',cancelProvider);
  window.addEventListener('keydown',event=>{if(event.key==='Escape'&&provider){event.preventDefault();cancelProvider();}});
  // The existing security widget owns its GIS callback. The dedicated privacy
  // view on the SAME allowed shell omits that widget; initialize exactly once.
  if(element.dataset.googleClientId&&!document.querySelector('[data-account-security37]')){
   const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;
   script.nonce=document.querySelector('script[nonce]')?.nonce||'';
   script.onerror=()=>{if(!controller.view().dead)googleStatus.textContent='Google no está disponible. Puedes usar tu contraseña actual.';};
   script.onload=()=>{
    if(controller.view().dead)return;
    window.google.accounts.id.initialize({client_id:element.dataset.googleClientId,auto_select:false,ux_mode:'popup',
     nonce:crypto.randomUUID(),essential_claims:'auth_time, amr',callback:async reply=>{
      let attempt=provider;
      if(!attempt||attempt.epoch!==providerEpoch||reply.state!==attempt.state||controller.view().dead)return;
      provider=null;google.inert=false;googleCancel.hidden=true;
      try{
       let captured=attempt.intent;attempt.intent=null;attempt=null;let credential=reply.credential;reply=null;
       const pending=controller.close(null,{google_credential:credential},captured);credential=null;captured=null;await pending;
      }catch{attempt=null;reply=null;clear();}
     }});
    renderGoogle=()=>{
     if(controller.view().dead)return;google.replaceChildren();const state='privacy39-'+crypto.randomUUID();
     window.google.accounts.id.renderButton(google,{type:'standard',theme:'filled_black',size:'large',text:'continue_with',locale:'es',
      width:Math.min(400,google.offsetWidth||280),state,click_listener:()=>{
       if(provider)return;
       try{const captured=controller.prepare(intent());provider={epoch:++providerEpoch,state,intent:captured};google.inert=true;googleCancel.hidden=false;
        googleStatus.textContent='Confirma la cuenta de Google vinculada para este cierre de acceso.';
       }catch{clear();status.textContent='Confirma el cierre y el factor vigente antes de verificar tu identidad.';status.tabIndex=-1;status.focus();}
      }});
    };renderGoogle();
   };document.head.appendChild(script);
  }else googleStatus.textContent=element.dataset.googleClientId?'Abre la vista de privacidad para verificar con Google.':'La verificación con Google no está configurada en esta vista. Usa tu contraseña actual.';
  async function download(next){const value=await controller.facts(next);if(!value||controller.view().dead)return;
   const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
   try{const link=document.createElement('a');link.href=url;link.download='metodobase-hechos-personales-pagina.json';link.click();}finally{URL.revokeObjectURL(url);}}
  element.querySelector('[data-privacy39-facts]').addEventListener('click',()=>download(false));
  element.querySelector('[data-privacy39-next]').addEventListener('click',()=>download(true));
  window.addEventListener('metodobase-session-changed',()=>{controller.invalidate();google.replaceChildren();if(terminalResult){try{api.checkClosed(terminalResult);}catch{terminalResult=null;terminalNode?.replaceChildren();terminalNode=null;}}});
  window.addEventListener('pagehide',()=>{controller.invalidate();terminalResult=null;terminalNode?.replaceChildren();terminalNode=null;element.replaceChildren();});
  return controller;
 }
 root.AccountPrivacy39=Object.freeze({create,mount});
 if(typeof document!=='undefined'){
  const start=()=>{for(const element of document.querySelectorAll('[data-account-privacy39]'))mount(element);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
 }
})(typeof window!=='undefined'?window:globalThis);
