"""Own consent event metadata export; never source-gym portfolio information."""
import json

from sqlalchemy import select
from web.database.models import ProgressConsent
from web.services.progress_share import consent_dto
from web.services.personal_progress import fail


def export_progress_consents(db,subject_id,*,limit,after=None,maximum_bytes):
    query=select(ProgressConsent).where(ProgressConsent.user_id==subject_id)
    if after is not None:query=query.where(ProgressConsent.id>after)
    rows=db.scalars(query.order_by(ProgressConsent.id).limit(limit+1))
    records=[];used=256;more=False
    try:
        for row in rows:
            if len(records)==limit:more=True;break
            item={"link_id":row.link_id,**consent_dto(row)}
            size=len(json.dumps(item,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8"))+1
            if used+size>maximum_bytes:
                if not records:fail(413,"privacy_record_requires_review")
                more=True;break
            records.append(item);used+=size
    finally:rows.close()
    return {"records":records,"next_after":records[-1]["id"] if more else None}
