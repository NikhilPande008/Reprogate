"""Deterministic test-runner adapters.

Implemented: pytest, Vitest, and Jest. Jest is intentionally diagnostic-only
until an exact test-name selector and JUnit mapping are available. Go, JUnit,
and RSpec remain future adapter targets; selecting them fails rather than
guessing.
"""

from triage.runners.adapters import RunnerAdapter, RunnerSelectionError, select_runner

__all__ = ["RunnerAdapter", "RunnerSelectionError", "select_runner"]
