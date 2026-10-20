/* Standalone purpose-only DOM adapter: text sinks, proof properties and RAM only. */
(function () {
  'use strict';
  const byId = id => document.getElementById('retirement-'+id), form = byId('form');
  if (!form || !window.RetiroConsentimientos) return;
  const email = byId('email'), password = byId('password'), factor = byId('factor'), kind = byId('factor-kind');
  const names = {weight:'Peso corporal',body_fat:'Grasa corporal',lean_mass:'Masa magra',completion:'Marcas de consumo completado'};
  let displayed = null, page;
  const node = (tag,text) => { const result = document.createElement(tag); result.textContent = text; return result; };
  const clearSecrets = () => { password.value = ''; factor.value = ''; };
  function showFactor() {
    factor.value = ''; const active = kind.value !== 'none';
    byId('factor-group').hidden = !active; factor.required = active; factor.disabled = !active;
    factor.inputMode = kind.value === 'totp' ? 'numeric' : 'text';
    byId('factor-label').textContent = kind.value === 'recovery' ? 'Código de recuperación sin usar' : 'Código actual de la aplicación';
  }
  function render(state) {
    byId('status').textContent = state.status; byId('error').textContent = state.error; byId('error').hidden = !state.error;
    form.setAttribute('aria-busy',String(state.busy));
    for (const suffix of ['password','factor-kind','query','next','withdraw']) byId(suffix).disabled = state.busy;
    factor.disabled = state.busy || kind.value === 'none';
    byId('next').hidden = !state.next; byId('withdraw').hidden = state.selected === null;
    byId('results').hidden = !state.rows.length;
    byId('selection').textContent = state.selected === null ? '' : 'Permiso '+(state.selected+1)+' seleccionado. Comprueba sus categorías y periodo antes de confirmar.';
    if (displayed !== state.rows) {
      displayed = state.rows; byId('items').replaceChildren();
      state.rows.forEach((row,index) => {
        const li = document.createElement('li'), article = document.createElement('article'), record = row.consent;
        article.append(node('h3','Permiso '+(index+1)),node('p','Categorías: '+(Object.keys(names).filter(key => record.categories[key]).map(key => names[key]).join(', ') || 'Ninguna categoría registrada')+'.'),
          node('p','Periodo: desde '+record.from_date+(record.ongoing ? ', sin fecha final indicada.' : ' hasta '+record.through_date+'.')),
          node('p','Registro: '+record.created_at+' (fecha y zona originales).'),
          node('p',record.event === 'withdraw' ? 'Retirado. El registro histórico se conserva.' : 'Permiso registrado. Esta consulta no demuestra acceso vigente a sus datos.'));
        if (row.capabilities.withdraw) {
          const button = node('button','Seleccionar permiso '+(index+1)+' para retirar'); button.type = 'button';
          button.disabled = state.busy; button.addEventListener('click',() => { page.select(index); if (page.view().selected === index) password.focus(); }); article.append(button);
        }
        li.append(article); byId('items').append(li);
      });
    }
    for (const button of byId('items').querySelectorAll('button')) button.disabled = state.busy;
  }
  page = RetiroConsentimientos.create({email:() => email.value,proof:() => ({password:password.value,factorKind:kind.value,factorValue:factor.value}),clearSecrets,fetch:(...args) => window.fetch(...args),render});
  async function action(call) {
    const result = await call();
    if (result === 'error' || result === 'invalid') { if (page.view().error) byId('error').focus(); }
    else if (result === 'confirmed') { if (page.view().rows.length) byId('results-title').focus(); else byId('status').focus(); }
  }
  form.addEventListener('submit',event => { event.preventDefault(); void action(page.query); });
  byId('next').addEventListener('click',() => { void action(page.more); });
  byId('withdraw').addEventListener('click',() => { void action(page.withdraw); });
  email.addEventListener('input',() => page.invalidate('El correo cambió. La consulta anterior se descartó; verifica de nuevo la cuenta.'));
  kind.addEventListener('change',showFactor);
  function discard(message) { email.value = ''; kind.value = 'none'; showFactor(); page.invalidate(message); }
  byId('clear').addEventListener('click',() => { discard('Consulta cancelada y datos de esta pantalla borrados. No cambia tu sesión habitual.'); email.focus(); });
  window.addEventListener('pagehide',() => discard('Consulta descartada al salir de la página.'));
  window.addEventListener('metodobase-session-changed',() => discard('La cuenta del navegador cambió. Verifica de nuevo los datos para esta consulta.'));
  window.addEventListener('storage',event => { if (event.key === null || ['mb_token','mb_refresh_token','mb_session_epoch'].includes(event.key)) discard('La cuenta del navegador cambió. Verifica de nuevo los datos para esta consulta.'); });
  email.disabled = false; byId('clear').disabled = false; showFactor(); render(page.view());
})();
