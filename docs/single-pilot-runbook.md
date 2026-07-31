# Single-Pilot Runbook

This runbook is for one consented customer repository. It does not authorize
GitHub writes, unattended posting, or work outside the configured repository.

## Deployment configuration

- Set `DATABASE_URL` to a PostgreSQL URL using the `psycopg` driver, for
  example `postgresql+psycopg://…`.
- Run `alembic upgrade head` before starting the API or worker.
- Set `PILOT_REVIEW_ENABLED=true` and provide a `PILOT_REVIEWER_REGISTRY` with
  only the pilot repository in each reviewer's `repositories` list.
- Use HTTPS and `PILOT_SESSION_SECURE_COOKIE=true` in the deployed environment.
- Keep `GITHUB_AUTO_POST_ENABLED=false` and `GITHUB_AUTO_POST_DRY_RUN=true`.
- Set `WORKER_PER_REPOSITORY_CONCURRENCY=2` only after confirming the
  repository and budget caps can support two simultaneous investigations.

The pilot-review API accepts either the existing reviewer/token headers or
standard HTTP Basic credentials. For Basic auth, the username is the configured
reviewer ID and the password is that reviewer's deployment-held token. The same
registry enforces repository scope; credentials are never stored in the
database or logged.

## Readiness and health

- `GET /health` verifies that the process is running.
- `GET /ready` verifies that the configured database accepts a read-only
  `SELECT 1` query.
- Treat a failed readiness check as an operational incident. Do not enqueue new
  work until database connectivity and migrations are restored.

## First startup and rollback

1. Copy `config/pilot.env.example` into deployment-held configuration and replace
   every placeholder outside the repository. Keep posting disabled.
2. Run `alembic upgrade head`, then record `alembic current` and the migration
   head in the startup evidence.
3. Start the API, verify `/health` and `/ready`, then run the local smoke check
   before starting workers.
4. Start workers with the configured global and per-repository limits. Do not
   enqueue an investigation merely to test startup.
5. To stop safely, stop workers first, preserve queue/job and artifact evidence,
   then stop the API. Do not delete the database, release reservations manually,
   or alter historical packets during rollback.

### Local Compose rehearsal

The pilot-only Compose stack never receives GitHub credentials and hard-disables
posting. Run `docker compose -f compose.pilot-local.yml up --build --abort-on-container-exit`
to verify the database migration and one bounded worker, then run
`docker compose -f compose.pilot-local.yml up -d api` and point the smoke check
at `http://127.0.0.1:8011`. Stop it with
`docker compose -f compose.pilot-local.yml down -v`; this removes only the
named local rehearsal volume.

## Incident evidence collection

Record the timestamp, repository, job/investigation ID, queue state, configured
worker limits, migration revision, readiness result, budget state, and the
bounded artifact/terminal references. Redact credentials and raw secrets. Keep
the evidence with the incident; do not retry or enable posting as an incident
workaround.

## Setup failure

1. Inspect the persisted setup command, manifest, and terminal evidence.
2. Confirm which supported manifest was detected and whether a lockfile exists.
3. Do not retry with an arbitrary shell command. Update the local setup profile
   or an explicitly reviewed `SANDBOX_SETUP_COMMAND`.
4. Re-run only after recording the remediation. The failed investigation stays
   in the evidence trail and receives an operational packet.

## Budget exhaustion

1. Stop accepting new work for the repository.
2. Review tracked OpenAI spend, outstanding reservations, and unpriced Codex
   wall time in the repository metrics.
3. Increase a budget only with the pilot owner's approval; never clear a
   reservation or rewrite historical cost evidence.
4. Resume from the durable queue after a fresh reservation succeeds.

## Agent timeout

1. Preserve the terminal output and mark the attempt operationally
   inconclusive; do not interpret a timeout as a behavior gap.
2. Check the sandbox timeout, repository setup duration, and selected test
   target before retrying.
3. Retry only within the configured job-attempt and budget limits.
4. Escalate repeated timeouts with the evidence packet and reproducibility
   manifest; do not enable GitHub posting as a workaround.

## Operational boundaries

- PostgreSQL advisory locks serialize per-repository job claims and OpenAI
  budget reservations for this single-pilot deployment.
- The public dashboard remains read-only. Pilot reviewers can access only
  repositories listed in their registry entry.
- A behavior-gap confirmation remains executable evidence for human review,
  not a semantic bug verdict.
