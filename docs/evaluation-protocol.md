# Evaluation Protocol (Pre-registered, Not Yet Executed)

ReproGate has no validated autonomous issue-triage accuracy claim. This
protocol defines the minimum independently reviewable evaluation required
before one can be considered.

The frozen local v1 assets are the [corpus-manifest schema](../demo/evaluations/corpus-manifest-v1.schema.json), [independent review rubric](evaluation-review-rubric.md), and [adjudication rules](evaluation-adjudication.md). They define a procedure only; they do not create a corpus, reviewers, or results.

## Frozen corpus

Before any evaluated run, publish a versioned corpus manifest containing the
sampling frame, inclusion and exclusion rules, issue-type strata, repository
commit SHA, issue URL, and selection timestamp. Select cases independently of
system outcomes across multiple repositories and include confirmable bugs,
feature requests, incomplete reports, duplicates, intended behavior,
environment failures, and ambiguous cases. Seeded demo cases are examples only
and cannot supply the corpus or its benchmark denominator.

## Independent review and adjudication

At least two qualified reviewers assess each packet while blinded to the
system classification when practical: one maintainer where available and one
independent engineer. They record claim fidelity, test fidelity, evidence
validity, non-confirming-outcome appropriateness, maintainer usefulness, and
aligned/misaligned/unresolved status. Preserve disagreements. Predefine an
adjudication record; it may explain a disagreement but must not erase it.

## Reporting

Report denominators, Wilson confidence intervals, and strata by repository,
issue type, runner, and outcome. Include confirmed precision and false
confirmation rate, useful `NEEDS_INFO` rate, operational-inconclusive rate,
rerun reproducibility, reviewer agreement and unresolved disagreement, median
OpenAI API cost, separate Codex/runtime cost, and rubric-based usefulness.
Operational failures remain separate from negative classifications.

## Safety boundary

Every corpus export must retain system version, prompts, models, configuration,
commit SHA, artifacts, packets, reviewer judgments, and consent/audit data.
Public actions remain approval-gated regardless of results. A disabled local
demo proves presentation safety only; it does not prove live Docker isolation,
credential separation, network controls, queue durability, or GitHub
ingestion.
