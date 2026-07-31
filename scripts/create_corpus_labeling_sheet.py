"""Create a blinded local worksheet for independent corpus-type labeling."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demo" / "evaluations" / "evaluation-corpus-v1.json"
OUTPUT = ROOT / "demo" / "evaluations" / "evaluation-corpus-labeling-v1.json"


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    for case in source.get("cases", []):
        rows.append({
            "case_id": case["case_id"],
            "repository": case["repository"],
            "issue_number": case["issue_number"],
            "issue_url": case["issue_url"],
            "revision_sha": case["revision_sha"],
            "reviewer_a": {"issue_type": None, "secondary_tags": [], "include": None, "rationale": None},
            "reviewer_b": {"issue_type": None, "secondary_tags": [], "include": None, "rationale": None},
            "adjudication": {"status": "PENDING", "issue_type": None, "include": None, "rationale": None},
        })
    payload = {
        "schema_version": "evaluation-corpus-labeling-v1",
        "source_manifest": SOURCE.name,
        "instructions": "Two independent reviewers label issue type and inclusion before any ReproGate result is shown. System outputs and classifications are intentionally absent.",
        "allowed_issue_types": ["confirmable_bug_report", "feature_request", "incomplete_or_needs_info", "duplicate_like", "intended_behavior", "environment_setup", "ambiguous_or_mixed"],
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(rows)} blinded labeling rows at {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
