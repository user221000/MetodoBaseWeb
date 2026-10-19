/* Purpose-only proof per call. No session transport, persistence or automatic retry. */
(function (root) {
  'use strict';
  const scope = 'own_consent_retirement_only';
  const paths = Object.freeze({query:'/api/auth/progress-retirement/metadata', withdraw:'/api/auth/progress-retirement/withdraw'});
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
  const categories = ['weight','body_fat','lean_mass','completion'];
  const maximum = 2147483647, responseBudget = 262144;
  const fail = code => Object.assign(new Error(code), {code});
  function keys(value, expected) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== expected.length || expected.some(key => !Object.prototype.hasOwnProperty.call(value,key))) throw fail('protocol');
  }
  function id(value) { if (typeof value !== 'string' || !uuid.test(value)) throw fail('protocol'); return value; }
  function integer(value) { if (!Number.isSafeInteger(value) || value < 1 || value > maximum) throw fail('protocol'); return value; }
  function day(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value+'T00:00:00Z')) || new Date(value+'T00:00:00Z').toISOString().slice(0,10) !== value) throw fail('protocol');
    return value;
  }
  function consent(value) {
    keys(value,['id','version','event','protocol','link_version','categories','from_date','through_date','ongoing','created_at']);
    if (!['grant','withdraw'].includes(value.event) || value.protocol !== 'progress_share_v1') throw fail('protocol');
    keys(value.categories,categories);
    if (categories.some(key => typeof value.categories[key] !== 'boolean') || typeof value.ongoing !== 'boolean') throw fail('protocol');
    const from = day(value.from_date), through = value.through_date === null ? null : day(value.through_date);
    if ((value.ongoing && through !== null) || (!value.ongoing && (through === null || through < from))) throw fail('protocol');
    if (typeof value.created_at !== 'string' || value.created_at.length > 64 || !/T.+(?:Z|[+-]\d{2}:\d{2})$/.test(value.created_at) || !Number.isFinite(Date.parse(value.created_at))) throw fail('protocol');
    return Object.freeze({id:id(value.id),version:integer(value.version),event:value.event,protocol:value.protocol,link_version:integer(value.link_version),categories:Object.freeze({...value.categories}),from_date:from,through_date:through,ongoing:value.ongoing,created_at:value.created_at});
  }
  function item(value) {
    keys(value,['link_id','consent','capabilities']);keys(value.capabilities,['withdraw','grant']);
    if (typeof value.capabilities.withdraw !== 'boolean' || value.capabilities.grant !== false) throw fail('protocol');
    const record = consent(value.consent);
    if (record.event === 'withdraw' && value.capabilities.withdraw) throw fail('protocol');
    return Object.freeze({link_id:id(value.link_id),consent:record,capabilities:Object.freeze({...value.capabilities})});
  }
  function metadata(value, after) {
    keys(value,['scope','items','next_after']);
    if (value.scope !== scope || !Array.isArray(value.items) || value.items.length > 50) throw fail('protocol');
    const rows = value.items.map(item);
    let previous = after || null;
    for (const row of rows) { if (previous !== null && row.link_id <= previous) throw fail('protocol'); previous = row.link_id; }
    const next = value.next_after === null ? null : id(value.next_after);
    if (next !== null && (!rows.length || next !== rows[rows.length-1].link_id)) throw fail('protocol');
    return Object.freeze({rows:Object.freeze(rows),next});
  }
  function withdrawal(value, selected) {
    keys(value,['scope','link_id','consent','capabilities','effective']);
    if (value.scope !== scope || value.effective !== false) throw fail('protocol');
    const row = item({link_id:value.link_id,consent:value.consent,capabilities:value.capabilities});
    const before = selected.consent, after = row.consent;
    if (row.link_id !== selected.link_id || after.id === before.id || after.event !== 'withdraw' || row.capabilities.withdraw || after.version !== before.version+1 || after.link_version !== before.link_version || after.from_date !== before.from_date || after.through_date !== before.through_date || after.ongoing !== before.ongoing || categories.some(key => after.categories[key] !== before.categories[key])) throw fail('protocol');
    return row;
  }
  const messages = Object.freeze({
    input:'Escribe el correo y la contraseña. Si usas verificación en dos pasos, elige el tipo y escribe un código nuevo válido.',
    protocol:'No pudimos comprobar la respuesta. No se confirma ningún retiro. Realiza otra consulta explícita con tu contraseña y un código nuevo, si corresponde.',
    progress_retirement_verification_failed:'No se pudo verificar la cuenta o el código. Revisa los datos y usa un código nuevo, si corresponde. No se confirma ningún retiro.',
    progress_retirement_primary_unavailable:'Esta vía requiere una contraseña. No admite Google ni una sesión abierta como sustitutos.',
    mfa_service_unavailable:'La verificación en dos pasos no está disponible. No se confirma ningún retiro. Consulta de nuevo cuando esté disponible, con otra prueba válida.',
    progress_retirement_throttled:'Se alcanzó el límite de intentos. Espera antes de realizar otra consulta explícita con una prueba nueva.',
    rate_limit_backend_unavailable:'La verificación no está disponible. No se confirma ningún retiro. Vuelve a consultar explícitamente más adelante.',
    progress_retirement_busy:'Hay otra operación de esta cuenta en curso. Espera antes de realizar una nueva consulta explícita con otra prueba válida.',
    conflict:'El permiso pudo cambiar o ya estar retirado. No repetiremos el retiro. Consulta otra vez con tu contraseña y un código nuevo, si corresponde.',
    uncertain:'No se pudo confirmar el resultado; la acción puede haberse realizado. No repetiremos la operación. Consulta de nuevo explícitamente con tu contraseña y otro código válido, si corresponde.',
    invalid:'La solicitud no pudo completarse. Revisa los datos y realiza otra consulta explícita. No se confirma ningún retiro.'
  });
  function errorMessage(error) {
    if (Object.prototype.hasOwnProperty.call(messages,error.code)) return messages[error.code];
    if (error.status === 404 || error.status === 409) return messages.conflict;
    if (error.status >= 500 || error.code === 'transport') return messages.uncertain;
    return messages.invalid;
  }
  function create(options) {
    let epoch = 0, busy = false, rows = Object.freeze([]), next = null, selected = null, controller = null, metadataEmail = null;
    let status = 'Escribe los datos de la cuenta para consultar sus permisos.', error = '';
    const email = () => String(options.email()).trim();
    const view = () => Object.freeze({rows,next:next !== null,selected:selected === null ? null : rows.indexOf(selected),busy,status,error});
    const emit = () => options.render(view());
    function invalidate(message) {
      epoch++; if (controller) controller.abort(); controller = null; busy = false;
      rows = Object.freeze([]); next = null; selected = null; metadataEmail = null; error = '';
      status = message || 'Consulta descartada. Escribe de nuevo los datos de la cuenta.';
      options.clearSecrets(); emit();
    }
    function check(ticket) {
      if (epoch === ticket.epoch && email() !== ticket.email) invalidate('El correo cambió. La consulta anterior se descartó; verifica de nuevo la cuenta.');
      if (epoch !== ticket.epoch || email() !== ticket.email) throw fail('changed');
    }
    function select(index) {
      if (metadataEmail !== null && metadataEmail !== email()) { invalidate(); return; }
      if (busy || !Number.isSafeInteger(index) || !rows[index] || !rows[index].capabilities.withdraw || rows[index].consent.event !== 'grant') return;
      selected = rows[index]; options.clearSecrets(); error = '';
      status = 'Permiso seleccionado. Escribe de nuevo tu contraseña y un código nuevo, si corresponde, para confirmar el retiro.'; emit();
    }
    function bodyFor(kind, paging) {
      const proof = options.proof(), address = email();
      if (!address || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address) || typeof proof.password !== 'string' || !proof.password) throw fail('input');
      const body = {primary:{method:'password',email:address,password:proof.password}};
      if (proof.factorKind === 'totp') { if (!/^\d{6}$/.test(proof.factorValue)) throw fail('input'); body.factor = {code:proof.factorValue}; }
      else if (proof.factorKind === 'recovery') { if (!/^[A-Za-z0-9_-]{22}$/.test(proof.factorValue)) throw fail('input'); body.factor = {recovery_code:proof.factorValue}; }
      else if (proof.factorKind !== 'none' || proof.factorValue) throw fail('input');
      if (kind === 'withdraw') {
        if (!selected || !selected.capabilities.withdraw) throw fail('input');
        Object.assign(body,{link_id:selected.link_id,expected_consent_id:selected.consent.id,expected_version:selected.consent.version});
      } else { if (paging && next === null) throw fail('input'); Object.assign(body,{limit:50,after:paging ? next : null}); }
      const serialized = JSON.stringify(body);
      if (new TextEncoder().encode(serialized).byteLength > 8192) throw fail('input');
      return serialized;
    }
    async function decode(response, ticket) {
      if (!response.headers || !/^application\/json(?:\s*;|$)/i.test(response.headers.get('Content-Type') || '')) throw fail('protocol');
      const size = response.headers.get('Content-Length');
      if (size !== null && (!/^\d+$/.test(size) || Number(size) > responseBudget)) throw fail('protocol');
      let text = '';
      if (response.body && typeof response.body.getReader === 'function') {
        const reader = response.body.getReader(), decoder = new TextDecoder('utf-8',{fatal:true}); let length = 0;
        try { while (true) { const part = await reader.read(); check(ticket); if (part.done) break; length += part.value.byteLength; if (length > responseBudget) throw fail('protocol'); text += decoder.decode(part.value,{stream:true}); } text += decoder.decode(); }
        finally { try { await reader.cancel(); } catch (_) {} check(ticket); }
      } else { text = await response.text(); check(ticket); if (new TextEncoder().encode(text).byteLength > responseBudget) throw fail('protocol'); }
      try { return JSON.parse(text); } catch (_) { throw fail('protocol'); }
    }
    async function submit(kind, paging) {
      if (busy) return 'busy';
      if ((kind === 'withdraw' || paging) && metadataEmail !== email()) { invalidate(); return 'changed'; }
      const ticket = {epoch,email:email()}, observed = selected, after = paging ? next : null;
      let body;
      try { body = bodyFor(kind,paging); check(ticket); }
      catch (_) {
        try { check(ticket); } catch (_) { return 'changed'; }
        options.clearSecrets(); error = messages.input; emit(); return 'invalid';
      }
      controller = new AbortController(); const current = controller;
      busy = true; error = ''; status = kind === 'withdraw' ? 'Comprobando la prueba y el retiro solicitado…' : 'Comprobando la prueba y consultando tus permisos…';
      options.clearSecrets();
      if (kind === 'query') { rows = Object.freeze([]); next = null; selected = null; metadataEmail = null; }
      try {
        emit(); check(ticket);
        const pending = options.fetch(paths[kind],{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body,credentials:'omit',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer',signal:current.signal});
        body = null;
        const response = await pending; check(ticket);
        const data = await decode(response,ticket); check(ticket);
        if (response.status !== 200) {
          const code = data && data.detail && typeof data.detail.code === 'string' ? data.detail.code : '';
          throw Object.assign(fail(code === 'progress_retirement_unconfirmed' ? 'uncertain' : code),{status:response.status});
        }
        if (kind === 'query') {
          const result = metadata(data,after); check(ticket); rows = result.rows; next = result.next; selected = null; metadataEmail = ticket.email;
          status = rows.length ? 'Consulta confirmada. Selecciona un permiso para retirarlo; deberás verificarte de nuevo.' : 'No hay permisos registrados en esta página de tu cuenta.';
        } else {
          const result = withdrawal(data,observed); check(ticket);
          rows = Object.freeze(rows.map(row => row === observed ? result : row)); selected = null;
          status = 'Retiro confirmado. Este permiso ya no autoriza compartir progreso. No se han borrado los registros históricos.';
        }
        check(ticket); busy = false; controller = null; options.clearSecrets(); emit(); check(ticket); return 'confirmed';
      } catch (problem) {
        if (problem.code === 'changed' || epoch !== ticket.epoch || email() !== ticket.email) return 'changed';
        rows = Object.freeze([]); next = null; selected = null; metadataEmail = null; busy = false; controller = null;
        error = errorMessage(problem.code ? problem : fail('transport')); status = 'No se confirma ningún retiro. Hace falta una consulta nueva.';
        options.clearSecrets(); emit(); return 'error';
      } finally { body = null; }
    }
    return Object.freeze({view,invalidate,select,query:() => submit('query',false),more:() => submit('query',true),withdraw:() => submit('withdraw',false)});
  }
  root.RetiroConsentimientos = Object.freeze({create,metadata,withdrawal});
})(typeof window === 'undefined' ? globalThis : window);
