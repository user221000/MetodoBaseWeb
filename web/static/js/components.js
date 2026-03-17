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
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || '📌'}</span>
      <span>${message}</span>
    `;

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

// ── Avatar color from name ─────────────────────────────────────────────────

const AVATAR_COLORS = [
  'linear-gradient(135deg,#667eea,#764ba2)',
  'linear-gradient(135deg,#ff6b9d,#ee5a24)',
  'linear-gradient(135deg,#48dbfb,#0abde3)',
  'linear-gradient(135deg,#feca57,#ff9f43)',
  'linear-gradient(135deg,#2ed573,#1e90ff)',
  'linear-gradient(135deg,#a29bfe,#fd79a8)',
];

function nameToInitials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]?.toUpperCase()).join('');
}

function nameToColor(name = '') {
  let hash = 0;
  for (const c of name) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function buildAvatar(name, size = '') {
  const div = document.createElement('div');
  div.className = `avatar ${size}`;
  div.style.background = nameToColor(name);
  div.textContent = nameToInitials(name) || '?';
  return div;
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
  const diff = Math.floor((Date.now() - d) / 86400000);
  if (diff === 0) return 'Hoy';
  if (diff === 1) return 'Ayer';
  if (diff < 7)  return `Hace ${diff} días`;
  return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' });
}

function formatKcal(n) {
  return n ? `${Math.round(n).toLocaleString('es-MX')} kcal` : '—';
}

// ── Expose globally ────────────────────────────────────────────────────────
window.Toast              = Toast;
window.Loading            = Loading;
window.animateCounter     = animateCounter;
window.animateAllCounters = animateAllCounters;
window.counterObserver    = counterObserver;
window.setActiveSidebarLink = setActiveSidebarLink;
window.buildAvatar        = buildAvatar;
window.buildBadge         = buildBadge;
window.nameToInitials     = nameToInitials;
window.nameToColor        = nameToColor;
window.formatDate         = formatDate;
window.formatKcal         = formatKcal;
