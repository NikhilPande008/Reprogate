import { useEffect, useMemo, useState } from "react";
import { api, type EvidenceArtifact, type Investigation, type SemanticReview, type ValidationCheck, type ValidationExplainer } from "../services/api";
import { boundedCaveat } from "./EvidenceBrief";

const stageTitles = ["The report", "Codex investigates", "Proof is checked", "A bounded outcome", "Review the evidence"];
const gateOrder = [
  ["exact_focused_test_selection", "Exact changed test"],
  ["proof_pattern_integrity", "Proof-integrity check"],
  ["structured_junit_result", "Structured JUnit failure"],
  ["clean_execution", "Clean execution"],
  ["confirmation_match", "Confirmation rerun"],
] as const;

function latest(items: Investigation[]) { return [...items].sort((a, b) => (b.completed_at ?? b.updated_at ?? "").localeCompare(a.completed_at ?? a.updated_at ?? ""))[0]; }
function artifact(items: EvidenceArtifact[], kind: string) { return items.find((item) => item.kind === kind); }
function testPath(content: string | null | undefined) { return content?.split("\n").map((line) => line.match(/^\+\+\+ b\/(.+)/)?.[1]).find((path) => path && (/(?:^|\/)test[^/]*\//i.test(path) || /test_/i.test(path))); }
function statusLabel(status: ValidationCheck["status"]) { return status === "PASS" ? "Passed" : status === "FAIL" ? "Blocked" : status === "NOT_APPLICABLE" ? "Not applicable" : "Unavailable"; }

function Gate({ check, fallback }: { check?: ValidationCheck; fallback: string }) {
  const status = check?.status ?? "UNAVAILABLE";
  return <article className={`demo-gate demo-gate-${status.toLowerCase()}`}><span aria-hidden="true">{status === "PASS" ? "✓" : status === "FAIL" ? "×" : "—"}</span><div><b>{fallback}</b><small>{statusLabel(status)}</small><p>{check?.explanation ?? "This persisted validation gate is unavailable for the selected evidence record."}</p></div></article>;
}

export function JudgeDemoTour() {
  const [stage, setStage] = useState(0);
  const [selected, setSelected] = useState<Investigation>();
  const [artifacts, setArtifacts] = useState<EvidenceArtifact[]>([]);
  const [validation, setValidation] = useState<ValidationExplainer>();
  const [semanticReview, setSemanticReview] = useState<SemanticReview>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.investigations(1, "BEHAVIOR_GAP_CONFIRMED").then(({ items }) => {
      const chosen = latest(items); setSelected(chosen);
      return chosen ? Promise.all([
        api.artifacts(chosen.id).then(({ items: value }) => setArtifacts(value)),
        api.validationExplainer(chosen.id).then(setValidation),
        api.semanticReview(chosen.id).then(setSemanticReview).catch(() => undefined),
      ]) : undefined;
    }).catch((value: Error) => setError(value.message)).finally(() => setLoading(false));
  }, []);
  const diff = useMemo(() => artifact(artifacts, "git_diff"), [artifacts]);
  const path = testPath(diff?.content);
  const checks = useMemo(() => new Map((validation?.checks ?? []).map((check) => [check.id, check])), [validation]);
  const issueUrl = selected && `https://github.com/${selected.repository}/issues/${selected.issue_number}`;
  const claim = semanticReview?.review?.evidence.claim;
  const detail = selected && `?id=${encodeURIComponent(selected.id)}`;

  if (loading) return <section className="demo-tour"><p role="status">Loading persisted evidence replay…</p></section>;
  if (error) return <section className="empty-state"><p className="eyebrow">Judge Demo Tour</p><h1>Evidence replay unavailable</h1><p>Recorded investigations could not be loaded: {error}</p><a className="button-link" href="/">Return to triage queue</a></section>;
  if (!selected) return <section className="empty-state"><p className="eyebrow">Judge Demo Tour</p><h1>No confirmed evidence case is available</h1><p>The tour only replays a persisted Behavior gap confirmed investigation. It never invents a successful case.</p><a className="button-link" href="/">Return to triage queue</a></section>;

  return <section className="demo-tour" aria-label="Judge Demo Tour">
    <div className="demo-topline"><a className="back-link" href="/">← Back to triage queue</a><span>Persisted evidence replay · read-only</span></div>
    <div className="demo-progress" aria-label={`Stage ${stage + 1} of 5`}>
      {stageTitles.map((title, index) => <button key={title} className={index === stage ? "active" : index < stage ? "seen" : ""} onClick={() => setStage(index)} aria-current={index === stage ? "step" : undefined}><i>{index + 1}</i><span>{title}</span></button>)}
    </div>
    <div className="demo-stage" key={stage}>
      {stage === 0 && <><p className="eyebrow">01 · The report</p><h1>Turn an issue into reviewable executable evidence—not an AI verdict.</h1><div className="demo-report"><span className="demo-icon" aria-hidden="true">#</span><div><a href={issueUrl} target="_blank" rel="noreferrer noopener"><b>{selected.repository} #{selected.issue_number}</b> ↗</a><h2>{selected.issue_title ?? "Untitled recorded issue"}</h2><p>This is the persisted issue record chosen for the replay.</p></div></div></>}
      {stage === 1 && <><p className="eyebrow">02 · Codex investigates</p><h1>Codex proposes; evidence decides.</h1><p className="demo-lede">The agent works in a bounded workspace, turning the report into a typed claim and then a focused test. It never gets to declare the final verdict.</p><div className="demo-pipeline" aria-label="Investigation pipeline"><div>Issue<br /><b>report</b></div><i>→</i><div>Typed<br /><b>claim</b></div><i>→</i><div>Isolated<br /><b>workspace</b></div><i>→</i><div>Focused<br /><b>test</b></div></div><div className="demo-claim"><b>Persisted claim</b><p>{claim?.available ? claim.summary ?? claim.actual_behavior ?? "A typed claim was recorded without a displayable summary." : "A persisted semantic claim is unavailable for this evidence record."}</p></div></>}
      {stage === 2 && <><p className="eyebrow">03 · Proof is checked</p><h1>Only deterministic gates can accept the proof.</h1><div className="demo-proof-grid"><section><p className="metadata">Changed focused test</p><h2>{path ?? "Changed test path unavailable"}</h2>{diff?.available && diff.content ? <pre className="evidence-code demo-diff"><code>{diff.content.split("\n").slice(0, 24).join("\n")}</code></pre> : <p className="artifact-unavailable">Git diff unavailable. {diff?.error ?? "No persisted diff is available."}</p>}</section><section className="demo-gate-board"><p className="metadata">Persisted validation gates</p>{gateOrder.map(([id, label]) => <Gate key={id} fallback={label} check={checks.get(id)} />)}</section></div></>}
      {stage === 3 && <><p className="eyebrow">04 · A bounded outcome</p><h1>{selected.classification === "BEHAVIOR_GAP_CONFIRMED" ? "Behavior gap confirmed." : "No behavior gap established."}</h1><div className="demo-decision"><span className={selected.asserts_failure ? "decision-mark confirmed" : "decision-mark"}>{selected.asserts_failure ? "✓" : "—"}</span><div><b>Deterministic validation reason</b><p>{selected.validation_reason ?? "No deterministic validation reason was retained."}</p></div></div><p className="brief-caveat">{boundedCaveat}</p></>}
      {stage === 4 && <><p className="eyebrow">05 · Review the evidence</p><h1>Every conclusion remains inspectable.</h1><p className="demo-lede">The replay ends at the original evidence—not a generated summary. Public views are read-only; no GitHub action is taken.</p><div className="demo-review-actions"><a className="button-link button-primary" href={detail}>Open complete evidence trail</a><a className="button-link" href={`?brief=1&id=${encodeURIComponent(selected.id)}`}>Open Evidence Brief</a></div><p className="demo-safety">Safety boundary: this tour reads persisted local evidence only. It does not call a model, start an investigation, or modify GitHub.</p></>}
    </div>
    <footer className="demo-controls"><button className="button-link" disabled={stage === 0} onClick={() => setStage((value) => value - 1)}>Back</button>{stage < 4 ? <><button className="demo-skip" onClick={() => setStage(4)}>Skip tour</button><button className="button-link button-primary" onClick={() => setStage((value) => value + 1)}>Continue <span aria-hidden="true">→</span></button></> : <a className="button-link button-primary" href={detail}>Review evidence <span aria-hidden="true">→</span></a>}</footer>
  </section>;
}
