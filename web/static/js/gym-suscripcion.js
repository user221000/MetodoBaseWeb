/* Provider returns never grant access. Authenticated APIs confirm account state. */
(function () {
  'use strict';
  if (localStorage.getItem('mb_tipo') === 'usuario') { location.replace('/mi-suscripcion'); return; }
  var config = null, subscription = null, owner = false, busy = false, loading = false, keys = {};
  var feedback = document.getElementById('billing-feedback');
  var names = { free: 'Free', standard: 'Standard', gym_comercial: 'Gym Comercial', clinica: 'Clínica' };
  var statuses = { active: 'Activo', trialing: 'Prueba', past_due: 'Pago atrasado', canceled: 'Cancelada', incomplete: 'Pago pendiente', incomplete_expired: 'Pago vencido', unpaid: 'Sin pago vigente', paused: 'Pausada', none: 'Sin suscripción de pago' };
  var returned = new URLSearchParams(location.search);
  function notify(message) { feedback.textContent = message; feedback.hidden = false; }
  function failure(error) { return (error.message || 'No pudimos completar la solicitud. Intenta de nuevo.') + (error.requestId ? ' Referencia: ' + error.requestId : ''); }
  function date(value) { if (!value) return 'Sin fecha confirmada'; var d = new Date(typeof value === 'number' ? value * 1000 : value); return Number.isNaN(d.getTime()) ? 'Sin fecha confirmada' : d.toLocaleDateString('es-MX'); }
  function provider() { var selected = document.querySelector('[name="billing-provider"]:checked'); return selected ? selected.value : null; }
  function configured(name) { return ['stripe','mercadopago'].includes(name) && !!config && config[name === 'stripe' ? 'stripe_configured' : 'mercadopago_configured'] === true; }
  function render() {
    var known = !!subscription, existingProvider = known && subscription.provider;
    document.getElementById('sub-plan-name').textContent = !known ? 'Por confirmar' : subscription.status === 'none' ? 'Sin suscripción de pago' : names[subscription.plan];
    document.getElementById('sub-status-badge').textContent = known ? statuses[subscription.status] : 'Por confirmar';
    document.getElementById('sub-renewal').textContent = known ? date(subscription.current_period_end) : '—';
    document.getElementById('sub-provider').textContent = existingProvider === 'stripe' ? 'Stripe' : existingProvider === 'mercadopago' ? 'Mercado Pago' : known && subscription.status === 'none' ? 'Sin pago' : 'Por confirmar';
    var max = known ? subscription.max_clientes : undefined;
    document.getElementById('sub-max-clientes').textContent = !Number.isInteger(max) || max < 0 ? 'Por confirmar' : max === 0 ? 'Sin límite del plan' : String(max);
    var info = config && subscription && config.plans[subscription.plan];
    document.getElementById('sub-precio').textContent = info && Number.isFinite(info.precio_mxn) ? '$' + info.precio_mxn + ' MXN' : known && subscription.status === 'none' ? 'Sin cargo' : 'Por confirmar';
    document.getElementById('sub-renewal-note').textContent = !known ? 'Consulta el estado antes de iniciar otro pago.' : existingProvider === 'mercadopago' ? 'Mercado Pago: pago único, sin renovación automática.' : subscription.cancel_at_period_end ? 'Cancelación programada. Consulta la vigencia confirmada.' : existingProvider === 'stripe' ? 'La renovación y la cancelación se gestionan en Stripe. Consulta de nuevo tras su confirmación.' : 'No hay una renovación automática confirmada para mostrar.';
    document.getElementById('btn-portal').hidden = !known || !owner || existingProvider !== 'stripe';
    document.getElementById('btn-portal').disabled = busy || loading;
    document.getElementById('btn-refresh-billing').disabled = !owner || busy || loading;
    document.getElementById('billing-methods').disabled = !owner || !known || busy || loading || existingProvider === 'stripe';
    document.querySelectorAll('[name="billing-provider"]').forEach(function(input) { input.disabled = !configured(input.value); });
    document.getElementById('billing-method-description').textContent = existingProvider === 'stripe' ? 'Ya tienes una suscripción con Stripe. Usa el portal para cambiarla o cancelarla.' : !config ? 'No se pudo confirmar la disponibilidad de pagos. Consulta de nuevo.' : !provider() ? 'No hay un proveedor de pago disponible en este momento.' : provider() === 'stripe' ? 'Stripe: suscripción mensual con renovación automática. Revisa las condiciones antes de confirmar en el proveedor.' : 'Mercado Pago: pago único por un mes, sin renovación automática. Revisa las condiciones antes de confirmar en el proveedor.';
    document.querySelectorAll('.btn-plan').forEach(function(button) {
      var current = known && subscription.plan === button.dataset.plan && ['active','trialing'].includes(subscription.status);
      var portalAvailable = existingProvider === 'stripe';
      button.disabled = !known || !owner || busy || loading || current || (!portalAvailable && !configured(provider()));
      button.textContent = current ? 'Plan actual' : portalAvailable ? 'Gestionar en Stripe' : 'Elegir ' + names[button.dataset.plan];
      document.getElementById('plan-' + button.dataset.plan).classList.toggle('current-plan', current);
    });
  }
  async function load() {
    if (!owner || busy || loading) return;
    loading = true; subscription = null; config = null; feedback.hidden = true; render();
    try {
      var result = await Promise.all([Api.billing.subscription(), Api.billing.config()]);
      var value = result[0], options = result[1];
      if (!value || !Object.prototype.hasOwnProperty.call(statuses, value.status) || (value.status === 'none' ? value.plan !== null : !Object.prototype.hasOwnProperty.call(names, value.plan))) throw new Error('El servidor devolvió un estado de suscripción incompleto. Intenta consultar de nuevo.');
      if (value.status !== 'none' && value.plan !== 'free' && !['stripe','mercadopago'].includes(value.provider)) throw new Error('El servidor no confirmó el proveedor de la suscripción. Intenta consultar de nuevo.');
      if (!options || typeof options.stripe_configured !== 'boolean' || typeof options.mercadopago_configured !== 'boolean' || !options.plans || typeof options.plans !== 'object') throw new Error('El servidor devolvió una disponibilidad de pagos incompleta. Intenta consultar de nuevo.');
      subscription = value; config = options;
      var selected = provider();
      if (!configured(selected)) selected = configured('stripe') ? 'stripe' : configured('mercadopago') ? 'mercadopago' : null;
      document.querySelectorAll('[name="billing-provider"]').forEach(function(input) { input.checked = input.value === selected; });
      if (returned.get('result') === 'success' || returned.get('subscription') === 'success' || returned.get('redirect_status') === 'succeeded') {
        notify(subscription.status === 'active' ? 'El panel muestra el estado confirmado de tu cuenta. El regreso del proveedor no confirma por sí solo un cambio de plan.' : 'El pago aún no aparece confirmado. Consulta de nuevo antes de iniciar otro pago.');
      } else if (returned.get('result') === 'canceled' || returned.get('subscription') === 'canceled') notify('Volviste del proveedor sin una confirmación de pago. Revisa el estado de tu cuenta.');
    } catch(error) { subscription = null; config = null; notify('No pudimos consultar tu suscripción y los medios de pago. ' + failure(error)); }
    finally { loading = false; render(); }
  }
  function redirect(value, name, portal) {
    var url;
    try { url = new URL(value); } catch (_) { throw new Error('El proveedor no devolvió una dirección válida. Consulta tu estado.'); }
    var hosts = name === 'mercadopago' ? ['www.mercadopago.com.mx','www.mercadopago.com','sandbox.mercadopago.com.mx','sandbox.mercadopago.com'] : [portal ? 'billing.stripe.com' : 'checkout.stripe.com'];
    if (url.protocol !== 'https:' || url.username || url.password || !hosts.includes(url.hostname)) throw new Error('No pudimos abrir el proveedor de pago. Consulta tu estado antes de intentar de nuevo.');
    location.assign(url.href);
  }
  async function portal() {
    if (busy || loading || !owner || !subscription || subscription.provider !== 'stripe') return;
    busy = true; render();
    try { redirect((await Api.billing.portal()).url, 'stripe', true); }
    catch(error) { notify(failure(error)); }
    finally { busy = false; render(); }
  }
  document.getElementById('btn-refresh-billing').addEventListener('click', function() { load(); payments(); });
  document.getElementById('btn-portal').addEventListener('click', portal);
  document.querySelectorAll('[name="billing-provider"]').forEach(function(input) { input.addEventListener('change', render); });
  document.querySelectorAll('.btn-plan').forEach(function(button) {
    button.addEventListener('click', async function() {
      if (busy || loading || !owner || !subscription) return;
      if (subscription.provider === 'stripe') return portal();
      var plan = button.dataset.plan, name = provider();
      if (!configured(name)) return;
      var intent = name + ':' + plan;
      if (!keys[intent]) keys[intent] = 'purchase-' + crypto.randomUUID();
      busy = true; render(); button.textContent = 'Abriendo proveedor…';
      try {
        var result = name === 'stripe' ? await Api.billing.checkout(plan, keys[intent]) : await Api.billing.mpPreference(plan, keys[intent]);
        redirect(name === 'stripe' ? result.url : result.redirect_url, name, false);
      } catch(error) { notify(failure(error)); feedback.scrollIntoView({block:'nearest'}); }
      finally { busy = false; render(); }
    });
  });
  async function payments() {
    if (!owner) return;
    var state = document.getElementById('payments-state'), body = document.getElementById('payments-tbody');
    body.replaceChildren(); state.textContent = 'Consultando pagos…';
    try {
      var response = await Api.billing.payments();
      if (!response || !Array.isArray(response.payments)) throw new Error('El servidor devolvió un historial de pagos incompleto.');
      var rows = response.payments;
      state.textContent = rows.length ? rows.length + ' pagos registrados.' : 'No hay pagos registrados en tu cuenta.';
      rows.forEach(function(payment) {
        var row = document.createElement('tr'), amount = 'Por confirmar';
        if (Number.isInteger(payment.amount_cents) && /^[A-Za-z]{3}$/.test(payment.currency || '')) {
          try { amount = new Intl.NumberFormat('es-MX',{style:'currency',currency:payment.currency.toUpperCase()}).format(payment.amount_cents/100); } catch (_) {}
        }
        [date(payment.created_at), amount, payment.status || 'Por confirmar', names[payment.plan] || 'Plan por confirmar'].forEach(function(text) { var cell = document.createElement('td'); cell.textContent = text; row.appendChild(cell); });
        body.appendChild(row);
      });
    } catch(error) { body.replaceChildren(); state.textContent = 'No pudimos consultar los pagos. ' + failure(error); }
  }
  (async function() {
    render();
    try {
      var me = await Api.auth.me();
      owner = String(me.role || '').toLowerCase() === 'owner';
      if (!owner) { notify('La facturación sólo está disponible para la persona propietaria del gimnasio.'); document.getElementById('payments-state').textContent = 'No tienes permiso para consultar pagos.'; render(); return; }
      await Promise.all([load(),payments()]);
    } catch(error) { notify('No pudimos consultar tu cuenta. ' + failure(error)); render(); }
  })();
  if (location.search) history.replaceState({}, '', '/suscripciones');
})();
