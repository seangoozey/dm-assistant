from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

# 1. Hoist a shared document-open handler and a page-having computation.
old = """  const sourceBackedLibraryDocuments = useMemo(() => {"""
new = """  const openSourceDocument = useCallback((document: SourceDocument) => {
    leaveEditorGuard(`the ${document.title ?? document.path} document`, () => {
      setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null);
      setSelectedDocumentId(document.document_id);
      void loadDocumentContent(document.document_id, document.path);
    });
  }, [leaveEditorGuard]);

  // An entry "has a page" when a document represents it under the same rules
  // the page matcher uses. Page-less entries are the uncompleted ones — the
  // sources are the thing; entity records without documents still owe a page.
  const unpagedEntryIds = useMemo(() => {
    const documentStubs = sourceDocuments.map((doc) => ({ document_id: doc.document_id, path: doc.path }));
    const entityNames = libraryEntries.map((entry) => entry.canonical_name);
    return new Set(libraryEntries
      .filter((entry) => !selectEntrySource(entry, documentStubs, entityNames))
      .map((entry) => entry.entry_id));
  }, [libraryEntries, sourceDocuments]);

  const sourceBackedLibraryDocuments = useMemo(() => {"""
assert old in text, "hoist"
text = text.replace(old, new, 1)

# 2. Unified kind groups: page-less marker everywhere; lore documents join the
# Worldbuilding group as one list.
old = """              {libraryMode === "entries" && libraryEntries.length > 0 && Array.from(new Set(libraryEntries.map((entry) => entry.entity_kind))).map((kind) => <details className="canonical-entry-group" key={kind}><summary>{entryKindLabel(kind)}</summary><div>{libraryEntries.filter((entry) => entry.entity_kind === kind).map((entry) => <button className={`tree-doc canonical-entry-link ${selectedEntryId === entry.entry_id ? "selected" : ""}`} key={entry.entry_id} onClick={() => leaveEditorGuard(entry.canonical_name, () => { setSelectedEntryId(entry.entry_id); void loadCanonicalEntry(entry.entry_id); })} type="button"><span className="tree-doc-name">{entry.canonical_name}</span></button>)}</div></details>)}"""
new = """              {libraryMode === "entries" && libraryEntries.length > 0 && Array.from(new Set(libraryEntries.map((entry) => entry.entity_kind))).map((kind) => {
                const loreDocuments = kind === "worldbuilding"
                  ? sourceBackedLibraryDocuments.filter((document) => pathEntryType(document.path) === "Worldbuilding")
                  : [];
                const entryRows = libraryEntries.filter((entry) => entry.entity_kind === kind).map((entry) => (
                  { key: `entry-${entry.entry_id}`, label: entry.canonical_name, selected: selectedEntryId === entry.entry_id, node: <button className={`tree-doc canonical-entry-link ${selectedEntryId === entry.entry_id ? "selected" : ""}`} key={entry.entry_id} onClick={() => leaveEditorGuard(entry.canonical_name, () => { setSelectedEntryId(entry.entry_id); void loadCanonicalEntry(entry.entry_id); })} type="button"><span className="tree-doc-name">{entry.canonical_name}</span>{unpagedEntryIds.has(entry.entry_id) && <span className="tree-doc-flag" title="No document backs this entry yet — its page is synthesized from claims. Write a description to give it one.">no page</span>}</button> }));
                const documentRows = loreDocuments.map((document) => (
                  { key: `doc-${document.document_id}`, label: sourceDocumentLabel(document), selected: selectedDocumentId === document.document_id, node: <div className="source-entry-row" key={document.document_id}><button className={`tree-doc canonical-entry-link ${selectedDocumentId === document.document_id ? "selected" : ""}`} onClick={() => openSourceDocument(document)} type="button"><span className="tree-doc-name">{sourceDocumentLabel(document)}</span></button></div> }));
                return <details className="canonical-entry-group" key={kind}><summary>{entryKindLabel(kind)}</summary><div>{[...entryRows, ...documentRows].sort((left, right) => left.label.toLocaleLowerCase().localeCompare(right.label.toLocaleLowerCase())).map((row) => row.node)}</div></details>;
              })}"""
assert old in text, "groups"
text = text.replace(old, new, 1)

# 3. The lore family no longer renders separately — it lives in the group above.
old = """              {libraryMode === "entries" && sourceBackedLibraryDocuments.length > 0 && Array.from(new Set(sourceBackedLibraryDocuments.map((document) => pathEntryType(document.path)))).map((family) => <SourceBackedFamily documents={sourceBackedLibraryDocuments.filter((document) => pathEntryType(document.path) === family)} family={family} key={family} onEditSession={(document) => void editSourceSessionDocument(document)} onSelect={(document) => leaveEditorGuard(`the ${document.title ?? document.path} document`, () => { setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null); setSelectedDocumentId(document.document_id); void loadDocumentContent(document.document_id, document.path); })} selectedDocumentId={selectedDocumentId} />)}"""
new = """              {libraryMode === "entries" && sourceBackedLibraryDocuments.length > 0 && Array.from(new Set(sourceBackedLibraryDocuments.map((document) => pathEntryType(document.path)))).filter((family) => family !== "Worldbuilding").map((family) => <SourceBackedFamily documents={sourceBackedLibraryDocuments.filter((document) => pathEntryType(document.path) === family)} family={family} key={family} onEditSession={(document) => void editSourceSessionDocument(document)} onSelect={openSourceDocument} selectedDocumentId={selectedDocumentId} />)}"""
assert old in text, "families"
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("unified worldbuilding patched")
