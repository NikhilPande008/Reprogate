import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ReviewerPacket } from "./ReviewerPacket";

const packet = {
  id: "packet-1", investigation_id: "run-1", repository: "psf/requests", issue_number: 7564, issue_title: "TLS material",
  version: 1, state: "OPEN", display_state: "Open", coverage: { MAINTAINER: 0, INDEPENDENT_ENGINEER: 0 },
  evidence: { claim: { available: true, summary: "Missing TLS material should raise FileNotFoundError." }, generated_test: { available: false }, junit: { available: false } },
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("renders the immutable packet and states that review never changes classification", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ packet }) }));
  render(<ReviewerPacket packetId="packet-1" />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "psf/requests #7564" })).toBeInTheDocument());
  expect(screen.getByText(/never changes deterministic validation or classification/)).toBeInTheDocument();
});

it("derives the outcome from the four judgments before submission", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ packet }) }));
  render(<ReviewerPacket packetId="packet-1" />);
  await waitFor(() => expect(screen.getByText("ALIGNED")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText(/Does the generated test represent that claim\?/), { target: { value: "UNCERTAIN" } });
  await waitFor(() => expect(screen.getByText("UNCLEAR")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText(/Does the extraction represent the bounded behavior claim\?/), { target: { value: "NO" } });
  await waitFor(() => expect(screen.getByText("MISALIGNED")).toBeInTheDocument());
});

it("requires a rationale once the derived outcome is not aligned", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ packet }) }));
  render(<ReviewerPacket packetId="packet-1" />);
  await waitFor(() => expect(screen.getByText("ALIGNED")).toBeInTheDocument());
  expect(screen.getByLabelText(/Rationale \(optional\)/)).not.toBeRequired();
  fireEvent.change(screen.getByLabelText(/Would a public comment be appropriate\?/), { target: { value: "NO" } });
  await waitFor(() => expect(screen.getByLabelText(/Rationale \(required\)/)).toBeRequired());
});

it("reports the recorded derived outcome after an append-only submission", async () => {
  vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => init?.method === "POST"
    ? Promise.resolve({ ok: true, json: async () => ({ id: "assessment-1", derived_review_outcome: "ALIGNED" }) })
    : Promise.resolve({ ok: true, json: async () => ({ packet }) })));
  render(<ReviewerPacket packetId="packet-1" />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Submit append-only assessment/ })).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /Submit append-only assessment/ }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Assessment recorded with derived outcome: ALIGNED."));
});

it("surfaces a packet load failure instead of an empty review form", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: "Not found" }) }));
  render(<ReviewerPacket packetId="missing" />);
  await waitFor(() => expect(screen.getByText(/Unable to load review packet/)).toBeInTheDocument());
  expect(screen.queryByRole("button", { name: /Submit/ })).not.toBeInTheDocument();
});
