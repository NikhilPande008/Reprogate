from fastapi.testclient import TestClient

from triage.api.main import app


def test_evaluation_status_is_explicitly_preliminary() -> None:
    with TestClient(app) as client:
        response = client.get("/evaluation/status")
    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "evaluation-status-v1",
        "corpus_version": None,
        "sample_size": 0,
        "reviewer_count": 0,
        "unresolved_cases": 0,
        "measured_metrics": [],
        "known_exclusions": [
            "No frozen, representative accuracy corpus has been run.",
            "No independent dual-review labels or adjudications have been collected.",
            "The retrospective sample and seeded demonstrations are product examples, not evaluation evidence.",
        ],
        "preliminary": True,
    }
