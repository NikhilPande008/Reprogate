from datetime import datetime, timezone

from triage.domain.enums import AssessmentConfidence, AssessmentJudgment, Classification, InvestigationStatus, ReviewerCohort
from triage.persistence.database import Base, create_session_factory
from triage.persistence.models import Investigation, ReviewPacket
from triage.review_assessments import PilotReviewer, ReviewAssessmentService
from triage.review_packets import canonical_json, packet_hash
from triage.semantic_alignment_report import SemanticAlignmentReportService, wilson_interval


def _packet(session, issue_number: int) -> ReviewPacket:
    investigation = Investigation(repository="owner/repo", issue_number=issue_number, status=InvestigationStatus.COMPLETED, classification=Classification.NEEDS_INFO)
    session.add(investigation); session.flush()
    snapshot = {"investigation": {"id": investigation.id}}
    packet = ReviewPacket(investigation_id=investigation.id, version=1, schema_version="1.0", snapshot_json=canonical_json(snapshot), integrity_hash=packet_hash(snapshot), created_at=datetime.now(timezone.utc))
    session.add(packet); session.commit()
    return packet


def _assess(session, packet: ReviewPacket, reviewer: str, cohort: ReviewerCohort, answers) -> None:
    ReviewAssessmentService(session).create(packet.id, PilotReviewer(reviewer, cohort), extraction_aligned=answers[0], test_aligned=answers[1], failure_supports_signal=answers[2], public_comment_appropriate=answers[3], confidence=AssessmentConfidence.HIGH, rationale="Recorded local adjudication.")


def test_interim_report_requires_full_coverage_and_preserves_disagreement(tmp_path) -> None:
    factory = create_session_factory(f"sqlite:///{tmp_path / 'alignment.db'}"); Base.metadata.create_all(factory.kw["bind"])
    with factory() as session:
        aligned = _packet(session, 1)
        yes = (AssessmentJudgment.YES,) * 4
        for reviewer, cohort in (("m1", ReviewerCohort.MAINTAINER), ("e1", ReviewerCohort.INDEPENDENT_ENGINEER), ("e2", ReviewerCohort.INDEPENDENT_ENGINEER)):
            _assess(session, aligned, reviewer, cohort, yes)
        disagreed = _packet(session, 2)
        _assess(session, disagreed, "m2", ReviewerCohort.MAINTAINER, yes)
        _assess(session, disagreed, "e3", ReviewerCohort.INDEPENDENT_ENGINEER, yes)
        _assess(session, disagreed, "e4", ReviewerCohort.INDEPENDENT_ENGINEER, (AssessmentJudgment.YES, AssessmentJudgment.NO, AssessmentJudgment.YES, AssessmentJudgment.YES))
        pending = _packet(session, 3)
        _assess(session, pending, "m3", ReviewerCohort.MAINTAINER, yes)
        report = SemanticAlignmentReportService(session).generate("owner/repo", datetime(2026, 7, 24, tzinfo=timezone.utc))
        assert report["counts"]["packets"] == 3
        assert report["counts"]["packets_issued"] == 3
        assert report["counts"]["pending_review"] == 1
        assert report["counts"]["fully_adjudicated"] == 2
        assert report["counts"]["aligned"] == 1
        assert report["counts"]["disagreed"] == 1
        assert report["alignment_rate"] == 0.5
        assert report["publication_status"] == "INSUFFICIENT_SAMPLE"


def test_wilson_interval_is_empty_without_adjudications() -> None:
    assert wilson_interval(0, 0) == (None, None)
