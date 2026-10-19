"""Private SQL-only source reader; never a SQL function or a source Session.

Only verified service paths call this module after holding account/link/latest
consent locks. Tenant GUCs are context, never signatures. The application role
already controls its GUCs; this introduces no new database impersonation API.
Every source read uses the SAME Connection, so pool1 needs no second checkout.
"""
from contextlib import contextmanager
from types import SimpleNamespace

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from web.database.models import ClientProgress, Cliente
from web.services import personal_progress as own
from web.database.tenant_context import current_tenant

_FIELDS=("id","record_key","version","source_kind","id_cliente","measured_on","fecha","recorded_at","updated_at","withdrawn_at")


@contextmanager
def _source_connection(db,expected_tenant,subject):
    """SAVEPOINT is after authorization locks; errors cannot leak source scope.

    No ORM query/flush runs inside, nor ContextVar/Session.info reassignment.
    An aborted connection cannot produce a result; the service rolls back the
    root transaction when restoring/verification is uncertain.
    """
    if (not db.in_transaction() or db.in_nested_transaction() or db.info.get("tenant_id")!=expected_tenant
            or current_tenant.get() not in {"",expected_tenant}):own.fail(503,"progress_context_unavailable")
    connection=db.connection();original_info=connection.info.get("_tenant_tx_identity")
    original_python_scope=current_tenant.get()
    if connection.in_nested_transaction():own.fail(503,"progress_context_unavailable")
    postgres=connection.dialect.name=="postgresql"
    if postgres:
        original_gucs=tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.client_invitation_digest',true),current_setting('app.mfa_actor',true)")).one())
        old=original_gucs[0]
        if old!=expected_tenant:own.fail(503,"progress_context_unavailable")
    nested=connection.begin_nested()
    try:
        if postgres:connection.execute(text("SELECT set_config('app.current_tenant',:subject,true)"),{"subject":subject})
        yield connection
        if postgres:
            connection.execute(text("SELECT set_config('app.current_tenant',:original,true)"),{"original":old})
            if tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.client_invitation_digest',true),current_setting('app.mfa_actor',true)")).one())!=original_gucs:raise RuntimeError("Progress restoration not confirmed")
        if connection.info.get("_tenant_tx_identity")!=original_info or db.info.get("tenant_id")!=expected_tenant or current_tenant.get()!=original_python_scope:raise RuntimeError("Progress binding changed")
        nested.commit()
    except Exception:
        # ROLLBACK TO restores all LOCAL changes made after this savepoint,
        # including when the aggregate statement aborted the PG transaction.
        try:
            nested.rollback()
            if postgres and tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.client_invitation_digest',true),current_setting('app.mfa_actor',true)")).one())!=original_gucs:
                raise RuntimeError("Progress rollback restoration not confirmed")
            if connection.info.get("_tenant_tx_identity")!=original_info or db.info.get("tenant_id")!=expected_tenant or current_tenant.get()!=original_python_scope:
                raise RuntimeError("Progress rollback binding changed")
        except Exception:
            # A connection with unconfirmed scope is never returned usable to
            # the pool. The service still fails/rolls back its root transaction.
            connection.invalidate()
            raise RuntimeError("Progress restoration unavailable") from None
        raise


