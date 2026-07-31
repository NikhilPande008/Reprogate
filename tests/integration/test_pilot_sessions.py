import base64
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from triage.api.main import app
from triage.api.routes.investigations import get_session
from triage.domain.enums import Classification, InvestigationStatus
from triage.persistence.database import Base, create_session_factory
from triage.persistence.models import Investigation, ReviewPacket
from triage.review_packets import canonical_json, packet_hash


def test_pilot_login_uses_httponly_cookie_csrf_and_logout(monkeypatch) -> None:
    monkeypatch.setenv("PILOT_REVIEW_ENABLED", "true")
    monkeypatch.setenv("PILOT_SESSION_SECURE_COOKIE", "false")
    monkeypatch.setenv("PILOT_REVIEWER_REGISTRY", json.dumps({"reviewer-a": {"cohort": "MAINTAINER", "token": "secret", "posting_approver": True}}))
    with TestClient(app) as client:
        assert client.get("/pilot-review/queue").status_code == 401
        assert client.post("/pilot-review/login", json={"reviewer_id": "reviewer-a", "token": "wrong"}).status_code == 403
        login = client.post("/pilot-review/login", json={"reviewer_id": "reviewer-a", "token": "secret"})
        assert login.status_code == 200
        assert "secret" not in login.text
        cookie = login.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie
        csrf = login.json()["csrf_token"]
        assert client.get("/pilot-review/me").json()["reviewer"]["external_id"] == "reviewer-a"
        assert client.post("/pilot-review/logout").status_code == 403
        assert client.post("/pilot-review/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        assert client.get("/pilot-review/me").status_code == 401


def test_disabled_pilot_has_no_login_or_queue(monkeypatch) -> None:
    monkeypatch.setenv("PILOT_REVIEW_ENABLED", "false")
    with TestClient(app) as client:
        assert client.post("/pilot-review/login", json={"reviewer_id": "x", "token": "x"}).status_code == 404
        assert client.get("/pilot-review/queue").status_code == 404


def test_basic_auth_is_repository_scoped_and_never_echoes_credentials(tmp_path, monkeypatch) -> None:
    factory = create_session_factory(f"sqlite:///{tmp_path / 'pilot-auth.db'}")
    Base.metadata.create_all(factory.kw["bind"])
    with factory() as session:
        allowed = Investigation(repository="owner/allowed", issue_number=1, status=InvestigationStatus.COMPLETED, classification=Classification.NEEDS_INFO)
        denied = Investigation(repository="owner/denied", issue_number=2, status=InvestigationStatus.COMPLETED, classification=Classification.NEEDS_INFO)
        session.add_all((allowed, denied)); session.flush()
        packet_ids = []
        for investigation in (allowed, denied):
            snapshot = {"investigation": {"id": investigation.id}}
            packet = ReviewPacket(investigation_id=investigation.id, version=1, schema_version="1.0", snapshot_json=canonical_json(snapshot), integrity_hash=packet_hash(snapshot), created_at=datetime.now(timezone.utc))
            session.add(packet); session.flush(); packet_ids.append(packet.id)
        session.commit()

    def override_session():
        with factory() as session:
            yield session

    monkeypatch.setenv("PILOT_REVIEW_ENABLED", "true")
    monkeypatch.setenv("PILOT_REVIEWER_REGISTRY", json.dumps({"reviewer-a": {"cohort": "MAINTAINER", "token": "basic-secret", "repositories": ["owner/allowed"]}}))
    header = "Basic " + base64.b64encode(b"reviewer-a:basic-secret").decode("ascii")
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            allowed_response = client.get(f"/pilot-review/packets/{packet_ids[0]}", headers={"Authorization": header})
            assert allowed_response.status_code == 200
            assert "basic-secret" not in allowed_response.text
            assert client.get(f"/pilot-review/packets/{packet_ids[1]}", headers={"Authorization": header}).status_code == 404
    finally:
        app.dependency_overrides.clear()
