/* Shared first-party presentation. Public messages never echo backend JSON/errors. */
(() => {
  'use strict';
  const uuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  const version = value => Number.isSafeInteger(value) && value > 0 && value <= 2147483647;
  function node(tag, text, parent) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = String(text);
    parent?.append(item); return item;
  }
  function date(value) {
    if (!value || !Number.isFinite(Date.parse(value))) return 'No disponible';
    return new Date(value).toLocaleString('es-MX');
  }
  function message(error, mutation = false) {
    if (['session_changed','session_expired','session_storage_error','member_context_changed'].includes(error.code)) return 'La sesión o el contexto cambió. Vuelve a abrir esta página desde tu cuenta.';
    if (error.code === 'member_context_requires_review') return 'Este contexto de cuenta requiere revisión. El vínculo no cambia tu rol ni adopta un perfil personal.';
    if (error.code === 'member_invitation_expired') return 'La invitación venció. Solicita al profesional una invitación nueva.';
    if (error.code === 'member_invitation_consumed') return 'Esta invitación ya se utilizó. Consulta tus vínculos para comprobar el resultado.';
    if (error.status === 404) return 'Este recurso no está disponible para tu cuenta. Vuelve a consultar su estado.';
    if (error.status === 403) return 'Tu cuenta no tiene permiso para esta acción.';
    if (error.status === 429) return 'Se alcanzó el límite de consultas o acciones. Espera antes de volver a intentar.';
    if (['member_version_conflict','member_link_conflict','member_request_key_conflict','member_operation_busy'].includes(error.code)) return 'El estado cambió o hay otra operación en curso. Consulta el estado antes de confirmar otra acción.';
    if (mutation) return 'No se pudo confirmar el resultado. Consulta el estado antes de repetir o preparar otra acción. No se enviará nada automáticamente.';
    return 'No se pudo completar la consulta. Puedes volver a intentar.';
  }
  function page(data) {
    if (!data || !Array.isArray(data.items) || data.items.length > 100 ||
        !(data.next_after === null || uuid(data.next_after))) throw new Error('Invalid resource page');
    return data;
  }
  function setup(options) {
    const status = document.getElementById(options.status), error = document.getElementById(options.error);
    const urls = new Set(); let busy = false;
    function releaseDownloads() { for (const url of urls) URL.revokeObjectURL(url); urls.clear(); }
    const context = MemberLinkContext.create({onInvalidated:() => {
      releaseDownloads(); options.clear();
      document.querySelectorAll('button,input,select').forEach(item => { item.disabled = true; });
      status.textContent = 'La sesión cambió. Vuelve a abrir esta página desde tu cuenta.';
      error.hidden = true; busy = false;
    }});
    async function run(task, mutation = false) {
      if (busy || !context.active) return;
      const disabled = new Map();
      try {
        context.check(); busy = true; error.hidden = true;
        document.querySelectorAll('button,input,select').forEach(item => { disabled.set(item,item.disabled); item.disabled = true; });
        context.check();
        await task(); context.check();
      } catch (reason) {
        if (!context.active) return;
        try { context.check(); } catch { return; }
        error.textContent = message(reason,mutation); error.hidden = false; error.focus();
      } finally {
        if (context.active) {
          try { context.check(); for (const [item,value] of disabled) item.disabled = value; options.controls?.(); context.check(); } catch {}
        }
        busy = false;
      }
    }
    function download(blob) {
      context.check(); const url = URL.createObjectURL(blob); urls.add(url);
      try {
        context.check(); const anchor = node('a'); anchor.href = url; anchor.download = 'plan_compartido.pdf';
        document.body.append(anchor); context.check(); anchor.click(); anchor.remove(); context.check();
        status.textContent = 'Se inició la descarga de esta publicación. Comprueba el archivo en tu navegador.';
      } finally { setTimeout(() => { URL.revokeObjectURL(url); urls.delete(url); },30000); }
    }
    return {context,run,download,releaseDownloads, get busy(){return busy;}, status:text => {context.check();status.textContent=text;}, clearError:()=>{error.hidden=true;}};
  }
  window.VinculosUI = Object.freeze({node,date,message,page,setup,uuid,version});
})();
