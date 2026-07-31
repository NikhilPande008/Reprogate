import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frozen_corpus_manifest_schema_requires_a_pinned_revision_and_selection_rules() -> None:
    schema = json.loads((ROOT / "demo" / "evaluations" / "corpus-manifest-v1.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "evaluation-corpus-v1"
    assert {"selection_method", "inclusion_rules", "exclusion_rules", "strata", "cases"}.issubset(schema["required"])
    assert {"repository", "issue_number", "issue_url", "revision_sha", "issue_type"}.issubset(schema["properties"]["cases"]["items"]["required"])
