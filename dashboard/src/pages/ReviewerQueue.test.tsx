import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ReviewerQueue } from "./ReviewerQueue";

const user = { reviewer: { external_id: "rev1", cohort: "MAINTAINER", posting_approver: true, repositories: ["psf/requests"] }, csrf_token: "csrf", expires_at: "2026-08-03T19:00:00Z" };
const queueItem = { packet_id: "packet-1", investigation_id: "run-1", repository: "psf/requests", issue_number: 7564, issue_title: "TLS material", classification: "BEHAVIOR_GAP_CONFIRMED", asserts_failure: true, consensus_state: "PENDING_REVIEW", coverage: { MAINTAINER: 0, INDEPENDENT_ENGINEER: 0 }, comment_status: null, posting_eligibility: "REVIEW_REQUIRED", review_age_started_at: null };

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("requires sign in before any reviewer evidence is shown", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: "Pilot session required" }) }));
  render(<ReviewerQueue />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Reviewer sign in" })).toBeInTheDocument());
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(screen.getByLabelText(/Reviewer token/)).toHaveAttribute("type", "password");
});

it("exchanges the token once and then loads the scoped queue", async () => {
  const fetchMock = vi.fn((url: string) => {
    if (url.includes("/pilot-review/me")) return Promise.resolve({ ok: false, status: 401, json: async () => ({ detail: "Pilot session required" }) });
    if (url.includes("/pilot-review/login")) return Promise.resolve({ ok: true, json: async () => user });
    return Promise.resolve({ ok: true, json: async () => ({ items: [queueItem] }) });
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ReviewerQueue />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Reviewer sign in" })).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText(/Reviewer ID/), { target: { value: "rev1" } });
  fireEvent.change(screen.getByLabelText(/Reviewer token/), { target: { value: "t0ken" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Reviewer queue" })).toBeInTheDocument());
  expect(screen.getByRole("link", { name: "psf/requests #7564" })).toHaveAttribute("href", "/?reviewer=1&packet=packet-1");
  expect(screen.getByText("PENDING_REVIEW")).toBeInTheDocument();
});

it("states that semantic review never changes the investigation verdict", async () => {
  vi.stubGlobal("fetch", vi.fn((url: string) => url.includes("/pilot-review/me")
    ? Promise.resolve({ ok: true, json: async () => user })
    : Promise.resolve({ ok: true, json: async () => ({ items: [queueItem] }) })));
  render(<ReviewerQueue />);
  await waitFor(() => expect(screen.getByText(/does not change the investigation verdict/)).toBeInTheDocument());
});

it("reports an empty queue rather than an empty table", async () => {
  vi.stubGlobal("fetch", vi.fn((url: string) => url.includes("/pilot-review/me")
    ? Promise.resolve({ ok: true, json: async () => user })
    : Promise.resolve({ ok: true, json: async () => ({ items: [] }) })));
  render(<ReviewerQueue />);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("No cases currently require reviewer attention."));
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
