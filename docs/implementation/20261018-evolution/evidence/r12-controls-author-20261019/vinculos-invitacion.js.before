(() => {
  'use strict';
  let captured = window.takeClientLinkInvitation?.();
  let token = captured?.token || null, info = null, scope = null, starting = false;
  captured = null;
  const inspect = document.getElementById('invitation-inspect'), accept = document.getElementById('invitation-accept');
  const details = document.getElementById('invitation-details'), panel = document.getElementById('invitation-context');
  const opened = document.getElementById('invitation-open-links');
  const ui = VinculosUI.setup({status:'invitation-status',error:'invitation-error',clear:() => {
    token = null; info = null; scope = null; details.replaceChildren(); panel.hidden = true; accept.hidden = true; opened.hidden = true;
  }});
  if (!token) {
    inspect.hidden = true;
    document.getElementById('invitation-status').textContent = 'Vuelve a abrir el enlace original del correo. No se pudo recuperar una invitación válida desde esta página.';
    return;
  }
  // No automatic inspect or acceptance on loading, logging in or creating an account.
  inspect.addEventListener('click', async () => {
    if (ui.busy || starting) return;
    starting = true; inspect.disabled = true;
    try { if (!ui.context.active) await ui.context.start(); ui.context.check(); inspect.disabled = false; }
    catch { token=null;inspect.disabled=true;return; }
    finally { starting = false; }
    await ui.run(async () => {
      scope?.invalidate(); info = null; accept.hidden = true; details.replaceChildren(); panel.hidden = true;
      scope = ui.context.scope(() => { info = null; details.replaceChildren(); panel.hidden = true; accept.hidden = true; });
      ui.status('Verificando invitación con tu cuenta…');
      const data = await scope.read(context => Api.vinculos.inspeccionar(token,context));
      scope.check();
      if (!data || !VinculosUI.uuid(data.link_id) || !VinculosUI.version(data.version) || data.context?.kind !== 'gym_member' || typeof data.context.gym_name !== 'string' || typeof data.context.client_display_name !== 'string' || typeof data.can_accept !== 'boolean') throw new Error('Invalid invitation result');
      scope.render(() => {
        info = data; const {node,date} = VinculosUI;
        node('dt','Gimnasio',details);node('dd',data.context.gym_name,details);
        node('dt','Destinatario',details);node('dd',data.context.client_display_name,details);
        node('dt','Vigencia del enlace',details);node('dd',date(data.expires_at),details);
        panel.hidden = false; accept.hidden = !data.can_accept || data.status !== 'pending';
        ui.status(data.can_accept && data.status === 'pending' ? 'Invitación verificada. Revisa el contexto y confirma si deseas vincular esta cuenta.' : 'La invitación no está disponible para una aceptación nueva. Consulta tus vínculos.');
        opened.hidden = data.status !== 'consumed';
      });
    });
  });
  accept.addEventListener('click', () => ui.run(async () => {
    scope?.check(); if (!scope || !info || !info.can_accept || info.status !== 'pending' || !token) return;
    const expected = info;
    // Remove this confirmation immediately; a lost ACK must be reconciled, not auto-consumed again.
    accept.hidden = true; info = null;
    ui.status('Confirmando el vínculo…');
    const data = await scope.read(context => Api.vinculos.aceptar(token,expected.version,context));
    scope.check();
    if (!data || data.status !== 'active' || data.link_id !== expected.link_id || !VinculosUI.version(data.version)) throw new Error('Invalid acceptance result');
    scope.render(() => { token = null; opened.hidden = false; inspect.hidden = true; ui.status('Vínculo aceptado. Tu cuenta y perfil personal se conservan. Puedes consultar los planes que te publique el profesional.'); });
  },true));
})();
