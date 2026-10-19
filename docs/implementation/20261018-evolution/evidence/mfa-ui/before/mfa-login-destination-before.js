/* Public primary/challenge lifecycle. No secret is exposed through view DTOs. */
(() => {
  'use strict';
  const methods=new Set(['totp','recovery_code']);
  const messages={mfa_throttled:'Hay un límite temporal de intentos. Espera antes de volver a verificar.',mfa_verification_failed:'No se confirmó el código. Usa una prueba vigente e inténtalo de nuevo.',mfa_proof_unavailable:'La verificación venció o ya se usó. Inicia un acceso nuevo.',mfa_unconfirmed:'No llegó una confirmación fiable. Puede haberse consumido la prueba; inicia un acceso nuevo.',mfa_service_unavailable:'La verificación no está disponible. No se inició sesión; vuelve a consultar.'};
  function message(error){return messages[error.code]||(error.status===429?messages.mfa_throttled:error.status===503?messages.mfa_unconfirmed:'No se pudo confirmar el acceso. Revisa los datos o inicia un acceso nuevo.');}
  function create(options={}){
    const api=options.api||Api.mfa;
    let context=null,challenge=null,method='totp',expiry=null,phase='primary',busy=false,epoch=0,dead=false,committing=false;
    const changed=()=>Object.assign(new Error('La sesión cambió. Vuelve a abrir esta página.'),{code:'session_changed'});
    function view(text){options.onView?.({phase,busy,method,expiresAt:expiry,message:text});}
    function clearProof(){challenge=null;expiry=null;options.onClear?.();}
    function invalidate(){if(dead)return;dead=true;epoch++;busy=false;context=null;clearProof();phase='invalidated';view('La sesión cambió. Se descartó la verificación anterior. Vuelve a abrir esta página.');}
    function check(ticket=epoch){if(dead||ticket!==epoch||!context)throw changed();api.check(context);}
    function cancel(){if(dead)return;epoch++;busy=false;clearProof();if(dead)return;context=null;phase='primary';view('Verificación descartada. Puedes iniciar un acceso nuevo.');}
    function failure(error,ticket){if(dead||ticket!==epoch)return;
      try{if(context)api.check(context);}catch{invalidate();return;}
      busy=false;
      if(['session_changed','session_storage_error','session_expired'].includes(error.code)){invalidate();return;}
      if(!error.status||error.status===503||['mfa_proof_unavailable','mfa_unconfirmed'].includes(error.code)){clearProof();phase='primary';context=null;}
      view(message(error)+(error.retryAfter?' Respeta el tiempo de espera indicado por el servidor.':''));
    }
    async function finish(data,ticket){
      check(ticket);
      if(!data || !['gym','usuario'].includes(data.tipo) || (options.audience==='gym' && data.tipo!=='gym'&&!data.team_gym_id) ||
          (options.audience==='usuario'&&data.tipo!=='usuario'&&!data.team_gym_id))throw Object.assign(new Error('Portal diferente'),{code:'login_audience_mismatch',status:403});
      clearProof();check(ticket);phase='committing';committing=true;
      try{context=api.finishLogin(data,context);}finally{committing=false;}
      check(ticket);data=null;phase='confirmed';view('Acceso confirmado. Consultando el destino de tu cuenta…');
      await options.onAuthenticated?.(context);check(ticket);
    }
    async function consumePrimary(kind,payload,ticket){
      try{
        check(ticket);
        const data=await (kind==='google'?api.primaryGoogle(payload,context):api.primaryPassword(payload,context));check(ticket);
        options.onClear?.();check(ticket);
        if(data.mfa_required===true){challenge=data.challenge;expiry=data.expires_at;method='totp';phase='factor';busy=false;view('La primaria fue válida. Confirma un factor para iniciar sesión.');return true;}
        await finish(data,ticket);busy=false;return true;
      }catch(error){failure(error,ticket);return false;}
    }
    async function primary(kind,payload){
      if(dead||busy||phase!=='primary')return false;
      const ticket=++epoch;
      try{context=api.capture();check(ticket);busy=true;view('Comprobando la autenticación primaria…');check(ticket);return await consumePrimary(kind,payload,ticket);}
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
    const notify=()=>{if(!committing)invalidate();};
    window.addEventListener('metodobase-session-changed',notify);window.addEventListener('pagehide',invalidate);
    window.addEventListener('storage',event=>{if(event.key===null||['mb_token','mb_refresh_token'].includes(event.key))invalidate();});
    return{primary,verify,cancel,invalidate,
      beginGoogle(){if(dead||busy||phase!=='primary')return null;const ticket=++epoch;try{context=api.capture();check(ticket);phase='google';view('Esperando la autenticación de Google. Todavía no se inició sesión; puedes descartarla.');check(ticket);return ticket;}catch(error){failure(error,ticket);return null;}},
      async completeGoogle(payload,ticket){if(dead||busy||phase!=='google'||ticket!==epoch)return false;try{check(ticket);busy=true;view('Comprobando la primaria de Google…');check(ticket);return await consumePrimary('google',payload,ticket);}catch(error){failure(error,ticket);return false;}},
      selectMethod(value){if(!dead&&!busy&&phase==='factor'&&methods.has(value)){method=value;options.onClear?.();view('Usa una prueba de '+(value==='totp'?'tu autenticador.':'recuperación que no hayas usado.'));}},
      expire(){if(!dead&&phase==='factor'&&Date.now()>=Date.parse(expiry)){cancel();view('La verificación venció. Inicia un acceso nuevo.');}},
      get active(){return!dead;},get phase(){return phase;}};
  }
  function mount(options){
    const get=id=>document.getElementById(id),form=get('loginForm'),factor=get('mfa-login-factor'),panel=get('mfa-login-panel'),status=get('mfa-login-status');
    const googleBox=get('googleBtnContainer'),googleError=get('googleErrorMsg'),button=get('submitBtn'),error=get('errorMsg');
    const initialLabel=button.textContent;let googleTicket=null,googleEpoch=0,googleRender=0,renderGoogle=null;
    const clear=()=>{form.password.value='';get('mfa-login-code').value='';get('mfa-login-recovery').value='';};
    const controller=create({audience:options.audience,onClear:clear,onView(update){
      googleTicket=null;googleEpoch++;
      panel.hidden=update.phase==='primary';factor.hidden=update.phase!=='factor';form.hidden=['factor','google'].includes(update.phase);googleBox.hidden=update.phase!=='primary';googleBox.inert=update.busy;
      for(const control of form.querySelectorAll('input,button'))control.disabled=update.busy||update.phase==='invalidated';
      for(const control of factor.querySelectorAll('input,button,select'))control.disabled=update.busy;
      get('mfa-login-cancel').disabled=update.phase==='invalidated';get('mfa-login-method').value=update.method;
      get('mfa-login-code-label').hidden=update.method!=='totp';get('mfa-login-recovery-label').hidden=update.method!=='recovery_code';
      status.textContent=update.message;error.textContent=update.message;error.style.display=update.phase==='primary'?'block':'none';
      button.textContent=update.busy?'Verificando…':initialLabel;
      if(update.phase==='primary'&&!update.busy&&renderGoogle)renderGoogle();
      if(update.phase==='factor'&&!update.busy)get(update.method==='totp'?'mfa-login-code':'mfa-login-recovery').focus();
      else if(update.phase==='invalidated')status.focus();
    },async onAuthenticated(handle){
      Api.mfa.check(handle);const {me,handle:checked}=await Api.mfa.context();Api.mfa.check(handle);Api.mfa.check(checked);
      if((options.audience==='gym'&&me.tipo!=='gym'&&!me.team_gym_id)||(options.audience==='usuario'&&me.tipo!=='usuario'&&!me.team_gym_id))throw new Error('No se confirmó el destino de esta cuenta.');
      Api.mfa.check(handle);window.location.assign(me.team_gym_id?'/equipo/inicio':options.audience==='gym'?'/dashboard':'/mi-plan');
    }});
    form.addEventListener('submit',event=>{event.preventDefault();googleTicket=null;googleEpoch++;return controller.primary('password',{email:form.email.value.trim(),password:form.password.value,remember_me:get('rememberMe').checked});});
    factor.addEventListener('submit',event=>{event.preventDefault();const input=get(get('mfa-login-method').value==='totp'?'mfa-login-code':'mfa-login-recovery');const value=input.value.trim();return controller.verify(value);});
    get('mfa-login-method').addEventListener('change',event=>controller.selectMethod(event.target.value));
    get('mfa-login-cancel').addEventListener('click',()=>{googleTicket=null;googleEpoch++;controller.cancel();form.email.focus();});
    get('mfa-login-reopen').addEventListener('click',()=>window.location.reload());
    document.querySelector('.pwd-toggle')?.addEventListener('click',event=>{const field=get('pwdField');field.type=field.type==='password'?'text':'password';event.currentTarget.setAttribute('aria-pressed',String(field.type==='text'));event.currentTarget.setAttribute('aria-label',field.type==='text'?'Ocultar contraseña':'Mostrar contraseña');});
    const interval=setInterval(()=>controller.expire(),1000);window.addEventListener('pagehide',()=>clearInterval(interval),{once:true});
    if(!options.googleClientId){googleBox.textContent='Google no está configurado. Puedes usar tu contraseña.';return controller;}
    const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;script.nonce=options.nonce;
    script.onerror=()=>{googleError.textContent='No se pudo cargar Google. Usa tu contraseña o vuelve a abrir esta página.';googleError.style.display='block';};
    script.onload=()=>{if(!controller.active)return;google.accounts.id.initialize({client_id:options.googleClientId,ux_mode:'popup',auto_select:false,essential_claims:'auth_time, amr',callback:async response=>{
      const attempt=googleTicket;if(!attempt||attempt.epoch!==googleEpoch||response.state!==attempt.state||controller.phase!=='google')return;googleTicket=null;
      try{Api.mfa.check(attempt.context);}catch{controller.invalidate();return;}
      await controller.completeGoogle({credential:response.credential,tipo:options.audience},attempt.flow);
    }});renderGoogle=()=>{googleBox.replaceChildren();const buttonState='mfa-login-'+(++googleRender);google.accounts.id.renderButton(googleBox,{theme:'filled_black',size:'large',shape:'rectangular',text:'continue_with',width:Math.min(400,googleBox.offsetWidth||300),locale:'es',state:buttonState,click_listener:()=>{
      if(controller.phase!=='primary'||!controller.active)return;try{const context=Api.mfa.capture(),flow=controller.beginGoogle();if(flow===null)return;googleTicket={epoch:googleEpoch,context,state:buttonState,flow};}catch{controller.invalidate();}
    }});};renderGoogle();};document.head.appendChild(script);return controller;
  }
  window.MfaLogin=Object.freeze({create,mount,message});
})();
