"""Independent privacy boundaries for persisted ownership and legacy cursors."""
import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tests.test_privacy_export import privacy_case, request_export


def test_owner_authority_excludes_portfolio_even_with_individual_persisted_type(privacy_case):
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole

    with Session(get_engine()) as db:
        owner = db.get(Usuario, privacy_case[1]["owner"])
        owner.tipo = "usuario"
        assert owner.role == UserRole.OWNER and owner.team_gym_id is None
        db.commit()
    response = request_export(privacy_case, "owner")
    assert response.status_code == 200
    assert response.json()["scope"]["personal_space"] is False
    assert response.json()["profiles"]["records"] == []
    assert "own-health-note-owner" not in response.text


@pytest.mark.parametrize("section,cursor", [("purchases", "after_purchase"), ("generation_requests", "after_generation")])
def test_valid_uppercase_uuid_cursors_do_not_omit_persisted_records(privacy_case, section, cursor):
    from web.database.engine import get_engine
    from web.database.models import PurchaseIntent, GenerationReservation

    model = PurchaseIntent if section == "purchases" else GenerationReservation
    subject = privacy_case[1]["member"]
    ids = [f"{letter * 8}-{letter * 4}-4{letter * 3}-8{letter * 3}-{letter * 12}" for letter in "ABC"]
    with Session(get_engine()) as db:
        predicate = model.subject_id == subject if section == "purchases" else model.user_id == subject
        db.execute(delete(model).where(predicate))
        for index, record_id in enumerate(ids):
            if section == "purchases":
                record = PurchaseIntent(id=record_id, subject_id=subject, provider="stripe", operation="checkout",
                    request_key="synthetic-review-purchase-" + str(index), plan="pro_usuario", amount_cents=7900)
            else:
                record = GenerationReservation(id=record_id, user_id=subject,
                    request_key="synthetic-review-generation-" + str(index), period="2026-10", status="released")
            db.add(record)
        db.commit()
        expected = list(db.scalars(select(model.id).where(predicate).order_by(model.id)))
    seen, after = [], None
    for _ in range(5):
        params = {"limit": 1}
        if after is not None:
            params[cursor] = after
        response = request_export(privacy_case, **params)
        assert response.status_code == 200
        page = response.json()[section]
        seen.extend(row["id"] for row in page["records"])
        after = page["next_after"]
        if after is None:
            break
    assert seen == expected
