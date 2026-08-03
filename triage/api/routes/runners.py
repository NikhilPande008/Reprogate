"""Read-only publication of the declared test-runner capability matrix."""

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import Depends

from triage.api.routes.investigations import get_session
from triage.persistence.models import Investigation
from triage.runners import runner_capabilities

router = APIRouter(prefix="/runners", tags=["runners"])

CAVEATS = (
    "This matrix declares implemented adapter capability. It is not evidence that any particular investigation confirmed a behavior gap.",
    "A confirmation-capable runner still reaches BEHAVIOR_GAP_CONFIRMED only when every deterministic gate passes.",
    "Unimplemented runners fail selection explicitly and are never guessed at.",
)


@router.get("")
def capability_matrix(session: Session = Depends(get_session)) -> dict:
    """Return declared runner capability alongside locally recorded usage.

    Recorded counts come from persisted investigations only. A runner with zero
    recorded investigations is reported as zero rather than hidden, so declared
    capability is never mistaken for demonstrated evidence.
    """
    recorded = dict(
        session.execute(
            select(Investigation.test_runner, func.count(Investigation.id)).group_by(Investigation.test_runner)
        ).all()
    )
    items = []
    for item in runner_capabilities():
        confirmations = 0
        if item["runner_id"] in recorded:
            confirmations = int(
                session.scalar(
                    select(func.count(Investigation.id)).where(
                        Investigation.test_runner == item["runner_id"],
                        Investigation.asserts_failure.is_(True),
                    )
                )
                or 0
            )
        items.append({**item, "recorded_investigations": int(recorded.get(item["runner_id"], 0) or 0), "recorded_confirmations": confirmations})
    return {"schema_version": "runner-capability-v1", "items": items, "caveats": list(CAVEATS)}
