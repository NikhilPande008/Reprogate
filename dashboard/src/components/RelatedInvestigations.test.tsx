import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { RelatedInvestigations } from "./RelatedInvestigations";

afterEach(cleanup);

it("distinguishes an analysis that ran and matched nothing from one that never ran", () => {
  render(<RelatedInvestigations data={{ items: [], available: true, reason: null }} />);
  expect(screen.getByText(/analysis completed/i)).toBeInTheDocument();
  expect(screen.getByText(/No investigation met the configured similarity threshold/)).toBeInTheDocument();
});

it("surfaces the recorded reason when duplicate analysis is unavailable", () => {
  render(<RelatedInvestigations data={{ items: [], available: false, reason: "Duplicate analysis unavailable: no completed similarity document" }} />);
  expect(screen.getByText("Duplicate analysis unavailable: no completed similarity document")).toBeInTheDocument();
  expect(screen.queryByText(/analysis completed/i)).not.toBeInTheDocument();
});

it("lists related investigations with their score and matched signals", () => {
  render(<RelatedInvestigations data={{ available: true, reason: null, items: [{ investigation_id: "run-9", repository: "psf/requests", issue_number: 7001, classification: "NEEDS_INFO", status: "COMPLETED_NO_GAP", similarity_score: 0.82, matched_signals: ["high overlap structured evidence"], label: "Potentially related investigation" }] }} />);
  expect(screen.getByRole("link", { name: "psf/requests #7001" })).toHaveAttribute("href", "?id=run-9");
  expect(screen.getByText("82% match")).toBeInTheDocument();
  expect(screen.getByText("high overlap structured evidence")).toBeInTheDocument();
});

it("always states that similarity is advisory only", () => {
  render(<RelatedInvestigations data={{ items: [], available: true, reason: null }} />);
  expect(screen.getByText(/never changes a classification, verdict, or maintainer action/)).toBeInTheDocument();
});

it("renders nothing before the related payload has loaded", () => {
  const { container } = render(<RelatedInvestigations data={undefined} />);
  expect(container).toBeEmptyDOMElement();
});
