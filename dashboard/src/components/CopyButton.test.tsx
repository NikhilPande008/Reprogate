import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CopyButton } from "./CopyButton";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("copies the value and reports success through a live region", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(<CopyButton value="run-1234" label="Copy investigation ID" />);
  fireEvent.click(screen.getByRole("button", { name: "Copy investigation ID" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Copied to clipboard."));
  expect(writeText).toHaveBeenCalledWith("run-1234");
});

it("reports a clipboard failure instead of claiming a successful copy", async () => {
  vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
  render(<CopyButton value="run-1234" />);
  fireEvent.click(screen.getByRole("button", { name: "Copy" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Unable to copy to clipboard."));
});

it("reports a failure when the clipboard API is entirely unavailable", async () => {
  vi.stubGlobal("navigator", {});
  render(<CopyButton value="run-1234" />);
  fireEvent.click(screen.getByRole("button", { name: "Copy" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Unable to copy to clipboard."));
});
