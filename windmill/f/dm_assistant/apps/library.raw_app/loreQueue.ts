/**
 * Lore creation queue (TKT-0099) — browser-local capture of names that need
 * campaign entries. NOT canonical: queued names are a to-look-at list, never
 * entities. Resolution through Core creates/links explicitly.
 */

export type LoreQueueStatus = "queued" | "resolved" | "dismissed";

export interface LoreQueueItem {
  id: string;
  name: string;
  context: string; // where it was queued from
  notes: string;
  queuedAt: string;
  status: LoreQueueStatus;
  resolvedAs?: string; // entity name it resolved to, or "dismissed"
  // Evidence workspace state (persists through refresh).
  savedEvidence?: SavedEvidence;
}

/** The evidence a working Lore item has accumulated — linked (included as
 * referenced records) and considered (kept for reference) claims — plus the
 * working file itself. Rule of thumb for workspaces (user ruling
 * 2026-09-21): the user should never have to worry about data loss, so the
 * kind, direction, and description auto-save with the evidence. */
export interface SavedEvidence {
  claims: Array<{
    claim_id: string;
    assertion_text: string;
    state: string;
    authority: string;
    source_excerpt?: string;
    owner_name?: string;
  }>;
  linkedClaimIds: string[];
  consideredClaimIds: string[];
  chosenKind?: string;
  direction?: string;
  prose?: string;
}

const STORAGE_KEY = "dm-assistant.loreQueue";

type Listener = (items: LoreQueueItem[]) => void;
const listeners = new Set<Listener>();
let items: LoreQueueItem[] = load();

function load(): LoreQueueItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as LoreQueueItem[];
    return Array.isArray(parsed) ? parsed.filter((item) => item && item.id && item.name) : [];
  } catch { return []; }
}

function persist(): void {
  try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); }
  catch { /* browser-local only; in-memory still works */ }
  for (const listener of listeners) listener(items);
}

export function getLoreQueue(): LoreQueueItem[] {
  return items;
}

export function subscribeLoreQueue(listener: Listener): () => void {
  listeners.add(listener);
  listener(items);
  return () => { listeners.delete(listener); };
}

export function queueForLore(name: string, context: string = "", notes: string = ""): LoreQueueItem {
  const trimmed = name.trim();
  if (!trimmed) throw new Error("a name is required to queue for Lore");
  // Idempotent: queueing the same name from the same context does not duplicate.
  const existing = items.find(
    (item) => item.status === "queued" && item.name.toLocaleLowerCase() === trimmed.toLocaleLowerCase());
  if (existing) {
    if (context && !existing.context.includes(context)) {
      existing.context = existing.context ? `${existing.context}; ${context}` : context;
      persist();
    }
    return existing;
  }
  const item: LoreQueueItem = {
    id: crypto.randomUUID(),
    name: trimmed, context, notes,
    queuedAt: new Date().toISOString(),
    status: "queued",
  };
  items = [...items, item];
  persist();
  return item;
}

export function resolveLoreItem(id: string, resolvedAs: string): void {
  items = items.map((item) => item.id === id ? { ...item, status: "resolved", resolvedAs } : item);
  persist();
}

export function dismissLoreItem(id: string): void {
  items = items.map((item) => item.id === id ? { ...item, status: "dismissed", resolvedAs: "dismissed" } : item);
  persist();
}

export function updateLoreNotes(id: string, notes: string): void {
  items = items.map((item) => item.id === id ? { ...item, notes } : item);
  persist();
}

/** Save the evidence workspace state for a working Lore item. */
export function saveLoreEvidence(id: string, evidence: SavedEvidence): void {
  items = items.map((item) => item.id === id ? { ...item, savedEvidence: evidence } : item);
  persist();
}

export function resetLoreQueueForTest(): void {
  items = [];
  try { window.localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  for (const listener of listeners) listener(items);
}
