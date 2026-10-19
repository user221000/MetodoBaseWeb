/* Invitation bearers live only in memory. New links use a fragment, never storage. */
(function () {
  'use strict';
  var fragment=new URLSearchParams(location.hash.slice(1)).getAll('token'), query=new URLSearchParams(location.search).getAll('token');
  var values=fragment.concat(query), token=values.length===1 ? values[0] : null, valid=false, busy=false;
  history.replaceState({},'',location.pathname);
  var feedback=document.getElementById('invite-feedback'), form=document.getElementById('invite-form'), submit=document.getElementById('invite-submit');
  function notify(text){feedback.textContent=text;feedback.hidden=false;}
  function showForm(){document.getElementById('invite-session').hidden=!valid || !localStorage.getItem('mb_token');form.hidden=!valid || !!localStorage.getItem('mb_token');submit.disabled=busy;}
  async function load(){
    if(busy)return;valid=false;busy=true;showForm();document.getElementById('invite-retry').hidden=true;
    if(!token || !/^[A-Za-z0-9_-]{43}$/.test(token)){notify('El enlace no está completo. Abre la invitación original o pide un enlace nuevo.');busy=false;return;}
    try{
      var info=await Api.team.info(token);
      if(!info || !['pending','expired'].includes(info.status) || typeof info.email!=='string' || typeof info.gym_name!=='string' || typeof info.can_accept!=='boolean' || !['admin','nutriologo','viewer'].includes(info.role) || info.membership_type!=='professional')throw new Error('No se pudo confirmar la información de la invitación.');
      document.getElementById('invite-gym').textContent=info.gym_name;document.getElementById('invite-email').textContent=info.email;document.getElementById('invite-role').textContent=info.role_display || info.role;
      var date=new Date(info.expires_at);document.getElementById('invite-expiry').textContent=Number.isNaN(date.getTime()) ? 'Por confirmar' : date.toLocaleString('es-MX');document.getElementById('invite-details-section').hidden=false;
      valid=info.status==='pending' && info.is_expired===false && info.can_accept===true && !Number.isNaN(date.getTime());
      var blocked=info.status==='pending' && info.can_accept===false;
      notify(valid ? 'Invitación disponible. Confirma los datos y crea una contraseña para aceptar.' : blocked ? (typeof info.unavailable_reason==='string' ? info.unavailable_reason : 'El plan actual del gimnasio no permite nuevas incorporaciones. Contacta a quien administra el equipo.') : 'La invitación venció. Pide un enlace nuevo a quien administra el gimnasio.');
      document.getElementById('invite-retry').hidden=!blocked;
    }catch(error){notify(error.message+' Si el enlace ya se usó o fue retirado, inicia sesión o pide otro.');document.getElementById('invite-retry').hidden=false;}
    finally{busy=false;showForm();}
  }
  document.getElementById('invite-retry').addEventListener('click',load);
  window.addEventListener('hashchange',function(){
    var incoming=new URLSearchParams(location.hash.slice(1)).getAll('token');
    history.replaceState({},'',location.pathname);
    if(busy){notify('Hay una solicitud en curso. Espera su resultado antes de abrir otra invitación.');return;}
    if (incoming.length === 1) {
      token = incoming[0];
    } else {
      token = null;
    }
    valid=false;document.getElementById('invite-details-section').hidden=true;
    document.getElementById('invite-password').value='';document.getElementById('invite-confirm').value='';
    load();
  });
  document.getElementById('invite-logout').addEventListener('click',async function(){
    if(busy)return;busy=true;this.disabled=true;
    try{var response=await fetch('/api/auth/logout',{method:'POST',headers:{'Authorization':'Bearer '+localStorage.getItem('mb_token')}});if(!response.ok && response.status!==401)throw new Error('No se pudo confirmar el cierre de la sesión. Intenta de nuevo.');Api.clearTokens();['mb_tipo','mb_nombre','mb_email'].forEach(function(key){localStorage.removeItem(key);});notify('Sesión cerrada. Revisa el correo invitado antes de aceptar.');}
    catch(error){notify(error.message);}
    finally{busy=false;this.disabled=false;showForm();}
  });
  form.addEventListener('submit',async function(event){
    event.preventDefault();if(busy || !valid || localStorage.getItem('mb_token'))return;
    var password=document.getElementById('invite-password'), confirmation=document.getElementById('invite-confirm');
    if(password.value!==confirmation.value){notify('Las contraseñas no coinciden. Revisa la confirmación.');confirmation.focus();return;}
    busy=true;submit.disabled=true;
    try{
      var result=await Api.team.accept(token,password.value);
      if(!result || result.success!==true || typeof result.access_token!=='string' || typeof result.refresh_token!=='string')throw new Error('No se pudo confirmar el acceso. Consulta la invitación antes de reintentar.');
      valid=false;token=null;password.value='';confirmation.value='';showForm();
      var response=await fetch('/api/auth/me',{headers:{'Authorization':'Bearer '+result.access_token}});
      if(!response.ok)throw new Error('La invitación se aceptó, pero no pudimos verificar la sesión. Inicia sesión para continuar.');
      var me=await response.json();
      if(!me || !me.team_gym_id || !['admin','nutriologo','viewer'].includes(me.role))throw new Error('No se pudo confirmar el acceso profesional. Inicia sesión para consultar tu cuenta.');
      Api.saveTokens({token:result.access_token,refresh_token:result.refresh_token});localStorage.setItem('mb_tipo',me.tipo);localStorage.setItem('mb_nombre',me.nombre || 'Mi cuenta');localStorage.setItem('mb_email',me.email || '');location.replace('/equipo/inicio');
    }catch(error){notify(error.message);if([400,402,409,410].includes(error.status)){valid=false;form.hidden=true;document.getElementById('invite-retry').hidden=false;}}
    finally{busy=false;submit.disabled=false;}
  });
  load();
})();
