import { StatusBadge } from "./StatusBadge";
import type { RelatedInvestigation } from "../services/api";

export function RelatedInvestigations({ data }: { data?: { items: RelatedInvestigation[]; available: boolean; reason: string | null } }) {
  if (!data) return null;
  // An analysis that ran and matched nothing is evidence; an analysis that
  // never ran is not. The two are reported separately and never merged.
  const body = !data.available
    ? <p className="metadata">{data.reason ?? "Advisory duplicate analysis is unavailable for this investigation."}</p>
    : data.items.length === 0
      ? <p className="metadata">Advisory similarity analysis completed against other investigations in this repository. No investigation met the configured similarity threshold, so none is suggested as related.</p>
      : <ul className="related-list">{data.items.map((item) => <li key={item.investigation_id}><a href={`?id=${encodeURIComponent(item.investigation_id)}`}><b>{item.repository} #{item.issue_number}</b></a><span className="related-score">{Math.round(item.similarity_score * 100)}% match</span><StatusBadge value={item.classification} /><p className="metadata">{item.matched_signals.join(" · ")}</p></li>)}</ul>;
  return <section className="card" id="related"><div className="section-heading"><div><p className="eyebrow">Advisory only</p><h2>Potentially related investigations</h2></div></div>{body}<p className="metadata">Similarity is advisory and never changes a classification, verdict, or maintainer action.</p></section>;
}
