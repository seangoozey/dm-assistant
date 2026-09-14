from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.test.tsx")
text = p.read_text(encoding="utf-8")

# Roster-refresh test: removal now uses the row's member_id directly, and the
# refresh must not flash a loading state over the open editor.
old = '''    const searchEntities = vi.fn().mockResolvedValue([
      { entity_id: "9b000000-0000-0000-0000-000000000002", canonical_name: "Coreferra", entity_kind: "npc", match_kind: "canonical" },
    ]);
    const removeMembership = vi.fn().mockResolvedValue({
      decision_id: "b7000000-0000-0000-0000-0000000000f7", kind: "membership",
      surface: "Carpet Rollers", idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, searchEntities, removeMembership,
    )} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Carpet Rollers" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    expect(screen.getAllByTitle("Remove membership")).toHaveLength(2);
    fireEvent.click(screen.getAllByTitle("Remove membership")[1]);
    await waitFor(() => expect(removeMembership).toHaveBeenCalledWith(
      faction.entry_id, "9b000000-0000-0000-0000-000000000002"));
    // The roster reloads from the library entry and the editor stays open.
    expect(getLibraryEntry).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.getAllByTitle("Remove membership")).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Save identity profile" })).toBeInTheDocument();
  });'''
new = '''    const removeMembership = vi.fn().mockResolvedValue({
      decision_id: "b7000000-0000-0000-0000-0000000000f7", kind: "membership",
      surface: "Carpet Rollers", idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, removeMembership,
    )} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Carpet Rollers" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    expect(screen.getAllByTitle("Remove membership")).toHaveLength(2);
    fireEvent.click(screen.getAllByTitle("Remove membership")[1]);
    await waitFor(() => expect(removeMembership).toHaveBeenCalledWith(
      faction.entry_id, "b1000000-0000-0000-0000-0000000000m2"));
    // The roster reloads in place: no loading flash, editor stays open.
    expect(screen.queryByText("Loading document…")).not.toBeInTheDocument();
    expect(getLibraryEntry).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.getAllByTitle("Remove membership")).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Save identity profile" })).toBeInTheDocument();
    expect(screen.getByText(/Removed Coreferra from Carpet Rollers/)).toBeInTheDocument();
  });

  it("surfaces membership refusals in the editor instead of silently failing", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Carpet Rollers",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [{ member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Ruhrogue", role_title: null, is_leadership: false }],
      current_claim_count: 9, source_count: 0,
    };
    const addMembership = vi.fn().mockRejectedValue(new Error("Ruhrogue is already a member of Carpet Rollers; remove first to change"));
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...faction, claims: [], claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Carpet Rollers",
      status: "active", base_location: null, aliases: [], summary: "",
    });
    const searchEntities = vi.fn().mockResolvedValue([
      { entity_id: "b1000000-0000-0000-0000-0000000000m1", canonical_name: "Ruhrogue", entity_kind: "pc", match_kind: "canonical" },
    ]);
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, addMembership, searchEntities,
    )} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Carpet Rollers" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    fireEvent.change(screen.getByLabelText("Search identities to add as member"), { target: { value: "Ruhrog" } });
    fireEvent.click(await screen.findByRole("option", { name: /Ruhrogue/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already a member");
    // The roster did not reload behind the refusal.
    expect(getLibraryEntry).toHaveBeenCalledTimes(1);
  });

  it("shows location template fields from the entity profile over document frontmatter", async () => {
    const location = {
      entry_id: "b1000000-0000-0000-0000-0000000000l1", canonical_name: "Faeroth Manor",
      entity_kind: "location" as const, aliases: ["The Manor"], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 0,
    };
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...location, claims: [], claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: location.entry_id, version: 1, canonical_name: "Faeroth Manor",
      status: "active", location_type: "estate", parent_location: "Unity", aliases: [], summary: "",
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([location]),
      getLibraryEntry, getEntityProfile,
    )} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Faeroth Manor" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(location.entry_id));
    expect(await screen.findByText("Aliases")).toBeInTheDocument();
    expect(screen.getByText("The Manor")).toBeInTheDocument();
    expect(screen.getByText("estate")).toBeInTheDocument();
    expect(screen.getByText("Unity")).toBeInTheDocument();
  });'''
assert old in text, "roster test"
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("tests updated")
