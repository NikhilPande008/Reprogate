import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from triage.api.routes.investigations import get_session
from triage.persistence.models import Investigation
from triage.retrospective_evaluation import DatasetError, load

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
DATASET = Path(__file__).resolve().parents[3] / "demo" / "evaluations" / "retrospective-v1.json"
STATUS = Path(__file__).resolve().parents[3] / "demo" / "evaluations" / "evaluation-status-v1.json"


@router.get("/status")
def status() -> dict:
    """Return the explicit, non-accuracy evaluation status for public display."""
    try:
        value = json.loads(STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": "evaluation-status-v1", "corpus_version": None, "sample_size": 0, "reviewer_count": 0, "unresolved_cases": 0, "measured_metrics": [], "known_exclusions": ["Evaluation status data is unavailable."], "preliminary": True}
    return value if isinstance(value, dict) else {"schema_version": "evaluation-status-v1", "corpus_version": None, "sample_size": 0, "reviewer_count": 0, "unresolved_cases": 0, "measured_metrics": [], "known_exclusions": ["Evaluation status data is invalid."], "preliminary": True}


@router.get("/retrospective")
def retrospective(session: Session = Depends(get_session)) -> dict:
    ids = set(session.scalars(select(Investigation.id)))
    try: data = load(DATASET, ids)
    except DatasetError as error: return {"status": "invalid", "reason": str(error)}
    return {"status": "no_data" if not data["cases"] else "available", "dataset": data}
