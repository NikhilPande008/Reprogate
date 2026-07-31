from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from triage.api.routes.artifacts import router as artifacts_router
from triage.api.routes.investigations import router as investigations_router, review_packets_router, pilot_router
from triage.api.routes.webhooks import router as webhooks_router
from triage.api.routes.live_demo import router as live_demo_router
from triage.api.routes.evaluation import router as evaluation_router
from triage.config.settings import Settings
from triage.core.logging import configure_logging
from triage.persistence.database import create_session_factory

settings = Settings()
configure_logging(settings.log_level)

app = FastAPI()
app.include_router(investigations_router)
app.include_router(review_packets_router)
app.include_router(pilot_router)
app.include_router(artifacts_router)
app.include_router(webhooks_router)
app.include_router(live_demo_router)
app.include_router(evaluation_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Database readiness for a single-pilot deployment; does not mutate state."""
    try:
        with create_session_factory(Settings().database_url)() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="database unavailable") from error
    return {"status": "ready", "database": "reachable"}
