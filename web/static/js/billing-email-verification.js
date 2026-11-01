/* The code confirms this account's mailbox; payment remains a separate action. */
(function () {
  'use strict';
  var dialog=document.getElementById('billing-email-dialog');
  if(!dialog)return;
  var form=document.getElementById('billing-email-form'),input=document.getElementById('billing-email-code');
  var confirm=document.getElementById('billing-email-confirm'),resend=document.getElementById('billing-email-resend');
  var status=document.getElementById('billing-email-status'),errorBox=document.getElementById('billing-email-error');
  var summary=document.getElementById('billing-email-summary'),active=null;
  var names={standard:'Standard',gym_comercial:'Gym Comercial',clinica:'Clínica',pro:'Pro'};
  function failure(code,message){return Object.assign(new Error(message),{code:code,paymentNotStarted:true});}
  function current(state){if(active!==state)return false;try{Api.billingEmail.check(state.handle);return true;}catch(error){finish(state,null,error);return false;}}
  function finish(state,proof,error){
    if(active!==state)return;
    active=null;clearInterval(state.timer);state.challenge=null;input.value='';errorBox.textContent='';errorBox.hidden=true;status.textContent='';
    if(dialog.open)dialog.close();
    if(state.focus && state.focus.isConnected && !state.focus.disabled)state.focus.focus();
    if(error)state.reject(error);else state.resolve(proof);
    proof=null;
  }
  function cancel(){if(active)finish(active,null,failure('billing_email_cancelled','Verificación cancelada.'));}
  function controls(state){
    if(active!==state)return;
    var waiting=Math.max(0,Math.ceil((state.resendAt-Date.now())/1000));
    input.disabled=state.busy || !state.challenge;
    confirm.disabled=state.busy || !state.challenge;
    confirm.textContent=state.verifying?'Verificando…':'Verificar y continuar';
    resend.disabled=state.busy || waiting>0;
    resend.textContent=waiting>0?'Reenviar en '+waiting+' s':'Reenviar código';
    form.setAttribute('aria-busy',String(state.busy));
  }
  function error(state,value){if(!current(state))return;errorBox.textContent=value.message || 'No pudimos confirmar la verificación. Intenta de nuevo.';errorBox.hidden=false;}
  function received(state,value){
    if(value.email_verification_required===false){finish(state,value,null);return;}
    state.challenge=value.challenge;state.expiresAt=Date.parse(value.expires_at);state.resendAt=Date.now()+value.resend_after_seconds*1000;
    status.textContent='Revisa '+value.masked_email+' e introduce el código.';
  }
  async function send(state){
    if(!current(state) || state.busy || Date.now()<state.resendAt)return;
    state.busy=true;state.challenge=null;state.resendAt=Date.now()+60000;input.value='';errorBox.hidden=true;status.textContent='Preparando tu código…';controls(state);
    try{
      var value=await Api.billingEmail.begin(state.action,state.plan,state.handle);
      if(!current(state))return;
      received(state,value);
    }catch(value){
      if(!current(state))return;
      var retry=Number(value.retryAfter);if(Number.isFinite(retry) && retry>0)state.resendAt=Math.max(state.resendAt,Date.now()+retry*1000);
      status.textContent='No pudimos confirmar el envío.';error(state,value);
    }finally{if(current(state)){state.busy=false;controls(state);if(state.challenge)input.focus();}}
  }
  form.addEventListener('submit',async function(event){
    event.preventDefault();var state=active;if(!state || !current(state) || state.busy || !state.challenge)return;
    if(!/^[0-9]{6}$/.test(input.value)){error(state,failure('billing_email_invalid_input','Escribe los seis dígitos del código.'));input.focus();return;}
    var code=input.value;input.value='';state.busy=true;state.verifying=true;errorBox.hidden=true;controls(state);
    try{
      var pending=Api.billingEmail.verify(state.action,state.plan,state.challenge,code,state.handle);code=null;
      var value=await pending;if(!current(state))return;
      finish(state,value.verification_token,null);value=null;
    }catch(value){error(state,value);}
    finally{code=null;if(current(state)){state.busy=false;state.verifying=false;controls(state);input.focus();}}
  });
  resend.addEventListener('click',function(){if(active)send(active);});
  document.getElementById('billing-email-close').addEventListener('click',cancel);
  document.getElementById('billing-email-cancel').addEventListener('click',cancel);
  dialog.addEventListener('cancel',function(event){event.preventDefault();cancel();});
  dialog.addEventListener('close',function(){if(active)cancel();});
  function invalidate(){if(active)finish(active,null,failure('session_changed','La sesión cambió. Inicia la verificación de nuevo.'));}
  window.addEventListener('metodobase-session-changed',invalidate);
  window.addEventListener('pagehide',invalidate);
  window.addEventListener('storage',function(event){if(!event.key || ['mb_session_epoch','mb_token','mb_refresh_token'].includes(event.key)){if(active)current(active);}});
  window.BillingEmailVerification=Object.freeze({
    isOpen:function(){return !!active;},
    authorize:function(action,plan,handle,initial){
      if(active)return Promise.reject(failure('billing_email_busy','Termina o cancela la verificación abierta.'));
      if(typeof dialog.showModal!=='function')return Promise.reject(failure('billing_email_ui_unavailable','Actualiza el navegador para verificar tu correo.'));
      return new Promise(function(resolve,reject){
        var state={action:action,plan:plan,handle:handle,resolve:resolve,reject:reject,challenge:null,resendAt:0,busy:false,focus:document.activeElement};
        active=state;input.value='';errorBox.hidden=true;summary.textContent=plan==='manage'?'Verifica tu correo registrado para gestionar tu suscripción.':'Verifica tu correo registrado antes de continuar con '+(names[plan] || 'tu plan')+'.';
        try{Api.billingEmail.check(handle);dialog.showModal();document.getElementById('billing-email-close').focus();}
        catch(value){finish(state,null,value);return;}
        state.timer=setInterval(function(){if(!current(state))return;if(state.challenge && Date.now()>=state.expiresAt){state.challenge=null;input.value='';status.textContent='El código venció. Solicita uno nuevo para continuar.';}controls(state);},500);
        if(initial){received(state,initial);controls(state);if(state.challenge)input.focus();}else send(state);
      });
    },
  });
})();
