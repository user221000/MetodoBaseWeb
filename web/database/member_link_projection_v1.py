"""Frozen SQL vocabulary for the source-bound revision29 projection.

Every helper is invoker-only, reads its arguments, and returns no global data.
Installation belongs to the migration; imports never execute DDL.
"""


def projection_sql():
    return r"""
CREATE FUNCTION public.r12_unique_json(value json, depth integer DEFAULT 0) RETURNS boolean
 LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE child json;
 BEGIN
  IF depth>12 THEN RETURN false; END IF;
  IF json_typeof(value)='object' THEN
   IF (SELECT count(*)<>count(DISTINCT key) FROM json_each(value)) THEN RETURN false; END IF;
   FOR child IN SELECT x.value FROM json_each(value) x LOOP
    IF NOT public.r12_unique_json(child,depth+1) THEN RETURN false; END IF;
   END LOOP;
  ELSIF json_typeof(value)='array' THEN
   FOR child IN SELECT json_array_elements(value) LOOP
    IF NOT public.r12_unique_json(child,depth+1) THEN RETURN false; END IF;
   END LOOP;
  END IF;
  RETURN true;
 END $$;
CREATE FUNCTION public.r12_keys(value jsonb, allowed text[], required text[]) RETURNS boolean
 LANGUAGE sql IMMUTABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 SELECT CASE WHEN jsonb_typeof(value)='object' THEN
  value ?& required AND NOT EXISTS(SELECT 1 FROM jsonb_object_keys(value) key WHERE NOT key=ANY(allowed))
  ELSE false END
 $$;
CREATE FUNCTION public.r12_number(value jsonb, positive boolean DEFAULT false) RETURNS boolean
 LANGUAGE sql IMMUTABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 SELECT CASE WHEN jsonb_typeof(value)='number' THEN
  (value::text)::numeric BETWEEN 0 AND 1000000000000 AND (NOT positive OR (value::text)::numeric>0)
  ELSE false END
 $$;
CREATE FUNCTION public.r12_food(value jsonb, vegetable boolean DEFAULT false) RETURNS boolean
 LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE macro jsonb;
 BEGIN
  IF NOT public.r12_keys(value,ARRAY['alimento','gramos','equivalencia','macros'],ARRAY['alimento','gramos'])
   OR jsonb_typeof(value->'alimento')<>'string' OR length(value->>'alimento') NOT BETWEEN 1 AND 200
   OR NOT public.r12_number(value->'gramos',true) THEN RETURN false; END IF;
  IF value ? 'equivalencia' AND (jsonb_typeof(value->'equivalencia')<>'string' OR length(value->>'equivalencia')>500) THEN RETURN false; END IF;
  IF value ? 'macros' THEN
   IF NOT public.r12_keys(value->'macros',ARRAY['kcal','proteina','carbs','grasa'],ARRAY[]::text[]) THEN RETURN false; END IF;
   FOR macro IN SELECT x.value FROM jsonb_each(value->'macros') x LOOP
    IF NOT public.r12_number(macro) THEN RETURN false; END IF;
   END LOOP;
  END IF;
  RETURN true;
 END $$;
CREATE FUNCTION public.r12_project_plan(source public.planes_generados) RETURNS jsonb
 LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE raw json; plan jsonb; meal jsonb; block jsonb; item jsonb; category text; name text;
  projected jsonb; metadata jsonb; scalar jsonb; foods integer;
 BEGIN
  IF source.plan_json IS NULL OR octet_length(source.plan_json)>262144 THEN
   RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source content unavailable'; END IF;
  raw=source.plan_json::json;
  IF NOT public.r12_unique_json(raw) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source content unavailable'; END IF;
  plan=raw::jsonb;
  IF NOT public.r12_keys(plan,ARRAY['desayuno','almuerzo','comida','cena'],ARRAY['desayuno','almuerzo','comida','cena']) THEN
   RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source schema unavailable'; END IF;
  FOREACH name IN ARRAY ARRAY['desayuno','almuerzo','comida','cena'] LOOP
   meal=plan->name;
   IF meal->>'tipo_plan'='opciones' THEN
    foods=0;
    IF NOT public.r12_keys(meal,ARRAY['kcal_objetivo','tipo_plan','proteinas','carbohidratos','grasas','vegetales'],
      ARRAY['kcal_objetivo','tipo_plan','proteinas','carbohidratos','grasas','vegetales'])
      OR NOT public.r12_number(meal->'kcal_objetivo') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source options unavailable'; END IF;
    FOREACH category IN ARRAY ARRAY['proteinas','carbohidratos','grasas'] LOOP
     block=meal->category;
     IF NOT public.r12_keys(block,ARRAY['cantidad_objetivo','opciones'],ARRAY['cantidad_objetivo','opciones'])
      OR NOT public.r12_number(block->'cantidad_objetivo') OR jsonb_typeof(block->'opciones')<>'array' THEN
       RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source options unavailable'; END IF;
     IF jsonb_array_length(block->'opciones')>256 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source options unavailable'; END IF;
     foods=foods+jsonb_array_length(block->'opciones');
     FOR item IN SELECT jsonb_array_elements(block->'opciones') LOOP
      IF NOT public.r12_food(item) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source food unavailable'; END IF;
     END LOOP;
    END LOOP;
    IF jsonb_typeof(meal->'vegetales')<>'array' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source vegetables unavailable'; END IF;
    IF jsonb_array_length(meal->'vegetales')>32 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source vegetables unavailable'; END IF;
    foods=foods+jsonb_array_length(meal->'vegetales');
    FOR item IN SELECT jsonb_array_elements(meal->'vegetales') LOOP
     IF NOT public.r12_food(item,true) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source food unavailable'; END IF;
    END LOOP;
    IF foods=0 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 empty meal unavailable'; END IF;
   ELSE
    IF NOT public.r12_keys(meal,ARRAY['kcal_objetivo','kcal_real','alimentos'],ARRAY['kcal_objetivo','kcal_real','alimentos'])
      OR NOT public.r12_number(meal->'kcal_objetivo') OR NOT public.r12_number(meal->'kcal_real')
      OR jsonb_typeof(meal->'alimentos')<>'object' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source fixed menu unavailable'; END IF;
    IF (SELECT count(*) FROM jsonb_object_keys(meal->'alimentos')) NOT BETWEEN 1 AND 256 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source foods unavailable'; END IF;
    FOR name,scalar IN SELECT key,value FROM jsonb_each(meal->'alimentos') LOOP
     IF length(name) NOT BETWEEN 1 AND 200 OR NOT public.r12_number(scalar,true) THEN
      RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source food unavailable'; END IF;
    END LOOP;
   END IF;
  END LOOP;
  metadata=jsonb_build_object('tmb',source.tmb,'get_total',source.get_total,'kcal_objetivo',source.kcal_objetivo,
    'kcal_real',source.kcal_real,'proteina_g',source.proteina_g,'carbs_g',source.carbs_g,'grasa_g',source.grasa_g,
    'objetivo',source.objetivo,'nivel_actividad',source.nivel_actividad,'tipo_plan',source.tipo_plan);
  FOREACH name IN ARRAY ARRAY['tmb','get_total','kcal_objetivo','kcal_real','proteina_g','carbs_g','grasa_g'] LOOP
   IF metadata->name<>'null'::jsonb AND NOT public.r12_number(metadata->name) THEN
    RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source metadata unavailable'; END IF;
  END LOOP;
  projected=jsonb_build_object('plan',plan,'meta',metadata);
  IF octet_length(projected::text)>262144 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 projection volume unavailable'; END IF;
  RETURN projected;
 EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN
  RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 source content unavailable';
 END $$;
"""
