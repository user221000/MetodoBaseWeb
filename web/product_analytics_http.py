"""Record only after the authorized HTTP200 body was accepted by ASGI send."""
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from web.services.product_facts import assigned_plan_served


class AssignedPlanResponse(JSONResponse):
    def __init__(self, content, principal, link_id, *, headers=None):
        super().__init__(content, headers=headers)
        # Keep only claims needed for revalidation; never copy bearer/contact data.
        self._actor = {k: principal.get(k) for k in ("id", "tipo", "role", "team_gym_id", "session_version")}
        self._link = link_id
        publication = content.get("publication")
        self._publication = (publication["id"], publication["version"]) if publication else None

    async def __call__(self, scope, receive, send):
        await super().__call__(scope, receive, send)
        if self.status_code == 200 and self._publication is not None:
            await run_in_threadpool(assigned_plan_served, self._actor, self._link, *self._publication)
