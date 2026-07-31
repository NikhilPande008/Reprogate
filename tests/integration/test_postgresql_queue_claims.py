"""PostgreSQL-only coverage for repository-scoped queue claims.

Set TEST_POSTGRESQL_URL to an isolated local database URL to run this test.
It deliberately never falls back to a remote or production database.
"""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.orm import sessionmaker

from triage.domain.enums import WebhookJobStatus
from triage.persistence.database import Base, create_engine_from_url
from triage.persistence.models import WebhookJob
from triage.persistence.repositories import WebhookJobRepository


POSTGRESQL_URL = os.getenv("TEST_POSTGRESQL_URL")


@pytest.mark.skipif(not POSTGRESQL_URL, reason="set TEST_POSTGRESQL_URL to run against local PostgreSQL")
def test_postgresql_claims_enforce_the_per_repository_limit() -> None:
    assert POSTGRESQL_URL is not None
    engine = create_engine_from_url(POSTGRESQL_URL)
    assert engine.dialect.name == "postgresql"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as session:
            jobs = WebhookJobRepository(session)
            jobs.enqueue_batch("owner/repository", 1)
            jobs.enqueue_batch("owner/repository", 2)
            session.commit()

        def claim(owner: str):
            with factory() as session:
                return WebhookJobRepository(session).claim_next(owner, 60, per_repository_limit=1)

        with ThreadPoolExecutor(max_workers=2) as executor:
            claims = list(executor.map(claim, ("worker-one", "worker-two")))

        assert sum(job is not None for job in claims) == 1
        with factory() as session:
            running = session.query(WebhookJob).filter_by(
                repository="owner/repository", status=WebhookJobStatus.RUNNING
            ).count()
        assert running == 1
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
