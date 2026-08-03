import type { ValidationExplainer as ValidationExplainerData } from "../services/api";

const anchorFor: Record<string, string> = { git_diff: "evidence", structured_test_results_junit: "evidence", reproducibility_manifest: "evidence" };

export function ValidationExplainer({ data, investigationId, compact = false }: { data?: ValidationExplainerData; investigationId: string; compact?: boolean }) {
  if (!data || !Array.isArray(data.checks)) return <section className="card"><h2>Why this failure counts</h2><p className="metadata">Deterministic validation evidence is unavailable.</p></section>;
  const confirmed = data.conclusion === "BEHAVIOR_GAP_CONFIRMED";
  const legacy = data.conclusion === "LEGACY_EVIDENCE_INCOMPLETE";
  const firstBlocked = data.checks.find((item) => item.status !== "PASS");
  const unavailable = data.checks.filter((item) => item.status !== "PASS").map((item) => item.label);
  const passed = data.passed_checks ?? data.checks.filter((item) => item.status === "PASS").length;
  const total = data.total_checks ?? data.checks.length;
  // A retained verdict this validator could not re-derive is reported as
  // incomplete provenance, never as a refutation and never as a confirmation.
  const conclusionTitle = confirmed ? "Behavior gap confirmed" : legacy ? "Retained verdict, incomplete provenance" : "No behavior gap established";
  const conclusionBody = confirmed
    ? "Every required deterministic check passed. This confirms the focused test fails against the inspected revision; it does not decide whether the behavior is a bug, regression, or intended."
    : legacy
      ? `This investigation ran before structured selection and proof-integrity artifacts were captured, so ${total - passed} of ${total} checks cannot be reconstructed from what was retained: ${unavailable.join(", ")}. Its stored verdict is shown as recorded and is deliberately neither re-derived nor upgraded here. Only the ${passed} checks marked passed above are evidence.`
      : `${firstBlocked?.label ?? "A required deterministic gate"} is ${firstBlocked?.status.toLowerCase() ?? "unavailable"}; this does not invalidate the issue.`;
  const body = <><div className="validation-explainer-grid">{data.checks.map((item) => <article className={`validation-check validation-${item.status.toLowerCase()}`} key={item.id}><span aria-label={`${item.label}: ${item.status}`}>{item.status === "PASS" ? "✓" : item.status === "FAIL" ? "×" : "—"}</span><div><b>{item.label}</b><p>{item.explanation}</p>{item.artifact_kind && <a href={`?id=${encodeURIComponent(investigationId)}#${anchorFor[item.artifact_kind] ?? "attempts"}`}>Open persisted evidence</a>}</div></article>)}</div><p className={legacy ? "validation-conclusion validation-conclusion-legacy" : "validation-conclusion"}><b>{conclusionTitle}</b> — {conclusionBody}</p></>;
  return <section className="card validation-explainer" id="validation-explainer"><div className="section-heading"><div><p className="eyebrow">Deterministic validator</p><h2>Why this failure counts</h2>{legacy && <p className="validation-provenance-note">Stored verdict retained from an earlier validator version · {passed}/{total} checks reconstructible</p>}</div><span className="metadata">{data.version}</span></div>{compact && !confirmed ? <details><summary>Show deterministic validation checks</summary>{body}</details> : body}</section>;
}
