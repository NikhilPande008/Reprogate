# ReproGate Product Overview

ReproGate is an evidence-first, read-only GitHub issue investigation
workflow. It helps maintainers assess a reported behavior through a bounded
claim, a focused test change, structured execution evidence, and a maintainer
decision—without presenting an automated semantic verdict as fact.

## Product outcome

For each investigation, ReproGate preserves an inspectable evidence packet:

1. A schema-validated extraction of the issue report.
2. The focused test change proposed in a sandboxed workspace.
3. Terminal output, Git diff, focused-test selection, and structured test results.
4. Deterministic validation and an advisory maintainer next action.

A behavior-gap confirmation means only that the generated test expectation is
absent in the inspected implementation under the recorded conditions. It does
not establish product intent, regression provenance, priority, or whether an
issue is a defect.

## Safety and trust boundaries

- GitHub access is read-only by default.
- Public dashboard pages cannot trigger a run, retry, comment, label, close, or
  otherwise mutate GitHub.
- Human semantic review is append-only and separate from deterministic
  validation; reviewer feedback never changes an investigation verdict.
- Setup failures, timeouts, malformed results, missing detail, and imprecise
  focused-test selection remain conservative or operationally inconclusive.
- Live investigations use fresh workspaces and short-lived non-privileged
  containers. Focused-test and confirmation phases have no Codex credential
  mount and are network-isolated by default.

## Offline demonstration

The committed demo snapshot lets users inspect persisted evidence without
GitHub access, OpenAI credentials, Codex authentication, Docker, or a live
investigation:

```bash
uv sync
uv run python scripts/seed_demo.py
uv run uvicorn triage.api.main:app --reload
```

In another terminal:

```bash
cd dashboard
npm install
npm run dev
```

Open <http://localhost:5173> and select `psf/requests #7564`. The example
shows its bounded claim, changed focused test, JUnit evidence, deterministic
validation, proof-integrity result, and advisory maintainer action.

## Current capability and roadmap

Pytest supports confirmation-quality evidence when exact changed-test selection
and matching JUnit results are available. Vitest supports the same outcome only
for a conservative static top-level test subset; Jest remains diagnostic-only.
The exact requirements and all rejected paths are defined in the
[Runner Capability Contract v1](docs/runner-capability-contract-v1.md).
PostgreSQL-grade shared job claims, production SSO/RBAC,
multi-tenant isolation, broader runner support, complete COGS, and external
design-partner measurement remain future work.

For detailed architecture, limitations, and operational evidence, see
[PRODUCT_REPORT.md](PRODUCT_REPORT.md) and [HANDOFF.md](HANDOFF.md).
