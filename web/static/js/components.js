/**
 * components.js — Componentes reutilizables de UI
 */

// ── Toast ──────────────────────────────────────────────────────────────────

const Toast = (() => {
  function show(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconSpan = document.createElement('span');
    iconSpan.className = 'toast-icon';
    iconSpan.textContent = icons[type] || '📌';
    
    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    
    toast.appendChild(iconSpan);
    toast.appendChild(msgSpan);

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'toastOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  return { show,
    success: (msg, d) => show(msg, 'success', d),
    error:   (msg, d) => show(msg, 'error',   d),
    info:    (msg, d) => show(msg, 'info',     d),
    warning: (msg, d) => show(msg, 'warning',  d),
  };
})();

// ── Loading overlay ────────────────────────────────────────────────────────

const Loading = (() => {
  let overlay = null;

  function getOverlay() {
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'loading-overlay hidden';
      overlay.innerHTML = `
        <div class="spinner" style="width:40px;height:40px;border-width:3px;"></div>
        <p id="loading-msg">Cargando...</p>
      `;
      document.body.appendChild(overlay);
    }
    return overlay;
  }

  function show(msg = 'Procesando...') {
    const el = getOverlay();
    el.querySelector('#loading-msg').textContent = msg;
    el.classList.remove('hidden');
  }

  function hide() { getOverlay().classList.add('hidden'); }

  return { show, hide };
})();

// ── Counter animation ──────────────────────────────────────────────────────

function animateCounter(el, target, duration = 1200) {
  const start = performance.now();
  const from  = parseInt(el.textContent) || 0;

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out quart
    const ease = 1 - Math.pow(1 - progress, 4);
    el.textContent = Math.round(from + (target - from) * ease);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

function animateAllCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    animateCounter(el, target);
  });
}

// ── Intersection observer para auto-animar counters ───────────────────────

const counterObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.querySelectorAll('[data-count]').forEach(el => {
          const target = parseInt(el.dataset.count, 10);
          animateCounter(el, target);
        });
        counterObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.2 }
);

// ── Sidebar active link ────────────────────────────────────────────────────

function setActiveSidebarLink() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href') || '';
    const isActive = href === path || (href !== '/' && path.startsWith(href));
    item.classList.toggle('active', isActive);
  });
}

// ── Avatar ──────────────────────────────────────────────────────────────────

function buildAvatar(name, size = '') {
  const wrapper = document.createElement('div');
  wrapper.className = size ? `avatar avatar-${size}` : 'avatar';
  wrapper.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.7 0 4.8-2.2 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg>';
  return wrapper;
}

// ── Objetivo badge  ────────────────────────────────────────────────────────

const OBJETIVO_LABELS = {
  deficit:       { label: 'Déficit',       cls: 'badge-purple' },
  mantenimiento: { label: 'Mantenimiento', cls: 'badge-yellow' },
  superavit:     { label: 'Superávit',     cls: 'badge-green'  },
};

function buildBadge(objetivo) {
  const cfg = OBJETIVO_LABELS[objetivo] || { label: objetivo, cls: 'badge-purple' };
  const span = document.createElement('span');
  span.className = `badge ${cfg.cls}`;
  span.textContent = cfg.label;
  return span;
}

// ── Format helpers ──────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  // Normalize to local calendar days to avoid UTC+offset comparisons
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dayD = new Date(d);
  dayD.setHours(0, 0, 0, 0);
  const diff = Math.round((today - dayD) / 86400000);
  if (diff <= 0) return 'Hoy';
  if (diff === 1) return 'Ayer';
  if (diff < 7)  return `Hace ${diff} días`;
  return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' });
}

function formatKcal(n) {
  return n ? `${Math.round(n).toLocaleString('es-MX')} kcal` : '—';
}

// ── Debounce utility ────────────────────────────────────────────────────────

function debounce(fn, ms = 300) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

// ── Escape HTML ──────────────────────────────────────────────────────────────

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/`/g, '&#x60;');
}

// ── Expose globally ──────────────────────────────────────────────────────────
window.Toast              = Toast;
window.Loading            = Loading;
window.animateCounter     = animateCounter;
window.animateAllCounters = animateAllCounters;
window.counterObserver    = counterObserver;
window.setActiveSidebarLink = setActiveSidebarLink;
window.buildAvatar        = buildAvatar;
window.buildBadge         = buildBadge;
window.formatDate         = formatDate;
window.formatKcal         = formatKcal;
window.debounce           = debounce;
window.esc                = esc;
