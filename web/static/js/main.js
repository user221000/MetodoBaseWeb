/**
 * main.js — Dashboard initialization + onboarding + keyboard UX
 */

// Ensure initDashboard runs even if DOMContentLoaded already fired
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setActiveSidebarLink();
    initDashboard();
    initKeyboardUX();
  });
} else {
  setActiveSidebarLink();
  initDashboard();
  initKeyboardUX();
}

// ── Dashboard ──────────────────────────────────────────────────────────────

async function initDashboard() {
  const kpiSection = document.getElementById('kpi-section');
  if (!kpiSection) return; // not on dashboard page

  counterObserver.observe(kpiSection);
  showKPISkeletons(true);

  try {
    const stats = await Api.stats.obtener();
    showKPISkeletons(false);
    renderActivityFeed(stats.top_clientes || []);
    renderTopClientes(stats.top_clientes || []);
    updateOnboarding(stats);

    // Render AI insights if available
    if (window.Insights && typeof Insights.render === 'function') {
      Insights.render(stats);
    }

    // Update sidebar badge
    setText('sb-total-clientes', stats.total_clientes || '');

    // Dynamic context bar — update based on client state
    const ctxDynamic = document.getElementById('ctx-dynamic');
    if (ctxDynamic) {
      const _total = stats.total_clientes || 0;
      const _inactivos = Math.max(0, _total - (stats.clientes_activos || 0));
      if (_total === 0) {
        ctxDynamic.textContent = '👋 Registra tu primer cliente para empezar';
      } else if (_inactivos > 0) {
        ctxDynamic.textContent = `🔔 ${_inactivos} cliente${_inactivos > 1 ? 's' : ''} sin plan reciente — genéra${_inactivos > 1 ? 'les' : 'le'} uno hoy`;
      } else {
        ctxDynamic.textContent = '🏆 Todos tus clientes tienen plan activo';
      }
    }
  } catch (err) {
    console.error('[dashboard] error:', err);
    showKPISkeletons(false);
    Toast.error('No se pudieron cargar las estadísticas');
  }
}

// ── Skeleton loading ───────────────────────────────────────────────────────

function showKPISkeletons(show) {
  const section = document.getElementById('kpi-section');
  if (!section) return;
  section.querySelectorAll('.kpi-value').forEach(el => {
    if (show) {
      el.dataset.originalText = el.textContent;
      el.innerHTML = '<div class="skeleton skeleton-value"></div>';
    } else {
      el.textContent = el.dataset.originalText || '—';
    }
  });
}

// ── Activity Feed ──────────────────────────────────────────────────────────

