# Runner Capability Contract v1

This is the canonical public contract for how ReproGate uses test runners.
It applies to new investigations. Historical records preserve their original
provenance and must not be upgraded from later rules.

| Runner / selection | May produce confirmation-quality evidence? | Required evidence | Outcome when requirement is missing or ambiguous |
| --- | --- | --- | --- |
| Pytest with exact changed-test selection | Yes | Changed executable test, exact target, matching JUnit `<failure>`, clean execution, proof-integrity pass, and matching confirmation rerun | Evidence-only or operationally inconclusive; never `BEHAVIOR_GAP_CONFIRMED` |
| Vitest static top-level test with exact selection | Yes | The same gates as Pytest, including a changed assertion mapping to one exact static top-level test name and matching JUnit testcase | Evidence-only or operationally inconclusive; never `BEHAVIOR_GAP_CONFIRMED` |
| Vitest file-only, nested, parameterized, dynamic, duplicate-name, or otherwise ambiguous selection | No | Diagnostic artifacts may be retained | Diagnostic-only; never `BEHAVIOR_GAP_CONFIRMED` |
| Jest | No | Diagnostic artifacts may be retained | Diagnostic-only; never `BEHAVIOR_GAP_CONFIRMED` |
| Unsupported or ambiguous setup | No | Persist the setup evidence and reason | Operationally inconclusive; never a semantic negative or confirmation |

`BEHAVIOR_GAP_CONFIRMED` means only that the generated focused expectation
failed through the required deterministic evidence gates. It does not decide
whether the issue is a bug, regression, intended behavior, or priority.

Any documentation, UI text, and evaluation report that describes runner support
must link to or match this contract. Changes require a versioned replacement,
implementation tests for both the permitted and rejected paths, and a recorded
review of the deterministic validator.
