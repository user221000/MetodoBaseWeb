/**
 * main.js — Inicialización global y página de Dashboard
 */

document.addEventListener('DOMContentLoaded', () => {
  setActiveSidebarLink();
  initDashboard();
});

// ── Dashboard ──────────────────────────────────────────────────────────────

async function initDashboard() {
  const kpiSection = document.getElementById('kpi-section');
  if (!kpiSection) return;   // no estamos en el dashboard

  // Registrar sección KPI para contador animado
  counterObserver.observe(kpiSection);

  try {
    const stats = await Api.stats.obtener();
    renderKPIs(stats);
    renderPlanesChart(stats);
    renderObjetivosChart(stats);
    renderTopClientes(stats.top_clientes || []);
  } catch (err) {
    console.error('[dashboard] error:', err);
    Toast.error('No se pudieron cargar las estadísticas');
    renderKPIs({});  // fallback a ceros
  }

  // Tabs de período del gráfico
  document.querySelectorAll('.time-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.time-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // TODO: recargar datos por período desde API
    });
  });
}

// ── KPI render ─────────────────────────────────────────────────────────────

function renderKPIs(stats) {
  setKPI('kpi-clientes',  stats.total_clientes   || 0);
  setKPI('kpi-planes',    stats.planes_periodo   || 0);
  setKPI('kpi-kcal',      Math.round(stats.promedio_kcal || 0));
  setKPI('kpi-activos',   stats.clientes_activos || 0);

  setText('kpi-nuevos-label', stats.clientes_nuevos
    ? `+${stats.clientes_nuevos} este mes`
    : '—');

  const retencion = stats.tasa_retencion
    ? `${Math.round(stats.tasa_retencion * 100)}%`
    : '—';
  setText('kpi-retencion', retencion);
}

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

// ── Planes chart ───────────────────────────────────────────────────────────

let _planesChart = null;

function renderPlanesChart(stats) {
  // Generar labels últimos 7 días
  const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  const labels = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return DIAS[d.getDay()];
  });

  // Usar datos reales si la API los envía, sino datos de ejemplo
  const data = stats.planes_por_dia || [4, 9, 6, 14, 11, 18, 13];
  _planesChart = initPlanesChart('planesChart', labels, data);
}

// ── Objetivos chart ────────────────────────────────────────────────────────

let _objetivosChart = null;

function renderObjetivosChart(stats) {
  const obj = stats.objetivos || { deficit: 1, mantenimiento: 1, superavit: 1 };
  _objetivosChart = initObjetivosChart('objetivosChart', obj);
}

// ── Top clientes ────────────────────────────────────────────────────────────

function renderTopClientes(top) {
  const tbody = document.getElementById('top-clientes-tbody');
  if (!tbody) return;

  tbody.innerHTML = '';

  if (!top.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted" style="padding:32px">
          Sin datos aún
        </td>
      </tr>`;
    return;
  }

  top.slice(0, 8).forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="flex items-center gap-3">
          <div></div>
          <div>
            <p class="font-semibold" style="font-size:.875rem">${esc(c.nombre)}</p>
            <p class="text-xs text-muted">${esc(c.telefono || '—')}</p>
          </div>
        </div>
      </td>
      <td>${buildBadge(c.objetivo).outerHTML}</td>
      <td class="text-secondary-color text-sm">${formatKcal(c.kcal_objetivo)}</td>
      <td class="text-secondary-color text-sm">${formatDate(c.ultima_actualizacion)}</td>
    `;
    // Insertar avatar
    tr.querySelector('div > div').replaceWith(buildAvatar(c.nombre));
    tbody.appendChild(tr);
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
