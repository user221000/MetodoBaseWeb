"""Existing best-effort notification with an authorized private PDF read.

This background task is not a durable outbox. R28 tracks delivery/retry policy;
no object key, filesystem path or bearer credential is sent to the recipient.
"""
import logging

from web.database.tenant_context import tenant_task


@tenant_task("gym_id")
def notify_plan_generated(email: str, nombre_cliente: str, gym_id: str, plan_id: int) -> bool:
    from sqlalchemy.orm import Session
    from web.database.engine import get_engine
    from web.services.plan_documents import read_plan_pdf
    from web.services.email_service import send_plan_generated

    try:
        with Session(get_engine()) as db:
            content = read_plan_pdf(db, gym_id, plan_id)
        return send_plan_generated(email, nombre_cliente, pdf_content=content)
    except Exception as error:
        logging.getLogger(__name__).warning("Plan notification unavailable class=%s", type(error).__name__)
        return False
