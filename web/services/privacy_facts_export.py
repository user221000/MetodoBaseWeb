"""Separate bounded personal fact page; portfolio and v1 export stay excluded."""
import re
from sqlalchemy import String, cast, exists, select
from web.database.models import Cliente, PlanGenerado, ProductAnalyticsFact as Fact
from web.services.personal_diary_persistence import require_personal_subject
from web.services.privacy_export import MAX_PAGE_SIZE, MAX_SECTION_BYTES, _encoded_size, _value
from fastapi import HTTPException

FIELDS=('id','event_type','source_id','source_version','origin','occurred_at')


def export_personal_facts(db,subject_id,*,limit=100,after=None):
    if type(limit) is not int or not 1<=limit<=MAX_PAGE_SIZE:
        raise ValueError('Invalid fact page size')
    if after is not None and (not isinstance(after,str) or re.fullmatch('[0-9A-Fa-f]{32}',after) is None):
        raise ValueError('Invalid exact fact keyset cursor')
    require_personal_subject(db,subject_id)
    own_profiles=select(Cliente.id_cliente).where(Cliente.gym_id==subject_id)
    own_source=exists(select(PlanGenerado.id).where(PlanGenerado.gym_id==subject_id,
        PlanGenerado.id_cliente.in_(own_profiles),cast(PlanGenerado.id,String)==Fact.source_id))
    query=select(*(getattr(Fact,name) for name in FIELDS)).where(Fact.owner_id==subject_id,Fact.context=='personal',
        ((Fact.event_type=='origin_declared') & (Fact.source_id==subject_id)) |
        ((Fact.event_type=='plan_saved') & own_source))
    if after is not None:query=query.where(Fact.id>after)
    rows=db.execute(query.order_by(Fact.id).limit(limit+1)).mappings()
    records=[];used=512;has_more=False
    try:
        for row in rows:
            if len(records)==limit:has_more=True;break
            item={name:_value(row[name]) for name in FIELDS}
            size=_encoded_size(item)+1
            if used+size>MAX_SECTION_BYTES:
                if not records:raise HTTPException(413,{'code':'privacy_fact_requires_review'})
                has_more=True;break
            records.append(item);used+=size
    finally:rows.close()
    return {'format_version':1,'scope':'own_personal_product_facts','consistency':'live_keyset_pages',
        'coverage':'typed_origin_and_plan_facts_with_current_own_source',
        'excluded_categories':['professional_portfolio','foreign_sources','unresolved_legacy_sources'],
        'max_response_bytes':MAX_SECTION_BYTES,'page_size':limit,
        'records':records,'next_after':records[-1]['id'] if has_more else None}
