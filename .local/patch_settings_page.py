from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

anchor = "function ActivityLogPage"
component = '''function SettingsPage({ settings, onChange }: { settings: import("./settings").Settings; onChange: (changes: import("./settings").PartialSettings) => void }) {
  const HIDEABLE = [
    { label: "Migration", note: "The import review workspace" },
    { label: "Conventions", note: "The UI reference page" },
  ];
  return <main className="page-settings">
    <section className="identity-page-header" aria-label="Settings">
      <div className="section-heading"><div><p className="kicker">Preferences</p><h2>Settings</h2></div>
        <p>DM preferences for how this app behaves. Everything here is stored in your browser and applies immediately — nothing touches campaign truth.</p></div>
    </section>

    <section className="page-panel settings-panel" aria-label="Notifications">
      <h3>Notifications</h3>
      <label className="setting-row"><input checked={settings.toastsEnabled} onChange={(event) => onChange({ toastsEnabled: event.target.checked })} type="checkbox" />
        <span><b>Show toasts</b><small>Transient confirmations in the top-right. Every outcome is still recorded in the Log regardless.</small></span></label>
      <label className="setting-row">Toast duration<input aria-label="Toast duration seconds" max={20} min={2} type="number" value={Math.round(settings.toastDurationMs / 1000)}
        onChange={(event) => { const seconds = Number(event.target.value); if (seconds >= 2 && seconds <= 20) onChange({ toastDurationMs: seconds * 1000 }); }} />
        <small>Seconds before each toast dismisses itself (2–20).</small></label>
    </section>

    <section className="page-panel settings-panel" aria-label="Activity log">
      <h3>Activity log</h3>
      <label className="setting-row"><input checked={settings.logErrorsOnly} onChange={(event) => onChange({ logErrorsOnly: event.target.checked })} type="checkbox" />
        <span><b>Errors only</b><small>The Log page shows just failures and refusals; receipts stay available per surface.</small></span></label>
    </section>

    <section className="page-panel settings-panel" aria-label="Navigation">
      <h3>Navigation</h3>
      <p className="roles-explainer">Hide pages you rarely open from the top bar. Hidden pages stay fully reachable — clear the checkbox to bring a page back.</p>
      {HIDEABLE.map((page) => <label className="setting-row" key={page.label}><input checked={!settings.hiddenNavPages.includes(page.label)}
        onChange={(event) => {
          const hidden = event.target.checked
            ? settings.hiddenNavPages.filter((item) => item !== page.label)
            : [...settings.hiddenNavPages, page.label];
          onChange({ hiddenNavPages: hidden });
        }} type="checkbox" />
        <span><b>Show {page.label}</b><small>{page.note}</small></span></label>)}
    </section>
  </main>;
}

function ActivityLogPage'''
assert anchor in text
text = text.replace(anchor, component, 1)

# Log page: errors-only filter.
old = "  const visible = filter === \"errors\" ? rows.filter((row) => row.kind === \"error\") : rows;"
assert old in text
new = """  const settings = getSettings();
  const visible = (filter === "errors" || settings.logErrorsOnly)
    ? rows.filter((row) => row.kind === "error") : rows;"""
text = text.replace(old, new, 1)

old = 'import { useSettings } from "./settings";'
new = 'import { getSettings, useSettings } from "./settings";'
assert old in text
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("settings page + log filter added")
