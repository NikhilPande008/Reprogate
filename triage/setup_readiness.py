"""Offline manifest-readiness measurement for local repository samples."""
from __future__ import annotations

from pathlib import Path

from triage.runners import RunnerSelectionError, select_runner
from triage.sandbox.manager import EnvironmentSetupFailure


TARGET_REPOSITORY_SAMPLE = 20


def report(paths: list[Path]) -> dict[str, object]:
    """Resolve setup profiles without cloning, installing, or executing code."""
    items: list[dict[str, object]] = []
    for path in paths:
        try:
            runner = select_runner("auto", path)
            setup = runner.setup_command(path, None)
            items.append({"path": str(path), "status": "READY", "runner": runner.id, "setup_command": setup.command, "setup_reason": setup.reason})
        except (RunnerSelectionError, EnvironmentSetupFailure) as error:
            items.append({"path": str(path), "status": "UNSUPPORTED", "reason": str(error)})
    ready = sum(item["status"] == "READY" for item in items)
    total = len(items)
    return {
        "setup_readiness_report_version": "1.0",
        "sample": {"repositories": total, "target_repositories": TARGET_REPOSITORY_SAMPLE, "remaining_to_target": max(0, TARGET_REPOSITORY_SAMPLE - total)},
        "counts": {"ready": ready, "unsupported": total - ready},
        "manifest_readiness_rate": ready / total if total else None,
        "items": items,
        "caveats": [
            "This is an offline manifest-readiness report: it does not clone repositories, install dependencies, or execute setup commands.",
            "It must not be reported as the runtime setup-failure rate required for the external 20-repository sample.",
        ],
    }
