from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.test.tsx")
text = p.read_text(encoding="utf-8")

anchor = '  it("records a misspelling from the target search results", async () => {'
test = '''  it("links Identity Review role declarations to factions from the Roles page", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 0, source_count: 0,
    };
    const listFactionRoles = vi.fn()
      .mockResolvedValueOnce([])
      .mockResolvedValue([{ faction_id: faction.entry_id, faction_name: "Inquisitors", name: "Grand Inquisitor", is_leadership: true, holders: [] }]);
    const listRoleDeclarations = vi.fn()
      .mockResolvedValueOnce([
        { surface: "Grand Inquisitor", normalized_surface: "grand inquisitor" },
        { surface: "Inquisitor", normalized_surface: "inquisitor" },
      ])
      .mockResolvedValue([{ surface: "Inquisitor", normalized_surface: "inquisitor" }]);
    const defineFactionRole = vi.fn().mockResolvedValue({
      decision_id: "bb000000-0000-0000-0000-0000000000fd", kind: "membership",
      surface: "Grand Inquisitor of Inquisitors", idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      listFactionRoles, listRoleDeclarations, defineFactionRole,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Roles" }));
    expect(await screen.findByText("Declared during Identity Review — unlinked")).toBeInTheDocument();
    expect(screen.getByText("Grand Inquisitor")).toBeInTheDocument();
    expect(screen.getByText("Inquisitor")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Link Grand Inquisitor to faction"), { target: { value: faction.entry_id } });
    fireEvent.click(screen.getByLabelText("Leadership ★"));
    fireEvent.click(screen.getByRole("button", { name: "Link" }));
    await waitFor(() => expect(defineFactionRole).toHaveBeenCalledWith(faction.entry_id, "Grand Inquisitor", true));
    expect(await screen.findByText(/Linked Grand Inquisitor ★ to Inquisitors/)).toBeInTheDocument();
    // The linked seat now lives in the faction block; the sibling declaration stays unlinked.
    expect(screen.getByText("Vacant")).toBeInTheDocument();
    expect(screen.getByText("Declared during Identity Review — unlinked")).toBeInTheDocument();
    expect(screen.getByText("Inquisitor")).toBeInTheDocument();
  });

'''
assert anchor in text
text = text.replace(anchor, test + anchor, 1)
p.write_text(text, encoding="utf-8")
print("test added")
