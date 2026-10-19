"""Bounded summary reads for an already verified personal subject and profile."""
from datetime import datetime

from sqlalchemy import select, tuple_, union_all
from sqlalchemy.orm import Session

from web.database.models import PlanGenerado
from web.services.generation_quota import individual_plan_results_query


def history_summary_rows(
    db: Session,
    subject: str,
    profile: str,
    limit: int,
    position: tuple[datetime | None, int] | None,
):
    """Read at most limit+1 summaries under the caller's existing tenant context.

    The route verifies identity, profile-bound cursor and the 1..200 limit.
    Both tenant predicates and the profile predicate remain on every branch.
    Dated cursors use an indexable row comparison; NULL dates occupy a separate
    bounded branch. One UNION statement gives both branches the same database
    snapshot and sorts at most 2*(limit+1) candidates, without loading plan JSON.
    This read performs no commit, provider call or file access.
    """
    query = individual_plan_results_query(db, subject).filter(
        PlanGenerado.id_cliente == profile
    )
    columns = (
        PlanGenerado.id, PlanGenerado.fecha_generacion,
        PlanGenerado.kcal_objetivo, PlanGenerado.proteina_g,
        PlanGenerado.carbs_g, PlanGenerado.grasa_g, PlanGenerado.tipo_plan,
        PlanGenerado.pdf_object_id, PlanGenerado.ruta_pdf,
    )
    # id is NOT NULL, so explicit NULL placement preserves every result. It
    # matches the new index and avoids a backward primary-key scan filtering
    # other histories in the undated branch (which orders only by id).
    order = (PlanGenerado.fecha_generacion.desc().nulls_last(), PlanGenerado.id.desc().nulls_last())
    if position is None:
        return query.with_entities(*columns).order_by(*order).limit(limit + 1).all()
    stamp, identity = position
    if stamp is None:
        return query.with_entities(*columns).filter(
            PlanGenerado.fecha_generacion.is_(None), PlanGenerado.id < identity,
        ).order_by(*order).limit(limit + 1).all()

    dated = query.with_entities(*columns).filter(
        PlanGenerado.fecha_generacion.is_not(None),
        tuple_(PlanGenerado.fecha_generacion, PlanGenerado.id) < (stamp, identity),
    ).order_by(*order).limit(limit + 1).subquery('dated_page')
    undated = query.with_entities(*columns).filter(
        PlanGenerado.fecha_generacion.is_(None),
    ).order_by(*order).limit(limit + 1).subquery('undated_page')
    candidates = union_all(select(*dated.c), select(*undated.c)).subquery('history_candidates')
    statement = select(*candidates.c).order_by(
        candidates.c.fecha_generacion.desc().nulls_last(), candidates.c.id.desc().nulls_last(),
    ).limit(limit + 1)
    return db.execute(statement).all()
