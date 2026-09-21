from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

anchor = "function ConflictReviewPanel"
component = '''function DescriptionComposer({ entry, claims, profile, onClose, onSaved }: {
  entry: LibraryEntrySummary; claims: SourceDocumentClaim[];
  profile: EntityProfile | null; onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<Set<string>>(() => new Set(claims.map((claim) => claim.claim_id)));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const campaignClient = useCampaignClient();

  const save = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const receipt = await campaignClient.writeEntityDescription(
        entry.entry_id, text.trim(), [...selected],
        `entity-description:${entry.entry_id}:${crypto.randomUUID()}`);
      setMessageIsError(false);
      setMessage(`Description filed as ${receipt.path} (receipt ${receipt.document_id.slice(0, 8)}) — the entry now has its page`);
      toast.push("success", `Description filed — ${entry.canonical_name} has its page`);
      await onSaved();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "The description could not be filed");
      toast.push("error", error instanceof Error ? error.message : "The description could not be filed");
    } finally { setBusy(false); }
  };

  const grouped = [
    { title: "Real-play facts", states: ["observed"] },
    { title: "Established information", states: ["established"] },
    { title: "Plans and preparation", states: ["intended", "prepared"] },
    { title: "Possibilities", states: ["possible"] },
  ];

  return <article className="document-view description-composer" aria-label="Description composer">
    <header><b>{display(entry.entity_kind)} description</b><span>Writing {entry.canonical_name}'s page</span></header>
    <section className="character-content">
      <p className="roles-explainer">Your prose becomes an evidence-class document filed as this entry's page (ADR-0015: authored canon-input). The gathered claims below are recorded as <Term term="claim">references</Term> — the description cites the record; it never duplicates it.</p>
      <label className="pc-background-field session-notes-field">Description<textarea aria-label="Entity description" placeholder={`Write ${entry.canonical_name}'s page — background, character, what matters at the table…`} rows={14} value={text} onChange={(event) => setText(event.target.value)} /></label>
      {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
      <details className="gathered-claims" open={claims.length > 0}><summary>Gathered claims ({selected.size} of {claims.length} referenced)</summary>
        <p className="roles-explainer">Selected claims are recorded as the description's references; supersession of a reference later flags the page stale.</p>
        {grouped.map((group) => {
          const items = claims.filter((claim) => group.states.includes(claim.state));
          return items.length > 0 && <section key={group.title}><h4>{group.title}</h4>
            {items.map((claim) => <label className="gathered-claim" key={claim.claim_id}>
              <input checked={selected.has(claim.claim_id)} onChange={(event) => setSelected((current) => {
                const next = new Set(current);
                event.target.checked ? next.add(claim.claim_id) : next.delete(claim.claim_id);
                return next;
              })} type="checkbox" />
              <span>{claim.assertion_text.slice(0, 160)}{claim.assertion_text.length > 160 ? "…" : ""}</span>
            </label>)}
          </section>;
        })}
        {claims.length === 0 && <p className="empty-section">No claims gathered — the description will be this entry's first canon input.</p>}
      </details>
      <div className="step-actions">
        <button className="text-button" disabled={busy} onClick={onClose} type="button">Cancel</button>
        <button className="decision-button" disabled={busy || !text.trim()} onClick={() => void save()} type="button">{busy ? "Filing…" : "File description"}</button>
      </div>
    </section>
  </article>;
}

function ConflictReviewPanel'''
assert anchor in text
text = text.replace(anchor, component, 1)
p.write_text(text, encoding="utf-8")
print("composer added")
