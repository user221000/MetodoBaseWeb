/* Read-only payment facts. Unknown historical refunds remain unknown. */
(function () {
  'use strict';
  var statuses = {
    succeeded: 'Pagado', paid: 'Pagado', pending: 'Pendiente', processing: 'En proceso',
    failed: 'Pago fallido', canceled: 'Cancelado', cancelled: 'Cancelado',
    partially_refunded: 'Devolución parcial', refunded: 'Devolución completa'
  };
  function cents(value) { return Number.isSafeInteger(value) && value >= 0; }
  function money(value, currency) {
    if (!cents(value) || typeof currency !== 'string' || !/^[A-Za-z]{3}$/.test(currency)) return 'Sin dato confirmado';
    try { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: currency.toUpperCase() }).format(value / 100); }
    catch (_) { return 'Sin dato confirmado'; }
  }
  function date(value) {
    if (typeof value !== 'string' || !value) return 'Sin fecha confirmada';
    var parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? 'Sin fecha confirmada' : parsed.toLocaleDateString('es-MX');
  }
  function cell(row, label, value) {
    var element = document.createElement('td');
    element.dataset.label = label;
    if (typeof value === 'string') element.textContent = value;
    else element.appendChild(value);
    row.appendChild(element);
  }
  function amounts(payment) {
    var facts = cents(payment.amount_cents) && cents(payment.refund_amount_cents) &&
      payment.refund_amount_cents <= payment.amount_cents && cents(payment.net_amount_cents) &&
      payment.net_amount_cents === payment.amount_cents - payment.refund_amount_cents;
    var summary = document.createElement('dl');
    summary.className = 'billing-payment-amounts';
    [
      ['Original', payment.amount_cents],
      ['Devuelto', facts ? payment.refund_amount_cents : null],
      ['Importe tras devolución', facts ? payment.net_amount_cents : null]
    ].forEach(function (item) {
      var pair = document.createElement('div'), label = document.createElement('dt'), value = document.createElement('dd');
      label.textContent = item[0];
      value.className = 'billing-payment-value';
      value.textContent = money(item[1], payment.currency);
      pair.append(label, value); summary.appendChild(pair);
    });
    return summary;
  }
  function render(body, rows, names) {
    if (!Array.isArray(rows) || rows.some(function (row) { return !row || typeof row !== 'object' || Array.isArray(row); })) {
      throw new Error('El servidor devolvió un historial de pagos incompleto.');
    }
    var fragment = document.createDocumentFragment();
    rows.forEach(function (payment) {
      var row = document.createElement('tr'), state = document.createElement('div');
      var label = Object.prototype.hasOwnProperty.call(statuses, payment.status) ? statuses[payment.status] : 'Estado por confirmar';
      state.textContent = label;
      if (cents(payment.refund_amount_cents) && payment.refund_amount_cents > 0 &&
          date(payment.refund_observed_at) !== 'Sin fecha confirmada') {
        var observed = document.createElement('small');
        observed.className = 'billing-refund-observed';
        observed.textContent = 'Devolución registrada el ' + date(payment.refund_observed_at);
        state.appendChild(observed);
      }
      cell(row, 'Fecha del pago', date(payment.created_at));
      cell(row, 'Importes', amounts(payment));
      cell(row, 'Estado', state);
      cell(row, 'Plan', Object.prototype.hasOwnProperty.call(names, payment.plan) ? names[payment.plan] : 'Plan por confirmar');
      fragment.appendChild(row);
    });
    body.replaceChildren(fragment);
  }
  window.PaymentHistory = Object.freeze({ render: render });
})();
