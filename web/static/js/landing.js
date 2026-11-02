/* Public local-only product tour, catalogue exploration and invitation. No account data or API calls. */
(function () {
  'use strict';
  var demo = document.getElementById('landing-demo');
  if (demo) {
    var tabs = Array.from(demo.querySelectorAll('[data-demo-tab]'));
    var panels = Array.from(demo.querySelectorAll('[data-demo-panel]'));
    var steps = Array.from(demo.querySelectorAll('[data-demo-target]'));
    var status = document.getElementById('demo-status');
    var labels = {clientes: 'Clientes', plan: 'Plan nutricional', historial: 'Historial y PDF', rutinas: 'Rutinas'};
    var previous = document.getElementById('demo-previous');
    var next = document.getElementById('demo-next');
    var progress = document.getElementById('demo-progress');
    var selectedIndex = 0;
    function select(name, focus, announce) {
      if (!Object.prototype.hasOwnProperty.call(labels, name)) return;
      var selected = tabs.find(function (tab) { return tab.dataset.demoTab === name; });
      if (!selected) return;
      selectedIndex = tabs.indexOf(selected);
      tabs.forEach(function (tab) {
        var active = tab === selected;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
      });
      panels.forEach(function (panel) { panel.hidden = panel.dataset.demoPanel !== name; });
      if (previous) previous.disabled = selectedIndex === 0;
      if (next) next.disabled = selectedIndex === tabs.length - 1;
      if (progress) {
        progress.textContent = String(selectedIndex + 1).padStart(2, '0') + ' / ' + String(tabs.length).padStart(2, '0');
        progress.setAttribute('aria-label', 'Paso ' + (selectedIndex + 1) + ' de ' + tabs.length + ': ' + labels[name]);
      }
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
    if (previous) previous.addEventListener('click', function () {
      if (selectedIndex > 0) select(tabs[selectedIndex - 1].dataset.demoTab, true, true);
    });
    if (next) next.addEventListener('click', function () {
      if (selectedIndex < tabs.length - 1) select(tabs[selectedIndex + 1].dataset.demoTab, true, true);
    });
    var search = document.getElementById('demo-client-search');
    var empty = document.getElementById('demo-client-empty');
    var clients = Array.from(demo.querySelectorAll('[data-demo-client]'));
    function normalized(text) { return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim(); }
    if (search) search.disabled = false;
    if (search) search.addEventListener('input', function () {
      var query = normalized(search.value), found = 0;
      clients.forEach(function (client) {
        var matches = normalized(client.dataset.clientName || '').includes(query);
        client.hidden = !matches;
        if (matches) found += 1;
      });
      if (empty) empty.hidden = found !== 0;
    });

    var expand = document.getElementById('demo-expand');
    var dialog = null, placeholder = null, opener = null;
    function expandDemo(name, trigger) {
      if (name) select(name, false, true);
      if (!dialog) {
        dialog = document.createElement('dialog');
        if (typeof dialog.showModal !== 'function') return;
        dialog.id = 'demo-dialog';
        dialog.className = 'demo-dialog';
        dialog.setAttribute('aria-labelledby', 'demo-dialog-title');
        var header = document.createElement('div');
        header.className = 'demo-dialog-header';
        var title = document.createElement('h2');
        title.id = 'demo-dialog-title';
        title.textContent = 'Explora Método Base';
        var collapse = document.createElement('button');
        collapse.type = 'button';
        collapse.id = 'demo-collapse';
        collapse.className = 'demo-dialog-close';
        collapse.textContent = 'Cerrar ×';
        collapse.setAttribute('aria-label', 'Cerrar demostración ampliada');
        collapse.addEventListener('click', function () { dialog.close(); });
        header.append(title, collapse);
        dialog.append(header);
        document.body.append(dialog);
        dialog.addEventListener('close', function () {
          if (placeholder && placeholder.parentNode) {
            placeholder.parentNode.insertBefore(demo, placeholder);
            placeholder.remove();
            placeholder = null;
          }
          demo.classList.remove('is-expanded');
          document.documentElement.classList.remove('demo-modal-open');
          if (opener && opener.isConnected) opener.focus();
        });
      }
      if (dialog.open) return;
      opener = trigger || document.activeElement;
      placeholder = document.createComment('Product tour original position');
      demo.before(placeholder);
      dialog.append(demo);
      demo.classList.add('is-expanded');
      document.documentElement.classList.add('demo-modal-open');
      dialog.showModal();
      document.getElementById('demo-collapse').focus();
    }
    if (expand && typeof document.createElement('dialog').showModal === 'function') {
      expand.disabled = false;
      expand.addEventListener('click', function () { expandDemo(null, expand); });
      document.querySelectorAll('[data-demo-launch]').forEach(function (button) {
        button.disabled = false;
        button.addEventListener('click', function () { expandDemo(button.dataset.demoLaunch, button); });
      });
    }
    select('clientes', false, false);
    demo.dataset.enhanced = 'true';
  }

  var pricing = document.getElementById('suscripciones');
  var controls = document.getElementById('pricing-controls');
  var compareButton = document.getElementById('pricing-compare');
  if (pricing && controls && compareButton) {
    var catalogues = {gym: document.getElementById('planes-negocio'), usuario: document.getElementById('planes-personales')};
    var audienceButtons = Array.from(controls.querySelectorAll('[data-pricing-audience]'));
    var planButtons = Array.from(pricing.querySelectorAll('[data-plan-select]'));
    var selectedPlans = {gym: 'free', usuario: 'starter'};
    var audience = 'gym', comparing = false;
    function renderPricing() {
      audienceButtons.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.pricingAudience === audience)); });
      Object.keys(catalogues).forEach(function (key) {
        var catalogue = catalogues[key];
        if (!catalogue) return;
        catalogue.hidden = key !== audience;
        catalogue.classList.toggle('pricing-single', !comparing);
        catalogue.querySelectorAll('[data-plan], [data-personal-plan]').forEach(function (card) {
          card.hidden = !comparing && (card.dataset.plan || card.dataset.personalPlan) !== selectedPlans[key];
        });
      });
      planButtons.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.planSelect === selectedPlans[button.dataset.planAudience])); });
      compareButton.setAttribute('aria-expanded', String(comparing));
      compareButton.textContent = comparing ? 'Volver a la elegida' : 'Comparar suscripciones';
      pricing.dataset.audience = audience;
      pricing.dataset.comparing = String(comparing);
    }
    function chooseAudience(value) {
      if (!Object.prototype.hasOwnProperty.call(catalogues, value)) return;
      audience = value;
      comparing = false;
      renderPricing();
    }
    audienceButtons.forEach(function (button) {
      button.disabled = false;
      button.addEventListener('click', function () { chooseAudience(button.dataset.pricingAudience); });
    });
    planButtons.forEach(function (button) {
      button.disabled = false;
      button.addEventListener('click', function () {
        var key = button.dataset.planAudience, choice = button.dataset.planSelect;
        var card = document.getElementById('plan-' + choice);
        if (!card || !catalogues[key] || !catalogues[key].contains(card)) return;
        selectedPlans[key] = choice;
        audience = key;
        comparing = false;
        renderPricing();
      });
    });
    compareButton.addEventListener('click', function () { comparing = !comparing; renderPricing(); });
    controls.hidden = false;
    compareButton.hidden = false;
    compareButton.disabled = false;
    pricing.querySelectorAll('[data-plan-picker]').forEach(function (picker) { picker.hidden = false; });
    var audienceHashes = {'#para-ti': 'usuario', '#planes-personales': 'usuario', '#planes-negocio': 'gym'};
    function applyHash(scroll) {
      var value = audienceHashes[location.hash];
      if (!value) return;
      chooseAudience(value);
      if (scroll) {
        var target = document.getElementById(location.hash.slice(1));
        if (target) target.scrollIntoView({block: 'start', behavior: 'auto'});
      }
    }
    renderPricing();
    pricing.dataset.enhanced = 'true';
    document.addEventListener('click', function (event) {
      var link = event.target.closest('a[href]');
      if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var value = audienceHashes[link.getAttribute('href')];
      if (value) chooseAudience(value);
    });
    window.addEventListener('hashchange', function () { applyHash(true); });
    if (Object.prototype.hasOwnProperty.call(audienceHashes, location.hash)) {
      applyHash(false);
      window.requestAnimationFrame(function () { applyHash(true); });
    }
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

