import { useEffect, useState } from "react";

export type ToastKind = "success" | "error" | "info";

export interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

export interface LogEntry {
  id: number;
  at: string;
  kind: ToastKind;
  message: string;
}

type Listener = (items: ToastItem[]) => void;
type LogListener = (entries: LogEntry[]) => void;

const DISMISS_AFTER_MS = 6500;
const MAX_VISIBLE = 4;
const MAX_LOG = 200;

let nextId = 1;
let items: ToastItem[] = [];
let log: LogEntry[] = [];
const timers = new Map<number, ReturnType<typeof setTimeout>>();
const listeners = new Set<Listener>();
const logListeners = new Set<LogListener>();

function emit(): void {
  for (const listener of listeners) listener(items);
}

function emitLog(): void {
  for (const listener of logListeners) listener(log);
}

function scheduleDismiss(id: number): void {
  const existing = timers.get(id);
  if (existing) clearTimeout(existing);
  timers.set(id, setTimeout(() => dismiss(id), DISMISS_AFTER_MS));
}

function dismiss(id: number): void {
  const timer = timers.get(id);
  if (timer) clearTimeout(timer);
  timers.delete(id);
  if (!items.some((item) => item.id === id)) return;
  items = items.filter((item) => item.id !== id);
  emit();
}

/**
 * App-wide transient notifications and the session activity log (TKT-0112/0113).
 * One event vocabulary: every push is recorded in the log (repeats included —
 * a repeated event is still an event) while the toast stack dedupes identical
 * visible messages. Session events are browser-session scoped; durable
 * decisions live in Campaign Core's audit tables and are merged on the Log page.
 */
export const toast = {
  push(kind: ToastKind, message: string): void {
    const trimmed = message.trim();
    if (!trimmed) return;
    log = [...log, { id: nextId++, at: new Date().toISOString(), kind, message: trimmed }].slice(-MAX_LOG);
    emitLog();
    const existing = items.find((item) => item.message === trimmed);
    if (existing) {
      scheduleDismiss(existing.id);
      emit();
      return;
    }
    const item: ToastItem = { id: nextId++, kind, message: trimmed };
    items = [...items, item].slice(-MAX_VISIBLE);
    scheduleDismiss(item.id);
    emit();
  },
  dismiss,
  logEntries(): LogEntry[] {
    return log;
  },
  subscribeLog(listener: LogListener): () => void {
    logListeners.add(listener);
    listener(log);
    return () => { logListeners.delete(listener); };
  },
  resetForTest(): void {
    for (const timer of timers.values()) clearTimeout(timer);
    timers.clear();
    items = [];
    log = [];
    emit();
    emitLog();
  },
};

export function ToastStack() {
  const [visible, setVisible] = useState<ToastItem[]>(items);
  useEffect(() => {
    const listener: Listener = (next) => setVisible([...next]);
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, []);
  if (visible.length === 0) return null;
  return <div className="toast-stack" aria-label="Notifications">
    {visible.map((item) => (
      <div
        className={`toast toast-${item.kind}`}
        key={item.id}
        onClick={() => dismiss(item.id)}
        role={item.kind === "error" ? "alert" : "status"}
        title="Dismiss"
      >
        {item.message}
      </div>
    ))}
  </div>;
}
