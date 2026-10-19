/* Personal diary: server dates/snapshots, explicit CAS writes, memory-only drafts. */
(() => {
  'use strict';
  const timezone = 'America/Mexico_City';
  const mealNames = ['desayuno','almuerzo','comida','cena'];
  const macroNames = ['kcal','protein_g','carbs_g','fat_g'];
  const sessionCodes = new Set(['session_changed','session_expired','session_storage_error','diary_identity_unavailable','diary_context_mismatch']);
  const copy = value => JSON.parse(JSON.stringify(value));
  const protocol = () => new Error('El servidor devolvió un diario incompleto. Vuelve a consultar.');
  function dateParts(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw protocol();
    const [year,month,day] = value.split('-').map(Number);
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > [31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]) throw protocol();
    return {year,month,day};
  }
  function totals(value) {
    if (!value || macroNames.some(name => typeof value[name] !== 'number' || !Number.isFinite(value[name]) || value[name] < 0)) throw protocol();
  }
  function parseDay(value, expected) {
    if (!value || value.timezone !== timezone) throw protocol();
    dateParts(value.local_date); dateParts(value.today);
    if (expected && value.local_date !== expected) throw protocol();
    if (!Number.isSafeInteger(value.version) || value.version < 0 || value.version > 2147483647 ||
        !Number.isInteger(value.water_ml) || value.water_ml < 0 || value.water_ml > 20000 ||
        !value.meals || typeof value.meals !== 'object' || Array.isArray(value.meals)) throw protocol();
    totals(value.totals);
    for (const [name,meal] of Object.entries(value.meals)) {
      if (!mealNames.includes(name) || !meal || meal.meal !== name || !Number.isSafeInteger(meal.source_plan_id) || meal.source_plan_id < 1 ||
          typeof meal.completed !== 'boolean' || !Array.isArray(meal.foods) || meal.foods.length > 32 || !meal.selections || typeof meal.recorded_at !== 'string') throw protocol();
      totals(meal.totals);
      for (const food of meal.foods) {
        if (!food || typeof food.food_id !== 'string' || !food.food_id || typeof food.grams !== 'number' || !Number.isFinite(food.grams) || food.grams <= 0) throw protocol();
        totals(food.macros);
      }
    }
    if (value.version === 0 && (value.water_ml !== 0 || Object.keys(value.meals).length || macroNames.some(name => value.totals[name] !== 0))) throw protocol();
    return copy(value);
  }
  function parseCalendar(value, start, end) {
    if (!value || value.timezone !== timezone || !Array.isArray(value.days) || value.days.length > 62) throw protocol();
    dateParts(value.today);
    let previous = '';
    const days = value.days.map(day => {
      const parsed = parseDay(day);
      if (parsed.today !== value.today || parsed.local_date <= previous || (start && parsed.local_date < start) || (end && parsed.local_date > end)) throw protocol();
      previous = parsed.local_date; return parsed;
    });
    return {today:value.today, timezone, days};
  }
  function monthRange(value) {
    const {year,month} = dateParts(value);
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const count = [31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1];
    const prefix = String(year).padStart(4,'0')+'-'+String(month).padStart(2,'0')+'-';
    return {start:prefix+'01',end:prefix+count,count};
  }
  function create(options) {
    const personal = options.personal;
    let current = null, today = null, selected = null, draft = null;
    let state = 'idle', invalid = false, saving = false, sequence = 0, calendarSequence = 0, reconsulted = false;
    const changed = () => Object.assign(new Error('La sesión cambió. Vuelve a abrir tu diario desde tu cuenta.'), {code:'session_changed'});
    function check(ticket = sequence) {
      if (invalid || ticket !== sequence) throw changed();
      personal.check();
    }
    function emit(next, message) {
      state = next;
      options.onState?.({state,message,today,selected,busy:saving,hasDraft:!!draft,canRetry:!!draft && reconsulted && !saving});
    }
    function expose() {
      check();
      if (current) options.onView?.(copy(current));
    }
    function invalidate(error = changed()) {
      if (!invalid) {
        invalid = true; sequence++; calendarSequence++; current = null; today = null; selected = null; draft = null; saving = false;
        options.onClear?.(); emit('invalidated',error.message);
      }
    }
    function failure(error, ticket) {
      if (invalid || ticket !== sequence) return;
      if (sessionCodes.has(error.code)) { invalidate(error); personal.invalidate(error); return; }
      try { check(ticket); } catch (changedError) { invalidate(changedError); return; }
      if (['diary_context_requires_review','diary_personal_space_required'].includes(error.code)) {
        current = null; draft = null; options.onClear?.(); emit('review','No se pudo confirmar tu espacio personal para el diario. Se requiere una revisión de la cuenta.');
      } else if (error.code === 'diary_version_conflict') {
        emit('conflict','Este día cambió en otro dispositivo. Tu borrador no se registró. Reconsulta los datos antes de decidir si deseas registrarlo.');
      } else if (error.code === 'diary_version_exhausted') {
        emit('exhausted','Este día requiere revisión antes de aceptar más cambios. Puedes volver a consultar los datos.');
      } else if (error.code === 'diary_save_unconfirmed' || (!error.status && draft)) {
        emit('unconfirmed','No se confirmó el registro. Puede haberse guardado. Reconsulta antes de intentar otra escritura.');
      } else {
        emit('error',error.message || 'No se pudo consultar el diario. Vuelve a intentarlo.');
      }
    }
    async function bootstrap() {
      if (invalid || saving) return;
      const ticket = ++sequence; current = null; draft = null; reconsulted = false;
      options.onClear?.(); emit('loading','Consultando la fecha y el diario del servidor…');
      try {
        const result = parseCalendar(await personal.read(context => Api.usuario.diarioHoy(context)));
        check(ticket);
        if (result.days.length !== 1 || result.days[0].local_date !== result.today) throw protocol();
        today = result.today; selected = today; current = result.days[0]; expose();
        emit('ready','Datos consultados. Registra cada cambio de forma explícita.');
      } catch (error) { failure(error,ticket); }
    }
    async function select(day, keepDraft = false) {
      if (invalid || saving) return;
      dateParts(day);
      const ticket = ++sequence; selected = day;
      if (!keepDraft) draft = null;
      current = null; reconsulted = false; options.onClear?.();
      emit('loading','Consultando el diario del '+day+'…');
      try {
        const result = parseDay(await personal.read(context => Api.usuario.diarioDia(day,context)),day);
        check(ticket); today = result.today; current = result; reconsulted = !!draft; expose();
        emit(draft ? 'reloaded' : 'ready',draft ? 'Estos son los datos actuales del servidor. Tu borrador sigue sin registrar; revisa y elige si deseas aplicarlo.' : 'Datos consultados. No se ha registrado ningún cambio.');
      } catch (error) { failure(error,ticket); }
    }
    async function calendar(start,end) {
      if (invalid) return null;
      dateParts(start); dateParts(end);
      const ticket = sequence, ownCalendar = ++calendarSequence;
      try {
        const result = parseCalendar(await personal.read(context => Api.usuario.diarioCalendario(start,end,context)),start,end);
        check(ticket); if (ownCalendar !== calendarSequence) return null;
        today = result.today; return result;
      } catch (error) {
        if (ownCalendar === calendarSequence) failure(error,ticket);
        return null;
      }
    }
    async function save(operation, retry = false) {
      if (invalid || saving || !current || ['review','exhausted'].includes(state)) return false;
      if (draft && !retry) {
        emit(state,'Tienes un borrador pendiente. Reconsúltalo o descártalo antes de registrar otro cambio.'); return false;
      }
      if (retry && (!draft || !reconsulted)) return false;
      check();
      const ticket = sequence, day = current.local_date, expected = current.version;
      const mutation = copy(operation);
      draft = {day,operation:mutation}; reconsulted = false; saving = true;
      emit('saving','Registrando el cambio en el servidor…');
      let timer;
      try {
        const result = parseDay(await Promise.race([
          personal.read(context => Api.usuario.guardarDiario(day,{...mutation,expected_version:expected},context)),
          new Promise((_,reject) => { timer = setTimeout(() => reject(new Error('No llegó la confirmación del registro.')),options.timeoutMs || 30000); }),
        ]),day);
        check(ticket);
        if (result.version !== expected+1) throw protocol();
        current = result; today = result.today; draft = null; expose();
        saving = false; emit('confirmed','Cambio confirmado por el servidor.'); return true;
      } catch (error) {
        saving = false; failure(error,ticket); return false;
      } finally { clearTimeout(timer); }
    }
    if (typeof window.addEventListener === 'function') window.addEventListener('metodobase-session-changed',event => {
      const error = Object.assign(new Error(event.detail?.message || 'La sesión cambió. Vuelve a abrir el diario.'),{code:event.detail?.code || 'session_changed'});
      invalidate(error); personal.invalidate(error);
    });
    return {
      bootstrap,select,calendar,invalidate,
      reconsult: () => selected ? select(selected,true) : bootstrap(),
      save,
      retry: () => draft && reconsulted ? save(draft.operation,true) : Promise.resolve(false),
      discard() { if (!saving && !invalid) { draft = null; reconsulted = false; if (current) expose(); emit('ready','Borrador descartado. No se registró otro cambio.'); } },
      get day() { return current ? copy(current) : null; },
      get today() { return today; },
      get selected() { return selected; },
      get draft() { return draft ? copy(draft) : null; },
      get state() { return state; },
      get writable() { return !invalid && !saving && !!current && !draft && !['review','exhausted'].includes(state) && current.local_date <= today; },
    };
  }
  function mountPlan(options) {
    const personal = options.personal, element = id => document.getElementById(id);
    const labels = {desayuno:'Desayuno',almuerzo:'Almuerzo',comida:'Comida',cena:'Cena'};
    const checks = {desayuno:'chk-des',almuerzo:'chk-alm',comida:'chk-com',cena:'chk-cen'};
    const number = value => Number(value).toLocaleString('es-MX',{maximumFractionDigits:1});
    const foodName = value => String(value).replace(/_/g,' ');
    let controller, source = null, chosen = {}, activeMeal = null, lastState = null;
    function close(id) {
      const panel = element(id); panel.style.display = 'none';
      if (window.DialogFocus) DialogFocus.close(panel);
    }
    function open(id, focus) {
      const panel = element(id); panel.style.display = 'flex';
      if (window.DialogFocus) DialogFocus.open(panel,() => close(id),focus);
      else focus.focus();
    }
    function clear() {
      if (!controller || !controller.draft) {
        source = null; chosen = {}; activeMeal = null;
        element('meal-tabs').replaceChildren(); element('meal-selector-content').replaceChildren();
        close('panel-agua-overlay'); close('panel-comidas-overlay');
      }
      element('diary-snapshots').replaceChildren();
      element('diary-water-current').textContent = '';
      element('water-saved-value').textContent = '';
      element('goal-current').textContent = '—'; element('goal-ring-pct').textContent = '—';
      element('goal-pct-label').textContent = 'Sin consultar';
      element('goal-progress-bar').style.width = '0%';
      element('water-input').value = '';
      for (const id of Object.values(checks)) { element(id).checked = false; element(id).disabled = true; }
    }
    function render(day) {
      personal.check();
      const completed = Object.values(day.meals).filter(meal => meal.completed).length;
      element('goal-current').textContent = number(day.totals.kcal);
      element('goal-pct-label').textContent = completed+' de 4 comidas completadas · '+Object.keys(day.meals).length+' registradas';
      element('goal-ring-pct').textContent = completed+'/4';
      element('goal-progress-bar').style.width = (completed*25)+'%';
      element('goal-ring').setAttribute('stroke-dashoffset',String(326.73*(1-completed/4)));
      element('goal-ring').closest('svg').setAttribute('aria-label',completed+' de 4 comidas completadas');
      element('diary-water-current').textContent = 'Agua registrada: '+number(day.water_ml)+' mL · '+day.local_date+' · '+timezone;
      element('water-saved-value').textContent = 'Valor actual del servidor: '+number(day.water_ml)+' mL para '+day.local_date+'.';
      const pending = controller.draft;
      element('water-input').value = pending?.operation.operation === 'water' ? pending.operation.water_ml : day.water_ml;
      for (const [name,id] of Object.entries(checks)) {
        element(id).checked = !!day.meals[name]?.completed;
        element(id).disabled = !controller.writable || !day.meals[name];
      }
      const root = element('diary-snapshots'); root.replaceChildren();
      const summary = document.createElement('p');
      summary.textContent = 'Consumo registrado: '+number(day.totals.kcal)+' kcal · proteína '+number(day.totals.protein_g)+' g · carbohidratos '+number(day.totals.carbs_g)+' g · grasas '+number(day.totals.fat_g)+' g.';
      root.append(summary);
      if (!Object.keys(day.meals).length) {
        const empty = document.createElement('p'); empty.textContent = 'Sin comidas registradas para esta fecha.'; root.append(empty);
      }
      for (const name of mealNames) {
        const saved = day.meals[name]; if (!saved) continue;
        const article = document.createElement('article'); article.className = 'u-card'; article.dataset.diaryMeal = name; article.dataset.sourcePlanId = saved.source_plan_id;
        const title = document.createElement('h3'); title.textContent = labels[name]+(saved.completed ? ' · completada' : ' · registrada, sin completar');
        const text = document.createElement('p'); text.textContent = number(saved.totals.kcal)+' kcal registradas. Los alimentos guardados se conservan aunque cambie tu plan.';
        const list = document.createElement('ul');
        for (const food of saved.foods) { const item = document.createElement('li'); item.textContent = foodName(food.food_id)+' · '+number(food.grams)+' g'+(food.equivalence ? ' · '+food.equivalence : ''); list.append(item); }
        if (!saved.foods.length) { const item = document.createElement('li'); item.textContent = 'Se registró una selección vacía.'; list.append(item); }
        article.append(title,text,list); root.append(article);
      }
    }
    function draftDescription() {
      const pending = controller.draft; if (!pending) return '';
      const operation = pending.operation;
      if (operation.operation === 'water') return 'Borrador sin confirmar para '+pending.day+': '+number(operation.water_ml)+' mL de agua.';
      if (operation.operation === 'completion') return 'Borrador sin confirmar: '+labels[operation.meal]+(operation.completed ? ' completada.' : ' sin completar.');
      const names = [];
      if (source?.plan_id === operation.source_plan_id) {
        for (const [group,index] of Object.entries(operation.selections)) {
          if (group === 'include_vegetables') continue;
          const food = source.plan[operation.meal]?.[group]?.opciones?.[index];
          if (food) names.push(foodName(food.alimento)+' '+number(food.gramos)+' g');
        }
        if (operation.selections.include_vegetables) names.push('vegetales seleccionados');
      }
      return 'Borrador sin confirmar para '+pending.day+': '+labels[operation.meal]+(names.length ? ' · '+names.join(', ') : ' · selección vacía')+'.';
    }
    function state(update) {
      lastState = update;
      for (const id of ['diary-status','water-status','diary-meal-status']) element(id).textContent = update.message;
      element('diary-section').setAttribute('aria-busy',String(update.state === 'loading' || update.busy));
      element('diary-date').value = update.selected || '';
      if (update.today) element('diary-date').max = update.today;
      element('diary-date').disabled = update.busy || ['review','invalidated'].includes(update.state);
      element('diary-today').disabled = update.busy || ['loading','review','invalidated'].includes(update.state);
      element('diary-reload').disabled = update.busy || update.state === 'loading' || update.state === 'invalidated';
      element('diary-retry').hidden = !update.hasDraft; element('diary-retry').disabled = !update.canRetry;
      element('diary-discard').hidden = !update.hasDraft; element('diary-discard').disabled = update.busy;
      element('diary-draft-summary').textContent = draftDescription();
      const editable = controller.writable;
      for (const id of ['btn-agua','water-input','btn-water-save','btn-comidas-save']) element(id).disabled = !editable;
      element('btn-comidas').disabled = !editable || !options.getPlan()?.plan_id;
      for (const input of element('meal-selector-content').querySelectorAll('input')) input.disabled = !editable;
      for (const [name,id] of Object.entries(checks)) element(id).disabled = !editable || !controller.day?.meals[name];
      if (['error','conflict','unconfirmed','review','exhausted','invalidated'].includes(update.state)) {
        const modal = ['panel-agua-overlay','panel-comidas-overlay'].map(element).find(panel => panel.style.display === 'flex');
        (modal?.querySelector('[data-diary-feedback]') || element('diary-status')).focus();
      }
    }
    controller = create({personal,onView:render,onClear:clear,onState:state});
    function localError(id,message) { const node = element(id); node.textContent = message; node.focus(); }
    element('diary-date').addEventListener('change',async event => {
      try { personal.check(); await controller.select(event.target.value); }
      catch (error) { localError('diary-status',error.message); }
    });
    element('diary-today').addEventListener('click',() => controller.bootstrap());
    element('diary-reload').addEventListener('click',() => controller.reconsult());
    element('diary-retry').addEventListener('click',() => controller.retry());
    element('diary-discard').addEventListener('click',() => controller.discard());
    element('btn-agua').addEventListener('click',() => {
      if (controller.writable) {
        element('water-status').textContent = 'Cambiar este campo no registra agua. Confirma con Registrar agua.';
        open('panel-agua-overlay',element('water-input'));
      }
    });
    element('water-input').addEventListener('input',() => { element('water-status').textContent = 'Borrador sin registrar. Confirma el total con Registrar agua.'; });
    element('btn-water-save').addEventListener('click',async () => {
      if (!controller.writable) return;
      const raw = element('water-input').value.trim(), value = Number(raw);
      if (!raw || !Number.isInteger(value) || value < 0 || value > 20000) { localError('water-status','Escribe un total entero entre 0 y 20 000 mL.'); return; }
      if (await controller.save({operation:'water',water_ml:value})) close('panel-agua-overlay');
    });
    for (const [name,id] of Object.entries(checks)) element(id).addEventListener('change',async event => {
      const wanted = event.target.checked; event.target.checked = !!controller.day?.meals[name]?.completed;
      if (controller.writable) await controller.save({operation:'completion',meal:name,completed:wanted});
    });
    function selector(name) {
      activeMeal = name; const meal = source?.plan[name], root = element('meal-selector-content'); root.replaceChildren();
      for (const button of element('meal-tabs').querySelectorAll('[data-meal]')) button.setAttribute('aria-pressed',String(button.dataset.meal === name));
      if (!meal) return;
      const selected = chosen[name] ||= {include_vegetables:false};
      for (const [group,label] of [['proteinas','Proteína'],['carbohidratos','Carbohidratos'],['grasas','Grasas']]) {
        const foods = meal[group]?.opciones; if (!Array.isArray(foods)) continue;
        const fieldset = document.createElement('fieldset'); fieldset.className = 'u-sel-macro-group';
        const legend = document.createElement('legend'); legend.textContent = label; fieldset.append(legend);
        foods.forEach((food,index) => {
          const item = document.createElement('label'); item.className = 'u-sel-option';
          const input = document.createElement('input'); input.type = 'radio'; input.name = 'diary-'+name+'-'+group; input.value = index;
          input.dataset.diaryGroup = group; input.checked = selected[group] === index;
          const text = document.createElement('span'); text.textContent = foodName(food.alimento)+' · '+number(food.gramos)+' g'+(food.equivalencia ? ' · '+food.equivalencia : '');
          input.addEventListener('change',() => { personal.check(); selected[group] = index;element('diary-meal-status').textContent = 'Borrador sin registrar. Confirma con Registrar esta comida.'; });
          item.append(input,text); fieldset.append(item);
        });
        root.append(fieldset);
      }
      if (Array.isArray(meal.vegetales) && meal.vegetales.length) {
        const label = document.createElement('label'), checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.checked = selected.include_vegetables;
        checkbox.dataset.diaryVegetables = 'true'; checkbox.addEventListener('change',() => { personal.check(); selected.include_vegetables = checkbox.checked;element('diary-meal-status').textContent = 'Borrador sin registrar. Confirma con Registrar esta comida.'; });
        label.append(checkbox,document.createTextNode(' Registrar también los vegetales mostrados: '+meal.vegetales.map(food => foodName(food.alimento)+' '+number(food.gramos)+' g').join(', ')));root.append(label);
      }
      const note = document.createElement('p'); note.textContent = 'Sin opciones seleccionadas se registrará una selección vacía, con 0 kcal. Este borrador no está guardado.'; root.append(note);
      element('diary-meal-status').textContent = 'Borrador sin registrar. Sólo se registra la comida seleccionada al confirmar.';
    }
    element('btn-comidas').addEventListener('click',() => {
      personal.check(); if (!controller.writable) return;
      const plan = options.getPlan(); if (!plan?.plan_id || !plan.plan) return;
      source = copy(plan); chosen = {}; activeMeal = null;
      element('diary-source-label').textContent = 'Fuente: el plan mostrado al abrir esta selección. Día de consumo: '+controller.selected+'.';
      const tabs = element('meal-tabs'); tabs.replaceChildren();
      for (const name of mealNames) {
        if (!source.plan[name]) continue;
        const button = document.createElement('button'); button.type = 'button'; button.className = 'u-meal-tab'; button.textContent = labels[name]; button.dataset.meal = name;
        button.addEventListener('click',() => { personal.check(); selector(name); }); tabs.append(button);
        if (!activeMeal) selector(name);
      }
      for (const button of tabs.querySelectorAll('[data-meal]')) button.setAttribute('aria-pressed',String(button.dataset.meal === activeMeal));
      open('panel-comidas-overlay',tabs.querySelector('button') || element('panel-comidas-close'));
    });
    element('btn-comidas-save').addEventListener('click',async () => {
      if (!controller.writable || !source || !activeMeal) return;
      if (await controller.save({operation:'meal',meal:activeMeal,source_plan_id:source.plan_id,selections:copy(chosen[activeMeal])})) close('panel-comidas-overlay');
    });
    for (const [panelId,closeId] of [['panel-agua-overlay','panel-agua-close'],['panel-comidas-overlay','panel-comidas-close']]) {
      element(closeId).addEventListener('click',() => close(panelId));
      element(panelId).addEventListener('click',event => { if (event.target === element(panelId)) close(panelId); });
    }
    controller.syncPlan = () => { if (lastState) state(lastState); };
    return controller;
  }
  function mountHistory(options) {
    const personal = options.personal, element = id => document.getElementById(id);
    const months = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
    const labels = {desayuno:'Desayuno',almuerzo:'Almuerzo',comida:'Comida',cena:'Cena'};
    const number = value => Number(value).toLocaleString('es-MX',{maximumFractionDigits:1});
    let controller, month = null, lastCalendar = null, loading = false, request = 0;
    function failed(error) {
      if (sessionCodes.has(error.code)) { controller.invalidate(error); personal.invalidate(error); }
      else { element('diary-calendar-status').textContent = error.message || 'No se pudo consultar el calendario.';element('diary-calendar-status').focus(); }
    }
    function guard(task) {
      try { personal.check();Promise.resolve(task()).catch(failed); }
      catch (error) { failed(error); }
    }
    function clear() { element('day-detail').replaceChildren(); element('day-detail').style.display = 'none'; }
    function renderDay(day) {
      personal.check();
      const root = element('day-detail'); root.replaceChildren(); root.style.display = '';
      const heading = document.createElement('h3'); heading.textContent = day.local_date+' · '+timezone; root.append(heading);
      if (day.version === 0) {
        const empty = document.createElement('p'); empty.textContent = 'No hay registros para esta fecha.'; root.append(empty);
      } else {
        const summary = document.createElement('p'); summary.textContent = 'Agua registrada: '+number(day.water_ml)+' mL. Consumo registrado: '+number(day.totals.kcal)+' kcal · proteína '+number(day.totals.protein_g)+' g · carbohidratos '+number(day.totals.carbs_g)+' g · grasas '+number(day.totals.fat_g)+' g.';root.append(summary);
        for (const name of mealNames) {
          const saved = day.meals[name]; if (!saved) continue;
          const article = document.createElement('article'); article.dataset.diaryMeal = name; article.dataset.sourcePlanId = saved.source_plan_id;
          const title = document.createElement('h4'); title.textContent = labels[name]+(saved.completed ? ' · completada' : ' · registrada, sin completar');article.append(title);
          const list = document.createElement('ul');
          for (const food of saved.foods) { const item = document.createElement('li'); item.textContent = food.food_id.replace(/_/g,' ')+' · '+number(food.grams)+' g'+(food.equivalence ? ' · '+food.equivalence : '');list.append(item); }
          if (!saved.foods.length) { const item = document.createElement('li'); item.textContent = 'Selección vacía registrada.';list.append(item); }
          article.append(list);root.append(article);
        }
      }
      for (const button of element('cal-days').querySelectorAll('[data-date]')) button.setAttribute('aria-pressed',String(button.dataset.date === day.local_date));
    }
    function state(update) {
      element('diary-calendar-status').textContent = update.message;
      element('history-diary-open').disabled = update.state === 'loading' || update.state === 'invalidated';
      if (update.state === 'invalidated') { lastCalendar = null; element('cal-days').replaceChildren(); element('cal-month-label').textContent = ''; }
      if (['error','review','invalidated'].includes(update.state) && element('panel-progreso-overlay').style.display === 'flex') element('diary-calendar-status').focus();
    }
    controller = create({personal,onClear:clear,onState:state,onView:renderDay});
    function controls() {
      const unavailable = loading || !month || !controller.today || ['review','invalidated'].includes(controller.state);
      element('cal-prev').disabled = unavailable || month === '0001-01-01';
      element('cal-next').disabled = unavailable || month.slice(0,7) >= controller.today?.slice(0,7);
      element('history-diary-reload').disabled = unavailable;
      element('history-diary-today').disabled = loading || controller.state === 'invalidated';
    }
    function mondayOffset(value) {
      let {year,month,day} = dateParts(value);
      if (month < 3) { month += 12; year--; }
      const century = Math.floor(year/100), within = year%100;
      return (day+Math.floor(13*(month+1)/5)+within+Math.floor(within/4)+Math.floor(century/4)+5*century+5)%7;
    }
    function renderCalendar(result) {
      personal.check();
      const range = monthRange(month), parts = dateParts(month), days = new Map(result.days.map(day => [day.local_date,day]));
      element('cal-month-label').textContent = months[parts.month-1]+' '+parts.year+' · '+timezone;
      const root = element('cal-days'); root.replaceChildren();
      for (let count=0; count<mondayOffset(range.start); count++) { const pad = document.createElement('span'); pad.className = 'u-cal-day'; pad.setAttribute('aria-hidden','true');root.append(pad); }
      for (let day=1; day<=range.count; day++) {
        const date = range.start.slice(0,8)+String(day).padStart(2,'0'), saved = days.get(date), future = date > result.today;
        const button = document.createElement('button'); button.type = 'button'; button.className = 'u-cal-day';button.dataset.date = date;button.disabled = future;
        const text = document.createElement('span');text.className = 'u-cal-day-num';text.textContent = day;button.append(text);
        const hasRecord = saved && saved.version > 0;
        button.setAttribute('aria-label',date+(future ? ', fecha futura' : hasRecord ? ', '+number(saved.totals.kcal)+' kcal y '+number(saved.water_ml)+' mL registrados' : ', sin registros'));
        button.setAttribute('aria-pressed',String(date === controller.selected));
        if (hasRecord && !future) {
          const value = document.createElement('span');value.className = 'u-cal-day-kcal';value.textContent = number(saved.totals.kcal)+' kcal';button.append(value);
        }
        button.addEventListener('click',() => guard(() => controller.select(date)));root.append(button);
      }
    }
    async function loadMonth() {
      if (!month || loading && !controller.today) return;
      const ownRequest = ++request, range = monthRange(month);loading = true;controls();
      element('diary-calendar-status').textContent = 'Consultando registros de este mes…';
      element('cal-days').setAttribute('aria-busy','true');
      try {
        const result = await controller.calendar(range.start,range.end);
        if (ownRequest !== request || !result) return;
        personal.check();lastCalendar = result;renderCalendar(result);
        element('diary-calendar-status').textContent = 'Calendario consultado. Cada día muestra únicamente registros del servidor.';
      } catch (error) { failed(error); }
      finally { if (ownRequest === request) { loading = false;element('cal-days').setAttribute('aria-busy','false');controls(); } }
    }
    async function bootstrap() {
      await controller.bootstrap();
      if (controller.today) { month = monthRange(controller.today).start;await loadMonth(); }
      controls();
    }
    function navigate(offset) {
      if (loading || !month) return;
      let parts = dateParts(month), year = parts.year, next = parts.month+offset;
      if (next === 0) { year--;next=12; } if (next === 13) { year++;next=1; }
      if (year < 1 || year > 9999) return;
      month = String(year).padStart(4,'0')+'-'+String(next).padStart(2,'0')+'-01';loadMonth();
    }
    element('cal-prev').addEventListener('click',() => guard(() => navigate(-1)));element('cal-next').addEventListener('click',() => guard(() => navigate(1)));
    element('history-diary-today').addEventListener('click',() => guard(bootstrap));element('history-diary-reload').addEventListener('click',() => guard(loadMonth));
    function close() { element('panel-progreso-overlay').style.display = 'none';if (window.DialogFocus) DialogFocus.close(element('panel-progreso-overlay')); }
    element('history-diary-open').addEventListener('click',() => guard(async () => {
      clear();element('cal-days').replaceChildren();element('cal-month-label').textContent = '';
      element('panel-progreso-overlay').style.display = 'flex';
      if (window.DialogFocus) DialogFocus.open(element('panel-progreso-overlay'),close,element('panel-progreso-close'));
      await loadMonth();
    }));
    element('panel-progreso-close').addEventListener('click',close);
    element('panel-progreso-overlay').addEventListener('click',event => { if (event.target === element('panel-progreso-overlay')) close(); });
    return {bootstrap,invalidate(error) { request++;lastCalendar=null;controller.invalidate(error);close(); }};
  }
  window.PersonalDiary = Object.freeze({create,mountPlan,mountHistory,dateParts,monthRange,timezone,mealNames,parseDay});
})();
