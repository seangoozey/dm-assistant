from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.test.tsx")
text = p.read_text(encoding="utf-8")

anchor = '  it("records a misspelling from the target search results", async () => {'
tests = '''  it("auto-cancels a clean editor and forces save-or-discard on dirty edits when switching entries", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 9, source_count: 0,
    };
    const other = {
      entry_id: "b1000000-0000-0000-0000-0000000000f2", canonical_name: "White Cloaks",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 3, source_count: 0,
    };
    const profile = { entity_id: faction.entry_id, version: 1, canonical_name: "Inquisitors", status: "active", base_location: null, aliases: [], summary: "" };
    const getLibraryEntry = vi.fn().mockImplementation(async (entryId: string) => ({
      ...(entryId === faction.entry_id ? faction : other), claims: [], claim_history: [], sources: [],
    }));
    const getEntityProfile = vi.fn().mockImplementation(async (entryId: string) =>
      entryId === faction.entry_id ? profile : null);
    const updateEntityProfile = vi.fn().mockResolvedValue({ receipt_id: "b9000000-0000-0000-0000-0000000000fa", entity_id: faction.entry_id, version: 2, idempotent_replay: false });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction, other]),
      getLibraryEntry, getEntityProfile, updateEntityProfile,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));

    // Clean editor: switching entries auto-cancels — no error, editor gone.
    fireEvent.click(screen.getByRole("button", { name: "White Cloaks" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(other.entry_id));
    expect(screen.queryByRole("button", { name: "Save identity profile" })).not.toBeInTheDocument();
    expect(screen.queryByText("Identity profile could not be loaded.")).not.toBeInTheDocument();

    // Dirty editor: switching is blocked until the profile is saved or discarded.
    fireEvent.click(screen.getByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    fireEvent.change(screen.getByLabelText("Identity status"), { target: { value: "disbanded" } });
    fireEvent.click(screen.getByRole("button", { name: "White Cloaks" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unsaved identity profile changes");
    expect(screen.queryByRole("heading", { name: "White Cloaks" })).not.toBeInTheDocument();
    // Saving through the prompt commits, then the switch proceeds.
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(updateEntityProfile).toHaveBeenCalled());
    expect(await screen.findByText(/Saved with receipt b9000000/)).toBeInTheDocument();
  });

  it("requires a document filename to carry the entity's whole distinctive name", () => {
    const sources = [
      { document_id: "d1", path: "locations/heart-of-unity.md" },
    ];
    // Partial overlap (Council of Unity vs heart-of-unity) must not borrow.
    expect(selectEntrySource({ canonical_name: "Council of Unity", entity_kind: "faction" }, sources)).toBeUndefined();
    // The sibling entity whose full name the file carries still borrows it.
    expect(selectEntrySource({ canonical_name: "Heart of Unity", entity_kind: "location" }, sources)?.path).toBe("locations/heart-of-unity.md");
    // Exact filename matches always win, apostrophes and all.
    expect(selectEntrySource({ canonical_name: "Goodman's City", entity_kind: "location" }, [
      { document_id: "d2", path: "lore/goodmans-city.md" },
      { document_id: "d3", path: "locations/lore-doc.md" },
    ])?.path).toBe("lore/goodmans-city.md");
  });

  it("lists faction template fields on the entry hero", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: ["Inquisition"], misspellings: [], tags: [],
      members: [{ member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Eustice", role_title: "Grand Inquisitor", is_leadership: true }],
      current_claim_count: 9, source_count: 0,
    };
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Inquisitors",
      status: "active", base_location: "Goodman's City", aliases: [], summary: "",
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...faction, roles: [{ name: "Grand Inquisitor", is_leadership: true, holder_names: ["Eustice"] }], claims: [], claim_history: [], sources: [] }),
      getEntityProfile,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    expect(await screen.findByText("Aliases")).toBeInTheDocument();
    expect(screen.getByText("Inquisition")).toBeInTheDocument();
    expect(screen.getByText("Goodman's City")).toBeInTheDocument();
    expect(screen.getByText("Grand Inquisitor ★ — Eustice")).toBeInTheDocument();
  });

  it("defines and seats faction roles from the Roles page", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [{ member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Eustice", role_title: null, is_leadership: false }],
      current_claim_count: 9, source_count: 0,
    };
    const rolesAfterDefine = [{ faction_id: faction.entry_id, faction_name: "Inquisitors", name: "Grand Inquisitor", is_leadership: true, holders: [] as { id: string; name: string }[] }];
    const rolesAfterSeat = [{ faction_id: faction.entry_id, faction_name: "Inquisitors", name: "Grand Inquisitor", is_leadership: true, holders: [{ id: "b1000000-0000-0000-0000-0000000000m1", name: "Eustice" }] }];
    const listFactionRoles = vi.fn()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(rolesAfterDefine)
      .mockResolvedValue(rolesAfterSeat);
    const defineFactionRole = vi.fn().mockResolvedValue({ decision_id: "ba000000-0000-0000-0000-0000000000fb", kind: "membership", surface: "Grand Inquisitor of Inquisitors", idempotent_replay: false });
    const assignFactionRole = vi.fn().mockResolvedValue({ decision_id: "ba000000-0000-0000-0000-0000000000fc", kind: "membership", surface: "Eustice in Inquisitors", idempotent_replay: false });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      listFactionRoles, defineFactionRole, assignFactionRole,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Roles" }));
    expect(await screen.findByText("No roles defined yet. Define one above or seat a member from a faction's profile editor.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Role faction"), { target: { value: faction.entry_id } });
    fireEvent.change(screen.getByLabelText("New role definition name"), { target: { value: "Grand Inquisitor" } });
    fireEvent.click(screen.getByLabelText("Leadership ★ (unique seat)"));
    fireEvent.click(screen.getByRole("button", { name: "Define role" }));
    await waitFor(() => expect(defineFactionRole).toHaveBeenCalledWith(faction.entry_id, "Grand Inquisitor", true));
    expect(await screen.findByText(/Defined Grand Inquisitor ★ for Inquisitors/)).toBeInTheDocument();
    expect(screen.getByText("Vacant")).toBeInTheDocument();
    // Seat the member from the listing's dropdown.
    fireEvent.change(screen.getByLabelText("Seat a member as Grand Inquisitor"), { target: { value: "b1000000-0000-0000-0000-0000000000m1" } });
    await waitFor(() => expect(assignFactionRole).toHaveBeenCalledWith(faction.entry_id, "b1000000-0000-0000-0000-0000000000m1", "Grand Inquisitor", false));
    expect(await screen.findByText(/Seated Eustice as Grand Inquisitor ★/)).toBeInTheDocument();
    expect(screen.getByText("Vacate")).toBeInTheDocument();
    expect(screen.queryByText("Vacant")).not.toBeInTheDocument();
  });

'''
assert anchor in text
text = text.replace(anchor, tests + anchor, 1)
p.write_text(text, encoding="utf-8")
print("tests added")
