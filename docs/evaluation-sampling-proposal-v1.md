# Evaluation Sampling Proposal v1 (Approval Required)

Status: **proposal only**. This document does not select cases, contact
maintainers, read remote repositories, or freeze a corpus.

## Objective and unit of analysis

Evaluate whether a bounded ReproGate packet faithfully represents an issue
and supports a maintainer's review. The unit is one issue at one immutable
repository revision, not an issue's eventual product outcome.

## Proposed sampling frame

Use six consented or publicly approved repositories that satisfy all of:

- a supported runner (pytest or the conservative exact-selection Vitest subset);
- reproducible dependency setup in a pinned checkout;
- public issue history sufficient to classify issue type without using system
  outcomes; and
- a maintainer contact or a documented independent-engineer substitute.

Pre-register the repository list and snapshot each repository's default-branch
HEAD SHA at corpus freeze. Do not substitute a repository after observing run
results; record any unavailable stratum as an exclusion.

## Proposed pilot size and strata

Target 48 cases: eight cases per repository, sampled before any system run.
Quota targets are intentionally balanced where the frame permits them:

| Stratum | Target | Notes |
| --- | ---: | --- |
| Confirmable bug report | 10 | Includes a concrete expected/actual behavior claim. |
| Feature request / intended-behavior ambiguity | 8 | Must not be scored as an automatic bug decision. |
| Incomplete / needs-information report | 7 | Includes missing reproduction or environmental detail. |
| Duplicate-like / already-addressed report | 5 | Record the independent public basis for the designation. |
| Environment or setup-sensitive report | 6 | Track setup failures separately from semantic outcomes. |
| Ambiguous or mixed-evidence report | 6 | Preserve unresolved review outcomes. |
| Closed historical issue | 6 | Include only when an independent public source is recorded. |

Open and closed state, runner, repository, and issue type are reporting
strata—not a reason to remove unfavorable outcomes. If a case fits multiple
types, assign the predeclared primary type and retain secondary tags.

## Selection method

1. Publish the eligible issue frame per repository with the capture timestamp,
   issue URL, open/closed state, and issue-type tags made by the selector.
2. Exclude only cases meeting a predeclared rule below, before any
   ReproGate output is viewed.
3. Within each repository/type stratum, sort by issue number and use a
   documented seeded random sample. Store the seed and ordered candidate list.
4. Create `evaluation-corpus-v1` using the frozen schema. Each entry records
   issue URL, exact commit SHA, issue type, selection stratum, and capture
   timestamp.
5. Hash the manifest and publish it before the first evaluated investigation.

## Inclusion rules

- Issue is publicly accessible or explicitly consented for evaluation.
- Repository revision can be pinned to a full 40-character commit SHA.
- Issue is within the predeclared capture window and has enough text to assess
  whether a bounded claim preserves stated constraints or missing information.
- Repository runner and setup approach are known before the run.

## Exclusion rules

- Private, deleted, security-sensitive, or access-restricted issues without
  explicit written authorization.
- Issues containing secrets or personal data that cannot be redacted while
  retaining reviewability.
- Repositories outside implemented runner support, unless retained as a
  separately reported operational-coverage stratum.
- Duplicate URL, duplicate repository/issue pair, or a case already used to
  tune the evaluated configuration.
- Unpinnable revisions. Record these as exclusions; do not replace them after
  system results are known.

## Revision and provenance capture procedure

For every approved candidate, capture read-only metadata: issue URL, issue
number, repository, selection timestamp, default-branch SHA, release/tag SHA
when relevant, runner selection, and setup manifest hashes. The evaluated run
must clone and test the exact recorded SHA. Any mismatch, unavailable commit,
or setup failure is recorded as operationally inconclusive.

## Approval gates

Approval is required before: naming the six repositories, reading remote issue
or revision metadata, contacting reviewers, freezing `evaluation-corpus-v1`,
or starting evaluated runs. The approved corpus must be immutable after its
manifest hash is published.
