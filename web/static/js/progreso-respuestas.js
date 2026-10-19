/* R25 DTO normalization. Only fixed contracts are accepted; unknown fields fail closed. */
(() => {
  'use strict';
  const invalid=()=>Object.assign(new Error('Los datos recibidos requieren revisión. No se muestran cifras sustitutas.'),{code:'progress_response_unavailable'});
  function object(value){if(!value||typeof value!=='object'||Array.isArray(value))throw invalid();return value;}
  function keys(value,names){object(value);if(Object.keys(value).length!==names.length||names.some(key=>!Object.hasOwn(value,key)))throw invalid();return value;}
  function day(value){try{ProgresoDatos.date(value);}catch{throw invalid();}return value;}
  function uuid(value){if(typeof value!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))throw invalid();return value;}
  function profileId(value){if(typeof value!=='string'||!value.length||value.length>36)throw invalid();return value;}
  function boolean(value){if(typeof value!=='boolean')throw invalid();return value;}
  function version(value,initial=false){if(!Number.isSafeInteger(value)||value<(initial?0:1)||value>2147483647)throw invalid();return value;}
  function instant(value,nullable=false){if(nullable&&value===null)return null;if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,9})?(?:Z|\+00:00)$/.test(value)||!Number.isFinite(Date.parse(value)))throw invalid();day(value.slice(0,10));return value;}
  const metrics=['peso_kg','grasa_corporal_pct','masa_magra_kg'],categoryNames=['weight','body_fat','lean_mass','completion'];
  function categories(input){keys(input,categoryNames);if(categoryNames.some(key=>typeof input[key]!=='boolean')||!categoryNames.some(key=>input[key]))throw invalid();return Object.freeze({...input});}
  function numeric(value,metric,legacy=false){if(value===null)return null;if(typeof value!=='number'||!Number.isFinite(value))throw invalid();if(!legacy&&((metric==='peso_kg'&&(value<20||value>300))||(metric==='grasa_corporal_pct'&&(value<3||value>60))||(metric==='masa_magra_kg'&&(value<=0||value>300))))throw invalid();return value;}
  function unit(value,metric){if(value!==(metric==='grasa_corporal_pct'?'percent':'kg'))throw invalid();return value;}
  function unique(items,key){if(new Set(items.map(key)).size!==items.length)throw invalid();return items;}
  function page(input){keys(input,['items','next_after']);if(!Array.isArray(input.items)||input.items.length>100)throw invalid();return input;}
  function range(from,through,today){try{if(!from||!through)throw invalid();ProgresoDatos.queryRange(from,through,today);}catch{throw invalid();}}
  function bounded(value){try{if(new TextEncoder().encode(JSON.stringify(value)).byteLength>262144)throw invalid();}catch{throw invalid();}return value;}
  function context(input){
    const data=keys(bounded(input),['today','timezone','profiles','capabilities','source_profile_required']);
    day(data.today);if(data.timezone!=='America/Mexico_City'||data.source_profile_required!==true)throw invalid();
    const profiles=keys(data.profiles,['items','next_after']),capabilities=keys(data.capabilities,['record_measurements','manage_consent','share_reciprocally']);
    if(!Array.isArray(profiles.items)||profiles.items.length>100||capabilities.share_reciprocally!==false)throw invalid();
    const seen=new Set(),items=profiles.items.map(value=>{
      const profile=keys(value,['id','display_name','active','can_record']),id=profileId(profile.id);
      if(seen.has(id)||typeof profile.display_name!=='string'||!profile.display_name.trim()||profile.display_name.length>1024)throw invalid();seen.add(id);
      const active=boolean(profile.active),canRecord=boolean(profile.can_record);if(canRecord){uuid(id);if(!active)throw invalid();}
      return Object.freeze({id,displayName:profile.display_name,active,canRecord});
    });
    const nextAfter=profiles.next_after===null?null:profileId(profiles.next_after);if(nextAfter!==null&&!items.length)throw invalid();
    return Object.freeze({today:data.today,timezone:data.timezone,sourceProfileRequired:true,profiles:Object.freeze({items:Object.freeze(items),nextAfter}),capabilities:Object.freeze({recordMeasurements:boolean(capabilities.record_measurements),manageConsent:boolean(capabilities.manage_consent),shareReciprocally:false})});
  }
  function completion(input){
    const data=keys(bounded(input),['today','timezone','from_date','through_date','basis','items']);
    day(data.today);if(data.timezone!=='America/Mexico_City'||data.basis!=='completed_of_registered_snapshots'||!Array.isArray(data.items))throw invalid();
    try{ProgresoDatos.queryRange(data.from_date,data.through_date,data.today);}catch{throw invalid();}
    if(!data.from_date||!data.through_date)throw invalid();const seen=new Set();let previous=null;
    const rows=data.items.map(value=>{
      const item=keys(value,['local_date','registered_snapshots','completed_snapshots','ratio','status']),localDate=day(item.local_date);
      if(seen.has(localDate)||localDate<data.from_date||localDate>data.through_date||(previous!==null&&localDate<=previous))throw invalid();seen.add(localDate);previous=localDate;
      let observed;try{observed=ProgresoDatos.observed(item.completed_snapshots,item.registered_snapshots);}catch{throw invalid();}
      if(item.ratio!==observed.ratio||item.status!==(observed.registered===0?'no_registered_snapshots':'observed'))throw invalid();
      return Object.freeze({localDate,registered:observed.registered,completed:observed.completed,ratio:observed.ratio,status:item.status});
    });
    return Object.freeze({today:data.today,timezone:data.timezone,fromDate:data.from_date,throughDate:data.through_date,rows:Object.freeze(rows)});
  }
  function measurement(input,{today,profile=null,canMutate=false}={}){
    const data=keys(bounded(input),['record_key','legacy_id','version','source_profile_id','source_kind','measured_on','legacy_recording_timestamp','recorded_at','updated_at','withdrawn_at','values','units','verification']);
    const legacy=data.source_kind==='legacy_unverified';if(!legacy&&data.source_kind!=='self_reported')throw invalid();version(data.version);profileId(data.source_profile_id);
    if(profile!==null&&profile!==data.source_profile_id)throw invalid();
    if(legacy){if(data.record_key!==null||!Number.isSafeInteger(data.legacy_id)||data.legacy_id<1||data.measured_on!==null||data.recorded_at!==null||data.updated_at!==null||data.withdrawn_at!==null||data.verification!=='legacy_requires_review')throw invalid();instant(data.legacy_recording_timestamp,true);}
    else{uuid(data.record_key);uuid(data.source_profile_id);day(data.measured_on);if(today){day(today);if(data.measured_on>today)throw invalid();}if(data.legacy_id!==null||data.legacy_recording_timestamp!==null||data.verification!=='self_reported')throw invalid();instant(data.recorded_at);instant(data.updated_at);instant(data.withdrawn_at,true);}
    keys(data.values,metrics);keys(data.units,metrics);const values={};for(const key of metrics){values[key]=numeric(data.values[key],key,legacy);unit(data.units[key],key);}if(!legacy&&!metrics.some(key=>values[key]!==null))throw invalid();
    return Object.freeze({key:legacy?'legacy:'+data.legacy_id:data.record_key,recordKey:data.record_key,legacyId:data.legacy_id,version:data.version,sourceProfileId:data.source_profile_id,sourceKind:data.source_kind,measuredOn:data.measured_on,recordedAt:legacy?data.legacy_recording_timestamp:data.recorded_at,updatedAt:data.updated_at,withdrawn:data.withdrawn_at!==null,values:Object.freeze(values),canWithdraw:!legacy&&canMutate&&data.withdrawn_at===null,canEdit:!legacy&&canMutate&&data.withdrawn_at===null});
  }
  function measurements(input,options){
    const data=keys(bounded(input),['items','next_after','from_date','through_date','timezone']);if(data.timezone!=='America/Mexico_City'||!Array.isArray(data.items)||data.items.length>100)throw invalid();range(data.from_date,data.through_date,options.today);
    const rows=unique(data.items.map(item=>measurement(item,options)),item=>item.key);
    for(const row of rows)if(row.measuredOn!==null&&(row.measuredOn<data.from_date||row.measuredOn>data.through_date))throw invalid();
    const next=data.next_after;if(next!==null&&(typeof next!=='string'||!next.length||next.length>512||!rows.length))throw invalid();
    return Object.freeze({rows:Object.freeze(rows),nextAfter:next,fromDate:data.from_date,throughDate:data.through_date,timezone:data.timezone});
  }
  function event(input){
    const data=keys(input,['id','version','event','protocol','link_version','source_profile_id','categories','from_date','through_date','ongoing','created_at']);uuid(data.id);version(data.version);version(data.link_version);
    if(!['grant','withdraw'].includes(data.event)||data.protocol!=='progress_share_v1')throw invalid();const selected=categories(data.categories);if(data.source_profile_id!==null)uuid(data.source_profile_id);if(categoryNames.slice(0,3).some(key=>selected[key])&&data.source_profile_id===null)throw invalid();
    day(data.from_date);boolean(data.ongoing);if(data.ongoing?data.through_date!==null:!data.through_date||day(data.through_date)<data.from_date)throw invalid();instant(data.created_at);
    return Object.freeze({id:data.id,version:data.version,event:data.event,protocol:data.protocol,linkVersion:data.link_version,sourceProfileId:data.source_profile_id,categories:selected,fromDate:data.from_date,throughDate:data.through_date,ongoing:data.ongoing,createdAt:data.created_at});
  }
  function consents(input){
    const data=page(bounded(input)),rows=unique(data.items.map(value=>{keys(value,['link_id','consent','capabilities']);uuid(value.link_id);keys(value.capabilities,['withdraw']);const consent=event(value.consent),withdraw=boolean(value.capabilities.withdraw);if(withdraw&&consent.event!=='grant')throw invalid();return Object.freeze({linkId:value.link_id,consent,canWithdraw:withdraw});}),item=>item.linkId);
    const next=data.next_after===null?null:uuid(data.next_after);if(next!==null&&(!rows.length||next!==rows.at(-1).linkId))throw invalid();return Object.freeze({rows:Object.freeze(rows),nextAfter:next});
  }
  function consent(input,expectedLink){
    const metadata=Object.hasOwn(object(input),'scope');keys(bounded(input),['link_id','consent','version','effective','capabilities',...(metadata?['scope']:[])]);uuid(input.link_id);if(expectedLink!==undefined&&input.link_id!==expectedLink)throw invalid();
    keys(input.capabilities,['withdraw','grant']);const value=input.consent===null?null:event(input.consent),count=version(input.version,true),withdraw=boolean(input.capabilities.withdraw),grant=boolean(input.capabilities.grant);
    if(value===null?(count!==0||withdraw||input.effective!==false):count!==value.version)throw invalid();
    if(metadata){if(input.scope!=='own_consent_metadata_only'||input.effective!==null||grant||value===null)throw invalid();}else boolean(input.effective);
    if(withdraw&&value?.event!=='grant')throw invalid();if(input.effective===true&&value?.event!=='grant')throw invalid();
    return Object.freeze({linkId:input.link_id,consent:value,version:count,effective:input.effective,metadataOnly:metadata,canWithdraw:withdraw,canGrant:grant});
  }
  function professional(input){
    const data=keys(bounded(input),['items','next_after','direction']);if(data.direction!=='native_professional_history_only'||!Array.isArray(data.items)||data.items.length>100)throw invalid();const rows=unique(data.items.map(item=>measurement(item)),item=>item.key);
    const next=data.next_after===null?null:version(data.next_after);if(next!==null&&!rows.length)throw invalid();return Object.freeze({rows:Object.freeze(rows),nextAfter:next});
  }
  function sharedContext(input,link){
    const data=keys(bounded(input),['link_id','link_version','consent','today','timezone','capabilities']);uuid(data.link_id);if(link!==data.link_id||data.timezone!=='America/Mexico_City')throw invalid();version(data.link_version);day(data.today);keys(data.capabilities,['read_shared_progress']);const canRead=boolean(data.capabilities.read_shared_progress),value=data.consent===null?null:event(data.consent);
    if(canRead&&(value?.event!=='grant'||value.linkVersion!==data.link_version))throw invalid();return Object.freeze({linkId:data.link_id,linkVersion:data.link_version,consent:value,today:data.today,timezone:data.timezone,canRead});
  }
  function shared(input,expected){
    if(!expected||expected.canRead!==true||!expected.consent)throw invalid();
    const data=keys(bounded(input),['link_id','link_version','consent_id','consent_version','from_date','through_date','timezone','measurements','completion','categories','consistency','cached']);
    if(data.link_id!==expected.linkId||data.link_version!==expected.linkVersion||data.consent_id!==expected.consent.id||data.consent_version!==expected.consent.version||data.timezone!=='America/Mexico_City'||data.consistency!=='live_authorized_read'||data.cached!==false)throw invalid();
    range(data.from_date,data.through_date,expected.today);const selected=categories(data.categories);if(categoryNames.some(key=>selected[key]!==expected.consent.categories[key])||data.from_date<expected.consent.fromDate||(expected.consent.throughDate!==null&&data.through_date>expected.consent.throughDate))throw invalid();
    const raw=page(data.measurements),allowed=metrics.filter((_,index)=>selected[categoryNames[index]]),rows=unique(raw.items.map(value=>{
      keys(value,['record_key','version','source_kind','measured_on','recorded_at','values','units']);uuid(value.record_key);version(value.version);day(value.measured_on);instant(value.recorded_at);if(value.source_kind!=='self_reported'||value.measured_on<data.from_date||value.measured_on>data.through_date)throw invalid();object(value.values);object(value.units);const names=Object.keys(value.values);if(!names.length||names.some(key=>!allowed.includes(key))||Object.keys(value.units).length!==names.length||Object.keys(value.units).some(key=>!names.includes(key)))throw invalid();const values={};for(const key of names){values[key]=numeric(value.values[key],key);unit(value.units[key],key);}if(!names.some(key=>values[key]!==null))throw invalid();
      return Object.freeze({key:value.record_key,recordKey:value.record_key,version:value.version,sourceKind:'self_reported',measuredOn:value.measured_on,recordedAt:value.recorded_at,withdrawn:false,values:Object.freeze(values),canWithdraw:false,canEdit:false});
    }),item=>item.key),next=raw.next_after===null?null:uuid(raw.next_after);if(next!==null&&!rows.length)throw invalid();
    keys(data.completion,['basis','items']);const observed=completion({today:expected.today,timezone:data.timezone,from_date:data.from_date,through_date:data.through_date,basis:data.completion.basis,items:data.completion.items});if(!selected.completion&&observed.rows.length)throw invalid();if(!allowed.length&&(rows.length||next!==null))throw invalid();
    return Object.freeze({linkId:data.link_id,linkVersion:data.link_version,consentId:data.consent_id,consentVersion:data.consent_version,fromDate:data.from_date,throughDate:data.through_date,categories:selected,measurements:Object.freeze({rows:Object.freeze(rows),nextAfter:next}),completion:observed});
  }
  window.ProgresoRespuestas=Object.freeze({context,completion,measurement,measurements,consents,consent,professional,sharedContext,shared});
})();
