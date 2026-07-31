import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { JudgeDemoTour } from "./JudgeDemoTour";

const confirmed = { id: "confirmed-1", repository: "psf/requests", issue_number: 7564, issue_title: "TLS behavior", test_runner: "pytest", status: "COMPLETED", classification: "BEHAVIOR_GAP_CONFIRMED", asserts_failure: true, validation_reason: "The focused assertion failed.", reproducibility_status: "STABLE", attempt_count: 1, started_at: null, updated_at: "2026-07-01T00:00:00Z", completed_at: "2026-07-01T00:00:00Z", duration_seconds: 2, cost_usd: null, tracked_llm_api_cost_usd: null, tracked_llm_api_latency_ms: null, tracked_llm_api_input_tokens: null, tracked_llm_api_cached_input_tokens: null, tracked_llm_api_output_tokens: null, tracked_llm_api_cost_status: "unavailable", tracked_llm_api_latency_status: "unavailable", tracked_llm_api_explanation: "No tracked LLM API calls are linked." };
afterEach(cleanup);

it("replays persisted evidence and exposes truthful deterministic gates", async () => {
  vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => {
    if (url.includes("/artifacts")) return { items: [{ id: "diff", kind: "git_diff", path: "git.diff", available: true, content: "+++ b/tests/test_tls.py\n+def test_tls():", size_bytes: 1, modified_at: null, error: null }] };
    if (url.includes("validation-explainer")) return { version: "v1", conclusion: "BEHAVIOR_GAP_CONFIRMED", checks: [{ id: "exact_focused_test_selection", label: "Exact focused-test selection", status: "PASS", explanation: "Exact target recorded.", artifact_kind: "focused_test_selection" }, { id: "proof_pattern_integrity", label: "Proof-pattern integrity", status: "PASS", explanation: "Proof accepted.", artifact_kind: "proof_integrity_report" }, { id: "structured_junit_result", label: "Valid structured JUnit result", status: "PASS", explanation: "JUnit recorded.", artifact_kind: "structured_test_results_junit" }, { id: "clean_execution", label: "No setup, error, or timeout", status: "PASS", explanation: "Clean.", artifact_kind: "structured_test_results_junit" }, { id: "confirmation_match", label: "Confirmation rerun matches", status: "PASS", explanation: "Matches.", artifact_kind: "reproducibility_manifest" }] };
    if (url.includes("semantic-review")) return { packet_status: "AVAILABLE", reason: null, review: { packet_version: 1, evidence: { claim: { available: true, summary: "TLS claim" }, generated_test: { available: false }, junit: { available: false } }, state: "OPEN", display_state: "Open", coverage: {} } };
    return { items: [confirmed] };
  } })));
  render(<JudgeDemoTour />);
  await waitFor(() => expect(screen.getByRole("heading", { name: /Turn an issue/ })).toBeInTheDocument());
  expect(screen.getByText("psf/requests #7564")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Continue/ }));
  await waitFor(() => expect(screen.getByText("TLS claim")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /Continue/ }));
  expect(screen.getByText("tests/test_tls.py")).toBeInTheDocument();
  expect(screen.getAllByText("Passed")).toHaveLength(5);
  fireEvent.click(screen.getByRole("button", { name: "Skip tour" }));
  expect(screen.getByRole("link", { name: "Open complete evidence trail" })).toHaveAttribute("href", "?id=confirmed-1");
});

it("does not fabricate a confirmed replay when none exists", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) }));
  render(<JudgeDemoTour />);
  await waitFor(() => expect(screen.getByText("No confirmed evidence case is available")).toBeInTheDocument());
});
