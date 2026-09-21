from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

# Life-status review panel: proposals + dead seats, inserted above the conflict panel.
anchor = "function ConflictReviewPanel"
component = '''function LifeStatusPanel({ campaignClient }: { campaignClient: CampaignClient }) {
  const [proposals, setProposals] = useState<LifeStatusProposal[] | null>(null);
  const [deadSeats, setDeadSeats] = useState<DeadSeat[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);

  const load = useCallback(async () => {
    try {
      const [items, seats] = await Promise.all([
        campaignClient.getLifeStatusProposals(),
        campaignClient.getDeadSeats().catch(() => [] as DeadSeat[]),
      ]);
      setProposals(items);
      setDeadSeats(seats);
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Life status is unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { if (proposals === null) void load(); }, [proposals === null, load]);

  const confirm = async (proposal: LifeStatusProposal) => {
    const [year, month, day] = proposal.death_date.split("-").map(Number);
    setBusy(proposal.entity_id);
    try {
      await campaignClient.setLifeStatus(
        proposal.entity_id, "dead", { year, month, day },
        proposal.death_claim_id, `life-status:${proposal.entity_id}`);
      setMessageIsError(false);
      setMessage(`Marked ${proposal.entity_name} dead as of ${proposal.death_date} — receipted against the observed claim`);
      toast.push("success", `${proposal.entity_name} marked dead (${proposal.death_date})`);
      await load();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "The status could not be set");
      toast.push("error", error instanceof Error ? error.message : "The status could not be set");
    } finally { setBusy(null); }
  };

  return <section className="page-panel life-status-panel" aria-label="Life status">
    <div className="section-heading"><div><p className="kicker">Campaign maintenance</p><h2>Life status</h2></div>
      <p>An enumerated canon dimension — alive, dead, undead, resurrected — set through audited decisions anchored to the claim that established it. Detectors read the enum; prose never decides.</p></div>
    {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    {proposals === null ? <p className="queue-empty">Loading…</p> : <>
      <p className="identity-count">SHOWING {proposals.length} DEATH PROPOSAL{proposals.length === 1 ? "" : "S"}{deadSeats.length > 0 ? ` · ${deadSeats.length} SEAT${deadSeats.length === 1 ? "" : "S"} HELD BY THE DEAD` : ""}</p>
      {proposals.length === 0 && deadSeats.length === 0 && <p className="identity-empty">No pending status proposals and no seats held by the dead.</p>}
      {proposals.map((proposal) => <article className="conflict-card" key={proposal.entity_id} aria-label={`Death proposal: ${proposal.entity_name}`}>
        <h3>{proposal.entity_name} <small>observed death {proposal.death_date}</small></h3>
        <div className="conflict-sides"><div className="conflict-side conflict-death">
          <span className="log-kind">Backing claim</span>
          <p>{proposal.death_assertion.slice(0, 300)}{proposal.death_assertion.length > 300 ? "…" : ""}</p>
        </div></div>
        <div className="conflict-actions">
          <button className="decision-button" disabled={busy === proposal.entity_id} onClick={() => void confirm(proposal)} type="button">Mark dead</button>
        </div>
      </article>)}
      {deadSeats.length > 0 && <details className="residue-queue" open><summary>Seats held by the dead ({deadSeats.length})</summary>
        <ul>{deadSeats.map((seat) => <li key={`${seat.faction_id}-${seat.member_id}`} className="residue-relevant">
          <span className="log-message">{seat.member_name} — {seat.role_title ?? "member"}{seat.is_leadership ? " ★" : ""} of {seat.faction_name}</span>
          <small> · dead since {seat.life_status_since}</small>
        </li>)}</ul>
      </details>}
    </>}
  </section>;
}

function ConflictReviewPanel'''
assert anchor in text
text = text.replace(anchor, component, 1)

# Import types
old = 'import type { CampaignClockChange, CampaignDate, ConflictPair, SessionDatingEntry, UndatedClaimEntry } from "./campaignClient";'
new = 'import type { CampaignClockChange, CampaignDate, ConflictPair, DeadSeat, LifeStatusProposal, SessionDatingEntry, UndatedClaimEntry } from "./campaignClient";'
assert old in text
text = text.replace(old, new, 1)

# Render above the conflict panel on Tools
old = '''      {activePage === "tools" && (
      <main>
        <ConflictReviewPanel campaignClient={campaignClient} />'''
new = '''      {activePage === "tools" && (
      <main>
        <LifeStatusPanel campaignClient={campaignClient} />
        <ConflictReviewPanel campaignClient={campaignClient} />'''
assert old in text
text = text.replace(old, new, 1)

# Hero display: Life status row for characters (from entity profile).
old = '''{entityTemplate?.roles && entityTemplate.roles.length > 0 && <div><dt><Term term="role">Roles</Term></dt>'''
new = '''{entityTemplate?.life_status && <div><dt><Term term="life-status">Life status</Term></dt><dd>{display(entityTemplate.life_status)}{entityTemplate.life_status_since ? ` (since ${entityTemplate.life_status_since.year}-${String(entityTemplate.life_status_since.month).padStart(2, "0")}-${String(entityTemplate.life_status_since.day).padStart(2, "0")})` : ""}</dd></div>}{entityTemplate?.roles && entityTemplate.roles.length > 0 && <div><dt><Term term="role">Roles</Term></dt>'''
assert old in text
text = text.replace(old, new, 1)

# entityTemplate type gains life_status passthrough
old = "entityTemplate?: { aliases: string[]; base_location?: string | null; location_type?: string | null; parent_location?: string | null; roles?: FactionRole[] }"
new = "entityTemplate?: { aliases: string[]; base_location?: string | null; location_type?: string | null; parent_location?: string | null; roles?: FactionRole[]; life_status?: EntityProfile[\"life_status\"]; life_status_since?: EntityProfile[\"life_status_since\"] }"
assert old in text
text = text.replace(old, new, 1)

# Call site passes life status through for character kinds
old = 'roles: selectedEntry.entity_kind === "faction" ? (selectedEntry.roles ?? []) : undefined } : undefined} />'
new = 'roles: selectedEntry.entity_kind === "faction" ? (selectedEntry.roles ?? []) : undefined, life_status: (selectedEntry.entity_kind === "pc" || selectedEntry.entity_kind === "npc") ? (entityProfile?.life_status ?? null) : undefined, life_status_since: (selectedEntry.entity_kind === "pc" || selectedEntry.entity_kind === "npc") ? (entityProfile?.life_status_since ?? null) : undefined } : undefined} />'
assert old in text
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("life status UI wired")
