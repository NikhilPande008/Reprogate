"""Local-only PostgreSQL coverage for the single-pilot control path."""

import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from triage.budget import BudgetExceeded, BudgetService
from triage.api.main import app
from triage.config.settings import Settings
from triage.persistence.database import Base, create_engine_from_url
from triage.persistence.models import Investigation
from triage.persistence.repositories import WebhookJobRepository


POSTGRESQL_URL = os.getenv("TEST_POSTGRESQL_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRESQL_URL, reason="set TEST_POSTGRESQL_URL to an isolated local PostgreSQL database"
)


def _engine():
    assert POSTGRESQL_URL is not None
    engine = create_engine_from_url(POSTGRESQL_URL)
    assert engine.dialect.name == "postgresql"
    return engine


def _reset(engine) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_alembic_migrates_a_local_postgresql_database(monkeypatch) -> None:
    assert POSTGRESQL_URL is not None
    engine = _engine()
    Base.metadata.drop_all(engine)
    monkeypatch.setenv("DATABASE_URL", POSTGRESQL_URL)
    command.upgrade(Config("alembic.ini"), "head")
    assert {"investigations", "webhook_jobs", "review_packets"} <= set(inspect(engine).get_table_names())
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_two_workers_can_claim_two_jobs_but_not_a_third_for_one_repository() -> None:
    engine = _engine(); _reset(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as session:
            jobs = WebhookJobRepository(session)
            for issue in (1, 2, 3):
                jobs.enqueue_batch("owner/repository", issue)

        def claim(owner: str):
            with factory() as session:
                return WebhookJobRepository(session).claim_next(owner, 60, per_repository_limit=2)

        with ThreadPoolExecutor(max_workers=3) as executor:
            claims = list(executor.map(claim, ("one", "two", "three")))
        assert sum(job is not None for job in claims) == 2
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_advisory_lock_prevents_concurrent_repository_over_reservation() -> None:
    engine = _engine(); _reset(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        budget_openai_per_investigation_usd=Decimal("1.00"),
        budget_openai_repository_daily_usd=Decimal("0.10"),
        budget_openai_repository_monthly_usd=Decimal("1.00"),
        budget_openai_reservation_usd=Decimal("0.10"),
    )
    try:
        with factory() as session:
            first, second = Investigation(repository="owner/repository", issue_number=1), Investigation(repository="owner/repository", issue_number=2)
            session.add_all((first, second)); session.commit()
            ids = (first.id, second.id)

        def reserve(investigation_id: str) -> bool:
            with factory() as session:
                try:
                    BudgetService(session, settings).reserve_openai(investigation_id)
                    return True
                except BudgetExceeded:
                    return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(reserve, ids))
        assert outcomes.count(True) == 1
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_ready_reports_reachable_postgresql_and_unavailable_database(monkeypatch) -> None:
    assert POSTGRESQL_URL is not None
    engine = _engine(); _reset(engine)
    try:
        monkeypatch.setenv("DATABASE_URL", POSTGRESQL_URL)
        with TestClient(app) as client:
            assert client.get("/ready").json() == {"status": "ready", "database": "reachable"}
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://127.0.0.1:1/unavailable")
        with TestClient(app) as client:
            assert client.get("/ready").status_code == 503
    finally:
        Base.metadata.drop_all(engine); engine.dispose()
