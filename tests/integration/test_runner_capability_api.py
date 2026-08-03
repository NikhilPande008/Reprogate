import asyncio
from datetime import datetime, timezone

import httpx

from triage.api.main import app
from triage.api.routes.investigations import get_session
from triage.domain.enums import Classification, InvestigationStatus
from triage.persistence.database import Base, create_session_factory
from triage.persistence.models import Investigation


def _seed(tmp_path):
    factory = create_session_factory(f"sqlite:///{tmp_path / 'runners.db'}")
    Base.metadata.create_all(factory.kw["bind"])
    now = datetime.now(timezone.utc)
    with factory() as session:
        session.add(Investigation(
            repository="psf/requests", issue_number=1, test_runner="pytest", status=InvestigationStatus.COMPLETED,
            classification=Classification.BEHAVIOR_GAP_CONFIRMED, asserts_failure=True, created_at=now, updated_at=now,
        ))
        session.add(Investigation(
            repository="psf/requests", issue_number=2, test_runner="pytest", status=InvestigationStatus.COMPLETED_NO_GAP,
            classification=Classification.NEEDS_INFO, asserts_failure=False, created_at=now, updated_at=now,
        ))
        session.commit()
    return factory


def test_capability_matrix_declares_runners_without_claiming_evidence(tmp_path) -> None:
    factory = _seed(tmp_path)

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async def request():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/runners")
                assert response.status_code == 200
                payload = response.json()
                assert payload["schema_version"] == "runner-capability-v1"
                by_id = {item["runner_id"]: item for item in payload["items"]}

                # Implemented adapters are published with their real capability.
                assert by_id["pytest"]["implemented"] and by_id["pytest"]["confirmation_capable"]
                assert by_id["vitest"]["implemented"] and by_id["vitest"]["confirmation_capable"]
                # Jest runs but is deliberately never confirmation-capable.
                assert by_id["jest"]["implemented"] and not by_id["jest"]["confirmation_capable"]
                assert by_id["jest"]["selection_precision"] == "FILE_ONLY"
                # Unimplemented runners are listed rather than silently omitted.
                for runner_id in ("cargo", "go", "junit-java", "rspec"):
                    assert not by_id[runner_id]["implemented"]
                    assert not by_id[runner_id]["confirmation_capable"]

                # Recorded counts come from persisted rows only.
                assert by_id["pytest"]["recorded_investigations"] == 2
                assert by_id["pytest"]["recorded_confirmations"] == 1
                # A capable-but-unexercised runner reports zero, never a blank.
                assert by_id["vitest"]["recorded_investigations"] == 0
                assert by_id["vitest"]["recorded_confirmations"] == 0

                assert any("not evidence" in caveat for caveat in payload["caveats"])

        asyncio.run(request())
    finally:
        app.dependency_overrides.clear()
