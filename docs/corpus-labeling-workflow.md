# Corpus Labeling Workflow v1

The draft metadata sample cannot be frozen as an evaluation corpus until two
independent humans classify each candidate without seeing a ReproGate
result. Run `scripts/create_corpus_labeling_sheet.py` to generate the local
worksheet.

For each row, reviewers independently choose one primary issue type, optional
secondary tags, inclusion/exclusion, and a concise rationale from the public
issue record. They must not see generated claims, tests, classifications, or
artifacts. Reviewers return their entries to the evaluation owner, who records
agreement or an adjudication using the frozen adjudication rules.

Only rows with two retained reviews and an adjudicated inclusion decision may
enter the final `evaluation-corpus-v1` manifest. Rows lacking agreement remain
unresolved and are reported; they are never silently relabeled from title or
issue metadata.
