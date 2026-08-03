import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

afterEach(cleanup);

it("renders bounded human labels rather than raw enum values", () => {
  render(<><StatusBadge value="BEHAVIOR_GAP_CONFIRMED" /><StatusBadge value="NEEDS_INFO" /><StatusBadge value="WONT_REPRO" /><StatusBadge value="NOT_A_BUG" /></>);
  expect(screen.getByText("Behavior gap confirmed")).toBeInTheDocument();
  expect(screen.getByText("Needs information")).toBeInTheDocument();
  // WONT_REPRO must never read as a defect judgment.
  expect(screen.getByText("No behavior gap established")).toBeInTheDocument();
  expect(screen.getByText("Possible non-defect framing")).toBeInTheDocument();
});

it("maps booleans and a missing classification without inventing a verdict", () => {
  render(<><StatusBadge value={true} /><StatusBadge value={false} /><StatusBadge value={null} /></>);
  expect(screen.getByText("TRUE")).toBeInTheDocument();
  expect(screen.getByText("FALSE")).toBeInTheDocument();
  expect(screen.getByText("No classification recorded")).toBeInTheDocument();
});

it("passes an unknown status through untranslated instead of guessing", () => {
  const { container } = render(<StatusBadge value="SOME_FUTURE_STATE" />);
  expect(screen.getByText("SOME_FUTURE_STATE")).toBeInTheDocument();
  expect(container.querySelector(".badge-some-future-state")).not.toBeNull();
});
