/**
 * insights.js — AI-style heuristic engine for MetodoBase dashboard.
 *
 * Analyzes stats data client-side and generates actionable business insights.
 * No backend AI: pure heuristic analysis of existing metrics.
 */

const Insights = (() => {

  /**
   * Generate business insights from dashboard stats.
   * @param {Object} stats — Stats object from API
   * @returns {Array<{icon: string, text: string}>}
   */
  function generate(stats) {
    const insights = [];
    const total = stats.total_clientes || 0;
    const nuevos = stats.clientes_nuevos || 0;
    const planes = stats.planes_periodo || 0;
    const activos = stats.clientes_activos || 0;
    const retencion = stats.tasa_retencion || 0;
    const objetivos = stats.objetivos || {};
    const planesArr = stats.planes_por_dia || [];

    // Growth insight
    if (nuevos > 0 && total > 0) {
      const growthPct = Math.round(nuevos / total * 100);
      insights.push({
        icon: '📈',
        text: `Crecimiento del ${growthPct}% este período — ${nuevos} clientes nuevos de ${total} totales.`
      });
    }

    // Retention alert
    if (total > 5 && retencion < 50) {
      const sinPlan = total - activos;
      insights.push({
        icon: '⚠️',
        text: `${sinPlan} clientes no tienen plan reciente. Retención al ${Math.round(retencion)}% — considera reactivarlos.`
      });
    } else if (retencion >= 80) {
      insights.push({
        icon: '🏆',
        text: `Excelente retención del ${Math.round(retencion)}%. Tu gimnasio mantiene alta fidelidad.`
      });
    }

    // Best day detection
    if (planesArr.length > 0) {
      const maxPlans = Math.max(...planesArr);
      const labels = stats.planes_labels || [];
      if (maxPlans > 0) {
        const bestIdx = planesArr.indexOf(maxPlans);
        const bestDay = labels[bestIdx] || '';
        insights.push({
          icon: '⚡',
          text: `Tu mejor día fue ${bestDay} con ${maxPlans} planes generados. Concentra campañas en ese día.`
        });
      }
    }

    // Objective imbalance
    const objValues = Object.values(objetivos);
    const objKeys = Object.keys(objetivos);
    if (objValues.length > 0) {
      const maxObj = Math.max(...objValues);
      const maxObjIdx = objValues.indexOf(maxObj);
      const dominantObj = objKeys[maxObjIdx];
      const pct = total > 0 ? Math.round(maxObj / total * 100) : 0;
      if (pct > 60) {
        const label = dominantObj === 'deficit' ? 'déficit' : dominantObj === 'superavit' ? 'superávit' : 'mantenimiento';
        insights.push({
          icon: '🎯',
          text: `El ${pct}% de tus clientes buscan ${label}. Oportunidad de diversificación de servicios.`
        });
      }
    }

    // Activity momentum
    if (planes > 0 && total > 0) {
      const ratio = (planes / total).toFixed(1);
      insights.push({
        icon: '🔄',
        text: `Promedio de ${ratio} planes por cliente este período. ${Number(ratio) >= 1 ? 'Ritmo saludable.' : 'Hay espacio para crecer.'}`
      });
    }

    return insights.slice(0, 4);
  }

  /**
   * Render insights into the AI insight card.
   */
  function render(stats) {
    const card = document.getElementById('ai-insights');
    const title = document.getElementById('ai-insight-title');
    const list = document.getElementById('ai-insight-list');
    if (!card || !list) return;

    const insights = generate(stats);

    if (insights.length === 0) {
      card.style.display = 'none';
      return;
    }

    if (title) title.textContent = 'Para hacer esta semana';
    list.innerHTML = insights.map(i =>
      `<li>${esc(i.icon)} ${esc(i.text)}</li>`
    ).join('');
    card.style.display = 'flex';
  }

  /**
   * Render chart annotation badge for best day.
   */
  function renderChartAnnotation(stats) {
    const badge = document.getElementById('chart-best-day');
    if (!badge) return;

    const planesArr = stats.planes_por_dia || [];
    const labels = stats.planes_labels || [];
    const maxPlans = Math.max(...planesArr);

    if (maxPlans <= 0) {
      badge.style.display = 'none';
      return;
    }

    const bestIdx = planesArr.indexOf(maxPlans);
    const totalPlanes = planesArr.reduce((a, b) => a + b, 0);
    const pct = totalPlanes > 0 ? Math.round(maxPlans / totalPlanes * 100) : 0;
    badge.textContent = `🔥 Pico: ${labels[bestIdx]} (${pct}% del total)`;
    badge.style.display = 'inline-flex';
  }

  return { generate, render, renderChartAnnotation };
})();

window.Insights = Insights;
