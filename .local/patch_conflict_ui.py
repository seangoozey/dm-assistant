from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

anchor = "function SessionDatingPanel"
component = '''function ConflictReviewPanel({ campaignClient }: { campaignClient: CampaignClient }) {
  const [conflicts, setConflicts] = useState<ConflictPair[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);

  const load = useCallback(async () => {
    try {
      setConflicts(await campaignClient.getConflictQueue());
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Conflict queue is unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { if (conflicts === null) void load(); }, [conflicts === null, load]);

  const decide = async (pair: ConflictPair, action: "dismiss" | "supersede") => {
    const reason = action === "dismiss"
      ? `Historical mention kept alongside ${pair.entity_name}'s observed death (${pair.claim_a_date})`
      : `Retired: contradicts the observed death of ${pair.entity_name} on ${pair.claim_a_date}`;
    setBusy(pair.claim_b_id);
    try {
      const result = await campaignClient.decideConflict(pair.claim_a_id, pair.claim_b_id, action, reason);
      setMessageIsError(false);
      setMessage(action === "dismiss"
        ? `Kept both — reviewed ${pair.entity_name} pair (receipt ${result.decision_id.slice(0, 8)})`
        : `Superseded the ${pair.claim_b_date} claim — death of ${pair.entity_name} stands (change set ${(result.change_set_id ?? "").slice(0, 8)})`);
      toast.push("success", action === "dismiss" ? `Conflict reviewed — kept both` : `Claim superseded — ${pair.entity_name}'s death stands`);
      await load();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "The decision failed");
      toast.push("error", error instanceof Error ? error.message : "The decision failed");
    } finally { setBusy(null); }
  };

  return <section className="page-panel conflict-review" aria-label="Conflict review">
    <div className="section-heading"><div><p className="kicker">Campaign maintenance</p><h2>Conflict review</h2></div>
      <p>Mechanical detection: an observed, dated death versus a current claim about the same record dated strictly later. Time keeps historical mentions out; every decision is receipted. <Term term="authority">Authority</Term> is shown on both sides — real play outranks lore.</p></div>
    {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    {conflicts === null ? <p className="queue-empty">Loading…</p> : <>
      <p className="identity-count">SHOWING {conflicts.length} CONFLICT{conflicts.length === 1 ? "" : "S"}</p>
      {conflicts.length === 0 && <p className="identity-empty">No detected conflicts right now. Observed deaths stand clean against dated claims.</p>}
      {conflicts.map((pair) => <article className="conflict-card" key={pair.claim_b_id} aria-label={`Conflict: ${pair.entity_name}`}>
        <h3>{pair.entity_name} <small>death observed {pair.claim_a_date}</small></h3>
        <div className="conflict-sides">
          <div className="conflict-side conflict-death">
            <span className="log-kind">Observed death</span>
            <p>{pair.claim_a_assertion.slice(0, 320)}{pair.claim_a_assertion.length > 320 ? "…" : ""}</p>
          </div>
          <div className="conflict-side conflict-later">
            <span className="log-kind">Later claim · {pair.claim_b_date} · {display(pair.claim_b_authority)}</span>
            <p>{pair.claim_b_assertion.slice(0, 320)}{pair.claim_b_assertion.length > 320 ? "…" : ""}</p>
          </div>
        </div>
        <p className="roles-explainer">If the later claim recounts pre-death events in past tense, keep both. If it asserts {pair.entity_name} operative after death, retire it.</p>
        <div className="conflict-actions">
          <button className="text-button" disabled={busy === pair.claim_b_id} onClick={() => void decide(pair, "dismiss")} type="button">Keep both — historical</button>
          <button className="decision-button" disabled={busy === pair.claim_b_id} onClick={() => void decide(pair, "supersede")} type="button">Retire later claim</button>
        </div>
      </article>)}
    </>}
  </section>;
}

function SessionDatingPanel'''
assert anchor in text
text = text.replace(anchor, component, 1)

old = 'import type { CampaignClockChange, CampaignDate, SessionDatingEntry, UndatedClaimEntry } from "./campaignClient";'
new = 'import type { CampaignClockChange, CampaignDate, ConflictPair, SessionDatingEntry, UndatedClaimEntry } from "./campaignClient";'
assert old in text
text = text.replace(old, new, 1)

old = '''      {activePage === "tools" && (
      <main>
        <SessionDatingPanel campaignClient={campaignClient} />'''
new = '''      {activePage === "tools" && (
      <main>
        <ConflictReviewPanel campaignClient={campaignClient} />
        <SessionDatingPanel campaignClient={campaignClient} />'''
assert old in text
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("conflict panel added")
