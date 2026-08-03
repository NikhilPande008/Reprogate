import { useEffect, useState } from "react";
import { api, type RunnerCapabilityMatrix } from "../services/api";

function Mark({ value }: { value: boolean }) {
  return <span className={value ? "runner-mark runner-mark-yes" : "runner-mark"} aria-label={value ? "yes" : "no"}>{value ? "✓" : "—"}</span>;
}

export function RunnerCapability() {
  const [data, setData] = useState<RunnerCapabilityMatrix>();
  const [error, setError] = useState<string>();
  useEffect(() => { api.runnerCapability().then(setData).catch((value: Error) => setError(value.message)); }, []);

  if (error) return <section className="empty-state"><p className="eyebrow">Runner capability</p><h1>Capability matrix unavailable</h1><p>{error}</p><a className="button-link" href="/">Return to triage queue</a></section>;
  if (!data) return <section><p role="status">Loading declared runner capability…</p></section>;
  const implemented = data.items.filter((item) => item.implemented);
  const planned = data.items.filter((item) => !item.implemented);

  return <section className="runner-page">
    <p className="eyebrow">Declared adapter capability</p>
    <h1>Which runners can reach a confirmation</h1>
    <p className="results-caveat">This page declares what each adapter is built to do. It is deliberately not a claim that any runner has confirmed a behavior gap here — recorded counts below come from persisted local investigations only, and a zero is shown as a zero.</p>

    <div className="runner-table-scroll">
      <table className="runner-table">
        <thead><tr><th>Runner</th><th>Confirmation-capable</th><th>Selection precision</th><th>Structured results</th><th>Recorded locally</th></tr></thead>
        <tbody>
          {implemented.map((item) => <tr key={item.runner_id}>
            <td><b>{item.runner_id}</b><p className="metadata">{item.summary}</p></td>
            <td><Mark value={item.confirmation_capable} /></td>
            <td>{item.selection_precision}</td>
            <td>{item.structured_results}</td>
            <td>{item.recorded_investigations} investigation{item.recorded_investigations === 1 ? "" : "s"}<p className="metadata">{item.recorded_confirmations} with assertsFailure</p></td>
          </tr>)}
        </tbody>
      </table>
    </div>

    <section className="card">
      <h2>Why a runner stops short</h2>
      <ul className="runner-constraints">{implemented.map((item) => <li key={item.runner_id}><b>{item.runner_id}</b> — {item.constraint}</li>)}</ul>
    </section>

    <section className="card">
      <h2>Not implemented</h2>
      <p className="metadata">Selecting one of these fails explicitly rather than guessing at a result.</p>
      <ul className="runner-constraints">{planned.map((item) => <li key={item.runner_id}><b>{item.runner_id}</b> — {item.constraint}</li>)}</ul>
    </section>

    <section className="card">
      <h2>Boundaries</h2>
      <ul className="runner-constraints">{data.caveats.map((item) => <li key={item}>{item}</li>)}</ul>
      <p className="metadata">Schema {data.schema_version}. The canonical definition is the Runner Capability Contract v1 in the repository.</p>
    </section>
  </section>;
}
