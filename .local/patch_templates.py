from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

# 1. RecordIcon gains the records kind.
old = '''function RecordIcon({ kind }: { kind: "edit" | "source" | "hide" | "show" | "note" | "unpaged" }) {
  if (kind === "unpaged")'''
new = '''function RecordIcon({ kind }: { kind: "edit" | "source" | "hide" | "show" | "note" | "unpaged" | "records" }) {
  if (kind === "records") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h13" /><path d="M17 15l3 3-3 3" /></svg>;
  if (kind === "unpaged")'''
assert old in text, "icon"
text = text.replace(old, new, 1)

# 2. StructuredEntryView: claims out of the default body; Records affordance + drawer.
old = '''    {entry.intro && <section className="entry-summary"><EntryText text={entry.intro} /></section>}
    <div className="entry-sections">{entry.sections.filter((section) => section.title.toLocaleLowerCase() !== "sources" && section.title.toLocaleLowerCase() !== "references").map((section, index) => <section className={`entry-section level-${section.level}`} key={`${section.title}-${index}`}><h2>{section.title}</h2><EntryText text={section.content} /></section>)}</div>
    <CanonicalClaimSections claims={claims} history={history} onEditClaim={onEditClaim} />
    <EntrySourceDrawer fallbackPath={path} sources={sources} />'''
new = '''    {entry.intro && <section className="entry-summary"><EntryText text={entry.intro} /></section>}
    <div className="entry-sections">{entry.sections.filter((section) => section.title.toLocaleLowerCase() !== "sources" && section.title.toLocaleLowerCase() !== "references").map((section, index) => <section className={`entry-section level-${section.level}`} key={`${section.title}-${index}`}><h2>{section.title}</h2><EntryText text={section.content} /></section>)}</div>
    <details className="records-hood" aria-label="Records (under the hood)"><summary><RecordIcon kind="records" /> Records — claims, provenance, history</summary>
      <CanonicalClaimSections claims={claims} history={history} onEditClaim={onEditClaim} />
      <EntrySourceDrawer fallbackPath={path} sources={sources} />
    </details>'''
assert old in text, "structured claims"
text = text.replace(old, new, 1)

# 3. CharacterDocumentView: dmClaims + claim history move under the hood the same way.
old_count = text.count("<CanonicalClaimSections claims={history=")
# The character view renders claim sections via a different call; find it.
import re
matches = [m.start() for m in re.finditer(r"<CanonicalClaimSections", text)]
print("CanonicalClaimSections sites:", len(matches))
p.write_text(text, encoding="utf-8")
print("phase 1 done")
