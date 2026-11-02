/* Public navigation intent only. Prices, permissions and payment stay on the server. */
(function () {
  'use strict';
  var parameter = 'subscription_plan';
  var plans = Object.freeze({standard:'Standard',gym_comercial:'Gym Comercial',clinica:'Clínica',pro:'Pro'});
  var values = new URLSearchParams(location.search).getAll(parameter);
  var selected = values.length === 1 && Object.prototype.hasOwnProperty.call(plans, values[0]) ? values[0] : null;
  function forAudience(audience) {
    return selected && (audience === 'gym' ? selected !== 'pro' : audience === 'usuario' && selected === 'pro') ? selected : null;
  }
  function href(path, audience) {
    var url = new URL(path, location.origin), choice = forAudience(audience);
    // Callers supply local paths. Never turn untrusted query values into a destination.
    if (url.origin !== location.origin) return '/';
    if (choice) url.searchParams.set(parameter, choice);
    else url.searchParams.delete(parameter);
    return url.pathname + url.search + url.hash;
  }
  function destination(me) {
    if (!me || !['gym','usuario'].includes(me.tipo)) return null;
    // Team membership keeps a separate personal subscription, even for a
    // legacy identity whose primary account type is gym.
    if (selected === 'pro' && (me.tipo === 'usuario' || me.team_gym_id)) return href('/mi-suscripcion', 'usuario');
    if (me.team_gym_id || !forAudience(me.tipo)) return null;
    return href(me.tipo === 'gym' ? '/suscripciones' : '/mi-suscripcion', me.tipo);
  }
  function decorate(audience) {
    document.querySelectorAll('a[href]').forEach(function (link) {
      var url = new URL(link.href, location.origin);
      if (url.origin !== location.origin) return;
      var target = url.pathname === '/login-gym' || url.pathname === '/suscripciones' || url.pathname === '/configuracion' || url.pathname === '/cuenta/seguridad' ? 'gym' :
        url.pathname === '/login-usuario' || url.pathname === '/mi-suscripcion' || url.pathname === '/mi-seguridad' ? 'usuario' :
        url.pathname === '/registro' ? url.searchParams.get('tipo') : null;
      if (target) link.href = href(url.pathname + url.search + url.hash, target);
    });
    var choice = forAudience(audience), note = document.getElementById('subscription-choice-note');
    if (!note) return;
    note.hidden = !choice;
    note.textContent = choice ? 'Suscripción elegida: ' + plans[choice] + '. Podrás revisar el precio y los requisitos en tu cuenta antes de pagar.' : '';
  }
  function choose(plan, audience) {
    if (!Object.prototype.hasOwnProperty.call(plans, plan) || (audience === 'gym' ? plan === 'pro' : audience !== 'usuario' || plan !== 'pro')) return;
    selected = plan;
    history.replaceState({}, '', href(location.pathname + location.search + location.hash, audience));
    decorate(audience);
  }
  window.SubscriptionChoice = Object.freeze({forAudience:forAudience,href:href,destination:destination,decorate:decorate,choose:choose});
  decorate(location.pathname.startsWith('/mi-') || location.pathname === '/login-usuario' ? 'usuario' : location.pathname === '/registro' ? document.getElementById('campoTipo')?.value : 'gym');
})();
