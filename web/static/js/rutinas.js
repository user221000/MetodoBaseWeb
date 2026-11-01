/* Account-authorized PPL examples. Requirements, calendar and timer live in RAM. */
(function(root){
  'use strict';
  const ids=['push','pull','legs'],durations=[60,90,120,180],frequencies=[3,4,5,6];
  const activities=['nula','leve','normal','moderada','intensa'],experiences=['inicial','intermedio','avanzado'];
  const equipmentKeys=['machine','cable','dumbbell','barbell','bench','bodyweight'];
  const basicEquipment=['barbell','bench','dumbbell','bodyweight'];
  const defaultDays={3:[0,2,4],4:[0,1,3,4],5:[0,1,2,3,4],6:[0,1,2,3,4,5]};
  const invalid=()=>Object.assign(Error('No pudimos validar los datos de rutinas.'),{code:'routine_invalid_response'});
  const text=value=>typeof value==='string'&&value.length>0&&value.length<=1000;
  const list=(value,min,max)=>Array.isArray(value)&&value.length>=min&&value.length<=max;
  const identifier=value=>typeof value==='string'&&value.length<=100&&/^[a-z]+(?:-[a-z]+)*$/.test(value);
  const clientIdentifier=value=>typeof value==='string'&&value.length>=1&&value.length<=36;
  const machineIdentifier=value=>typeof value==='string'&&/^[a-z][a-z0-9-]{0,63}$/.test(value);
  const sameIds=(left,right)=>JSON.stringify([...left].sort())===JSON.stringify([...right].sort());
  function validateInventoryMeta(value){
    if(!value||typeof value.configured!=='boolean'||!Number.isSafeInteger(value.revision)||value.revision<0||value.revision>2147483647||!list(value.machine_ids,0,128)||!value.machine_ids.every(machineIdentifier)||new Set(value.machine_ids).size!==value.machine_ids.length||value.configured&&value.revision<1||!value.configured&&(value.revision!==0||value.machine_ids.length!==0))throw invalid();
    return value;
  }
  function validateInventory(value){
    validateInventoryMeta(value);
    if(value.version!==1||value.scope!=='gym'||typeof value.can_edit!=='boolean'||!list(value.machines,1,128)||!list(value.base_equipment,4,4)||new Set(value.base_equipment).size!==4||!value.base_equipment.every(key=>basicEquipment.includes(key))||!list(value.effective_equipment,4,6)||!value.effective_equipment.every(key=>equipmentKeys.includes(key))||new Set(value.effective_equipment).size!==value.effective_equipment.length||!basicEquipment.every(key=>value.effective_equipment.includes(key)))throw invalid();
    const known=new Set();for(const machine of value.machines){if(!machineIdentifier(machine.id)||known.has(machine.id)||!text(machine.label)||!text(machine.group))throw invalid();known.add(machine.id);}
      if(!value.machine_ids.every(key=>known.has(key)))throw invalid();
    return value;
  }
  function validateExercise(exercise){
    const sets=exercise?.sets,unit=exercise?.repetition_unit===undefined?'repetitions':exercise.repetition_unit;
    if(!identifier(exercise?.id)||!text(exercise.name)||!Number.isInteger(sets?.minimum)||!Number.isInteger(sets.maximum)||sets.minimum<1||sets.maximum>4||sets.minimum>sets.maximum||!text(exercise.repetitions)||!['seconds','repetitions'].includes(unit)||!durations.includes(exercise.rest_seconds)||!list(exercise.equipment,1,4)||!exercise.equipment.every(text)||!list(exercise.cues,2,3)||!exercise.cues.every(text))throw invalid();
    if(!text(exercise.alternative?.name)||!text(exercise.alternative.cue)||!list(exercise.alternative.equipment,1,4)||!exercise.alternative.equipment.every(text))throw invalid();
    return exercise;
  }
  function formatDose(exercise){
    const perSide=/\s+por lado$/.test(exercise.repetitions),amount=exercise.repetitions.replace(/\s+por lado$/,'');
    return amount+(exercise.repetition_unit==='seconds'?' s':' repeticiones')+(perSide?' por lado':'');
  }
  function normalizeDeclaredRequirements(value){
    const keys=['activity_level','experience','goal','equipment','exercises_per_session','days_per_week','session_minutes','variant','excluded_exercises'];
    if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).length!==keys.length||!keys.every(key=>Object.hasOwn(value,key)))throw invalid();
    if(!activities.includes(value.activity_level)||!experiences.includes(value.experience)||!['fuerza_general','hipertrofia'].includes(value.goal)||![6,7,8].includes(value.exercises_per_session)||!frequencies.includes(value.days_per_week)||![45,60,75,90].includes(value.session_minutes)||!Number.isInteger(value.variant)||value.variant<0||value.variant>9)throw invalid();
    if(!list(value.equipment,1,6)||!value.equipment.every(key=>equipmentKeys.includes(key))||new Set(value.equipment).size!==value.equipment.length||!list(value.excluded_exercises,0,100)||!value.excluded_exercises.every(identifier)||new Set(value.excluded_exercises).size!==value.excluded_exercises.length)throw invalid();
    return{activity_level:value.activity_level==='normal'?'moderada':value.activity_level,experience:value.experience,goal:value.goal,equipment:equipmentKeys.filter(key=>value.equipment.includes(key)),exercises_per_session:value.exercises_per_session,days_per_week:value.days_per_week,session_minutes:value.session_minutes,variant:value.variant,excluded_exercises:[...value.excluded_exercises].sort()};
  }
  function validate(value,scope){
    if(value?.version!==1||value.scope!==scope||!value.program||value.program.id!=='ppl-basico-v1')throw invalid();
    const p=value.program;
    const pendingGym=scope==='gym'&&p.requires_generation===true&&p.generated===false;
    if(p.requires_generation===true&&!pendingGym)throw invalid();
    for(const key of ['title','audience','summary','starting_point','guideline_note'])if(!text(p[key]))throw invalid();
    if(!list(p.warmup,1,4)||!list(p.cautions,1,4)||![...p.warmup,...p.cautions].every(text))throw invalid();
    const schedule=p.schedule;
    if(!frequencies.includes(schedule?.sessions_per_week)||schedule.nonconsecutive!==false||schedule.minimum_rest_days!==1||schedule.rotation!=='continuous'||!list(schedule.available_sessions,4,4)||!schedule.available_sessions.every((n,i)=>n===frequencies[i])||!list(schedule.cycle,3,3)||!schedule.cycle.every((id,i)=>id===ids[i])||!list(schedule.days,7,7)||!schedule.days.every(text)||!text(schedule.note)||!validWeek(schedule.default_days,schedule.sessions_per_week))throw invalid();
    if(!list(p.sessions,3,3))throw invalid();
    const exerciseIds=new Set();
    p.sessions.forEach((session,index)=>{
      if(session.id!==ids[index]||!['name','label','focus','description'].every(key=>text(session[key]))||!(pendingGym?list(session.exercises,0,0):list(session.exercises,6,8)))throw invalid();
      if(session.estimated_minutes!==undefined&&(!Number.isInteger(session.estimated_minutes)||session.estimated_minutes<1||session.estimated_minutes>240))throw invalid();
      session.exercises.forEach(exercise=>{validateExercise(exercise);if(exerciseIds.has(exercise.id))throw invalid();exerciseIds.add(exercise.id);});
    });
    if(!list(p.sources,4,8)||p.sources.some(source=>!text(source.label)||!text(source.url)||!/^https:\/\/(?:acsm\.org|www\.cdc\.gov|www\.betterhealth\.vic\.gov\.au|www\.nasm\.org|www\.nsca\.com)\//.test(source.url)))throw invalid();
    if(p.duration_basis!==undefined&&!text(p.duration_basis))throw invalid();
    if(pendingGym)validateInventoryMeta(p.inventory);
    return p;
  }
  function validWeek(days,frequency=Array.isArray(days)?days.length:0){
    return frequencies.includes(frequency)&&list(days,frequency,frequency)&&days.every(day=>Number.isInteger(day)&&day>=0&&day<=6)&&new Set(days).size===frequency;
  }
  function cycleLength(days){return validWeek(days)?(days.length%ids.length===0?1:3):0;}
  function week(days,labels,cycleWeek=1){
    if(!validWeek(days)||!list(labels,7,7)||!labels.every(text)||!Number.isInteger(cycleWeek)||cycleWeek<1||cycleWeek>cycleLength(days))return null;
    const offset=(cycleWeek-1)*days.length;
    return [...days].sort((a,b)=>a-b).map((day,index)=>({day,label:labels[day],session:ids[(offset+index)%ids.length]}));
  }
  function createTimer(now=()=>performance.now()){
    let duration=90,remaining=90,end=null;
    function read(){if(end!==null){remaining=Math.max(0,Math.ceil((end-now())/1000));if(remaining===0)end=null;}return{duration,remaining,running:end!==null};}
    return Object.freeze({read,reset(seconds=duration){if(!durations.includes(seconds))throw RangeError('Unsupported rest duration');duration=remaining=seconds;end=null;return read();},toggle(){const state=read();if(state.running){end=null;}else{if(remaining===0)remaining=duration;end=now()+remaining*1000;}return read();}});
  }
  async function routineRequest(api,scope,path,method='GET',body=undefined,fetcher=root.fetch.bind(root)){
    if(!['gym','personal'].includes(scope)||!/^\/api\/rutinas\/(?:catalogo|ejercicios|generar|requisitos|clientes|equipamiento)\?context=(?:gym|personal)(?:&|$)/.test(path))throw invalid();
    await api.session.ready;
    const context=api.session.capture(),token=api.getToken();api.session.check(context);
    if(!token)throw Object.assign(Error('Inicia sesión para consultar las rutinas.'),{status:401});
    const options={method,headers:{Accept:'application/json',Authorization:'Bearer '+token},credentials:'omit',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'};
    if(body!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
    const response=await fetcher(path,options);api.session.check(context);
    if(response.status===401)api.session.rejectUnauthorized(context,token);
    const raw=await response.text();api.session.check(context);
    if(new TextEncoder().encode(raw).byteLength>524288)throw invalid();
    let value;try{value=JSON.parse(raw);}catch{throw invalid();}
    if(!response.ok){const detail=value?.detail;throw Object.assign(Error(text(detail?.message)?detail.message:'No pudimos preparar esta rutina. Revisa tus opciones.'),{status:response.status,code:detail?.code});}
    return value;
  }
  async function readCatalog(api,scope,fetcher=root.fetch.bind(root)){
    return validate(await routineRequest(api,scope,'/api/rutinas/catalogo?context='+scope,'GET',undefined,fetcher),scope);
  }
  async function readInventory(api,fetcher=root.fetch.bind(root)){
    return validateInventory(await routineRequest(api,'gym','/api/rutinas/equipamiento?context=gym','GET',undefined,fetcher));
  }
  async function readExerciseCatalog(api,scope,fetcher=root.fetch.bind(root)){
    const value=await routineRequest(api,scope,'/api/rutinas/ejercicios?context='+scope,'GET',undefined,fetcher);
    if(value?.version!==1||value.scope!==scope||!list(value.exercises,18,300))throw invalid();
    const snapshot=scope==='gym'?validateInventoryMeta(value.inventory):null;
    const seen=new Set();
    for(const exercise of value.exercises){
      validateExercise(exercise);
      if(seen.has(exercise.id)||!ids.includes(exercise.session)||!list(exercise.equipment_keys,1,6)||!exercise.equipment_keys.every(key=>equipmentKeys.includes(key)))throw invalid();
      if(snapshot&&(!list(exercise.required_machine_ids,0,20)||!exercise.required_machine_ids.every(machineIdentifier)||typeof exercise.available_in_inventory!=='boolean'||exercise.available_in_inventory!==exercise.required_machine_ids.every(key=>snapshot.machine_ids.includes(key))))throw invalid();
      seen.add(exercise.id);
    }
    return value;
  }
  async function readExercises(api,scope,fetcher=root.fetch.bind(root)){
    return(await readExerciseCatalog(api,scope,fetcher)).exercises;
  }
  async function generateRoutine(api,scope,requirements,fetcher=root.fetch.bind(root)){
    if(!requirements||typeof requirements!=='object'||Array.isArray(requirements))throw invalid();
    const declared={...requirements},revision=declared.expected_inventory_revision;delete declared.expected_inventory_revision;
    if(scope==='gym'&&(!Number.isSafeInteger(revision)||revision<0||revision>2147483647)||scope==='personal'&&Object.hasOwn(requirements,'expected_inventory_revision'))throw invalid();
    const expected=normalizeDeclaredRequirements(declared);
    const p=validate(await routineRequest(api,scope,'/api/rutinas/generar?context='+scope,'POST',requirements,fetcher),scope);
    if(p.generated!==true||JSON.stringify(normalizeDeclaredRequirements(p.requirements))!==JSON.stringify(expected)||p.schedule.sessions_per_week!==expected.days_per_week||!Number.isInteger(p.catalog_count)||p.catalog_count<18||p.catalog_count>300)throw invalid();
    const snapshot=scope==='gym'?validateInventoryMeta(p.inventory):null;
    if(snapshot&&snapshot.revision!==revision)throw invalid();
    for(const session of p.sessions){
      if(session.exercises.length!==expected.exercises_per_session||!Number.isInteger(session.estimated_minutes)||session.estimated_minutes>expected.session_minutes)throw invalid();
      for(const exercise of session.exercises)if(exercise.session!==session.id||!list(exercise.equipment_keys,1,6)||!exercise.equipment_keys.every(key=>expected.equipment.includes(key))||!experiences.includes(exercise.experience_min)||experiences.indexOf(exercise.experience_min)>experiences.indexOf(expected.experience)||expected.excluded_exercises.includes(exercise.id))throw invalid();
      if(snapshot)for(const exercise of session.exercises)if(!list(exercise.required_machine_ids,0,20)||!exercise.required_machine_ids.every(key=>snapshot.machine_ids.includes(key)))throw invalid();
    }
    return p;
  }
  async function readRequirements(api,scope,clientId,fetcher=root.fetch.bind(root)){
    if(scope==='gym'&&!clientIdentifier(clientId)||scope==='personal'&&clientId!==undefined)throw invalid();
    const path='/api/rutinas/requisitos?context='+scope+(scope==='gym'?'&client_id='+encodeURIComponent(clientId):'');
    const value=await routineRequest(api,scope,path,'GET',undefined,fetcher);
    if(value?.version!==1||value.scope!==scope||typeof value.available!=='boolean'||value.source!==(scope==='gym'?'client':'personal')||!value.requirements||!(value.requirements.activity_level===null||activities.includes(value.requirements.activity_level)))throw invalid();
    return value;
  }
  async function readClients(api,query='',offset=0,fetcher=root.fetch.bind(root)){
    if(typeof query!=='string'||query.length>80||!Number.isInteger(offset)||offset<0||offset>100000)throw invalid();
    const path='/api/rutinas/clientes?context=gym&q='+encodeURIComponent(query)+'&limit=30&offset='+offset;
    const value=await routineRequest(api,'gym',path,'GET',undefined,fetcher);
    if(value?.version!==1||value.scope!=='gym'||!list(value.clients,0,30)||typeof value.has_more!=='boolean'||value.offset!==offset||value.limit!==30)throw invalid();
    const seen=new Set();
    for(const row of value.clients){if(!clientIdentifier(row.id)||!text(row.name)||seen.has(row.id))throw invalid();seen.add(row.id);}
    return value;
  }
  function mount(panel,api=(typeof Api!=='undefined'?Api:undefined)){
    const get=name=>panel.querySelector('[data-routine-'+name+']');
    const put=(parent,tag,value,className)=>{const node=document.createElement(tag);if(value!==undefined)node.textContent=value;if(className)node.className=className;parent.append(node);return node;};
    const scope=panel.dataset.scope,timer=createTimer();
    let program=null,selected=[0,2,4],frequency=3,cycleWeek=1,epoch=0,dead=false,interval=null,printed=[];
    let dirty=false,busy=false,variant=0,generationEpoch=0,profileEpoch=0,libraryEpoch=0,clientEpoch=0,clientOffset=0,clientQuery='';
    let library=[],clients=[],excluded=new Set(),inventory=null,inventoryBusy=false,inventoryEpoch=0;
    function stop(){if(interval!==null)root.clearInterval(interval);interval=null;}
    function clock(){const s=timer.read();get('clock').textContent=String(Math.floor(s.remaining/60)).padStart(2,'0')+':'+String(s.remaining%60).padStart(2,'0');get('timer-start').textContent=s.running?'Pausar':s.remaining===0?'Iniciar de nuevo':'Iniciar';if(!s.running&&interval!==null){stop();get('timer-status').textContent='Descanso terminado. Continúa cuando te sientas preparado.';}}
    function resetTimer(seconds){stop();timer.reset(seconds);get('rest').value=String(seconds);clock();get('timer-status').textContent='Temporizador reiniciado. No se registra actividad.';}
    function invalidate(){
      if(dead)return;dead=true;epoch++;generationEpoch++;profileEpoch++;libraryEpoch++;clientEpoch++;inventoryEpoch++;stop();timer.reset();
      program=null;selected=[];library=[];clients=[];excluded.clear();inventory=null;frequency=3;cycleWeek=1;
      get('content').hidden=true;get('sessions').replaceChildren();get('week-summary').replaceChildren();get('library-list').replaceChildren();get('client-select').replaceChildren();get('client-query').value='';get('profile-status').textContent='';
      get('stamp-count').textContent='3';get('stamp').setAttribute('aria-label','3 días de entrenamiento a elegir');
      get('inventory-summary').textContent='';get('inventory-status').textContent='La sesión cambió.';get('inventory-reload').disabled=true;
      get('status').textContent='La sesión cambió. Abre de nuevo las rutinas desde tu cuenta.';get('recovery').hidden=false;get('reload').disabled=true;
    }
    function markDirty(){
      if(!program||dead)return;dirty=true;variant=0;generationEpoch++;profileEpoch++;busy=false;stop();
      get('generate').disabled=scope==='gym'&&(!inventory||inventoryBusy);get('another').disabled=true;get('sessions').hidden=true;get('session-nav').hidden=true;get('preparation').hidden=true;
      get('summary').textContent='Genera la rutina para aplicar los requisitos elegidos.';
      get('generator-status').textContent='Cambiaste los requisitos. Genera una rutina para aplicar los cambios.';drawWeek();
    }
    function drawWeek(){
      get('week-summary').replaceChildren();
      const valid=validWeek(selected,frequency),rows=!dirty&&valid?week(selected,program.schedule.days,cycleWeek):null;
      get('print').disabled=!rows||busy;get('stamp-count').textContent=String(frequency);get('stamp').setAttribute('aria-label',frequency+' días de entrenamiento a elegir');
      get('cycle-controls').hidden=![4,5].includes(frequency);get('cycle-week').value=String(cycleWeek);
      get('calendar-title').textContent=rows?([4,5].includes(frequency)?'Semana '+cycleWeek+' de 3':'Tu semana'):'Tu calendario';
      get('week-status').textContent=dirty?'Genera la rutina con los requisitos elegidos para ver su calendario.':rows?frequency+' días de entrenamiento · '+(7-frequency)+' de descanso. Puedes elegir días seguidos.':selected.length===7?'Deja al menos un día de descanso. Quita '+(7-frequency)+' día'+(7-frequency===1?'':'s')+'.':selected.length<frequency?'Te falta elegir '+(frequency-selected.length)+' día'+(frequency-selected.length===1?'':'s')+'.':'Quita '+(selected.length-frequency)+' día'+(selected.length-frequency===1?'':'s')+' para entrenar '+frequency+'.';
      get('cycle-note').textContent=rows&&[4,5].includes(frequency)?'Continúa el ciclo entre semanas. La semana '+(cycleWeek===3?1:cycleWeek+1)+' empieza con '+program.sessions[(cycleWeek*frequency)%ids.length].name+'. Repite las tres semanas.':rows?'Push → Pull → Legs. Esta distribución se repite cada semana.':'El calendario aparecerá cuando completes la selección y generes tu rutina.';
      if(rows)for(let day=0;day<7;day++){
        const row=rows.find(item=>item.day===day),item=put(get('week-summary'),'li',undefined,row?'routines-training-day':'routines-rest-day');put(item,'strong',program.schedule.days[day]);
        if(row){const session=program.sessions.find(value=>value.id===row.session),link=put(item,'a',session.name+' · '+session.label);link.href='#routine-'+session.id;}else put(item,'span','Descanso');
      }
    }
    function applyRequirements(p){
      const r=p.requirements;if(!r||typeof r!=='object')return;
      if(activities.includes(r.activity_level))get('activity').value=r.activity_level;
      if(experiences.includes(r.experience))get('experience').value=r.experience;
      if(['fuerza_general','hipertrofia'].includes(r.goal))get('goal').value=r.goal;
      if([6,7,8].includes(r.exercises_per_session))get('exercise-count').value=String(r.exercises_per_session);
      if([45,60,75,90].includes(r.session_minutes))get('session-minutes').value=String(r.session_minutes);
      if(list(r.equipment,1,6)&&r.equipment.every(key=>equipmentKeys.includes(key)))for(const input of get('equipment').querySelectorAll('input'))input.checked=r.equipment.includes(input.value);
    }
    function renderSessions(p){
      get('sessions').replaceChildren();get('session-nav').replaceChildren();
      p.sessions.forEach((session,index)=>{
        const link=put(get('session-nav'),'a');link.href='#routine-'+session.id;put(link,'span','0'+(index+1));put(link,'strong',session.name+' · '+session.label);
        const section=put(get('sessions'),'section',undefined,'routines-session');section.id='routine-'+session.id;section.setAttribute('aria-labelledby',section.id+'-title');
        const heading=put(section,'div',undefined,'routines-session-heading');put(heading,'span','0'+(index+1),'routines-session-number');const headingText=put(heading,'div'),title=put(headingText,'h2',session.name);title.id=section.id+'-title';put(title,'span',session.label);put(headingText,'p',session.focus);
        put(section,'p',session.description,'routines-session-description');
        if(session.estimated_minutes!==undefined)put(section,'p',session.exercises.length+' ejercicios · '+session.estimated_minutes+' min estimados','routines-duration');
        session.exercises.forEach(exercise=>{
          const details=put(section,'details',undefined,'routines-exercise'),summary=put(details,'summary');put(summary,'h3',exercise.name);
          const sets=exercise.sets.minimum===exercise.sets.maximum?String(exercise.sets.minimum):exercise.sets.minimum+'–'+exercise.sets.maximum;
          put(summary,'span',sets+(exercise.sets.maximum===1?' serie':' series')+' · '+formatDose(exercise)+' · '+exercise.rest_seconds+' s de descanso','routines-prescription');
          const body=put(details,'div',undefined,'routines-exercise-body');put(body,'p','Equipo: '+exercise.equipment.join(' · '));const cues=put(body,'ol');exercise.cues.forEach(cue=>put(cues,'li',cue));
          const alternative=put(body,'div',undefined,'routines-alternative');put(alternative,'strong','Alternativa · '+exercise.alternative.name);put(alternative,'p',exercise.alternative.equipment.join(' · '));put(alternative,'p',exercise.alternative.cue);
          const rest=put(body,'button','Preparar descanso de '+exercise.rest_seconds+' s','routines-button routines-button-secondary');rest.type='button';rest.addEventListener('click',()=>{resetTimer(exercise.rest_seconds);get('timer-status').textContent='Descanso preparado para '+exercise.name+'. Pulsa Iniciar cuando quieras.';get('timer-start').focus();});
        });
      });
    }
    function draw(p,keepSelection=false){
      const previous=[...selected];program=p;frequency=p.schedule.sessions_per_week;cycleWeek=1;
      selected=keepSelection&&validWeek(previous,frequency)?previous:[...p.schedule.default_days];get('frequency').value=String(frequency);applyRequirements(p);
      for(const[key,value]of[['audience',p.audience],['summary',p.summary],['starting',p.starting_point],['guideline',p.guideline_note],['schedule-note',p.schedule.note]])get(key).textContent=value;
      for(const[key,values]of[['warmup',p.warmup],['cautions',p.cautions]]){get(key).replaceChildren();for(const value of values)put(get(key),'li',value);}
      get('days').replaceChildren();
      p.schedule.days.forEach((day,index)=>{const label=put(get('days'),'label',undefined,'routines-day'),input=put(label,'input');input.type='checkbox';input.value=String(index);input.checked=selected.includes(index);input.setAttribute('aria-label',day);put(label,'span',day.slice(0,3));input.addEventListener('change',()=>{selected=Array.from(get('days').querySelectorAll('input:checked'),el=>Number(el.value));cycleWeek=1;drawWeek();});});
      dirty=false;busy=false;renderSessions(p);get('sessions').hidden=false;get('session-nav').hidden=false;get('preparation').hidden=false;drawWeek();
      get('sources').replaceChildren();for(const source of p.sources){const li=put(get('sources'),'li'),a=put(li,'a',source.label);a.href=source.url;a.rel='noreferrer';}
      get('duration-basis').textContent=p.duration_basis||'El tiempo es orientativo; incluye preparación y descansos.';
      get('library-count').textContent=Number.isInteger(p.catalog_count)?String(p.catalog_count):'—';
      get('another').disabled=false;resetTimer(90);get('content').hidden=false;
    }
    function collectRequirements(nextVariant){
      if(scope==='gym'&&(!inventory||inventoryBusy))throw Object.assign(Error('Actualiza el inventario del gimnasio antes de generar.'),{status:422});
      const equipment=scope==='gym'?equipmentKeys.filter(key=>inventory.effective_equipment.includes(key)):Array.from(get('equipment').querySelectorAll('input:checked'),input=>input.value);
      if(!equipment.length)throw Object.assign(Error('Elige al menos un tipo de equipo disponible.'),{status:422});
      if(!validWeek(selected,frequency))throw Object.assign(Error('Completa los '+frequency+' días de entrenamiento antes de generar.'),{status:422});
      const result={activity_level:get('activity').value,experience:get('experience').value,goal:get('goal').value,equipment,exercises_per_session:Number(get('exercise-count').value),days_per_week:frequency,session_minutes:Number(get('session-minutes').value),variant:nextVariant,excluded_exercises:[...excluded].sort()};
      if(scope==='gym')result.expected_inventory_revision=inventory.revision;
      return result;
    }
    async function generate(nextVariant=0,alternate=false){
      if(dead||busy||!program)return;let requirements;
      try{requirements=collectRequirements(nextVariant);}catch(error){get('generator-status').textContent=error.message;return;}
      const signature=p=>p.sessions.map(session=>session.id+':'+session.exercises.map(exercise=>exercise.id).sort().join(',')).join('|');
      const previous=signature(program),ticket=++generationEpoch,stamp=JSON.stringify(requirements);busy=true;get('generate').disabled=true;get('another').disabled=true;get('print').disabled=true;get('generator-status').textContent='Preparando tus sesiones Push / Pull / Legs…';
      try{
        const p=await generateRoutine(api,scope,requirements);
        if(dead||ticket!==generationEpoch||stamp!==JSON.stringify(collectRequirements(nextVariant)))return;
        if(scope==='gym'&&(!inventory||p.inventory.configured!==inventory.configured||!sameIds(p.inventory.machine_ids,inventory.machine_ids)))throw invalid();
        const repeated=alternate&&previous===signature(p);variant=nextVariant;draw(p,true);get('generator-status').textContent=repeated?'La combinación coincide con la anterior. Amplía el equipo o revisa las exclusiones para tener más opciones.':'Rutina preparada · '+p.sessions[0].exercises.length+' ejercicios por sesión · combinación '+(variant+1)+'. Puedes imprimirla; no se ha guardado actividad.';
      }catch(error){if(dead||ticket!==generationEpoch)return;dirty=true;get('sessions').hidden=true;get('session-nav').hidden=true;if(scope==='gym'&&error.status===409)staleInventory();get('generator-status').textContent=error.status===401?'Vuelve a iniciar sesión para generar tu rutina.':error.status===403?'No puedes preparar rutinas desde este espacio.':scope==='gym'&&error.status===409?'El inventario del gimnasio cambió. Actualízalo y vuelve a generar.':text(error.message)&&error.status===422?error.message:'No pudimos preparar la rutina. Revisa tus opciones y vuelve a intentarlo.';}
      finally{if(!dead&&ticket===generationEpoch){busy=false;get('generate').disabled=scope==='gym'&&(!inventory||inventoryBusy);get('another').disabled=dirty;drawWeek();}}
    }
    function showInventory(value){
      const names=value.machine_ids.map(key=>value.machines.find(machine=>machine.id===key).label);
      get('inventory-status').textContent=value.configured?(names.length?'Inventario guardado · '+names.length+' máquinas disponibles.':'Inventario guardado · sólo equipo básico.'):'El dueño aún no ha guardado las máquinas. Por ahora se usará sólo el equipo básico.';
      get('inventory-summary').textContent=names.length?names.slice(0,4).join(' · ')+(names.length>4?' · +'+(names.length-4)+' más':''):'Barras, discos, bancos y mancuernas disponibles.';
      get('inventory-link').textContent=value.can_edit?'Configurar máquinas':'Ver máquinas del gimnasio';
    }
    function staleInventory(){
      inventory=null;library=[];libraryEpoch++;get('library-list').replaceChildren();get('inventory-status').textContent='El inventario cambió. Actualízalo antes de preparar otra rutina.';get('inventory-summary').textContent='';get('inventory-reload').disabled=false;get('generate').disabled=true;
    }
    async function refreshInventory(){
      if(dead||scope!=='gym'||inventoryBusy||!program)return;const ticket=++inventoryEpoch;inventoryBusy=true;inventory=null;generationEpoch++;libraryEpoch++;library=[];get('library-list').replaceChildren();get('inventory-reload').disabled=true;
      if(program)markDirty();get('inventory-status').textContent='Consultando las máquinas guardadas…';
      try{
        const value=await readInventory(api);if(dead||ticket!==inventoryEpoch)return;inventory=value;showInventory(value);
        get('generator-status').textContent='Inventario actualizado. Genera la rutina con el equipo del gimnasio.';
      }catch(error){if(dead||ticket!==inventoryEpoch)return;get('inventory-status').textContent=error.status===401?'Vuelve a iniciar sesión para consultar el inventario.':'No pudimos consultar las máquinas. Actualiza el inventario para continuar.';}
      finally{if(!dead&&ticket===inventoryEpoch){inventoryBusy=false;get('inventory-reload').disabled=false;get('generate').disabled=!inventory;if(inventory&&get('library').open)loadLibrary();}}
    }
    async function loadProfile(){
      if(dead)return;const clientId=scope==='gym'?get('client-select').value:undefined;
      if(scope==='gym'&&!clients.some(row=>row.id===clientId)){get('profile-status').textContent='Busca y elige un cliente primero.';return;}
      const ticket=++profileEpoch;get('load-profile').disabled=true;get('profile-status').textContent='Consultando actividad registrada…';
      try{
        const result=await readRequirements(api,scope,clientId);
        if(dead||ticket!==profileEpoch)return;
        if(!result.available||result.requirements.activity_level===null){get('profile-status').textContent='No hay actividad registrada. Elige las opciones de abajo.';return;}
        get('activity').value=result.requirements.activity_level;markDirty();
        get('profile-status').textContent=scope==='gym'?'Actividad cargada del cliente elegido. Confirma experiencia, equipo y tiempo.':'Actividad cargada de tu perfil. Confirma experiencia, equipo y tiempo.';
      }catch(error){if(dead||ticket!==profileEpoch)return;get('profile-status').textContent=error.status===404?'Este cliente ya no está disponible. Busca de nuevo.':'No pudimos consultar la actividad. Puedes elegirla manualmente.';}
      finally{if(!dead)get('load-profile').disabled=false;}
    }
    async function searchClients(more=false){
      if(dead||scope!=='gym')return;const query=get('client-query').value.trim().slice(0,80),offset=more?clientOffset+30:0,ticket=++clientEpoch;
      get('client-search').disabled=true;get('client-more').disabled=true;get('profile-status').textContent='Buscando clientes…';
      try{
        const result=await readClients(api,query,offset);
        if(dead||ticket!==clientEpoch||query!==get('client-query').value.trim().slice(0,80))return;
        if(!more){if(get('client-select').value)markDirty();clients=[];get('client-select').replaceChildren();const option=put(get('client-select'),'option','Elige un cliente');option.value='';}
        for(const row of result.clients)if(!clients.some(old=>old.id===row.id)){clients.push(row);const option=put(get('client-select'),'option',row.name);option.value=row.id;}
        clientOffset=offset;clientQuery=query;get('client-more').hidden=!result.has_more;get('client-select').disabled=!clients.length;get('profile-status').textContent=clients.length?'Elige un cliente y pulsa «Usar actividad».':'No hay clientes con esa búsqueda.';
      }catch(error){if(dead||ticket!==clientEpoch)return;get('profile-status').textContent='No pudimos consultar los clientes. Puedes elegir los requisitos manualmente.';}
      finally{if(!dead&&ticket===clientEpoch){get('client-search').disabled=false;get('client-more').disabled=false;}}
    }
    function drawLibrary(){
      const query=get('library-query').value.trim().toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,''),group=get('library-group').value;
      const rows=library.filter(exercise=>(group==='all'||exercise.session===group)&&exercise.name.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').includes(query));
      get('library-list').replaceChildren();
      for(const exercise of rows){
        const card=put(get('library-list'),'li',undefined,'routines-library-item'),label=put(card,'label'),input=put(label,'input');input.type='checkbox';input.checked=excluded.has(exercise.id);input.setAttribute('aria-label','Excluir '+exercise.name);
        const copy=put(label,'span');put(copy,'strong',exercise.name);put(copy,'small',exercise.equipment.join(' · '));
        if(scope==='gym'&&exercise.available_in_inventory===false)put(copy,'small','No disponible en tu gimnasio','routines-library-unavailable');
        input.addEventListener('change',()=>{if(input.checked)excluded.add(exercise.id);else excluded.delete(exercise.id);markDirty();get('excluded-count').textContent=String(excluded.size);});
      }
      get('library-status').textContent=rows.length+' de '+library.length+' ejercicios · marca los que quieres excluir.'+(scope==='gym'?' Las máquinas no disponibles quedan fuera automáticamente.':'');get('excluded-count').textContent=String(excluded.size);
    }
    async function loadLibrary(){
      if(dead||library.length)return;if(scope==='gym'&&(!inventory||inventoryBusy)){get('library-status').textContent='Actualiza el inventario del gimnasio para consultar su disponibilidad.';return;}const ticket=++libraryEpoch;get('library-status').textContent='Consultando biblioteca de ejercicios…';get('library-retry').disabled=true;
      try{const value=await readExerciseCatalog(api,scope);if(dead||ticket!==libraryEpoch)return;if(scope==='gym'&&(!inventory||value.inventory.revision!==inventory.revision||value.inventory.configured!==inventory.configured||!sameIds(value.inventory.machine_ids,inventory.machine_ids))){staleInventory();markDirty();get('library-status').textContent='El inventario cambió. Actualízalo para revisar los ejercicios.';return;}library=value.exercises;get('library-count').textContent=String(library.length);drawLibrary();get('library-retry').hidden=true;}
      catch(error){if(dead||ticket!==libraryEpoch)return;get('library-status').textContent='No pudimos consultar la biblioteca. Puedes intentarlo de nuevo.';get('library-retry').hidden=false;}
      finally{if(!dead&&ticket===libraryEpoch)get('library-retry').disabled=false;}
    }
    async function load(){
      if(dead)return;const ticket=++epoch;generationEpoch++;get('reload').disabled=true;get('content').hidden=true;stop();get('status').textContent='Consultando las rutinas disponibles…';
      if(scope==='gym'){inventoryEpoch++;inventory=null;inventoryBusy=false;libraryEpoch++;library=[];get('library-list').replaceChildren();}
      try{const [p,machines]=await Promise.all([readCatalog(api,scope),scope==='gym'?readInventory(api):Promise.resolve(null)]);if(dead||ticket!==epoch)return;inventory=machines;variant=0;draw(p);if(scope==='gym'){showInventory(machines);markDirty();get('generator-status').textContent='Elige los requisitos y genera las sesiones con el inventario del gimnasio.';}else get('generator-status').textContent='Empieza con este ejemplo o ajusta los requisitos para generar otra rutina.';get('status').textContent='Rutinas disponibles. La actividad registrada sólo se consulta cuando la solicitas.';get('recovery').hidden=true;}
      catch(error){if(dead||ticket!==epoch)return;get('status').textContent=error.status===401?'Inicia sesión para consultar las rutinas.':error.status===403?'Este espacio no está disponible para tu cuenta. Entra desde la navegación de tu espacio.':'No pudimos consultar las rutinas. Puedes volver a intentarlo; no se ha guardado actividad.';get('recovery').hidden=false;}
      finally{if(!dead&&ticket===epoch)get('reload').disabled=false;}
    }
    get('gym-source').hidden=scope!=='gym';get('personal-source').hidden=scope!=='personal';
    get('inventory').hidden=scope!=='gym';get('personal-equipment').hidden=scope==='gym';get('library-count-label').textContent=scope==='gym'?'en biblioteca':'disponibles';
    get('inventory-reload').addEventListener('click',refreshInventory);
    get('reload').addEventListener('click',load);
    get('default').addEventListener('click',()=>{if(!program)return;frequency=3;selected=[...defaultDays[3]];cycleWeek=1;get('frequency').value='3';for(const input of get('days').querySelectorAll('input'))input.checked=selected.includes(Number(input.value));if(program.schedule.sessions_per_week!==frequency)markDirty();else drawWeek();});
    get('frequency').addEventListener('change',()=>{if(!program)return;const value=Number(get('frequency').value);if(!frequencies.includes(value))return;frequency=value;selected=[...defaultDays[value]];cycleWeek=1;for(const input of get('days').querySelectorAll('input'))input.checked=selected.includes(Number(input.value));markDirty();});
    get('cycle-week').addEventListener('change',()=>{if(!program)return;const value=Number(get('cycle-week').value);if(!Number.isInteger(value)||value<1||value>cycleLength(selected))return;cycleWeek=value;drawWeek();});
    for(const name of ['activity','experience','goal','exercise-count','session-minutes'])get(name).addEventListener('change',markDirty);
    for(const input of get('equipment').querySelectorAll('input')){input.disabled=scope==='gym';if(scope==='personal')input.addEventListener('change',markDirty);}
    get('generator').addEventListener('submit',event=>{event.preventDefault();generate(0);});
    get('another').addEventListener('click',()=>{if(!dirty)generate((variant+1)%10,true);});
    get('load-profile').addEventListener('click',loadProfile);
    get('client-search').addEventListener('click',()=>searchClients(false));
    get('client-more').addEventListener('click',()=>{if(clientQuery===get('client-query').value.trim().slice(0,80))searchClients(true);else searchClients(false);});
    get('client-select').addEventListener('change',()=>{profileEpoch++;markDirty();get('profile-status').textContent='Pulsa «Usar actividad» para cargar la del cliente elegido.';});
    get('client-query').addEventListener('input',()=>{clientEpoch++;profileEpoch++;get('client-search').disabled=false;get('client-more').hidden=true;});
    get('client-query').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();searchClients(false);}});
    get('library').addEventListener('toggle',()=>{if(get('library').open)loadLibrary();});
    get('library-retry').addEventListener('click',loadLibrary);
    get('library-query').addEventListener('input',drawLibrary);get('library-group').addEventListener('change',drawLibrary);
    get('clear-exclusions').addEventListener('click',()=>{if(excluded.size){excluded.clear();markDirty();drawLibrary();}});
    get('rest').addEventListener('change',()=>resetTimer(Number(get('rest').value)));
    get('timer-reset').addEventListener('click',()=>resetTimer(Number(get('rest').value)));
    get('timer-start').addEventListener('click',()=>{stop();const state=timer.toggle();get('timer-status').textContent=state.running?'Descanso en curso. Puedes pausarlo o reiniciarlo.':'Temporizador en pausa.';clock();if(state.running)interval=root.setInterval(clock,250);});
    get('print').addEventListener('click',()=>{if(!dirty&&!busy&&validWeek(selected,frequency))root.print();});
    root.addEventListener('beforeprint',()=>{printed=Array.from(get('sessions').querySelectorAll('details'),node=>[node,node.open]);for(const[node]of printed)node.open=true;});
    root.addEventListener('afterprint',()=>{for(const[node,open]of printed)node.open=open;printed=[];});
    root.addEventListener('metodobase-session-changed',invalidate);root.addEventListener('pagehide',invalidate);root.addEventListener('pageshow',event=>{if(event.persisted)invalidate();});
    root.addEventListener('metodobase-gym-equipment-changed',()=>{if(scope==='gym'&&!dead){staleInventory();if(program)markDirty();}});
    load();return Object.freeze({invalidate});
  }
  const exported=Object.freeze({validate,validateExercise,formatDose,normalizeDeclaredRequirements,validateInventory,validateInventoryMeta,validWeek,cycleLength,week,createTimer,readCatalog,readInventory,readExercises,generateRoutine,readRequirements,readClients,mount});
  if(typeof module!=='undefined'&&module.exports)module.exports=exported;root.RoutinePanel=exported;
  if(typeof document!=='undefined'){const start=()=>{const panel=document.querySelector('[data-routines]');if(panel)mount(panel);};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();}
})(typeof window==='undefined'?globalThis:window);
