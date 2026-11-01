/* First-party MFA views. Proofs never enter attributes, Storage, logs or URLs. */
(() => {
  'use strict';
  const bearer=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{43}$/.test(value);
  const expires=value=>typeof value==='string'&&Number.isFinite(Date.parse(value));
  const bad=()=>Object.assign(new Error('No se pudo confirmar la respuesta de verificación.'),{code:'mfa_invalid_response'});
  const cancelled=()=>Object.assign(new Error('Verificación cancelada. No se solicitó la operación.'),{code:'mfa_cancelled'});
  const messages={
    mfa_invalid_input:'Completa el método elegido y su código vigente.',
    mfa_google_email_unavailable:'La confirmación de Google por correo no está disponible. Usa tu contraseña o vuelve a intentarlo más tarde.',
    mfa_google_email_delivery_unconfirmed:'No se pudo confirmar el envío del código de seguridad. Espera antes de iniciar otra verificación con Google.',
    mfa_google_email_code_invalid:'El código de este cambio no es válido o venció. Revisa las seis cifras del correo más reciente.',
    mfa_google_email_identity_changed:'La cuenta o el contacto cambiaron. Inicia una verificación nueva con tu cuenta actual.',
    mfa_google_email_link_required:'Usa la cuenta de Google vinculada a este perfil o verifica o recupera tu contraseña actual.',
    mfa_google_email_throttled:'Espera antes de solicitar o verificar otro código de seguridad.',
    mfa_fresh_verification_required:'Necesitas una prueba vigente para esta operación.',
    mfa_enrollment_required:'Activa un factor en la seguridad de tu cuenta antes de continuar.',
    mfa_primary_reauthentication_required:'Vuelve a verificar tu identidad con tu contraseña o con Google para continuar.',
    mfa_verification_failed:'No se confirmó el código. Revisa el método y usa una prueba vigente.',
    mfa_proof_unavailable:'La prueba venció o ya se usó. Inicia una verificación nueva.',
    mfa_throttled:'Hay un límite temporal de intentos. Espera antes de volver a verificar.',
    mfa_unconfirmed:'La respuesta es incierta. Puede haberse confirmado el cambio. Inicia sesión de nuevo y consulta el estado; no repitas la operación a ciegas.',
    mfa_service_unavailable:'La verificación no está disponible. No se confirmó el cambio.',
    mfa_busy:'Hay una verificación en curso. Espera o descártala.',
    mfa_session_version_exhausted:'La cuenta necesita revisión antes de cambiar sus opciones de seguridad. No se modificó el segundo factor.',
    session_changed:'La sesión cambió. Se cerró la verificación anterior.',
    session_storage_error:'No se pudo guardar la sesión de forma segura. Vuelve a iniciar sesión.'
  };
  const notice=error=>messages[error?.code]||(error?.status===429?'Hay un límite temporal. Respeta el tiempo de espera del servidor.':error?.status===503?'La confirmación es incierta. Consulta el estado antes de otra operación.':'No se pudo confirmar la operación. Vuelve a consultar el estado.');
  function factor(method,value){
    if(method==='totp'&&/^\d{6}$/.test(value))return{code:value};
    if(method==='recovery_code'&&/^[A-Za-z0-9_-]{22}$/.test(value))return{recovery_code:value};
    throw Object.assign(new Error('Escribe una prueba completa del método elegido.'),{code:'mfa_invalid_input'});
  }
  const node=(tag,text,parent)=>{const item=document.createElement(tag);if(text!==undefined)item.textContent=text;if(parent)parent.append(item);return item;};
  function kit(root,codes,context,loginUrl,api=Api.mfa){
    let active=true,values=codes.slice();
    function clear(){if(!active)return;active=false;values.fill('');values=[];root.replaceChildren();window.removeEventListener('metodobase-session-changed',clear);window.removeEventListener('pagehide',clear);window.removeEventListener('storage',storage);}
    function storage(event){if(event.key===null||['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key))clear();}
    function check(){if(!active)throw cancelled();api.check(context);}
    window.addEventListener('metodobase-session-changed',clear);window.addEventListener('pagehide',clear);window.addEventListener('storage',storage);
    try{
      check();root.replaceChildren();node('h3','Guarda tu nuevo kit de recuperación',root);
      node('p','La sesión se cerró en este navegador después de confirmar el cambio. Estos ocho códigos se muestran una vez y cada uno es de un uso. No podemos volver a mostrarlos.',root);
      const list=node('ol',undefined,root);list.className='mfa-secret';for(const code of values){check();node('li',code,list);check();}
      node('p','El código usado al confirmar ya fue consumido. Para iniciar sesión, espera un intervalo nuevo del autenticador o usa un código de recuperación sin usar.',root);
      const close=node('button','Ya guardé el kit: descartarlo de esta vista',root);close.type='button';close.addEventListener('click',()=>{clear();const link=node('a','Volver a iniciar sesión',root);link.href=loginUrl;});
      check();close.focus();
    }catch(error){clear();throw error;}
    return{clear};
  }
  function createAccount(options){
    const api=options.api||Api.mfa;let context=null,status=null,enrollment=null,busy=false,dead=false,epoch=0;
    function clear(){enrollment=null;options.onClear?.();}
    function invalidate(){if(dead)return;dead=true;epoch++;context=null;status=null;busy=false;clear();options.onState?.({state:'invalidated',busy:false,message:'La sesión o el almacenamiento cambiaron. Se descartaron los secretos de esta vista.'});}
    function check(ticket=epoch){if(dead||ticket!==epoch||!context)throw Object.assign(new Error('Session changed'),{code:'session_changed'});api.check(context);}
    function emit(state,text){options.onState?.({state,busy,status:status?{...status}:null,message:text});}
    function failure(error,ticket,message){if(dead||ticket!==epoch)return;try{check(ticket);}catch{invalidate();return;}busy=false;
      if(['session_changed','session_storage_error'].includes(error.code)){invalidate();return;}
      if(error.status===503||!error.status){clear();emit('unconfirmed',message||notice(error));}else emit('error',message||notice(error));}
    async function load(){if(dead||busy)return;const ticket=++epoch;busy=true;clear();if(dead||ticket!==epoch)return;emit('loading','Consultando la seguridad de esta cuenta…');if(dead||ticket!==epoch)return;
      try{if(!context){const value=await api.context();if(dead||ticket!==epoch)return;context=value.handle;}check(ticket);
        const value=await api.status(context);check(ticket);
        if(!value||typeof value.enabled!=='boolean'||typeof value.pending!=='boolean'||!Number.isInteger(value.recovery_codes_remaining)||value.recovery_codes_remaining<0||value.recovery_codes_remaining>8||typeof value.required_for_privileged_actions!=='boolean'||value.totp_period_seconds!==30||value.challenge_lifetime_seconds!==300)throw bad();
        status=value;busy=false;emit('ready','Estado actualizado. Confirma tu identidad para hacer cambios.');
      }catch(error){if(!context&&!dead){busy=false;emit('error',notice(error));}else failure(error,ticket);}}
    async function mutate(action,primary,proof,verifiedPrimary=null){
      if(dead||busy||!status)return false;check();const ticket=epoch;busy=true;clear();if(dead||ticket!==epoch)return false;emit('saving','Verificando tu identidad; el cambio aún no está confirmado…');if(dead||ticket!==epoch)return false;
      let stage='primary';
      try{
        check(ticket);const reauth=verifiedPrimary===null?await api.reauth(primary,context):verifiedPrimary;primary=null;verifiedPrimary=null;check(ticket);
        if(!reauth||!bearer(reauth.reauthentication_token)||!expires(reauth.expires_at)||Date.parse(reauth.expires_at)<=Date.now())throw bad();
        stage='factor';
        let body={reauthentication_token:reauth.reauthentication_token,...(status.enabled?proof:{})};
        if(action==='enroll'){
          const reply=await api.enroll(body,context);body=null;proof=null;check(ticket);
          if(!reply||typeof reply.enrollment_id!=='string'||!/^[0-9a-f]{32}$/.test(reply.enrollment_id)||typeof reply.secret!=='string'||!/^[A-Z2-7]{16,128}$/.test(reply.secret)||!expires(reply.expires_at)||reply.shown_once!==true||typeof reply.otpauth_uri!=='string'||!reply.otpauth_uri.startsWith('otpauth://totp/'))throw bad();
          enrollment={id:reply.enrollment_id,secret:reply.secret,expiry:reply.expires_at};busy=false;
          options.onSeed?.(enrollment.secret,enrollment.expiry);check(ticket);emit('enrolling','Semilla recibida una vez. Todavía no se activó: configura tu autenticador y confirma un código.');return true;
        }
        if(!['regenerate','revoke'].includes(action)||!status.enabled)throw bad();
        const reply=await api[action](body,context);body=null;proof=null;check(ticket);
        if(action==='regenerate')return finishKit(reply,ticket);
        if(reply?.success!==true||reply.enabled!==false||reply.reauthenticate!==true)throw bad();
        const previous=context;clear();check(ticket);dead=true;epoch++;context=null;status=null;busy=false;
        try{const closed=api.close(previous);api.check(closed);options.onClosed?.(closed);return true;}
        catch(error){options.onClosedError?.(notice(error));return false;}
      }catch(error){primary=null;proof=null;verifiedPrimary=null;failure(error,ticket,error.code==='mfa_verification_failed'&&stage==='primary'?'No se confirmó tu identidad. Revisa tu contraseña actual o vuelve a verificar con Google.':null);return false;}}
    function finishKit(reply,ticket){
      check(ticket);
      if(reply?.success!==true||reply.shown_once!==true||reply.reauthenticate!==true||!Array.isArray(reply.recovery_codes)||reply.recovery_codes.length!==8||new Set(reply.recovery_codes).size!==8||reply.recovery_codes.some(code=>typeof code!=='string'||!/^[A-Za-z0-9_-]{22}$/.test(code)))throw bad();
      const values=reply.recovery_codes.slice(),previous=context;clear();check(ticket);
      dead=true;epoch++;context=null;status=null;busy=false;
      try{const closed=api.close(previous);api.check(closed);options.onKit?.(values,closed);api.check(closed);return true;}
      catch(error){values.fill('');options.onClear?.();options.onClosedError?.(notice(error));return false;}
    }
    async function confirm(code){
      if(dead||busy||!enrollment)return false;
      if(!/^\d{6}$/.test(code)){emit('enrolling','Escribe seis cifras de tu autenticador.');return false;}
      if(Date.now()>=Date.parse(enrollment.expiry)){clear();emit('error','La clave de configuración venció. Vuelve a verificar tu identidad.');return false;}
      check();const ticket=epoch,body={enrollment_id:enrollment.id,code};busy=true;options.onInputsClear?.();if(dead||ticket!==epoch)return false;emit('saving','Confirmando el factor; todavía no hay un cambio confirmado…');if(dead||ticket!==epoch)return false;
      try{const reply=await api.confirm(body,context);check(ticket);if(reply?.enabled!==true)throw bad();return finishKit(reply,ticket);}
      catch(error){failure(error,ticket);return false;}}
    window.addEventListener('metodobase-session-changed',invalidate);window.addEventListener('pagehide',invalidate);window.addEventListener('storage',event=>{if(event.key===null||['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key))invalidate();});
    return{load,mutate:(action,primary,proof)=>mutate(action,primary,proof),mutateVerified:(action,receipt,proof)=>mutate(action,null,proof,receipt),confirm,invalidate,discard(){if(!dead&&!busy){clear();emit('ready','Semilla descartada de esta vista. Consulta el estado antes de iniciar otro cambio.');}},check,
      get enabled(){return status?.enabled===true;},get active(){return!dead;}};
  }
  let activePrompt=false;
  async function authorize(operation,reason){
    if(activePrompt)throw Object.assign(new Error('Otra verificación está abierta.'),{code:'mfa_busy'});
    Api.mfa.checkOperation(operation);activePrompt=true;
    return new Promise((resolve,reject)=>{
      const previous=document.activeElement,dialog=node('dialog');dialog.className='mfa-dialog';dialog.setAttribute('aria-labelledby','mfa-prompt-title');
      node('h2','Confirmar esta operación',dialog).id='mfa-prompt-title';const status=node('p',notice(reason),dialog);status.setAttribute('role','status');status.tabIndex=-1;
      const form=node('form',undefined,dialog),label=node('label','Método de verificación',form),method=node('select',undefined,label);
      for(const[key,text]of[['totp','Aplicación autenticadora'],['recovery_code','Código de recuperación']]){const item=node('option',text,method);item.value=key;}
      const valueLabel=node('label','Prueba del método elegido',form),input=node('input',undefined,valueLabel);input.type='text';input.autocomplete='one-time-code';input.inputMode='numeric';input.maxLength=6;input.spellcheck=false;
      const submit=node('button','Verificar esta operación',form);submit.type='submit';const cancel=node('button','Cancelar',dialog);cancel.type='button';let settled=false,busy=false;
      function cleanup(){input.value='';dialog.replaceChildren();dialog.remove();activePrompt=false;window.removeEventListener('metodobase-session-changed',changed);window.removeEventListener('pagehide',changed);previous?.focus();}
      function finish(error,grant){if(settled)return;settled=true;cleanup();if(error)reject(error);else resolve(grant);}
      const changed=()=>finish(Object.assign(new Error('La sesión cambió.'),{code:'session_changed'}));
      cancel.addEventListener('click',()=>finish(cancelled()));dialog.addEventListener('cancel',event=>{event.preventDefault();finish(cancelled());});
      method.addEventListener('change',()=>{input.value='';input.inputMode=method.value==='totp'?'numeric':'text';input.autocomplete=method.value==='totp'?'one-time-code':'off';input.maxLength=method.value==='totp'?6:22;input.focus();});
      form.addEventListener('submit',async event=>{event.preventDefault();if(busy||settled)return;busy=true;submit.disabled=true;
        try{Api.mfa.checkOperation(operation);const proof=factor(method.value,input.value.trim());input.value='';const grant=await Api.mfa.grant(operation,proof);Api.mfa.checkOperation(operation);finish(null,grant);}
        catch(error){if(settled)return;try{Api.mfa.checkOperation(operation);}catch{changed();return;}status.textContent=notice(error);status.focus();}
        finally{busy=false;if(!settled)submit.disabled=false;}});
      window.addEventListener('metodobase-session-changed',changed);window.addEventListener('pagehide',changed);
      if(reason.code==='mfa_enrollment_required'){form.hidden=true;const link=node('a','Abrir seguridad de la cuenta',dialog);link.href='/configuracion#mfa-account';}
      try{Api.mfa.checkOperation(operation);document.body.append(dialog);if(typeof dialog.showModal!=='function')throw bad();dialog.showModal();(form.hidden?cancel:input).focus();Api.mfa.checkOperation(operation);}catch(error){finish(error);}
    });
  }
  function mountAccount(options){
    const root=document.getElementById('mfa-account');if(!root)return;
    const get=id=>root.querySelector('#'+id),form=get('mfa-account-primary'),state=get('mfa-account-status'),seed=get('mfa-account-seed'),confirmation=get('mfa-account-confirm'),kitRoot=get('mfa-account-kit');
    const googleTarget=get('mfa-account-google'),googleSection=get('mfa-account-google-section'),googleStatus=get('mfa-account-google-status'),mailForm=get('mfa-account-google-email'),mailCode=get('mfa-account-google-email-code');
    let recoveryView=null,providerAttempt=null,providerEpoch=0,providerRender=0,renderGoogle=null,mail=null,mailBusy=false,mailTimer=null,lastState=null,emailEpoch=0;
    const personal=options.loginUrl==='/login-usuario',securityUrl=personal?'/mi-seguridad':'/cuenta/seguridad';
    get('mfa-account-email-link').href=securityUrl;get('mfa-account-security-link').href=securityUrl;get('mfa-account-subscription-link').href=personal?'/mi-suscripcion':'/suscripciones';
    function clearMail(){clearInterval(mailTimer);mailTimer=null;if(mail)mail.proof=null;mail=null;mailBusy=false;mailCode.value='';mailForm.hidden=true;}
    function clearInputs(){for(const input of root.querySelectorAll('input'))input.value='';providerAttempt=null;providerEpoch++;clearMail();get('mfa-account-google-cancel').hidden=true;googleTarget.inert=false;}
    function clear(){clearInputs();seed.replaceChildren();confirmation.hidden=true;recoveryView?.clear();recoveryView=null;kitRoot.replaceChildren();}
    function badge(id,text,kind){const target=get(id);target.textContent=text;target.dataset.state=kind;}
    function actionHelp(){
      const selected=get('mfa-account-action').value,enabled=controller.enabled;
      get('mfa-account-action-help').textContent=selected==='regenerate'?'El nuevo kit reemplazará los códigos anteriores y cerrará tus sesiones.':selected==='revoke'?'Se desactivará el autenticador y se cerrarán tus sesiones. Las acciones protegidas requerirán activarlo de nuevo.':enabled?'Para reemplazar el autenticador, confirma tu identidad y un código del método actual.':'La primera activación necesita tu identidad y un código de la nueva aplicación.';
      get('mfa-account-submit').textContent=selected==='regenerate'?'Reemplazar kit con mi contraseña':selected==='revoke'?'Desactivar con mi contraseña':enabled?'Reemplazar con mi contraseña':'Continuar con mi contraseña';
    }
    function mailControls(){
      if(!mail)return;
      const expired=Date.now()>=mail.expiresAt,waiting=Math.max(0,Math.ceil((mail.resendAt-Date.now())/1000));
      mailCode.disabled=mailBusy||expired;get('mfa-account-google-email-submit').disabled=mailBusy||expired;
      get('mfa-account-google-email-submit').textContent=mailBusy?'Verificando…':'Verificar y continuar';
      get('mfa-account-google-email-restart').disabled=mailBusy||waiting>0;
      get('mfa-account-google-email-restart').textContent=waiting?'Nueva verificación en '+waiting+' s':'Volver a verificar con Google';
      mailForm.setAttribute('aria-busy',String(mailBusy));
      if(expired)googleStatus.textContent='El código de este cambio venció. Vuelve a verificar con Google para solicitar uno nuevo.';
    }
    function render(update){
      lastState=update;root.dataset.phase=update.state;state.textContent=update.message;
      if(update.state==='invalidated'){emailEpoch++;badge('mfa-account-email-state','Por consultar','unknown');get('mfa-account-email-summary').textContent='Se descartó el estado de la sesión anterior.';get('mfa-account-summary').textContent='';badge('mfa-account-factor-state','Por consultar','unknown');}
      const unavailable=['loading','saving','invalidated','unconfirmed'].includes(update.state),configuring=seed.childElementCount>0;
      form.hidden=update.state==='invalidated'||configuring;form.inert=!!mail||mailBusy;
      for(const control of root.querySelectorAll('input,select,button'))control.disabled=update.busy||update.state==='invalidated';
      if(mail||mailBusy)for(const control of form.querySelectorAll('input,select,button'))control.disabled=true;
      get('mfa-account-submit').disabled=unavailable||!!mail||mailBusy;
      get('mfa-account-refresh').disabled=update.busy||update.state==='invalidated'||mailBusy;
      googleSection.hidden=['invalidated','unconfirmed'].includes(update.state)||configuring;googleTarget.hidden=!!mail;googleTarget.inert=update.busy||mailBusy;
      get('mfa-account-google-cancel').hidden=!providerAttempt&&!mail;
      if(update.status){
        const enabled=update.status.enabled;
        badge('mfa-account-factor-state',configuring?'Pendiente de activar':enabled?'Activo':update.status.pending?'Configuración pendiente':'Sin activar',configuring||!enabled?'pending':'confirmed');
        get('mfa-account-summary').textContent=(enabled?'Autenticador activo. ':'Todavía no hay un autenticador activo. ')+update.status.recovery_codes_remaining+' códigos de recuperación disponibles.'+(update.status.pending&&!configuring?' Hay una configuración pendiente; su clave no puede volver a mostrarse.':'');
        get('mfa-account-existing-factor').hidden=!enabled;
        for(const option of get('mfa-account-action').options)option.disabled=option.value!=='enroll'&&!enabled;
        if(!enabled)get('mfa-account-action').value='enroll';actionHelp();
      }
      mailControls();if(['error','invalidated','unconfirmed'].includes(update.state))state.focus();
    }
    const controller=createAccount({onClear:clear,onInputsClear:clearInputs,onState:render,onSeed(secret,expiry){
      controller.check();seed.replaceChildren();node('h3','Vincula tu aplicación autenticadora',seed);
      node('p','En tu aplicación, añade una cuenta e introduce esta clave manual. Selecciona códigos TOTP de seis cifras con un intervalo de 30 segundos.',seed);
      const value=node('p',secret,seed);value.className='mfa-secret';
      node('p','La clave sólo se muestra en esta vista. Configúrala antes de '+new Date(expiry).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})+' y confirma el código de la nueva aplicación.',seed);
      controller.check();confirmation.hidden=false;get('mfa-account-new-code').focus();
    },onKit(codes,closed){
      Api.mfa.check(closed);get('mfa-account-summary').textContent='';badge('mfa-account-factor-state','Cambio confirmado','confirmed');
      form.hidden=true;confirmation.hidden=true;googleSection.hidden=true;get('mfa-account-refresh').hidden=true;state.textContent='Cambio confirmado. Sesión anterior cerrada; guarda el kit antes de salir.';
      recoveryView=kit(kitRoot,codes,closed,options.loginUrl);Api.mfa.check(closed);
    },onClosed(closed){
      Api.mfa.check(closed);get('mfa-account-summary').textContent='';form.hidden=true;confirmation.hidden=true;googleSection.hidden=true;badge('mfa-account-factor-state','Desactivado','pending');
      state.textContent='Autenticación en dos pasos desactivada y sesión cerrada. Para hacer cambios protegidos tendrás que activarla de nuevo.';
      const link=node('a','Iniciar sesión de nuevo',kitRoot);link.href=options.loginUrl;Api.mfa.check(closed);
    },onClosedError(text){clear();form.hidden=true;googleSection.hidden=true;state.textContent=text;state.focus();}});
    function currentProof(){return controller.enabled?factor(get('mfa-account-method').value,get('mfa-account-factor').value.trim()):{};}
    function showError(error){if(controller.active){root.dataset.phase='error';state.textContent=notice(error);state.focus();}}
    async function refresh(){
      const ticket=++emailEpoch;await controller.load();if(!controller.active||ticket!==emailEpoch)return;
      try{
        controller.check();const handle=Api.mfa.capture(),value=await Api.accountSecurity.status(handle);controller.check();Api.mfa.check(handle);if(ticket!==emailEpoch)return;
        if(!value||typeof value.email_verified!=='boolean'||(value.email_verified&&(!expires(value.email_verified_at)||Date.parse(value.email_verified_at)>Date.now())))throw bad();
        badge('mfa-account-email-state',value.email_verified?'Confirmado':'Por confirmar',value.email_verified?'confirmed':'pending');
        get('mfa-account-email-summary').textContent=value.email_verified?'Tu correo actual ya está confirmado. No necesitas confirmarlo otra vez para elegir un plan.':'Confirma el correo de tu cuenta desde las opciones de seguridad antes de continuar.';
      }catch(error){if(controller.active&&ticket===emailEpoch){badge('mfa-account-email-state','No disponible','unknown');get('mfa-account-email-summary').textContent='No se pudo consultar el estado del correo. Puedes revisarlo en las opciones de tu cuenta.';}}
    }
    function discardProvider(message){
      providerAttempt=null;providerEpoch++;clearMail();googleTarget.hidden=false;googleTarget.inert=false;get('mfa-account-google-cancel').hidden=true;
      if(renderGoogle&&controller.active)renderGoogle();if(lastState&&controller.active)render(lastState);if(message)googleStatus.textContent=message;
    }
    form.addEventListener('submit',async event=>{
      event.preventDefault();if(mail||mailBusy)return;
      try{controller.check();const proof=currentProof(),action=get('mfa-account-action').value,password=get('mfa-account-password').value;
        if(!password){state.textContent='Escribe tu contraseña actual o confirma tu identidad con Google.';state.focus();return;}
        await controller.mutate(action,{password},proof);
      }catch(error){showError(error);}
    });
    confirmation.addEventListener('submit',async event=>{event.preventDefault();await controller.confirm(get('mfa-account-new-code').value.trim());});
    get('mfa-account-refresh').addEventListener('click',refresh);get('mfa-account-discard').addEventListener('click',()=>controller.discard());
    get('mfa-account-method').addEventListener('change',()=>{const input=get('mfa-account-factor'),totp=get('mfa-account-method').value==='totp';input.value='';input.maxLength=totp?6:22;input.autocomplete=totp?'one-time-code':'off';input.inputMode=totp?'numeric':'text';});
    get('mfa-account-action').addEventListener('change',actionHelp);
    mailForm.addEventListener('submit',async event=>{
      event.preventDefault();const attempt=mail;if(!attempt||mailBusy||Date.now()>=attempt.expiresAt)return;
      let code=mailCode.value.trim();mailCode.value='';if(!/^\d{6}$/.test(code)){googleStatus.textContent='Escribe las seis cifras enviadas a tu correo para este cambio.';mailCode.focus();return;}
      mailBusy=true;mailControls();
      try{
        controller.check();Api.mfa.check(attempt.context);const pending=Api.mfa.googleEmailVerify({challenge:attempt.challenge,code},attempt.context);code=null;
        const receipt=await pending;controller.check();Api.mfa.check(attempt.context);if(mail!==attempt||attempt.epoch!==providerEpoch)return;
        badge('mfa-account-email-state','Confirmado','confirmed');get('mfa-account-email-summary').textContent='Tu correo actual quedó confirmado. No necesitas confirmarlo otra vez para elegir un plan.';
        const action=attempt.action,proof=attempt.proof;attempt.proof=null;clearMail();await controller.mutateVerified(action,receipt,proof);
      }catch(error){code=null;if(mail===attempt&&controller.active){
        if(!error.status||error.status>=500||error.code==='mfa_google_email_identity_changed'){clearMail();googleTarget.hidden=false;googleTarget.inert=false;if(renderGoogle)renderGoogle();if(lastState)render(lastState);}
        googleStatus.textContent=notice(error);googleStatus.tabIndex=-1;googleStatus.focus();
      }}
      finally{code=null;if(mail===attempt&&controller.active){mailBusy=false;mailControls();mailCode.focus();}}
    });
    get('mfa-account-google-email-restart').addEventListener('click',()=>{if(mail&&!mailBusy&&Date.now()>=mail.resendAt)discardProvider('Vuelve a pulsar Google para solicitar un código nuevo.');});
    get('mfa-account-google-cancel').addEventListener('click',()=>discardProvider('Verificación con Google descartada. No se solicitó el cambio.'));
    window.addEventListener('keydown',event=>{if(event.key==='Escape'&&(providerAttempt||mail)&&!mailBusy){event.preventDefault();discardProvider('Verificación con Google descartada.');}});
    if(options.googleClientId){
      const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;script.nonce=options.nonce;
      script.onerror=()=>{if(controller.active)googleStatus.textContent='No se pudo cargar Google. Usa tu contraseña actual o vuelve a intentarlo.';};
      script.onload=()=>{
        if(!controller.active)return;
        google.accounts.id.initialize({client_id:options.googleClientId,auto_select:false,ux_mode:'popup',callback:async reply=>{
          const attempt=providerAttempt;if(!attempt||attempt.epoch!==providerEpoch||reply.state!==attempt.state||!controller.active)return;
          providerAttempt=null;mailBusy=true;googleTarget.inert=true;googleStatus.textContent='Solicitando un código para confirmar este cambio de seguridad…';
          try{
            controller.check();Api.mfa.check(attempt.context);const requested=Api.mfa.googleEmailRequest({google_credential:reply.credential},attempt.context);reply=null;
            const value=await requested;controller.check();Api.mfa.check(attempt.context);if(attempt.epoch!==providerEpoch)return;
            mail={epoch:attempt.epoch,context:attempt.context,action:attempt.action,proof:attempt.proof,challenge:value.challenge,expiresAt:Date.parse(value.expires_at),resendAt:Date.now()+value.resend_after_seconds*1000};attempt.proof=null;mailBusy=false;
            get('mfa-account-google-email-recipient').textContent='Revisa '+value.masked_email+' e introduce el código de este cambio.';
            mailForm.hidden=false;googleTarget.hidden=true;get('mfa-account-google-cancel').hidden=false;googleStatus.textContent='El código de correo confirma tu identidad para esta operación. Después vincularás el autenticador.';
            mailTimer=setInterval(()=>{if(!controller.active||!mail){clearInterval(mailTimer);return;}try{Api.mfa.check(mail.context);mailControls();}catch{clearMail();}},500);
            if(lastState)render(lastState);mailCode.focus();
          }catch(error){attempt.proof=null;if(controller.active&&attempt.epoch===providerEpoch){mailBusy=false;googleTarget.inert=false;get('mfa-account-google-cancel').hidden=true;if(renderGoogle)renderGoogle();googleStatus.textContent=notice(error);if(lastState)render(lastState);}}
        }});
        renderGoogle=()=>{
          googleTarget.replaceChildren();const buttonState='mfa-account-'+(++providerRender);
          google.accounts.id.renderButton(googleTarget,{type:'standard',theme:'outline',size:'large',text:'continue_with',locale:'es',width:Math.max(200,Math.min(400,googleTarget.offsetWidth||280)),state:buttonState,click_listener:()=>{
            if(providerAttempt||mail||mailBusy)return;
            try{controller.check();providerAttempt={epoch:++providerEpoch,state:buttonState,context:Api.mfa.capture(),action:get('mfa-account-action').value,proof:currentProof()};googleTarget.inert=true;get('mfa-account-google-cancel').hidden=false;googleStatus.textContent='Elige tu cuenta de Google. Confirmaremos este cambio con un código temporal en tu correo.';}
            catch(error){providerAttempt=null;showError(error);}
          }});
        };renderGoogle();
      };document.head.appendChild(script);
      for(const id of ['mfa-account-action','mfa-account-method','mfa-account-factor','mfa-account-password'])get(id).addEventListener('input',()=>{discardProvider('');});
    }else googleStatus.textContent='La verificación con Google no está disponible. Usa tu contraseña actual.';
    window.addEventListener('pagehide',()=>{emailEpoch++;clearMail();recoveryView?.clear();});refresh();return controller;
  }
  window.MfaUI=Object.freeze({authorize,createAccount,mountAccount,kit,factor,notice,node});
})();
