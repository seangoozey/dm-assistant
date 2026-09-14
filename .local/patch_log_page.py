from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

# --- Component before AppProps ---
anchor = "interface AppProps {"
component = """function ActivityLogPage({ campaignClient }: { campaignClient: CampaignClient }) {
  const [sessionEvents, setSessionEvents] = useState<LogEntry[]>([]);
  const [decisions, setDecisions] = useState<IdentityDecisionEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "errors">("all");
  const [notice, setNotice] = useState("");

  useEffect(() => toast.subscribeLog(setSessionEvents), []);

  const loadDecisions = useCallback(async () => {
    setLoading(true);
    try {
      setDecisions(await campaignClient.listRecentDecisions(100));
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Decisions could not be loaded");
    } finally { setLoading(false); }
  }, [campaignClient]);

  useEffect(() => { if (decisions === null && !loading) void loadDecisions(); }, [decisions === null, loading, loadDecisions]);

  const timeOf = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const decisionSummary = (decision: IdentityDecisionEntry) => {
    const details = (decision.details ?? {}) as Record<string, unknown>;
    const action = typeof details.action === "string" ? details.action : null;
    const parts = [
      action ? display(action) : null,
      typeof details.role_name === "string" ? `role: ${details.role_name}` : null,
      typeof details.member_name === "string" ? `member: ${details.member_name}` : null,
      typeof details.faction_name === "string" ? `faction: ${details.faction_name}` : null,
    ].filter(Boolean);
    return parts.length > 0 ? parts.join(" · ") : null;
  };
  const rows = [
    ...sessionEvents.map((event) => ({
      key: `session-${event.id}`, at: event.at, time: timeOf(event.at),
      kind: event.kind, label: event.kind === "success" ? "Done" : event.kind === "error" ? "Error" : "Notice",
      message: event.message, detail: null as string | null, source: "This session",
    })),
    ...(decisions ?? []).map((decision) => ({
      key: `decision-${decision.decision_id}`, at: decision.decided_at, time: timeOf(decision.decided_at),
      kind: "decision" as const, label: `Decision · ${display(decision.kind)}`,
      message: decision.surface, detail: decisionSummary(decision), source: "Campaign Core audit",
    })),
  ].sort((left, right) => right.at.localeCompare(left.at));
  const visible = filter === "errors" ? rows.filter((row) => row.kind === "error") : rows;

  return <main className="page-log">
    <section className="identity-page-header" aria-label="Activity log">
      <div className="section-heading"><div><p className="kicker">Maintenance</p><h2>Activity Log</h2></div><p>Every outcome this session plus the durable decision audit from Campaign Core — newest first. Session events live in this browser; decisions persist with receipts.</p></div>
      <div className="identity-toolbar">
        <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")} type="button">All</button>
        <button className={filter === "errors" ? "active" : ""} onClick={() => setFilter("errors")} type="button">Errors only</button>
        <button className="secondary-button" disabled={loading} onClick={() => void loadDecisions()} type="button">{loading ? "Working…" : "Refresh"}</button>
      </div>
      {notice && <p role="alert" className="identity-message notice error">{notice}</p>}
    </section>
    <p className="identity-count">Showing {visible.length} event{visible.length === 1 ? "" : "s"} · {sessionEvents.length} this session · {decisions?.length ?? 0} audited decisions</p>
    {visible.length === 0 && <p className="identity-empty">Nothing logged yet.</p>}
    <ul className="log-list" aria-label="Activity events">
      {visible.slice(0, 300).map((row) => <li className={`log-row log-${row.kind}`} key={row.key}>
        <time>{row.time}</time>
        <span className="log-kind">{row.label}</span>
        <span className="log-message">{row.message}{row.detail ? ` — ${row.detail}` : ""}</span>
        <small>{row.source}</small>
      </li>)}
    </ul>
  </main>;
}

interface AppProps {"""
assert anchor in text
text = text.replace(anchor, component, 1)

# --- activePage union ---
old = 'const [activePage, setActivePage] = useState<"documents" | "brainstorm" | "identity" | "roles" | "migration" | "tools" | "conventions">("documents");'
new = 'const [activePage, setActivePage] = useState<"documents" | "brainstorm" | "identity" | "roles" | "migration" | "tools" | "log" | "conventions">("documents");'
assert old in text
text = text.replace(old, new, 1)

# --- Nav button between Tools and Conventions ---
old = '          <button className={activePage === "conventions" ? "active" : ""} onClick={() => setActivePage("conventions")} type="button">Conventions</button>'
new = '          <button className={activePage === "log" ? "active" : ""} onClick={() => setActivePage("log")} type="button">Log</button>\n' + old
assert old in text
text = text.replace(old, new, 1)

# --- Render before conventions ---
old = '      {activePage === "conventions" && ('
new = '      {activePage === "log" && <ActivityLogPage campaignClient={campaignClient} />}\n' + old
assert text.count(old) == 1
text = text.replace(old, new, 1)

# --- Imports ---
old = 'import { ToastStack, toast } from "./toasts";'
new = 'import { LogEntry, ToastStack, toast } from "./toasts";'
assert old in text
text = text.replace(old, new, 1)

old = """  EntityIdentity,
  FactionRole,"""
new = """  EntityIdentity,
  FactionRole,
  IdentityDecisionEntry,"""
assert old in text
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("log page added")
