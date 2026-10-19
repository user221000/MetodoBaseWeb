/* Explicit provider association. Proofs, credentials and intents live only in this closure. */
(function(root){
  'use strict';
  const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,bearer=/^[A-Za-z0-9_-]{43}$/;
  const bad=()=>Object.assign(new Error('No se pudo comprobar la respuesta.'),{code:'google_link_invalid_response'});
  const changed=()=>Object.assign(new Error('La sesión cambió.'),{code:'session_changed'});
  function keys(value,names){if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).length!==names.length||names.some(name=>!Object.prototype.hasOwnProperty.call(value,name)))throw bad();}
  function timestamp(value){return typeof value==='string'&&value.length<=64&&/^\d{4}-\d\d-\d\dT.+(?:Z|[+-]\d\d:\d\d)$/.test(value)&&Number.isFinite(Date.parse(value));}
  function listing(data,after){
    keys(data,['provider','can_link','items','next_after']);if(data.provider!=='google'||typeof data.can_link!=='boolean'||!Array.isArray(data.items)||data.items.length>20)throw bad();
    let previous=after;const items=data.items.map(item=>{keys(item,['id','version','active','created_at','revoked_at']);
      if(typeof item.id!=='string'||!uuid.test(item.id)||!Number.isSafeInteger(item.version)||item.version<1||item.version>2147483647||typeof item.active!=='boolean'||!timestamp(item.created_at)||(item.revoked_at!==null&&!timestamp(item.revoked_at))||(previous!==null&&item.id<=previous))throw bad();
      previous=item.id;return Object.freeze({...item});});
    if(data.next_after!==null&&(typeof data.next_after!=='string'||!uuid.test(data.next_after)||!items.length||data.next_after!==items[items.length-1].id))throw bad();
    return{items:Object.freeze(items),canLink:data.can_link,next:data.next_after};
  }
  function primary(proof){
    if(!proof||typeof proof.password!=='string'||!proof.password)throw Object.assign(bad(),{code:'google_link_invalid_input'});
    const body={password:proof.password};
    if(proof.method==='totp'&&typeof proof.factor==='string'&&/^\d{6}$/.test(proof.factor))body.code=proof.factor;
    else if(proof.method==='recovery'&&typeof proof.factor==='string'&&/^[A-Za-z0-9_-]{22}$/.test(proof.factor))body.recovery_code=proof.factor;
    else if(proof.method!=='none'||proof.factor)throw Object.assign(bad(),{code:'google_link_invalid_input'});
    return body;
  }
  function bounded(body){if(new TextEncoder().encode(JSON.stringify(body)).length>32768)throw Object.assign(bad(),{code:'google_link_invalid_input'});return body;}
  const messages=Object.freeze({
    google_link_verification_failed:'No se pudo verificar tu contraseña local. Un acceso con Google o una sesión abierta no la sustituyen.',
    google_link_conflict:'El vínculo cambió o no se puede asignar a esta cuenta. Consulta el estado de nuevo antes de otra operación.',
    google_link_intent_unavailable:'La confirmación venció, se usó o pertenece a otro acceso. Se descartó; consulta y prepara un vínculo nuevo explícitamente.',
    google_link_session_version_exhausted:'Esta cuenta necesita revisión antes de cambiar su acceso con Google. No se confirma ningún cambio.',
    mfa_busy:'Hay otra operación en curso. Espera y realiza una consulta nueva antes de continuar.',
    mfa_verification_failed:'No se confirmó el segundo factor. Usa una prueba nueva al preparar otra operación.',
    mfa_primary_reauthentication_required:'Google no confirmó una autenticación suficientemente reciente. No basta con elegir una cuenta. Vuelve a autenticarte con Google y prepara la operación de nuevo; si no ofrece esa verificación, no puedes completar este vínculo por ahora.',
    google_identity_invalid:'No se pudo verificar la autenticación de Google. Se descartó; no se confirmó ningún vínculo.',
    google_link_invalid_input:'Escribe tu contraseña local y una prueba completa del segundo factor, si está activo. Confirma también la selección para desvincular.',
    google_link_invalid_response:'No pudimos comprobar la respuesta. No se confirma ningún cambio. Consulta de nuevo explícitamente antes de otra operación.',
  });
  function notice(error){if(Object.prototype.hasOwnProperty.call(messages,error.code))return messages[error.code];if(error.status===429)return'Hay un límite temporal de intentos. Espera antes de una nueva consulta u operación explícita.';if(error.status===501)return'Google no está configurado para este acceso. No se confirmó ningún vínculo.';if(error.status>=500||!error.status)return'El resultado es incierto; el cambio puede haberse confirmado. No repetiremos la operación ni consultaremos automáticamente. Vuelve a iniciar sesión cuando corresponda y consulta el estado explícitamente.';return'No se pudo confirmar el cambio. Consulta el estado antes de otra operación.';}
  function create(options){
    const api=options.api||Api.googleLink,now=options.now||Date.now;
    let context=null,epoch=0,phase='idle',busy=false,dead=false,closing=false,items=Object.freeze([]),next=null,canLink=false,selected=null,attempt=null,credential=null,credentialUntil=0,intent=null,expires=null,contact=null;
    let message='Consulta los vínculos de la cuenta con la que ya iniciaste sesión.';
    const view=()=>Object.freeze({phase,busy,items,next:next!==null,canLink,selected:selected===null?null:items.indexOf(selected),contact,expires,message});
    const emit=()=>options.onView?.(view());
    function clearProof(){credential=null;credentialUntil=0;attempt=null;intent=null;expires=null;contact=null;options.onClear?.();}
    function clearData(){clearProof();items=Object.freeze([]);next=null;canLink=false;selected=null;}
    function invalidate(){if(closing||phase==='invalidated')return;dead=true;epoch++;busy=false;context=null;phase='invalidated';clearData();message='La sesión o el almacenamiento cambiaron. Se descartó esta vista. Vuelve a abrirla desde la cuenta que quieres gestionar.';emit();}
    function alive(ticket){if(dead||ticket!==epoch)throw changed();}
    function check(ticket=epoch){alive(ticket);if(!context)throw changed();api.check(context);}
    function failure(error,ticket){
      if(dead||ticket!==epoch)return false;
      try{if(context)check(ticket);}catch(_){invalidate();return false;}
      if(['session_changed','session_storage_error','session_expired','mfa_identity_unavailable'].includes(error.code)){invalidate();return false;}
      clearData();if(dead||ticket!==epoch)return false;busy=false;phase='error';message=notice(error);emit();return false;
    }
    async function load(paging=false){
      if(dead||busy)return false;if(paging&&next===null)return false;
      const after=paging?next:null,ticket=++epoch;busy=true;clearData();if(dead||ticket!==epoch)return false;phase='loading';message='Consultando los vínculos de esta cuenta…';emit();
      try{alive(ticket);if(!context){const result=await api.context();alive(ticket);context=result.handle;}check(ticket);
        await api.verify(context);check(ticket);const reply=await api.status(context,after);check(ticket);const parsed=listing(reply,after);check(ticket);
        items=parsed.items;next=parsed.next;canLink=parsed.canLink;busy=false;phase='ready';message=items.length?'Estado consultado. Un vínculo nuevo requiere una verificación y una confirmación explícitas.':'Esta página no contiene vínculos registrados. Puedes preparar uno nuevo si está habilitado.';emit();check(ticket);return true;
      }catch(error){return failure(error,ticket);}
    }
    function cancel(){if(dead||closing)return;epoch++;busy=false;clearData();if(dead)return;phase='idle';message='Pruebas y vista descartadas. Una solicitud ya enviada puede haber finalizado; consulta el estado explícitamente antes de otra operación.';emit();}
    function beginGoogle(){
      if(dead||busy||phase!=='ready'||!canLink)return null;const ticket=++epoch;
      try{check(ticket);clearProof();check(ticket);selected=null;attempt=Object.freeze({});const result=attempt;phase='google';message='Elige la cuenta de Google. Todavía no se ha preparado ni confirmado un vínculo.';emit();check(ticket);return result;}catch(error){failure(error,ticket);return null;}
    }
    function acceptGoogle(value,observed){
      if(dead||busy||phase!=='google'||attempt!==observed)return false;const ticket=epoch;
      try{check(ticket);if(typeof value!=='string'||!value||value.length>30000)throw bad();credential=value;credentialUntil=now()+300000;attempt=null;phase='proof';message='Ahora verifica esta cuenta con su contraseña local y un código nuevo, si usa segundo factor. Google debe haber confirmado una autenticación reciente; elegir una cuenta no lo garantiza.';emit();check(ticket);return true;}catch(error){return failure(error,ticket);}
    }
    async function start(proof){
      if(dead||busy||phase!=='proof'||!credential)return false;const ticket=epoch;let body;
      try{check(ticket);if(now()>=credentialUntil)throw Object.assign(bad(),{code:'mfa_primary_reauthentication_required'});body=bounded({...primary(proof),google_credential:credential});check(ticket);
        busy=true;clearProof();check(ticket);phase='saving';message='Verificando la prueba. El vínculo todavía no está confirmado…';emit();check(ticket);
        const reply=await api.start(body,context);body=null;check(ticket);keys(reply,['intent','expires_at','provider','google_email','confirmation_required']);
        if(!bearer.test(reply.intent)||typeof reply.intent!=='string'||!timestamp(reply.expires_at)||Date.parse(reply.expires_at)<=now()||reply.provider!=='google'||typeof reply.google_email!=='string'||!reply.google_email||reply.google_email.length>320||reply.confirmation_required!==true)throw bad();
        check(ticket);intent=reply.intent;expires=reply.expires_at;contact=reply.google_email;busy=false;phase='confirm';message='Verificación recibida. Comprueba la cuenta de Google mostrada y confirma sólo si quieres vincularla.';emit();check(ticket);return true;
      }catch(error){body=null;return failure(error,ticket);}
    }
    function selectUnlink(index){if(dead||busy||!Number.isSafeInteger(index)||!items[index]||!items[index].active)return false;const ticket=epoch;
      try{check(ticket);clearProof();check(ticket);selected=items[index];phase='unlink';message='Comprueba la selección. Para desvincular se requiere tu contraseña local y un código nuevo, si usas segundo factor.';emit();check(ticket);return true;}catch(error){return failure(error,ticket);}}
    function finish(reply,ticket,unlink){
      check(ticket);keys(reply,unlink?['success','provider','identity_id','version','linked','reauthenticate']:['success','provider','linked','reauthenticate']);
      if(reply.success!==true||reply.provider!=='google'||reply.reauthenticate!==true||reply.linked!==!unlink||(unlink&&(reply.identity_id!==selected.id||!Number.isSafeInteger(reply.version)||reply.version>2147483647||reply.version!==selected.version+1)))throw bad();
      const previous=context;clearData();check(ticket);phase='closing';message='El servidor confirmó el cambio. Cerrando la sesión local…';emit();check(ticket);
      dead=true;epoch++;context=null;busy=false;closing=true;
      try{const closed=api.close(previous);closing=false;api.check(closed);phase='closed';message=unlink?'Desvinculación confirmada. La sesión local se cerró; inicia sesión de nuevo.':'Vínculo confirmado. La sesión local se cerró; inicia sesión de nuevo.';emit();api.check(closed);return true;}
      catch(error){closing=false;if(error.code==='session_changed'){invalidate();return false;}clearData();phase='closed_error';message='El servidor confirmó el cambio, pero no pudimos cerrar la sesión de forma segura. No repitas la operación; vuelve a iniciar sesión y consulta el estado.';emit();return false;}
    }
    async function confirm(){if(dead||busy||phase!=='confirm'||!intent)return false;const ticket=epoch;let body;
      try{check(ticket);if(now()>=Date.parse(expires))throw Object.assign(bad(),{code:'google_link_intent_unavailable'});body={intent,confirm:true};busy=true;clearProof();check(ticket);phase='saving';message='Confirmando el vínculo solicitado…';emit();check(ticket);const reply=await api.confirm(body,context);body=null;check(ticket);return finish(reply,ticket,false);}catch(error){body=null;return failure(error,ticket);}}
    async function unlink(proof,confirmed){if(dead||busy||phase!=='unlink'||!selected)return false;const ticket=epoch;let body;
      try{check(ticket);if(confirmed!==true)throw Object.assign(bad(),{code:'google_link_invalid_input'});body=bounded({...primary(proof),identity_id:selected.id,expected_version:selected.version});check(ticket);busy=true;clearProof();check(ticket);phase='saving';message='Verificando y desvinculando únicamente el vínculo seleccionado…';emit();check(ticket);const reply=await api.unlink(body,context);body=null;check(ticket);return finish(reply,ticket,true);}catch(error){body=null;return failure(error,ticket);}}
    function expire(){if(dead||busy)return;if((phase==='proof'&&now()>=credentialUntil)||(phase==='confirm'&&now()>=Date.parse(expires))){clearData();phase='error';message='La verificación venció. Consulta el estado y prepara una operación nueva; no se repitió ninguna acción.';emit();}}
    return Object.freeze({view,load,more:()=>load(true),beginGoogle,acceptGoogle,start,confirm,selectUnlink,unlink,cancel,invalidate,expire});
  }
  root.GoogleVinculo=Object.freeze({create,listing});
})(typeof window==='undefined'?globalThis:window);
