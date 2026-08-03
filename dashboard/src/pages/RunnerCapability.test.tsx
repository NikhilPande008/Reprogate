import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { RunnerCapability } from "./RunnerCapability";

const matrix = {
  schema_version: "runner-capability-v1",
  caveats: ["This matrix declares implemented adapter capability."],
  items: [
    { runner_id: "pytest", implemented: true, confirmation_capable: true, selection_precision: "EXACT", structured_results: "JUnit XML required", summary: "Default runner.", constraint: "Requires a resolvable setup command.", recorded_investigations: 5, recorded_confirmations: 3 },
    { runner_id: "jest", implemented: true, confirmation_capable: false, selection_precision: "FILE_ONLY", structured_results: "Not mapped", summary: "Diagnostic only.", constraint: "Exact selection is not implemented.", recorded_investigations: 0, recorded_confirmations: 0 },
    { runner_id: "go", implemented: false, confirmation_capable: false, selection_precision: "UNAVAILABLE", structured_results: "Not implemented", summary: "Not implemented.", constraint: "Future adapter target.", recorded_investigations: 0, recorded_confirmations: 0 },
  ],
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("separates implemented runners from unimplemented ones", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => matrix }));
  render(<RunnerCapability />);
  await waitFor(() => expect(screen.getByRole("heading", { name: /Which runners can reach a confirmation/ })).toBeInTheDocument());
  expect(screen.getByRole("cell", { name: /pytest/ })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Not implemented" })).toBeInTheDocument();
  expect(screen.getByText(/Future adapter target/)).toBeInTheDocument();
});

it("shows a zero recorded count rather than hiding an unexercised runner", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => matrix }));
  render(<RunnerCapability />);
  await waitFor(() => expect(screen.getByText("5 investigations")).toBeInTheDocument());
  expect(screen.getByText("0 investigations")).toBeInTheDocument();
  expect(screen.getByText("3 with assertsFailure")).toBeInTheDocument();
});

it("states that declared capability is not evidence of a confirmation", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => matrix }));
  render(<RunnerCapability />);
  await waitFor(() => expect(screen.getByText(/deliberately not a claim that any runner has confirmed/)).toBeInTheDocument());
});

it("reports a load failure instead of rendering an empty matrix", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: "unavailable" }) }));
  render(<RunnerCapability />);
  await waitFor(() => expect(screen.getByText("Capability matrix unavailable")).toBeInTheDocument());
});
