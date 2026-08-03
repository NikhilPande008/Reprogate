import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ASSERTS_FAILURE_EXPLANATION, VALIDATION_REASON_EXPLANATION, ValidationHelp } from "./ValidationHelp";

afterEach(cleanup);

it("explains assertsFailure as deterministic and never model-decided", () => {
  render(<ValidationHelp kind="assertsFailure" />);
  expect(screen.getByText(ASSERTS_FAILURE_EXPLANATION)).toBeInTheDocument();
  expect(ASSERTS_FAILURE_EXPLANATION).toMatch(/never decided by a model/);
});

it("explains the validation reason and labels the disclosure for screen readers", () => {
  render(<ValidationHelp kind="validation reason" />);
  expect(screen.getByText(VALIDATION_REASON_EXPLANATION)).toBeInTheDocument();
  expect(screen.getByLabelText("About validation reason")).toBeInTheDocument();
});
