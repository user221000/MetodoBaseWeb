"""Bounded recipient metadata export; independent of personal-space authority."""
from sqlalchemy import and_

from web.database.models import ClientAccountLink,ClientPlanPublication,Usuario,UserRole
from web.services.client_link_context import canonical_gym,utc,valid_actor
from web.services.client_link_plans import member_link_query


def export_member_links(db,user,*,limit,after=None,maximum_bytes):
    from web.services.privacy_export import _encoded_size
    from fastapi import HTTPException
    parent=db.get(Usuario,user.team_gym_id) if user.team_gym_id else None
    if not valid_actor(user,parent) or (user.role==UserRole.OWNER and not canonical_gym(user)):
        return {'records':[],'next_after':None}
    query=member_link_query(user.id).add_columns(ClientPlanPublication.id.label('publication_id'),
        ClientPlanPublication.publication_version,ClientPlanPublication.published_at)
    query=query.outerjoin(ClientPlanPublication,and_(ClientPlanPublication.link_id==ClientAccountLink.id,
        ClientPlanPublication.gym_id==ClientAccountLink.gym_id,ClientPlanPublication.client_id==ClientAccountLink.client_id,
        ClientPlanPublication.status=='published'))
    if after is not None:query=query.where(ClientAccountLink.id>after)
    rows=db.execute(query.order_by(ClientAccountLink.id).limit(limit+1).execution_options(yield_per=1))
    records=[];used=256;has_more=False
    try:
        for row in rows:
            if len(records)==limit:has_more=True;break
            link=row[0]
            item={'id':link.id,'status':link.status,'version':link.version,'gym_name':link.gym_name,
                'client_display_name':link.client_display_name,'accepted_at':utc(link.accepted_at),
                'publication':{'id':row.publication_id,'version':row.publication_version,'published_at':utc(row.published_at)}
                    if row.publication_id else None}
            size=_encoded_size(item)+1
            if used+size>maximum_bytes:
                if not records:
                    raise HTTPException(413,{'code':'privacy_record_requires_review','message':'Un registro supera el volumen de descarga.'})
                has_more=True;break
            used+=size;records.append(item)
    finally:rows.close()
    return {'records':records,'next_after':records[-1]['id'] if has_more else None}
