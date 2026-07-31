"""Freeze a read-only, deterministic public-issue evaluation corpus manifest."""
from __future__ import annotations

import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo" / "evaluations" / "evaluation-corpus-v1.json"
REPOSITORIES = ("psf/requests", "openai/openai-python", "pydantic/pydantic", "pallets/flask", "pytest-dev/pytest", "fastapi/fastapi")
SEED = 20260725


def gh_json(path: str) -> object:
    result = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def issue_type(issue: dict[str, object]) -> str:
    labels = " ".join(str(label.get("name", "")) for label in issue.get("labels", []) if isinstance(label, dict)).lower()
    text = f"{issue.get('title', '')} {labels}".lower()
    if "duplicate" in text: return "duplicate_like"
    if any(word in text for word in ("install", "setup", "environment", "dependency", "build", "ci")): return "environment_setup"
    if any(word in text for word in ("feature", "enhancement", "proposal", "request")): return "feature_request"
    if any(word in text for word in ("question", "help", "support", "documentation")): return "incomplete_or_needs_info"
    if "bug" in text or "regression" in text: return "confirmable_bug_report"
    return "ambiguous_or_mixed"


def main() -> int:
    rng = random.Random(SEED)
    cases: list[dict[str, object]] = []
    for repository in REPOSITORIES:
        metadata = gh_json(f"repos/{repository}")
        branch = str(metadata["default_branch"])
        revision = str(gh_json(f"repos/{repository}/commits/{branch}")["sha"])
        issues = gh_json(f"search/issues?q=repo:{repository}+is:issue&per_page=100&sort=created&order=desc")["items"]
        if len(issues) < 8: raise RuntimeError(f"{repository} has fewer than eight eligible public issues in the frozen frame")
        selected = sorted(rng.sample(issues, 8), key=lambda item: int(item["number"]))
        for issue in selected:
            cases.append({"case_id": f"{repository.replace('/', '-')}-{issue['number']}", "repository": repository, "issue_number": issue["number"], "issue_url": issue["html_url"], "revision_sha": revision, "issue_type": issue_type(issue), "state_at_capture": issue["state"], "selection_stratum": repository})
    manifest = {"schema_version": "evaluation-corpus-v1", "corpus_version": "evaluation-corpus-v1", "frozen_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "selection_method": f"Public GitHub issue-only search frame; sorted deterministic sample of eight issues per repository using seed {SEED}. encode/httpx was excluded before freeze because its initial captured repository frame had fewer than eight eligible issues; pytest-dev/pytest replaced it before any system run.", "inclusion_rules": ["Public issue", "repository supports pytest", "default-branch revision pinned at capture"], "exclusion_rules": ["Pull request", "private or restricted issue", "unavailable pinned revision", "repository frame with fewer than eight eligible issues"], "strata": ["repository", "issue_type", "state_at_capture"], "cases": cases}
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen {len(cases)} cases in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