def _counts_sql(dialect):
    # Validate the bounded document and structural facts supporting this
    # counter. No nutritional snapshot/food/text crosses the SQL result boundary.
    if dialect=="postgresql":
        return text(r"""
WITH days AS MATERIALIZED (
 SELECT local_date,version,timezone,
  CASE WHEN octet_length(meals_json)<=65536 THEN
       CASE WHEN meals_json IS JSON OBJECT WITH UNIQUE KEYS THEN meals_json::jsonb ELSE NULL END
       ELSE NULL END AS j
 FROM personal_diary_days WHERE user_id=:subject AND local_date BETWEEN :start AND :finish FOR SHARE
), expanded AS (
 SELECT d.local_date,d.version,d.timezone,d.j,e.key,e.value AS snapshot FROM days d
 LEFT JOIN LATERAL jsonb_each(COALESCE(d.j,'{}'::jsonb)) e ON true
), evaluated AS (
 SELECT *,CASE WHEN key IS NULL THEN true ELSE
  key IN ('desayuno','almuerzo','comida','cena') AND jsonb_typeof(snapshot)='object'
  AND snapshot->>'meal'=key AND jsonb_typeof(snapshot->'completed')='boolean'
  AND jsonb_typeof(snapshot->'source_plan_id')='number' AND (snapshot->>'source_plan_id')~'^[1-9][0-9]{0,9}$'
  AND (snapshot->>'source_plan_id')::bigint<=2147483647
  AND jsonb_typeof(snapshot->'recorded_at')='string' AND (snapshot->>'recorded_at')~'(Z|[+-][0-9]{2}:[0-9]{2})$'
  AND (snapshot->>'recorded_at')::timestamptz IS NOT NULL
  AND jsonb_typeof(snapshot->'selections')='object' AND jsonb_typeof(snapshot->'totals')='object'
  AND jsonb_typeof(snapshot->'foods')='array'
  AND (SELECT count(*) FROM jsonb_object_keys(snapshot)) IN (7,8)
  AND NOT EXISTS(SELECT 1 FROM jsonb_object_keys(snapshot) k WHERE k NOT IN ('meal','source_plan_id','completed','recorded_at','selections','totals','foods','source_context'))
  AND NOT EXISTS(SELECT 1 FROM jsonb_each(snapshot->'selections') s WHERE s.key NOT IN ('proteinas','carbohidratos','grasas','include_vegetables','include_fixed_menu')
    OR (s.key IN ('include_vegetables','include_fixed_menu') AND jsonb_typeof(s.value)<>'boolean')
    OR (s.key IN ('proteinas','carbohidratos','grasas') AND NOT (jsonb_typeof(s.value)='null' OR (jsonb_typeof(s.value)='number' AND s.value::text~'^[0-9]+$'))))
  AND (NOT (snapshot ? 'source_context') OR (jsonb_typeof(snapshot->'source_context')='object'
    AND (SELECT count(*) FROM jsonb_object_keys(snapshot->'source_context'))=6
    AND (snapshot->'source_context') ?& ARRAY['kind','link_id','publication_id','link_version','publication_version','published_at']
    AND snapshot->'source_context'->>'kind'='publication'
    AND snapshot->'source_context'->>'link_id'~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
    AND snapshot->'source_context'->>'publication_id'~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
    AND jsonb_typeof(snapshot->'source_context'->'link_version')='number'
    AND jsonb_typeof(snapshot->'source_context'->'publication_version')='number'
    AND (snapshot->'source_context'->>'link_version')~'^[1-9][0-9]{0,9}$'
    AND (snapshot->'source_context'->>'publication_version')~'^[1-9][0-9]{0,9}$'
    AND (snapshot->'source_context'->>'link_version')::bigint BETWEEN 1 AND 2147483647
    AND (snapshot->'source_context'->>'publication_version')::bigint BETWEEN 1 AND 2147483647
    AND snapshot->'source_context'->>'published_at'~'(Z|[+-][0-9]{2}:[0-9]{2})$'
    AND (snapshot->'source_context'->>'published_at')::timestamptz IS NOT NULL))
  AND (SELECT count(*) FROM jsonb_object_keys(snapshot->'totals'))=4
  AND NOT EXISTS(SELECT 1 FROM jsonb_each(snapshot->'totals') m WHERE m.key NOT IN ('kcal','protein_g','carbs_g','fat_g') OR jsonb_typeof(m.value)<>'number' OR (m.value::text)::double precision<0 OR (m.value::text)::double precision>'1.7976931348623157e308'::double precision)
  AND jsonb_array_length(snapshot->'foods')<=32
  AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(snapshot->'foods') f WHERE jsonb_typeof(f)<>'object'
    OR (SELECT count(*) FROM jsonb_object_keys(f))<>4 OR NOT (f ?& ARRAY['food_id','grams','equivalence','macros'])
    OR jsonb_typeof(f->'food_id')<>'string' OR length(f->>'food_id') NOT BETWEEN 1 AND 200
    OR jsonb_typeof(f->'grams')<>'number' OR (f->>'grams')::double precision<=0 OR (f->>'grams')::double precision>'1.7976931348623157e308'::double precision
    OR NOT (jsonb_typeof(f->'equivalence')='null' OR (jsonb_typeof(f->'equivalence')='string' AND length(f->>'equivalence')<=500))
    OR jsonb_typeof(f->'macros')<>'object' OR (SELECT count(*) FROM jsonb_object_keys(f->'macros'))<>4
    OR EXISTS(SELECT 1 FROM jsonb_each(f->'macros') m WHERE m.key NOT IN ('kcal','protein_g','carbs_g','fat_g') OR jsonb_typeof(m.value)<>'number' OR (m.value::text)::double precision<0 OR (m.value::text)::double precision>'1.7976931348623157e308'::double precision))
  AND NOT EXISTS(SELECT 1 FROM jsonb_each(snapshot->'totals') total WHERE total.value::text::numeric IS DISTINCT FROM
    COALESCE((SELECT round(sum((f->'macros'->>total.key)::numeric),1) FROM jsonb_array_elements(snapshot->'foods') f),0))
 END AS valid FROM expanded
)
SELECT local_date,count(key) AS registered,
 count(key) FILTER(WHERE snapshot->'completed'='true'::jsonb) AS completed,
 bool_and(j IS NOT NULL AND version BETWEEN 1 AND 2147483647 AND timezone='America/Mexico_City' AND valid IS TRUE) AS valid
FROM evaluated GROUP BY local_date ORDER BY local_date
""")
    return text(r"""
WITH days AS MATERIALIZED (
 SELECT local_date,version,timezone,
  CASE WHEN length(CAST(meals_json AS BLOB))<=65536 THEN
       CASE WHEN json_valid(meals_json) THEN CASE WHEN json_type(meals_json)='object' THEN meals_json ELSE NULL END ELSE NULL END
       ELSE NULL END AS j
 FROM personal_diary_days WHERE user_id=:subject AND local_date BETWEEN :start AND :finish
), expanded AS (
 SELECT d.*,e.key,e.value AS snapshot FROM days d LEFT JOIN json_each(COALESCE(d.j,'{}')) e ON true
), evaluated AS (
 SELECT *,CASE WHEN key IS NULL THEN 1 ELSE
  key IN ('desayuno','almuerzo','comida','cena') AND json_type(snapshot)='object'
  AND json_extract(snapshot,'$.meal')=key AND json_type(snapshot,'$.completed') IN ('true','false')
  AND json_type(snapshot,'$.source_plan_id')='integer' AND json_extract(snapshot,'$.source_plan_id') BETWEEN 1 AND 2147483647
  AND json_type(snapshot,'$.recorded_at')='text' AND julianday(json_extract(snapshot,'$.recorded_at')) IS NOT NULL
  AND (substr(json_extract(snapshot,'$.recorded_at'),-1)='Z' OR (substr(json_extract(snapshot,'$.recorded_at'),-6,1) IN ('+','-') AND substr(json_extract(snapshot,'$.recorded_at'),-3,1)=':'))
  AND json_type(snapshot,'$.selections')='object' AND json_type(snapshot,'$.totals')='object' AND json_type(snapshot,'$.foods')='array'
  AND (SELECT count(*) FROM json_each(snapshot)) IN (7,8)
  AND (SELECT count(*) FROM json_each(snapshot))=(SELECT count(DISTINCT key) FROM json_each(snapshot))
  AND NOT EXISTS(SELECT 1 FROM json_each(snapshot) x WHERE x.key NOT IN ('meal','source_plan_id','completed','recorded_at','selections','totals','foods','source_context'))
  AND NOT EXISTS(SELECT 1 FROM json_each(snapshot,'$.selections') s WHERE s.key NOT IN ('proteinas','carbohidratos','grasas','include_vegetables','include_fixed_menu')
    OR (s.key IN ('include_vegetables','include_fixed_menu') AND s.type NOT IN ('true','false'))
    OR (s.key IN ('proteinas','carbohidratos','grasas') AND NOT (s.type='null' OR (s.type='integer' AND s.value>=0))))
  AND (json_type(snapshot,'$.source_context') IS NULL OR (json_type(snapshot,'$.source_context')='object'
    AND (SELECT count(*) FROM json_each(snapshot,'$.source_context'))=6
    AND (SELECT count(DISTINCT key) FROM json_each(snapshot,'$.source_context'))=6
    AND NOT EXISTS(SELECT 1 FROM json_each(snapshot,'$.source_context') s WHERE s.key NOT IN ('kind','link_id','publication_id','link_version','publication_version','published_at'))
    AND json_extract(snapshot,'$.source_context.kind')='publication'
    AND length(json_extract(snapshot,'$.source_context.link_id'))=36 AND json_extract(snapshot,'$.source_context.link_id') NOT GLOB '*[^a-f0-9-]*'
    AND substr(json_extract(snapshot,'$.source_context.link_id'),9,1)='-' AND substr(json_extract(snapshot,'$.source_context.link_id'),14,1)='-' AND substr(json_extract(snapshot,'$.source_context.link_id'),19,1)='-' AND substr(json_extract(snapshot,'$.source_context.link_id'),24,1)='-'
    AND length(replace(json_extract(snapshot,'$.source_context.link_id'),'-',''))=32
    AND length(json_extract(snapshot,'$.source_context.publication_id'))=36 AND json_extract(snapshot,'$.source_context.publication_id') NOT GLOB '*[^a-f0-9-]*'
    AND substr(json_extract(snapshot,'$.source_context.publication_id'),9,1)='-' AND substr(json_extract(snapshot,'$.source_context.publication_id'),14,1)='-' AND substr(json_extract(snapshot,'$.source_context.publication_id'),19,1)='-' AND substr(json_extract(snapshot,'$.source_context.publication_id'),24,1)='-'
    AND length(replace(json_extract(snapshot,'$.source_context.publication_id'),'-',''))=32
    AND json_type(snapshot,'$.source_context.link_version')='integer' AND json_extract(snapshot,'$.source_context.link_version') BETWEEN 1 AND 2147483647
    AND json_type(snapshot,'$.source_context.publication_version')='integer' AND json_extract(snapshot,'$.source_context.publication_version') BETWEEN 1 AND 2147483647
    AND julianday(json_extract(snapshot,'$.source_context.published_at')) IS NOT NULL
    AND (substr(json_extract(snapshot,'$.source_context.published_at'),-1)='Z' OR (substr(json_extract(snapshot,'$.source_context.published_at'),-6,1) IN ('+','-') AND substr(json_extract(snapshot,'$.source_context.published_at'),-3,1)=':'))))
  AND (SELECT count(*) FROM json_each(snapshot,'$.totals'))=4
  AND (SELECT count(DISTINCT key) FROM json_each(snapshot,'$.totals'))=4
  AND NOT EXISTS(SELECT 1 FROM json_each(snapshot,'$.totals') m WHERE m.key NOT IN ('kcal','protein_g','carbs_g','fat_g') OR m.type NOT IN ('integer','real') OR m.value<0 OR m.value>1.7976931348623157e308)
  AND json_array_length(snapshot,'$.foods')<=32
  AND NOT EXISTS(SELECT 1 FROM json_each(snapshot,'$.foods') f WHERE f.type<>'object'
    OR (SELECT count(*) FROM json_each(f.value))<>4
    OR (SELECT count(DISTINCT key) FROM json_each(f.value))<>4
    OR EXISTS(SELECT 1 FROM json_each(f.value) x WHERE x.key NOT IN ('food_id','grams','equivalence','macros'))
    OR json_type(f.value,'$.food_id')<>'text' OR length(json_extract(f.value,'$.food_id')) NOT BETWEEN 1 AND 200
    OR json_type(f.value,'$.grams') NOT IN ('integer','real') OR json_extract(f.value,'$.grams')<=0 OR json_extract(f.value,'$.grams')>1.7976931348623157e308
    OR NOT (json_type(f.value,'$.equivalence')='null' OR (json_type(f.value,'$.equivalence')='text' AND length(json_extract(f.value,'$.equivalence'))<=500))
    OR json_type(f.value,'$.macros')<>'object' OR (SELECT count(*) FROM json_each(f.value,'$.macros'))<>4
    OR (SELECT count(DISTINCT key) FROM json_each(f.value,'$.macros'))<>4
    OR EXISTS(SELECT 1 FROM json_each(f.value,'$.macros') m WHERE m.key NOT IN ('kcal','protein_g','carbs_g','fat_g') OR m.type NOT IN ('integer','real') OR m.value<0 OR m.value>1.7976931348623157e308))
  AND NOT EXISTS(SELECT 1 FROM json_each(snapshot,'$.totals') total WHERE total.value IS NOT
    COALESCE((SELECT round(sum(json_extract(f.value,'$.macros.'||total.key)),1) FROM json_each(snapshot,'$.foods') f),0))
 END AS valid FROM expanded
)
SELECT local_date,count(key) AS registered,
 count(CASE WHEN json_type(snapshot,'$.completed')='true' THEN key END) AS completed,
 min(j IS NOT NULL AND version BETWEEN 1 AND 2147483647 AND timezone='America/Mexico_City' AND valid IS 1)
 AND count(key)=count(DISTINCT key) AS valid
FROM evaluated GROUP BY local_date ORDER BY local_date
""")


