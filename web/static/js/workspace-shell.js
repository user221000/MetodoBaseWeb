/* One accessible mobile navigation owner for both account spaces. */
(() => {
  'use strict';
  const button = document.getElementById('btn-hamburger');
  const sidebar = document.getElementById('main-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const main = document.getElementById('main-content');
  if (!button || !sidebar || !overlay || !main) return;
  const mobile = window.matchMedia('(max-width: 768px)');
  let opened = false;
  function items() {
    return Array.from(sidebar.querySelectorAll('a[href],button:not(:disabled),summary,[tabindex="0"]'))
      .filter(node => !node.closest('[hidden],[inert]') && node.getClientRects().length);
  }
  function setOpen(value, restore = false) {
    opened = mobile.matches && value;
    sidebar.classList.toggle('open', opened);
    overlay.classList.toggle('active', opened);
    document.body.classList.toggle('mb-menu-open', opened);
    button.setAttribute('aria-expanded', String(opened));
    button.setAttribute('aria-label', opened ? 'Cerrar menú' : 'Abrir menú');
    sidebar.inert = mobile.matches && !opened;
    main.inert = opened;
    if (opened) (items()[0] || button).focus();
    else if (restore) button.focus();
  }
  setOpen(false);
  button.addEventListener('click', () => setOpen(!opened, true));
  overlay.addEventListener('click', () => setOpen(false, true));
  mobile.addEventListener('change', () => setOpen(false));
  window.addEventListener('metodobase-session-changed', () => setOpen(false));
  document.addEventListener('keydown', event => {
    if (!opened) return;
    if (event.key === 'Escape') { event.preventDefault(); setOpen(false, true); return; }
    if (event.key !== 'Tab') return;
    const nodes = items();
    const first = nodes[0] || button, last = nodes[nodes.length - 1] || button;
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); button.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); button.focus(); }
    else if (document.activeElement === button) { event.preventDefault(); (event.shiftKey ? last : first).focus(); }
    else if (!sidebar.contains(document.activeElement)) { event.preventDefault(); first.focus(); }
  });
})();
