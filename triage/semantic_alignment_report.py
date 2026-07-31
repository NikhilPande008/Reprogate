"""Local, deterministic interim semantic-fidelity measurement."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from triage.domain.enums import ConsensusState
from triage.persistence.models import Investigation, ReviewPacket
from triage.review_consensus import ReviewConsensusService


REPORT_VERSION = "1.0"
TARGET_FULLY_ADJUDICATED_EXAMPLES = 50
WILSON_Z_95 = 1.959963984540054


def wilson_interval(successes: int, total: int, z: float = WILSON_Z_95) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


class SemanticAlignmentReportService:
    """Summarize only human-adjudicated semantic fidelity; never alter verdicts."""

    def __init__(self, session: Session):
        self.session = session

    def generate(self, repository: str | None = None, now: datetime | None = None) -> dict[str, object]:
        statement = select(ReviewPacket).join(Investigation, ReviewPacket.investigation_id == Investigation.id).order_by(ReviewPacket.created_at, ReviewPacket.id)
        if repository:
            statement = statement.where(Investigation.repository == repository)
        packets = list(self.session.scalars(statement))
        consensus = ReviewConsensusService(self.session)
        states: dict[str, int] = {}
        full_coverage = aligned = disagreement = 0
        for packet in packets:
            result = consensus.current(packet.id)
            state = str(result["state"])
            states[state] = states.get(state, 0) + 1
            coverage = result.get("coverage", {})
            covered = isinstance(coverage, dict) and coverage.get("MAINTAINER", 0) >= 1 and coverage.get("INDEPENDENT_ENGINEER", 0) >= 2
            if not covered:
                continue
            full_coverage += 1
            if state == ConsensusState.UNANIMOUSLY_ALIGNED.value:
                aligned += 1
            if state == ConsensusState.DISAGREED.value:
                disagreement += 1
        lower, upper = wilson_interval(aligned, full_coverage)
        rate = aligned / full_coverage if full_coverage else None
        publishable = full_coverage >= TARGET_FULLY_ADJUDICATED_EXAMPLES
        return {
            "semantic_alignment_report_version": REPORT_VERSION,
            "repository": repository,
            "source_cutoff_at": (now or datetime.now(timezone.utc)).isoformat(),
            "measurement": {
                "definition": "Alignment is a fully covered packet with unanimous YES judgments for extraction, test, failure signal, and suggested response.",
                "cohort_requirement": "At least one MAINTAINER and two INDEPENDENT_ENGINEER assessments on the same immutable packet.",
                "confidence_interval": "Two-sided Wilson 95% confidence interval.",
            },
            "counts": {
                "packets_issued": len(packets),
                "packets": len(packets),
                "pending_review": states.get(ConsensusState.PENDING_REVIEW.value, 0),
                "fully_adjudicated": full_coverage,
                "aligned": aligned,
                "disagreed": disagreement,
                "consensus_states": states,
            },
            "alignment_rate": rate,
            "alignment_rate_wilson_95": {"lower": lower, "upper": upper},
            "target": {"fully_adjudicated_examples": TARGET_FULLY_ADJUDICATED_EXAMPLES, "remaining": max(0, TARGET_FULLY_ADJUDICATED_EXAMPLES - full_coverage)},
            "publication_status": "READY_FOR_INTERIM_RATE" if publishable else "INSUFFICIENT_SAMPLE",
            "caveats": [
                "Human semantic review is separate from deterministic validation and does not change an investigation verdict.",
                "This is pilot measurement, not an accuracy or customer-value claim.",
                "Disagreement and insufficient-context outcomes remain visible in the state distribution.",
            ],
        }
