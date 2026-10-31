/* Public primary/challenge lifecycle. No secret is exposed through view DTOs. */
(() => {
  'use strict';
  const methods=new Set(['totp','recovery_code']);
  const messages={mfa_throttled:'Hay un límite temporal de intentos. Espera antes de volver a verificar.',mfa_verification_failed:'No se confirmó el código. Usa una prueba vigente e inténtalo de nuevo.',mfa_proof_unavailable:'La verificación venció o ya se usó. Inicia un acceso nuevo.',mfa_unconfirmed:'No llegó una confirmación fiable. Puede haberse consumido la prueba; inicia un acceso nuevo.',mfa_service_unavailable:'La verificación no está disponible. No se inició sesión; vuelve a consultar.'};
  const googleMessages=Object.freeze({google_link_required:'Este vínculo de Google está desactivado. Usa otro acceso de tu cuenta para consultar tus vínculos.',google_link_conflict:'No se pudo confirmar este vínculo de Google. Descarta el intento y consulta tus vínculos desde el acceso local; no se inició una sesión nueva.',google_identity_invalid:'No se pudo verificar la cuenta de Google. Descarta el intento y usa una autenticación válida; no se inició sesión.',google_email_unavailable:'El servicio de envío de códigos no está disponible. No se inició sesión. Inténtalo cuando el servicio se restablezca.',google_email_delivery_unconfirmed:'No pudimos confirmar el envío del código. No se inició sesión. Descarta este intento antes de comenzar uno nuevo.',google_email_code_invalid:'No se pudo confirmar el código del correo. Revisa las seis cifras o inicia un acceso nuevo si venció o ya lo usaste.',google_email_throttled:'Hay un límite temporal para los códigos del correo. Espera antes de iniciar otro intento.',google_email_identity_changed:'La cuenta cambió durante la verificación. Inicia un acceso nuevo con Google.',google_email_unconfirmed:'No pudimos confirmar la verificación del correo. No se inició sesión. Inicia un acceso nuevo.'});
  function message(error){if(error.code==='registration_invalid')return 'No se pudo crear la cuenta. Revisa el correo, el nombre y la contraseña (mínimo 15 caracteres).';if(Object.prototype.hasOwnProperty.call(googleMessages,error.code))return googleMessages[error.code];return messages[error.code]||(error.status===429?messages.mfa_throttled:error.status===503?messages.mfa_unconfirmed:'No se pudo confirmar el acceso. Revisa los datos o inicia un acceso nuevo.');}
  function create(options={}){
    const api=options.api||Api.mfa;
    let context=null,challenge=null,method='totp',expiry=null,maskedEmail=null,primaryKind=null,phase='primary',busy=false,epoch=0,dead=false,committing=false,committed=false;
    const changed=()=>Object.assign(new Error('La sesión cambió. Vuelve a abrir esta página.'),{code:'session_changed'});
    function view(text,code){options.onView?.({phase,busy,method,expiresAt:expiry,maskedEmail,message:text,code});}
    function clearProof(){challenge=null;expiry=null;maskedEmail=null;options.onClear?.();}
    function invalidate(){if(dead)return;dead=true;epoch++;busy=false;context=null;primaryKind=null;clearProof();phase='invalidated';view('La sesión cambió. Se descartó la verificación anterior. Vuelve a abrir esta página.');}
    function check(ticket=epoch){if(dead||ticket!==epoch||!context)throw changed();api.check(context);}
    function cancel(){if(dead||committed)return;epoch++;busy=false;primaryKind=null;clearProof();if(dead)return;context=null;phase='primary';view('Verificación descartada. Puedes iniciar un acceso nuevo.');}
    function failure(error,ticket){if(dead||ticket!==epoch)return;
      try{if(context)api.check(context);}catch{invalidate();return;}
      busy=false;
      if(['session_changed','session_storage_error','session_expired'].includes(error.code)){invalidate();return;}
      if(committed){phase='destination_error';view('El acceso se confirmó, pero no pudimos consultar el destino de esta cuenta. Puedes consultarlo de nuevo sin repetir la autenticación.');return;}
      if(['google_link_required','google_email_identity_changed'].includes(error.code)){
        const discarded=++epoch;context=null;primaryKind=null;clearProof();if(dead||epoch!==discarded)return;
        phase='primary';view(message(error),error.code);return;
      }
      if(!error.status||error.status===503||['mfa_proof_unavailable','mfa_unconfirmed'].includes(error.code)){
        const discarded=++epoch;context=null;primaryKind=null;clearProof();if(dead||epoch!==discarded)return;phase='primary';
      }
      view(message(error)+(error.retryAfter?' Respeta el tiempo de espera indicado por el servidor.':''),error.code);
    }
    async function finish(data,ticket){
      check(ticket);
      if(!data || !['gym','usuario'].includes(data.tipo) || (primaryKind!=='google'&&((options.audience==='gym' && data.tipo!=='gym'&&!data.team_gym_id) ||
          (options.audience==='usuario'&&data.tipo!=='usuario'&&!data.team_gym_id))))throw Object.assign(new Error('Portal diferente'),{code:'login_audience_mismatch',status:403});
      clearProof();check(ticket);phase='committing';committing=true;
      try{context=api.finishLogin(data,context);}finally{committing=false;}
      check(ticket);data=null;committed=true;phase='confirmed';view('Acceso confirmado. Consultando el destino de tu cuenta…');
      await options.onAuthenticated?.(context,Object.freeze({primaryMethod:primaryKind}));check(ticket);
    }
    async function acceptVerified(data,ticket){
      options.onClear?.();check(ticket);maskedEmail=null;
      if(data.mfa_required===true){challenge=data.challenge;expiry=data.expires_at;method='totp';phase='factor';busy=false;view('Ahora confirma el código de tu autenticador para iniciar sesión.');return true;}
      await finish(data,ticket);busy=false;return true;
    }
    async function consumePrimary(kind,payload,ticket){
      try{
        check(ticket);primaryKind=kind;
        const data=await (kind==='google'?api.primaryGoogle(payload,context):kind==='registration'?api.registerPassword(payload,context):api.primaryPassword(payload,context));check(ticket);
        if(kind==='google'){
          if(data.email_verification_required!==true)throw Object.assign(new Error('No se confirmó el paso del correo.'),{code:'google_email_unconfirmed',status:503});
          options.onClear?.();check(ticket);challenge=data.challenge;expiry=data.expires_at;maskedEmail=data.masked_email;phase='email';busy=false;
          view('Enviamos un código a tu correo. Escríbelo para continuar; todavía no se inició sesión.');return true;
        }
        return await acceptVerified(data,ticket);
      }catch(error){failure(error,ticket);return false;}
    }
    async function primary(kind,payload){
      if(dead||busy||phase!=='primary')return false;
      const ticket=++epoch;
      try{if(options.ready)await options.ready;if(dead||ticket!==epoch)return false;context=api.capture();check(ticket);busy=true;view('Comprobando tus datos de acceso…');check(ticket);return await consumePrimary(kind,payload,ticket);}
      catch(error){failure(error,ticket);return false;}
    }
    async function verify(value){
      if(dead||busy||phase!=='factor'||!challenge)return false;
      const valid=method==='totp'?/^\d{6}$/.test(value):/^[A-Za-z0-9_-]{22}$/.test(value);
      if(!valid){view(method==='totp'?'Escribe seis cifras del autenticador.':'Pega un código de recuperación completo, respetando mayúsculas y minúsculas.');return false;}
      if(Date.now()>=Date.parse(expiry)){cancel();view('La verificación venció. Inicia un acceso nuevo.');return false;}
      const ticket=epoch,body={challenge,[method==='totp'?'code':'recovery_code']:value};busy=true;
      try{options.onClear?.();check(ticket);view('Verificando el factor; el acceso aún no está confirmado…');check(ticket);const data=await api.loginVerify(body,context);check(ticket);await finish(data,ticket);busy=false;return true;}
      catch(error){failure(error,ticket);return false;}
    }
    async function verifyEmail(value){
      if(dead||busy||phase!=='email'||!challenge)return false;
      if(!/^\d{6}$/.test(value)){view('Escribe las seis cifras del código que recibiste por correo.','google_email_code_invalid');return false;}
      if(Date.now()>=Date.parse(expiry)){cancel();view('El código del correo venció. Inicia un acceso nuevo con Google.');return false;}
      const ticket=epoch,body={challenge,code:value};busy=true;
      try{options.onClear?.();check(ticket);view('Verificando el código del correo; el acceso aún no está confirmado…');check(ticket);
        const data=await api.googleEmailVerify(body,context);check(ticket);return await acceptVerified(data,ticket);
      }catch(error){failure(error,ticket);return false;}
    }
    const notify=()=>{if(committing)return;if(api.isPrimaryBoundary?.(context)){try{api.check(context);return;}catch{/* The exact owner must still be valid. */}}invalidate();};
    window.addEventListener('metodobase-session-changed',notify);window.addEventListener('pagehide',invalidate);
    window.addEventListener('storage',event=>{if(event.key===null||['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key))invalidate();});
    return{primary,verify,verifyEmail,cancel,invalidate,
      async retryDestination(){if(dead||busy||!committed||phase!=='destination_error')return false;const ticket=epoch;busy=true;
        try{check(ticket);view('Acceso confirmado. Consultando el destino de esta cuenta…');check(ticket);await options.onAuthenticated?.(context,Object.freeze({primaryMethod:primaryKind}));check(ticket);phase='confirmed';busy=false;return true;}
        catch(error){failure(error,ticket);return false;}},
      beginGoogle(){if(dead||busy||phase!=='primary')return null;const ticket=++epoch;try{context=api.capture();check(ticket);phase='google';view('Esperando la autenticación de Google. Todavía no se inició sesión; puedes descartarla.');check(ticket);return ticket;}catch(error){failure(error,ticket);return null;}},
      async completeGoogle(payload,ticket){if(dead||busy||phase!=='google'||ticket!==epoch)return false;try{check(ticket);busy=true;view('Comprobando tu cuenta de Google…');check(ticket);return await consumePrimary('google',payload,ticket);}catch(error){failure(error,ticket);return false;}},
      selectMethod(value){if(!dead&&!busy&&phase==='factor'&&methods.has(value)){method=value;options.onClear?.();view('Usa una prueba de '+(value==='totp'?'tu autenticador.':'recuperación que no hayas usado.'));}},
      expire(){if(!dead&&['factor','email'].includes(phase)&&Date.now()>=Date.parse(expiry)){cancel();view('La verificación venció. Inicia un acceso nuevo.');}},
      get active(){return!dead;},get phase(){return phase;}};
  }
  function mount(options){
    const get=id=>document.getElementById(id),registration=options.registration===true,form=get(options.formId||'loginForm'),factor=get('mfa-login-factor'),emailForm=get('mfa-login-email'),panel=get('mfa-login-panel'),status=get('mfa-login-status');
    const googleBox=get('googleBtnContainer'),googleError=get('googleErrorMsg'),googleHelp=get('mfa-login-google-help'),button=get('submitBtn'),error=get('errorMsg');
    const emailInput=get('mfa-login-email-code'),emailFeedback=get('mfa-login-email-feedback'),emailSubmit=get('mfa-login-email-submit');
    const typeButtons=registration?[get('btnGym'),get('btnUsuario')]:[],audience=()=>options.readAudience?options.readAudience():options.audience;
    const initialLabel=button.textContent;let googleTicket=null,googleEpoch=0,googleRender=0,renderGoogle=null,bootReady=false,invalidEmailInput=false;
    const clear=()=>{form.password.value='';if(registration)form.confirm_password.value='';get('mfa-login-code').value='';get('mfa-login-recovery').value='';get('mfa-login-email-code').value='';};
    const controller=create({audience:registration?undefined:options.audience,ready:Api.session.ready,onClear:clear,onView(update){
      googleTicket=null;googleEpoch++;
      googleHelp.hidden=update.code!=='google_link_required';
      if(update.phase!=='email'||update.busy)invalidEmailInput=false;
      const emailInvalid=update.phase==='email'&&!update.busy&&(invalidEmailInput||update.code==='google_email_code_invalid');
      panel.setAttribute('data-phase',update.phase);panel.setAttribute('aria-busy',String(update.busy));
      panel.hidden=update.phase==='primary';factor.hidden=update.phase!=='factor';emailForm.hidden=update.phase!=='email';form.hidden=['email','factor','google','confirmed','destination_error'].includes(update.phase);googleBox.hidden=update.phase!=='primary';googleBox.inert=update.busy;
      get('mfa-login-title').textContent=update.phase==='email'?'Confirma tu correo':update.phase==='factor'?'Verifica tu cuenta':update.phase==='google'?'Continuar con Google':'Verificar acceso';
      get('mfa-login-email-target').textContent=update.phase==='email'&&update.maskedEmail?'Enviado a '+update.maskedEmail:'';
      for(const control of form.querySelectorAll('input,button'))control.disabled=update.busy||update.phase==='invalidated';
      for(const control of factor.querySelectorAll('input,button,select'))control.disabled=update.busy;
      for(const control of emailForm.querySelectorAll('input,button'))control.disabled=update.busy;
      emailSubmit.disabled=update.busy;emailSubmit.textContent=update.busy?'Comprobando…':'Confirmar y continuar';emailSubmit.setAttribute('data-busy',String(update.busy));
      emailInput.setAttribute('aria-invalid',String(emailInvalid));emailFeedback.hidden=!emailInvalid;
      emailFeedback.textContent=emailInvalid?(invalidEmailInput?'Escribe las seis cifras del código.':'Revisa el código. Puede haber vencido o ya haberse usado.'):'';
      for(const control of typeButtons)control.disabled=update.busy||update.phase!=='primary';
      get('mfa-login-cancel').disabled=['invalidated','confirmed','destination_error'].includes(update.phase);get('mfa-login-method').value=update.method;
      get('mfa-login-cancel').hidden=['invalidated','confirmed','destination_error'].includes(update.phase);
      get('mfa-login-reopen').hidden=['confirmed','destination_error'].includes(update.phase);
      get('mfa-login-destination').hidden=update.phase!=='destination_error';get('mfa-login-destination').disabled=update.busy;
      get('mfa-login-code-label').hidden=update.method!=='totp';get('mfa-login-recovery-label').hidden=update.method!=='recovery_code';
      let visibleMessage=update.message;
      if(update.phase==='email'&&update.busy)visibleMessage='Estamos comprobando tu código…';
      else if(update.phase==='email'&&visibleMessage?.startsWith('Enviamos un código'))visibleMessage='Escribe el código que te enviamos para continuar.';
      else if(update.phase==='factor'&&visibleMessage?.startsWith('Ahora confirma'))visibleMessage='Usa el código de tu aplicación autenticadora.';
      status.hidden=emailInvalid;status.textContent=visibleMessage;
      status.setAttribute('role',update.code||update.phase==='invalidated'?'alert':'status');
      status.setAttribute('aria-live',update.code||update.phase==='invalidated'?'assertive':'polite');
      error.textContent=update.message;error.style.display=update.phase==='primary'?'block':'none';
      button.textContent=update.busy?'Verificando…':initialLabel;
      if(update.phase==='primary'&&!update.busy&&renderGoogle)renderGoogle();
      if(update.phase==='email'&&!update.busy)get('mfa-login-email-code').focus();
      else if(update.phase==='factor'&&!update.busy)get(update.method==='totp'?'mfa-login-code':'mfa-login-recovery').focus();
      else if(update.phase==='invalidated')status.focus();
    },async onAuthenticated(handle,authentication={}){
      Api.mfa.check(handle);const {me,handle:checked}=await Api.mfa.context();Api.mfa.check(handle);Api.mfa.check(checked);
      if(!['gym','usuario'].includes(me.tipo)||(!registration&&authentication.primaryMethod!=='google'&&((options.audience==='gym'&&me.tipo!=='gym'&&!me.team_gym_id)||(options.audience==='usuario'&&me.tipo!=='usuario'&&!me.team_gym_id))))throw new Error('No se confirmó el destino de esta cuenta.');
      Api.mfa.check(handle);window.location.assign(me.team_gym_id?'/equipo/inicio':me.tipo==='gym'?(registration?'/configuracion':'/dashboard'):'/mi-plan');
    }});
    form.addEventListener('submit',event=>{
      event.preventDefault();if(controller.phase!=='primary'||!controller.active)return false;googleTicket=null;googleEpoch++;
      if(!registration)return controller.primary('password',{email:form.email.value.trim(),password:form.password.value,remember_me:get('rememberMe').checked});
      const password=form.password.value;
      let problem='';if(password!==form.confirm_password.value)problem='Las contraseñas no coinciden.';
      else if(Array.from(password).length<15||new TextEncoder().encode(password).length>72)problem='La contraseña debe tener al menos 15 caracteres y como máximo 72 bytes UTF-8.';
      const tipo=audience();if(!['gym','usuario'].includes(tipo))problem='Selecciona un tipo de cuenta válido.';
      if(problem){error.textContent=problem;error.style.display='block';return false;}
      return controller.primary('registration',{email:form.email.value.trim(),password,nombre:form.nombre.value.trim(),apellido:form.apellido.value.trim(),tipo});
    });
    emailForm.addEventListener('submit',event=>{event.preventDefault();const value=emailInput.value.trim();invalidEmailInput=!/^\d{6}$/.test(value);return controller.verifyEmail(value);});
    const clearEmailFeedback=()=>{const wasInvalid=!emailFeedback.hidden;invalidEmailInput=false;emailInput.setAttribute('aria-invalid','false');emailFeedback.hidden=true;emailFeedback.textContent='';status.hidden=false;status.setAttribute('role','status');status.setAttribute('aria-live','polite');if(wasInvalid)status.textContent='Escribe el código que aparece en tu correo.';};
    emailInput.addEventListener('input',clearEmailFeedback);
    emailInput.addEventListener('paste',event=>{const pasted=(event.clipboardData?.getData('text')||'').replace(/[\s-]/g,'');if(/^\d{6}$/.test(pasted)){event.preventDefault();emailInput.value=pasted;clearEmailFeedback();}});
    factor.addEventListener('submit',event=>{event.preventDefault();const input=get(get('mfa-login-method').value==='totp'?'mfa-login-code':'mfa-login-recovery');const value=input.value.trim();return controller.verify(value);});
    get('mfa-login-method').addEventListener('change',event=>controller.selectMethod(event.target.value));
    get('mfa-login-cancel').addEventListener('click',()=>{googleTicket=null;googleEpoch++;controller.cancel();form.email.focus();});
    get('mfa-login-reopen').addEventListener('click',()=>window.location.reload());
    get('mfa-login-destination').addEventListener('click',()=>controller.retryDestination());
    button.disabled=true;googleBox.hidden=true;status.textContent='Verificando la sesión del navegador…';
    Api.session.ready.then(()=>{if(!controller.active)return;bootReady=true;button.disabled=false;status.textContent='';googleBox.hidden=false;if(renderGoogle)renderGoogle();}).catch(error=>{button.disabled=true;googleBox.hidden=true;status.textContent=error.message;status.setAttribute('role','alert');status.focus();});
    document.querySelector('.pwd-toggle')?.addEventListener('click',event=>{const field=get('pwdField');field.type=field.type==='password'?'text':'password';event.currentTarget.setAttribute('aria-pressed',String(field.type==='text'));event.currentTarget.setAttribute('aria-label',field.type==='text'?'Ocultar contraseña':'Mostrar contraseña');});
    const interval=setInterval(()=>controller.expire(),1000);window.addEventListener('pagehide',()=>clearInterval(interval),{once:true});
    if(!options.googleClientId){googleBox.textContent='Google no está configurado. Puedes usar tu contraseña.';return controller;}
    const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;script.nonce=options.nonce;
    script.onerror=()=>{googleError.textContent='No se pudo cargar Google. Usa tu contraseña o vuelve a abrir esta página.';googleError.style.display='block';};
    script.onload=()=>{if(!controller.active)return;google.accounts.id.initialize({client_id:options.googleClientId,ux_mode:'popup',auto_select:false,callback:async response=>{
      const attempt=googleTicket;if(!attempt||attempt.epoch!==googleEpoch||response.state!==attempt.state||controller.phase!=='google')return;googleTicket=null;
      try{Api.mfa.check(attempt.context);}catch{controller.invalidate();return;}
      await controller.completeGoogle({credential:response.credential,tipo:attempt.audience},attempt.flow);
    }});renderGoogle=()=>{if(!bootReady)return;googleBox.replaceChildren();const buttonState='mfa-login-'+(++googleRender);google.accounts.id.renderButton(googleBox,{theme:'filled_black',size:'large',shape:'rectangular',text:'continue_with',width:Math.min(400,googleBox.offsetWidth||300),locale:'es',state:buttonState,click_listener:()=>{
      if(controller.phase!=='primary'||!controller.active)return;try{const tipo=audience();if(!['gym','usuario'].includes(tipo))return;const context=Api.mfa.capture(),flow=controller.beginGoogle();if(flow===null)return;googleTicket={epoch:googleEpoch,context,state:buttonState,flow,audience:tipo};}catch{controller.invalidate();}
    }});};renderGoogle();};document.head.appendChild(script);return controller;
  }
  window.MfaLogin=Object.freeze({create,mount,message});
})();
