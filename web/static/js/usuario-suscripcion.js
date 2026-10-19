/* The server owns paid access. A return URL only requests a fresh status. */
(function () {
  'use strict';
  var subscription = null;
  var billing = null;
  var selectedMethod = null;
  var busy = false;
  var lastFocus = null;
  var purchaseKeys = {};
  var modal = document.getElementById('modal-pago');
  var feedback = document.getElementById('subscription-feedback');
  var params = new URLSearchParams(window.location.search);
  var returnedFromPayment = params.get('result') === 'success' || params.get('subscription') === 'success' || params.get('redirect_status') === 'succeeded';
  var canceledReturn = params.get('result') === 'canceled' || params.get('subscription') === 'canceled';

  function notify(message, error) {
    feedback.hidden = false;
    feedback.classList.toggle('u-inline-error', !!error);
    feedback.textContent = message;
  }

  function failureMessage(error) {
    var message = error.message || 'No pudimos completar la solicitud. Intenta de nuevo.';
    return error.requestId ? message + ' Referencia: ' + error.requestId : message;
  }

  function formatDate(value) {
    if (!value) return 'Sin fecha confirmada';
    var date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'Sin fecha confirmada' : date.toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function canManage() { return subscription && subscription.provider === 'stripe'; }

  function validateSubscription(value) {
    if (!value || !['starter', 'pro'].includes(value.plan) || typeof value.status !== 'string' ||
        !Number.isInteger(value.planes_usados) || value.planes_usados < 0 ||
        !Number.isInteger(value.max_planes) || value.max_planes < 1) {
      throw new Error('El servidor devolvió un estado de suscripción incompleto. Intenta consultar de nuevo.');
    }
    return value;
  }

  function render() {
    var known = !!subscription;
    var paid = known && subscription.plan === 'pro' && subscription.status === 'active';
    var statusNames = { active: paid ? 'Activo' : 'Gratis', canceled: 'Cancelada', past_due: 'Pago atrasado', unpaid: 'Sin pago vigente', incomplete: 'Pago pendiente', incomplete_expired: 'Pago vencido', paused: 'Pausada', trialing: 'Prueba' };
    document.getElementById('sub-plan-name').textContent = known ? (subscription.plan === 'pro' ? 'Pro' : 'Starter') : 'Por confirmar';
    document.getElementById('sub-planes-uso').textContent = known ? subscription.planes_usados + ' / ' + subscription.max_planes : '—';
    document.getElementById('sub-renewal').textContent = known ? (subscription.period_end ? formatDate(subscription.period_end) : subscription.renovacion) : '—';
    var badge = document.getElementById('sub-status-badge');
    badge.textContent = known ? (statusNames[subscription.status] || 'Estado por confirmar') : 'Consultando';
    badge.className = 'u-badge' + (known && subscription.status === 'active' ? ' u-badge-green' : '');
    document.getElementById('card-starter').classList.toggle('u-plan-active', known && subscription.plan === 'starter' && subscription.status === 'active');
    document.getElementById('card-pro').classList.toggle('u-plan-active', !!paid);
    var pro = document.getElementById('btn-pro');
    pro.disabled = !known || !billing || busy || !!paid || (!canManage() && !billing.checkout_supported && !billing.mercadopago_configured);
    pro.textContent = paid ? 'Plan actual' : canManage() ? 'Gestionar pago' : 'Elegir Pro';
    document.getElementById('btn-starter').textContent = known && subscription.plan === 'starter' ? 'Plan actual' : known ? 'Plan gratuito' : 'Consultando';
    var manage = document.getElementById('btn-manage-subscription');
    manage.hidden = !canManage();
    manage.disabled = busy || !known;
    var terms = document.getElementById('subscription-terms');
    if (!known) terms.textContent = 'Consulta el estado de tu cuenta antes de iniciar otro pago.';
    else if (subscription.provider === 'mercadopago') terms.textContent = 'Mercado Pago: pago único. Este pago no genera renovación automática. ' + (paid ? 'Acceso hasta ' + formatDate(subscription.period_end) + '.' : 'Consulta la vigencia y el estado confirmado de tu pago.');
    else if (subscription.cancel_at_period_end) terms.textContent = 'Cancelación programada. Acceso vigente hasta ' + formatDate(subscription.period_end) + '.';
    else if (subscription.provider === 'stripe') terms.textContent = 'Stripe: gestiona pagos y cancelación en el portal del proveedor. El estado se actualizará después de su confirmación.';
    else terms.textContent = 'Starter no tiene cargo. Los límites mensuales se muestran según el estado de tu cuenta.';
    document.getElementById('pm-card').disabled = busy || !billing || !billing.checkout_supported;
    document.getElementById('pm-mercadopago').disabled = busy || !billing || !billing.mercadopago_configured;
    document.getElementById('pago-modal-close').disabled = busy;
    document.getElementById('pago-btn-cancel').disabled = busy;
    modal.setAttribute('aria-busy', String(busy));
  }

  async function loadSubscription() {
    document.getElementById('btn-refresh-subscription').disabled = true;
    try {
      subscription = validateSubscription(await Api.usuario.suscripcion());
      render();
      if (returnedFromPayment) notify(subscription.plan === 'pro' && subscription.status === 'active' ? 'Tu plan Pro está activo según el estado de tu cuenta.' : 'Tu pago aún no aparece confirmado. Puedes volver a consultar el estado en unos momentos.');
      else if (canceledReturn) notify('Volviste del proveedor sin una confirmación de pago. El panel muestra el estado actual de tu cuenta.');
      else { feedback.hidden = true; }
    } catch (error) {
      notify('No pudimos consultar tu suscripción. ' + failureMessage(error), true);
      render();
    } finally { document.getElementById('btn-refresh-subscription').disabled = false; }
  }

  function closeModal() {
    if (busy) return;
    modal.classList.add('hidden');
    modal.hidden = true;
    setBackgroundInert(false);
    if (lastFocus && lastFocus.isConnected) lastFocus.focus();
  }

  function openModal() {
    if (!subscription || !billing) return;
    lastFocus = document.activeElement;
    selectedMethod = null;
    document.querySelectorAll('.u-pm-btn').forEach(function (button) { button.setAttribute('aria-pressed', 'false'); button.classList.remove('selected'); });
    document.getElementById('pago-btn-confirm').disabled = true;
    document.getElementById('payment-method-description').textContent = 'Elige un proveedor. No se activará Pro hasta confirmar el pago.';
    modal.hidden = false;
    modal.classList.remove('hidden');
    setBackgroundInert(true);
    document.getElementById('pago-modal-close').focus();
  }

  function redirectToProvider(value, portal) {
    var url;
    try { url = new URL(value); }
    catch (_) { throw new Error('El proveedor no devolvió una dirección válida. Consulta tu estado antes de intentar de nuevo.'); }
    var allowed = portal ? ['billing.stripe.com'] : ['checkout.stripe.com', 'www.mercadopago.com.mx', 'mercadopago.com.mx', 'sandbox.mercadopago.com.mx'];
    if (url.protocol !== 'https:' || allowed.indexOf(url.hostname) === -1) throw new Error('No pudimos abrir el proveedor de pago. Vuelve a consultar tu estado.');
    window.location.assign(url.href);
  }

  function setBackgroundInert(value) {
    document.querySelectorAll('.u-main > :not(#modal-pago), .u-sidebar, #btn-hamburger').forEach(function (element) { element.inert = value; });
    document.body.classList.toggle('u-dialog-open', value);
  }

  async function openPortal() {
    if (busy || !canManage()) return;
    busy = true;
    render();
    try { redirectToProvider((await Api.usuario.portal()).url, true); }
    catch (error) { notify(failureMessage(error), true); }
    finally { busy = false; render(); }
  }

  function purchaseKey(method) {
    if (!purchaseKeys[method]) purchaseKeys[method] = 'purchase-' + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2));
    return purchaseKeys[method];
  }

  document.getElementById('btn-pro').addEventListener('click', function () { if (canManage()) openPortal(); else openModal(); });
  document.getElementById('btn-manage-subscription').addEventListener('click', openPortal);
  document.getElementById('btn-refresh-subscription').addEventListener('click', loadSubscription);
  document.getElementById('pago-modal-close').addEventListener('click', closeModal);
  document.getElementById('pago-btn-cancel').addEventListener('click', closeModal);
  modal.addEventListener('click', function (event) { if (event.target === modal) closeModal(); });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !modal.hidden) { event.preventDefault(); closeModal(); }
  });
  modal.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { event.preventDefault(); closeModal(); }
    if (event.key !== 'Tab') return;
    var focusable = Array.from(modal.querySelectorAll('button:not([disabled]), a[href], [tabindex="0"]')).filter(function (element) { return element.offsetParent !== null; });
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  document.querySelectorAll('.u-pm-btn').forEach(function (button) {
    button.addEventListener('click', function () {
      selectedMethod = button.dataset.method;
      document.querySelectorAll('.u-pm-btn').forEach(function (item) { item.setAttribute('aria-pressed', String(item === button)); item.classList.toggle('selected', item === button); });
      document.getElementById('pago-btn-confirm').disabled = false;
      document.getElementById('payment-method-description').textContent = selectedMethod === 'card' ? 'Stripe: suscripción mensual. Podrás gestionar la renovación desde su portal.' : 'Mercado Pago: pago único por un mes de acceso; sin renovación automática.';
    });
  });
  document.getElementById('pago-btn-confirm').addEventListener('click', async function () {
    if (!selectedMethod || busy) return;
    busy = true;
    render();
    var button = this;
    button.disabled = true;
    button.textContent = 'Abriendo proveedor…';
    try {
      var result = selectedMethod === 'card' ? await Api.usuario.checkout(purchaseKey('card')) : await Api.usuario.mpPreference('pro', purchaseKey('mercadopago'));
      redirectToProvider(result.url || result.redirect_url, false);
    } catch (error) {
      document.getElementById('payment-method-description').textContent = failureMessage(error);
    } finally { busy = false; button.disabled = false; button.textContent = 'Continuar al proveedor'; render(); }
  });

  render();
  Promise.allSettled([loadSubscription(), Api.usuario.billingConfig().then(function (config) {
    billing = config;
    render();
    if (!billing.checkout_supported && !billing.mercadopago_configured) {
      var unavailable = document.getElementById('billing-feedback');
      unavailable.hidden = false;
      unavailable.textContent = 'Los pagos no están disponibles en este momento. Puedes seguir consultando el estado de tu cuenta.';
    }
  }).catch(function (error) {
    var unavailable = document.getElementById('billing-feedback');
    unavailable.hidden = false;
    unavailable.textContent = 'No pudimos consultar los medios de pago. ' + failureMessage(error);
  })]);
  if (returnedFromPayment || params.get('result') === 'canceled' || params.get('subscription') === 'canceled') history.replaceState({}, '', '/mi-suscripcion');
})();
