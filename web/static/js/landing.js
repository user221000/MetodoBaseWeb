/* Public illustrative tour and a dismissible invitation. No account data or API calls. */
(function () {
  'use strict';
  var demo = document.getElementById('landing-demo');
  if (demo) {
    var tabs = Array.from(demo.querySelectorAll('[data-demo-tab]'));
    var panels = Array.from(demo.querySelectorAll('[data-demo-panel]'));
    var steps = Array.from(demo.querySelectorAll('[data-demo-target]'));
    var status = document.getElementById('demo-status');
    var labels = {clientes: 'Clientes', plan: 'Plan nutricional', historial: 'Historial y PDF', rutinas: 'Rutinas'};
    function select(name, focus, announce) {
      if (!Object.prototype.hasOwnProperty.call(labels, name)) return;
      var selected = tabs.find(function (tab) { return tab.dataset.demoTab === name; });
      if (!selected) return;
      tabs.forEach(function (tab) {
        var active = tab === selected;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
      });
      panels.forEach(function (panel) { panel.hidden = panel.dataset.demoPanel !== name; });
      if (focus) selected.focus();
      if (announce && status) status.textContent = 'Mostrando ' + labels[name] + '. Demostración con datos de ejemplo.';
    }
    tabs.forEach(function (tab, index) {
      tab.disabled = false;
      tab.addEventListener('click', function () { select(tab.dataset.demoTab, false, true); });
      tab.addEventListener('keydown', function (event) {
        var next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault();
        select(tabs[next].dataset.demoTab, true, true);
      });
    });
    steps.forEach(function (button) {
      button.disabled = false;
      button.addEventListener('click', function () { select(button.dataset.demoTarget, true, true); });
    });
    select('clientes', false, false);
    demo.dataset.enhanced = 'true';
  }

  var invite = document.getElementById('registration-invite');
  var panel = document.getElementById('registration-invite-panel');
  var toggle = document.getElementById('registration-invite-toggle');
  var close = document.getElementById('registration-invite-close');
  var register = document.getElementById('registration-invite-register');
  if (!invite || !panel || !toggle || !close || !register) return;
  var storageKey = 'mb_landing_registration_dismissed_v1';
  var destinations = {gym: '/registro?tipo=gym', usuario: '/registro?tipo=usuario'};
  var dismissed = false;
  var interacted = false;
  var automatic = null;
  try { dismissed = window.sessionStorage.getItem(storageKey) === '1'; } catch (_) { /* Preference storage is optional. */ }
  function show(open, restoreFocus) {
    panel.hidden = !open;
    toggle.hidden = open;
    toggle.setAttribute('aria-expanded', String(open));
    invite.dataset.open = String(open);
    if (restoreFocus) toggle.focus();
  }
  function dismiss() {
    var restore = panel.contains(document.activeElement);
    interacted = true;
    dismissed = true;
    window.clearTimeout(automatic);
    try { window.sessionStorage.setItem(storageKey, '1'); } catch (_) { /* Browsing remains available with storage disabled. */ }
    show(false, restore);
  }
  invite.hidden = false;
  show(false, false);
  toggle.addEventListener('click', function () {
    interacted = true;
    window.clearTimeout(automatic);
    show(true, false);
    var selected = invite.querySelector('input[name="invite-audience"]:checked');
    if (selected) selected.focus();
  });
  close.addEventListener('click', dismiss);
  invite.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !panel.hidden && invite.contains(document.activeElement)) {
      event.preventDefault();
      dismiss();
    }
  });
  invite.querySelectorAll('input[name="invite-audience"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      if (radio.checked && Object.prototype.hasOwnProperty.call(destinations, radio.value)) {
        register.href = destinations[radio.value];
      }
    });
  });
  if (!dismissed) {
    automatic = window.setTimeout(function () {
      if (!dismissed && !interacted && document.visibilityState !== 'hidden' && !invite.contains(document.activeElement)) show(true, false);
    }, 1100);
  }
  window.addEventListener('pagehide', function () { window.clearTimeout(automatic); }, {once: true});
})();