def _counts(connection,subject,start,end):
    try:
        rows=connection.execute(_counts_sql(connection.dialect.name),{"subject":subject,"start":start,"finish":end}).mappings().all()
    except DBAPIError:
        # The scope wrapper restores via savepoint before the caller sees this.
        own.fail(409,"progress_source_requires_review")
    items=[]
    for row in rows:
        if not row["valid"]:own.fail(409,"progress_source_requires_review")
        registered,completed=row["registered"],row["completed"]
        if type(registered) is not int or type(completed) is not int or not 0<=completed<=registered<=4:own.fail(409,"progress_source_requires_review")
        items.append({"local_date":str(row["local_date"]),"registered_snapshots":registered,"completed_snapshots":completed,
            "ratio":completed/registered if registered else None,"status":"observed" if registered else "no_registered_snapshots"})
    return items


def own_completion(db,principal,*,start=None,end=None,now=None):
    start,end=own.period(start,end,now=now)
    with own.operation(db):
        actor=own.personal(db,principal)
        with _source_connection(db,actor.id,actor.id) as connection:items=_counts(connection,actor.id,start,end)
        return own.bounded({"today":own.local_today(now).isoformat(),"timezone":"America/Mexico_City",
            "from_date":start.isoformat(),"through_date":end.isoformat(),"basis":"completed_of_registered_snapshots","items":items})


