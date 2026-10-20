/* Team UI consumes capabilities returned by the authenticated team API. */
(function () {
  'use strict';
  var labels = {owner:'Propietario',admin:'Administrador',nutriologo:'Nutriólogo',viewer:'Solo lectura'};
  var actor = null, state = null, busy = false, context = null, epoch = 0, invalid = false, uncertain = false;
  var feedback = document.getElementById('team-feedback');
  function invalidate() {
    if(invalid)return;invalid=true;epoch++;actor=null;state=null;context=null;busy=false;
    if(document.getElementById('professional-context')){document.getElementById('professional-context').textContent='La sesión cambió. Recarga para consultar tu equipo.';return;}
    document.getElementById('team-invite-form').reset();document.getElementById('team-members').replaceChildren();document.getElementById('team-role').replaceChildren();
    document.getElementById('team-share').hidden=true;document.getElementById('team-share-link').value='';document.getElementById('team-delivery').textContent='';document.getElementById('team-share-expiry').textContent='';
    document.getElementById('team-summary').textContent='';document.getElementById('team-plan-requirement').textContent='';document.getElementById('team-management').hidden=true;
    document.getElementById('team-loading').hidden=false;document.getElementById('team-loading').textContent='La sesión cambió o no se pudo leer de forma segura. Recarga para consultar tu equipo.';
    document.getElementById('team-refresh').disabled=true;message('Se descartaron los datos de la sesión anterior.');
    document.querySelectorAll('#team-management input,#team-management button,#team-management select').forEach(function(control){control.disabled=true;});
  }
  function current(ticket) {if(invalid || ticket!==epoch || !context)return false;try{Api.stats.validarContexto(context);return !invalid && ticket===epoch;}catch(_){invalidate();return false;}}
  async function verify(ticket) {if(!current(ticket))return false;await Api.stats.verificarContexto(context);return current(ticket);}
  function has(permission) { return actor && Array.isArray(actor.permissions) && actor.permissions.some(function(value) { return Array.isArray(value) && value.join(':') === permission; }); }
  function message(value) { feedback.textContent=value; feedback.hidden=false; }
  function failure(error) { return error.message + (error.requestId ? ' Referencia: '+error.requestId : ''); }
  function setBusy(value) { busy=value; document.querySelectorAll('#team-management input,#team-management button,#team-management select,#team-refresh').forEach(function(control) { control.disabled=invalid || value || (uncertain && control.id!=='team-refresh'); }); if (!value && !invalid) availability(); }
  function availability() {
    var allowed=state && state.capabilities.invite === true && has('invite:team') && state.assignable_roles.length>0;
    document.querySelectorAll('#team-invite-form input,#team-invite-form select,#team-invite-form button').forEach(function(control){control.disabled=invalid || busy || uncertain || !allowed;});
  }
  function element(tag,text,className) { var value=document.createElement(tag); if(text!==undefined) value.textContent=text; if(className) value.className=className; return value; }
  function button(text,callback) { var value=element('button',text,'team-button');value.type='button';value.addEventListener('click',callback);return value; }
  function showInvitation(result, ticket) {
    if(!current(ticket))return;
    if (!result || result.success!==true || !['not_confirmed','provider_accepted'].includes(result.delivery_status)) throw new Error('No se pudo confirmar la invitación. Consulta el equipo antes de reintentar.');
    var url;
    try { url=new URL(result.invitation_link); } catch (_) { throw new Error('No se pudo confirmar el enlace. Consulta el equipo antes de reintentar.'); }
    if (url.origin!==location.origin || url.pathname!=='/auth/accept-invite' || !/^[A-Za-z0-9_-]{43}$/.test(new URLSearchParams(url.hash.slice(1)).get('token') || '')) throw new Error('No se pudo confirmar un enlace válido para esta aplicación. Consulta el equipo.');
    document.getElementById('team-share-link').value=url.href;
    document.getElementById('team-delivery').textContent=result.delivery_status==='provider_accepted' ? 'El proveedor aceptó el correo. Su entrega no está confirmada; también puedes compartir este enlace con la persona invitada.' : 'La invitación se creó. La entrega del correo no está confirmada; comparte este enlace con la persona invitada.';
    var date=new Date(result.expires_at);
    document.getElementById('team-share-expiry').textContent=Number.isNaN(date.getTime()) ? 'Consulta la vigencia al abrir el enlace.' : 'Vence: '+date.toLocaleString('es-MX');
    document.getElementById('team-share').hidden=false;
  }
  function render(ticket) {
    if(!current(ticket))return;
    var list=document.getElementById('team-members');list.replaceChildren();
    var roles=document.getElementById('team-role'), previous=roles.value;roles.replaceChildren();
    var placeholder=element('option','Elige un rol');placeholder.value='';roles.appendChild(placeholder);
    state.assignable_roles.forEach(function(role) { var option=element('option',labels[role]);option.value=role;roles.appendChild(option); });
    roles.value=state.assignable_roles.includes(previous) ? previous : '';
    var requirement=document.getElementById('team-plan-requirement');
    requirement.textContent=state.invitation_requirement || '';requirement.hidden=!state.invitation_requirement;
    document.getElementById('team-summary').textContent=state.total+' personas; '+state.pending_invitations+' invitaciones pendientes.';
    var status={active:'Acceso activo',pending:'Invitación pendiente',expired:'Invitación vencida',inactive:'Acceso inactivo'};
    state.members.forEach(function(member) {
      var card=element('li',undefined,'team-member');
      card.append(element('h3',(member.nombre+' '+(member.apellido || '')).trim()),element('p',member.email),element('p',labels[member.role] || 'Rol por confirmar'),element('p',status[member.invitation_status] || 'Estado por confirmar','team-muted'));
      if (member.invitation_expires_at) { var expires=new Date(member.invitation_expires_at);if(!Number.isNaN(expires.getTime()))card.append(element('p','Vence: '+expires.toLocaleString('es-MX'),'team-muted')); }
      var actions=element('div',undefined,'team-actions');
      if (member.can_change_role===true && has('update_role:team')) {
        var label=element('label','Rol de '+member.nombre), select=element('select',undefined,'team-input');
        state.assignable_roles.forEach(function(role) {var option=element('option',labels[role]);option.value=role;select.appendChild(option);});select.value=member.role;label.appendChild(select);actions.appendChild(label);
        actions.appendChild(button('Guardar rol',function() {var desiredRole=select.value;run(async function(token) {var result=await Api.team.role(member.id,desiredRole);if(!await verify(token))return;if(!result || result.role!==desiredRole)throw new Error('No se confirmó el cambio de rol. Consulta el equipo.');message('Rol actualizado. Las sesiones anteriores de esa persona se invalidaron.');});}));
      }
      if (member.can_resend===true && has('invite:team')) actions.appendChild(button('Crear enlace nuevo',function() {run(async function(token) {var result=await Api.team.resend(member.id);if(!await verify(token))return;showInvitation(result,token);message('Se creó un enlace nuevo. El anterior dejó de funcionar.');});}));
      if (member.can_remove===true && has('remove:team') && state.capabilities.revoke_preserves_identity===true) actions.appendChild(button('Retirar acceso',function() {
        if(!confirm('¿Retirar el acceso profesional de '+member.nombre+'? Su cuenta y sus datos personales se conservarán.'))return;
        run(async function(token) {var result=await Api.team.remove(member.id);if(!await verify(token))return;if(!result || result.success!==true || result.status!=='revoked')throw new Error('No se confirmó la revocación. Consulta el equipo.');document.getElementById('team-share').hidden=true;document.getElementById('team-share-link').value='';message('Acceso al equipo revocado. La cuenta y los datos personales se conservaron.');});
      }));
      if(actions.children.length)card.appendChild(actions);list.appendChild(card);
    });
  }
  async function load(ticket) {
    if(!current(ticket))return;
    state=null;document.getElementById('team-management').hidden=true;document.getElementById('team-loading').hidden=false;document.getElementById('team-loading').textContent='Consultando el equipo…';
    var value=await Api.team.list();
    if(!await verify(ticket))return;
    if(!value || !Array.isArray(value.members) || !Array.isArray(value.assignable_roles) || !value.assignable_roles.every(function(role){return ['admin','nutriologo','viewer'].includes(role);}) || !value.capabilities || typeof value.capabilities.invite!=='boolean' || (value.invitation_requirement!=null && typeof value.invitation_requirement!=='string') || !Number.isInteger(value.total) || !Number.isInteger(value.pending_invitations) || !value.members.every(function(member){return member && typeof member.id==='string' && typeof member.email==='string' && Object.prototype.hasOwnProperty.call(labels,member.role);}))throw new Error('El servidor devolvió un equipo incompleto. Vuelve a consultar.');
    state=value;uncertain=false;render(ticket);if(!current(ticket))return;document.getElementById('team-management').hidden=false;document.getElementById('team-loading').hidden=true;
  }
  async function run(action, mutation) {
    if(busy || invalid || !actor || (uncertain && mutation!==false))return;var ticket=epoch;setBusy(true);
    try{if(!await verify(ticket))return;await action(ticket);if(!current(ticket))return;await load(ticket);}
    catch(error){if(!current(ticket))return;if(['session_changed','session_expired','session_storage_error'].includes(error.code)){invalidate();return;}
      if(mutation!==false && (!error.status || error.status>=500) && !['mfa_cancelled','mfa_ui_unavailable'].includes(error.code))uncertain=true;
      message(failure(error)+(uncertain?' El resultado es incierto. Consulta el equipo antes de iniciar otra acción.':''));if(!state)document.getElementById('team-loading').textContent='No se pudo consultar el equipo. Usa Consultar equipo para reintentar.';}
    finally{if(current(ticket))setBusy(false);}
  }
  window.addEventListener('metodobase-session-changed',invalidate);window.addEventListener('storage',function(event){if(!event.key || ['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key))current(epoch);});window.addEventListener('pagehide',invalidate);
  (async function() {
    var ticket=epoch;
    try {
      context=await Api.stats.contexto();if(invalid || ticket!==epoch)return;actor=await Api.auth.me();if(!await verify(ticket))return;
      if(document.getElementById('professional-context')) {
        if(!actor || !actor.team_gym_id) return;
        document.getElementById('professional-context').textContent='Equipo del gimnasio · '+(actor.role_display || labels[actor.role] || 'Rol por confirmar');return;
      }
      if(!actor || !has('read:team')) {document.getElementById('team-loading').textContent='Tu rol no permite administrar el equipo. Usa las secciones disponibles en el menú.';document.getElementById('team-refresh').disabled=true;return;}
      document.getElementById('team-refresh').addEventListener('click',function(){run(async function(){feedback.hidden=true;},false);});
      document.getElementById('team-invite-form').addEventListener('submit',function(event){event.preventDefault();if(!current(epoch) || !state || state.capabilities.invite!==true || !has('invite:team'))return;
        var form=event.target,body={nombre:form.elements.namedItem('nombre').value.trim(),apellido:form.elements.namedItem('apellido').value.trim(),email:form.elements.namedItem('email').value.trim(),role:form.elements.namedItem('role').value};
        run(async function(token){var result=await Api.team.invite(body);if(!await verify(token))return;showInvitation(result,token);if(!current(token))return;form.reset();message('Invitación creada. Revisa el enlace y el estado del correo.');});});
      document.getElementById('team-copy-link').addEventListener('click',async function(){var token=epoch;if(!current(token))return;var link=document.getElementById('team-share-link').value;if(!link)return;try{await navigator.clipboard.writeText(link);if(current(token))message('Enlace copiado. Compártelo sólo con la persona invitada.');}catch(_){if(current(token)){message('No se pudo copiar automáticamente. Selecciona el enlace para copiarlo.');document.getElementById('team-share-link').select();}}});
      await run(async function(){},false);
    }catch(error){if(!invalid && ticket===epoch){if(['session_changed','session_storage_error'].includes(error.code))invalidate();else if(feedback)message(failure(error));}}
  })();
})();
