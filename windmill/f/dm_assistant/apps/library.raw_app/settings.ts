import { useEffect, useState } from "react";

/** DM-managed UI preferences (TKT-0114). Client-side only — nothing here
 * changes Core behavior or campaign truth. Storage mirrors the existing
 * library-panel-collapse localStorage pattern. */

export type PartialSettings = Partial<Settings>;

/** Where the tray array anchors on the bottom edge. */
export type TrayAnchor = "left" | "right" | "centered";

export interface TrayLayout {
  anchor: TrayAnchor;
  session: boolean; // session notes tray launcher visible
  drafts: boolean; // Drafts tray launcher visible when idle
  search: boolean; // Ask-the-archive launcher visible (the topbar icon always works)
}

export interface RecordsVisibility {
  sources: boolean; // sources & provenance drawers/details
  earlierVersions: boolean; // superseded claim history blocks
}

export interface Settings {
  toastsEnabled: boolean;
  toastDurationMs: number;
  logErrorsOnly: boolean;
  hiddenNavPages: string[]; // nav button labels, e.g. ["Migration", "Conventions"]
  trayLayout: TrayLayout;
  recordsVisibility: RecordsVisibility;
  showLegacyMigration: boolean; // phase-1 import wizard (shelved 2026-09-21; session-note review still lives there until re-homed)
}

export const DEFAULT_SETTINGS: Settings = {
  toastsEnabled: true,
  toastDurationMs: 6500,
  logErrorsOnly: false,
  hiddenNavPages: [],
  trayLayout: { anchor: "right", session: true, drafts: true, search: true },
  recordsVisibility: { sources: false, earlierVersions: false },
  showLegacyMigration: false,
};

const STORAGE_KEY = "dm-assistant.settings";

type Listener = (settings: Settings) => void;
const listeners = new Set<Listener>();

function read(): Settings {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<Settings>;
    const stored = parsed.trayLayout as Partial<TrayLayout> & { session?: string; drafts?: string } | undefined;
    // Migrate the pre-0128 per-side layout: either non-hidden side anchors the array.
    const migrated: TrayAnchor = stored && (stored.session === "left" || stored.drafts === "left")
      ? "left" : "centered" === (stored?.anchor as TrayAnchor | undefined) ? "centered" : "right";
    const tray: TrayLayout = {
      anchor: (stored?.anchor as TrayAnchor | undefined) ?? migrated,
      session: typeof stored?.session === "boolean" ? stored.session : stored?.session !== "hidden",
      drafts: typeof stored?.drafts === "boolean" ? stored.drafts : stored?.drafts !== "hidden",
      search: stored?.search ?? true,
    };
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      hiddenNavPages: Array.isArray(parsed.hiddenNavPages) ? parsed.hiddenNavPages : [],
      trayLayout: tray,
      recordsVisibility: {
        sources: parsed.recordsVisibility?.sources ?? DEFAULT_SETTINGS.recordsVisibility.sources,
        earlierVersions: parsed.recordsVisibility?.earlierVersions ?? DEFAULT_SETTINGS.recordsVisibility.earlierVersions,
      },
    };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

let current: Settings = read();

export function getSettings(): Settings {
  return current;
}

export function updateSettings(changes: Partial<Settings>): void {
  current = { ...current, ...changes };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
  } catch {
    // browser storage may be unavailable; in-memory settings still apply
  }
  for (const listener of listeners) listener(current);
}

export function subscribeToSettings(listener: Listener): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

/** Reset-for-test: clears storage and listeners' cached state. */
export function resetSettingsForTest(): void {
  current = { ...DEFAULT_SETTINGS, hiddenNavPages: [] };
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
  for (const listener of listeners) listener(current);
}

/** React hook: live settings that re-render on change. */
export function useSettings(): [Settings, (changes: Partial<Settings>) => void] {
  const [settings, setSettings] = useState<Settings>(current);
  useEffect(() => subscribeToSettings(setSettings), []);
  return [settings, updateSettings];
}
