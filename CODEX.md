# How Codex Is Used

ReproGate is built on a single premise: **an agent should be able to propose a
proof, but never to certify one.** Codex is the execution layer that turns a
GitHub issue into a candidate failing test. It is never the authority that
decides whether that test counts.

This document records exactly what Codex does, the bounds it runs inside, and
the capabilities deliberately withheld from it.

## What Codex does

Codex works inside an isolated container against a fresh clone of the target
repository and performs the narrow, repetitive work a maintainer would otherwise
do by hand:

1. Read the typed extraction of the issue report.
2. Locate the relevant implementation branch in an unfamiliar codebase.
3. Propose the **smallest focused executable test** that expresses the reported
   behavior as an assertion.
4. Run that test.
5. Leave behind the diff, the terminal output, and the structured test results
   for every attempt.

Step 3 is the part that would be genuinely tedious to automate any other way.
Turning prose like *"raise `FileNotFoundError` for missing TLS material"* into
a test that names the right symbol, the right errno, and the right call site
requires reading the actual repository, not pattern-matching the issue text.

## What Codex is not permitted to do

| Withheld capability | Enforced by |
| --- | --- |
| Decide the verdict | Deterministic validator runs after the agent exits |
| Grade its own test | Validation reads persisted artifacts, never agent claims |
| Edit implementation, config, or fixture paths | Proof-integrity diff analysis rejects the diff |
| Write to GitHub | GitHub client is read-only; no mutation path exists |
| Retry without bound | Hard cap of 3 attempts per investigation |
| Run indefinitely | 900-second wall cap per investigation |
| Hold credentials during verification | Credential mount is scoped to the agent role only |

The last row is the one most often skipped. See
[Execution boundary](#execution-boundary) below.

## The seven deterministic checks

After Codex exits, a validator that shares no code path with the agent inspects
the persisted artifacts. All seven checks must pass before evidence may be
recorded as `BEHAVIOR_GAP_CONFIRMED`:

| # | Check | Rejects |
| --- | --- | --- |
| 1 | Changed executable test | A diff that touched no runnable test |
| 2 | Exact focused-test selection | File-level guesses; requires an AST-derived test node |
| 3 | Valid structured JUnit result | Terminal output alone; requires machine-readable results |
| 4 | Explicit assertion failure | A `<error>` masquerading as a `<failure>` |
| 5 | No setup, error, or timeout | Infrastructure noise scored as a finding |
| 6 | Confirmation rerun matches | Flaky results; the test is re-run in the same environment |
| 7 | Proof-pattern integrity | Manufactured proofs — see below |

Any check failing means the investigation is recorded with a bounded
non-confirming outcome (`NEEDS_INFO`, `WONT_REPRO`, `NOT_A_BUG`, or
`FLAKY_OR_INCONCLUSIVE`). **The result never upgrades.** There is no partial
credit and no path by which a near-miss becomes a confirmation.

### Proof-pattern integrity

Check 7 exists because the obvious failure mode of "have an agent write a
failing test" is an agent that writes a test which fails for the wrong reason.
The diff analyzer rejects, among others:

- `NO_CHANGED_EXECUTABLE_TEST` — nothing runnable actually changed.
- `UNCONDITIONAL_FALSE_ASSERTION` — a literal-false assert that would fail
  against any implementation.
- `UNCONDITIONAL_FAILURE_HELPER` — a bare failure call in the test body.
- `MODIFIED_FIXTURE_OR_SNAPSHOT` — a fixture or golden file edited to
  manufacture a mismatch.

Ambiguous cases are recorded as review flags rather than silently accepted or
silently discarded.

## Execution boundary

An investigation runs across three container roles with different privileges.
The distinction matters: the container that holds the Codex credential is never
the container that produces the evidence.

| Role | Credential mount | Network | Purpose |
| --- | --- | --- | --- |
| `SETUP` | none | dependency install only | Prepare the workspace |
| `AGENT` | Codex auth, read-only | provider connectivity | Propose the focused test |
| `TEST` | none | `none` by default | Execute the test and confirmation rerun |

Every container is non-privileged, receives an explicitly empty environment
rather than an inherited one, and never mounts the Docker socket. The
reproducibility manifest records the role and network policy actually used for
each phase, so the boundary is auditable after the fact rather than merely
asserted here.

This reduces test-execution exposure. It does not claim complete protection
against all agent-runtime supply-chain or credential risk — the agent phase
still requires provider connectivity by construction.

## Where GPT-5.6 fits

Codex is not the only model in the pipeline, and neither model can promote its
own output.

- **GPT-5.6 Luna** produces the typed, schema-validated extraction of the issue
  report. After deterministic validation has already run, it assigns bounded
  non-confirming classifications such as `NEEDS_INFO` or `WONT_REPRO`.
- It cannot authorize a behavior-gap confirmation. Confirmation is reachable
  only through the seven deterministic checks.

Extraction and classification are tracked OpenAI API calls with linked cost,
token, and latency records. Codex execution is recorded as wall time and
invocation count, and its dollar cost is explicitly reported as unavailable
rather than estimated — inventing a billing number would undercut the point of
the project.

## What this cost in practice

From the recorded cross-repository run on 2026-07-21, six issues across two
repositories:

- ~$0.03 tracked OpenAI API spend
- ~46 seconds tracked OpenAI API latency
- ~23 minutes of unpriced Codex execution
- 2 behavior gaps confirmed, 4 investigations declined
- 0 GitHub writes

The declines are the load-bearing number. An agent that confirms everything has
told you nothing.

## Reproducing the agent boundary

The role separation is covered by tests that do not require credentials:

```bash
.venv/bin/python -m pytest tests/unit/test_sandbox_container.py \
                  tests/unit/test_investigation_engine.py \
                  tests/unit/test_providers.py -q
```

Docker-dependent smoke tests for the same boundary live in
`tests/integration/test_docker_role_boundary_smoke.py` and
`tests/integration/test_docker_codex_compatibility_smoke.py`.

Full suite: `.venv/bin/python -m pytest -q` — 221 passed, 7 skipped.

## Related documentation

- [README.md](README.md) — product overview, flagship evidence, quickstart.
- [PRODUCT_REPORT.md](PRODUCT_REPORT.md) — detailed capability and risk report.
- [DECISIONS.md](DECISIONS.md) — architectural decision records.
- [docs/runner-capability-contract-v1.md](docs/runner-capability-contract-v1.md)
  — canonical definition of which runner results can support confirmation.