def shared_projection(db,principal,client_id,link_id,*,expected_id,expected_version,expected_link,start=None,end=None,limit=100,after=None,now=None):
    from web.services import progress_share as sharing
    own.page_size(limit);start,end=own.period(start,end,now=now)
    if after is not None:own.uuid_text(after)
    with own.operation(db):
        _,gym,link=sharing.professional_context(db,principal,client_id,link_id)
        consent=sharing.authorized_consent(db,link,expected_id,expected_version,expected_link,start,end)
        selected={"peso_kg":consent.share_weight,"grasa_corporal_pct":consent.share_body_fat,"masa_magra_kg":consent.share_lean_mass}
        items=[];counts=[];next_after=None
        with _source_connection(db,gym,link.user_id) as connection:
            if consent.source_profile_id is not None:
                # Lock source identity only; no private profile text is selected.
                query=select(Cliente.id).where(Cliente.gym_id==link.user_id,Cliente.id_cliente==consent.source_profile_id,Cliente.activo.is_(True),Cliente.deleted_at.is_(None)).with_for_update(read=True)
                if connection.scalar(query) is None:own.fail(409,"progress_scope_changed")
            if any(selected.values()):
                columns=[getattr(ClientProgress,name) for name in _FIELDS]+[getattr(ClientProgress,name) for name in selected if selected[name]]
                query=select(*columns).join(Cliente,Cliente.id_cliente==ClientProgress.id_cliente).where(
                    ClientProgress.gym_id==link.user_id,Cliente.gym_id==link.user_id,Cliente.id_cliente==consent.source_profile_id,
                    Cliente.activo.is_(True),Cliente.deleted_at.is_(None),ClientProgress.source_kind=="self_reported",ClientProgress.withdrawn_at.is_(None),
                    ClientProgress.measured_on>=start,ClientProgress.measured_on<=end)
                selected_nonnull=[getattr(ClientProgress,name).is_not(None) for name in selected if selected[name]]
                from sqlalchemy import or_
                query=query.where(or_(*selected_nonnull))
                if after is not None:query=query.where(ClientProgress.record_key>after)
                rows=connection.execute(query.order_by(ClientProgress.record_key).limit(limit+1).with_for_update(read=True,of=ClientProgress)).mappings().all()
                for row in rows[:limit]:
                    values={name:row[name] for name in selected if selected[name]}
                    import math
                    if any(value is not None and (type(value) not in {int,float} or not math.isfinite(value)) for value in values.values()):own.fail(409,"progress_source_requires_review")
                    items.append({"record_key":row["record_key"],"version":row["version"],"source_kind":"self_reported",
                        "measured_on":row["measured_on"].isoformat(),"recorded_at":own.identity.utc(row["recorded_at"]),
                        "values":values,"units":{name:("percent" if name=="grasa_corporal_pct" else "kg") for name in values}})
                if len(rows)>limit:next_after=rows[limit-1]["record_key"]
            if consent.share_completion:counts=_counts(connection,link.user_id,start,end)
        return own.bounded({"link_id":link.id,"link_version":link.version,"consent_id":consent.id,"consent_version":consent.version,
            "from_date":start.isoformat(),"through_date":end.isoformat(),"timezone":"America/Mexico_City",
            "measurements":{"items":items,"next_after":next_after},"completion":{"basis":"completed_of_registered_snapshots","items":counts},
            "categories":sharing.consent_dto(consent)["categories"],"consistency":"live_authorized_read","cached":False})


def native_progress(db,principal,client_id,*,limit=100,after=0):
    from web.services import progress_share as sharing
    own.page_size(limit)
    with own.operation(db):
        _,gym,_=sharing.professional_context(db,principal,client_id)
        # Explicit scalar allowlist: no notes, profile/contact data or raw diary.
        query=select(*[getattr(ClientProgress,name) for name in _FIELDS],ClientProgress.peso_kg,ClientProgress.grasa_corporal_pct,ClientProgress.masa_magra_kg).join(Cliente,Cliente.id_cliente==ClientProgress.id_cliente).where(
            ClientProgress.gym_id==gym,Cliente.gym_id==gym,Cliente.id_cliente==client_id,Cliente.deleted_at.is_(None),ClientProgress.id>after,
            ClientProgress.withdrawn_at.is_(None)).order_by(ClientProgress.id).limit(limit+1)
        rows=db.execute(query).mappings().all()
        return own.bounded({"items":[own.measurement_dto(SimpleNamespace(**row)) for row in rows[:limit]],
            "next_after":rows[limit-1]["id"] if len(rows)>limit else None,"direction":"native_professional_history_only"})
