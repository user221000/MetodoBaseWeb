/* Generic catalogue, RAM-only week/timer. No training record or background work. */
(function(root){
  'use strict';
  const ids=['push','pull','legs'],durations=[60,90,120];
  const invalid=()=>Object.assign(Error('No pudimos validar el catálogo de rutinas.'),{code:'routine_invalid_response'});
  const text=value=>typeof value==='string'&&value.length>0&&value.length<=1000;
  const list=(value,min,max)=>Array.isArray(value)&&value.length>=min&&value.length<=max;
  function validate(value,scope){
    if(value?.version!==1||value.scope!==scope||!value.program||value.program.id!=='ppl-basico-v1')throw invalid();
    const p=value.program;
    for(const key of['title','audience','summary','starting_point','guideline_note'])if(!text(p[key]))throw invalid();
    if(!list(p.warmup,1,4)||!list(p.cautions,1,4)||![...p.warmup,...p.cautions].every(text))throw invalid();
    if(p.schedule?.sessions_per_week!==3||p.schedule.nonconsecutive!==true||!list(p.schedule.days,7,7)||!p.schedule.days.every(text)||!text(p.schedule.note)||!validWeek(p.schedule.default_days))throw invalid();
    if(!list(p.sessions,3,3))throw invalid();
    const exerciseIds=new Set();
    p.sessions.forEach((session,index)=>{
      if(session.id!==ids[index]||!['name','label','focus','description'].every(key=>text(session[key]))||!list(session.exercises,4,5))throw invalid();
      session.exercises.forEach(exercise=>{
        if(typeof exercise.id!=='string'||!/^[a-z]+(?:-[a-z]+)*$/.test(exercise.id)||exerciseIds.has(exercise.id))throw invalid();
        exerciseIds.add(exercise.id);
        if(!text(exercise.name)||exercise.sets?.minimum!==1||exercise.sets.maximum!==2||!text(exercise.repetitions)||!durations.includes(exercise.rest_seconds)||!list(exercise.equipment,1,4)||!exercise.equipment.every(text)||!list(exercise.cues,2,3)||!exercise.cues.every(text))throw invalid();
        if(!text(exercise.alternative?.name)||!text(exercise.alternative.cue)||!list(exercise.alternative.equipment,1,4)||!exercise.alternative.equipment.every(text))throw invalid();
      });
    });
    if(!list(p.sources,3,3)||p.sources.some(source=>!text(source.label)||!text(source.url)||!/^https:\/\/(?:acsm\.org|www\.cdc\.gov|www\.betterhealth\.vic\.gov\.au)\//.test(source.url)))throw invalid();
    return p;
  }
  function validWeek(days){
    return list(days,3,3)&&days.every(day=>Number.isInteger(day)&&day>=0&&day<=6)&&new Set(days).size===3&&!days.some(day=>days.includes((day+1)%7));
  }
  function week(days,labels){
    if(!validWeek(days))return null;
    return [...days].sort((a,b)=>a-b).map((day,index)=>({day,label:labels[day],session:ids[index]}));
  }
  function createTimer(now=()=>performance.now()){
    let duration=90,remaining=90,end=null;
    function read(){if(end!==null){remaining=Math.max(0,Math.ceil((end-now())/1000));if(remaining===0)end=null;}return{duration,remaining,running:end!==null};}
    return Object.freeze({read,reset(seconds=duration){if(!durations.includes(seconds))throw RangeError('Unsupported rest duration');duration=remaining=seconds;end=null;return read();},toggle(){const state=read();if(state.running){end=null;}else{if(remaining===0)remaining=duration;end=now()+remaining*1000;}return read();}});
  }
  async function readCatalog(api,scope,fetcher=root.fetch.bind(root)){
    if(!['gym','personal'].includes(scope))throw invalid();
    await api.session.ready;
    const context=api.session.capture(),token=api.getToken();api.session.check(context);
    if(!token)throw Object.assign(Error('Inicia sesión para consultar el catálogo.'),{status:401});
    const response=await fetcher('/api/rutinas/catalogo?context='+scope,{method:'GET',headers:{Accept:'application/json',Authorization:'Bearer '+token},credentials:'omit',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});
    api.session.check(context);
    if(response.status===401)api.session.rejectUnauthorized(context,token);
    const raw=await response.text();api.session.check(context);
    if(new TextEncoder().encode(raw).byteLength>131072)throw invalid();
    let value;try{value=JSON.parse(raw);}catch{throw invalid();}
    if(!response.ok)throw Object.assign(Error('No se pudo consultar este espacio.'),{status:response.status,code:value?.detail?.code});
    return validate(value,scope);
  }
  function mount(panel,api=(typeof Api!=='undefined'?Api:undefined)){
    const get=name=>panel.querySelector('[data-routine-'+name+']');
    const put=(parent,tag,value,className)=>{const node=document.createElement(tag);if(value!==undefined)node.textContent=value;if(className)node.className=className;parent.append(node);return node;};
    let program=null,selected=[0,2,4],epoch=0,dead=false,interval=null,printed=[];
    const timer=createTimer();
    function stop(){if(interval!==null)root.clearInterval(interval);interval=null;}
    function clock(){const s=timer.read();get('clock').textContent=String(Math.floor(s.remaining/60)).padStart(2,'0')+':'+String(s.remaining%60).padStart(2,'0');get('timer-start').textContent=s.running?'Pausar':s.remaining===0?'Iniciar de nuevo':'Iniciar';if(!s.running&&interval!==null){stop();get('timer-status').textContent='Descanso terminado. Continúa cuando te sientas preparado; no se ha registrado actividad.';}}
    function resetTimer(seconds){stop();timer.reset(seconds);get('rest').value=String(seconds);clock();get('timer-status').textContent='Temporizador reiniciado. No se registra actividad.';}
    function invalidate(){if(dead)return;dead=true;epoch++;stop();timer.reset();program=null;get('content').hidden=true;get('sessions').replaceChildren();get('status').textContent='La sesión cambió. Abre de nuevo las rutinas desde tu cuenta.';get('recovery').hidden=false;get('reload').disabled=true;}
    function drawWeek(){
      get('week-summary').replaceChildren();
      const rows=week(selected,program.schedule.days);
      get('week-status').textContent=rows?'Tres días no consecutivos. Push → Pull → Legs; el resto queda libre.':'Elige exactamente tres días no consecutivos. Esta selección aún no forma una semana válida.';
      if(rows)for(const row of rows){const item=put(get('week-summary'),'li');put(item,'strong',row.label);put(item,'span',program.sessions.find(session=>session.id===row.session).name);}
    }
    function draw(p){
      program=p;selected=[...p.schedule.default_days];
      for(const[key,value]of[['audience',p.audience],['summary',p.summary],['starting',p.starting_point],['guideline',p.guideline_note],['schedule-note',p.schedule.note]])get(key).textContent=value;
      for(const[key,values]of[['warmup',p.warmup],['cautions',p.cautions]]){get(key).replaceChildren();for(const value of values)put(get(key),'li',value);}
      get('days').replaceChildren();
      p.schedule.days.forEach((day,index)=>{const label=put(get('days'),'label',undefined,'routines-day'),input=put(label,'input');input.type='checkbox';input.value=String(index);input.checked=selected.includes(index);input.setAttribute('aria-label',day);put(label,'span',day.slice(0,3));input.addEventListener('change',()=>{selected=Array.from(get('days').querySelectorAll('input:checked'),el=>Number(el.value));drawWeek();});});
      drawWeek();get('sessions').replaceChildren();get('session-nav').replaceChildren();
      p.sessions.forEach((session,index)=>{
        const link=put(get('session-nav'),'a');link.href='#routine-'+session.id;put(link,'span','0'+(index+1));put(link,'strong',session.name+' · '+session.label);
        const section=put(get('sessions'),'section',undefined,'routines-session');section.id='routine-'+session.id;section.setAttribute('aria-labelledby',section.id+'-title');
        const heading=put(section,'div',undefined,'routines-session-heading');put(heading,'span','0'+(index+1),'routines-session-number');const headingText=put(heading,'div'),title=put(headingText,'h2',session.name);title.id=section.id+'-title';put(title,'span',session.label);put(headingText,'p',session.focus);put(section,'p',session.description,'routines-session-description');
        session.exercises.forEach(exercise=>{
          const details=put(section,'details',undefined,'routines-exercise'),summary=put(details,'summary');put(summary,'h3',exercise.name);put(summary,'span',exercise.sets.minimum+'–'+exercise.sets.maximum+' series · '+exercise.repetitions+' repeticiones · '+exercise.rest_seconds+' s de descanso','routines-prescription');
          const body=put(details,'div',undefined,'routines-exercise-body');put(body,'p','Equipo: '+exercise.equipment.join(' · '));const cues=put(body,'ol');exercise.cues.forEach(cue=>put(cues,'li',cue));
          const alternative=put(body,'div',undefined,'routines-alternative');put(alternative,'strong','Alternativa · '+exercise.alternative.name);put(alternative,'p',exercise.alternative.equipment.join(' · '));put(alternative,'p',exercise.alternative.cue);
          const rest=put(body,'button','Preparar descanso de '+exercise.rest_seconds+' s','routines-button routines-button-secondary');rest.type='button';rest.addEventListener('click',()=>{resetTimer(exercise.rest_seconds);get('timer-status').textContent='Descanso preparado para '+exercise.name+'. Pulsa Iniciar cuando quieras.';get('timer-start').focus();});
        });
      });
      get('sources').replaceChildren();for(const source of p.sources){const li=put(get('sources'),'li'),a=put(li,'a',source.label);a.href=source.url;a.rel='noreferrer';}
      resetTimer(90);get('content').hidden=false;
    }
    async function load(){
      if(dead)return;const ticket=++epoch;get('reload').disabled=true;get('content').hidden=true;stop();get('status').textContent='Consultando el catálogo general…';
      try{const p=await readCatalog(api,panel.dataset.scope);if(dead||ticket!==epoch)return;draw(p);get('status').textContent='Catálogo general disponible. No utiliza tu perfil ni guarda actividad.';get('recovery').hidden=true;}
      catch(error){if(dead||ticket!==epoch)return;get('status').textContent=error.status===401?'Inicia sesión para consultar las rutinas.':error.status===403?'Este espacio no está disponible para tu cuenta. Entra desde la navegación de tu espacio.':'No pudimos consultar las rutinas. Puedes volver a consultarlas; no se ha guardado actividad.';get('recovery').hidden=false;}
      finally{if(!dead&&ticket===epoch)get('reload').disabled=false;}
    }
    get('reload').addEventListener('click',load);
    get('default').addEventListener('click',()=>{selected=[...program.schedule.default_days];for(const input of get('days').querySelectorAll('input'))input.checked=selected.includes(Number(input.value));drawWeek();});
    get('rest').addEventListener('change',()=>resetTimer(Number(get('rest').value)));
    get('timer-reset').addEventListener('click',()=>resetTimer(Number(get('rest').value)));
    get('timer-start').addEventListener('click',()=>{stop();const state=timer.toggle();get('timer-status').textContent=state.running?'Descanso en curso. Puedes pausarlo o reiniciarlo.':'Temporizador en pausa.';clock();if(state.running)interval=root.setInterval(clock,250);});
    get('print').addEventListener('click',()=>root.print());
    root.addEventListener('beforeprint',()=>{printed=Array.from(panel.querySelectorAll('details'),node=>[node,node.open]);for(const[node]of printed)node.open=true;});
    root.addEventListener('afterprint',()=>{for(const[node,open]of printed)node.open=open;printed=[];});
    root.addEventListener('metodobase-session-changed',invalidate);
    root.addEventListener('pagehide',invalidate);
    root.addEventListener('pageshow',event=>{if(event.persisted)invalidate();});
    load();return Object.freeze({invalidate});
  }
  const exported=Object.freeze({validate,validWeek,week,createTimer,readCatalog,mount});
  if(typeof module!=='undefined'&&module.exports)module.exports=exported;
  root.RoutinePanel=exported;
  if(typeof document!=='undefined'){
    const start=()=>{const panel=document.querySelector('[data-routines]');if(panel)mount(panel);};
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  }
})(typeof window==='undefined'?globalThis:window);
