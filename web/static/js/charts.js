/**
 * charts.js — Configuraciones Chart.js para MetodoBase
 */

Chart.defaults.color        = '#a0a0b5';
Chart.defaults.borderColor  = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family  = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size    = 12;

/**
 * Crea un gradiente vertical para áreas de chart.
 * @param {CanvasRenderingContext2D} ctx
 * @param {string} colorTop  - rgba top
 * @param {string} colorBot  - rgba bottom
 * @param {number} height
 */
function makeGradient(ctx, colorTop, colorBot, height = 350) {
  const g = ctx.createLinearGradient(0, 0, 0, height);
  g.addColorStop(0, colorTop);
  g.addColorStop(1, colorBot);
  return g;
}

/** Tooltip estándar dark */
const darkTooltip = {
  backgroundColor: 'rgba(26,26,36,0.97)',
  titleColor: '#fff',
  bodyColor: '#a0a0b5',
  padding: 14,
  borderColor: 'rgba(255,255,255,0.08)',
  borderWidth: 1,
  cornerRadius: 10,
  displayColors: true,
  boxPadding: 4,
};

/**
 * Inicializa el gráfico de línea de planes generados.
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {number[]} data
 * @returns {Chart}
 */
function initPlanesChart(canvasId, labels, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const ctx = canvas.getContext('2d');

  const gradFill = makeGradient(ctx, 'rgba(102,126,234,0.45)', 'rgba(102,126,234,0.0)');

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Planes generados',
        data,
        borderColor: '#667eea',
        backgroundColor: gradFill,
        borderWidth: 2.5,
        tension: 0.42,
        fill: true,
        pointBackgroundColor: '#667eea',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 7,
        pointHoverBorderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: darkTooltip,
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { stepSize: 5 },
        },
        x: {
          grid: { display: false },
        },
      },
    },
  });
}

/**
 * Gráfico de dona para distribución de objetivos.
 * @param {string} canvasId
 * @param {object} objetivos  - { deficit: n, mantenimiento: n, superavit: n }
 * @returns {Chart}
 */
function initObjetivosChart(canvasId, objetivos) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const ctx = canvas.getContext('2d');

  const labels = Object.keys(objetivos).map(k => k.charAt(0).toUpperCase() + k.slice(1));
  const values = Object.values(objetivos);
  const colors = ['#667eea', '#feca57', '#ff6b9d'];
  const hovered = ['#8096ef', '#fed870', '#ff89b2'];

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        hoverBackgroundColor: hovered,
        borderWidth: 0,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { usePointStyle: true, padding: 16, boxWidth: 8 },
        },
        tooltip: darkTooltip,
      },
    },
  });
}

/**
 * Actualiza los datos de un chart existente con animación.
 * @param {Chart} chart
 * @param {string[]} labels
 * @param {number[]} data
 */
function updateChart(chart, labels, data) {
  if (!chart) return;
  chart.data.labels = labels;
  chart.data.datasets[0].data = data;
  chart.update('active');
}
