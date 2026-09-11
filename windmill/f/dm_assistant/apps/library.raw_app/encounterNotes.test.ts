import { describe, expect, it } from "vitest";

import { assembleEncounterNotes, chronologicalEncounterNotes, encounterSectionKey, loadEncounterNotes, saveEncounterNotes, type EncounterTableNote } from "./encounterNotes";

function note(noteId: string, capturedAt: string, text: string): EncounterTableNote {
  return { noteId, capturedAt, updatedAt: capturedAt, text, sourceDocumentId: "doc-1", sourcePath: "encounters/exile.md", encounterName: "Exile Camp Meeting", sectionKey: `section-${noteId}`, sectionTitle: noteId };
}

describe("encounter table notes", () => {
  it("orders assembled session text by capture time rather than section order", () => {
    const notes = [note("common-fire", "2026-08-26T20:10:00Z", "They visited the common fire."), note("meeting", "2026-08-26T20:05:00Z", "They began the meeting early.")];
    expect(assembleEncounterNotes(notes)).toBe("They began the meeting early.\nThey visited the common fire.");
    expect(chronologicalEncounterNotes(notes).map((item) => item.noteId)).toEqual(["meeting", "common-fire"]);
  });

  it("retains hidden encounter context through browser-local storage", () => {
    let stored = "";
    const storage = { getItem: () => stored, setItem: (_key: string, value: string) => { stored = value; } };
    const notes = [note("common-fire", "2026-08-26T20:10:00Z", "The party spoke with the exiles.")];
    saveEncounterNotes(notes, storage);
    expect(loadEncounterNotes(storage)[0]).toMatchObject({ sectionTitle: "common-fire", text: "The party spoke with the exiles." });
  });

  it("builds deterministic section identities from source position and title", () => {
    expect(encounterSectionKey("encounters/exile.md", 4, "The Common Fire (Goodman Section)")).toBe("encounters/exile.md#5-the-common-fire-goodman-section");
  });
});

