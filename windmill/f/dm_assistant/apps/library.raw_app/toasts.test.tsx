// @vitest-environment jsdom

import { act } from "react";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ToastStack, toast } from "./toasts";

describe("global toast bus", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); toast.resetForTest(); cleanup(); });

  it("shows pushes and dismisses on click", async () => {
    render(<ToastStack />);
    await act(async () => toast.push("success", "Added Ruhrogue to Carpet Rollers"));
    expect(screen.getByText("Added Ruhrogue to Carpet Rollers")).toBeInTheDocument();
    await act(async () => fireEvent.click(screen.getByText("Added Ruhrogue to Carpet Rollers")));
    expect(screen.queryByText("Added Ruhrogue to Carpet Rollers")).not.toBeInTheDocument();
  });

  it("roles errors as alerts and auto-dismisses", async () => {
    render(<ToastStack />);
    await act(async () => toast.push("error", "Grand Inquisitor is currently held by Eustice"));
    expect(screen.getByRole("alert")).toHaveTextContent("held by Eustice");
    await act(async () => vi.advanceTimersByTime(7000));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("refreshes an identical message instead of stacking duplicates", async () => {
    render(<ToastStack />);
    await act(async () => { toast.push("info", "Roster refreshed"); toast.push("info", "Roster refreshed"); });
    expect(screen.getAllByText("Roster refreshed")).toHaveLength(1);
  });

  it("records every push in the session log, repeats included", async () => {
    render(<ToastStack />);
    await act(async () => { toast.push("info", "Roster refreshed"); toast.push("info", "Roster refreshed"); });
    const entries = toast.logEntries();
    expect(entries).toHaveLength(2);
    expect(entries.every((entry) => entry.message === "Roster refreshed" && entry.kind === "info")).toBe(true);
    expect(typeof entries[0].at).toBe("string");
  });

  it("caps the visible stack", async () => {
    render(<ToastStack />);
    await act(async () => { for (let index = 0; index < 6; index++) toast.push("info", `Notice ${index}`); });
    expect(screen.queryByText("Notice 0")).not.toBeInTheDocument();
    expect(screen.getByText("Notice 5")).toBeInTheDocument();
  });
});
