export const ENCOUNTER_NOTES_STORAGE_KEY = "dm-assistant.encounter-table-notes.v1";

export interface EncounterNoteContext {
  contextKind?: "general" | "encounter";
  sourceDocumentId: string;
  sourcePath: string;
  encounterName: string;
  sectionKey: string;
  sectionTitle: string;
}

export interface EncounterTableNote extends EncounterNoteContext {
  noteId: string;
  text: string;
  capturedAt: string;
  updatedAt: string;
}

export function encounterSectionKey(sourcePath: string, index: number, title: string): string {
  const normalized = title.trim().toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `${sourcePath}#${index + 1}-${normalized || "section"}`;
}

export function chronologicalEncounterNotes(notes: EncounterTableNote[]): EncounterTableNote[] {
  return [...notes].sort((left, right) => left.capturedAt.localeCompare(right.capturedAt) || left.noteId.localeCompare(right.noteId));
}

export function assembleEncounterNotes(notes: EncounterTableNote[]): string {
  return chronologicalEncounterNotes(notes).map((note) => note.text.trim()).filter(Boolean).join("\n");
}

export function loadEncounterNotes(storage: Pick<Storage, "getItem"> | undefined = typeof window === "undefined" ? undefined : window.localStorage): EncounterTableNote[] {
  if (!storage) return [];
  try {
    const value = JSON.parse(storage.getItem(ENCOUNTER_NOTES_STORAGE_KEY) ?? "[]");
    if (!Array.isArray(value)) return [];
    return chronologicalEncounterNotes(value.filter((note): note is EncounterTableNote => Boolean(
      note && typeof note.noteId === "string" && typeof note.text === "string" && typeof note.capturedAt === "string"
      && typeof note.sourceDocumentId === "string" && typeof note.sectionKey === "string",
    )));
  } catch {
    return [];
  }
}

export function generalSessionNoteContext(): EncounterNoteContext {
  return {
    contextKind: "general",
    sourceDocumentId: "",
    sourcePath: "",
    encounterName: "Session",
    sectionKey: "session-general",
    sectionTitle: "General note",
  };
}

export function saveEncounterNotes(notes: EncounterTableNote[], storage: Pick<Storage, "setItem"> | undefined = typeof window === "undefined" ? undefined : window.localStorage): void {
  if (!storage) return;
  storage.setItem(ENCOUNTER_NOTES_STORAGE_KEY, JSON.stringify(chronologicalEncounterNotes(notes)));
}
