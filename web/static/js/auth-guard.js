/* Resolve cookie bootstrap before identity, permissions or navigation. */
(function () {
  'use strict';
  var path = location.pathname;
  var personalRoutine = path === '/mis-rutinas' || path === '/mis-rutinas/';
  var publicPages = ['/', '/login-gym', '/login-usuario', '/registro', '/auth/accept-invite'];
  if (publicPages.includes(path)) return;
  var current = null;
  var ready = new Promise(function(resolve) {
    async function resolveIdentity() {
      try {
        await Api.session.ready;
        if (!Api.getToken()) { location.replace(path.startsWith('/mi-') || personalRoutine ? '/login-usuario' : '/login-gym'); resolve(null); return; }
        var context=Api.session.capture();
        var me = await Api.auth.me();
        Api.session.check(context);
        if (!me || typeof me.tipo !== 'string' || typeof me.role !== 'string') throw new Error('No se pudo confirmar el acceso de tu cuenta.');
        current = me;
        var professional = !!me.team_gym_id && ['admin','nutriologo','viewer'].includes(me.role);
        var owner = !me.team_gym_id && me.tipo === 'gym' && me.role === 'owner';
        var personal = !me.team_gym_id && me.tipo === 'usuario';
        var gymPage = ['/dashboard','/clientes','/planes','/suscripciones','/configuracion','/generar-plan','/equipo','/equipo/inicio','/rutinas','/rutinas/'].includes(path);
        var personalPage = ['/mi-plan','/mi-perfil','/mi-historial','/mi-suscripcion','/mis-rutinas','/mis-rutinas/'].includes(path);
        if (professional && path === '/dashboard') { location.replace('/equipo/inicio'); resolve(me); return; }
        if (personal && gymPage) { location.replace('/mi-plan'); resolve(me); return; }
        if (owner && personalPage) { location.replace('/dashboard'); resolve(me); return; }
        if (owner && path === '/equipo/inicio') { location.replace('/dashboard'); resolve(me); return; }
        if (!professional && !owner && !personal) throw new Error('No se pudo confirmar el contexto de tu cuenta. Vuelve a iniciar sesión.');
        if (professional) {
          document.querySelectorAll('a[href="/dashboard"]').forEach(function(link) { link.href='/equipo/inicio'; });
          var role = document.getElementById('sb-tipo');
          if (role) role.textContent = personalPage ? 'Perfil personal' : 'Equipo · ' + (me.role_display || 'Acceso profesional');
        }
        document.querySelectorAll('[data-professional-context]').forEach(function(link) { link.hidden=!professional; });
        document.querySelectorAll('[data-personal-context]').forEach(function(link) { link.hidden=!professional; });
        applyPermissions(document);
        new MutationObserver(function(records) {
          records.forEach(function(record) { record.addedNodes.forEach(function(node) { if (node.nodeType === 1) applyPermissions(node); }); });
        }).observe(document.body,{childList:true,subtree:true});
        if (typeof setActiveSidebarLink === 'function') setActiveSidebarLink();
        resolve(me);
      } catch(error) {
        current = null; applyPermissions(document);
        var notice = document.createElement('div');
        notice.className = 'chart-container'; notice.setAttribute('role','alert');
        var text = document.createElement('p'); text.textContent = 'No pudimos verificar tu acceso. ' + error.message;
        var retry = document.createElement('button'); retry.type='button'; retry.className='btn btn-outline'; retry.textContent='Volver a consultar';
        retry.addEventListener('click',function() { location.reload(); });
        notice.append(text,retry);
        var main=document.querySelector('main'); if (main) main.prepend(notice);
        resolve(null);
      }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',resolveIdentity,{once:true});
    else resolveIdentity();
  });
  function can(permission) {
    return !!current && Array.isArray(current.permissions) && current.permissions.some(function(value) { return Array.isArray(value) && value[0]+':'+value[1] === permission; });
  }
  function applyPermissions(root) {
    var controls = root.matches && root.matches('[data-permission]') ? [root] : [];
    if (root.querySelectorAll) controls = controls.concat(Array.from(root.querySelectorAll('[data-permission]')));
    controls.forEach(function(control) { var hide=!can(control.dataset.permission); if (control.hidden !== hide) control.hidden=hide; });
  }
  window.SessionIdentity = {ready:ready, can:can};
  window.addEventListener('metodobase-session-changed',function(){current=null;applyPermissions(document);});
})();
