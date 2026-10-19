/* Bounded, explicit export parts. Export data/cursors never enter browser storage. */
(function () {
  'use strict';
  var section=document.getElementById('personal-data-section');if(!section)return;
  var names=['profiles','plans','measurements','purchases','generation_requests','personal_diary'];
  var cursorNames={profiles:'profile',plans:'plan',measurements:'measurement',purchases:'purchase',generation_requests:'generation',personal_diary:'diary'};
  var uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  var status=document.getElementById('privacy-status'),errorBox=document.getElementById('privacy-error');
  var start=document.getElementById('privacy-start'),next=document.getElementById('privacy-next'),again=document.getElementById('privacy-again'),restart=document.getElementById('privacy-restart');
  var state=null,lastFile=null,busy=false,failed=false,urls=new Map(),pageContext=null,epoch=0,invalid=false;
  var sessionCodes=['session_changed','session_expired','session_storage_error'];
  function changed(){return Object.assign(new Error('La sesión cambió. Vuelve a abrir tus datos desde la cuenta actual.'),{code:'session_changed'});}
  function check(context,ticket){
    if(invalid || ticket!==epoch || !context)throw changed();
    Api.usuario.validarContexto(context);
  }
  function invalidate(error){
    epoch++;invalid=true;pageContext=null;busy=false;discard(true);controls();
    status.textContent='La descarga se descartó porque no se pudo confirmar la sesión.';
    errorBox.textContent=error && error.code==='session_storage_error' ? 'No se pudo verificar el almacenamiento de la sesión. Vuelve a iniciar sesión.' : 'La sesión cambió o no se pudo verificar. Vuelve a abrir tus datos desde la cuenta actual.';
    errorBox.hidden=false;errorBox.focus();
  }
  async function verify(context,ticket){
    try{check(context,ticket);await Api.usuario.verificarContexto(context);check(context,ticket);}
    catch(error){if(ticket===epoch && !invalid)invalidate(error);throw error;}
  }
  function protocol(){throw new Error('No pudimos verificar esta parte. Vuelve a intentarlo; no se preparó un archivo nuevo.');}
  function recordId(value,name){return ['purchases','generation_requests','personal_diary'].includes(name) ? typeof value==='string' && uuid.test(value) : Number.isSafeInteger(value) && value>0;}
  function diaryDate(value){
    if(typeof value!=='string' || !/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
    var parts=value.split('-').map(Number),year=parts[0],month=parts[1],day=parts[2],leap=year%4===0 && (year%100!==0 || year%400===0);
    return year>=1 && month>=1 && month<=12 && day>=1 && day<=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1];
  }
  if(!section.querySelector('[data-export-count="personal_diary"]')){
    var countRow=document.createElement('div'),countLabel=document.createElement('dt'),countValue=document.createElement('dd');
    countLabel.textContent='Días de diario';countValue.dataset.exportCount='personal_diary';countValue.textContent='0';countRow.append(countLabel,countValue);document.getElementById('privacy-counts').append(countRow);
  }
  function controls(){
    if(!invalid && pageContext){try{Api.usuario.validarContexto(pageContext);}catch(error){invalidate(error);return;}}
    var received=state && state.part>0;
    start.hidden=!!received && !state.complete;start.textContent=received ? 'Empezar otra descarga' : failed ? 'Volver a intentar descarga' : 'Descargar mis datos';
    next.hidden=!received || state.complete;next.textContent=failed ? 'Volver a intentar esta parte' : 'Descargar siguiente parte';
    again.hidden=!lastFile;restart.hidden=!received || state.complete;
    [start,next,again,restart].forEach(function(button){button.disabled=busy || invalid || !pageContext;});
    section.setAttribute('aria-busy',String(busy));document.getElementById('privacy-progress').hidden=!busy;
    document.getElementById('privacy-counts').hidden=!received;
    document.getElementById('privacy-content-warning').hidden=!state || state.contentReview===0;
    names.forEach(function(name){section.querySelector('[data-export-count="'+name+'"]').textContent=state ? state.counts[name].toLocaleString('es-MX') : '0';});
    if(!invalid && pageContext){try{Api.usuario.validarContexto(pageContext);}catch(error){invalidate(error);}}
  }
  function release(url){var timer=urls.get(url);if(timer)clearTimeout(timer);try{URL.revokeObjectURL(url);}finally{urls.delete(url);}}
  function discard(revokeNow){state=null;lastFile=null;failed=false;if(revokeNow)urls.forEach(function(_,url){release(url);});}
  function fail(error){failed=true;errorBox.textContent=error.status===422 ? 'No se pudo continuar esta descarga. Empieza una descarga nueva.' : error.message || 'No fue posible preparar esta parte. Vuelve a intentarlo.';errorBox.hidden=false;errorBox.focus();}
  function newState(context){
    var value={id:crypto.randomUUID(),context:context,accountId:context.me.id,startedAt:new Date().toISOString(),part:0,complete:false,contentReview:0,done:{},cursors:{},counts:{},pages:{},seen:{}};
    names.forEach(function(name){value.done[name]=false;value.counts[name]=0;value.pages[name]=0;value.seen[name]=[];});return value;
  }
  function verified(data,expected){
    if(!data || data.format_version!==1 || typeof data.exported_at!=='string' || !Number.isFinite(Date.parse(data.exported_at)) || !data.account || data.account.id!==expected || !Object.prototype.hasOwnProperty.call(data,'personal_subscription') || !Object.prototype.hasOwnProperty.call(data,'canonical_subscription') || !data.scope || data.scope.consistency!=='live_keyset_pages' || data.scope.coverage!=='account_and_persisted_personal_space' || typeof data.scope.personal_space!=='boolean' || typeof data.scope.professional_membership!=='boolean' || !Number.isInteger(data.scope.page_size) || data.scope.page_size<1 || data.scope.page_size>200 || !Array.isArray(data.scope.excluded_categories) || !data.scope.excluded_categories.length || !data.scope.excluded_categories.every(function(value){return typeof value==='string';})){
      if(data && data.account && data.account.id!==expected)throw changed();protocol();
    }
    names.forEach(function(name){
      var collection=data[name];
      if(!collection || !Array.isArray(collection.records) || collection.records.length>data.scope.page_size || !Object.prototype.hasOwnProperty.call(collection,'next_after'))protocol();
      var ids=collection.records.map(function(record){if(!record || !recordId(record.id,name))protocol();return record.id;});
      if(new Set(ids).size!==ids.length)protocol();
      var cursorValues=name==='personal_diary' ? collection.records.map(function(record){if(!diaryDate(record.local_date))protocol();return record.local_date;}) : ids;
      if(name==='personal_diary' && cursorValues.some(function(value,index){return index>0 && value<=cursorValues[index-1];}))protocol();
      if(!data.scope.personal_space && ['profiles','plans','measurements','personal_diary'].includes(name) && ids.length)protocol();
      var after=collection.next_after;
      if(after!==null && (!(name==='personal_diary' ? diaryDate(after) : recordId(after,name)) || !cursorValues.length || after!==cursorValues[cursorValues.length-1]))protocol();
      if(!state.done[name]){
        var previous=state.cursors[cursorNames[name]];
        if(previous!=null && (cursorValues.includes(previous) || ((typeof previous==='number' || name==='personal_diary') && cursorValues.some(function(value){return value<=previous;}))))protocol();
        if(after!==null && (after===previous || state.seen[name].includes(after)))protocol();
      }
      if(name==='plans' && collection.records.some(function(record){return !['structured_copy','unavailable_legacy_content','oversized_legacy_content','content_requires_authorized_review'].includes(record.content_status);}))protocol();
    });
    return data;
  }
  function prepare(data,context,ticket){
    check(context,ticket);
    var updated={...state,part:state.part+1,done:{...state.done},cursors:{...state.cursors},counts:{...state.counts},pages:{...state.pages},seen:{...state.seen}};
    var collections={},manifestCollections={};
    names.forEach(function(name){
      if(state.done[name]){manifestCollections[name]={status:'included_in_previous_parts',pages_prepared:state.pages[name],records_in_this_part:0,records_prepared:state.counts[name]};return;}
      var source=data[name],records=source.records,more=source.next_after!==null,key=cursorNames[name];
      collections[name]={records:records};updated.done[name]=!more;updated.pages[name]+=1;updated.counts[name]+=records.length;
      if(more){updated.cursors[key]=source.next_after;updated.seen[name]=[...state.seen[name].slice(-31),source.next_after];}else delete updated.cursors[key];
      if(name==='plans')updated.contentReview+=records.filter(function(record){return record.content_status!=='structured_copy';}).length;
      manifestCollections[name]={status:more ? 'more_parts_required' : 'finished_in_this_part',collection_page:updated.pages[name],records_in_this_part:records.length,records_prepared:updated.counts[name]};
    });
    updated.complete=names.every(function(name){return updated.done[name];});
    var first=updated.part===1;
    var file={format:'metodobase_personal_export_part',format_version:1,
      manifest:{export_id:state.id,part:updated.part,started_at:state.startedAt,queried_at:data.exported_at,consistency:'live_keyset_pages',coverage:data.scope.coverage,
        all_available_pages_prepared:updated.complete,parts_total:updated.complete ? updated.part : null,requires_parts_from:1,requires_parts_through:updated.part,
        account_and_subscriptions:first ? 'included_in_this_part' : 'included_in_part_1',collections:manifestCollections,plans_requiring_content_review:updated.contentReview,
        note:'Este conjunto contiene sólo el alcance declarado. Las partes son consultas sucesivas, no una copia inmutable. Conserva todas las partes de esta descarga. Los planes con contenido no disponible requieren revisión autorizada.'},
      scope:data.scope,account:first ? data.account : null,personal_subscription:first ? data.personal_subscription : null,canonical_subscription:first ? data.canonical_subscription : null,collections:collections};
    var stamp=state.startedAt.replace(/[-:.]/g,'');
    var bytes=JSON.stringify(file,null,2);check(context,ticket);
    var blob=new Blob([bytes],{type:'application/json;charset=utf-8'});check(context,ticket);
    return {updated:updated,file:{blob:blob,name:'metodobase-datos-personales-'+stamp+'-'+state.id.slice(0,8)+'-parte-'+String(updated.part).padStart(3,'0')+'.json'}};
  }
  function download(file,context,ticket){
    check(context,ticket);
    var url=URL.createObjectURL(file.blob),anchor;urls.set(url,null);
    try{
      check(context,ticket);anchor=document.createElement('a');anchor.href=url;anchor.download=file.name;anchor.hidden=true;
      document.body.appendChild(anchor);check(context,ticket);anchor.click();check(context,ticket);
      urls.set(url,setTimeout(function(){release(url);},2000));
    }catch(error){release(url);throw error;}
    finally{if(anchor)anchor.remove();}
  }
  async function part(fresh){
    if(busy || invalid || !pageContext)return;
    var ticket=epoch,context=pageContext;
    busy=true;failed=false;errorBox.hidden=true;controls();
    status.textContent='Consultando tus datos y preparando una parte…';
    try{
      await verify(context,ticket);check(context,ticket);
      if(fresh || !state){discard(true);check(context,ticket);state=newState(context);}
      var exportId=state.id,accountId=state.accountId,response;
      try{check(context,ticket);response=await Api.usuario.exportarDatos(state.cursors,context);check(context,ticket);}
      catch(error){check(context,ticket);await verify(context,ticket);check(context,ticket);throw error;}
      await verify(context,ticket);check(context,ticket);
      if(!state || state.id!==exportId || state.context!==context)throw changed();
      var data=verified(response,accountId);check(context,ticket);
      var result=prepare(data,context,ticket);check(context,ticket);
      download(result.file,context,ticket);check(context,ticket);state=result.updated;lastFile=result.file;
      status.textContent=state.complete ? 'Se prepararon todas las partes disponibles para este alcance: '+state.part+'. Conserva todos los archivos de esta descarga.' : 'Parte '+state.part+' preparada. Quedan registros; descarga la siguiente parte para continuar.';
      check(context,ticket);
    }catch(error){
      if(ticket!==epoch || invalid)return;
      try{check(context,ticket);}catch(sessionError){invalidate(sessionError);return;}
      if(sessionCodes.includes(error.code)){invalidate(error);return;}
      status.textContent=state && state.part ? (state.part===1 ? 'Se mantiene la parte preparada. ' : 'Se mantienen las '+state.part+' partes preparadas. ')+'La nueva parte no se preparó.' : 'Todavía no se preparó un archivo de esta descarga.';fail(error);
    }finally{if(ticket===epoch && !invalid){busy=false;controls();if(errorBox.hidden)(state && !state.complete ? next : again).focus();}}
  }
  start.addEventListener('click',function(){part(true);});next.addEventListener('click',function(){part(false);});
  restart.addEventListener('click',function(){if(busy || invalid)return;try{check(pageContext,epoch);discard(true);errorBox.hidden=true;status.textContent='Puedes iniciar otra descarga desde la primera parte.';controls();start.focus();}catch(error){invalidate(error);}});
  again.addEventListener('click',async function(){
    if(busy || invalid || !lastFile)return;busy=true;errorBox.hidden=true;controls();
    var ticket=epoch,context=state.context,exportId=state.id,file=lastFile;
    try{await verify(context,ticket);check(context,ticket);if(!state || state.id!==exportId || lastFile!==file)throw changed();download(file,context,ticket);check(context,ticket);status.textContent='Se volvió a preparar la descarga de la parte '+state.part+'. '+(state.complete ? 'Ya se prepararon todas las partes de este alcance.' : 'Quedan registros; descarga la siguiente parte para continuar.');check(context,ticket);}
    catch(error){if(ticket===epoch && !invalid){try{check(context,ticket);}catch(sessionError){invalidate(sessionError);return;}if(sessionCodes.includes(error.code))invalidate(error);else fail(error);}}
    finally{if(ticket===epoch && !invalid){busy=false;controls();}}
  });
  window.addEventListener('storage',function(event){if(event.key==='mb_token' || event.key==='mb_refresh_token' || event.key===null)invalidate(changed());});
  window.addEventListener('metodobase-session-changed',function(event){invalidate({code:event.detail && event.detail.code});});
  window.addEventListener('pagehide',function(){epoch++;invalid=true;pageContext=null;busy=false;discard(true);controls();});
  window.addEventListener('pageshow',function(event){if(event.persisted)invalidate(changed());});
  (async function(){var ticket=epoch;try{
      if(window.SessionIdentity){await SessionIdentity.ready;if(ticket!==epoch || invalid)return;}
      var context=await Api.usuario.contexto();check(context,ticket);pageContext=context;
      status.textContent='Descarga tus datos por partes. El archivo indicará su alcance y contenido.';
      check(context,ticket);
    }catch(error){if(ticket===epoch && !invalid)invalidate(error);}finally{controls();}})();
})();