function renderActivityFeed(clientes) {
  const feed = document.getElementById('recent-activity');
  if (!feed) return;

  feed.innerHTML = '';

  if (!clientes.length) {
    feed.innerHTML = `
      <li class="feed-item">
        <div class="feed-info">
          <span class="feed-name" style="color:var(--text-muted)">Sin actividad reciente</span>
        </div>
      </li>`;
    return;
  }

  clientes.slice(0, 3).forEach(c => {
    const hasPlan = c.ultimo_plan != null;
    const actionText = hasPlan ? 'Plan generado' : 'Registrado';
    const dateRef = c.ultimo_plan || c.fecha_registro;
    const timeAgo = formatRelativeTime(dateRef);
    const li = document.createElement('li');
    li.className = 'feed-item';
    li.innerHTML = `
      <div class="feed-avatar"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.7 0 4.8-2.2 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg></div>
      <div class="feed-info">
        <span class="feed-name">${esc(c.nombre)}</span>
        <span class="feed-action">${actionText}</span>
      </div>
      <span class="feed-time">${timeAgo}</span>
    `;
    feed.appendChild(li);
  });
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'ahora';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;
  return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

// ── KPI helpers ────────────────────────────────────────────────────────────

function setKPI(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.dataset.count = value;
  animateCounter(el, value);
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ── Top clientes table ─────────────────────────────────────────────────────

function renderTopClientes(top) {
  const tbody = document.getElementById('top-clientes-tbody');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (!top.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4">
          <div class="empty-state-smart">
            <div class="empty-icon">
              <svg style="width:32px;height:32px;color:var(--accent-purple)" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </div>
            <p style="font-weight:600;color:var(--text-primary);font-size:.95rem;margin-bottom:4px;">Sin clientes aún</p>
            <p style="color:var(--text-muted);font-size:.82rem;margin-bottom:14px;">Usa el botón “Nuevo cliente” para registrar tu primer cliente</p>
          </div>
        </td>
      </tr>`;
    return;
  }

  top.slice(0, 5).forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="flex items-center gap-3">
          <div></div>
          <span class="font-semibold" style="font-size:.875rem">${esc(c.nombre)}</span>
        </div>
      </td>
      <td>${buildBadge(c.objetivo).outerHTML}</td>
      <td class="text-secondary-color text-sm">${c.ultimo_plan ? formatDate(c.ultimo_plan) : (c.fecha_registro ? formatDate(c.fecha_registro) : '—')}</td>
      <td><a href="/generar-plan?id=${esc(c.id_cliente || c.id)}" class="btn btn-primary btn-sm" style="font-size:.72rem;padding:4px 10px;">Plan →</a></td>
    `;
    tr.querySelector('div > div').replaceWith(buildAvatar(c.nombre));
    tbody.appendChild(tr);
  });
}

// ── Onboarding Checklist ───────────────────────────────────────────────────

function updateOnboarding(stats) {
  const section = document.getElementById('onboarding-section');
  if (!section) return;

  const totalClientes = stats.total_clientes || 0;
  const totalPlanes = stats.planes_periodo || 0;
  const hasClients = totalClientes > 0;
  const hasPlans = totalPlanes > 0;
  const hasExported = hasPlans;

  const steps = [
    { done: hasClients, id: 1 },
    { done: hasPlans, id: 2 },
    { done: hasExported, id: 3 },
  ];

  const completedCount = steps.filter(s => s.done).length;

  // Hide onboarding if all steps complete AND user has seen it
  if (completedCount === 3) {
    if (localStorage.getItem('mb_onboarding_complete') === '1') {
      section.style.display = 'none';
      return;
    }
    localStorage.setItem('mb_onboarding_complete', '1');
  }

  // Always show for incomplete or newly completed
  section.style.display = 'block';

  // Update progress bar
  const pct = Math.round((completedCount / 3) * 100);
  const pctEl = document.getElementById('onboarding-pct');
  const barEl = document.getElementById('onboarding-bar-fill');
  if (pctEl) pctEl.textContent = pct + '%';
  if (barEl) barEl.style.width = pct + '%';

  // Update step states
  let firstIncomplete = true;
  steps.forEach(step => {
    const stepEl = document.getElementById('ob-step-' + step.id);
    if (!stepEl) return;

    stepEl.classList.remove('completed', 'current');
    if (step.done) {
      stepEl.classList.add('completed');
    } else if (firstIncomplete) {
      stepEl.classList.add('current');
      firstIncomplete = false;
    }
  });

  // Wire onboarding action: step 1 opens the modal
  const action1 = document.getElementById('ob-action-1');
  if (action1) {
    action1.addEventListener('click', () => {
      const btn = document.getElementById('btn-generar-plan');
      if (btn) btn.click();
    });
  }
}

// ── Keyboard UX — Enter triggers primary action everywhere ─────────────────

function initKeyboardUX() {
  // Wire Enter key for all search inputs globally
  document.querySelectorAll('input[type="search"], input[id*="search"]').forEach(input => {
    input.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      // Find the nearest search/submit button
      const container = input.closest('.search-bar, .food-panel-search, .chart-container, div');
      const btn = container?.querySelector('.btn-primary, [id*="buscar"], button[type="submit"]');
      if (btn) {
        btn.click();
      } else {
        // Trigger input event for live-search fields
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    // Only handle Enter key
    if (e.key !== 'Enter') return;

    // Don't interfere with textareas or contenteditable
    const tag = e.target.tagName;
    if (tag === 'TEXTAREA' || e.target.isContentEditable) return;

    // If inside a form, let the form handle it naturally
    if (e.target.closest('form')) return;

    // If target is a search input, already handled above
    if (e.target.type === 'search' || e.target.id?.includes('search')) return;

    // If a modal is open, trigger its primary button
    const openModal = document.querySelector('.modal-backdrop:not(.hidden)');
    if (openModal) {
      const primaryBtn = openModal.querySelector('.btn-primary:not(:disabled)');
      if (primaryBtn) {
        e.preventDefault();
        primaryBtn.click();
        return;
      }
    }

    // On dashboard, trigger the hero CTA
    const heroCta = document.getElementById('btn-generar-plan');
    if (heroCta && !heroCta.disabled && document.getElementById('kpi-section')) {
      e.preventDefault();
      heroCta.click();
    }
  });

  // Tab navigation: ensure all interactive elements are focusable
  document.querySelectorAll('.kpi-card, .nav-item, .btn, button, a[href]').forEach(el => {
    if (!el.getAttribute('tabindex') && el.tagName !== 'A' && el.tagName !== 'BUTTON' && el.tagName !== 'INPUT') {
      el.setAttribute('tabindex', '0');
    }
  });

  // Escape key closes any open modal
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const openModal = document.querySelector('.modal-backdrop:not(.hidden)');
    if (openModal) {
      e.preventDefault();
      const closeBtn = openModal.querySelector('.modal-close, [id*="modal-close"], [id*="close"]');
      if (closeBtn) {
        closeBtn.click();
      } else {
        openModal.classList.add('hidden');
      }
    }
  });
}
