# Part 2: Remote-readiness review

Date: 2026-07-25  
Scope: the pilot-development copy only. This Phase 4 review does not provision,
deploy, push, migrate a remote database, access GitHub, or modify the frozen
`github issue triage` project.

## Decision

**Local single-pilot readiness is verified; remote execution remains a
per-action approval decision.** Remote work may use only the pilot copy and
must not update, push from, deploy, or otherwise affect the frozen project.

## Evidence reviewed

- PostgreSQL is now a declared runtime dependency (`psycopg[binary]`).
- Alembic sources `DATABASE_URL` from application settings and can migrate the
  configured database.
- `GET /ready` checks database reachability without writing data.
- Queue claims and OpenAI budget reservations use transaction-scoped,
  repository-keyed PostgreSQL advisory locks. A no-claim path now closes its
  transaction so advisory locks are not retained by an idle worker session.
- Pilot-review access remains feature-gated, repository-scoped, and supports
  existing header credentials or HTTP Basic credentials. Browser session routes
  return `401` when no identity is present; invalid supplied credentials return
  `403`.
- GitHub commenting remains disabled by default and requires the enabled flag,
  non-dry-run mode, and an explicit repository allowlist.

## Verification completed locally

| Check | Result |
| --- | --- |
| Clean PostgreSQL migration, queue, budget, and readiness suite | 5 passed |
| Full Python suite | 210 passed, 7 intentional skips |
| Dashboard tests | 17 files / 38 tests passed |
| Dashboard production build | Passed |
| Isolated Docker role-boundary check | 1 passed |
| Sandbox toolchain | `uv 0.7.20`; Poetry `2.1.3`, verified network-disabled |
| `git diff --check` | Passed |

The skips are opt-in/environment-dependent tests. The PostgreSQL suite ran
against temporary local PostgreSQL 16 clusters, which were stopped and removed.

## Completed local gates

The clean PostgreSQL suite now proves Alembic upgrade through head, a
per-repository queue limit of two, advisory-lock budget reservation behavior,
and `/ready` success/unavailable outcomes. HTTP Basic tests prove valid
repository-scoped access, cross-repository rejection, and no credential echo.

The operator package now includes a placeholder-only configuration template,
smoke check, documented rollback/evidence collection, 23 locally backfilled
review packets, and an alignment report with explicit packet/pending counts.

## Preconditions before any remote action

1. Provision a dedicated PostgreSQL database with TLS, backups/restore testing,
   least-privilege application credentials, and a separate migration role.
2. Run `alembic upgrade head`, then verify `/ready` and a migration-head check.
   `/ready` currently proves connectivity only; it does not prove schema level.
3. Put the API behind HTTPS, set `PILOT_SESSION_SECURE_COOKIE=true`, inject
   reviewer and GitHub credentials through the deployment secret store, and
   confirm secrets are not present in logs or images.
4. Configure one consented repository in every allowlist and keep
   `GITHUB_AUTO_POST_ENABLED=false` and `GITHUB_AUTO_POST_DRY_RUN=true` for
   the initial remote read-only pilot.
5. Define operational ownership for alerts, queue lease recovery, database
   incidents, retention, and a tested rollback path. Keep global and
   per-repository worker concurrency at conservative values until observed
   queue and budget behavior supports an increase.

## Per-action remote authority checklist

| Action | Purpose and minimum data | Required safeguards / rollback | Explicit approval needed |
| --- | --- | --- | --- |
| Create a pilot-only remote/repository | Host the pilot copy only | New remote, no push or branch operation against frozen project; delete/archive new remote if abandoned | Yes |
| Provision hosted PostgreSQL and deployment | One-pilot API/worker runtime | TLS, backups, least privilege, separate migration role, tested restore; destroy pilot resources on rollback | Yes |
| Configure GitHub read-only access | Fetch one consented customer repository | Installation token limited to metadata/issues read; no write scopes; revoke token to stop | Yes, plus repository owner consent |
| Collect semantic-review corpus consent | Evaluation-only measurements | Written consent, retention reference, revocation handling, no raw logs/credentials | Yes |
| Recruit reviewers and run cohorts | Independent review evidence | One maintainer plus two independent engineers per packet; no automated decision/posting | Yes |
| Python/Vitest external samples | Measure setup/runtime support | Pre-registered selection, per-run budget/time caps, bounded cohort, stop on safety failure | Yes |
| Publish a 50-example report | Report only fully covered cohort evidence | Publish only after coverage threshold; include disagreement and caveats | Yes |
| Enable a pilot deployment | Controlled read-only operation | Posting disabled, repository allowlists, monitoring owner, stop procedure | Yes |

## Approval boundary

The next remote-capable action is creating a pilot-only remote/repository or
provisioning a pilot-only environment. It must use the pilot copy exclusively;
no Docker or Git action may be performed in the frozen project. None of these
remote actions has been performed by this review.
