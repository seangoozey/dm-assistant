from pathlib import Path

p = Path("App.tsx")
t = p.read_text(encoding="utf-8")

# Types + client (interface, local, windmill) and bridge op come first.
old = '''export interface UnpromotedFinding {'''
new = '''export interface ExclusiveClaim { claim_id: string; assertion_text: string; state: string; owner_entity_id?: string | null; owner_name?: string | null; }
export interface EntityDocumentClaims { entity_id: string; canonical_name: string; entity_kind: string; document_id?: string | null; document_path?: string | null; claims: ExclusiveClaim[]; }
export interface ExclusiveClaimsResult { entities_with_exclusive_claims: number; total_claims: number; groups: EntityDocumentClaims[]; }
export interface UnpromotedFinding {'''
assert t.count(old) == 1
t = t.replace(old, new)

# Panel: the Assign Ownership lane.
old2 = '''  // The Q1 gather lane: entry-scoped material search for a zero-claims
  // record — claims mentioning its name, grouped by owner, movable home.
  const [gathering, setGathering] = useState<{ entityId: string; name: string } | null>(null);
  const [gathered, setGathered] = useState<GatheredClaim[] | null>(null);
  const [gatherLoading, setGatherLoading] = useState(false);
  const [movingId, setMovingId] = useState<string | null>(null);'''
new2 = '''  // The Q1 gather lane: entry-scoped material search for a zero-claims
  // record — claims mentioning its name, grouped by owner, movable home.
  const [gathering, setGathering] = useState<{ entityId: string; name: string } | null>(null);
  const [gathered, setGathered] = useState<GatheredClaim[] | null>(null);
  const [gatherLoading, setGatherLoading] = useState(false);
  const [movingId, setMovingId] = useState<string | null>(null);
  // Step 1 (2026-09-22 ruling): document-exclusive claims with checked
  // boxes and one Assign Ownership action per entity.
  const [docClaims, setDocClaims] = useState<ExclusiveClaimsResult | null>(null);
  const [docClaimsLoading, setDocClaimsLoading] = useState(false);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [assigningFor, setAssigningFor] = useState<string | null>(null);

  const gatherDocumentClaims = useCallback(async () => {
    setDocClaimsLoading(true);
    try {
      const result = await campaignClient.getExclusiveClaims();
      setDocClaims(result);
      const nextChecked: Record<string, boolean> = {};
      for (const group of result.groups) for (const claim of group.claims) nextChecked[claim.claim_id] = true;
      setChecked(nextChecked);
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "The document-claims gather could not run");
    } finally { setDocClaimsLoading(false); }
  }, [campaignClient]);

  const assignOwnership = useCallback(async (group: EntityDocumentClaims) => {
    if (assigningFor) return;
    const claimIds = group.claims.filter((claim) => checked[claim.claim_id]);
    if (claimIds.length === 0) return;
    setAssigningFor(group.entity_id);
    let moved = 0;
    const errors: string[] = [];
    for (const claim of claimIds) {
      try {
        await campaignClient.reattributeClaim(claim.claim_id, group.entity_id, `Assign Ownership: ${group.canonical_name}'s document claims`);
        moved += 1;
      } catch (cause) {
        errors.push(cause instanceof Error ? cause.message : String(cause));
      }
    }
    setAssigningFor(null);
    toast.push(moved > 0 ? "success" : "error",
      `Assigned ${moved} of ${claimIds.length} claim${claimIds.length === 1 ? "" : "s"} to ${group.canonical_name}${errors.length > 0 ? ` — ${errors.length} failed (see Log)` : ""}`);
    await gatherDocumentClaims();
    await run();
  }, [campaignClient, checked, assigningFor, gatherDocumentClaims, run]);'''
assert t.count(old2) == 1
t = t.replace(old2, new2)

# Render: Step 1 section above the criteria groups.
old3 = '''    {Object.entries(byCriterion).map(([criterion, group]) => <div className="source-review-queue" key={criterion}>'''
new3 = '''    <div className="qualified-step1" aria-label="Document-exclusive claims">
      <header><div><span>Step 1 — Assign Ownership</span><h4>Claims that live only on the record's document</h4></div>
        <button className="secondary-button" disabled={docClaimsLoading} onClick={() => void gatherDocumentClaims()} type="button">{docClaimsLoading ? "Gathering…" : docClaims ? "Re-gather" : "Gather document claims"}</button></header>
      <p className="roles-explainer">For every unqualified record: the claims evidenced only on the document that represents it — the migration's material whose ownership was never assigned. Checked boxes mean included; Assign Ownership re-attributes the checked claims to the record (receipted, provenance untouched).</p>
      {docClaims && <p className="identity-count">{docClaims.entities_with_exclusive_claims} record{docClaims.entities_with_exclusive_claims === 1 ? "" : "s"} · {docClaims.total_claims} exclusive claim{docClaims.total_claims === 1 ? "" : "s"}</p>}
      {docClaims?.groups.map((group) => <details className="qualified-step1-group" key={group.entity_id} open>
        <summary>{group.canonical_name} <small>{group.claims.length} claim{group.claims.length === 1 ? "" : "s"} · {group.document_path}</small></summary>
        {group.claims.map((claim) => <label className="gathered-claim" key={claim.claim_id}>
          <input aria-label={`Include claim for ${group.canonical_name}: ${claim.assertion_text.slice(0, 40)}`} checked={Boolean(checked[claim.claim_id])} onChange={(event) => setChecked((current) => ({ ...current, [claim.claim_id]: event.target.checked }))} type="checkbox" />
          <span>{claim.assertion_text}
            <small className="ai-activation-note"> · {claim.owner_name ? `currently owned by ${claim.owner_name}` : "no owner — initial attribution"} · {display(claim.state)}</small>
          </span>
        </label>)}
        <div className="lore-item-actions">
          <button className="decision-button" disabled={assigningFor !== null || !group.claims.some((claim) => checked[claim.claim_id])} onClick={() => void assignOwnership(group)} type="button">{assigningFor === group.entity_id ? "Assigning…" : `Assign Ownership (${group.claims.filter((claim) => checked[claim.claim_id]).length})`}</button>
        </div>
      </details>)}
    </div>
    {Object.entries(byCriterion).map(([criterion, group]) => <div className="source-review-queue" key={criterion}>'''
assert t.count(old3) == 1
t = t.replace(old3, new3)
p.write_text(t, encoding="utf-8")
print("step 1 built")
