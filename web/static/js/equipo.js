/* Team UI consumes capabilities returned by the authenticated team API. */
(function () {
  'use strict';
  var labels = {owner:'Propietario',admin:'Administrador',nutriologo:'Nutriólogo',viewer:'Solo lectura'};
  var actor = null, state = null, busy = false;
  var feedback = document.getElementById('team-feedback');
  function has(permission) { return actor && Array.isArray(actor.permissions) && actor.permissions.some(function(value) { return Array.isArray(value) && value.join(':') === permission; }); }
  function message(value) { feedback.textContent=value; feedback.hidden=false; }
  function failure(error) { return error.message + (error.requestId ? ' Referencia: '+error.requestId : ''); }
  function setBusy(value) { busy=value; document.querySelectorAll('#team-management button,#team-management select,#team-refresh').forEach(function(control) { control.disabled=value; }); if (!value) availability(); }
  function availability() {
    var allowed=state && state.capabilities.invite === true && has('invite:team') && state.assignable_roles.length>0;
    document.querySelectorAll('#team-invite-form input,#team-invite-form select,#team-invite-form button').forEach(function(control){control.disabled=busy || !allowed;});
  }
  function element(tag,text,className) { var value=document.createElement(tag); if(text!==undefined) value.textContent=text; if(className) value.className=className; return value; }
  function button(text,callback) { var value=element('button',text,'team-button');value.type='button';value.addEventListener('click',callback);return value; }
  function showInvitation(result) {
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
  function render() {
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
        actions.appendChild(button('Guardar rol',function() {run(async function() {var result=await Api.team.role(member.id,select.value);if(!result || result.role!==select.value)throw new Error('No se confirmó el cambio de rol. Consulta el equipo.');message('Rol actualizado. Las sesiones anteriores de esa persona se invalidaron.');});}));
      }
      if (member.can_resend===true && has('invite:team')) actions.appendChild(button('Crear enlace nuevo',function() {run(async function() {showInvitation(await Api.team.resend(member.id));message('Se creó un enlace nuevo. El anterior dejó de funcionar.');});}));
      if (member.can_remove===true && has('remove:team') && state.capabilities.revoke_preserves_identity===true) actions.appendChild(button('Retirar acceso',function() {
        if(!confirm('¿Retirar el acceso profesional de '+member.nombre+'? Su cuenta y sus datos personales se conservarán.'))return;
        run(async function() {var result=await Api.team.remove(member.id);if(!result || result.success!==true || result.status!=='revoked')throw new Error('No se confirmó la revocación. Consulta el equipo.');document.getElementById('team-share').hidden=true;document.getElementById('team-share-link').value='';message('Acceso al equipo revocado. La cuenta y los datos personales se conservaron.');});
      }));
      if(actions.children.length)card.appendChild(actions);list.appendChild(card);
    });
  }
  async function load() {
    state=null;document.getElementById('team-management').hidden=true;document.getElementById('team-loading').hidden=false;document.getElementById('team-loading').textContent='Consultando el equipo…';
    var value=await Api.team.list();
    if(!value || !Array.isArray(value.members) || !Array.isArray(value.assignable_roles) || !value.assignable_roles.every(function(role){return ['admin','nutriologo','viewer'].includes(role);}) || !value.capabilities || typeof value.capabilities.invite!=='boolean' || (value.invitation_requirement!=null && typeof value.invitation_requirement!=='string') || !Number.isInteger(value.total) || !Number.isInteger(value.pending_invitations) || !value.members.every(function(member){return member && typeof member.id==='string' && typeof member.email==='string' && Object.prototype.hasOwnProperty.call(labels,member.role);}))throw new Error('El servidor devolvió un equipo incompleto. Vuelve a consultar.');
    state=value;render();document.getElementById('team-management').hidden=false;document.getElementById('team-loading').hidden=true;
  }
  async function run(action) {
    if(busy || !actor)return;setBusy(true);
    try{await action();await load();}catch(error){message(failure(error));if(!state)document.getElementById('team-loading').textContent='No se pudo consultar el equipo. Usa Consultar equipo para reintentar.';}
    finally{setBusy(false);}
  }
  (async function() {
    try {
      actor=window.SessionIdentity ? await SessionIdentity.ready : await Api.auth.me();
      if(document.getElementById('professional-context')) {
        if(!actor || !actor.team_gym_id) return;
        document.getElementById('professional-context').textContent='Equipo del gimnasio · '+(actor.role_display || labels[actor.role] || 'Rol por confirmar');return;
      }
      if(!actor || !has('read:team')) {document.getElementById('team-loading').textContent='Tu rol no permite administrar el equipo. Usa las secciones disponibles en el menú.';document.getElementById('team-refresh').disabled=true;return;}
      document.getElementById('team-refresh').addEventListener('click',function(){run(async function(){feedback.hidden=true;});});
      document.getElementById('team-invite-form').addEventListener('submit',function(event){event.preventDefault();if(!state || state.capabilities.invite!==true || !has('invite:team'))return;run(async function(){var form=event.target;showInvitation(await Api.team.invite({nombre:form.elements.namedItem('nombre').value.trim(),apellido:form.elements.namedItem('apellido').value.trim(),email:form.elements.namedItem('email').value.trim(),role:form.elements.namedItem('role').value}));form.reset();message('Invitación creada. Revisa el enlace y el estado del correo.');});});
      document.getElementById('team-copy-link').addEventListener('click',async function(){try{await navigator.clipboard.writeText(document.getElementById('team-share-link').value);message('Enlace copiado. Compártelo sólo con la persona invitada.');}catch(_){message('No se pudo copiar automáticamente. Selecciona el enlace para copiarlo.');document.getElementById('team-share-link').select();}});
      await run(async function(){});
    }catch(error){if(feedback)message(failure(error));}
  })();
})();
