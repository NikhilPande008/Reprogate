# Pilot baseline report

Date: 2026-07-25  
Scope: `/Users/nikhil/Projects/github issue triage-pilot` only. The frozen
source copy was not modified. This report is local-only and records no GitHub,
deployment, image-pull, or external-data activity.

## Verified local baseline

| Check | Result |
| --- | --- |
| Backend test suite | 209 passed, 3 intentional environment-dependent skips |
| Dashboard test suite | 17 files / 38 tests passed |
| Dashboard production build | Passed |
| Alembic head | `0023_live_demo_progress` |
| Local PostgreSQL queue-claim test | Passed on a temporary PostgreSQL 16 cluster; the cluster was stopped and removed |
| Docker daemon | Unavailable (`~/.docker/run/docker.sock` is absent) |

## Implemented in the pilot copy

- Semantic review packets support backfill; a deterministic interim alignment
  report measures fully adjudicated, aligned, disagreed, and remaining-to-50
  counts without changing any investigation verdict.
- Queue claims and OpenAI budget reservations use PostgreSQL advisory locks
  keyed by normalized repository. SQLite remains local single-host only.
- Pilot review remains feature-gated and repository-scoped. Existing header
  credentials and HTTP Basic credentials are supported; browser session routes
  distinguish a missing identity (`401`) from invalid supplied credentials
  (`403`).
- Sandbox setup profiles use pinned `uv` and Poetry versions. The offline
  readiness report resolves manifests without cloning, installing, or running
  repository code.
- Pytest and the conservative static-top-level Vitest subset can supply
  confirmation-grade structured evidence. Jest and ambiguous Vitest selection
  remain diagnostic-only.

## Locally tested but incomplete for the single-pilot path

- The PostgreSQL concurrency test verifies one running job with a
  per-repository limit of one. It does **not** yet prove the required limit of
  two, migration compatibility, or budget over-reservation prevention.
- `/ready` has no dedicated integration coverage yet, including its PostgreSQL
  success path and database-unavailable `503` path.
- Existing assessment tests prove repository scoping for header-based pilot
  credentials. HTTP Basic authentication needs explicit valid/scoped/rejected
  integration cases.
- The local Docker daemon is unavailable. Sandbox image build, pinned-tool
  inspection, and isolated-container setup fixtures have not run.

## Known constraints and deferred work

- `GET /ready` proves only database connectivity; it does not verify migration
  level. The operating package needs a migration-state check.
- The semantic report has the core measurements but does not yet expose a
  dedicated, prominent pending-review count.
- No placeholder-only pilot environment template or local smoke-test script
  exists yet.
- No fixture matrix currently covers every required setup profile or the
  negative/ambiguous Vitest cases from the execution scope.
- External pilot activities, deployment, GitHub credentials, repository
  selection, consent collection, and external cohorts remain out of scope
  until separately approved.

## Execution gates

Phase 1 PostgreSQL and HTTP work can proceed locally without contacting any
remote service. Docker-dependent Phase 3 work requires a local daemon, and an
image build must not pull base images or dependencies without explicit
approval. Phase 4 remains documentation-only; Phase 5 requires explicit
approval for every remote action.
