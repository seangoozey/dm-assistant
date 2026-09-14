from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

anchor = "interface AppProps {"
component = """function FactionRolesPage({ campaignClient, factions, onRefreshLibrary, onOpenFaction }: { campaignClient: CampaignClient; factions: LibraryEntrySummary[]; onRefreshLibrary: () => void; onOpenFaction: (entryId: string) => void }) {
  const [roles, setRoles] = useState<FactionRoleSummary[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [defineFaction, setDefineFaction] = useState("");
  const [defineName, setDefineName] = useState("");
  const [defineLeadership, setDefineLeadership] = useState(false);

  const loadRoles = useCallback(async () => {
    setLoading(true);
    try {
      setRoles(await campaignClient.listFactionRoles());
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Roles could not be loaded");
    } finally { setLoading(false); }
  }, [campaignClient]);

  useEffect(() => { if (roles === null && !loading) void loadRoles(); }, [roles === null, loading, loadRoles]);

  const decide = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    try {
      await action();
      setMessageIsError(false);
      setMessage(done);
      await loadRoles();
      onRefreshLibrary();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error && error.message ? error.message : "Role decision failed");
    } finally { setBusy(false); }
  };

  const rosterOf = (factionId: string) => factions.find((entry) => entry.entry_id === factionId)?.members ?? [];
  const grouped = new Map<string, { faction: LibraryEntrySummary | undefined; roles: FactionRoleSummary[] }>();
  for (const role of roles ?? []) {
    const block = grouped.get(role.faction_id) ?? { faction: factions.find((entry) => entry.entry_id === role.faction_id), roles: [] };
    block.roles.push(role);
    grouped.set(role.faction_id, block);
  }

  return <main className="page-roles">
    <section className="identity-page-header" aria-label="Faction roles">
      <div className="section-heading"><div><p className="kicker">Identity maintenance</p><h2>Faction Roles</h2></div><p>Every role definition across factions, who holds it, and where the vacant seats are. Roles are faction-scoped titles — unique leadership seats carry the ★.</p></div>
      <div className="identity-toolbar"><button className="secondary-button" disabled={loading || busy} onClick={() => void loadRoles()} type="button">{loading ? "Working…" : "Refresh"}</button></div>
      {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    </section>

    <section className="page-panel" aria-label="Define a role">
      <h3>Define a role</h3>
      <div className="form-grid">
        <label>Faction<select aria-label="Role faction" value={defineFaction} onChange={(event) => setDefineFaction(event.target.value)}>
          <option value="">Choose a faction…</option>
          {factions.map((faction) => <option key={faction.entry_id} value={faction.entry_id}>{faction.canonical_name}</option>)}
        </select></label>
        <label>Role name<input aria-label="New role definition name" placeholder="Grand Inquisitor" value={defineName} onChange={(event) => setDefineName(event.target.value)} /></label>
        <label className="member-role-leadership"><input checked={defineLeadership} onChange={(event) => setDefineLeadership(event.target.checked)} type="checkbox" />Leadership ★ (unique seat)</label>
      </div>
      <div className="step-actions">
        <button className="decision-button" disabled={busy || !defineFaction || !defineName.trim()} onClick={() => { const factionName = factions.find((entry) => entry.entry_id === defineFaction)?.canonical_name ?? "the faction"; void decide(() => campaignClient.defineFactionRole(defineFaction, defineName.trim(), defineLeadership), `Defined ${defineName.trim()}${defineLeadership ? " ★" : ""} for ${factionName}`).then(() => { setDefineName(""); setDefineLeadership(false); }); }} type="button">Define role</button>
      </div>
    </section>

    {roles !== null && roles.length === 0 && <p className="identity-empty">No roles defined yet. Define one above or seat a member from a faction's profile editor.</p>}
    {[...grouped.entries()].map(([factionId, block]) => <section className="page-panel roles-faction-block" key={factionId} aria-label={`Roles of ${block.faction?.canonical_name ?? factionId}`}>
      <h3>{block.faction ? <button className="text-button" onClick={() => onOpenFaction(factionId)} type="button">{block.faction.canonical_name}</button> : factionId}</h3>
      <ul>{block.roles.map((role) => <li key={role.name} className="role-row">
        <span className={role.is_leadership ? "role-chip leadership" : "role-chip"}>{role.name}{role.is_leadership ? " ★" : ""}</span>
        <span className="role-holders">{role.holders.length > 0 ? role.holders.map((holder) => <span key={holder.id} className="role-holder">{holder.name} <button className="text-button" disabled={busy} onClick={() => void decide(() => campaignClient.assignFactionRole(factionId, holder.id, null, false), `Vacated ${role.name} (${holder.name})`)} type="button">Vacate</button></span>) : <span className="role-vacant">Vacant</span>}</span>
        <span className="member-role-control">
          <select aria-label={`Seat a member as ${role.name}`} disabled={busy} value="" onChange={(event) => { const member = rosterOf(factionId).find((row) => row.member_id === event.target.value); if (member) void decide(() => campaignClient.assignFactionRole(factionId, member.member_id, role.name, false), `Seated ${member.name} as ${role.name}${role.is_leadership ? " ★" : ""}`); event.currentTarget.value = ""; }}>
            <option value="">Seat a member…</option>
            {rosterOf(factionId).filter((row) => !role.holders.some((holder) => holder.id === row.member_id)).map((row) => <option key={row.member_id} value={row.member_id}>{row.name}</option>)}
          </select>
        </span>
      </li>)}</ul>
    </section>)}
  </main>;
}

interface AppProps {"""
assert anchor in text, "anchor"
text = text.replace(anchor, component, 1)

old = 'const [activePage, setActivePage] = useState<"documents" | "brainstorm" | "identity" | "migration" | "tools" | "conventions">("documents");'
new = 'const [activePage, setActivePage] = useState<"documents" | "brainstorm" | "identity" | "roles" | "migration" | "tools" | "conventions">("documents");'
assert old in text, "activePage"
text = text.replace(old, new, 1)

old = '          <button className={activePage === "identity" ? "active" : ""} onClick={() => setActivePage("identity")} type="button">Identity</button>\n'
new = old + '          <button className={activePage === "roles" ? "active" : ""} onClick={() => setActivePage("roles")} type="button">Roles</button>\n'
assert old in text, "nav"
text = text.replace(old, new, 1)

old = """  EntityIdentity,
  FactionRole,
  LibraryEntrySummary,
  LibraryMember,"""
new = """  EntityIdentity,
  FactionRole,
  FactionRoleSummary,
  LibraryEntrySummary,
  LibraryMember,"""
assert old in text, "imports"
text = text.replace(old, new, 1)

old = '      {activePage === "migration" && ('
new = """      {activePage === "roles" && <FactionRolesPage campaignClient={campaignClient} factions={libraryEntries.filter((entry) => entry.entity_kind === "faction")} onRefreshLibrary={() => campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {})} onOpenFaction={(entryId) => { setActivePage("documents"); leaveEditorGuard(libraryEntries.find((entry) => entry.entry_id === entryId)?.canonical_name ?? "the faction", () => { setSelectedEntryId(entryId); void loadCanonicalEntry(entryId); }); }} />}
      {activePage === "migration" && ("""
assert text.count(old) == 1, "render"
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("roles page done")
