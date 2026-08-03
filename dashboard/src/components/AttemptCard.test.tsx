import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { AttemptCard } from "./AttemptCard";
import type { TimelineAttempt } from "../services/api";

const attempt = (overrides: Partial<TimelineAttempt> = {}): TimelineAttempt => ({
  attempt_number: 1, hypothesis: "Missing TLS material should raise FileNotFoundError.", revision_reason: null,
  action: "Ran the focused pytest node.", result: "FAILING_TEST", duration_ms: 2400, ...overrides,
} as TimelineAttempt);

afterEach(cleanup);

it("shows the attempt number, hypothesis, action, and duration in seconds", () => {
  render(<AttemptCard attempt={attempt()} />);
  expect(screen.getByText("Attempt 1: FAILING_TEST")).toBeInTheDocument();
  expect(screen.getByText("Missing TLS material should raise FileNotFoundError.")).toBeInTheDocument();
  expect(screen.getByText("Ran the focused pytest node.")).toBeInTheDocument();
  expect(screen.getByText("2.4s")).toBeInTheDocument();
});

it("omits the revision reason and duration when neither was recorded", () => {
  render(<AttemptCard attempt={attempt({ revision_reason: null, duration_ms: null })} />);
  expect(screen.queryByText(/Revision reason/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Duration/)).not.toBeInTheDocument();
});

it("shows why a later attempt was revised", () => {
  render(<AttemptCard attempt={attempt({ attempt_number: 2, revision_reason: "Previous attempt made no repository changes." })} />);
  expect(screen.getByText("Previous attempt made no repository changes.")).toBeInTheDocument();
});
