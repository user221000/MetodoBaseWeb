"""Original retention criteria with current dashboard seam and task DTO."""
from tests.ci_web37.legacy_current import namespace

_literal = namespace("tests/test_retention_followup.py", __name__)
globals().update({name: value for name, value in _literal.items() if not name.startswith("__")})


def test_empty_current_task_projection_records_no_assignment_or_delivery(followup):
    from sqlalchemy.orm import Session

    from web.database.models import FollowupTask

    response = _literal["read"](followup)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert sum(len(row["per_cause_tasks"]) for row in body["items"]) == 0
    assert body["responsibility"] == "per_cause_tasks"
    assert body["task_coverage"] == "current_open_tasks_by_cause"
    assert body["payment_evidence"] == "unavailable"
    with Session(followup[1]) as db:
        assert db.query(FollowupTask).filter_by(gym_id=followup[2]["id"]).count() == 0
