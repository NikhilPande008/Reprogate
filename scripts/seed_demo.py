"""Install the committed, read-only dashboard demo without API keys."""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATABASE = ROOT / "demo" / "seed" / "triage-demo.db"
SOURCE_ARTIFACTS = ROOT / "demo" / "seed" / "artifacts"

sys.path.insert(0, str(ROOT))


@contextlib.contextmanager
def _working_directory(path: Path):
    """Persisted artifact paths are root-relative; resolve them from one place."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def build_similarity_index(database: Path, artifacts: Path) -> tuple[int, int]:
    """Compute advisory similarity locally: no embeddings, no network, no cost.

    Without this the dashboard reports duplicate analysis as unavailable, which
    is indistinguishable from the feature being broken. Running it makes the
    honest result visible: an analysis that completed and found no near
    duplicate is not the same as an analysis that never ran.
    """
    from triage.config.settings import Settings
    from triage.persistence import create_session_factory
    from triage.persistence.models import Investigation
    from triage.similarity.service import DuplicateSimilarityService
    from sqlalchemy import select

    settings = Settings(database_url=f"sqlite:///{database}")
    factory = create_session_factory(settings.database_url)
    documents = candidates = 0
    with factory() as session, _working_directory(artifacts.parent):
        service = DuplicateSimilarityService(session, settings)
        for investigation in session.scalars(select(Investigation)):
            if investigation.status.value != "COMPLETED":
                continue
            candidates += len(service.analyze(investigation.id))
            documents += 1
    return documents, candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the committed dashboard demo data.")
    parser.add_argument("--database", type=Path, default=ROOT / "triage.db")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--force", action="store_true", help="Replace existing demo destinations.")
    parser.add_argument("--skip-similarity", action="store_true", help="Do not build the local similarity index.")
    args = parser.parse_args()
    destinations = (args.database, args.artifacts)
    existing = [path for path in destinations if path.exists()]
    if existing and not args.force:
        parser.error("destination exists; pass --force to replace: " + ", ".join(str(path) for path in existing))
    if args.database.exists():
        args.database.unlink()
    if args.artifacts.exists():
        shutil.rmtree(args.artifacts)
    args.database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_DATABASE, args.database)
    shutil.copytree(SOURCE_ARTIFACTS, args.artifacts)
    print(f"Installed demo database at {args.database} and artifacts at {args.artifacts}.")
    if not args.skip_similarity:
        documents, candidates = build_similarity_index(args.database, args.artifacts)
        print(f"Indexed {documents} investigation(s) for advisory similarity; {candidates} related pair(s) met the configured threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
