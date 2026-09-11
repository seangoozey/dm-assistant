import type { LibraryEntrySummary } from "./campaignClient";

// Presentation only: never change the citation used for provenance.
export function evidenceTitle(citation: string, entries: Pick<LibraryEntrySummary, "canonical_name" | "aliases">[]): string {
  const [path, ...sections] = citation.split("#");
  const stem = path.replace(/\\/g, "/").split("/").pop()?.replace(/\.md$/i, "") ?? "Source";
  const key = (value: string) => value.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
  const match = entries.find((entry) => [entry.canonical_name, ...entry.aliases].some((name) => key(name) === key(stem)));
  const name = match?.canonical_name ?? stem.replace(/[-_]+/g, " ").replace(/([a-z])(\d)/gi, "$1 $2").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const section = sections.join("#").replace(/\s*\(Canonical\)/gi, "").replace(/\s+—\s+Layout$/i, "").trim();
  return section && key(section) !== key(name) ? `${name}: ${section}` : name;
}
