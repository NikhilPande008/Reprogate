"""Deterministic test-runner adapters.

Implemented: pytest, Vitest, and Jest. Jest is intentionally diagnostic-only
until an exact test-name selector and JUnit mapping are available. Go, JUnit,
and RSpec remain future adapter targets; selecting them fails rather than
guessing.
"""

from triage.runners.adapters import (
    RUNNER_CAPABILITIES,
    RunnerAdapter,
    RunnerCapability,
    RunnerSelectionError,
    runner_capabilities,
    select_runner,
)

__all__ = [
    "RUNNER_CAPABILITIES",
    "RunnerAdapter",
    "RunnerCapability",
    "RunnerSelectionError",
    "runner_capabilities",
    "select_runner",
]
