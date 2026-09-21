// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_SETTINGS, getSettings, resetSettingsForTest, subscribeToSettings, updateSettings,
} from "./settings";
import { toast } from "./toasts";

beforeEach(() => { resetSettingsForTest(); });
afterEach(() => { resetSettingsForTest(); cleanup(); window.localStorage.clear(); });

describe("settings store", () => {
  it("defaults apply and persist to localStorage", () => {
    expect(getSettings()).toEqual(DEFAULT_SETTINGS);
    updateSettings({ logErrorsOnly: true, hiddenNavPages: ["Migration"] });
    expect(getSettings().logErrorsOnly).toBe(true);
    expect(window.localStorage.getItem("dm-assistant.settings")).toContain("Migration");
  });

  it("notifies subscribers and stops on unsubscribe", () => {
    const seen: boolean[] = [];
    const unsubscribe = subscribeToSettings((settings) => seen.push(settings.logErrorsOnly));
    updateSettings({ logErrorsOnly: true });
    unsubscribe();
    updateSettings({ logErrorsOnly: false });
    expect(seen).toEqual([true]);
  });
});

describe("toast settings integration", () => {
  it("disabled toasts skip the visible stack but the log still records", async () => {
    const { ToastStack } = await import("./toasts");
    updateSettings({ toastsEnabled: false });
    render(<ToastStack />);
    await act(async () => { toast.push("success", "hidden from screen"); });
    expect(screen.queryByText("hidden from screen")).not.toBeInTheDocument();
    expect(toast.logEntries()).toHaveLength(1);

    updateSettings({ toastsEnabled: true });
    await act(async () => { toast.push("error", "back on screen"); });
    expect(await screen.findByText("back on screen")).toBeInTheDocument();
  });
});
