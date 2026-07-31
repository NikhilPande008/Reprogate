"""Regression coverage for the committed offline dashboard seed."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from triage.api.main import app


ROOT = Path(__file__).resolve().parents[2]


def test_committed_demo_seed_serves_the_flagship_semantic_review(tmp_path, monkeypatch) -> None:
    database = tmp_path / "triage-demo.db"
    shutil.copy2(ROOT / "demo" / "seed" / "triage-demo.db", database)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    with TestClient(app) as client:
        investigations = client.get("/investigations?page_size=100")
        assert investigations.status_code == 200
        flagship = next(item for item in investigations.json()["items"] if item["repository"] == "psf/requests" and item["issue_number"] == 7564)
        response = client.get(f"/investigations/{flagship['id']}/semantic-review")
    assert response.status_code == 200
    payload = response.json()
    assert payload["packet_status"] == "AVAILABLE"
    assert payload["review"] is not None
