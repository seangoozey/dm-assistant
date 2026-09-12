import { FormEvent, KeyboardEvent as ReactKeyboardEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { evidenceTitle } from "./evidenceTitle";

import type {
  CampaignClient,
  BrainstormSession,
  AIConfigurationSnapshot,
  CandidateExtraction,
  CandidateProposalApproval,
  CandidateFilters,
  CandidateProposalVersion,
  CreateProposalItem,
  CreateClaimProposalItem,
  EntityKind,
  EntityKindGuidance,
  EntityIdentity,
  LibraryEntrySummary,
  LibraryEntry,
  LibraryEntrySource,
  ImportCandidate,
  ImportReviewItem,
  ImportRunSummary,
  PlanKind,
  PlanKindGuidance,
  PlanLifecycle,
  PlanProposalVersion,
  PlanRecord,
  RetrievalResult,
  SourceDocument,
  SourceDocumentContent,
  PCProfile,
  ClaimOverlap,
  ClaimReplacementDraft,
  ClaimSnapshot,
  ReconciliationDecision,
  SourceDocumentClaim,
  SourceDocumentClaimHistory,
  SessionRun,
  EncounterProgress,
  EncounterLifecycle,
  IdentityGap,
  IdentityDecisionReceipt,
} from "./campaignClient";
import type { JobPlatform, JobSnapshot } from "./jobPlatform";
import {
  assembleEncounterNotes,
  chronologicalEncounterNotes,
  encounterSectionKey,
  generalSessionNoteContext,
  loadEncounterNotes,
  saveEncounterNotes,
  type EncounterNoteContext,
  type EncounterTableNote,
} from "./encounterNotes";
import { EXTRACTION_ERROR_KEY, EXTRACTION_JOB_KEY, LAST_EXTRACTION_JOB_KEY, loadPendingJob, savePendingJob } from "./operationState";
import {
  loadReviewState,
  saveReviewState,
  type PersistedReviewState,
} from "./reviewState";

interface DocTreeNode {
  docs: SourceDocument[];
  dirs: Map<string, DocTreeNode>;
}
type MigrationStep = 1 | 2 | 3 | 4 | 5 | 6;

interface ExtractionDraft {
  extractionId: string;
  included: boolean;
  subject: string;
  subjectResolution: "focal_entity" | "named_identity" | "non_entity" | "unresolved";
  predicate: string;
  objectEntity: string;
  state: string;
  authority: string;
  visibility: string;
  assertionText: string;
  supportingExcerpt: string;
  confidence: string;
}

interface ClaimCorrectionDraft {
  assertion_text: string;
  state: string;
  authority: string;
  visibility: string;
  is_conditional: boolean;
  predicts_subject_action: boolean;
  condition_text: string;
}

interface SubjectTarget {
  mode: "new" | "existing";
  canonicalName: string;
  entityKind: EntityKind;
  entityId: string;
}

interface CharacterDocument {
  kind: "pc" | "npc";
  name: string;
  player?: string;
  race?: string;
  sex?: string;
  status?: string;
  background?: string;
  realPlaySummary?: string;
  playerPlans?: string;
  dmPlans?: string;
  npcPlans?: string;
  aliases?: string[];
  sections?: MarkdownSection[];
}

interface MarkdownSection { level: number; title: string; content: string; }
interface ParsedEntry { type: string; name: string; metadata: Map<string, string>; intro: string; sections: MarkdownSection[]; }

function cleanMarkdown(value: string): string {
  return value
    .replace(/\[\[[^\]|]+\|([^\]]+)\]\]/g, "$1")
    .replace(/\[\[([^\]]+)\]\]/g, (_, target: string) => target.split("/").pop()?.replace(/-/g, " ") ?? target)
    .replace(/\*\*(.*?)\*\*/g, "$1").replace(/\*(.*?)\*/g, "$1").replace(/`([^`]+)`/g, "$1");
}

function parseEntry(markdown: string): ParsedEntry {
  const frontmatter = markdown.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*(?:\r?\n|$)/);
  const metadata = new Map<string, string>();
  for (const line of (frontmatter?.[1] ?? "").split(/\r?\n/)) {
    const match = line.match(/^([a-z_]+):\s*(.+?)\s*$/i);
    if (match) metadata.set(match[1].toLocaleLowerCase(), match[2].replace(/^['"]|['"]$/g, ""));
  }
  const body = markdown.slice(frontmatter?.[0].length ?? 0);
  const title = body.match(/^#\s+(.+)$/m);
  const headings = [...body.matchAll(/^(#{2,4})\s+(.+?)\s*$/gm)];
  const introStart = title ? (title.index ?? 0) + title[0].length : 0;
  const introEnd = headings[0]?.index ?? body.length;
  return {
    type: metadata.get("type") ?? "source",
    name: cleanMarkdown(title?.[1]?.trim() ?? "Untitled entry"), metadata,
    intro: body.slice(introStart, introEnd).trim(),
    sections: headings.map((heading, index) => ({
      level: heading[1].length, title: cleanMarkdown(heading[2].trim()),
      content: body.slice((heading.index ?? 0) + heading[0].length, headings[index + 1]?.index ?? body.length).trim(),
    })),
  };
}

function NpcLinkedText({ value, npcs, onOpenNpc }: { value: string; npcs: LibraryEntrySummary[]; onOpenNpc?: (npc: LibraryEntrySummary) => void }) {
  if (!onOpenNpc || npcs.length === 0) return <>{value}</>;
  const names = new Map<string, LibraryEntrySummary>();
  npcs.forEach((npc) => [npc.canonical_name, ...npc.aliases].filter((name) => name.trim().length > 1).forEach((name) => names.set(name.trim().toLocaleLowerCase(), npc)));
  const pattern = Array.from(names.keys()).sort((left, right) => right.length - left.length).map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  if (!pattern) return <>{value}</>;
  const matches = [...value.matchAll(new RegExp(pattern, "giu"))].filter((match) => {
    const start = match.index ?? 0;
    const end = start + match[0].length;
    return !/[\p{L}\p{N}]/u.test(value[start - 1] ?? "") && !/[\p{L}\p{N}]/u.test(value[end] ?? "");
  });
  if (matches.length === 0) return <>{value}</>;
  const parts = [];
  let offset = 0;
  matches.forEach((match, index) => {
    const start = match.index ?? 0;
    if (start > offset) parts.push(value.slice(offset, start));
    const npc = names.get(match[0].toLocaleLowerCase());
    if (npc) parts.push(<button className="encounter-npc-link" key={`${start}-${index}`} onClick={() => onOpenNpc(npc)} type="button">{match[0]}</button>);
    offset = start + match[0].length;
  });
  if (offset < value.length) parts.push(value.slice(offset));
  return <>{parts}</>;
}

function parseMarkdownTable(block: string): { headers: string[]; rows: string[][] } | null {
  const lines = block.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2 || !lines.every((line) => line.startsWith("|"))) return null;
  const cells = (line: string) => line
    .replace(/\[\[[^\]]+\]\]/g, (link) => link.replace(/\|/g, "\u0000"))
    .replace(/\\\|/g, "\u0001")
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((cell) => cell.replace(/\u0000/g, "|").replace(/\u0001/g, "|").trim());
  const headers = cells(lines[0]);
  const divider = cells(lines[1]);
  if (headers.length === 0 || divider.length !== headers.length || !divider.every((cell) => /^:?-{3,}:?$/.test(cell))) return null;
  return { headers, rows: lines.slice(2).map(cells).filter((row) => row.some(Boolean)) };
}

function EntryTable({ block, npcs, onOpenNpc }: { block: string; npcs: LibraryEntrySummary[]; onOpenNpc?: (npc: LibraryEntrySummary) => void }) {
  const parsed = parseMarkdownTable(block);
  if (!parsed) return <pre className="entry-table-fallback">{cleanMarkdown(block)}</pre>;
  return <div className="entry-table-scroll"><table className="entry-table"><thead><tr>{parsed.headers.map((header, index) => <th key={`${header}-${index}`} scope="col"><NpcLinkedText value={cleanMarkdown(header)} npcs={npcs} onOpenNpc={onOpenNpc} /></th>)}</tr></thead><tbody>{parsed.rows.map((row, rowIndex) => <tr key={rowIndex}>{parsed.headers.map((header, cellIndex) => <td data-label={cleanMarkdown(header)} key={cellIndex}><NpcLinkedText value={cleanMarkdown(row[cellIndex] ?? "")} npcs={npcs} onOpenNpc={onOpenNpc} /></td>)}</tr>)}</tbody></table></div>;
}

function EntryText({ text, npcEntries = [], onOpenNpc }: { text: string; npcEntries?: LibraryEntrySummary[]; onOpenNpc?: (npc: LibraryEntrySummary) => void }) {
  const blocks = text.split(/\r?\n\s*\r?\n/).map((block) => block.trim()).filter(Boolean);
  return <div className="entry-text">{blocks.map((block, index) => {
    const value = cleanMarkdown(block);
    if (/^>/.test(block)) return <blockquote className="read-aloud" key={index}><NpcLinkedText value={cleanMarkdown(block.replace(/^>\s?/gm, ""))} npcs={npcEntries} onOpenNpc={onOpenNpc} /></blockquote>;
    if (/^(?:[-*]|\d+\.)\s/m.test(block)) return <ul key={index}>{block.split(/\r?\n/).filter(Boolean).map((line, item) => { const cleaned = cleanMarkdown(line.replace(/^\s*(?:[-*]|\d+\.)\s+/, "")); return <li className={/\bDC\s+\d+/i.test(line) ? "check-line" : ""} key={item}><NpcLinkedText value={cleaned} npcs={npcEntries} onOpenNpc={onOpenNpc} /></li>; })}</ul>;
    if (/^\|/.test(block)) return <EntryTable block={block} key={index} npcs={npcEntries} onOpenNpc={onOpenNpc} />;
    return <p className={/\bDC\s+\d+/i.test(block) ? "check-line" : ""} key={index}><NpcLinkedText value={value} npcs={npcEntries} onOpenNpc={onOpenNpc} /></p>;
  })}</div>;
}

function ClaimAssertion({ claim }: { claim: SourceDocumentClaim }) {
  const compact = claim.assertion_text.replace(/\s+/g, " ").trim();
  if (compact.length <= 420) return <p>{claim.assertion_text}</p>;
  const sentence = compact.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim();
  const summary = sentence && sentence.length >= 40 && sentence.length <= 280
    ? sentence
    : `${compact.slice(0, 240).replace(/\s+\S*$/, "")}…`;
  return <><p>{summary}</p><details className="full-assertion"><summary>Read full canonical assertion</summary><p>{claim.assertion_text}</p></details></>;
}

function RecordIcon({ kind }: { kind: "edit" | "source" | "hide" | "show" | "note" }) {
  if (kind === "edit") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16v4Zm9.5-13.5 4 4" /></svg>;
  if (kind === "source") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 3h9l3 3v15H6V3Z" /><path d="M15 3v4h4M9 11h6M9 15h6" /></svg>;
  if (kind === "hide") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" /><path d="m4 4 16 16" /></svg>;
  if (kind === "note") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 4h14v16H5zM8 8h8M8 12h5" /><path d="M16 14v6M13 17h6" /></svg>;
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" /><circle cx="12" cy="12" r="2.5" /></svg>;
}

function EntrySourceDrawer({ sources, fallbackPath }: { sources: LibraryEntrySource[]; fallbackPath?: string }) {
  const unique = sources.length
    ? Array.from(new Map(sources.map((source) => [source.document_id, source])).values())
    : fallbackPath ? [{ document_id: fallbackPath, path: fallbackPath }] : [];
  if (!unique.length) return null;
  return <details className="source-drawer"><summary>Sources</summary>{unique.map((source) => <code key={source.document_id}>{source.path}</code>)}</details>;
}

function CanonicalClaimSections({ claims, history, onEditClaim }: { claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; onEditClaim?: (claimId: string) => void }) {
  const [hiddenClaims, setHiddenClaims] = useState<Set<string>>(() => new Set());
  const [showHidden, setShowHidden] = useState(false);
  const groups = [
    { title: "Real-play facts", states: ["observed"] },
    { title: "Established information", states: ["established"] },
    { title: "Plans and preparation", states: ["intended", "prepared"] },
    { title: "Possibilities", states: ["possible"] },
  ];
  if (claims.length === 0 && history.length === 0) return null;
  return <section className="entry-claims canonical-record"><header><div><span>Campaign record</span><h2>Current information</h2></div><button aria-label={showHidden ? "Hide hidden records" : "Show hidden records"} disabled={hiddenClaims.size === 0} onClick={() => setShowHidden((value) => !value)} title={hiddenClaims.size === 0 ? "No hidden records" : showHidden ? "Hide hidden" : "Show hidden"} type="button"><RecordIcon kind={showHidden ? "hide" : "show"} /></button></header><div className="record-details-body">{groups.map((group) => {
    const items = claims.filter((claim) => group.states.includes(claim.state) && (showHidden || !hiddenClaims.has(claim.claim_id)));
    return items.length > 0 && <section key={group.title}><h3>{group.title}</h3><div className="canonical-claim-list">{items.map((claim) => { const isHidden = hiddenClaims.has(claim.claim_id); const hasSource = Boolean(claim.source_excerpt || claim.sources?.length); return <article className={isHidden ? "hidden-record" : ""} key={claim.claim_id}><div className="record-card-actions">{onEditClaim && <button aria-label="Edit claim" onClick={() => onEditClaim(claim.claim_id)} title="Edit" type="button"><RecordIcon kind="edit" /></button>}<button aria-label="Show source" disabled={!hasSource} title={hasSource ? "Source" : "No source available"} type="button" onClick={(event) => { const details = event.currentTarget.closest("article")?.querySelector("details.record-source") as HTMLDetailsElement | null; if (details) details.open = !details.open; }}><RecordIcon kind="source" /></button><button aria-label={isHidden ? "Restore record" : "Hide record"} onClick={() => setHiddenClaims((current) => { const next = new Set(current); next.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id); return next; })} title={isHidden ? "Restore" : "Hide"} type="button"><RecordIcon kind={isHidden ? "show" : "hide"} /></button></div><ClaimAssertion claim={claim} />{claim.conditional && claim.condition_text && <p className="claim-condition"><b>Prerequisite:</b> {claim.condition_text}</p>}<details className="record-source"><summary>Provenance</summary>{claim.source_excerpt && <pre>{claim.source_excerpt}</pre>}{claim.sources?.map((source) => <code key={source.document_id}>{source.path}</code>)}</details></article>; })}</div></section>;
  })}{history.length > 0 && <details className="claim-history"><summary>Earlier versions ({history.length})</summary>{history.map((claim) => <article key={claim.claim_id}><p>{claim.assertion_text}</p><small>{claim.supersession_reason}</small>{claim.sources?.length ? <details className="record-source"><summary>Provenance</summary>{claim.sources.map((source) => <code key={source.document_id}>{source.path}</code>)}</details> : null}</article>)}</details>}</div></section>;
}

function EncounterEntryView({ entry, path, sourceDocumentId, claims, history, sources, npcEntries, noteCounts, onOpenNpc, onAddNote, onOpenNotes, onEditClaim }: { entry: ParsedEntry; path: string; sourceDocumentId: string; claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; sources: LibraryEntrySource[]; npcEntries: LibraryEntrySummary[]; noteCounts: Map<string, number>; onOpenNpc: (npc: LibraryEntrySummary) => void; onAddNote: (context: EncounterNoteContext) => void; onOpenNotes: () => void; onEditClaim?: (claimId: string) => void }) {
  let stage = 0;
  const generalContext: EncounterNoteContext = { sourceDocumentId, sourcePath: path, encounterName: entry.name, sectionKey: `${path}#encounter`, sectionTitle: "General encounter note" };
  return <article className="document-view entry-view encounter-entry">
    <header><b>Encounter</b><span>Run at the table</span><div className="entry-page-actions encounter-page-actions"><button aria-label={`Add a general note for ${entry.name}`} onClick={() => onAddNote(generalContext)} title="Add table note" type="button"><RecordIcon kind="note" /></button><button className="encounter-note-count" onClick={onOpenNotes} type="button">{noteCounts.size ? `${Array.from(noteCounts.values()).reduce((total, count) => total + count, 0)} notes` : "Notes"}</button></div></header>
    <section className="entry-hero"><span>Prepared encounter</span><h1>{entry.name}</h1><dl><div><dt>Status</dt><dd>{entry.metadata.get("canon_status") ?? "prepared"}</dd></div>{entry.metadata.get("updated") && <div><dt>Updated</dt><dd>{entry.metadata.get("updated")}</dd></div>}</dl></section>
    {entry.intro && <section className="entry-summary"><EntryText text={entry.intro} npcEntries={npcEntries} onOpenNpc={onOpenNpc} /></section>}
    <div className="encounter-flow">{entry.sections.map((section, index) => {
      if (section.level === 2) stage += 1;
      const className = section.level === 2 ? "encounter-stage" : section.level === 3 ? "encounter-area" : "encounter-detail";
      const sectionKey = encounterSectionKey(path, index, section.title);
      const context: EncounterNoteContext = { sourceDocumentId, sourcePath: path, encounterName: entry.name, sectionKey, sectionTitle: section.title };
      const count = noteCounts.get(sectionKey) ?? 0;
      return <section className={className} key={`${section.title}-${index}`}><header>{section.level === 2 && <span>{String(stage).padStart(2, "0")}</span>}<h2>{section.title}</h2><button aria-label={`Add note for ${section.title}`} className="encounter-section-note" onClick={() => onAddNote(context)} title="Add table note" type="button"><RecordIcon kind="note" />{count > 0 && <small>{count}</small>}</button></header><EntryText text={section.content} npcEntries={npcEntries} onOpenNpc={onOpenNpc} /></section>;
    })}</div>
    <CanonicalClaimSections claims={claims} history={history} onEditClaim={onEditClaim} />
    <EntrySourceDrawer fallbackPath={path} sources={sources} />
  </article>;
}

interface EncounterDossier { entry: LibraryEntry; profile: CharacterDocument | null; path: string; }

function NpcDossierDrawer({ dossier, collapsed, initialScroll, onScroll, onToggleCollapsed, onClose, onOpenFull }: { dossier: EncounterDossier; collapsed: boolean; initialScroll: number; onScroll: (position: number) => void; onToggleCollapsed: () => void; onClose: () => void; onOpenFull: () => void }) {
  const bodyRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (bodyRef.current) bodyRef.current.scrollTop = initialScroll; }, [dossier.entry.entry_id, initialScroll]);
  const profile = dossier.profile;
  const claims = dossier.entry.claims;
  const facts = claims.filter((claim) => claim.projection === "real_play" || claim.projection === "lore_fact");
  const plans = claims.filter((claim) => claim.projection === "npc_plan" || claim.projection === "dm_plan");
  const usefulSections = (profile?.sections ?? []).filter((section) => /relationship|goal|motivation|status|personality|appearance|role/i.test(section.title));
  return <aside aria-label={`${dossier.entry.canonical_name} dossier`} className={`npc-dossier-drawer ${collapsed ? "collapsed" : ""}`}>
    <button aria-label={collapsed ? "Expand NPC dossier" : "Collapse NPC dossier"} className="npc-dossier-handle" onClick={onToggleCollapsed} title={collapsed ? "Expand dossier" : "Collapse dossier"} type="button"><span aria-hidden="true">{collapsed ? "‹" : "›"}</span></button>
    <header><div><span>NPC dossier</span><h2>{dossier.entry.canonical_name}</h2></div><button aria-label="Close NPC dossier" onClick={onClose} title="Close" type="button">×</button></header>
    <div className="npc-dossier-body" onScroll={(event) => onScroll(event.currentTarget.scrollTop)} ref={bodyRef}>
      <dl className="npc-dossier-identity">{profile?.race && <div><dt>Race</dt><dd>{profile.race}</dd></div>}{profile?.sex && <div><dt>Sex</dt><dd>{profile.sex}</dd></div>}{profile?.status && <div><dt>Status</dt><dd>{profile.status}</dd></div>}</dl>
      {profile?.background && <section><h3>Background</h3><EntryText text={profile.background} /></section>}
      {usefulSections.map((section) => <section key={section.title}><h3>{section.title}</h3><EntryText text={section.content} /></section>)}
      <section><h3>Known facts</h3>{facts.length ? facts.map((claim) => <p key={claim.claim_id}>{claim.assertion_text}</p>) : <p className="empty-section">None</p>}</section>
      <section><h3>Plans and motivations</h3>{plans.length ? plans.map((claim) => <p key={claim.claim_id}>{claim.assertion_text}</p>) : <p className="empty-section">None</p>}</section>
      <details className="source-drawer"><summary>Sources</summary>{dossier.entry.sources.map((source) => <code key={source.document_id}>{source.path}</code>)}</details>
    </div>
    <footer><button onClick={onOpenFull} type="button">Open full NPC entry</button></footer>
  </aside>;
}

function StructuredEntryView({ entry, path, claims, history, sources, onEditClaim }: { entry: ParsedEntry; path: string; claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; sources: LibraryEntrySource[]; onEditClaim?: (claimId: string) => void }) {
  const label = pathEntryType(path) === "Source" ? (entry.type === "lore" ? "Worldbuilding" : display(entry.type)) : pathEntryType(path);
  return <article className={`document-view entry-view ${entry.type}-entry`}>
    <header><b>{label}</b><span>Campaign entry</span></header>
    <section className="entry-hero"><span>{label}</span><h1>{entry.name}</h1><dl>{["location_type", "status", "canon_status", "parent_location"].map((key) => entry.metadata.get(key) && <div key={key}><dt>{display(key)}</dt><dd>{cleanMarkdown(entry.metadata.get(key)!)}</dd></div>)}</dl></section>
    {entry.intro && <section className="entry-summary"><EntryText text={entry.intro} /></section>}
    <div className="entry-sections">{entry.sections.filter((section) => section.title.toLocaleLowerCase() !== "sources" && section.title.toLocaleLowerCase() !== "references").map((section, index) => <section className={`entry-section level-${section.level}`} key={`${section.title}-${index}`}><h2>{section.title}</h2><EntryText text={section.content} /></section>)}</div>
    <CanonicalClaimSections claims={claims} history={history} onEditClaim={onEditClaim} />
    <EntrySourceDrawer fallbackPath={path} sources={sources} />
  </article>;
}

function SessionNoteEntryView({ note, claims, history, onEditClaim, onEdit }: { note: SourceDocumentContent; claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; onEditClaim?: (claimId: string) => void; onEdit: () => void }) {
  const campaignDate = note.in_game_date;
  const campaignDateLabel = campaignDate ? `${String(campaignDate.year).padStart(4, "0")}-${String(campaignDate.month).padStart(2, "0")}-${String(campaignDate.day).padStart(2, "0")} CE` : "Not recorded";
  return <article className="document-view entry-view session-note-entry">
    <header><b>Session note</b><span>Actual play</span><div className="entry-page-actions"><button aria-label="Edit session note" onClick={onEdit} title="Create a corrected revision" type="button"><RecordIcon kind="edit" /></button></div></header>
    <section className="entry-hero"><span>Session</span><h1>{note.title ?? "Untitled session"}</h1><dl><div><dt>Played</dt><dd>{note.session_date ?? "Not recorded"}</dd></div><div><dt>Campaign date</dt><dd>{campaignDateLabel}</dd></div></dl></section>
    <section className="entry-section"><h2>Session record</h2>{claims.length > 0 ? <div className="canonical-claim-list">{claims.map((claim) => <article key={claim.claim_id}>{onEditClaim && <div className="record-card-actions"><button aria-label="Edit claim" onClick={() => onEditClaim(claim.claim_id)} title="Edit" type="button"><RecordIcon kind="edit" /></button></div>}<ClaimAssertion claim={claim} /></article>)}</div> : <p>No committed claims yet.</p>}</section>
    <details className="source-drawer"><summary>Original note and provenance</summary><EntryText text={note.content} /><code>{note.path}</code></details>
    {history.length > 0 && <details className="claim-history"><summary>Superseded claim history ({history.length})</summary>{history.map((claim) => <p key={claim.claim_id}>{claim.assertion_text}</p>)}</details>}
  </article>;
}

function PlanEntryView({ plan }: { plan: PlanRecord }) {
  return <article className="document-view entry-view plan-entry"><header><b>{display(plan.plan_kind)}</b><span>{display(plan.lifecycle)}</span></header><section className="entry-hero"><span>Campaign plan</span><h1>{plan.canonical_name}</h1><dl><div><dt>Lifecycle</dt><dd>{display(plan.lifecycle)}</dd></div><div><dt>Knowledge</dt><dd>{display(plan.knowledge_boundary)}</dd></div>{plan.owner_name && <div><dt>Owner</dt><dd>{plan.owner_name}</dd></div>}</dl></section><section className="entry-summary"><h2>Summary</h2><p>{plan.summary}</p></section>{plan.objective && <section className="entry-section"><h2>Objective</h2><p>{plan.objective}</p></section>}{plan.mechanism && <section className="entry-section"><h2>Mechanism</h2><p>{plan.mechanism}</p></section>}{plan.intended_outcome && <section className="entry-section"><h2>Intended outcome</h2><p>{plan.intended_outcome}</p></section>}{(plan.evidence_source_span_ids.length > 0 || plan.supporting_claim_ids.length > 0) && <details className="source-drawer"><summary>Provenance</summary><p>Supporting evidence and related campaign facts are retained with this plan.</p></details>}</article>;
}

function characterDocument(markdown: string): CharacterDocument | null {
  const frontmatter = markdown.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*(?:\r?\n|$)/);
  const metadata = new Map<string, string>();
  for (const line of (frontmatter?.[1] ?? "").split(/\r?\n/)) {
    const match = line.match(/^([a-z_]+):\s*(.+?)\s*$/i);
    if (match) metadata.set(match[1].toLocaleLowerCase(), match[2]);
  }
  const kind = metadata.get("type");
  if (kind !== "pc" && kind !== "npc") return null;
  const body = markdown.slice(frontmatter?.[0].length ?? 0);
  const name = body.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? "Unnamed character";
  const sections = new Map<string, string>();
  const headings = [...body.matchAll(/^##\s+(.+?)\s*$/gm)];
  headings.forEach((heading, index) => {
    const start = (heading.index ?? 0) + heading[0].length;
    const end = headings[index + 1]?.index ?? body.length;
    sections.set(heading[1].trim().toLocaleLowerCase(), body.slice(start, end).trim());
  });
  const details = sections.get("character details") ?? "";
  const detail = (label: string) => details.match(new RegExp(`^- \\*\\*${label}:\\*\\*\\s*(.+)$`, "im"))?.[1]?.trim();
  const curatedPcRace: Record<string, string> = {
    Coreferra: "Tabaxi",
    Ladir: "Dwarf",
    Ruhrogue: "Half-elf",
    "Zander Thromius": "Half-elf",
  };
  return {
    kind,
    name,
    player: metadata.get("player") ?? detail("Player"),
    race: metadata.get("race") ?? detail("Race") ?? (kind === "pc" ? curatedPcRace[name] : undefined),
    sex: metadata.get("sex") ?? detail("Sex"),
    status: metadata.get("status") ?? detail("Status"),
    background: kind === "pc"
      ? sections.get("original biography source")
      : sections.get("background / history"),
    realPlaySummary: sections.get("current status"),
    playerPlans: sections.get("player plans"),
    dmPlans: sections.get("private gm notes"),
    npcPlans: sections.get("current goals") ?? sections.get("goals & motivations"),
    sections: parseEntry(markdown).sections,
  };
}

function CharacterDocumentView({ profile, path, sources = [], onEdit, dmClaims = [], claimHistory = [], onEditClaim }: { profile: CharacterDocument; path: string; sources?: LibraryEntrySource[]; onEdit?: () => void; dmClaims?: SourceDocumentClaim[]; claimHistory?: SourceDocumentClaimHistory[]; onEditClaim?: (claimId: string) => void }) {
  const [hiddenClaims, setHiddenClaims] = useState<Set<string>>(() => new Set());
  const [visibleSources, setVisibleSources] = useState<Set<string>>(() => new Set());
  const [showHidden, setShowHidden] = useState(false);
  const Field = ({ label, value }: { label: string; value?: string }) => <div><dt>{label}</dt><dd className={value ? "" : "missing"}>{value || "Not recorded"}</dd></div>;
  const claims = dmClaims;
  const normalized = (value?: string) => (value ?? "").replace(/\s+/g, " ").trim().toLocaleLowerCase();
  const projectedAs = (claim: SourceDocumentClaim): SourceDocumentClaim["projection"] => claim.projection ?? (["brainstorm", "preparation"].includes(claim.authority) ? "dm_plan" : claim.authority === "npc_intention" ? "npc_plan" : ["real_play", "dm_correction"].includes(claim.authority) ? "real_play" : "lore_fact");
  const ClaimList = ({ projection, empty }: { projection: SourceDocumentClaim["projection"]; empty: string }) => {
    const items = claims.filter((claim) => projectedAs(claim) === projection);
    const visible = items.filter((claim) => showHidden || !hiddenClaims.has(claim.claim_id));
    return visible.length ? <div className="canonical-claim-list">{visible.map((claim) => {
      const isHidden = hiddenClaims.has(claim.claim_id);
      const hasSource = Boolean(claim.source_excerpt || claim.sources?.length);
      return <article className={isHidden ? "hidden-record" : ""} key={claim.claim_id}><div className="record-card-actions">{onEditClaim && <button aria-label="Edit claim" onClick={() => onEditClaim(claim.claim_id)} title="Edit" type="button"><RecordIcon kind="edit" /></button>}<button aria-label="Show source" disabled={!hasSource} onClick={() => setVisibleSources((current) => { const next = new Set(current); next.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id); return next; })} title={hasSource ? "Source" : "No source available"} type="button"><RecordIcon kind="source" /></button><button aria-label={isHidden ? "Restore record" : "Hide record"} onClick={() => setHiddenClaims((current) => { const next = new Set(current); next.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id); return next; })} title={isHidden ? "Restore" : "Hide"} type="button"><RecordIcon kind={isHidden ? "show" : "hide"} /></button></div><ClaimAssertion claim={claim} />{claim.conditional && claim.condition_text && <p className="claim-condition"><b>Prerequisite:</b> {claim.condition_text}</p>}{visibleSources.has(claim.claim_id) && <div className="record-source">{claim.source_excerpt && normalized(claim.source_excerpt) !== normalized(claim.assertion_text) && <pre>{claim.source_excerpt}</pre>}{claim.sources?.map((source) => <code key={source.document_id}>{source.path}</code>)}</div>}</article>;
    })}</div> : <p className="empty-section">{empty}</p>;
  };
  return <article className="document-view character-document">
    <header><b>{profile.kind === "pc" ? "Player character" : "Non-player character"}</b><span>Campaign character</span><div className="entry-page-actions">{onEdit && <button aria-label={`Edit ${profile.kind.toUpperCase()} page`} onClick={onEdit} title="Edit" type="button"><RecordIcon kind="edit" /></button>}<button aria-label={showHidden ? "Hide hidden records" : "Show hidden records"} disabled={hiddenClaims.size === 0} onClick={() => setShowHidden((value) => !value)} title={hiddenClaims.size === 0 ? "No hidden records" : showHidden ? "Hide hidden" : "Show hidden"} type="button"><RecordIcon kind={showHidden ? "hide" : "show"} /></button></div></header>
    <section className="character-profile">
      <div><span>{profile.kind === "pc" ? "Player character" : "Non-player character"}</span><h1>{profile.name}</h1></div>
      <dl>
        {profile.kind === "pc" && <Field label="Player" value={profile.player} />}
        <Field label="Race" value={profile.race} />
        <Field label="Sex" value={profile.sex} />
        <Field label="Status" value={profile.status} />
      </dl>
    </section>
    <section className="character-content"><h2>Background</h2>{profile.background ? <pre>{profile.background}</pre> : <p className="empty-section">No authoritative background recorded.</p>}</section>
    {profile.kind === "npc" && <section className="character-content character-dossier"><h2>Character dossier</h2><div>{(profile.sections ?? []).filter((section) => !["background/history", "background / history", "current status/goals", "current goals", "goals & motivations", "references", "notes"].includes(section.title.toLocaleLowerCase())).map((section) => <section key={section.title}><h3>{section.title}</h3><EntryText text={section.content} /></section>)}</div></section>}
    {profile.kind === "npc" && <section className="character-content"><h2>Known facts</h2><ClaimList projection="lore_fact" empty="None" /></section>}
    <section className="character-content"><h2>Real-play facts</h2><ClaimList projection="real_play" empty="None" /></section>
    {profile.kind === "pc" && <section className="character-content"><h2>Player plans</h2><ClaimList projection="player_plan" empty="None" /></section>}
    {profile.kind === "npc" && <section className="character-content"><h2>NPC plans</h2><ClaimList projection="npc_plan" empty="None" /></section>}
    <section className="character-content"><h2>DM plans</h2><ClaimList projection="dm_plan" empty="None" /></section>
    {claimHistory.length > 0 && <section className="character-content claim-history"><details><summary>Earlier versions ({claimHistory.length})</summary>{claimHistory.map((claim) => <article key={claim.claim_id}><p>{claim.assertion_text}</p><small>Superseded: {claim.supersession_reason}</small>{claim.source_excerpt && <details><summary>Source evidence</summary><pre>{claim.source_excerpt}</pre></details>}</article>)}</details></section>}
    <EntrySourceDrawer fallbackPath={path} sources={sources} />
  </article>;
}

function CharacterProfileEditor({ profile, kind, changedFields, preview, onChange, onCancel, onReview, onSave }: {
  profile: PCProfile;
  kind: "pc" | "npc";
  changedFields: string[];
  preview: boolean;
  onChange: (profile: PCProfile) => void;
  onCancel: () => void;
  onReview: () => void;
  onSave: () => void;
}) {
  const label = kind.toUpperCase();
  return <article className="document-view pc-editor">
    <header><b>{kind === "pc" ? "Player character" : "Non-player character"}</b><span>Editing version {profile.version}</span></header>
    <section className="character-content">
      <div className="form-grid">
        <label>Name<input aria-label={`${label} name`} value={profile.canonical_name} onChange={(event) => onChange({ ...profile, canonical_name: event.target.value })} /></label>
        {kind === "pc" && <label>Player<input aria-label="PC player" value={profile.player ?? ""} onChange={(event) => onChange({ ...profile, player: event.target.value })} /></label>}
        <label>Race<input aria-label={`${label} race`} value={profile.race ?? ""} onChange={(event) => onChange({ ...profile, race: event.target.value || undefined })} /></label>
        <label>Sex<input aria-label={`${label} sex`} value={profile.sex ?? ""} onChange={(event) => onChange({ ...profile, sex: event.target.value || undefined })} /></label>
        <label>Status<input aria-label={`${label} status`} value={profile.status} onChange={(event) => onChange({ ...profile, status: event.target.value })} /></label>
        {/* The in-progress (last) segment keeps its trailing space mid-word; its leading space would double the join separator, so it is start-trimmed. */}
        <label>Aliases<input aria-label={`${label} aliases`} value={profile.aliases.join(", ")} onChange={(event) => onChange({ ...profile, aliases: event.target.value.split(",").map((value, index, all) => index < all.length - 1 ? value.trim() : value.trimStart()) })} onBlur={(event) => onChange({ ...profile, aliases: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></label>
      </div>
      <label className="pc-background-field">Background<textarea aria-label={`${label} background`} rows={14} value={profile.background} onChange={(event) => onChange({ ...profile, background: event.target.value })} /></label>
      {preview && <section className="pc-change-preview" aria-label={`${label} profile change review`}><div><h2>Save these changes?</h2><p>{changedFields.length === 1 ? "1 field changed" : `${changedFields.length} fields changed`}: {changedFields.join(", ")}.</p></div><button onClick={onSave} type="button">Save changes</button></section>}
      <div className="step-actions"><button className="text-button" onClick={onCancel} type="button">Cancel</button><button disabled={!profile.canonical_name.trim() || (kind === "pc" && !profile.player?.trim()) || !profile.status.trim() || changedFields.length === 0} onClick={onReview} type="button">Review changes</button></div>
    </section>
  </article>;
}

function subjectKey(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function localCalendarDate(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function AssertionFirstReview(props: {
  drafts: ExtractionDraft[];
  setDrafts: (update: (prior: ExtractionDraft[]) => ExtractionDraft[]) => void;
  onBack: () => void;
  onAbandon: () => void;
  onContinue: (subject: string) => void;
}) {
  const [openIndexes, setOpenIndexes] = useState<Set<number>>(() => new Set());
  const update = (index: number, change: Partial<ExtractionDraft>) =>
    props.setDrafts((prior) => prior.map((draft, itemIndex) =>
      itemIndex === index ? { ...draft, ...change } : draft));
  const canContinue = props.drafts.some((draft) =>
    draft.included && draft.assertionText.trim() && draft.subject.trim());
  return <section className="assertion-review" aria-label="Assertion-first extraction review">
    <header>
      <span>Review extracted assertions</span>
      <p>The complete assertion is the record. Subject is required for resolution; predicate and object are optional retrieval indexes.</p>
    </header>
    <div className="extraction-draft-list">{props.drafts.map((draft, index) =>
      <article className={draft.included ? "extraction-draft" : "extraction-draft excluded"} key={draft.extractionId}>
        <label className="include-extraction"><input checked={draft.included} onChange={(event) => update(index, { included: event.target.checked })} type="checkbox" />Include assertion {index + 1}</label>
        <label className="assertion-field">Assertion<textarea aria-label={`Extraction ${index + 1} assertion`} value={draft.assertionText} onChange={(event) => update(index, { assertionText: event.target.value })} /></label>
        <label>Principal subject<input aria-label={`Assertion ${index + 1} principal subject`} value={draft.subject} onChange={(event) => update(index, { subject: event.target.value })} /></label>
        <p className={`subject-resolution subject-${draft.subjectResolution}`}>{draft.subjectResolution === "focal_entity" ? "Resolved from the document's focal subject" : draft.subjectResolution === "named_identity" ? "Named identity grounded in the cited source" : draft.subjectResolution === "non_entity" ? "Source-grounded non-entity phrase — choose the principal entity before proposing" : "Unresolved model phrasing — explicitly choose or correct the principal identity"}</p>
        <details className="retrieval-indexes" onToggle={(event) => setOpenIndexes((prior) => { const next = new Set(prior); if (event.currentTarget.open) next.add(index); else next.delete(index); return next; })}>
          <summary>Optional retrieval indexes</summary>
          {openIndexes.has(index) && <div className="form-grid">
            <label>Predicate<input aria-label={`Assertion ${index + 1} index predicate`} value={draft.predicate} onChange={(event) => update(index, { predicate: event.target.value })} /></label>
            <label>Object text<input aria-label={`Assertion ${index + 1} index object`} value={draft.objectEntity} onChange={(event) => update(index, { objectEntity: event.target.value })} /></label>
          </div>}
        </details>
        <blockquote>{draft.supportingExcerpt}</blockquote>
      </article>)}</div>
    <div className="step-actions"><button className="danger-button" onClick={props.onAbandon} type="button">Abandon extraction</button><button className="text-button" onClick={props.onBack} type="button">Back to extraction</button><button disabled={!canContinue} onClick={() => props.onContinue(props.drafts.find((draft) => draft.included)?.subject.trim() ?? "")} type="button">Continue with selected assertions</button></div>
  </section>;
}

const MIGRATION_STEPS = [
  "Document", "Assertion", "Optional extraction", "Proposal", "Approval", "Application",
] as const;

function buildDocTree(docs: SourceDocument[]): Record<string, DocTreeNode> {
  const root: Record<string, DocTreeNode> = {};
  for (const doc of docs) {
    const parts = doc.path.split("/");
    const top = parts[0];
    if (!root[top]) root[top] = { docs: [], dirs: new Map() };
    let node = root[top];
    for (let i = 1; i < parts.length; i++) {
      if (i === parts.length - 1) {
        node.docs.push(doc);
      } else {
        const child = parts.slice(0, i + 1).join("/");
        if (!node.dirs.has(child)) node.dirs.set(child, { docs: [], dirs: new Map() });
        node = node.dirs.get(child)!;
      }
    }
    if (parts.length === 1) node.docs.push(doc);
  }
  return root;
}

function entryLabel(path: string): string {
  let leaf = (path.split("/").pop() ?? path).replace(/\.md$/i, "");
  if (/^sessions\/notes\//i.test(path)) leaf = leaf.replace(/^\d{4}-\d{2}-\d{2}-/, "").replace(/-[0-9a-f]{8}$/i, "");
  return leaf.split("-").map((part) => part ? part[0].toLocaleUpperCase() + part.slice(1) : part).join(" ");
}

function pathSegmentLabel(value: string): string {
  const spaced = value.replace(/\.md$/i, "").replaceAll("-", " ");
  return /[A-Z]/.test(value) ? spaced : entryLabel(value);
}

function sourceDocumentLabel(document: SourceDocument): string {
  const pathParts = document.path.replace(/\\/g, "/").split("/");
  const isEncounterOverview = pathParts[0]?.toLocaleLowerCase() === "encounters"
    && pathParts.length > 2
    && /^overview\.md$/i.test(pathParts.at(-1) ?? "");
  const title = document.title ?? (isEncounterOverview ? pathSegmentLabel(pathParts.at(-2)!) : entryLabel(document.path));
  return document.document_type === "session_note" && document.session_date
    ? `${document.session_date} — ${title}`
    : title;
}

function sourceDocumentOrder(left: SourceDocument, right: SourceDocument): number {
  if (left.document_type === "session_note" || right.document_type === "session_note") {
    const byDate = (right.session_date ?? "").localeCompare(left.session_date ?? "");
    if (byDate) return byDate;
  }
  return sourceDocumentLabel(left).localeCompare(sourceDocumentLabel(right), undefined, { numeric: true });
}

function encounterCollection(document: SourceDocument): string | null {
  const parts = document.path.replace(/\\/g, "/").split("/");
  return parts[0]?.toLocaleLowerCase() === "encounters" && parts.length > 2
    ? parts.slice(1, -1).map(pathSegmentLabel).join(" / ")
    : null;
}

function SourceBackedFamily({ family, documents, selectedDocumentId, onSelect, onEditSession }: {
  family: string;
  documents: SourceDocument[];
  selectedDocumentId: string | null;
  onSelect: (document: SourceDocument) => void;
  onEditSession: (document: SourceDocument) => void;
}) {
  const row = (document: SourceDocument) => <div className="source-entry-row" key={document.document_id}>
    <button className={`tree-doc canonical-entry-link ${selectedDocumentId === document.document_id ? "selected" : ""}`} onClick={() => onSelect(document)} type="button"><span className="tree-doc-name">{sourceDocumentLabel(document)}</span></button>
    {document.document_type === "session_note" && <button aria-label={`Edit ${sourceDocumentLabel(document)}`} className="source-entry-edit" onClick={() => onEditSession(document)} title="Edit session note" type="button"><RecordIcon kind="edit" /></button>}
  </div>;
  const sorted = [...documents].sort(sourceDocumentOrder);
  const heading = ({ "GM planning": "GM planning", Worldbuilding: "Worldbuilding", Session: "Sessions", Handout: "Handouts" } as Record<string, string>)[family] ?? `${family}s`;
  if (family !== "Encounter") return <details className="canonical-entry-group source-backed-group"><summary>{heading}</summary><div>{sorted.map(row)}</div></details>;
  const collections = new Map<string, SourceDocument[]>();
  sorted.forEach((document) => {
    const collection = encounterCollection(document);
    if (collection) collections.set(collection, [...(collections.get(collection) ?? []), document]);
  });
  const ungrouped = sorted.filter((document) => {
    const collection = encounterCollection(document);
    return !collection || (collections.get(collection)?.length ?? 0) < 2;
  });
  return <details className="canonical-entry-group source-backed-group"><summary>Encounters</summary><div>{ungrouped.map(row)}{Array.from(collections.entries()).filter(([, items]) => items.length > 1).map(([name, items]) => <details className="encounter-collection" key={name}><summary>{name}</summary><div>{items.map(row)}</div></details>)}</div></details>;
}

function pathEntryType(path: string): string {
  const root = path.split("/")[0];
  return ({ pcs: "PC", npcs: "NPC", encounters: "Encounter", locations: "Location", lore: "Worldbuilding", gm: "GM planning", handouts: "Handout", sessions: "Session" } as Record<string, string>)[root] ?? "Source";
}

function isSourceBackedEntry(doc: SourceDocument): boolean {
  if (/^sessions\/prep\//i.test(doc.path)) return false;
  if (/^gm\/(?:location-evidence|location-migration-inventory)(?:\/|\.md$)/i.test(doc.path)) return false;
  return /^(?:encounters|gm|handouts|lore|sessions)\//i.test(doc.path);
}

function TreeDir(props: {
  name: string;
  depth: number;
  children_: DocTreeNode;
  expanded: Set<string>;
  setExpanded: (fn: (prev: Set<string>) => Set<string>) => void;
  selectedDocumentId: string | null;
  onSelect: (docId: string) => void;
  sourceMode?: boolean;
}) {
  const isOpen = props.expanded.has(props.name);
  const toggle = () => props.setExpanded((prev) => {
    const next = new Set(prev);
    if (isOpen) next.delete(props.name); else next.add(props.name);
    return next;
  });
  return (
    <div className="tree-dir">
      <button className="tree-dir-toggle" onClick={toggle} style={{ paddingLeft: `${props.depth * 14 + 8}px` }} type="button">
        <span className={`tree-arrow ${isOpen ? "open" : ""}`}>▸</span>
        <span className="tree-dir-name">{props.name.split("/").pop()}</span>
        {props.children_.docs.length > 0 && <span className="tree-count">{props.children_.docs.length}</span>}
      </button>
      {isOpen && (
        <div className="tree-children">
          {props.children_.docs.map((doc) => (
            <button
              key={doc.document_id}
              aria-label={`${pathEntryType(doc.path)} ${sourceDocumentLabel(doc)} (${doc.path.split("/").pop()})`}
              className={`tree-doc ${doc.document_id === props.selectedDocumentId ? "selected" : ""}`}
              onClick={() => props.onSelect(doc.document_id)}
              style={{ paddingLeft: `${(props.depth + 1) * 14 + 8}px` }}
              type="button"
            >
              <span className={`tree-classification tree-cls-${doc.classification}`}>{props.sourceMode ? display(doc.classification) : pathEntryType(doc.path)}</span>
              <span className="tree-doc-name">{props.sourceMode ? doc.path.split("/").pop() : sourceDocumentLabel(doc)}</span>
              {doc.candidate_count > 0 && <span className="tree-count">{doc.candidate_count}</span>}
              {doc.extraction_count > 0 && <span className="tree-extracted" title="Extractions available">✦</span>}
              {doc.open_review_count > 0 && <span className="tree-warning" title={`${doc.open_review_count} open reviews`}>⚠</span>}
              {doc.missing_source && <span className="tree-missing" title="Source file missing">✕</span>}
            </button>
          ))}
          {Array.from(props.children_.dirs.entries()).map(([subName, subNode]) => (
            <TreeDir
              key={subName}
              name={subName}
              depth={props.depth + 1}
              children_={subNode}
              expanded={props.expanded}
              setExpanded={props.setExpanded}
              selectedDocumentId={props.selectedDocumentId}
              onSelect={props.onSelect}
              sourceMode={props.sourceMode}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface AppProps {
  campaignClient: CampaignClient;
  jobPlatform: JobPlatform;
  storage?: Storage;
  pollIntervalMs?: number;
}

const MODE_COPY: Record<RetrievalResult["answer_mode"], { eyebrow: string; title: string }> = {
  answer: { eyebrow: "Grounded answer", title: "The archive supports this" },
  insufficient_evidence: { eyebrow: "Records incomplete", title: "Not enough evidence" },
  conflict: { eyebrow: "Conflict", title: "The records disagree" },
  possible_retcon: { eyebrow: "Review required", title: "Possible retcon detected" },
  restricted: { eyebrow: "Restricted", title: "Visible records cannot answer this" },
};

const JOB_COPY: Record<JobSnapshot["state"], string> = {
  queued: "Waiting for a worker",
  running: "Campaign Core check in progress",
  succeeded: "Campaign Core is available",
  failed: "Campaign Core check failed",
};

const ENTITY_KINDS: EntityKindGuidance[] = [
  { kind: "npc", label: "NPC", description: "A DM-controlled character." },
  { kind: "pc", label: "PC", description: "A character controlled only by its player." },
  { kind: "location", label: "Location", description: "A place at any geographic scale." },
  { kind: "faction", label: "Faction", description: "An organized group with shared identity." },
  { kind: "item", label: "Item", description: "An in-world object with canonical identity." },
  { kind: "event", label: "Event", description: "A distinct historical, mythical, or cosmological occurrence." },
  { kind: "worldbuilding", label: "Worldbuilding", description: "An era, legend, cosmological structure, or abstract setting concept." },
  { kind: "rules_element", label: "Rules element", description: "A reusable spell, feat, or ability." },
];

const INITIAL_TAGS = [
  "history", "mythology", "cosmology", "world", "continent", "country",
  "region", "settlement", "monster", "deity", "religion", "political",
];

function ArchiveMark() {
  return (
    <svg aria-hidden="true" className="archive-mark" viewBox="0 0 40 40">
      <path d="M20 3 34 10v20l-14 7L6 30V10l14-7Z" />
      <path d="m12 14 8-4 8 4v12l-8 4-8-4V14Z" />
      <path d="M20 10v20M12 14l8 4 8-4" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  );
}

function PulseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M3 12h4l2.2-5 4.1 10 2.2-5H21" />
    </svg>
  );
}

function display(value: string): string {
  return value.replaceAll("_", " ");
}

function PinIcon() {
  return (
    <svg aria-hidden="true" className="pin-icon" viewBox="0 0 24 24">
      <path d="M8 3h8l-1.4 6 3 3v2H13v7l-1 1-1-1v-7H6.4v-2l3-3L8 3Z" />
    </svg>
  );
}

function entryKindLabel(value: string): string {
  if (value.toLowerCase() === "npc") return "NPC";
  if (value.toLowerCase() === "pc") return "PC";
  const label = display(value);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function cleanImportedAssertion(value: string): string {
  return value
    .split(/\r?\n/)
    .filter((line) => !/^\s*Source:\s*\[\[.*\]\]\s*$/i.test(line))
    .filter((line) => !/^\s*#{1,6}\s+/.test(line))
    .filter((line) => !/^\s*These are GM planning notes only\b/i.test(line))
    .map((line) => line.replace(/^\s*-\s+/, "").replaceAll("**", "").trimEnd())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function reviewSummary(review: ImportReviewItem): string {
  for (const key of ["reason", "warning", "message", "path"]) {
    const value = review.details[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return display(review.kind);
}

function phaseLabel(state: PersistedReviewState): string {
  const labels: Record<PersistedReviewState["phase"], string> = {
    idle: "No pending action",
    proposal_pending: "Ready for approval",
    approved: "Approved and ready to apply",
    applied: "Applied with receipt",
    rejected: "Candidate rejected",
    deferred: "Candidate deferred",
    stale: "Stale proposal version",
    failed: "Operation failed",
  };
  return labels[state.phase];
}

function App({ campaignClient, jobPlatform, storage, pollIntervalMs = 700 }: AppProps) {
  const session = storage ?? window.sessionStorage;
  const [question, setQuestion] = useState("");
  const [queryState, setQueryState] = useState<"idle" | "loading" | "error">("idle");
  const [queryError, setQueryError] = useState("");
  const [result, setResult] = useState<RetrievalResult | null>(null);
  const [job, setJob] = useState<JobSnapshot | null>(() => loadPendingJob(session));
  const [extractionJob, setExtractionJob] = useState<JobSnapshot | null>(() =>
    loadPendingJob(session, EXTRACTION_JOB_KEY),
  );
  const [lastExtractionJob, setLastExtractionJob] = useState<JobSnapshot | null>(() =>
    loadPendingJob(session, LAST_EXTRACTION_JOB_KEY),
  );
  const [extractionTaskError, setExtractionTaskError] = useState(() =>
    session.getItem(EXTRACTION_ERROR_KEY) ?? "",
  );
  const [cancelBusy, setCancelBusy] = useState(false);
  const [jobActionError, setJobActionError] = useState("");
  const pollTimer = useRef<number | undefined>(undefined);
  const extractionPollTimer = useRef<number | undefined>(undefined);

  const [runs, setRuns] = useState<ImportRunSummary[]>([]);
  const [candidates, setCandidates] = useState<ImportCandidate[]>([]);
  const [reviews, setReviews] = useState<ImportReviewItem[]>([]);
  const [identityGaps, setIdentityGaps] = useState<IdentityGap[] | null>(null);
  const [identityBusy, setIdentityBusy] = useState(false);
  const [identityMessage, setIdentityMessage] = useState("");
  const [identityKinds, setIdentityKinds] = useState<Record<string, string>>({});
  const [identityAliasSelection, setIdentityAliasSelection] = useState<Record<string, string[]>>({});
  const [queueTotal, setQueueTotal] = useState(0);
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocument[]>([]);
  const [libraryEntries, setLibraryEntries] = useState<LibraryEntrySummary[]>([]);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<LibraryEntry | null>(null);
  const [libraryPlans, setLibraryPlans] = useState<PlanRecord[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<PlanRecord | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewError, setReviewError] = useState("");
  const [selected, setSelected] = useState<ImportCandidate | null>(null);
  const [filters, setFilters] = useState<CandidateFilters>({ status: "active", review_status: "pending" });
  const [reviewState, setReviewState] = useState<PersistedReviewState>(() =>
    loadReviewState(session),
  );
  const [proposalValidated, setProposalValidated] = useState(!reviewState.proposal);
  const [proposalValidationError, setProposalValidationError] = useState("");
  const [resolution, setResolution] = useState<"new" | "existing">("new");
  const [entityName, setEntityName] = useState("");
  const [entityKind, setEntityKind] = useState<EntityKind>("npc");
  const [entityKinds, setEntityKinds] = useState(ENTITY_KINDS);
  const [availableTags, setAvailableTags] = useState<string[]>(INITIAL_TAGS);
  const [tagsExpanded, setTagsExpanded] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [additionalSubjectTargets, setAdditionalSubjectTargets] = useState<Record<string, SubjectTarget>>({});
  const [entityMatches, setEntityMatches] = useState<EntityIdentity[]>([]);
  const [entityLookupBusy, setEntityLookupBusy] = useState(false);
  const [observedAt, setObservedAt] = useState("");
  const [observedCampaignDate, setObservedCampaignDate] = useState("");
  const [conditionText, setConditionText] = useState("");
  const [conditionEnabled, setConditionEnabled] = useState(false);
  const [provenanceAssertion, setProvenanceAssertion] = useState("");
  const [splitClaims, setSplitClaims] = useState<string[] | null>(null);
  const candidateLoadSequence = useRef(0);
  const [provenanceState, setProvenanceState] = useState("");
  const [provenanceAuthority, setProvenanceAuthority] = useState("");
  const [provenanceVisibility, setProvenanceVisibility] = useState("");
  const [dispositionReason, setDispositionReason] = useState("");
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [claimCorrection, setClaimCorrection] = useState<ClaimCorrectionDraft | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [extractionNotice, setExtractionNotice] = useState("");
  const [migrationStep, setMigrationStep] = useState<MigrationStep>(() =>
    reviewState.phase === "approved" || reviewState.phase === "applied" ? 6 : reviewState.proposal ? 5 : 1,
  );
  const [extractionDrafts, setExtractionDrafts] = useState<ExtractionDraft[]>([]);
  const [batchBusy, setBatchBusy] = useState(false);
  const [batchNotice, setBatchNotice] = useState("");
  const extractionPending = Boolean(
    extractionJob && ["queued", "running"].includes(extractionJob.state),
  );
  const displayedExtractionJob = (extractionJob ?? lastExtractionJob)!;

  useEffect(() => {
    if (claimCorrection?.state === "possible" && claimCorrection.is_conditional) {
      setClaimCorrection({ ...claimCorrection, is_conditional: false, condition_text: "" });
    }
  }, [claimCorrection]);

  useEffect(() => savePendingJob(session, job), [job, session]);
  useEffect(() => savePendingJob(session, extractionJob, EXTRACTION_JOB_KEY), [extractionJob, session]);
  useEffect(() => savePendingJob(session, lastExtractionJob, LAST_EXTRACTION_JOB_KEY), [lastExtractionJob, session]);
  useEffect(() => {
    if (extractionTaskError) session.setItem(EXTRACTION_ERROR_KEY, extractionTaskError);
    else session.removeItem(EXTRACTION_ERROR_KEY);
  }, [extractionTaskError, session]);
  useEffect(() => saveReviewState(session, reviewState), [reviewState, session]);

  useEffect(() => {
    if (migrationStep !== 4 || !entityName.trim()) {
      setEntityMatches([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setEntityLookupBusy(true);
      try {
        const matches = await campaignClient.searchEntities(entityName.trim());
        if (cancelled) return;
        setEntityMatches(matches);
        const exactMatches = matches.filter((match) =>
          match.match_kind === "alias"
          || match.canonical_name.toLocaleLowerCase() === entityName.trim().toLocaleLowerCase(),
        );
        const exact = exactMatches.length === 1 ? exactMatches[0] : undefined;
        if (exact) {
          setResolution("existing");
          setSubjectId(exact.entity_id);
          setEntityKind(exact.entity_kind);
        } else if (exactMatches.length > 1) {
          setResolution("existing");
          setSubjectId("");
        }
      } catch {
        if (!cancelled) setEntityMatches([]);
      } finally {
        if (!cancelled) setEntityLookupBusy(false);
      }
    }, 200);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [campaignClient, entityName, migrationStep]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.state)) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const next = await jobPlatform.inspect(job.jobId);
        if (cancelled) return;
        setJob(next);
        setJobActionError("");
        if (["queued", "running"].includes(next.state)) {
          pollTimer.current = window.setTimeout(poll, pollIntervalMs);
        }
      } catch (error) {
        if (!cancelled) {
          setJobActionError(error instanceof Error ? error.message : "Job status is unavailable");
        }
      }
    };
    pollTimer.current = window.setTimeout(poll, 0);
    return () => {
      cancelled = true;
      if (pollTimer.current !== undefined) window.clearTimeout(pollTimer.current);
    };
  }, [job?.jobId, job?.state, jobPlatform, pollIntervalMs]);

  useEffect(() => {
    if (!extractionJob || !["queued", "running"].includes(extractionJob.state)) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const next = await jobPlatform.inspect(extractionJob.jobId);
        if (cancelled) return;
        setExtractionJob({ ...next, totalItems: extractionJob.totalItems, candidateIds: extractionJob.candidateIds });
      } catch (error) {
        if (!cancelled) {
          setReviewError(error instanceof Error ? error.message : "Extraction job status is unavailable");
          extractionPollTimer.current = window.setTimeout(poll, pollIntervalMs * 2);
        }
      }
    };
    extractionPollTimer.current = window.setTimeout(poll, 0);
    return () => {
      cancelled = true;
      if (extractionPollTimer.current !== undefined) window.clearTimeout(extractionPollTimer.current);
    };
  }, [extractionJob?.jobId, extractionJob?.state, jobPlatform, pollIntervalMs]);

  useEffect(() => {
    if (!extractionJob || !["succeeded", "failed"].includes(extractionJob.state)) return;
    let cancelled = false;
    const finish = async () => {
      if (extractionJob.state === "failed") {
        const message = extractionJob.error ?? "Background extraction failed";
        setReviewError(message);
        setExtractionTaskError(message);
        setExtractionNotice("Background extraction failed. Completed candidates remain stored.");
        setLastExtractionJob(extractionJob);
        setExtractionJob(null);
        return;
      }
      const payload = extractionJob.result as { results?: Array<{ candidate_id: string; ok: boolean; error?: string }> } | undefined;
      const results = payload?.results ?? [];
      const succeeded = results.filter((result) => result.ok);
      const failed = results.filter((result) => !result.ok);
      setExtractionNotice(`${succeeded.length} candidate${succeeded.length === 1 ? "" : "s"} extracted${failed.length ? `; ${failed.length} failed` : ""}.`);
      if (failed.length) {
        const message = failed.map((result) => result.error).filter(Boolean).join("; ") || `${failed.length} extraction item${failed.length === 1 ? "" : "s"} failed`;
        setReviewError(message);
        setExtractionTaskError(message);
      }
      const preferredId = selected && succeeded.some((result) => result.candidate_id === selected.candidate_id) ? selected.candidate_id : succeeded[0]?.candidate_id;
      if (preferredId) {
        try {
          const detail = await campaignClient.getCandidate(preferredId);
          if (cancelled) return;
          setSelected(detail);
          setCandidates((prior) => prior.map((candidate) => candidate.candidate_id === detail.candidate_id ? detail : candidate));
          if (detail.extractions?.length) beginExtractionReview(detail.extractions, detail);
        } catch (error) {
          if (!cancelled) setReviewError(error instanceof Error ? error.message : "Extracted candidate could not be refreshed");
        }
      }
      if (!cancelled) {
        setLastExtractionJob(extractionJob);
        setExtractionJob(null);
      }
    };
    void finish();
    return () => { cancelled = true; };
  }, [extractionJob?.jobId, extractionJob?.state]);

  async function loadReviewWorkspace(
    activeFilters: CandidateFilters = filters,
    restoreSelection = true,
  ) {
    setReviewLoading(true);
    setReviewError("");
    try {
      const [taxonomy, runPage, candidatePage, reviewPage, docPage, entries, planRecords] = await Promise.all([
        campaignClient.getTaxonomy(),
        campaignClient.listImportRuns(),
        campaignClient.listCandidates(activeFilters),
        campaignClient.listReviews(activeFilters.run_id),
        campaignClient.listSourceDocuments(),
        campaignClient.listLibraryEntries(),
        campaignClient.listPlans(),
      ]);
      setEntityKinds(taxonomy.entity_kinds);
      setAvailableTags(taxonomy.tags);
      setRuns(runPage.items);
      const visibleCandidates = activeFilters.source && activeFilters.review_status === undefined
        ? candidatePage.items.filter((candidate) => ["pending", "proposed"].includes(candidate.review_status))
        : candidatePage.items;
      setCandidates(visibleCandidates);
      setQueueTotal(activeFilters.source && activeFilters.review_status === undefined ? visibleCandidates.length : candidatePage.total);
      setReviews(reviewPage.items);
      setSourceDocuments(docPage.items);
      setLibraryEntries(entries);
      setLibraryPlans(planRecords);
      const persistedId = restoreSelection ? reviewState.selectedCandidateId : undefined;
      if (persistedId) {
        const detail = await campaignClient.getCandidate(persistedId);
        setSelected(detail);
      }
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Import review is unavailable");
    } finally {
      setReviewLoading(false);
    }
  }

  async function confirmProposalVersion(proposalToConfirm: CandidateProposalVersion) {
    setProposalValidated(false);
    setProposalValidationError("");
    try {
      const current = await Promise.race([
        campaignClient.getProposal(proposalToConfirm.proposal_id),
        new Promise<never>((_resolve, reject) => window.setTimeout(
          () => reject(new Error("Campaign Core confirmation timed out.")),
          10000,
        )),
      ]);
      if (
        current.version_number !== proposalToConfirm.version_number
        || current.content_hash !== proposalToConfirm.content_hash
      ) {
        setReviewState((prior) => ({
          ...prior,
          phase: "stale",
          proposal: current,
          approval: undefined,
          message: "The proposal changed after the displayed version was reviewed.",
        }));
        setProposalValidationError("The displayed proposal is stale. Review the current version.");
        return;
      }
      setReviewState((prior) => ({ ...prior, proposal: current }));
      setSelectedItemIds(current.items.map((item) => item.item_id));
      setProposalValidated(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Proposal confirmation failed";
      setProposalValidationError(message);
      setReviewState((prior) => ({ ...prior, message }));
    }
  }

  useEffect(() => {
    void loadReviewWorkspace();
    if (reviewState.proposal) {
      void confirmProposalVersion(reviewState.proposal);
    }
    // The initial snapshot is intentionally restored exactly once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ask(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    setQueryState("loading");
    setQueryError("");
    try {
      setResult(
        await campaignClient.query({
          question: trimmed,
          requester_visibility: { role: "dm" },
        }),
      );
      setQueryState("idle");
    } catch (error) {
      setQueryError(error instanceof Error ? error.message : "The archive could not be queried");
      setQueryState("error");
    }
  }

  async function startHealthCheck() {
    setJobActionError("");
    try {
      setJob(await jobPlatform.startHealthCheck());
    } catch (error) {
      setJobActionError(error instanceof Error ? error.message : "The job could not be started");
    }
  }

  function initializeCandidateDraft(detail: ImportCandidate) {
    setSelected(detail);
    setConditionEnabled(false);
    setConditionText("");
    setProvenanceAssertion(cleanImportedAssertion(detail.assertion_text));
    setSplitClaims(null);
    setProvenanceState(detail.state);
    setProvenanceAuthority(detail.authority);
    setProvenanceVisibility(detail.visibility);
    const capturedDate = detail.evidence.find((item) => item.in_game_date)?.in_game_date;
    setObservedAt(detail.state === "observed" && capturedDate?.year ? String(capturedDate.year) : "");
    setObservedCampaignDate(detail.state === "observed" && capturedDate?.year && capturedDate.month && capturedDate.day
      ? `${String(capturedDate.year).padStart(4, "0")}-${String(capturedDate.month).padStart(2, "0")}-${String(capturedDate.day).padStart(2, "0")}` : "");
    setClaimCorrection(null);
  }

  async function chooseCandidate(candidateId: string) {
    const queuedCandidate = candidates.find((candidate) => candidate.candidate_id === candidateId);
    if (["proposal_pending", "approved"].includes(reviewState.phase) && queuedCandidate?.review_status !== "proposed" && reviewState.selectedCandidateId !== candidateId) return;
    setReviewBusy(true);
    const loadSequence = ++candidateLoadSequence.current;
    try {
      const detail = await campaignClient.getCandidate(candidateId);
      if (loadSequence !== candidateLoadSequence.current) return;
      initializeCandidateDraft(detail);
      if (detail.review_status === "proposed") {
        const recovered = await campaignClient.getCandidateProposal(candidateId);
        setSelectedItemIds(recovered.items.map((item) => item.item_id));
        setProposalValidated(true);
        setReviewState({ selectedCandidateId: candidateId, phase: "proposal_pending", proposal: recovered, message: `Recovered immutable proposal version ${recovered.version_number}.` });
        setMigrationStep(5);
        return;
      }
      setReviewState({ selectedCandidateId: candidateId, phase: "idle" });
      setEntityName("");
      setDispositionReason("");
      setExtractionDrafts([]);
      setExtractionNotice("");
      if (detail.extractions?.length) beginExtractionReview(detail.extractions, detail);
      else setMigrationStep(2);
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Candidate could not be loaded");
    } finally {
      setReviewBusy(false);
    }
  }

  async function runExtraction(candidateId: string) {
    if (!selected || extractionPending) return;
    setReviewError("");
    setBatchNotice("");
    setExtractionNotice("Queueing background extraction…");
    setExtractionTaskError("");
    try {
      setExtractionJob(await jobPlatform.startCandidateExtraction([candidateId]));
      setExtractionNotice("Background extraction queued. You can continue browsing.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Extraction could not be queued";
      setReviewError(message);
      setExtractionTaskError(message);
      setExtractionNotice("");
    }
  }

  async function retryFailedExtraction() {
    if (!displayedExtractionJob || extractionPending) return;
    const results = (displayedExtractionJob.result as { results?: Array<{ candidate_id: string; ok: boolean }> } | undefined)?.results ?? [];
    const failedIds = results.filter((result) => !result.ok).map((result) => result.candidate_id);
    const candidateIds = failedIds.length > 0 ? failedIds : displayedExtractionJob.candidateIds ?? [];
    if (candidateIds.length === 0) {
      setExtractionTaskError("This older task did not retain its candidate IDs. Retry it once from the candidate page; future retries will be available here.");
      return;
    }
    setExtractionNotice(`Retrying ${candidateIds.length} failed candidate${candidateIds.length === 1 ? "" : "s"}…`);
    try {
      const next = await jobPlatform.startCandidateExtraction(candidateIds);
      setExtractionJob(next);
      setExtractionTaskError("");
      setReviewError("");
      setExtractionNotice(`${candidateIds.length} failed candidate${candidateIds.length === 1 ? "" : "s"} queued again.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Extraction retry could not be queued";
      setReviewError(message);
      setExtractionTaskError(message);
      setExtractionNotice("");
    }
  }

  async function extractPendingSequence() {
    const pending = candidates.filter((candidate) => candidate.review_status === "pending");
    if (pending.length === 0 || batchBusy || extractionPending) return;
    setBatchBusy(true);
    setReviewError("");
    setExtractionTaskError("");
    const bounded = pending.slice(0, 50);
    setBatchNotice(`Queueing ${bounded.length} pending candidate${bounded.length === 1 ? "" : "s"}…`);
    try {
      setExtractionJob(await jobPlatform.startCandidateExtraction(bounded.map((candidate) => candidate.candidate_id)));
      setBatchNotice(`${bounded.length} candidate${bounded.length === 1 ? "" : "s"} queued in the background. You can continue browsing.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Batch extraction could not be queued";
      setReviewError(message);
      setExtractionTaskError(message);
      setBatchNotice("");
    } finally {
      setBatchBusy(false);
    }
  }

  async function cancelExtraction() {
    if (!extractionJob || !extractionPending || cancelBusy) return;
    setCancelBusy(true);
    try {
      await jobPlatform.cancel(extractionJob.jobId);
      const cancelled = { ...extractionJob, state: "failed" as const, progress: 100, error: "Cancelled by user." };
      setLastExtractionJob(cancelled);
      setExtractionJob(null);
      setExtractionNotice("Background extraction cancelled.");
      setExtractionTaskError("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Extraction could not be cancelled";
      setReviewError(message);
      setExtractionTaskError(message);
    } finally {
      setCancelBusy(false);
    }
  }

  function beginExtractionReview(
    extractions: CandidateExtraction[],
    candidate: ImportCandidate,
  ) {
    setExtractionDrafts(extractions.map((extraction) => ({
      extractionId: extraction.extraction_id,
      included: true,
      subject: extraction.subject,
      subjectResolution: extraction.subject_resolution ?? "named_identity",
      predicate: extraction.predicate ?? "",
      objectEntity: extraction.object_entity ?? "",
      // The candidate's reviewed truth dimensions govern promotion. AI extraction
      // identifies claims, but cannot silently reclassify their epistemic status.
      state: candidate.state,
      authority: candidate.authority,
      visibility: candidate.visibility,
      assertionText: extraction.assertion_text,
      supportingExcerpt: extraction.supporting_excerpt,
      confidence: extraction.confidence,
    })));
    setEntityName(extractions[0]?.subject ?? "");
    const sourcePath = candidate.evidence[0]?.source_path.toLocaleLowerCase() ?? "";
    const inferredKind = sourcePath.startsWith("pcs/")
      ? "pc"
      : sourcePath.startsWith("npcs/")
        ? "npc"
        : sourcePath.startsWith("locations/")
          ? "location"
          : null;
    if (inferredKind && entityKinds.some((kind) => kind.kind === inferredKind)) {
      setEntityKind(inferredKind as EntityKind);
    }
    setMigrationStep(3);
  }
  function claimItem(
    candidate: ImportCandidate,
    evidenceRevisionId: string,
    targetSubjectId: string,
    draft: ExtractionDraft,
  ): CreateProposalItem {
    return {
      mutation_kind: "create_claim",
      candidate_id: candidate.candidate_id,
      candidate_extraction_id: draft.extractionId,
      evidence_revision_id: evidenceRevisionId,
      target_id: crypto.randomUUID(),
      subject_entity_id: targetSubjectId,
      assertion_text: draft.assertionText.trim(),
      ...(draft.predicate.trim() ? { predicate: draft.predicate.trim() } : {}),
      state: draft.state,
      authority: draft.authority,
      visibility: draft.visibility,
      confidence: "1",
      is_conditional: draft.state === "possible" ? false : conditionEnabled,
      ...(draft.state !== "possible" && conditionEnabled && conditionText.trim()
        ? { condition_text: conditionText.trim() }
        : {}),
      predicts_subject_action: candidate.predicts_subject_action,
      recorded_at: new Date().toISOString(),
      ...(draft.state === "observed" && observedAt
        ? { observed_at: { calendar_id: "gregorian-ce", year: Number(observedAt) } }
        : {}),
    };
  }

  async function prepareSubjectGroups(subject: string) {
    const subjects = [...new Map(extractionDrafts.filter((draft) => draft.included).map((draft) => [subjectKey(draft.subject), draft.subject.trim()])).values()];
    setEntityName(subject);
    const additional = subjects.slice(1);
    const resolved = await Promise.all(additional.map(async (name) => {
      const matches = await campaignClient.searchEntities(name);
      const exact = matches.filter((match) => match.match_kind === "alias" || match.canonical_name.toLocaleLowerCase() === name.toLocaleLowerCase());
      const match = exact.length === 1 ? exact[0] : undefined;
      return [subjectKey(name), match ? { mode: "existing" as const, canonicalName: match.canonical_name, entityKind: match.entity_kind, entityId: match.entity_id } : { mode: "new" as const, canonicalName: name, entityKind, entityId: "" }] as const;
    }));
    setAdditionalSubjectTargets(Object.fromEntries(resolved));
    setMigrationStep(4);
  }

  async function createProposal(event: FormEvent) {
    event.preventDefault();
    const includedDrafts = extractionDrafts.filter(
      (draft) => draft.included && draft.subject.trim(),
    );
    if (!selected || !selected.evidence[0] || includedDrafts.length === 0) return;
    if (includedDrafts.some((draft) => draft.state !== "possible") && conditionEnabled && !conditionText.trim()) {
      setReviewError("A conditional claim needs a concrete trigger before it can be proposed.");
      return;
    }
    if (includedDrafts.some((draft) => draft.state === "observed") && !observedAt) {
      setReviewError("Real-play claims need an observed campaign date before they can be proposed.");
      return;
    }
    if (Object.values(additionalSubjectTargets).some((target) =>
      target.mode === "existing" ? !target.entityId.trim() : !target.canonicalName.trim())) return;
    setReviewBusy(true);
    setReviewError("");
    try {
      const evidenceRevisionId = selected.evidence[0].source_revision_id;
      const items: CreateProposalItem[] = [];
      const primarySubject = subjectKey(includedDrafts[0].subject);
      const targetIds = new Map<string, string>();
      if (resolution === "new") {
        const entityId = crypto.randomUUID();
        targetIds.set(primarySubject, entityId);
        items.push({
            mutation_kind: "create_entity",
            candidate_id: selected.candidate_id,
            evidence_revision_id: evidenceRevisionId,
            target_id: entityId,
            entity_kind: entityKind,
            canonical_name: entityName.trim(),
            tags: selectedTags,
          });
      } else {
        targetIds.set(primarySubject, subjectId.trim());
      }
      for (const [key, target] of Object.entries(additionalSubjectTargets)) {
        if (target.mode === "existing") targetIds.set(key, target.entityId.trim());
        else {
          const entityId = crypto.randomUUID();
          targetIds.set(key, entityId);
          items.push({ mutation_kind: "create_entity", candidate_id: selected.candidate_id, evidence_revision_id: evidenceRevisionId, target_id: entityId, entity_kind: target.entityKind, canonical_name: target.canonicalName.trim(), tags: [] });
        }
      }
      items.push(...includedDrafts.map((draft) => claimItem(selected, evidenceRevisionId, targetIds.get(subjectKey(draft.subject)) ?? "", draft)));
      const proposal = await campaignClient.createProposal(items);
      setProposalValidated(true);
      setSelectedItemIds(proposal.items.map((item) => item.item_id));
      setReviewState({
        selectedCandidateId: selected.candidate_id,
        phase: "proposal_pending",
        proposal,
      });
      setMigrationStep(5);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Proposal creation failed";
      setReviewState((prior) => ({ ...prior, phase: "failed", message }));
    } finally {
      setReviewBusy(false);
    }
  }

  async function createProvenanceFirstProposal() {
    if (!selected || !selected.evidence[0]) return;
    setReviewBusy(true);
    setReviewError("");
    try {
      const item: CreateProposalItem = {
        mutation_kind: "create_claim",
        candidate_id: selected.candidate_id,
        evidence_revision_id: selected.evidence[0].source_revision_id,
        target_id: crypto.randomUUID(),
        assertion_text: provenanceAssertion.trim(),
        state: provenanceState,
        authority: provenanceAuthority,
        visibility: provenanceVisibility,
        confidence: "1",
        is_conditional: provenanceState === "possible" ? false : conditionEnabled,
        ...(provenanceState !== "possible" && conditionEnabled ? { condition_text: conditionText.trim() } : {}),
        predicts_subject_action: selected.predicts_subject_action,
        recorded_at: new Date().toISOString(),
        ...(provenanceState === "observed" && observedAt
          ? { observed_at: { calendar_id: "gregorian-ce", year: Number(observedAt) } }
          : {}),
      };
      let created: CandidateProposalVersion;
      try {
        created = await campaignClient.createProposal([item]);
      } catch (error) {
        if (!/409|conflict|already|proposal/i.test(error instanceof Error ? error.message : String(error))) throw error;
        created = await campaignClient.getCandidateProposal(selected.candidate_id);
      }
      setProposalValidated(true);
      setSelectedItemIds(created.items.map((proposalItem) => proposalItem.item_id));
      setReviewState({
        selectedCandidateId: selected.candidate_id,
        phase: "proposal_pending",
        proposal: created,
        message: "Source-backed assertion is ready for exact approval.",
      });
      setMigrationStep(5);
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Proposal could not be created");
    } finally {
      setReviewBusy(false);
    }
  }

  async function commitDirectInputClaim() {
    const assertions = (splitClaims ?? [provenanceAssertion]).map((value) => value.trim()).filter(Boolean);
    if (!selected || !selected.evidence[0] || assertions.length === 0 || (provenanceState === "observed" && !observedCampaignDate)) return;
    setReviewBusy(true); setReviewError("");
    try {
      const commonItem = {
        mutation_kind: "create_claim",
        candidate_id: selected.candidate_id,
        evidence_revision_id: selected.evidence[0].source_revision_id,
        state: provenanceState,
        authority: provenanceAuthority,
        visibility: provenanceVisibility,
        confidence: "1",
        is_conditional: provenanceState === "possible" ? false : conditionEnabled,
        ...(provenanceState !== "possible" && conditionEnabled ? { condition_text: conditionText.trim() } : {}),
        predicts_subject_action: selected.predicts_subject_action,
        recorded_at: new Date().toISOString(),
        ...(provenanceState === "observed" && observedCampaignDate ? (() => { const [year, month, day] = observedCampaignDate.split("-").map(Number); return { observed_at: { calendar_id: "gregorian-ce", year, month, day } }; })() : {}),
      };
      const mentions = selected.evidence.flatMap((evidence) => evidence.mentions ?? []);
      const items: CreateProposalItem[] = assertions.map((assertionText) => ({
        ...commonItem,
        target_id: crypto.randomUUID(),
        assertion_text: assertionText,
        related_entity_ids: Array.from(new Set(mentions
          .filter((mention) => assertionText.toLocaleLowerCase().includes(mention.display_name.toLocaleLowerCase()))
          .map((mention) => mention.entity_id))),
      } as CreateProposalItem));
      let created: CandidateProposalVersion;
      try {
        created = await campaignClient.createProposal(items);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (!/409|conflict|already|proposal/i.test(message)) throw error;
        created = await campaignClient.getCandidateProposal(selected.candidate_id);
        const existingClaims = created.items.filter((proposalItem) => proposalItem.mutation_kind === "create_claim");
        const proposalMatchesDraft = existingClaims.length === items.length && existingClaims.every((proposalItem, index) => {
          const desired = items[index];
          if (desired.mutation_kind !== "create_claim") return false;
          const currentRelated = Array.isArray(proposalItem.after.related_entity_ids) ? proposalItem.after.related_entity_ids.map(String).sort() : [];
          return String(proposalItem.after.assertion_text ?? "") === desired.assertion_text
            && JSON.stringify(currentRelated) === JSON.stringify([...(desired.related_entity_ids ?? [])].sort());
        });
        if (!proposalMatchesDraft) created = await campaignClient.reviseProposal(created.proposal_id, items);
      }
      const confirmed = await campaignClient.getProposal(created.proposal_id);
      if (confirmed.version_number !== created.version_number || confirmed.content_hash !== created.content_hash) throw new Error("Campaign Core returned a different immutable proposal version.");
      const scope = confirmed.items.map((proposalItem) => proposalItem.item_id).sort();
      const approval = await campaignClient.approveProposal(confirmed, scope, `direct-review:${confirmed.proposal_id}:${confirmed.version_number}:${scope.join(",")}`);
      const receipt = await campaignClient.applyApproval(confirmed, approval);
      setCandidates((current) => current.map((candidate) => candidate.candidate_id === selected.candidate_id ? { ...candidate, review_status: "applied" } : candidate));
      void campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => { /* the applied receipt remains authoritative if projection refresh is temporarily unavailable */ });
      void campaignClient.listSourceDocuments().then((page) => setSourceDocuments(page.items)).catch(() => { /* source navigation refreshes independently */ });
      const next = candidates.find((candidate) => candidate.candidate_id !== selected.candidate_id && candidate.review_status === "pending");
      if (next) {
        setBatchNotice(`Applied with receipt ${receipt.receipt_id}. Opening the next note line.`);
        await chooseCandidate(next.candidate_id);
      } else {
        setSessionReviewComplete({
          sourceDocumentId: selected.source_document_id,
          sourcePath: selected.evidence[0].source_path,
          receiptId: receipt.receipt_id,
        });
        setSelected(null);
        setReviewState({ phase: "idle" });
        setBatchNotice("");
        setMigrationStep(1);
      }
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "The claim could not be committed");
    } finally { setReviewBusy(false); }
  }

  function beginClaimSplit() {
    const sentences = provenanceAssertion.trim().split(/(?<=[.!?])\s+(?=[A-Z@])/).map((value) => value.trim()).filter(Boolean);
    const initial = sentences.length > 1 ? sentences : [provenanceAssertion.trim(), ""];
    setSplitClaims(initial);
  }

  function abandonExtraction() {
    setExtractionDrafts([]);
    setExtractionNotice("Extraction abandoned. The source-backed candidate remains available.");
    setMigrationStep(2);
  }

  function proposalDecision(item: CandidateProposalVersion["items"][number]): CreateProposalItem {
    const after = item.after;
    if (item.mutation_kind === "create_entity") {
      return {
        mutation_kind: "create_entity", candidate_id: item.evidence.candidate_id,
        evidence_revision_id: item.evidence.source_revision_id, target_id: item.target_id,
        entity_kind: String(after.entity_kind ?? after.entity_type) as EntityKind,
        canonical_name: String(after.canonical_name),
        tags: Array.isArray(after.tags) ? after.tags.map(String) : [],
      };
    }
    return {
      mutation_kind: "create_claim", candidate_id: item.evidence.candidate_id,
      evidence_revision_id: item.evidence.source_revision_id, target_id: item.target_id,
      ...(after.subject_entity_id ? { subject_entity_id: String(after.subject_entity_id) } : {}),
      ...(after.assertion_text ? { assertion_text: String(after.assertion_text) } : {}),
      ...(after.predicate ? { predicate: String(after.predicate) } : {}),
      state: String(after.state), authority: String(after.authority),
      visibility: String(after.visibility), confidence: String(after.confidence ?? "1"),
      is_conditional: Boolean(after.is_conditional),
      ...(after.condition_text ? { condition_text: String(after.condition_text) } : {}),
      predicts_subject_action: Boolean(after.predicts_subject_action),
      recorded_at: String(after.recorded_at),
      ...(after.observed_at && typeof after.observed_at === "object"
        ? { observed_at: after.observed_at as CreateClaimProposalItem["observed_at"] }
        : {}),
    };
  }

  async function reviseClaimProposal() {
    const proposal = reviewState.proposal;
    if (!proposal || !claimCorrection) return;
    if (claimCorrection.is_conditional && !claimCorrection.condition_text.trim()) {
      setReviewError("Conditional claims require a concrete trigger.");
      return;
    }
    const claimItem = proposal.items.find((item) => item.mutation_kind === "create_claim");
    if (!claimItem || !claimCorrection.assertion_text.trim()) return;
    setReviewBusy(true); setProposalValidated(false); setReviewError("");
    try {
      const items = proposal.items.map((item) => {
        const decision = proposalDecision(item);
        if (item.item_id !== claimItem.item_id) return decision;
        return { ...decision, ...claimCorrection, assertion_text: claimCorrection.assertion_text.trim(), ...(claimCorrection.is_conditional ? { condition_text: claimCorrection.condition_text.trim() } : { condition_text: undefined }) } as CreateClaimProposalItem;
      });
      const revised = await campaignClient.reviseProposal(proposal.proposal_id, items);
      setReviewState((prior) => ({ ...prior, proposal: revised, phase: "proposal_pending", message: `Correction saved as immutable version ${revised.version_number}.` }));
      setSelectedItemIds(revised.items.map((item) => item.item_id));
      setClaimCorrection(null); setProposalValidated(true);
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Proposal correction failed");
      setProposalValidated(true);
    } finally { setReviewBusy(false); }
  }

  function addTag(value: string) {
    const normalized = value.trim().toLocaleLowerCase().replace(/\s+/g, " ");
    if (!normalized || selectedTags.includes(normalized)) return;
    setSelectedTags([...selectedTags, normalized]);
    setTagDraft("");
  }

  async function disposition(dispositionValue: "deferred" | "rejected") {
    if (!selected || !dispositionReason.trim()) return;
    setReviewBusy(true);
    try {
      const result = await campaignClient.dispositionCandidate(
        selected.candidate_id,
        dispositionValue,
        dispositionReason.trim(),
      );
      const next = { ...selected, review_status: result.review_status };
      setSelected(next);
      setCandidates((prior) =>
        prior.map((item) => (item.candidate_id === next.candidate_id ? next : item)),
      );
      setReviewState({
        selectedCandidateId: selected.candidate_id,
        phase: result.review_status,
        message: result.reason,
      });
      if (selected.extractor_version.startsWith("direct-input/session-note")) {
        const following = candidates.find((candidate) => candidate.candidate_id !== selected.candidate_id && candidate.review_status === "pending");
        if (following) {
          setBatchNotice(`${display(result.review_status)} with an audit reason. Opening the next note line.`);
          await chooseCandidate(following.candidate_id);
        } else {
          setSessionReviewComplete({ sourceDocumentId: selected.source_document_id, sourcePath: selected.evidence[0]?.source_path ?? "", receiptId: "not applicable — final statement skipped" });
          setSelected(null);
          setReviewState({ phase: "idle" });
          setBatchNotice("");
          setMigrationStep(1);
        }
      }
    } catch (error) {
      setReviewState((prior) => ({
        ...prior,
        phase: "failed",
        message: error instanceof Error ? error.message : "Disposition failed",
      }));
    } finally {
      setReviewBusy(false);
    }
  }

  async function approveAndApplyProposal() {
    const proposal = reviewState.proposal;
    if (!proposal || !proposalValidated || selectedItemIds.length === 0) return;
    setReviewBusy(true);
    try {
      const scope = [...selectedItemIds].sort();
      const approval = await campaignClient.approveProposal(
        proposal,
        scope,
        `review:${proposal.proposal_id}:${proposal.version_number}:${scope.join(",")}`,
      );
      setReviewState((prior) => ({ ...prior, phase: "approved", approval, message: undefined }));
      setMigrationStep(6);
      try {
        const receipt = await campaignClient.applyApproval(proposal, approval);
        setReviewState((prior) => ({
          ...prior,
          phase: "applied",
          approval,
          receipt,
          message: undefined,
        }));
        if (selected) {
          setSelected({ ...selected, review_status: "applied" });
          setCandidates((prior) => filters.source && filters.review_status === undefined
            ? prior.filter((candidate) => candidate.candidate_id !== selected.candidate_id)
            : prior.map((candidate) => candidate.candidate_id === selected.candidate_id
              ? { ...candidate, review_status: "applied" } : candidate));
        }
        void campaignClient.listSourceDocuments().then((page) => setSourceDocuments(page.items));
        const next = candidates.find(
          (candidate) =>
            candidate.candidate_id !== selected?.candidate_id &&
            candidate.review_status === "pending",
        );
        if (next) {
          setBatchNotice(`Applied with receipt ${receipt.receipt_id}. Opening the next candidate.`);
          try {
            const detail = await campaignClient.getCandidate(next.candidate_id);
            initializeCandidateDraft(detail);
            setReviewState({ selectedCandidateId: detail.candidate_id, phase: "idle" });
            setExtractionDrafts([]);
            if (detail.extractions?.length) beginExtractionReview(detail.extractions, detail);
            else setMigrationStep(2);
          } catch {
            setBatchNotice(`Applied with receipt ${receipt.receipt_id}. Select the next candidate to continue.`);
          }
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Application failed";
        const stale = /stale|version|superseded/i.test(message);
        setReviewState((prior) => ({
          ...prior,
          phase: stale ? "stale" : "approved",
          approval,
          message: stale ? message : `Application failed: ${message}`,
        }));
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Approval failed";
      const stale = /stale|version|superseded/i.test(message);
      setReviewState((prior) => ({
        ...prior,
        phase: stale ? "stale" : "failed",
        message,
      }));
    } finally {
      setReviewBusy(false);
    }
  }

  async function applyApproval() {
    const { proposal, approval } = reviewState;
    if (!proposal || !approval || !proposalValidated) return;
    setReviewBusy(true);
    try {
      const receipt = await campaignClient.applyApproval(proposal, approval);
      setReviewState((prior) => ({
        ...prior,
        phase: "applied",
        receipt,
        message: undefined,
      }));
      if (selected) {
        setSelected({ ...selected, review_status: "applied" });
        setCandidates((prior) => filters.source && filters.review_status === undefined
          ? prior.filter((candidate) => candidate.candidate_id !== selected.candidate_id)
          : prior.map((candidate) => candidate.candidate_id === selected.candidate_id
            ? { ...candidate, review_status: "applied" } : candidate));
      }
      void campaignClient.listSourceDocuments().then((page) => setSourceDocuments(page.items));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Application failed";
      const stale = /stale|version|superseded/i.test(message);
      setReviewState((prior) => ({
        ...prior,
        phase: stale ? "stale" : "approved",
        message: stale ? message : `Application failed: ${message}`,
      }));
    } finally {
      setReviewBusy(false);
    }
  }

  const loadIdentityGaps = useCallback(async () => {
    setIdentityBusy(true);
    try {
      const queue = await campaignClient.getIdentityGaps(30);
      setIdentityGaps(queue.gaps);
      // Related surfaces default to selected: merging variants is the common
      // case, and deselecting is the explicit refusal.
      setIdentityAliasSelection(Object.fromEntries(queue.gaps.map((gap) => [
        gap.normalized_surface, [...gap.related_surfaces]])));
      setIdentityMessage("");
    } catch (error) {
      setIdentityMessage(error instanceof Error ? error.message : "Identity queue could not be loaded");
    } finally {
      setIdentityBusy(false);
    }
  }, [campaignClient]);

  const decideIdentity = useCallback(async (action: () => Promise<IdentityDecisionReceipt>, done: string) => {
    setIdentityBusy(true);
    try {
      const receipt = await action();
      await loadIdentityGaps();
      setIdentityMessage(`${done} with receipt ${receipt.decision_id}`);
    } catch (error) {
      setIdentityMessage(error instanceof Error ? error.message : "Identity decision failed");
    } finally {
      setIdentityBusy(false);
    }
  }, [campaignClient, loadIdentityGaps]);

  const selectedReviews = useMemo(
    () => reviews.filter((review) => review.subject_id === selected?.source_document_id),
    [reviews, selected?.source_document_id],
  );
  const sourceReviews = useMemo(
    () =>
      [...reviews]
        .filter((review) => review.subject_type === "source_document")
        .sort((left, right) => {
          const leftQuarantine = left.kind === "import_quarantine" ? 0 : 1;
          const rightQuarantine = right.kind === "import_quarantine" ? 0 : 1;
          return leftQuarantine - rightQuarantine || left.kind.localeCompare(right.kind);
        }),
    [reviews],
  );
  const quarantineCount = reviews.filter(
    (review) => review.kind === "import_quarantine" || review.classification === "quarantine",
  ).length;
  const activeRun = runs.find((run) => run.import_run_id === filters.run_id) ?? runs[0];
  const proposal = reviewState.proposal;
  const proposalBelongsToSelected = Boolean(
    proposal && selected && proposal.items.some(
      (item) => item.evidence.candidate_id === selected.candidate_id,
    ),
  );
  const modeCopy = result ? MODE_COPY[result.answer_mode] : null;
  const isPending = job && ["queued", "running"].includes(job.state);
  const proposalBlocksSelection = proposalBelongsToSelected
    && ["proposal_pending", "approved"].includes(reviewState.phase);

  const sourceBackedLibraryDocuments = useMemo(() => {
    const canonicalPCNames = new Set(libraryEntries.filter((entry) => entry.entity_kind === "pc").map((entry) => entry.canonical_name.trim().toLocaleLowerCase()));
    return sourceDocuments.filter((doc) => isSourceBackedEntry(doc) || (
      /^pcs\//i.test(doc.path) && !canonicalPCNames.has((doc.title ?? entryLabel(doc.path)).trim().toLocaleLowerCase())
    ));
  }, [libraryEntries, sourceDocuments]);

  const editableSessionDocuments = useMemo(
    () => sourceDocuments.filter((document) => document.document_type === "session_note" && document.capture_mode === "direct_input")
      .sort((left, right) => (right.session_date ?? "").localeCompare(left.session_date ?? "")),
    [sourceDocuments],
  );

  const [activePage, setActivePage] = useState<"documents" | "brainstorm" | "migration" | "tools">("documents");
  const [sessionCaptureOpen, setSessionCaptureOpen] = useState(false);
  const [sessionReviewComplete, setSessionReviewComplete] = useState<{ sourceDocumentId: string; sourcePath: string; receiptId?: string } | null>(null);
  const [sessionCaptureDate, setSessionCaptureDate] = useState(() => localCalendarDate());
  const [sessionCaptureTitle, setSessionCaptureTitle] = useState("");
  const [sessionCaptureId, setSessionCaptureId] = useState<string | null>(null);
  const [sessionCaptureText, setSessionCaptureText] = useState("");
  const [inGameDate, setInGameDate] = useState("");
  const [sessionCaptureBusy, setSessionCaptureBusy] = useState(false);
  const [sessionCaptureError, setSessionCaptureError] = useState("");
  const [sessionMentions, setSessionMentions] = useState<EntityIdentity[]>([]);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionMatches, setMentionMatches] = useState<EntityIdentity[]>([]);
  const [mentionHighlight, setMentionHighlight] = useState(0);
  const [mentionMenuPosition, setMentionMenuPosition] = useState({ left: 16, top: 48 });
  const sessionNotesRef = useRef<HTMLTextAreaElement>(null);
  const [libraryMode, setLibraryMode] = useState<"entries" | "sources">("entries");
  const [libraryPanelCollapsed, setLibraryPanelCollapsed] = useState(() => {
    try { return window.localStorage.getItem("dm-assistant.library-panel-collapsed") === "true"; } catch { return false; }
  });
  useEffect(() => {
    try { window.localStorage.setItem("dm-assistant.library-panel-collapsed", String(libraryPanelCollapsed)); } catch { /* browser storage may be unavailable */ }
  }, [libraryPanelCollapsed]);
  const [docContent, setDocContent] = useState<string>("");
  const [docMetadata, setDocMetadata] = useState<SourceDocumentContent | null>(null);
  const [docContentPath, setDocContentPath] = useState<string>("");
  const [docCanonicalClaims, setDocCanonicalClaims] = useState<SourceDocumentClaim[]>([]);
  const [docClaimHistory, setDocClaimHistory] = useState<SourceDocumentClaimHistory[]>([]);
  const [encounterDossier, setEncounterDossier] = useState<EncounterDossier | null>(null);
  const [encounterDossierCollapsed, setEncounterDossierCollapsed] = useState(false);
  const [encounterDossierLoading, setEncounterDossierLoading] = useState(false);
  const [encounterDossierError, setEncounterDossierError] = useState("");
  const dossierScrollPositions = useRef(new Map<string, number>());
  const [encounterNotes, setEncounterNotes] = useState<EncounterTableNote[]>(() => loadEncounterNotes());
  const [sessionRun, setSessionRun] = useState<SessionRun | null>(null);
  const [encounterProgress, setEncounterProgress] = useState<EncounterProgress[]>([]);
  const [newSessionMenuOpen, setNewSessionMenuOpen] = useState(false);
  const sessionRunRef = useRef<SessionRun | null>(null);
  const sessionRunOpening = useRef<Promise<SessionRun> | null>(null);
  const [tableNotesSyncError, setTableNotesSyncError] = useState("");
  const [tableNotesOpen, setTableNotesOpen] = useState(false);
  const [tableNoteContext, setTableNoteContext] = useState<EncounterNoteContext | null>(null);
  const [tableNoteDraft, setTableNoteDraft] = useState("");
  const [editingTableNoteId, setEditingTableNoteId] = useState<string | null>(null);
  const [tableNoteDestination, setTableNoteDestination] = useState("new");
  const [sessionCaptureTableNoteIds, setSessionCaptureTableNoteIds] = useState<string[]>([]);
  const tableNoteInputRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { saveEncounterNotes(encounterNotes); }, [encounterNotes]);
  useEffect(() => { sessionRunRef.current = sessionRun; }, [sessionRun]);
  useEffect(() => {
    let cancelled = false;
    void campaignClient.listEncounterProgress()
      .then((items) => { if (!cancelled) setEncounterProgress(items); })
      .catch(() => { /* progress is supplementary to note capture */ });
    return () => { cancelled = true; };
  }, [campaignClient]);
  useEffect(() => {
    let cancelled = false;
    const localNotes = loadEncounterNotes();
    void (async () => {
      try {
        let run = await campaignClient.getOpenSessionRun();
        if (!run && localNotes.length > 0) {
          const currentDate = await campaignClient.getCurrentCampaignDate().catch(() => null);
          run = await campaignClient.openSessionRun({
            session_date: localCalendarDate(),
            ...(currentDate ? { in_game_date: currentDate } : {}),
            title: localNotes[0]?.encounterName ?? "Session notes",
          });
        }
        if (!run || cancelled) return;
        sessionRunRef.current = run;
        const remoteIds = new Set(run.notes.map((note) => note.note_id));
        for (const note of localNotes.filter((item) => !remoteIds.has(item.noteId))) {
          await campaignClient.saveSessionRunNote(run.run_id, {
            note_id: note.noteId, source_document_id: note.sourceDocumentId || undefined,
            source_path: note.sourcePath, context_kind: note.contextKind ?? "encounter",
            ...(note.contextKind === "general" ? {} : {
              encounter_name: note.encounterName, section_key: note.sectionKey,
              section_title: note.sectionTitle,
            }),
            text: note.text, captured_at: note.capturedAt,
          });
        }
        const refreshed = localNotes.some((item) => !remoteIds.has(item.noteId))
          ? await campaignClient.getOpenSessionRun() : run;
        if (!refreshed || cancelled) return;
        setSessionRun(refreshed);
        sessionRunRef.current = refreshed;
        const durableNotes = refreshed.notes.map((note): EncounterTableNote => ({
          contextKind: note.context_kind,
          noteId: note.note_id, sourceDocumentId: note.source_document_id ?? "",
          sourcePath: note.source_path, encounterName: note.encounter_name ?? "Session",
          sectionKey: note.section_key ?? "session-general",
          sectionTitle: note.section_title ?? "General note",
          text: note.text, capturedAt: note.captured_at, updatedAt: note.updated_at,
        }));
        setEncounterNotes((current) => {
          const merged = new Map(durableNotes.map((note) => [note.noteId, note]));
          current.forEach((note) => { if (!merged.has(note.noteId)) merged.set(note.noteId, note); });
          return chronologicalEncounterNotes(Array.from(merged.values()));
        });
        setTableNotesSyncError("");
      } catch (error) {
        if (!cancelled) setTableNotesSyncError(error instanceof Error ? error.message : "Session notes could not be restored");
      }
    })();
    return () => { cancelled = true; };
  }, [campaignClient]);
  useEffect(() => { setEncounterDossier(null); setEncounterDossierCollapsed(false); setEncounterDossierError(""); }, [selectedDocumentId]);
  useEffect(() => {
    if (!encounterDossier) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => { if (event.key === "Escape") setEncounterDossier(null); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [encounterDossier]);
  const [claimEdit, setClaimEdit] = useState<ClaimSnapshot | null>(null);
  const [claimEditDrafts, setClaimEditDrafts] = useState<ClaimReplacementDraft[]>([]);
  const [claimEditReason, setClaimEditReason] = useState("");
  const [claimEditMessage, setClaimEditMessage] = useState("");
  const [claimEditBusy, setClaimEditBusy] = useState(false);
  const [docLoading, setDocLoading] = useState(false);
  const [pcProfile, setPCProfile] = useState<PCProfile | null>(null);
  const [pcDraft, setPCDraft] = useState<PCProfile | null>(null);
  const [pcEditing, setPCEditing] = useState(false);
  const [pcPreview, setPCPreview] = useState(false);
  const [pcSaveKey, setPCSaveKey] = useState("");
  const [pcMessage, setPCMessage] = useState("");
  const [aiConfiguration, setAIConfiguration] = useState<AIConfigurationSnapshot | null>(null);
  const [selectedAIProfile, setSelectedAIProfile] = useState("");
  const [aiConfigurationError, setAIConfigurationError] = useState("");
  const [aiConfigurationBusy, setAIConfigurationBusy] = useState(false);

  useEffect(() => {
    if (activePage !== "tools") return;
    void campaignClient.getAIConfiguration().then((snapshot) => {
      setAIConfiguration(snapshot);
      setSelectedAIProfile(snapshot.active_profile_key);
      setAIConfigurationError("");
    }).catch((error) => setAIConfigurationError(error instanceof Error ? error.message : "AI configuration unavailable"));
  }, [activePage, campaignClient]);

  async function activateAIProfile() {
    if (!selectedAIProfile || selectedAIProfile === aiConfiguration?.active_profile_key) return;
    setAIConfigurationBusy(true);
    try {
      await campaignClient.activateAIProfile(selectedAIProfile);
      const snapshot = await campaignClient.getAIConfiguration();
      setAIConfiguration(snapshot);
      setSelectedAIProfile(snapshot.active_profile_key);
      setAIConfigurationError("");
    } catch (error) {
      setAIConfigurationError(error instanceof Error ? error.message : "AI profile activation failed");
    } finally {
      setAIConfigurationBusy(false);
    }
  }

  async function captureSessionNote() {
    if (!sessionCaptureDate || !sessionCaptureTitle.trim() || !sessionCaptureText.trim() || !inGameDate) return;
    setSessionCaptureBusy(true); setSessionCaptureError("");
    setSessionReviewComplete(null);
    try {
      const receipt = await campaignClient.captureSessionNote({
        session_date: sessionCaptureDate,
        in_game_date: (() => { const [year, month, day] = inGameDate.split("-").map(Number); return { calendar_id: "gregorian-ce", year, month, day }; })(),
        title: sessionCaptureTitle.trim(),
        text: sessionCaptureText,
        mentions: sessionMentions.flatMap((entity) => {
          const token = `@${entity.canonical_name}`;
          const found = [];
          let offset = sessionCaptureText.indexOf(token);
          while (offset >= 0) {
            found.push({ entity_id: entity.entity_id, display_name: entity.canonical_name, start_offset: offset, end_offset: offset + token.length });
            offset = sessionCaptureText.indexOf(token, offset + token.length);
          }
          return found;
        }),
        visibility: "dm_only",
        idempotency_key: `session-note:${sessionCaptureDate}:${crypto.randomUUID()}`,
        ...(sessionCaptureId ? { capture_id: sessionCaptureId } : {}),
      });
      setSessionCaptureId(receipt.capture_id);
      if (sessionCaptureTableNoteIds.length > 0) {
        const openRun = sessionRunRef.current;
        if (openRun) {
          await campaignClient.closeSessionRun(openRun.run_id, receipt.source_document_id, receipt.capture_id);
          sessionRunRef.current = null;
          setSessionRun(null);
        }
        const captured = new Set(sessionCaptureTableNoteIds);
        setEncounterNotes((current) => current.filter((note) => !captured.has(note.noteId)));
        setSessionCaptureTableNoteIds([]);
      }
      const detail = await campaignClient.getCandidate(receipt.candidate_id);
      const sourcePath = detail.evidence[0]?.source_path;
      const nextFilters: CandidateFilters = { status: "active", review_status: "pending", ...(sourcePath ? { source: sourcePath } : {}) };
      setFilters(nextFilters);
      setSessionCaptureOpen(false); setSessionCaptureTitle(""); setSessionCaptureText(""); setSessionCaptureId(null); setSessionMentions([]); setMentionQuery(null); setMentionMatches([]);
      const updatedDocuments = await campaignClient.listSourceDocuments();
      setSourceDocuments(updatedDocuments.items);
      setActivePage("migration");
      await loadReviewWorkspace(nextFilters, false);
      await chooseCandidate(receipt.candidate_id);
    } catch (error) {
      setSessionCaptureError(error instanceof Error ? error.message : "Session note could not be captured");
    } finally { setSessionCaptureBusy(false); }
  }

  useEffect(() => {
    if (mentionQuery === null) { setMentionMatches([]); return; }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const matches = await campaignClient.searchEntities(mentionQuery);
        if (!cancelled) {
          setMentionMatches(matches.filter((match) => ["pc", "npc", "location"].includes(match.entity_kind)).slice(0, 8));
          setMentionHighlight(0);
        }
      } catch { if (!cancelled) setMentionMatches([]); }
    }, 120);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [campaignClient, mentionQuery]);

  function positionMentionMenu(textarea: HTMLTextAreaElement) {
    const caret = textarea.selectionStart ?? textarea.value.length;
    const style = window.getComputedStyle(textarea);
    const mirror = document.createElement("div");
    const properties = ["fontFamily", "fontSize", "fontWeight", "fontStyle", "letterSpacing", "lineHeight", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth", "boxSizing", "whiteSpace", "wordBreak", "overflowWrap"] as const;
    mirror.style.position = "fixed";
    mirror.style.visibility = "hidden";
    mirror.style.pointerEvents = "none";
    mirror.style.width = `${textarea.clientWidth}px`;
    mirror.style.whiteSpace = "pre-wrap";
    mirror.style.overflowWrap = "break-word";
    properties.forEach((property) => { mirror.style[property] = style[property]; });
    mirror.textContent = textarea.value.slice(0, caret);
    const marker = document.createElement("span");
    marker.textContent = "\u200b";
    mirror.appendChild(marker);
    document.body.appendChild(mirror);
    const lineHeight = Number.parseFloat(style.lineHeight) || Number.parseFloat(style.fontSize) * 1.3 || 20;
    const left = Math.max(8, Math.min(textarea.clientWidth - 250, marker.offsetLeft - textarea.scrollLeft));
    const top = textarea.offsetTop + marker.offsetTop - textarea.scrollTop + lineHeight + 4;
    document.body.removeChild(mirror);
    setMentionMenuPosition({ left, top });
  }

  function updateSessionCaptureText(value: string, textarea: HTMLTextAreaElement) {
    setSessionCaptureText(value);
    const caret = textarea.selectionStart ?? value.length;
    const match = value.slice(0, caret).match(/(?:^|\s)@([^@\s]*)$/);
    setMentionQuery(match ? match[1] : null);
    if (match) positionMentionMenu(textarea);
  }

  function selectSessionMention(entity: EntityIdentity) {
    const textarea = sessionNotesRef.current;
    const caret = textarea?.selectionStart ?? sessionCaptureText.length;
    const before = sessionCaptureText.slice(0, caret);
    const match = before.match(/@([^@\s]*)$/);
    if (!match) return;
    const mentionStart = caret - match[0].length;
    const inserted = `@${entity.canonical_name} `;
    const nextText = sessionCaptureText.slice(0, mentionStart) + inserted + sessionCaptureText.slice(caret);
    const nextCaret = mentionStart + inserted.length;
    setSessionCaptureText(nextText);
    setSessionMentions((current) => current.some((item) => item.entity_id === entity.entity_id) ? current : [...current, entity]);
    setMentionQuery(null); setMentionMatches([]);
    window.setTimeout(() => {
      sessionNotesRef.current?.focus();
      sessionNotesRef.current?.setSelectionRange(nextCaret, nextCaret);
    }, 0);
  }

  function handleSessionNotesKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (mentionMatches.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setMentionHighlight((current) => (current + 1) % mentionMatches.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setMentionHighlight((current) => (current - 1 + mentionMatches.length) % mentionMatches.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      selectSessionMention(mentionMatches[mentionHighlight] ?? mentionMatches[0]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setMentionQuery(null); setMentionMatches([]);
    }
  }

  async function openSessionCapture(seed?: { title?: string; text?: string; tableNoteIds?: string[] }) {
    setSelectedPlan(null); setSessionCaptureId(null); setSessionCaptureError(""); setSessionCaptureOpen(true);
    setSessionCaptureTitle(seed?.title ?? "");
    setSessionCaptureText(seed?.text ?? "");
    setSessionMentions([]);
    setSessionCaptureTableNoteIds(seed?.tableNoteIds ?? []);
    try {
      const current = await campaignClient.getCurrentCampaignDate();
      if (current) {
        setInGameDate(`${String(current.year).padStart(4, "0")}-${String(current.month).padStart(2, "0")}-${String(current.day).padStart(2, "0")}`);
      }
    } catch (error) {
      setSessionCaptureError(error instanceof Error ? error.message : "Current in-game date is unavailable");
    }
  }

  function editSessionNote(note: SourceDocumentContent) {
    setSessionCaptureId(note.capture_id ?? null);
    setSessionCaptureDate(note.session_date ?? localCalendarDate());
    setSessionCaptureTitle(note.title ?? "");
    setSessionCaptureText(note.content);
    if (note.in_game_date) setInGameDate(`${String(note.in_game_date.year).padStart(4, "0")}-${String(note.in_game_date.month).padStart(2, "0")}-${String(note.in_game_date.day).padStart(2, "0")}`);
    setSessionMentions(Array.from(new Map((note.mentions ?? []).map((mention) => [mention.entity_id, {
      entity_id: mention.entity_id,
      canonical_name: mention.display_name,
      entity_kind: "npc" as EntityKind,
    }])).values()));
    setSelectedPlan(null);
    setSessionCaptureError("");
    setSessionCaptureTableNoteIds([]);
    setSessionCaptureOpen(true);
  }

  function openTableNoteComposer(context: EncounterNoteContext) {
    setTableNoteContext(context);
    setEditingTableNoteId(null);
    setTableNoteDraft("");
    setTableNotesOpen(true);
    window.setTimeout(() => tableNoteInputRef.current?.focus(), 0);
  }

  async function ensureSessionRun(note: EncounterTableNote): Promise<SessionRun> {
    if (sessionRunRef.current) return sessionRunRef.current;
    if (sessionRunOpening.current) return sessionRunOpening.current;
    sessionRunOpening.current = (async () => {
      const currentDate = await campaignClient.getCurrentCampaignDate().catch(() => null);
      const opened = await campaignClient.openSessionRun({
        session_date: localCalendarDate(),
        ...(currentDate ? { in_game_date: currentDate } : {}),
        title: note.encounterName || "Session notes",
      });
      sessionRunRef.current = opened;
      setSessionRun(opened);
      return opened;
    })();
    try { return await sessionRunOpening.current; }
    finally { sessionRunOpening.current = null; }
  }

  async function beginLiveSession(): Promise<SessionRun> {
    if (sessionRunRef.current) {
      setTableNotesOpen(true);
      setNewSessionMenuOpen(false);
      return sessionRunRef.current;
    }
    const currentDate = await campaignClient.getCurrentCampaignDate().catch(() => null);
    const opened = await campaignClient.openSessionRun({
      session_date: localCalendarDate(),
      ...(currentDate ? { in_game_date: currentDate } : {}),
      title: `Session ${localCalendarDate()}`,
    });
    sessionRunRef.current = opened;
    setSessionRun(opened);
    setTableNotesOpen(true);
    setNewSessionMenuOpen(false);
    return opened;
  }

  async function refreshEncounterProgress() {
    setEncounterProgress(await campaignClient.listEncounterProgress());
  }

  async function setEncounterLifecycle(
    sourceDocumentId: string,
    sourcePath: string,
    encounterName: string,
    status: EncounterLifecycle,
    checkpoint?: { key: string; title: string },
  ) {
    try {
      const updated = await campaignClient.updateEncounterProgress({
        source_document_id: sourceDocumentId,
        source_path: sourcePath,
        encounter_name: encounterName,
        status,
        ...(checkpoint ? { resume_section_key: checkpoint.key, resume_section_title: checkpoint.title } : {}),
        ...(sessionRunRef.current ? { session_run_id: sessionRunRef.current.run_id } : {}),
      });
      setEncounterProgress((current) => [...current.filter((item) => item.source_document_id !== updated.source_document_id), updated]);
      setTableNotesSyncError("");
    } catch (error) {
      setTableNotesSyncError(error instanceof Error ? error.message : "Encounter progress could not be saved");
    }
  }

  async function resumeEncounter(progress: EncounterProgress) {
    const run = await beginLiveSession();
    const updated = await campaignClient.updateEncounterProgress({
      source_document_id: progress.source_document_id,
      source_path: progress.source_path,
      encounter_name: progress.encounter_name,
      status: "in_progress",
      ...(progress.resume_section_key && progress.resume_section_title ? {
        resume_section_key: progress.resume_section_key,
        resume_section_title: progress.resume_section_title,
      } : {}),
      session_run_id: run.run_id,
    });
    setEncounterProgress((current) => [...current.filter((item) => item.source_document_id !== updated.source_document_id), updated]);
    setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null);
    setSelectedDocumentId(progress.source_document_id);
    await loadDocumentContent(progress.source_document_id, progress.source_path);
  }

  async function persistTableNote(note: EncounterTableNote) {
    try {
      const run = await ensureSessionRun(note);
      const saved = await campaignClient.saveSessionRunNote(run.run_id, {
        note_id: note.noteId, source_document_id: note.sourceDocumentId || undefined,
        source_path: note.sourcePath, context_kind: note.contextKind ?? "encounter",
        ...(note.contextKind === "general" ? {} : {
          encounter_name: note.encounterName, section_key: note.sectionKey,
          section_title: note.sectionTitle,
        }),
        text: note.text, captured_at: note.capturedAt,
      });
      const updated = { ...run, updated_at: saved.updated_at, notes: [...run.notes.filter((item) => item.note_id !== saved.note_id), saved] };
      sessionRunRef.current = updated;
      setSessionRun(updated);
      await refreshEncounterProgress();
      setTableNotesSyncError("");
    } catch (error) {
      setTableNotesSyncError(error instanceof Error ? error.message : "Table note was saved locally but could not be synced");
    }
  }

  function saveTableNote() {
    if (!tableNoteContext || !tableNoteDraft.trim()) return;
    const now = new Date().toISOString();
    let saved: EncounterTableNote;
    if (editingTableNoteId) {
      const existing = encounterNotes.find((note) => note.noteId === editingTableNoteId);
      if (!existing) return;
      saved = { ...existing, text: tableNoteDraft.trim(), updatedAt: now };
      setEncounterNotes((current) => current.map((note) => note.noteId === editingTableNoteId ? saved : note));
    } else {
      saved = { ...tableNoteContext, noteId: crypto.randomUUID(), text: tableNoteDraft.trim(), capturedAt: now, updatedAt: now };
      setEncounterNotes((current) => [...current, saved]);
    }
    setTableNoteContext(null); setEditingTableNoteId(null); setTableNoteDraft("");
    void persistTableNote(saved);
  }

  async function removeTableNote(note: EncounterTableNote) {
    setEncounterNotes((current) => current.filter((item) => item.noteId !== note.noteId));
    const run = sessionRunRef.current;
    if (!run) return;
    try {
      await campaignClient.deleteSessionRunNote(run.run_id, note.noteId);
      const updated = { ...run, notes: run.notes.filter((item) => item.note_id !== note.noteId) };
      sessionRunRef.current = updated;
      setSessionRun(updated);
      setTableNotesSyncError("");
    } catch (error) {
      setEncounterNotes((current) => chronologicalEncounterNotes([...current, note]));
      setTableNotesSyncError(error instanceof Error ? error.message : "Table note could not be removed");
    }
  }

  function editTableNote(note: EncounterTableNote) {
    setTableNoteContext(note);
    setEditingTableNoteId(note.noteId);
    setTableNoteDraft(note.text);
    setTableNotesOpen(true);
    window.setTimeout(() => tableNoteInputRef.current?.focus(), 0);
  }

  async function assembleTableNotesIntoSession() {
    const notes = chronologicalEncounterNotes(encounterNotes);
    const text = assembleEncounterNotes(notes);
    if (!text) return;
    const noteIds = notes.map((note) => note.noteId);
    setTableNotesOpen(false);
    if (tableNoteDestination === "new") {
      const encounterNames = Array.from(new Set(notes.filter((note) => note.contextKind !== "general").map((note) => note.encounterName)));
      await openSessionCapture({ title: encounterNames.length === 1 ? encounterNames[0] : "Session notes", text, tableNoteIds: noteIds });
      return;
    }
    setDocLoading(true);
    try {
      const note = await campaignClient.getSourceDocument(tableNoteDestination);
      editSessionNote(note);
      setSessionCaptureText([note.content.trim(), text].filter(Boolean).join("\n"));
      setSessionCaptureTableNoteIds(noteIds);
    } catch (error) {
      setSessionCaptureError(error instanceof Error ? error.message : "Session note could not be opened");
      setSessionCaptureOpen(true);
    } finally {
      setDocLoading(false);
    }
  }

  async function editSourceSessionDocument(document: SourceDocument) {
    setDocLoading(true);
    try {
      const note = await campaignClient.getSourceDocument(document.document_id);
      editSessionNote(note);
    } catch (error) {
      setSessionCaptureError(error instanceof Error ? error.message : "Session note could not be opened for editing");
    } finally {
      setDocLoading(false);
    }
  }

  async function openEncounterNpcDossier(npc: LibraryEntrySummary) {
    if (encounterDossier?.entry.entry_id === npc.entry_id) {
      setEncounterDossier(null);
      return;
    }
    setEncounterDossierLoading(true);
    setEncounterDossierCollapsed(false);
    setEncounterDossierError("");
    try {
      const entry = await campaignClient.getLibraryEntry(npc.entry_id);
      const source = entry.sources[0];
      let profile: CharacterDocument | null = null;
      if (source) {
        const document = await campaignClient.getSourceDocument(source.document_id);
        profile = characterDocument(document.content);
      }
      setEncounterDossier({ entry, profile, path: source?.path ?? "" });
    } catch (error) {
      setEncounterDossierError(error instanceof Error ? error.message : "NPC dossier could not be loaded");
    } finally {
      setEncounterDossierLoading(false);
    }
  }

  async function loadDocumentContent(documentId: string, path: string) {
    setDocLoading(true);
    try {
      const result = await campaignClient.getSourceDocument(documentId);
      setDocMetadata(result);
      setDocContent(result.content);
      setDocContentPath(path);
      setDocCanonicalClaims(result.canonical_claims ?? []);
      setDocClaimHistory(result.claim_history ?? []);
      setClaimEdit(null); setClaimEditMessage("");
      const parsed = characterDocument(result.content);
      if (parsed?.kind === "pc" || parsed?.kind === "npc") {
        const stored = await campaignClient.getPCProfile(documentId);
        const initial: PCProfile = stored ?? {
          document_id: documentId, source_revision_id: result.source_revision_id, version: 0,
          canonical_name: parsed.name, player: parsed.player, race: parsed.race,
          sex: parsed.sex, status: parsed.status ?? "active", aliases: parsed.aliases ?? [],
          background: parsed.background ?? "",
        };
        setPCProfile(initial); setPCDraft(initial);
      } else { setPCProfile(null); setPCDraft(null); }
      setPCEditing(false); setPCPreview(false); setPCSaveKey(""); setPCMessage("");
    } catch {
      setDocContent("Unable to load document content.");
    } finally {
      setDocLoading(false);
    }
  }

  async function loadCanonicalEntry(entryId: string) {
    setDocLoading(true);
    try {
      const entry = await campaignClient.getLibraryEntry(entryId);
      setSelectedEntry(entry);
      setSelectedPlan(null);
      const preferredRoot = ({ pc: "pcs/", npc: "npcs/", location: "locations/" } as Partial<Record<EntityKind, string>>)[entry.entity_kind];
      const source = entry.sources.find((item) => preferredRoot && item.path.toLocaleLowerCase().startsWith(preferredRoot)) ?? entry.sources[0];
      setDocCanonicalClaims(entry.claims);
      setDocClaimHistory(entry.claim_history ?? []);
      setClaimEdit(null); setClaimEditMessage("");
      if (source) {
        const result = await campaignClient.getSourceDocument(source.document_id);
        setDocMetadata(result);
        setSelectedDocumentId(source.document_id);
        setDocContent(result.content);
        setDocContentPath(source.path);
        const parsed = characterDocument(result.content);
        if (parsed?.kind === "pc" || parsed?.kind === "npc") {
          const stored = await campaignClient.getPCProfile(source.document_id);
          const initial: PCProfile = stored ?? { document_id: source.document_id, source_revision_id: result.source_revision_id, version: 0, canonical_name: entry.canonical_name, player: parsed.player, race: parsed.race, sex: parsed.sex, status: parsed.status ?? "active", aliases: entry.aliases, background: parsed.background ?? "" };
          setPCProfile(initial); setPCDraft(initial);
        } else { setPCProfile(null); setPCDraft(null); }
      } else {
        setDocMetadata(null);
        setSelectedDocumentId(null);
        setDocContent(`---\ntype: ${entry.entity_kind}\n---\n# ${entry.canonical_name}\n`);
        setDocContentPath("");
        setPCProfile(null); setPCDraft(null);
      }
      setPCEditing(false); setPCPreview(false); setPCSaveKey(""); setPCMessage("");
    } catch (error) {
      setSelectedEntry(null);
      setDocContent(error instanceof Error ? error.message : "Unable to load canonical entry.");
    } finally { setDocLoading(false); }
  }

  useEffect(() => {
    if (activePage === "documents" && selectedDocumentId && docContentPath) {
      void loadDocumentContent(selectedDocumentId, docContentPath);
    }
  }, [activePage]);

  async function savePCProfile() {
    const characterKind = characterDocument(docContent)?.kind;
    if (!pcDraft || !pcDraft.canonical_name.trim() || (characterKind === "pc" && !pcDraft.player?.trim())) return;
    try {
      const receipt = await campaignClient.updatePCProfile(pcDraft.document_id, {
        source_revision_id: pcDraft.source_revision_id, version: pcDraft.version,
        canonical_name: pcDraft.canonical_name.trim(), player: pcDraft.player?.trim() || undefined,
        race: pcDraft.race?.trim() || undefined, sex: pcDraft.sex?.trim() || undefined,
        status: pcDraft.status.trim(),
        aliases: pcDraft.aliases.map((value) => value.trim()).filter(Boolean),
        background: pcDraft.background,
        idempotency_key: pcSaveKey || `pc-profile:${pcDraft.document_id}:${pcDraft.version}:${crypto.randomUUID()}`,
      });
      const saved = { ...pcDraft, version: receipt.version };
      setPCProfile(saved); setPCDraft(saved); setPCEditing(false); setPCPreview(false); setPCSaveKey("");
      const sync = receipt.alias_sync;
      const syncCopy = !sync ? "" : ` Identity aliases ${sync.applied.length || sync.removed.length || sync.skipped_conflicting.length ? `for ${sync.entity_name}:` : `checked for ${sync.entity_name}; no changes.`}`
        + [sync.applied.length ? ` added ${sync.applied.join(", ")}` : "",
           sync.removed.length ? ` removed ${sync.removed.join(", ")}` : "",
           sync.skipped_conflicting.length ? ` skipped (owned by another identity): ${sync.skipped_conflicting.join(", ")}` : ""].filter(Boolean).join(";") + ".";
      setPCMessage(`Saved with receipt ${receipt.receipt_id}${syncCopy}`);
    } catch (error) { setPCMessage(error instanceof Error ? error.message : "PC profile could not be saved"); }
  }

  async function beginClaimEdit(claimId: string) {
    try {
      const claim = await campaignClient.getClaimSnapshot(claimId);
      const draft: ClaimReplacementDraft = {
        assertion_text: claim.assertion_text, state: claim.state, authority: claim.authority,
        visibility: claim.visibility, condition_text: claim.condition_text,
        effective_from: claim.effective_from, effective_until: claim.effective_until,
        expected: claim.expected, observed: claim.observed,
      };
      setClaimEdit(claim); setClaimEditDrafts([draft]); setClaimEditReason(""); setClaimEditMessage("");
    } catch (error) { setClaimEditMessage(error instanceof Error ? error.message : "Claim could not be loaded"); }
  }

  async function saveClaimCorrection() {
    if (!claimEdit || claimEditDrafts.some((draft) => !draft.assertion_text.trim()) || !claimEditReason.trim() || !selectedDocumentId) return;
    setClaimEditBusy(true);
    try {
      const receipt = await campaignClient.replaceClaim(claimEdit, claimEditDrafts.map((draft) => ({ ...draft, assertion_text: draft.assertion_text.trim(), condition_text: draft.condition_text?.trim() || undefined })), claimEditReason.trim());
      setClaimEdit(null); setClaimEditDrafts([]); setClaimEditReason("");
      if (selectedEntryId) await loadCanonicalEntry(selectedEntryId);
      else await loadDocumentContent(selectedDocumentId, docContentPath);
      setClaimEditMessage(`Claim corrected with receipt ${receipt.receipt_id}`);
    } catch (error) { setClaimEditMessage(error instanceof Error ? error.message : "Claim correction failed"); }
    finally { setClaimEditBusy(false); }
  }

  const pcChangedFields = !pcProfile || !pcDraft ? [] : [
    ["name", pcProfile.canonical_name !== pcDraft.canonical_name],
    ["player", pcProfile.player !== pcDraft.player],
    ["race", pcProfile.race !== pcDraft.race],
    ["sex", pcProfile.sex !== pcDraft.sex],
    ["status", pcProfile.status !== pcDraft.status],
    ["aliases", pcProfile.aliases.join("\n") !== pcDraft.aliases.join("\n")],
    ["background", pcProfile.background !== pcDraft.background],
  ].filter(([, changed]) => changed).map(([field]) => field as string);
  const directSessionReview = Boolean(selected?.extractor_version.startsWith("direct-input/session-note"));
  const sessionReviewActive = directSessionReview || Boolean(sessionReviewComplete);
  const directMentions = selected ? Array.from(new Map(
    selected.evidence.flatMap((evidence) => evidence.mentions ?? []).map((mention) => [mention.entity_id, mention]),
  ).values()) : [];
  const directPending = candidates.filter((candidate) => candidate.review_status === "pending");
  const directPosition = selected ? Math.max(1, directPending.findIndex((candidate) => candidate.candidate_id === selected.candidate_id) + 1) : 1;
  const closeoutNotes = chronologicalEncounterNotes(encounterNotes.filter((note) => sessionCaptureTableNoteIds.includes(note.noteId)));
  const closeoutEncounters = Array.from(new Map(closeoutNotes.filter((note) => note.contextKind !== "general").map((note) => [note.sourceDocumentId || note.sourcePath, note])).values());

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setActivePage("documents")} type="button" aria-label="DM Assistant home">
          <ArchiveMark />
          <span><strong>DM Assistant</strong><small>Campaign librarian</small></span>
        </button>
        <nav aria-label="Primary navigation">
          <button className={activePage === "documents" ? "active" : ""} onClick={() => setActivePage("documents")} type="button">Library</button>
          <button className={activePage === "brainstorm" ? "active" : ""} onClick={() => setActivePage("brainstorm")} type="button">Brainstorm</button>
          <button className={activePage === "migration" ? "active" : ""} onClick={() => setActivePage("migration")} type="button">Migration</button>
          <button className={activePage === "tools" ? "active" : ""} onClick={() => setActivePage("tools")} type="button">Tools</button>
        </nav>
        <div className="identity"><span>DM</span><b>Private archive</b></div>
      </header>

      {activePage === "documents" && (
      <main className="page-documents">
        <div className={`doc-layout ${libraryPanelCollapsed ? "library-collapsed" : ""}`}>
          <button aria-label={libraryPanelCollapsed ? "Expand Library" : "Collapse Library"} className="library-panel-handle" onClick={() => setLibraryPanelCollapsed((value) => !value)} title={libraryPanelCollapsed ? "Expand Library" : "Collapse Library"} type="button">{libraryPanelCollapsed ? "›" : "‹"}</button>
          <aside className={`doc-tree-panel ${libraryPanelCollapsed ? "collapsed" : ""}`} aria-label="Entry library">
            <div className="tree-header library-tree-header"><div><span>{libraryMode === "entries" ? "Campaign library" : "Source files"}</span></div><div className="library-header-actions"><div className="new-session-menu"><button aria-expanded={newSessionMenuOpen} aria-label="New session" className="new-session-note" onClick={() => { if (sessionRunRef.current) setTableNotesOpen(true); else setNewSessionMenuOpen((open) => !open); }} title={sessionRun ? "Open session" : "New session"} type="button">+</button>{newSessionMenuOpen && !sessionRun && <div role="menu"><button onClick={() => void beginLiveSession()} role="menuitem" type="button"><b>Start live session</b><span>Capture events as they happen</span></button><button onClick={() => { setNewSessionMenuOpen(false); void openSessionCapture(); }} role="menuitem" type="button"><b>Write session log directly</b><span>Enter a finished account for review</span></button></div>}</div><label className="source-mode-toggle"><span>Source</span><button aria-checked={libraryMode === "sources"} aria-label="Source view" onClick={() => setLibraryMode((mode) => mode === "sources" ? "entries" : "sources")} role="switch" type="button"><i /></button></label></div></div>
            <div className="tree-body">
              {sourceDocuments.length === 0 && reviewLoading && <p className="queue-empty">Loading…</p>}
              {libraryMode === "entries" && libraryEntries.length > 0 && Array.from(new Set(libraryEntries.map((entry) => entry.entity_kind))).map((kind) => <details className="canonical-entry-group" key={kind}><summary>{entryKindLabel(kind)}</summary><div>{libraryEntries.filter((entry) => entry.entity_kind === kind).map((entry) => <button className={`tree-doc canonical-entry-link ${selectedEntryId === entry.entry_id ? "selected" : ""}`} key={entry.entry_id} onClick={() => { setSelectedEntryId(entry.entry_id); void loadCanonicalEntry(entry.entry_id); }} type="button"><span className="tree-doc-name">{entry.canonical_name}</span></button>)}</div></details>)}
              {libraryMode === "entries" && libraryPlans.length > 0 && <details className="canonical-entry-group"><summary>Plans</summary><div>{libraryPlans.map((plan) => <button className={`tree-doc canonical-entry-link ${selectedPlan?.id === plan.id ? "selected" : ""}`} key={plan.id} onClick={() => { setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(plan); setDocContent(""); }} type="button"><span className="tree-doc-name">{plan.canonical_name}</span></button>)}</div></details>}
              {libraryMode === "entries" && sourceBackedLibraryDocuments.length > 0 && Array.from(new Set(sourceBackedLibraryDocuments.map((document) => pathEntryType(document.path)))).map((family) => <SourceBackedFamily documents={sourceBackedLibraryDocuments.filter((document) => pathEntryType(document.path) === family)} family={family} key={family} onEditSession={(document) => void editSourceSessionDocument(document)} onSelect={(document) => { setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null); setSelectedDocumentId(document.document_id); void loadDocumentContent(document.document_id, document.path); }} selectedDocumentId={selectedDocumentId} />)}
              {(libraryMode === "sources" || libraryEntries.length === 0) && <>{libraryMode === "sources" && <p className="tree-explainer">Immutable imported evidence, organized by source path.</p>}{Object.entries(buildDocTree(sourceDocuments)).map(([dir, children]) => (
                <TreeDir key={dir} name={dir} depth={0} children_={children} expanded={expandedDirs} setExpanded={setExpandedDirs} selectedDocumentId={selectedDocumentId} sourceMode={libraryMode === "sources"} onSelect={(docId) => { const doc = sourceDocuments.find((d) => d.document_id === docId); if (doc) { setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null); setSelectedDocumentId(docId); void loadDocumentContent(docId, doc.path); } }} />
              ))}</>}
            </div>
          </aside>
          <section className={`doc-content-panel ${encounterDossier ? (encounterDossierCollapsed ? "dossier-collapsed" : "dossier-open") : ""}`} aria-label="Document content">
            {sessionCaptureOpen && closeoutNotes.length > 0 && <section aria-label="Session closeout context" className="session-closeout-context"><header><div><span>Session context</span><b>{closeoutNotes.length} timeline note{closeoutNotes.length === 1 ? "" : "s"}</b></div><button className="text-button" onClick={() => setTableNotesOpen(true)} type="button">Review timeline</button></header>{closeoutEncounters.length > 0 ? <div>{closeoutEncounters.map((note) => { const progress = encounterProgress.find((item) => item.source_document_id === note.sourceDocumentId); return <article key={note.sourceDocumentId || note.sourcePath}><b>{note.encounterName}</b><span>{progress?.resume_section_title ? `Resume at ${progress.resume_section_title}` : progress?.status === "completed" ? "Completed" : progress?.status === "abandoned" ? "Abandoned" : "No resume point saved"}</span></article>; })}</div> : <p>These notes occurred outside a prepared encounter.</p>}<small>Encounter and resume labels stay with the session run. Only the editable note text becomes source evidence.</small></section>}
            {sessionCaptureOpen ? <article className="document-view session-note-capture"><header><b>{sessionCaptureId ? "Edit session note" : "New session note"}</b><span>{sessionCaptureId ? "Corrected revision" : "Direct input"}</span></header><section className="character-content"><p>Capture manicured notes from actual play. The submitted text is preserved as immutable evidence before review.</p><div className="form-grid"><label>Session date<input aria-label="Session date" type="date" value={sessionCaptureDate} onChange={(event) => setSessionCaptureDate(event.target.value)} /></label><label>Title<input aria-label="Session note title" placeholder="Return to the Monastery" value={sessionCaptureTitle} onChange={(event) => setSessionCaptureTitle(event.target.value)} /></label></div><fieldset className="campaign-date-fields"><legend>In-game date</legend><p>This becomes the default campaign date for the next session note.</p><label>Campaign date (CE)<input aria-label="In-game date" type="date" value={inGameDate} onChange={(event) => setInGameDate(event.target.value)} /></label></fieldset><label className="pc-background-field session-notes-field">Notes<textarea ref={sessionNotesRef} aria-label="Session notes" placeholder="Enter one reviewable event or statement per line. Type @ to link a character or location." rows={18} value={sessionCaptureText} onChange={(event) => updateSessionCaptureText(event.target.value, event.currentTarget)} onKeyDown={handleSessionNotesKeyDown} />{mentionMatches.length > 0 && <div className="mention-suggestions" style={mentionMenuPosition} role="listbox" aria-label="Entity mentions">{mentionMatches.map((entity, index) => <button className={index === mentionHighlight ? "active" : ""} aria-selected={index === mentionHighlight} key={entity.entity_id} onMouseDown={(event) => event.preventDefault()} onClick={() => selectSessionMention(entity)} role="option" type="button"><b>{entity.canonical_name}</b><span>{display(entity.entity_kind)}</span></button>)}</div>}</label>{sessionMentions.length > 0 && <div className="mention-chips" aria-label="Linked records">{sessionMentions.map((entity) => <span key={entity.entity_id}>@{entity.canonical_name}<small>{display(entity.entity_kind)}</small></span>)}</div>}{sessionCaptureError && <div className="notice error" role="alert">{sessionCaptureError}</div>}<div className="step-actions"><button className="text-button" disabled={sessionCaptureBusy} onClick={() => { setSessionCaptureOpen(false); setSessionCaptureTableNoteIds([]); }} type="button">Cancel</button><button disabled={sessionCaptureBusy || !sessionCaptureDate || !inGameDate || !sessionCaptureTitle.trim() || !sessionCaptureText.trim()} onClick={() => void captureSessionNote()} type="button">{sessionCaptureBusy ? "Saving…" : sessionCaptureId ? "Save revision and review" : "Capture and review"}</button></div></section></article>
              : selectedPlan ? <PlanEntryView plan={selectedPlan} /> : docLoading ? <p className="queue-empty">Loading document…</p>
              : docContent ? (docMetadata?.document_type === "session_note" ? <><SessionNoteEntryView note={docMetadata} claims={docCanonicalClaims} history={docClaimHistory} onEditClaim={(claimId) => void beginClaimEdit(claimId)} onEdit={() => editSessionNote(docMetadata)} />{claimEdit && <ClaimReplacementEditor drafts={claimEditDrafts} busy={claimEditBusy} reason={claimEditReason} onChange={setClaimEditDrafts} onReasonChange={setClaimEditReason} onCancel={() => setClaimEdit(null)} onSave={() => void saveClaimCorrection()} />}{claimEditMessage && <div className="notice" role="status">{claimEditMessage}</div>}</> : characterDocument(docContent) ?
                <>{pcProfile && !pcEditing
                  ? <><CharacterDocumentView path={docContentPath} sources={selectedEntry?.sources ?? []} profile={{ ...characterDocument(docContent)!, name: pcProfile.canonical_name, player: pcProfile.player, race: pcProfile.race, sex: pcProfile.sex, status: pcProfile.status, background: pcProfile.background, aliases: pcProfile.aliases }} dmClaims={docCanonicalClaims} claimHistory={docClaimHistory} onEditClaim={(claimId) => void beginClaimEdit(claimId)} onEdit={() => { setPCDraft(pcProfile); setPCEditing(true); setPCPreview(false); setPCSaveKey(""); setPCMessage(""); }} />{claimEdit && <ClaimReplacementEditor drafts={claimEditDrafts} busy={claimEditBusy} reason={claimEditReason} onChange={setClaimEditDrafts} onReasonChange={setClaimEditReason} onCancel={() => setClaimEdit(null)} onSave={() => void saveClaimCorrection()} />}{claimEditMessage && <div className="notice" role="status">{claimEditMessage}</div>}</>
                  : pcDraft && pcEditing ? <CharacterProfileEditor profile={pcDraft} kind={characterDocument(docContent)?.kind ?? "npc"} changedFields={pcChangedFields} preview={pcPreview} onChange={setPCDraft} onCancel={() => { setPCEditing(false); setPCPreview(false); setPCSaveKey(""); setPCDraft(pcProfile); }} onReview={() => { const prefix = characterDocument(docContent)?.kind === "pc" ? "pc-profile" : "character-profile"; setPCSaveKey((current) => current || `${prefix}:${pcDraft.document_id}:${pcDraft.version}:${crypto.randomUUID()}`); setPCPreview(true); }} onSave={() => void savePCProfile()} />
                  : <CharacterDocumentView path={docContentPath} sources={selectedEntry?.sources ?? []} profile={characterDocument(docContent)!} dmClaims={docCanonicalClaims} claimHistory={docClaimHistory} onEditClaim={(claimId) => void beginClaimEdit(claimId)} />}{pcMessage && <div className="notice" role="status">{pcMessage}</div>}</>
                : <>{parseEntry(docContent).type === "encounter" ? <EncounterEntryView entry={parseEntry(docContent)} path={docContentPath} sourceDocumentId={docMetadata?.document_id ?? selectedDocumentId ?? ""} claims={docCanonicalClaims} history={docClaimHistory} sources={selectedEntry?.sources ?? []} npcEntries={libraryEntries.filter((entry) => entry.entity_kind === "npc")} noteCounts={new Map(Array.from(encounterNotes.filter((note) => note.sourceDocumentId === (docMetadata?.document_id ?? selectedDocumentId)).reduce((counts, note) => counts.set(note.sectionKey, (counts.get(note.sectionKey) ?? 0) + 1), new Map<string, number>()).entries()))} onOpenNpc={(npc) => void openEncounterNpcDossier(npc)} onAddNote={openTableNoteComposer} onOpenNotes={() => setTableNotesOpen(true)} onEditClaim={(claimId) => void beginClaimEdit(claimId)} />
                : <StructuredEntryView entry={parseEntry(docContent)} path={docContentPath} claims={docCanonicalClaims} history={docClaimHistory} sources={selectedEntry?.sources ?? []} onEditClaim={(claimId) => void beginClaimEdit(claimId)} />}{claimEdit && <ClaimReplacementEditor drafts={claimEditDrafts} busy={claimEditBusy} reason={claimEditReason} onChange={setClaimEditDrafts} onReasonChange={setClaimEditReason} onCancel={() => setClaimEdit(null)} onSave={() => void saveClaimCorrection()} />}{claimEditMessage && <div className="notice" role="status">{claimEditMessage}</div>}</>
              ) : <div className="detail-empty">Select an entry from the library.</div>}
            {encounterDossierLoading && <div className="npc-dossier-loading" role="status">Loading NPC dossier…</div>}
            {encounterDossierError && <div className="npc-dossier-error" role="alert">{encounterDossierError}<button onClick={() => setEncounterDossierError("")} type="button">Dismiss</button></div>}
            {encounterDossier && <NpcDossierDrawer dossier={encounterDossier} collapsed={encounterDossierCollapsed} initialScroll={dossierScrollPositions.current.get(encounterDossier.entry.entry_id) ?? 0} onScroll={(position) => dossierScrollPositions.current.set(encounterDossier.entry.entry_id, position)} onToggleCollapsed={() => setEncounterDossierCollapsed((value) => !value)} onClose={() => setEncounterDossier(null)} onOpenFull={() => { const entryId = encounterDossier.entry.entry_id; setEncounterDossier(null); setSelectedDocumentId(null); setSelectedPlan(null); setSelectedEntryId(entryId); void loadCanonicalEntry(entryId); }} />}
            {!tableNotesOpen && (sessionRun || encounterNotes.length > 0) && <button className="table-notes-launcher" onClick={() => setTableNotesOpen(true)} type="button"><RecordIcon kind="note" /><span>Open session</span>{encounterNotes.length > 0 && <b>{encounterNotes.length}</b>}</button>}
            {tableNotesOpen && <aside aria-label="Session table notes" className="table-notes-panel">
              <header><div><span>{sessionRun ? `Open session · ${sessionRun.session_date}` : "Session timeline"}</span><h2>Table notes</h2></div><div className="table-notes-header-actions"><button onClick={() => openTableNoteComposer(generalSessionNoteContext())} type="button">+ General note</button><button aria-label="Close table notes" onClick={() => { setTableNotesOpen(false); setTableNoteContext(null); setEditingTableNoteId(null); setTableNoteDraft(""); }} type="button">×</button></div></header>
              {tableNotesSyncError && <div className="notice error" role="alert">Saved in this browser. Durable sync failed: {tableNotesSyncError}</div>}
              {tableNoteContext && <section className="table-note-composer"><span>{tableNoteContext.contextKind === "general" ? "Outside an encounter" : tableNoteContext.encounterName}</span><h3>{tableNoteContext.sectionTitle}</h3><textarea aria-label="Table note" onChange={(event) => setTableNoteDraft(event.target.value)} onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); saveTableNote(); } }} placeholder="What happened at the table?" ref={tableNoteInputRef} rows={4} value={tableNoteDraft} /><div><button className="text-button" onClick={() => { setTableNoteContext(null); setEditingTableNoteId(null); setTableNoteDraft(""); }} type="button">Cancel</button><button disabled={!tableNoteDraft.trim()} onClick={saveTableNote} type="button">{editingTableNoteId ? "Save note" : "Add to timeline"}</button></div><small>Ctrl+Enter saves. Context is retained without changing the claim text.</small></section>}
              {encounterProgress.filter((item) => item.status === "in_progress").length > 0 && <section className="unfinished-encounters" aria-label="Unfinished encounters"><span>Unfinished encounters</span>{encounterProgress.filter((item) => item.status === "in_progress").map((item) => <article key={item.source_document_id}><div><b>{item.encounter_name}</b>{item.resume_section_title && <small>Resume at {item.resume_section_title}</small>}</div><div><button onClick={() => void resumeEncounter(item)} type="button">Resume</button><button onClick={() => void setEncounterLifecycle(item.source_document_id, item.source_path, item.encounter_name, "completed")} type="button">Complete</button><button className="text-button" onClick={() => void setEncounterLifecycle(item.source_document_id, item.source_path, item.encounter_name, "abandoned")} type="button">Abandon</button></div></article>)}</section>}
              <div className="table-notes-timeline">{chronologicalEncounterNotes(encounterNotes).length === 0 ? <p className="empty-section">No table notes yet. Add a general note or use a note icon in an encounter.</p> : chronologicalEncounterNotes(encounterNotes).map((note) => <article key={note.noteId}><time dateTime={note.capturedAt}>{new Date(note.capturedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time><div><span>{note.contextKind === "general" ? "General session note" : `${note.encounterName} · ${note.sectionTitle}`}</span><p>{note.text}</p>{note.contextKind !== "general" && note.sourceDocumentId && <button className="resume-checkpoint" onClick={() => void setEncounterLifecycle(note.sourceDocumentId, note.sourcePath, note.encounterName, "in_progress", { key: note.sectionKey, title: note.sectionTitle })} type="button">Resume here next session</button>}</div><div className="table-note-actions"><button aria-label={`Edit note from ${note.sectionTitle}`} onClick={() => editTableNote(note)} title="Edit note" type="button"><RecordIcon kind="edit" /></button><button aria-label={`Remove note from ${note.sectionTitle}`} onClick={() => void removeTableNote(note)} title="Remove note" type="button">×</button></div></article>)}</div>
              {encounterNotes.length > 0 && <footer><label>Add chronologically to<select aria-label="Session note destination" onChange={(event) => setTableNoteDestination(event.target.value)} value={tableNoteDestination}><option value="new">A new session note</option>{editableSessionDocuments.map((document) => <option key={document.document_id} value={document.document_id}>{document.session_date ? `${document.session_date} — ` : ""}{document.title ?? entryLabel(document.path)}</option>)}</select></label><button onClick={() => void assembleTableNotesIntoSession()} type="button">Continue in session note</button></footer>}
            </aside>}
          </section>
        </div>

        <details className="ask-panel">
          <summary>Ask the archive</summary>
          <section className="hero">
            <form className="ask-box" onSubmit={ask}>
              <div className="ask-row">
                <SearchIcon />
              <textarea id="campaign-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What do the records establish about…" rows={2} />
              <button disabled={!question.trim() || queryState === "loading"} type="submit">{queryState === "loading" ? "Searching…" : "Search records"}</button>
            </div>
            <div className="ask-meta"><span>Visibility</span><b>Dungeon Master</b><span className="dot" />No creative inference</div>
          </form>
        </section>

        <section aria-live="polite" className="result-region">
          {queryState === "error" && <div className="notice error"><b>Campaign Core is unavailable.</b><span>{queryError}</span></div>}
          {!result && queryState !== "error" && <div className="empty-state"><div className="empty-glyph"><SearchIcon /></div><div><b>Your evidence will appear here</b><span>Ask a question to inspect canonical records and cited context.</span></div></div>}
          {result && modeCopy && <article className={`answer-card mode-${result.answer_mode}`}><header><div><p>{modeCopy.eyebrow}</p><h2>{modeCopy.title}</h2></div><span>{result.evidence.length} evidence item{result.evidence.length === 1 ? "" : "s"}</span></header>{result.evidence.length === 0 ? <p className="no-evidence">No visible authoritative record supports an answer. Nothing was invented.</p> : <div className="evidence-list">{result.evidence.map((item) => <div className="evidence" key={item.record_id}><span className={`role role-${item.role}`}>{item.role}</span><p>{item.assertion}</p><dl><div><dt>Authority</dt><dd>{display(item.authority)}</dd></div><div><dt>State</dt><dd>{item.state}</dd></div></dl><cite>{item.citation}</cite></div>)}</div>}<footer>{result.reasons.map(display).join(" · ")}</footer></article>}
        </section>
        </details>
      </main>
      )}

      {activePage === "brainstorm" && <BrainstormWorkspace campaignClient={campaignClient} onReviewProposal={async (created) => {
        const firstCandidateId = created.items[0]?.evidence.candidate_id;
        if (!firstCandidateId) return;
        setReviewState({ selectedCandidateId: firstCandidateId, phase: "proposal_pending", proposal: created, message: "Brainstorm promotion proposal is ready for exact review." });
        setSelectedItemIds(created.items.map((item) => item.item_id));
        setProposalValidated(true);
        setActivePage("migration");
        await chooseCandidate(firstCandidateId);
      }} />}

      {activePage === "migration" && (
      <main className="page-migration">
        {sessionReviewActive ? <nav aria-label="Session review progress" className="session-review-progress"><b>Review session statements</b><span>{sessionReviewComplete ? "Complete" : `${directPosition} of ${directPending.length} pending`}</span></nav> : <nav aria-label="Migration progress" className="migration-progress">
          {MIGRATION_STEPS.map((label, index) => {
            const step = (index + 1) as MigrationStep;
            return <button aria-current={migrationStep === step ? "step" : undefined} className={migrationStep === step ? "active" : migrationStep > step ? "complete" : ""} disabled={step > migrationStep || proposalBlocksSelection} key={label} onClick={() => setMigrationStep(step)} type="button"><span>{step}</span>{label}</button>;
          })}
        </nav>}{(batchNotice || (!sessionReviewActive && (extractionNotice || extractionJob))) && <div className="batch-notice" role="status"><span>{batchNotice || extractionNotice || "Background extraction running."}</span>{!sessionReviewActive && extractionJob && <small>{display(extractionJob.state)} · {displayedExtractionJob.jobId.slice(0, 12)}</small>}</div>}<div className={`doc-layout ${sessionReviewActive ? "session-review-layout" : ""}`}>
          {!sessionReviewActive && <aside className="doc-tree-panel" aria-label="Document tree">
            <div className="tree-header"><span>Documents</span><b>{sourceDocuments.length} files</b></div>
            {activeRun && <div className="run-summary-compact" aria-label="Import run summary"><span>{activeRun.admitted_file_count} files</span><span>{activeRun.candidate_count} candidates</span><span>{activeRun.review_count} reviews</span></div>}
            <div className="migration-filters"><label>Review status<select aria-label="Review status" value={filters.review_status ?? ""} onChange={(event) => { const next = { ...filters, review_status: event.target.value || undefined }; setFilters(next); void loadReviewWorkspace(next); }}><option value="">Any status</option><option value="pending">Pending</option><option value="proposed">Proposed</option><option value="deferred">Deferred</option><option value="rejected">Rejected</option><option value="applied">Applied</option></select></label></div>
            <div className="tree-body">
              {Object.entries(buildDocTree(sourceDocuments)).map(([dir, children]) => (
                <TreeDir key={dir} name={dir} depth={0} children_={children} expanded={expandedDirs} setExpanded={setExpandedDirs} selectedDocumentId={selectedDocumentId} onSelect={(docId) => { const doc = sourceDocuments.find((d) => d.document_id === docId); setSelectedDocumentId(docId); setSelected(null); setCandidates([]); setExtractionDrafts([]); setExtractionNotice(""); setBatchNotice(""); setMigrationStep(1); const next = { ...filters, source: doc?.path, review_status: undefined }; setFilters(next); void loadReviewWorkspace(next, false); }} />
              ))}
            </div>
            <section className="background-tasks" aria-label="Background tasks">
              <header><span>Background Tasks</span><b>{extractionPending ? "1 active" : "0 active"}</b></header>
              {!displayedExtractionJob ? <p>No extraction tasks yet.</p> : <article className={`task-${displayedExtractionJob.state}`}>
                <div><span>AI extraction</span><b>{display(displayedExtractionJob.state)}</b></div>
                <code title={displayedExtractionJob.jobId}>{displayedExtractionJob.jobId.slice(0, 12)}</code>
                <div className="task-progress"><span style={{ width: `${displayedExtractionJob.progress}%` }} /></div>
                {["queued", "running"].includes(displayedExtractionJob.state) && <small>{displayedExtractionJob.state === "queued" ? "Waiting for worker" : `${displayedExtractionJob.progress}% complete`}{displayedExtractionJob.totalItems ? ` · ${displayedExtractionJob.totalItems} candidate${displayedExtractionJob.totalItems === 1 ? "" : "s"}` : ""}</small>}
                {extractionPending && <button className="task-cancel" disabled={cancelBusy} onClick={() => void cancelExtraction()} type="button">{cancelBusy ? "Cancelling…" : "Cancel extraction"}</button>}
                {displayedExtractionJob.state === "succeeded" && <small>{(() => { const results = (displayedExtractionJob.result as { results?: Array<{ ok: boolean }> } | undefined)?.results ?? []; const succeeded = results.filter((result) => result.ok).length; return `${succeeded} completed · ${results.length - succeeded} failed`; })()}</small>}
                {displayedExtractionJob.error && <small>{displayedExtractionJob.error}</small>}
                {!extractionPending && (displayedExtractionJob.state === "failed" || ((displayedExtractionJob.result as { results?: Array<{ ok: boolean }> } | undefined)?.results ?? []).some((result) => !result.ok)) && <button className="task-retry" onClick={() => void retryFailedExtraction()} type="button">Retry failed extraction</button>}
              </article>}
              {extractionTaskError && <div className="task-error" role="alert"><span>{extractionTaskError}</span><button aria-label="Dismiss extraction error" onClick={() => setExtractionTaskError("")} type="button">Dismiss</button></div>}
            </section>
          </aside>}
          <section className="doc-content-panel" aria-label="Migration workspace">
            {sessionReviewComplete ? <section className="session-review-complete" aria-label="Session review complete"><span>Session note complete</span><h2>Every statement has been reviewed.</h2><p>The claims were applied with their original note evidence and campaign date.</p><small>Final receipt {sessionReviewComplete.receiptId}</small><div className="step-actions"><button className="text-button" onClick={() => { setSessionReviewComplete(null); setActivePage("documents"); setSelectedDocumentId(sessionReviewComplete.sourceDocumentId); void loadDocumentContent(sessionReviewComplete.sourceDocumentId, sessionReviewComplete.sourcePath); }} type="button">View session note</button><button onClick={() => { setSessionReviewComplete(null); setActivePage("documents"); void openSessionCapture(); }} type="button">Capture another session note</button></div></section> : migrationStep === 1 ? <div className="detail-empty batch-start"><span>{selectedDocumentId ? "Review one candidate, or prepare every pending candidate in this document." : "Select a document to narrow the queue, then select a candidate."}</span>{selectedDocumentId && candidates.some((candidate) => candidate.review_status === "pending") && <button disabled={batchBusy || extractionPending} onClick={() => void extractPendingSequence()} type="button">{extractionPending ? "Extraction job running" : batchBusy ? "Queueing sequence…" : "Extract pending candidates"}</button>}</div> : !selected ? <div className="detail-empty">Select a candidate to review.</div> : (
              <div className={`candidate-detail migration-detail ${directSessionReview ? "direct-session-review" : ""}`}>
                {reviewError && <div className="notice error persistent-review-error" role="alert"><b>Claim was not committed.</b><span>{reviewError}</span><button className="text-button" onClick={() => setReviewError("")} type="button">Dismiss</button></div>}
                <header className="candidate-title"><div><span className={`status-pill status-${selected.review_status}`}>{display(selected.review_status)}</span><h3>{selected.assertion_text}</h3></div>{!directSessionReview && <dl><div><dt>State</dt><dd>{display(selected.state)}</dd></div><div><dt>Authority</dt><dd>{display(selected.authority)}</dd></div><div><dt>Visibility</dt><dd>{display(selected.visibility)}</dd></div></dl>}</header>
                {selected.evidence.map((evidence) => directSessionReview ? <details className="source-evidence compact-evidence" key={evidence.source_revision_id}><summary>Evidence details</summary><blockquote>{evidence.excerpt}</blockquote><dl><div><dt>Source</dt><dd>{evidence.source_path}</dd></div><div><dt>Section</dt><dd>{evidence.section}</dd></div><div><dt>Offsets</dt><dd>{evidence.start_offset}–{evidence.end_offset}</dd></div><div><dt>Revision</dt><dd title={evidence.content_hash}>{evidence.content_hash.slice(0, 12)}</dd></div></dl></details> : <article className="source-evidence" key={evidence.source_revision_id}><div><span>Exact source evidence</span><b>{evidence.source_path}</b></div><blockquote>{evidence.excerpt}</blockquote><dl><div><dt>Section</dt><dd>{evidence.section}</dd></div><div><dt>Classification</dt><dd>{display(evidence.classification)}</dd></div><div><dt>Offsets</dt><dd>{evidence.start_offset}–{evidence.end_offset}</dd></div><div><dt>Revision</dt><dd title={evidence.content_hash}>{evidence.content_hash.slice(0, 12)}</dd></div></dl></article>)}
                {[2, 3].includes(migrationStep) && selected.review_status === "pending" && !proposalBelongsToSelected && <section className={`resolution-form ${directSessionReview ? "session-claim-review" : ""}`} aria-label="Provenance-first proposal"><header><span>{directSessionReview ? "Review statement" : "Promote this assertion"}</span><p>{directSessionReview ? "Correct the claim if needed, then commit it and continue to the next statement." : "Edit the canonical wording and truth dimensions. The exact imported text remains unchanged below as provenance."}</p></header>{splitClaims ? <section className="split-claim-editor" aria-label="Split claims"><header><span>Split claims</span><p>Each entry will become its own claim with the same source evidence and campaign date.</p></header>{splitClaims.map((claim, index) => <div className="split-claim-row" key={index}><label>Claim {index + 1}<textarea aria-label={`Split claim ${index + 1}`} value={claim} onChange={(event) => setSplitClaims((prior) => prior?.map((value, itemIndex) => itemIndex === index ? event.target.value : value) ?? null)} /></label><button className="text-button" disabled={splitClaims.length <= 1} onClick={() => setSplitClaims((prior) => prior?.filter((_value, itemIndex) => itemIndex !== index) ?? null)} type="button">Remove</button></div>)}<div className="step-actions"><button className="text-button" onClick={() => setSplitClaims((prior) => [...(prior ?? []), ""])} type="button">Add claim</button><button className="text-button" onClick={() => setSplitClaims(null)} type="button">Cancel split</button></div></section> : <label>Canonical assertion<textarea aria-label="Canonical assertion" value={provenanceAssertion} onChange={(event) => setProvenanceAssertion(event.target.value)} /></label>}{directSessionReview && !splitClaims && <button className="text-button" onClick={beginClaimSplit} type="button">Split into claims</button>}{directMentions.length > 0 && <div className="candidate-mentions"><span>Related records</span>{directMentions.map((mention) => <b key={mention.entity_id}>@{mention.display_name}</b>)}<small>These records will be linked to every claim; no subject role is inferred.</small></div>}{directSessionReview ? <label>Observed campaign date<input aria-label="Observed campaign date" required type="date" value={observedCampaignDate} onChange={(event) => setObservedCampaignDate(event.target.value)} /></label> : <><div className="form-grid"><label>State<select aria-label="Canonical assertion state" value={provenanceState} onChange={(event) => { setProvenanceState(event.target.value); if (event.target.value === "possible") { setConditionEnabled(false); setConditionText(""); } }}><option value="observed">Observed</option><option value="established">Established</option><option value="intended">Intended</option><option value="prepared">Prepared</option><option value="possible">Possible</option></select></label><label>Authority<select aria-label="Canonical assertion authority" value={provenanceAuthority} onChange={(event) => setProvenanceAuthority(event.target.value)}><option value="real_play">Real play</option><option value="explicit_lore">Explicit lore</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option><option value="unclassified">Unclassified</option></select></label><label>Visibility<select aria-label="Canonical assertion visibility" value={provenanceVisibility} onChange={(event) => setProvenanceVisibility(event.target.value)}><option value="dm_only">DM only</option><option value="party">Party</option><option value="character">Character</option></select></label></div>{provenanceState === "observed" && <label>Observed campaign year<input aria-label="Observed campaign year" required type="number" value={observedAt} onChange={(event) => setObservedAt(event.target.value)} /></label>}{provenanceState !== "possible" && <fieldset><label><input checked={conditionEnabled} onChange={(event) => { setConditionEnabled(event.target.checked); if (!event.target.checked) setConditionText(""); }} type="checkbox" />Has a concrete prerequisite</label></fieldset>}{conditionEnabled && provenanceState !== "possible" && <label>Condition trigger<input aria-label="Condition trigger" placeholder="The concrete event that activates this consequence" value={conditionText} onChange={(event) => setConditionText(event.target.value)} /></label>}</>}<div className="step-actions">{directSessionReview && <button className="text-button" disabled={reviewBusy || !dispositionReason.trim()} onClick={() => void disposition("deferred")} type="button">Skip with reason</button>}<button disabled={reviewBusy || (splitClaims ? !splitClaims.some((claim) => claim.trim()) : !provenanceAssertion.trim()) || (directSessionReview ? !observedCampaignDate : (provenanceState === "observed" && !observedAt)) || (conditionEnabled && provenanceState !== "possible" && !conditionText.trim())} onClick={() => void (directSessionReview ? commitDirectInputClaim() : createProvenanceFirstProposal())} type="button">{directSessionReview ? `Commit ${splitClaims ? splitClaims.filter((claim) => claim.trim()).length : 1} claim${splitClaims && splitClaims.filter((claim) => claim.trim()).length !== 1 ? "s" : ""} and continue` : "Create source-backed proposal"}</button></div>{directSessionReview && <input aria-label="Skip reason" value={dispositionReason} onChange={(event) => setDispositionReason(event.target.value)} placeholder="Reason required only when skipping" />}</section>}
                {migrationStep === 2 && selected.review_status === "pending" && <div className="extraction-actions"><button className="text-button" disabled={extractionPending || proposalBlocksSelection} onClick={() => void runExtraction(selected.candidate_id)} type="button">{extractionPending ? "Extraction job running" : (selected.extractions && selected.extractions.length > 0 ? "Re-extract this candidate" : "Extract this candidate")}</button>{candidates.filter((candidate) => candidate.review_status === "pending").length > 1 && <button className="text-button" disabled={batchBusy || extractionPending || proposalBlocksSelection} onClick={() => void extractPendingSequence()} type="button">{`Extract all ${Math.min(50, candidates.filter((candidate) => candidate.review_status === "pending").length)} pending candidates`}</button>}</div>}
                {migrationStep === 3 && selected.extraction_segments && selected.extraction_segments.length > 0 && <section className="extraction-coverage" aria-label="Extraction coverage"><header><span>Source coverage</span><b>{selected.extraction_segments.filter((segment) => segment.disposition !== "unaccounted").length} / {selected.extraction_segments.length} accounted for</b></header>{selected.extraction_segments.some((segment) => segment.disposition !== "extracted") ? <div>{selected.extraction_segments.filter((segment) => segment.disposition !== "extracted").map((segment) => <article key={segment.segment_id}><div><b>{segment.segment_id}</b><span>{display(segment.disposition)}</span></div><p>{segment.text}</p></article>)}</div> : <p>Every source segment is represented by extracted claims.</p>}</section>}
                {!directSessionReview && migrationStep === 3 && extractionDrafts.length > 0 && <AssertionFirstReview drafts={extractionDrafts} setDrafts={setExtractionDrafts} onBack={() => setMigrationStep(2)} onAbandon={abandonExtraction} onContinue={(subject) => void prepareSubjectGroups(subject)} />}
                {!directSessionReview && migrationStep === 3 && extractionDrafts.length > 0 && <section className="extraction-editor" aria-label="Editable extraction review"><header><span>Review extracted claims</span><p>All grounded claims are grouped here. Correct mistakes or exclude a claim, then continue once.</p></header><div className="extraction-draft-list">{extractionDrafts.map((draft, index) => <article className={draft.included ? "extraction-draft" : "extraction-draft excluded"} key={draft.extractionId}><label className="include-extraction"><input checked={draft.included} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, included: event.target.checked } : item))} type="checkbox" />Include claim {index + 1}</label><div className="form-grid"><label>Subject<input aria-label={`Extraction ${index + 1} subject`} value={draft.subject} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, subject: event.target.value } : item))} /></label><label>Predicate<input aria-label={`Extraction ${index + 1} predicate`} value={draft.predicate} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, predicate: event.target.value } : item))} /></label><label>Object<input aria-label={`Extraction ${index + 1} object`} value={draft.objectEntity} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, objectEntity: event.target.value } : item))} /></label><label>State<select aria-label={`Extraction ${index + 1} state`} value={draft.state} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, state: event.target.value } : item))}><option value="observed">Observed</option><option value="established">Established</option><option value="intended">Intended</option><option value="prepared">Prepared</option><option value="possible">Possible</option></select></label><label>Authority<select aria-label={`Extraction ${index + 1} authority`} value={draft.authority} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, authority: event.target.value } : item))}><option value="real_play">Real play</option><option value="explicit_lore">Explicit lore</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option><option value="unclassified">Unclassified</option></select></label><label>Visibility<select aria-label={`Extraction ${index + 1} visibility`} value={draft.visibility} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, visibility: event.target.value } : item))}><option value="dm_only">DM only</option><option value="party">Party</option><option value="character">Character</option></select></label></div></article>)}</div><p className="extraction-note">Object text remains review context; a canonical object relationship requires an explicit entity identity.</p><div className="step-actions"><button className="danger-button" onClick={abandonExtraction} type="button">Abandon extraction</button><button className="text-button" onClick={() => setMigrationStep(2)} type="button">Back to candidate</button><button disabled={!extractionDrafts.some((draft) => draft.included && draft.subject.trim() && draft.predicate.trim())} onClick={() => { const first = extractionDrafts.find((draft) => draft.included); setEntityName(first?.subject.trim() ?? ""); setMigrationStep(4); }} type="button">Continue with selected claims</button></div></section>}
                {migrationStep === 2 && selectedReviews.length > 0 && <details className="diagnostics"><summary>Warnings and conflicts ({selectedReviews.length})</summary>{selectedReviews.map((review) => <div key={review.review_id}><span>{display(review.kind)}</span><p>{reviewSummary(review)}</p></div>)}</details>}
                {migrationStep === 2 && !proposalBelongsToSelected && !["rejected", "deferred", "applied"].includes(reviewState.phase) && <div className="candidate-actions"><div><label htmlFor="disposition-reason">Disposition reason</label><input id="disposition-reason" value={dispositionReason} onChange={(event) => setDispositionReason(event.target.value)} placeholder="Required audit reason" /></div><button className="text-button" disabled={!dispositionReason.trim() || reviewBusy} onClick={() => void disposition("deferred")} type="button">Defer</button><button className="danger-button" disabled={!dispositionReason.trim() || reviewBusy} onClick={() => void disposition("rejected")} type="button">Reject</button></div>}
                {!directSessionReview && migrationStep === 3 && extractionDrafts.length > 0 && <section className="extraction-evidence-list" aria-label="Extraction evidence">{extractionDrafts.map((draft, index) => <article key={draft.extractionId}><header><b>Claim {index + 1} evidence</b><span>{Math.round(Number(draft.confidence) * 100)}% extraction confidence</span></header><p>{draft.assertionText}</p><blockquote>{draft.supportingExcerpt}</blockquote></article>)}</section>}
                {migrationStep === 4 && Object.keys(additionalSubjectTargets).length > 0 && <section className="subject-group-resolutions" aria-label="Additional subject identities"><header><span>Additional principal subjects</span><p>Each subject receives its own canonical target.</p></header>{Object.entries(additionalSubjectTargets).map(([key, target]) => <article key={key}><b>{extractionDrafts.find((draft) => subjectKey(draft.subject) === key)?.subject}</b><fieldset><label><input checked={target.mode === "new"} name={`target-${key}`} onChange={() => setAdditionalSubjectTargets((prior) => ({ ...prior, [key]: { ...target, mode: "new", entityId: "" } }))} type="radio" />Create entity</label><label><input checked={target.mode === "existing"} name={`target-${key}`} onChange={() => setAdditionalSubjectTargets((prior) => ({ ...prior, [key]: { ...target, mode: "existing" } }))} type="radio" />Existing entity</label></fieldset>{target.mode === "new" ? <div className="form-grid"><label>Canonical name<input aria-label={`${key} canonical name`} value={target.canonicalName} onChange={(event) => setAdditionalSubjectTargets((prior) => ({ ...prior, [key]: { ...target, canonicalName: event.target.value } }))} /></label><label>Entity kind<select aria-label={`${key} entity kind`} value={target.entityKind} onChange={(event) => setAdditionalSubjectTargets((prior) => ({ ...prior, [key]: { ...target, entityKind: event.target.value as EntityKind } }))}>{entityKinds.map((kind) => <option key={kind.kind} value={kind.kind}>{kind.label}</option>)}</select></label></div> : <label>Existing entity ID<input aria-label={`${key} existing entity ID`} value={target.entityId} onChange={(event) => setAdditionalSubjectTargets((prior) => ({ ...prior, [key]: { ...target, entityId: event.target.value } }))} /></label>}</article>)}</section>}
                {migrationStep === 4 && !proposalBelongsToSelected && selected.review_status === "pending" && extractionDrafts.some((draft) => draft.included) && <form className="resolution-form" onSubmit={createProposal}>
                  <header><span>Grouped proposal draft</span><p>One identity decision and all selected claims will be proposed together with their original provenance.</p></header>
                  <section className="proposal-draft-list" aria-label="Corrected extraction proposal">{extractionDrafts.filter((draft) => draft.included).map((draft, index) => <article className="proposal-draft-summary" key={draft.extractionId}><div><span>Claim</span><b>{index + 1}</b></div><div><span>Subject</span><b>{draft.subject}</b></div><div><span>Predicate</span><b>{draft.predicate}</b></div><div><span>Object</span><b>{draft.objectEntity || "No entity relationship"}</b></div><div><span>State</span><b>{display(draft.state)}</b></div><div><span>Authority / visibility</span><b>{display(draft.authority)} · {display(draft.visibility)}</b></div></article>)}</section>
                  <fieldset><legend>Subject identity</legend><label><input checked={resolution === "new"} name="resolution" onChange={() => { setResolution("new"); setSubjectId(""); }} type="radio" />Create a new entity</label><label><input checked={resolution === "existing"} name="resolution" onChange={() => setResolution("existing")} type="radio" />Use an existing entity</label></fieldset>
                  <section className="entity-match-list" aria-label="Matching existing entities"><span>{entityLookupBusy ? "Searching existing identities…" : entityMatches.length ? "Existing identities found" : "No matching identity found"}</span>{entityMatches.map((match) => <button className={resolution === "existing" && subjectId === match.entity_id ? "selected" : ""} key={match.entity_id} onClick={() => { setResolution("existing"); setSubjectId(match.entity_id); setEntityKind(match.entity_kind); }} type="button"><b>{match.canonical_name}</b><small>{display(match.entity_kind)} · {match.entity_id}</small></button>)}</section>
                  {resolution === "new" ? <>
                    <div className="form-grid">
                      <label>Canonical name<input aria-label="Canonical name" required value={entityName} onChange={(event) => setEntityName(event.target.value)} /></label>
                      <label>Entity kind<select aria-label="Entity kind" required value={entityKind} onChange={(event) => setEntityKind(event.target.value as EntityKind)}>{entityKinds.map((kind) => <option key={kind.kind} value={kind.kind}>{kind.label}</option>)}</select></label>
                    </div>
                    <p className="kind-guidance">{entityKinds.find((kind) => kind.kind === entityKind)?.description}</p>
                    <div className="tag-control">
                      <button aria-expanded={tagsExpanded} className="text-button" onClick={() => setTagsExpanded(!tagsExpanded)} type="button">{tagsExpanded ? "Hide tags" : "Add tags (optional)"}</button>
                      {selectedTags.length > 0 && <div className="selected-tags" aria-label="Selected tags">{selectedTags.map((tag) => <button aria-label={`Remove ${tag} tag`} key={tag} onClick={() => setSelectedTags(selectedTags.filter((item) => item !== tag))} type="button">{tag} ×</button>)}</div>}
                      {tagsExpanded && <div className="tag-expansion"><div className="tag-options">{availableTags.map((tag) => <label key={tag}><input checked={selectedTags.includes(tag)} onChange={() => selectedTags.includes(tag) ? setSelectedTags(selectedTags.filter((item) => item !== tag)) : addTag(tag)} type="checkbox" />{tag}</label>)}</div><div className="new-tag"><input aria-label="New tag" list="known-tags" maxLength={64} placeholder="New tag" value={tagDraft} onChange={(event) => setTagDraft(event.target.value)} /><datalist id="known-tags">{availableTags.map((tag) => <option key={tag} value={tag} />)}</datalist><button className="text-button" disabled={!tagDraft.trim() || selectedTags.includes(tagDraft.trim().toLocaleLowerCase())} onClick={() => addTag(tagDraft)} type="button">Add explicit tag</button></div></div>}
                    </div>
                  </> : <label>Existing entity ID<input aria-label="Existing entity ID" pattern="[0-9a-fA-F-]{36}" required value={subjectId} onChange={(event) => setSubjectId(event.target.value)} /></label>}
                  {extractionDrafts.some((draft) => draft.included && draft.state === "observed") && <label>Observed campaign year<input aria-label="Observed campaign year" required type="number" value={observedAt} onChange={(event) => setObservedAt(event.target.value)} /></label>}
                  <div className="step-actions"><button className="text-button" onClick={() => setMigrationStep(3)} type="button">Back to extraction</button><button disabled={reviewBusy || (resolution === "new" ? !entityName.trim() : !subjectId.trim()) || (extractionDrafts.some((draft) => draft.included && draft.state === "observed") && !observedAt)} type="submit">Create grouped proposal</button></div>
                </form>}
                {migrationStep === 5 && proposal && <ProposalReview proposal={proposal} selectedItemIds={selectedItemIds} setSelectedItemIds={setSelectedItemIds} />}
                {migrationStep === 5 && proposal && reviewState.phase === "proposal_pending" && !claimCorrection && proposal.items.some((item) => item.mutation_kind === "create_claim") && <div className="proposal-correction-action"><button className="text-button" onClick={() => { const claim = proposal.items.find((item) => item.mutation_kind === "create_claim")!; setClaimCorrection({ assertion_text: String(claim.after.assertion_text ?? ""), state: String(claim.after.state), authority: String(claim.after.authority), visibility: String(claim.after.visibility), is_conditional: Boolean(claim.after.is_conditional), predicts_subject_action: Boolean(claim.after.predicts_subject_action), condition_text: String(claim.after.condition_text ?? "") }); }} type="button">Correct claim before approval</button></div>}
                {migrationStep === 5 && claimCorrection?.is_conditional && <label className="condition-trigger-field">Condition trigger<input aria-label="Corrected condition trigger" placeholder="The concrete event that activates this consequence" value={claimCorrection.condition_text} onChange={(event) => setClaimCorrection({ ...claimCorrection, condition_text: event.target.value })} /></label>}
                {migrationStep === 5 && proposal && claimCorrection && <section className="resolution-form proposal-correction" aria-label="Correct pending claim"><header><span>New immutable proposal version</span><p>The evidence remains unchanged. Saving replaces no history and invalidates approval of the displayed version.</p></header><label>Assertion<textarea aria-label="Corrected assertion" value={claimCorrection.assertion_text} onChange={(event) => setClaimCorrection({ ...claimCorrection, assertion_text: event.target.value })} /></label><div className="form-grid"><label>State<select aria-label="Corrected state" value={claimCorrection.state} onChange={(event) => { const state = event.target.value; const authority = ({ observed: "real_play", established: "explicit_lore", intended: "npc_intention", prepared: "preparation", possible: "brainstorm" } as Record<string, string>)[state]; setClaimCorrection({ ...claimCorrection, state, authority }); }}><option value="observed">Observed</option><option value="established">Established</option><option value="intended">Intended</option><option value="prepared">Prepared</option><option value="possible">Possible</option></select></label><label>Authority<select aria-label="Corrected authority" value={claimCorrection.authority} onChange={(event) => setClaimCorrection({ ...claimCorrection, authority: event.target.value })}><option value="real_play">Real play</option><option value="explicit_lore">Explicit lore</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option></select></label><label>Visibility<select aria-label="Corrected visibility" value={claimCorrection.visibility} onChange={(event) => setClaimCorrection({ ...claimCorrection, visibility: event.target.value })}><option value="dm_only">DM only</option><option value="party">Party</option><option value="character">Character</option></select></label></div><fieldset><label><input checked={claimCorrection.is_conditional} onChange={(event) => setClaimCorrection({ ...claimCorrection, is_conditional: event.target.checked })} type="checkbox" />Conditional</label><label><input checked={claimCorrection.predicts_subject_action} onChange={(event) => setClaimCorrection({ ...claimCorrection, predicts_subject_action: event.target.checked })} type="checkbox" />Predicts subject action</label></fieldset><div className="step-actions"><button className="text-button" onClick={() => setClaimCorrection(null)} type="button">Cancel correction</button><button disabled={reviewBusy || !claimCorrection.assertion_text.trim()} onClick={() => void reviseClaimProposal()} type="button">Save as new version</button></div></section>}
                {migrationStep === 5 && proposal && !proposalValidated && <div className="notice"><b>{proposalValidationError ? "Confirmation failed." : "Revalidating displayed version."}</b><span>{proposalValidationError || "Approval and application remain locked until Campaign Core confirms the immutable version."}</span><button className="secondary-button" disabled={reviewBusy} onClick={() => void confirmProposalVersion(proposal)} type="button">Retry confirmation</button></div>}
                {migrationStep === 5 && proposal && reviewState.phase === "proposal_pending" && !claimCorrection && <div className="confirmation-panel" role="region" aria-label="Pending proposal confirmation"><div><span>Visible pending action</span><b>Approve and apply selected items from version {proposal.version_number}</b><code>{proposal.content_hash}</code></div><button disabled={!proposalValidated || selectedItemIds.length === 0 || reviewBusy} onClick={() => void approveAndApplyProposal()} type="button">Approve and apply {selectedItemIds.length} exact item{selectedItemIds.length === 1 ? "" : "s"}</button></div>}
                {migrationStep === 6 && reviewState.phase === "approved" && <div className="apply-panel"><div><span>Approval recorded</span><b>{reviewState.approval?.approval_id}</b><p>Only the displayed version and selected scope can be applied.</p></div><button disabled={!proposalValidated || reviewBusy} onClick={() => void applyApproval()} type="button">Apply approved change</button></div>}
                {reviewState.phase !== "idle" && !(reviewState.phase === "proposal_pending" && !proposalValidated) && <div className={`review-outcome outcome-${reviewState.phase}`} role="status"><b>{phaseLabel(reviewState)}</b>{reviewState.message && <span>{reviewState.message}</span>}{reviewState.receipt && <dl><div><dt>Receipt</dt><dd>{reviewState.receipt.receipt_id}</dd></div><div><dt>Outcome</dt><dd>{reviewState.receipt.outcome}</dd></div><div><dt>Applied items</dt><dd>{reviewState.receipt.applied_item_ids.length}</dd></div></dl>}</div>}
              </div>
            )}
            {candidates.length > 0 && (
              <div className="migration-queue">
                <header><span>Candidates</span><b>{reviewLoading ? "Loading…" : `${candidates.length} shown`}</b></header>
                {candidates.map((candidate) => <button className={candidate.candidate_id === selected?.candidate_id ? "selected" : ""} disabled={reviewBusy || (proposalBlocksSelection && candidate.review_status !== "proposed" && reviewState.selectedCandidateId !== candidate.candidate_id)} key={candidate.candidate_id} onClick={() => void chooseCandidate(candidate.candidate_id)} type="button"><span>{display(candidate.authority)} · {display(candidate.state)}</span><b>{candidate.assertion_text}</b><small>{display(candidate.review_status)}</small></button>)}
              </div>
            )}
          </section>
        </div>
      </main>
      )}

      {activePage === "tools" && (
      <main>
        <section className="ai-settings" aria-label="AI model settings">
          <div className="section-heading"><div><p className="kicker">Controlled provider configuration</p><h2>AI model</h2></div><p>Campaign Core owns activation. Provider credentials never enter the browser.</p></div>
          {aiConfigurationError && <div className="notice error" role="alert">{aiConfigurationError}</div>}
          {aiConfiguration && <div className="ai-settings-grid"><article><label>Extraction profile<select aria-label="Extraction model profile" value={selectedAIProfile} onChange={(event) => setSelectedAIProfile(event.target.value)}>{aiConfiguration.profiles.map((profile) => <option disabled={!profile.selectable} key={profile.key} value={profile.key}>{profile.model_slug} — {profile.suitability}</option>)}</select></label>{(() => { const profile = aiConfiguration.profiles.find((item) => item.key === selectedAIProfile); return profile ? <dl><div><dt>Provider</dt><dd>{profile.provider}</dd></div><div><dt>Reasoning</dt><dd>{profile.reasoning_effort ?? "none"}</dd></div><div><dt>Output limit</dt><dd>{profile.max_tokens}</dd></div><div><dt>Timeout</dt><dd>{profile.timeout_seconds}s</dd></div><div><dt>Retries</dt><dd>{profile.retry_limit}</dd></div></dl> : null; })()}<button disabled={aiConfigurationBusy || selectedAIProfile === aiConfiguration.active_profile_key} onClick={() => void activateAIProfile()} type="button">{aiConfigurationBusy ? "Activating…" : "Activate profile"}</button></article><article><header><span>Prompt</span><b>{aiConfiguration.prompt_version}</b></header><pre>{aiConfiguration.prompt_text}</pre></article></div>}
        </section>
        <section className="hero" id="ask">
          <p className="kicker">Starfall campaign records</p>
          <h1>Ask the archive.<br /><i>Keep the evidence.</i></h1>
          <p className="intro">Grounded answers only—every result carries its source, authority, and truth state.</p>
          <form className="ask-box" onSubmit={ask}>
            <label htmlFor="campaign-question">Campaign question</label>
            <div className="ask-row">
              <SearchIcon />
              <textarea id="campaign-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What do the records establish about…" rows={2} />
              <button disabled={!question.trim() || queryState === "loading"} type="submit">{queryState === "loading" ? "Searching…" : "Search records"}</button>
            </div>
            <div className="ask-meta"><span>Visibility</span><b>Dungeon Master</b><span className="dot" />No creative inference</div>
          </form>
        </section>

        <section aria-live="polite" className="result-region">
          {queryState === "error" && <div className="notice error"><b>Campaign Core is unavailable.</b><span>{queryError}</span></div>}
          {!result && queryState !== "error" && <div className="empty-state"><div className="empty-glyph"><SearchIcon /></div><div><b>Your evidence will appear here</b><span>Ask a question to inspect canonical records and cited context.</span></div></div>}
          {result && modeCopy && <article className={`answer-card mode-${result.answer_mode}`}><header><div><p>{modeCopy.eyebrow}</p><h2>{modeCopy.title}</h2></div><span>{result.evidence.length} evidence item{result.evidence.length === 1 ? "" : "s"}</span></header>{result.evidence.length === 0 ? <p className="no-evidence">No visible authoritative record supports an answer. Nothing was invented.</p> : <div className="evidence-list">{result.evidence.map((item) => <div className="evidence" key={item.record_id}><span className={`role role-${item.role}`}>{item.role}</span><p>{item.assertion}</p><dl><div><dt>Authority</dt><dd>{display(item.authority)}</dd></div><div><dt>State</dt><dd>{item.state}</dd></div></dl><cite>{item.citation}</cite></div>)}</div>}<footer>{result.reasons.map(display).join(" · ")}</footer></article>}
        </section>

        {sourceReviews.length > 0 && <section className="operations source-reviews-tool" aria-label="Source reviews"><div className="section-heading"><div><p className="kicker">Import maintenance</p><h2>Source Reviews</h2></div><p>Source-level quarantine and unresolved-reference work lives outside the migration workflow.</p></div><div className="source-review-queue"><header><span>Open source reviews</span><b>{sourceReviews.length} open · {quarantineCount} quarantined</b></header>{sourceReviews.slice(0, 20).map((review) => <article key={review.review_id}><span>{display(review.kind)} · {display(review.classification ?? "unclassified")}</span><b>{review.source_path ?? review.subject_id}</b><p>{reviewSummary(review)}</p></article>)}</div></section>}

        <section className="operations identity-review-tool" aria-label="Identity review">
          <div className="section-heading"><div><p className="kicker">Identity maintenance</p><h2>Identity Review</h2></div><p>Names that recur in current claims but resolve to no identity. Detection is automatic; every decision is yours and recorded. Nothing merges automatically.</p></div>
          <div className="identity-queue" data-testid="identity-queue">
            <header><span>Unresolved surfaces</span><button className="secondary-button" disabled={identityBusy} onClick={() => void loadIdentityGaps()}>{identityBusy ? "Working…" : identityGaps === null ? "Review identities" : "Refresh"}</button></header>
            {identityMessage && <p role="status">{identityMessage}</p>}
            {identityGaps !== null && identityGaps.length === 0 && <p className="identity-empty">No unresolved surfaces right now.</p>}
            {identityGaps?.slice(0, 20).map((gap) => <article key={gap.normalized_surface} className="identity-gap">
              <div className="identity-gap-main"><b>{gap.surface}</b><span>{gap.retrieval_demand > 0 && <>{gap.retrieval_demand} lookup miss{gap.retrieval_demand === 1 ? "" : "es"} · </>}{gap.claims_with_phrase} claim{gap.claims_with_phrase === 1 ? "" : "s"} · {gap.total_mentions} mention{gap.total_mentions === 1 ? "" : "s"}</span></div>
              {gap.evidence[0] && <p className="identity-evidence">“{gap.evidence[0].excerpt}”</p>}
              {gap.role_hint && <p className="identity-role-hint">Ends like a role or title you have marked before.</p>}
              {gap.related_surfaces.length > 0 && <fieldset className="identity-related"><legend>Merge these related surfaces as aliases?</legend>{gap.related_surfaces.map((surface) => <label key={surface}><input checked={(identityAliasSelection[gap.normalized_surface] ?? []).includes(surface)} onChange={(event) => setIdentityAliasSelection((current) => ({ ...current, [gap.normalized_surface]: event.target.checked ? [...(current[gap.normalized_surface] ?? []), surface] : (current[gap.normalized_surface] ?? []).filter((item) => item !== surface) }))} type="checkbox" />{surface}</label>)}</fieldset>}
              {gap.alias_candidates.length > 0 && <div className="identity-alias-candidates">{gap.alias_candidates.map((candidate) => <button key={candidate.entity_id} type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.addIdentityAlias(gap.surface, candidate.entity_id, `identity-alias:${gap.normalized_surface}:${candidate.entity_id}:${Date.now()}`), `Aliased “${gap.surface}” to ${candidate.canonical_name}`)}>Alias → {candidate.canonical_name}</button>)}</div>}
              <div className="identity-actions">
                <label>Kind<select aria-label={`Entity kind for ${gap.surface}`} value={identityKinds[gap.normalized_surface] ?? "faction"} onChange={(event) => setIdentityKinds((current) => ({ ...current, [gap.normalized_surface]: event.target.value }))}>{["faction", "worldbuilding", "location", "npc", "item", "event"].map((kind) => <option key={kind} value={kind}>{display(kind)}</option>)}</select></label>
                <button type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.createIdentityEntity(gap.surface, identityKinds[gap.normalized_surface] ?? "faction", `identity-create:${gap.normalized_surface}:${Date.now()}`, identityAliasSelection[gap.normalized_surface] ?? []), `Created ${gap.surface} as an identity${(identityAliasSelection[gap.normalized_surface] ?? []).length ? ` with ${(identityAliasSelection[gap.normalized_surface] ?? []).length} alias${(identityAliasSelection[gap.normalized_surface] ?? []).length === 1 ? "" : "es"}` : ""}`)}>{(identityAliasSelection[gap.normalized_surface] ?? []).length ? `Create with ${(identityAliasSelection[gap.normalized_surface] ?? []).length} alias${(identityAliasSelection[gap.normalized_surface] ?? []).length === 1 ? "" : "es"}` : "Create entity"}</button>
                <button className="text-button" type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.markIdentityRole(gap.surface, `identity-role:${gap.normalized_surface}:${Date.now()}`), `Marked “${gap.surface}” as a role or title`)}>Mark as role</button>
                <button className="text-button" type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.dismissIdentityGap(gap.surface, `identity-dismiss:${gap.normalized_surface}:${Date.now()}`), `Dismissed “${gap.surface}”`)}>Dismiss</button>
              </div>
            </article>)}
          </div>
        </section>

        <ClaimReconciliationWorkspace campaignClient={campaignClient} />
        <PlanWorkspace campaignClient={campaignClient} />

        <section className="operations" id="operations"><div className="section-heading"><div><p className="kicker">Infrastructure</p><h2>Operations</h2></div><p>Background work remains visible and recoverable after refresh.</p></div><article className="operation-card"><div className="operation-icon"><PulseIcon /></div><div className="operation-copy"><span>Campaign Core</span><h3>Service health check</h3><p>Runs through the isolated Windmill job adapter. No campaign database credential crosses this boundary.</p>{job && <div className={`job-status status-${job.state}`} role="status"><div><b>{JOB_COPY[job.state]}</b><span>{job.jobId.slice(0, 12)}</span></div><div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div>{job.error && <p>{job.error}</p>}</div>}{jobActionError && <p className="inline-error">Status unavailable: {jobActionError}</p>}</div><button className="secondary-button" disabled={Boolean(isPending)} onClick={startHealthCheck} type="button">{isPending ? "Checking…" : job?.state === "failed" ? "Retry check" : "Run check"}</button></article></section>
      </main>
      )}
      <footer className="page-footer"><span>Private campaign workspace</span></footer>
    </div>
  );
}

interface BrainstormPromotionDraft {
  included: boolean;
  assertion: string;
  subjectEntityId: string;
  state: "established" | "intended" | "prepared" | "possible";
}

const BRAINSTORM_SEARCH_STOP_WORDS = new Set([
  "about", "after", "and", "are", "for", "from", "how", "into", "that", "the", "this", "was", "were", "what", "when", "where", "which", "who", "with",
]);

function brainstormSearchTerms(value: string): string[] {
  return [...new Set(value.toLocaleLowerCase().replace(/[^a-z0-9]+/g, " ").split(/\s+/)
    .filter((term) => term.length > 2 && !BRAINSTORM_SEARCH_STOP_WORDS.has(term)))];
}

function rankBrainstormEvidence(evidence: RetrievalResult["evidence"], query: string): RetrievalResult["evidence"] {
  const terms = brainstormSearchTerms(query);
  if (!terms.length) return [];
  return evidence
    .map((item) => {
      const haystack = `${item.assertion} ${item.citation}`.toLocaleLowerCase().replace(/[^a-z0-9]+/g, " ");
      const matches = terms.filter((term) => haystack.includes(term)).length;
      const exactBonus = haystack.includes(terms.join(" ")) ? terms.length * 2 : 0;
      // Graph context may be relevant without repeating the query's words.
      const graphBonus = item.graph_trace?.length ? terms.length * 30 : 0;
      return { item, score: matches * 10 + exactBonus + graphBonus };
    })
    .filter(({ score }) => score >= Math.max(10, Math.ceil(terms.length * 0.3) * 10))
    .sort((left, right) => right.score - left.score)
    .slice(0, 10)
    .map(({ item }) => item);
}

function brainstormEvidenceExcerpt(assertion: string, terms: string[], expanded: boolean): string {
  if (expanded || assertion.length <= 520) return assertion;
  const normalized = assertion.toLocaleLowerCase();
  const firstMatch = terms.reduce((earliest, term) => {
    const index = normalized.indexOf(term);
    return index >= 0 && (earliest < 0 || index < earliest) ? index : earliest;
  }, -1);
  const anchor = firstMatch >= 0 ? firstMatch : 0;
  let start = Math.max(0, anchor - 150);
  let end = Math.min(assertion.length, Math.max(anchor + 300, start + 480));
  if (start > 0) {
    const nextSpace = assertion.indexOf(" ", start);
    if (nextSpace >= 0 && nextSpace < anchor) start = nextSpace + 1;
  }
  if (end < assertion.length) {
    const previousSpace = assertion.lastIndexOf(" ", end);
    if (previousSpace > anchor) end = previousSpace;
  }
  return `${start > 0 ? "…" : ""}${assertion.slice(start, end).trim()}${end < assertion.length ? "…" : ""}`;
}

function highlightBrainstormTerms(text: string, terms: string[]): ReactNode[] {
  if (!terms.length) return [text];
  const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(pattern).filter(Boolean).map((part, index) =>
    terms.some((term) => part.toLocaleLowerCase() === term)
      ? <mark key={`${index}-${part}`}>{part}</mark>
      : part,
  );
}

function BrainstormWorkspace({ campaignClient, onReviewProposal }: {
  campaignClient: CampaignClient;
  onReviewProposal: (proposal: CandidateProposalVersion) => Promise<void>;
}) {
  const [session, setSession] = useState<BrainstormSession | null>(null);
  const [entries, setEntries] = useState<LibraryEntrySummary[]>([]);
  const [title, setTitle] = useState("");
  const [thought, setThought] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drafts, setDrafts] = useState<Record<string, BrainstormPromotionDraft>>({});
  const [proposal, setProposal] = useState<CandidateProposalVersion | null>(null);
  const [linkedEntities, setLinkedEntities] = useState<EntityIdentity[]>([]);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionMatches, setMentionMatches] = useState<EntityIdentity[]>([]);
  const [mentionHighlight, setMentionHighlight] = useState(0);
  const [mentionPosition, setMentionPosition] = useState({ left: 12, top: 44 });
  const [search, setSearch] = useState("");
  const [contentEvidence, setContentEvidence] = useState<RetrievalResult["evidence"]>([]);
  const [contentSearchLoading, setContentSearchLoading] = useState(false);
  const [contentSearchError, setContentSearchError] = useState("");
  const [dossier, setDossier] = useState<LibraryEntry | null>(null);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<Set<string>>(new Set());
  const thoughtRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([campaignClient.getOpenBrainstorm(), campaignClient.listLibraryEntries()])
      .then(([open, availableEntries]) => {
        if (cancelled) return;
        setSession(open);
        setEntries(availableEntries);
        if (open?.proposal_id) void campaignClient.getProposal(open.proposal_id).then(setProposal).catch(() => undefined);
      })
      .catch((loadError) => { if (!cancelled) setError(loadError instanceof Error ? loadError.message : "Brainstorm workspace is unavailable"); });
    return () => { cancelled = true; };
  }, [campaignClient]);

  useEffect(() => {
    if (!session) return;
    setDrafts((current) => {
      const next = { ...current };
      session.thoughts.forEach((item) => {
        if (!next[item.candidate_id]) next[item.candidate_id] = { included: false, assertion: item.text.trim(), subjectEntityId: "", state: "established" };
      });
      return next;
    });
  }, [session]);

  useEffect(() => {
    if (mentionQuery === null) { setMentionMatches([]); return; }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void campaignClient.searchEntities(mentionQuery).then((matches) => {
        if (!cancelled) { setMentionMatches(matches.slice(0, 8)); setMentionHighlight(0); }
      }).catch(() => { if (!cancelled) setMentionMatches([]); });
    }, 120);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [campaignClient, mentionQuery]);

  useEffect(() => {
    const question = search.trim();
    if (question.length < 3) {
      setContentEvidence([]);
      setContentSearchLoading(false);
      setContentSearchError("");
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setContentSearchLoading(true);
      setContentSearchError("");
      void campaignClient.query({ question, requester_visibility: { role: "dm" } }, controller.signal)
        .then((result) => { if (!cancelled) setContentEvidence(result.evidence); })
        .catch((searchError) => {
          if (!cancelled && !(searchError instanceof DOMException && searchError.name === "AbortError")) {
            setContentEvidence([]);
            setContentSearchError(searchError instanceof Error ? searchError.message : "Canonical content search failed");
          }
        })
        .finally(() => { if (!cancelled) setContentSearchLoading(false); });
    }, 280);
    return () => { cancelled = true; controller.abort(); window.clearTimeout(timer); };
  }, [campaignClient, search]);

  function positionBrainstormMention(textarea: HTMLTextAreaElement) {
    const caret = textarea.selectionStart ?? textarea.value.length;
    const style = window.getComputedStyle(textarea);
    const mirror = document.createElement("div");
    mirror.style.cssText = `position:fixed;visibility:hidden;pointer-events:none;width:${textarea.clientWidth}px;white-space:pre-wrap;overflow-wrap:break-word;font:${style.font};padding:${style.padding};box-sizing:${style.boxSizing}`;
    mirror.textContent = textarea.value.slice(0, caret);
    const marker = document.createElement("span"); marker.textContent = "\u200b"; mirror.appendChild(marker);
    document.body.appendChild(mirror);
    const lineHeight = Number.parseFloat(style.lineHeight) || 20;
    setMentionPosition({
      left: Math.max(8, Math.min(textarea.clientWidth - 250, marker.offsetLeft - textarea.scrollLeft)),
      top: textarea.offsetTop + marker.offsetTop - textarea.scrollTop + lineHeight + 4,
    });
    document.body.removeChild(mirror);
  }

  function updateThought(value: string, textarea: HTMLTextAreaElement) {
    setThought(value);
    const caret = textarea.selectionStart ?? value.length;
    const match = value.slice(0, caret).match(/(?:^|\s)@([^@\s]*)$/);
    setMentionQuery(match ? match[1] : null);
    if (match) positionBrainstormMention(textarea);
  }

  function selectBrainstormMention(entity: EntityIdentity) {
    const textarea = thoughtRef.current;
    const caret = textarea?.selectionStart ?? thought.length;
    const before = thought.slice(0, caret);
    const match = before.match(/@([^@\s]*)$/);
    if (!match) return;
    const start = caret - match[0].length;
    const inserted = `@${entity.canonical_name} `;
    const next = thought.slice(0, start) + inserted + thought.slice(caret);
    const nextCaret = start + inserted.length;
    setThought(next);
    setLinkedEntities((current) => current.some((item) => item.entity_id === entity.entity_id) ? current : [...current, entity]);
    setMentionQuery(null); setMentionMatches([]);
    window.setTimeout(() => { thoughtRef.current?.focus(); thoughtRef.current?.setSelectionRange(nextCaret, nextCaret); }, 0);
  }

  function handleThoughtKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (mentionMatches.length === 0) return;
    if (event.key === "ArrowDown") { event.preventDefault(); setMentionHighlight((value) => (value + 1) % mentionMatches.length); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setMentionHighlight((value) => (value - 1 + mentionMatches.length) % mentionMatches.length); }
    else if (event.key === "Enter") { event.preventDefault(); selectBrainstormMention(mentionMatches[mentionHighlight] ?? mentionMatches[0]); }
    else if (event.key === "Escape") { event.preventDefault(); setMentionQuery(null); setMentionMatches([]); }
  }

  async function start() {
    if (!title.trim()) return;
    setBusy(true); setError("");
    try { setSession(await campaignClient.startBrainstorm(title.trim())); setTitle(""); }
    catch (startError) { setError(startError instanceof Error ? startError.message : "Brainstorm could not be started"); }
    finally { setBusy(false); }
  }

  async function capture() {
    if (!session || !thought.trim()) return;
    setBusy(true); setError("");
    try {
      const mentions = linkedEntities.flatMap((entity) => {
        const token = `@${entity.canonical_name}`;
        const found = [];
        let offset = thought.indexOf(token);
        while (offset >= 0) {
          found.push({ entity_id: entity.entity_id, display_name: entity.canonical_name, start_offset: offset, end_offset: offset + token.length });
          offset = thought.indexOf(token, offset + token.length);
        }
        return found;
      });
      setSession(await campaignClient.captureBrainstormThought(session.session_id, thought, mentions));
      setThought(""); setLinkedEntities([]); setMentionQuery(null); setMentionMatches([]);
    }
    catch (captureError) { setError(captureError instanceof Error ? captureError.message : "Thought could not be preserved"); }
    finally { setBusy(false); }
  }

  async function togglePin(entityId: string) {
    if (!session || busy) return;
    setBusy(true); setError("");
    try {
      const pinned = session.pins.some((pin) => pin.entity_id === entityId);
      setSession(await (pinned
        ? campaignClient.unpinBrainstormEntity(session.session_id, entityId)
        : campaignClient.pinBrainstormEntity(session.session_id, entityId)));
    } catch (pinError) { setError(pinError instanceof Error ? pinError.message : "Brainstorm context could not be changed"); }
    finally { setBusy(false); }
  }

  async function toggleEvidencePin(recordId: string, searchQuery?: string) {
    if (!session || busy) return;
    setBusy(true); setError("");
    try {
      const pinned = (session.evidence_pins ?? []).some((pin) => pin.record_id === recordId);
      setSession(await (pinned
        ? campaignClient.unpinBrainstormEvidence(session.session_id, recordId)
        : searchQuery ? campaignClient.pinBrainstormEvidence(session.session_id, recordId, searchQuery)
        : campaignClient.pinBrainstormEvidence(session.session_id, recordId)));
    } catch (pinError) { setError(pinError instanceof Error ? pinError.message : "Brainstorm evidence could not be pinned"); }
    finally { setBusy(false); }
  }

  async function openDossier(entityId: string) {
    setDossierLoading(true); setError("");
    try { setDossier(await campaignClient.getLibraryEntry(entityId)); }
    catch (dossierError) { setError(dossierError instanceof Error ? dossierError.message : "Campaign record could not be opened"); }
    finally { setDossierLoading(false); }
  }

  async function prepareProposal() {
    if (!session) return;
    const selected = session.thoughts.filter((item) => drafts[item.candidate_id]?.included);
    if (!selected.length || selected.some((item) => !drafts[item.candidate_id]?.subjectEntityId)) return;
    setBusy(true); setError("");
    try {
      const authorityByState = { established: "explicit_lore", intended: "npc_intention", prepared: "preparation", possible: "brainstorm" } as const;
      const items: CreateProposalItem[] = selected.map((item) => {
        const draft = drafts[item.candidate_id];
        return {
          mutation_kind: "create_claim",
          candidate_id: item.candidate_id,
          evidence_revision_id: item.source_revision_id,
          target_id: crypto.randomUUID(),
          subject_entity_id: draft.subjectEntityId,
          assertion_text: draft.assertion.trim(),
          state: draft.state,
          authority: authorityByState[draft.state],
          visibility: "dm_only",
          confidence: "1",
          is_conditional: false,
          predicts_subject_action: false,
          recorded_at: new Date().toISOString(),
        };
      });
      const created = await campaignClient.createProposal(items, session.session_id);
      setProposal(created);
      setSession(await campaignClient.closeBrainstorm(session.session_id, created.proposal_id));
    } catch (proposalError) { setError(proposalError instanceof Error ? proposalError.message : "Promotion proposal could not be prepared"); }
    finally { setBusy(false); }
  }

  const latest = session?.thoughts.at(-1);
  const supporting = latest?.evidence.evidence.filter((item) => item.role === "support") ?? [];
  const suggestions = supporting.filter((item) => !(session?.evidence_pins ?? []).some((pin) => pin.record_id === item.record_id));
  const contradictions = latest?.evidence.evidence.filter((item) => item.role === "conflict") ?? [];
  const selectedDrafts = Object.values(drafts).filter((draft) => draft.included);
  const proposalReady = selectedDrafts.length > 0 && selectedDrafts.every((draft) => draft.assertion.trim() && draft.subjectEntityId);
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const searchResults = normalizedSearch ? entries.filter((entry) =>
    [entry.canonical_name, ...entry.aliases, ...entry.tags].some((value) => value.toLocaleLowerCase().includes(normalizedSearch))
  ).slice(0, 12) : [];
  const isDiscovery = (item: RetrievalResult["evidence"][number]) => {
    const text = `${item.assertion} ${item.citation}`.toLocaleLowerCase().replace(/[^a-z0-9]+/g, " ");
    return item.graph_trace?.some((step) => step.startsWith("Connected through:"))
      && !brainstormSearchTerms(search).every((term) => text.includes(term));
  };
  const contentSearchGroups: [string, RetrievalResult["evidence"]][] = [
    ["Related discoveries", rankBrainstormEvidence(contentEvidence.filter(isDiscovery), search)],
    ["Direct matches", rankBrainstormEvidence(contentEvidence.filter((item) => !isDiscovery(item)), search)],
  ];
  const contentSearchTerms = brainstormSearchTerms(search);

  if (!session) return <main className="brainstorm-page"><section className="brainstorm-start"><span>Non-canonical workspace</span><h1>Start a brainstorm</h1><p>Capture working ideas freely. Nothing entered here becomes campaign truth without an exact reviewed proposal.</p><label>Working title<input aria-label="Brainstorm title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What are you exploring?" /></label><button disabled={busy || !title.trim()} onClick={() => void start()} type="button">Start brainstorm</button>{error && <div className="notice error" role="alert">{error}</div>}</section></main>;

  return (
    <main className="brainstorm-page">
      <header className="brainstorm-heading">
        <div><span>Brainstorm · {session.status}</span><h1>{session.title}</h1><p>Every thought is preserved as DM-only, non-canonical evidence.</p></div>
        {session.thoughts.length > 0 && <b>{session.thoughts.length} thought{session.thoughts.length === 1 ? "" : "s"}</b>}
      </header>
      {error && <div className="notice error" role="alert">{error}</div>}
      <div className="brainstorm-grid">
        <section className="brainstorm-capture" aria-label="Brainstorm thoughts">
          <div className="brainstorm-timeline">
            {session.thoughts.length === 0
              ? <p className="brainstorm-empty">Start with a possibility, question, connection, or consequence you want to explore.</p>
              : session.thoughts.map((item) => <article key={item.thought_id}><span>{item.sequence}</span><p>{item.text}</p><small>Preserved outside canon</small></article>)}
          </div>
          {session.status === "open" && <div className="brainstorm-composer">
            <label htmlFor="brainstorm-thought">Next thought</label>
            <div className="brainstorm-thought-input">
              <textarea ref={thoughtRef} id="brainstorm-thought" value={thought} onChange={(event) => updateThought(event.target.value, event.currentTarget)} onKeyDown={handleThoughtKeyDown} placeholder="Add the next idea exactly as it occurs to you… Type @ for an accurate campaign name." rows={5} />
              {mentionMatches.length > 0 && <div className="mention-suggestions brainstorm-mentions" style={mentionPosition} role="listbox" aria-label="Brainstorm entity mentions">
                {mentionMatches.map((entity, index) => <button className={index === mentionHighlight ? "active" : ""} aria-selected={index === mentionHighlight} key={entity.entity_id} onMouseDown={(event) => event.preventDefault()} onClick={() => selectBrainstormMention(entity)} role="option" type="button"><b>{entity.canonical_name}</b><span>{display(entity.entity_kind)}{entity.match_kind === "alias" && entity.matched_name ? ` · ${entity.matched_name}` : ""}</span></button>)}
              </div>}
            </div>
            {linkedEntities.length > 0 && <div className="mention-chips" aria-label="Linked brainstorm records">{linkedEntities.map((entity) => <span key={entity.entity_id}>@{entity.canonical_name}<small>{display(entity.entity_kind)}</small></span>)}</div>}
            <button disabled={busy || !thought.trim()} onClick={() => void capture()} type="button">Preserve thought</button>
          </div>}
          <section className="brainstorm-promotion" aria-label="Promotion draft">
            <header><div><span>Optional conclusion</span><h2>Prepare exact promotion</h2></div><p>Select only conclusions you want to consider for canon. Assign the record each claim is about.</p></header>
            {session.thoughts.map((item) => {
              const draft = drafts[item.candidate_id];
              if (!draft) return null;
              return <article className={draft.included ? "selected" : ""} key={item.candidate_id}>
                <label className="brainstorm-include"><input checked={draft.included} disabled={Boolean(proposal)} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, included: event.target.checked } }))} type="checkbox" />Promote thought {item.sequence}</label>
                {draft.included && <><label>Exact claim<textarea aria-label={`Brainstorm claim ${item.sequence}`} value={draft.assertion} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, assertion: event.target.value } }))} /></label><div><label>Affected record<select aria-label={`Brainstorm target ${item.sequence}`} value={draft.subjectEntityId} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, subjectEntityId: event.target.value } }))}><option value="">Choose a campaign record…</option>{entries.map((entry) => <option key={entry.entry_id} value={entry.entry_id}>{entry.canonical_name} · {display(entry.entity_kind)}</option>)}</select></label><label>Truth coordinate<select aria-label={`Brainstorm state ${item.sequence}`} value={draft.state} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, state: event.target.value as BrainstormPromotionDraft["state"] } }))}><option value="established">Established lore</option><option value="intended">NPC or faction intention</option><option value="prepared">Prepared material</option><option value="possible">Retain as possibility</option></select></label></div></>}
              </article>;
            })}
            {proposal ? <div className="brainstorm-proposal-ready"><b>Immutable proposal version {proposal.version_number} is ready.</b><span>No claim has been approved or applied.</span><button onClick={() => void onReviewProposal(proposal)} type="button">Review exact proposal</button></div> : session.status === "open" && session.thoughts.length > 0 && <button disabled={busy || !proposalReady} onClick={() => void prepareProposal()} type="button">End brainstorm and prepare proposal</button>}
          </section>
        </section>
        <aside className="brainstorm-evidence" aria-label="Grounded continuity evidence">
          <header><span>Continuity panel</span><h2>{latest ? `After thought ${latest.sequence}` : "Campaign context"}</h2><p>Search and pin records without leaving your thought. Nothing here changes canon.</p></header>
          <label className="brainstorm-search"><SearchIcon /><input aria-label="Search campaign during brainstorm" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search names, aliases, tags, or campaign facts…" /></label>
          {searchResults.length > 0 && <section className="brainstorm-search-results"><h3>Records</h3>{searchResults.map((entry) => { const pinned = session.pins.some((pin) => pin.entity_id === entry.entry_id); return <article className="brainstorm-context-card" key={entry.entry_id}><button className="brainstorm-card-main" onClick={() => void openDossier(entry.entry_id)} type="button"><b>{entry.canonical_name}</b><span>{display(entry.entity_kind)}{entry.aliases.length ? ` · ${entry.aliases.join(", ")}` : ""}</span></button><button aria-label={`${pinned ? "Unpin" : "Pin"} ${entry.canonical_name}`} className={pinned ? "pin active" : "pin"} disabled={busy || session.status !== "open"} onClick={() => void togglePin(entry.entry_id)} title={pinned ? "Remove from Brainstorm context" : "Keep in Brainstorm context"} type="button"><PinIcon /></button></article>; })}</section>}
          {contentSearchLoading && <p className="brainstorm-search-status" role="status">Searching canonical content…</p>}
          {contentSearchError && <p className="inline-error" role="alert">Content search failed: {contentSearchError}</p>}
{contentSearchGroups.map(([heading, results]) => results.length > 0 && <section className="brainstorm-content-results" key={heading}><details className="brainstorm-search-category"><summary>{heading}<span>{results.length}</span></summary>{results.map((item) => { const owner = item.entity_id ? entries.find((entry) => entry.entry_id === item.entity_id) : undefined; const ownerName = owner?.canonical_name ?? "canonical record"; const pinned = (session.evidence_pins ?? []).some((pin) => pin.record_id === item.record_id); const expanded = expandedEvidence.has(item.record_id); const excerpt = brainstormEvidenceExcerpt(item.assertion, contentSearchTerms, expanded); return <article className={`brainstorm-canon-card brainstorm-search-card${expanded ? " expanded" : ""}`} key={`search-${item.record_id}`}><div className="brainstorm-search-title" title={`${evidenceTitle(item.citation, entries)}\n${item.citation}`}>{evidenceTitle(item.citation, entries)}</div><button aria-expanded={expanded} aria-label={`${expanded ? "Collapse" : "Expand"} canonical result from ${item.citation}`} className="brainstorm-result-main" onClick={() => setExpandedEvidence((current) => { const next = new Set(current); if (next.has(item.record_id)) next.delete(item.record_id); else next.add(item.record_id); return next; })} type="button"><p>{highlightBrainstormTerms(excerpt, contentSearchTerms)}</p>{heading === "Related discoveries" && <div className="brainstorm-connection"><strong>Connected through</strong>{item.graph_trace?.filter((step) => step.startsWith("Connected through:")).map((step, index) => <span key={index}>{step.replace("Connected through: ", "")}</span>)}<small>Associated names · not an event claim</small></div>}<cite>{item.citation}</cite><span>{expanded ? "Show excerpt" : "Show full text"}</span></button>{heading === "Related discoveries" && Boolean(item.graph_sources?.length) && <details className="brainstorm-connection-sources"><summary>Read connection context</summary>{item.graph_sources!.map((source) => <section key={source.record_id}><p>{source.assertion}</p><cite>{source.citation}</cite></section>)}</details>}<div className="brainstorm-card-actions"><button aria-label={`${expanded ? "Collapse" : "Expand"} search card from ${item.citation}`} aria-expanded={expanded} onClick={() => setExpandedEvidence((current) => { const next = new Set(current); if (next.has(item.record_id)) next.delete(item.record_id); else next.add(item.record_id); return next; })} title={expanded ? "Collapse text" : "Expand full text"} type="button">{expanded ? "−" : "⤢"}</button>{item.entity_id && <button aria-label={`Open ${ownerName}`} onClick={() => void openDossier(item.entity_id!)} title={`Open ${ownerName} dossier`} type="button">↗</button>}<button aria-label={`${pinned ? "Unpin" : "Pin"} search evidence from ${item.citation}`} className={pinned ? "pin active" : "pin"} disabled={busy || session.status !== "open"} onClick={() => void toggleEvidencePin(item.record_id, search)} title={pinned ? "Remove from Brainstorm context" : "Keep in Brainstorm context"} type="button"><PinIcon /></button></div></article>; })}</details></section>)}
          {dossierLoading && <p className="brainstorm-empty">Opening campaign record…</p>}
          {dossier && <section className="brainstorm-dossier" aria-label="Brainstorm record dossier"><header><div><span>{display(dossier.entity_kind)}</span><h3>{dossier.canonical_name}</h3></div><button aria-label="Close brainstorm dossier" onClick={() => setDossier(null)} type="button">×</button></header>{dossier.aliases.length > 0 && <p><b>Also known as:</b> {dossier.aliases.join(", ")}</p>}<div>{dossier.claims.length ? dossier.claims.map((claim) => <article key={claim.claim_id}><p>{claim.assertion_text}</p></article>) : <p className="brainstorm-empty">No current claims are recorded.</p>}</div></section>}
          <section className="brainstorm-pinned"><h3>Pinned context</h3>{session.pins.map((pin) => <article className="brainstorm-context-card" key={pin.entity_id}><button className="brainstorm-card-main" onClick={() => void openDossier(String(pin.entity_id))} type="button"><b>{pin.canonical_name}</b><span>{display(pin.entity_kind)}</span></button><button aria-label={`Unpin ${pin.canonical_name}`} className="pin active" disabled={busy || session.status !== "open"} onClick={() => void togglePin(String(pin.entity_id))} title="Remove from Brainstorm context" type="button"><PinIcon /></button></article>)}{(session.evidence_pins ?? []).map((pin) => <article className="brainstorm-canon-card" key={`pinned-${pin.record_id}`}><div><p>{pin.assertion}</p><cite>{pin.citation}</cite></div><div className="brainstorm-card-actions">{pin.entity_id && <button aria-label="Open pinned evidence record" onClick={() => void openDossier(pin.entity_id!)} title="Open dossier" type="button">↗</button>}<button aria-label="Unpin suggested evidence" className="pin active" disabled={busy || session.status !== "open"} onClick={() => void toggleEvidencePin(pin.record_id)} title="Remove evidence from Brainstorm context" type="button"><PinIcon /></button></div></article>)}{session.pins.length === 0 && (session.evidence_pins ?? []).length === 0 && <p className="brainstorm-empty">Pin records or exact evidence you want kept in view and included in later continuity searches.</p>}</section>
          <section><h3>Suggested for latest thought</h3>{suggestions.length ? suggestions.map((item) => { const pinned = (session.evidence_pins ?? []).some((pin) => pin.record_id === item.record_id); return <article className="brainstorm-canon-card" key={item.record_id}><div><p>{item.assertion}</p><cite>{item.citation}</cite></div><div className="brainstorm-card-actions">{item.entity_id && <button aria-label={`Open relevant record ${item.entity_id}`} onClick={() => void openDossier(item.entity_id!)} title="Open dossier" type="button">↗</button>}<button aria-label={`${pinned ? "Unpin" : "Pin"} suggested evidence`} className={pinned ? "pin active" : "pin"} disabled={busy || session.status !== "open"} onClick={() => void toggleEvidencePin(item.record_id)} title={pinned ? "Remove evidence from Brainstorm context" : "Keep this evidence in Brainstorm context"} type="button"><PinIcon /></button></div></article>; }) : <p className="brainstorm-empty">No additional suggestions; pinned evidence is kept above.</p>}</section>
          <section className={contradictions.length ? "has-conflict" : ""}><details className="brainstorm-search-category"><summary>Possible conflicts<span>{contradictions.length}</span></summary>{contradictions.length ? contradictions.map((item) => <article key={item.record_id}><p>{item.assertion}</p><cite>{item.citation}</cite></article>) : <p className="brainstorm-empty">No contradiction was found in the retrieved canon.</p>}</details></section>
          <section><h3>Consequences to review</h3>{supporting.length ? supporting.map((item) => <article key={`consequence-${item.record_id}`}><p>If this idea is promoted, review its effect on: {item.assertion}</p><cite>{item.citation}</cite></article>) : <p className="brainstorm-empty">No grounded continuity consequence is currently visible.</p>}</section>
        </aside>
      </div>
    </main>
  );
}

const CLAIM_STATES = ["observed", "established", "intended", "prepared", "possible", "proposed", "disputed"];
const CLAIM_AUTHORITIES = ["real_play", "dm_correction", "explicit_lore", "npc_intention", "preparation", "brainstorm", "unclassified", "derived"];
const CLAIM_VISIBILITIES = ["dm_only", "party", "character"];

function ClaimReplacementEditor({ drafts, reason, busy, onChange, onReasonChange, onCancel, onSave }: {
  drafts: ClaimReplacementDraft[]; reason: string; busy: boolean;
  onChange: (drafts: ClaimReplacementDraft[]) => void; onReasonChange: (reason: string) => void;
  onCancel: () => void; onSave: () => void;
}) {
  const invalidObserved = drafts.some((draft) => draft.state === "observed" && !draft.observed?.year);
  const update = (index: number, patch: Partial<ClaimReplacementDraft>) => onChange(
    drafts.map((draft, position) => position === index ? { ...draft, ...patch } : draft),
  );
  const add = () => onChange([...drafts, {
    assertion_text: "", state: drafts[0]?.state ?? "established",
    authority: drafts[0]?.authority ?? "explicit_lore",
    visibility: drafts[0]?.visibility ?? "dm_only",
  }]);
  return <article className="claim-editor"><header><b>Replace committed claim</b><span>The original remains in audit history. Add rows to split mixed material.</span></header>
    {drafts.map((draft, index) => <fieldset className="claim-replacement" key={index}><legend>Replacement {index + 1}</legend>
      <label>Assertion<textarea aria-label={`Replacement ${index + 1} assertion`} rows={5} value={draft.assertion_text} onChange={(event) => update(index, { assertion_text: event.target.value })} /></label>
      <div className="form-grid"><label>State<select value={draft.state} onChange={(event) => update(index, { state: event.target.value })}>{CLAIM_STATES.map((value) => <option key={value} value={value}>{display(value)}</option>)}</select></label><label>Authority<select value={draft.authority} onChange={(event) => update(index, { authority: event.target.value })}>{CLAIM_AUTHORITIES.map((value) => <option key={value} value={value}>{display(value)}</option>)}</select></label><label>Visibility<select value={draft.visibility} onChange={(event) => update(index, { visibility: event.target.value })}>{CLAIM_VISIBILITIES.map((value) => <option key={value} value={value}>{display(value)}</option>)}</select></label></div>
      <label>Explicit prerequisite<input value={draft.condition_text ?? ""} placeholder="Leave blank when there is no concrete trigger" onChange={(event) => update(index, { condition_text: event.target.value || undefined })} /></label>
      <div className="form-grid"><ClaimDateEditor label="Effective from" value={draft.effective_from} onChange={(value) => update(index, { effective_from: value })} /><ClaimDateEditor label="Effective until" value={draft.effective_until} onChange={(value) => update(index, { effective_until: value })} /><ClaimDateEditor label="Expected" value={draft.expected} onChange={(value) => update(index, { expected: value })} /><ClaimDateEditor label="Observed" value={draft.observed} onChange={(value) => update(index, { observed: value })} /></div>
      {drafts.length > 1 && <button className="secondary-button" onClick={() => onChange(drafts.filter((_, position) => position !== index))} type="button">Remove replacement</button>}
    </fieldset>)}
    <button className="secondary-button" onClick={add} type="button">Split into another claim</button>
    {invalidObserved && <div className="notice warning" role="alert">Observed replacements require an observed campaign date.</div>}
    <label>Audit reason<textarea aria-label="Claim correction reason" rows={3} value={reason} onChange={(event) => onReasonChange(event.target.value)} /></label>
    <div className="review-actions"><button className="secondary-button" onClick={onCancel} type="button">Cancel</button><button disabled={busy || invalidObserved || drafts.some((draft) => !draft.assertion_text.trim()) || !reason.trim()} onClick={onSave} type="button">{busy ? "Saving…" : drafts.length > 1 ? "Save split claims" : "Save replacement claim"}</button></div>
  </article>;
}

function ClaimDateEditor({ label, value, onChange }: { label: string; value?: { year: number; month?: number; day?: number }; onChange: (value: { year: number; month?: number; day?: number } | undefined) => void }) {
  const number = (raw: string) => raw === "" ? undefined : Number(raw);
  return <fieldset className="claim-date"><legend>{label}</legend><label>Year<input type="number" value={value?.year ?? ""} onChange={(event) => { const year = number(event.target.value); onChange(year === undefined ? undefined : { year, month: value?.month, day: value?.day }); }} /></label><label>Month<input min={1} max={12} type="number" value={value?.month ?? ""} onChange={(event) => value && onChange({ ...value, month: number(event.target.value), day: number(event.target.value) === undefined ? undefined : value.day })} /></label><label>Day<input min={1} max={31} type="number" value={value?.day ?? ""} onChange={(event) => value && onChange({ ...value, day: number(event.target.value) })} /></label></fieldset>;
}

export function ClaimReconciliationWorkspace({ campaignClient }: { campaignClient: CampaignClient }) {
  const [overlaps, setOverlaps] = useState<ClaimOverlap[]>([]);
  const [selected, setSelected] = useState<ClaimOverlap | null>(null);
  const [decision, setDecision] = useState<ReconciliationDecision>("supersede");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const dimensionsConflict = selected !== null && (
    selected.superseding.state !== selected.superseded.state ||
    selected.superseding.authority !== selected.superseded.authority ||
    selected.superseding.visibility !== selected.superseded.visibility ||
    (selected.superseding.condition_text ?? "") !== (selected.superseded.condition_text ?? "")
  );

  async function reload() {
    try {
      const found = await campaignClient.discoverClaimOverlaps();
      setOverlaps(found);
      setSelected((current) => found.find((item) =>
        item.superseding.claim_id === current?.superseding.claim_id &&
        item.superseded.claim_id === current?.superseded.claim_id) ?? null);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Claim overlaps are unavailable");
    }
  }

  useEffect(() => { void reload(); }, [campaignClient]);

  async function apply(event: FormEvent) {
    event.preventDefault();
    if (!selected || !reason.trim()) return;
    setBusy(true);
    try {
      const receipt = await campaignClient.reconcileClaims(selected, decision, reason.trim());
      setMessage(`${display(receipt.decision)} applied · receipt ${receipt.receipt_id}`);
      setReason("");
      setSelected(null);
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Claim reconciliation failed");
    } finally {
      setBusy(false);
    }
  }

  return <section className="operations claim-reconciliation" aria-label="Claim reconciliation">
    <div className="section-heading"><div><p className="kicker">Canonical maintenance</p><h2>Claim reconciliation</h2></div><p>Review likely overlaps. Nothing is merged or removed automatically.</p></div>
    {message && <div className="notice" role="status">{message}</div>}
    {!selected && <div className="reconciliation-list"><header><span>Likely overlaps</span><b>{overlaps.length}</b></header>{overlaps.length === 0 ? <p className="empty-section">No unresolved overlapping claims found.</p> : overlaps.map((overlap) => <button key={`${overlap.superseding.claim_id}:${overlap.superseded.claim_id}`} onClick={() => { setSelected(overlap); setDecision("supersede"); setReason(""); }} type="button"><span>{Math.round(overlap.similarity * 100)}% similar · {overlap.superseding.source_paths.join(", ")}</span><b>{overlap.superseding.assertion_text}</b><small>Compare with: {overlap.superseded.assertion_text}</small></button>)}</div>}
    {selected && <form className="reconciliation-review" onSubmit={apply}>
      <div className="claim-comparison"><ClaimSnapshotCard label="Newer claim" claim={selected.superseding} /><ClaimSnapshotCard label="Earlier claim" claim={selected.superseded} /></div>
      {dimensionsConflict && <div className="notice warning" role="alert"><b>Truth dimensions conflict.</b><span>These claims differ in state, authority, visibility, or condition. Nothing is reconciled automatically; select the intended outcome and record why.</span></div>}
      <fieldset><legend>Decision</legend><label><input checked={decision === "supersede"} name="reconciliation-decision" onChange={() => setDecision("supersede")} type="radio" /> Supersede earlier claim</label><label><input checked={decision === "duplicate"} name="reconciliation-decision" onChange={() => setDecision("duplicate")} type="radio" /> Mark earlier claim duplicate</label><label><input checked={decision === "retain_both"} name="reconciliation-decision" onChange={() => setDecision("retain_both")} type="radio" /> Retain both as current</label></fieldset>
      <label>Audit reason<textarea aria-label="Reconciliation reason" onChange={(event) => setReason(event.target.value)} rows={3} value={reason} /></label>
      <div className="review-actions"><button className="secondary-button" onClick={() => setSelected(null)} type="button">Back</button><button disabled={busy || !reason.trim()} type="submit">{busy ? "Applying…" : "Apply decision"}</button></div>
    </form>}
  </section>;
}

function ClaimSnapshotCard({ label, claim }: { label: string; claim: ClaimOverlap["superseding"] }) {
  const evidence = claim.evidence ?? [];
  return <article><header><span>{label}</span><b>{display(claim.state)} · {display(claim.authority)}</b></header><p>{claim.assertion_text}</p><dl><div><dt>Visibility</dt><dd>{display(claim.visibility)}</dd></div><div><dt>Recorded</dt><dd>{new Date(claim.recorded_at).toLocaleString()}</dd></div><div><dt>Condition</dt><dd>{claim.condition_text ?? "None"}</dd></div><div><dt>Evidence</dt><dd>{evidence.length === 0 ? "None" : evidence.map((item) => `${item.source_path} · ${item.section_path} · ${item.start_offset}–${item.end_offset} · ${display(item.evidence_role)}`).join("\n")}</dd></div></dl><small>{claim.claim_id}</small></article>;
}

export function PlanWorkspace({ campaignClient }: { campaignClient: CampaignClient }) {
  const [plans, setPlans] = useState<PlanRecord[]>([]);
  const [kinds, setKinds] = useState<PlanKindGuidance[]>([]);
  const [kind, setKind] = useState<PlanKind>("campaign_direction");
  const [name, setName] = useState("");
  const [summary, setSummary] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [attribution, setAttribution] = useState("");
  const [communicatedAt, setCommunicatedAt] = useState("");
  const [evidenceIds, setEvidenceIds] = useState("");
  const [relatedIds, setRelatedIds] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [nextLifecycle, setNextLifecycle] = useState<PlanLifecycle>("abandoned");
  const [supportingClaimIds, setSupportingClaimIds] = useState("");
  const [proposal, setProposal] = useState<PlanProposalVersion>();
  const [approval, setApproval] = useState<CandidateProposalApproval>();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const parseIds = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);
  const reload = async () => {
    const [taxonomy, records] = await Promise.all([
      campaignClient.getTaxonomy(), campaignClient.listPlans(),
    ]);
    setKinds(taxonomy.plan_kinds ?? []);
    setPlans(records);
  };
  useEffect(() => { void reload().catch((error) => setMessage(String(error))); }, []);

  async function proposePlan(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const created = await campaignClient.createPlanProposal({
        target_id: crypto.randomUUID(), plan_kind: kind, canonical_name: name, summary,
        owner_record_id: ownerId || undefined,
        player_attribution: attribution || undefined,
        communicated_at: communicatedAt ? new Date(communicatedAt).toISOString() : undefined,
        evidence_source_span_ids: parseIds(evidenceIds), related_plan_ids: parseIds(relatedIds),
      });
      setProposal(created); setApproval(undefined);
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  }

  async function proposeTransition(event: FormEvent) {
    event.preventDefault(); if (!selectedPlanId) return; setBusy(true); setMessage("");
    try {
      const created = await campaignClient.transitionPlanProposal(
        selectedPlanId, nextLifecycle, parseIds(supportingClaimIds),
      );
      setProposal(created); setApproval(undefined);
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  }

  async function approveAndApply() {
    if (!proposal) return; setBusy(true);
    try {
      const approved = approval ?? await campaignClient.approvePlanProposal(
          proposal, `plan:${proposal.proposal_id}:${proposal.version_number}`,
        );
      setApproval(approved);
      const receipt = await campaignClient.applyApproval(proposal, approved);
      setMessage(`Applied with receipt ${receipt.receipt_id}.`);
      setProposal(undefined); setApproval(undefined); await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
    finally { setBusy(false); }
  }

  return <section className="review-workspace" id="plans">
    <div className="section-heading"><div><p className="kicker">Agency-aware planning</p><h2>Plans</h2></div><p>Plans describe guidance or intention. They never prove an outcome or predict a PC action.</p></div>
    <div className="review-grid">
      <aside className="candidate-queue" aria-label="Plan records"><header><span>Plan records</span><b>{plans.length}</b></header>{plans.map((plan) => <button className={selectedPlanId === plan.id ? "selected" : ""} key={plan.id} onClick={() => setSelectedPlanId(plan.id)} type="button"><span>{display(plan.plan_kind)} · {display(plan.lifecycle)}</span><b>{plan.canonical_name}</b><small>{plan.owner_name ?? display(plan.knowledge_boundary)}</small></button>)}</aside>
      <div className="candidate-detail">
        <form className="resolution-form" onSubmit={proposePlan}><header><span>New stable plan</span><p>Creation remains non-canonical until its exact proposal is approved and applied.</p></header><div className="form-grid"><label>Plan kind<select aria-label="Plan kind" value={kind} onChange={(event) => setKind(event.target.value as PlanKind)}>{(kinds.length ? kinds : [{ kind: "campaign_direction", label: "Campaign direction", description: "DM guidance" }, { kind: "in_world_plan", label: "In-world plan", description: "NPC or faction intention" }, { kind: "player_plan", label: "Player plan", description: "Attributed player communication" }]).map((item) => <option key={item.kind} value={item.kind}>{item.label}</option>)}</select></label><label>Canonical name<input aria-label="Plan name" required value={name} onChange={(event) => setName(event.target.value)} /></label></div><p className="kind-guidance">{kinds.find((item) => item.kind === kind)?.description}</p><label>Summary<textarea aria-label="Plan summary" required value={summary} onChange={(event) => setSummary(event.target.value)} /></label>{kind !== "campaign_direction" && <label>Owner record ID<input aria-label="Plan owner record ID" required value={ownerId} onChange={(event) => setOwnerId(event.target.value)} /></label>}{kind === "player_plan" && <div className="form-grid"><label>Player attribution<input aria-label="Player attribution" required value={attribution} onChange={(event) => setAttribution(event.target.value)} /></label><label>Communicated at<input aria-label="Communicated at" required type="datetime-local" value={communicatedAt} onChange={(event) => setCommunicatedAt(event.target.value)} /></label></div>}<label>Evidence source-span IDs<input aria-label="Plan evidence IDs" placeholder="Comma-separated; required for player plans" value={evidenceIds} onChange={(event) => setEvidenceIds(event.target.value)} /></label><label>Related plan IDs<input aria-label="Related plan IDs" placeholder="Comma-separated" value={relatedIds} onChange={(event) => setRelatedIds(event.target.value)} /></label><button disabled={busy || !name.trim() || !summary.trim()} type="submit">Create exact plan proposal</button></form>
        {selectedPlanId && <form className="resolution-form" onSubmit={proposeTransition}><header><span>Reviewed lifecycle transition</span><p>Completion and failure require separate observed claim IDs.</p></header><div className="form-grid"><label>New lifecycle<select aria-label="New plan lifecycle" value={nextLifecycle} onChange={(event) => setNextLifecycle(event.target.value as PlanLifecycle)}><option value="active">Active</option><option value="completed">Completed</option><option value="failed">Failed</option><option value="abandoned">Abandoned</option><option value="superseded">Superseded</option></select></label><label>Observed claim IDs<input aria-label="Supporting observed claim IDs" placeholder="Comma-separated" value={supportingClaimIds} onChange={(event) => setSupportingClaimIds(event.target.value)} /></label></div><button disabled={busy} type="submit">Propose lifecycle transition</button></form>}
        {proposal && <article className="proposal-review"><header><div><span>Immutable plan proposal</span><h4>{display(proposal.item.mutation_kind)}</h4></div><code>{proposal.content_hash}</code></header><div className="proposal-items"><div><b>Before</b><pre>{JSON.stringify(proposal.item.before ?? null, null, 2)}</pre><b>After</b><pre>{JSON.stringify(proposal.item.after, null, 2)}</pre></div></div><footer>Every kind, owner, knowledge boundary, lifecycle, visibility, relationship, and evidence coordinate shown above is included in the reviewed hash.</footer></article>}
        {proposal && <div className="confirmation-panel"><button disabled={busy} onClick={() => void approveAndApply()} type="button">{approval ? "Retry approved plan application" : "Approve and apply exact plan proposal"}</button></div>}
        {message && <div className="notice" role="status"><span>{message}</span></div>}
      </div>
    </div>
  </section>;
}

interface ProposalReviewProps {
  proposal: CandidateProposalVersion;
  selectedItemIds: string[];
  setSelectedItemIds: (itemIds: string[]) => void;
}

function ProposalReview({ proposal, selectedItemIds, setSelectedItemIds }: ProposalReviewProps) {
  return <article className="proposal-review"><header><div><span>Immutable proposal</span><h4>Version {proposal.version_number}</h4></div><code title={proposal.content_hash}>{proposal.content_hash}</code></header><div className="proposal-items">{proposal.items.map((item) => { const checked = selectedItemIds.includes(item.item_id); return <label key={item.item_id}><input checked={checked} onChange={() => setSelectedItemIds(checked ? selectedItemIds.filter((id) => id !== item.item_id) : [...selectedItemIds, item.item_id])} type="checkbox" /><div><span>Item {item.sequence} · {display(item.mutation_kind)}</span><b>{String(item.after.canonical_name ?? item.after.assertion_text ?? item.target_id)}</b><dl><ProposalField label="Target" value={item.target_type} />{item.mutation_kind === "create_entity" ? <><ProposalField label="Record type" value={item.after.record_type} /><ProposalField label="Entity kind" value={item.after.entity_kind ?? item.after.entity_type} /><ProposalField label="Kind version" value={item.after.entity_kind_version} /><ProposalField label="Tags" value={Array.isArray(item.after.tags) ? item.after.tags.join(", ") || "none" : "none"} /></> : <><ProposalField label="Predicate" value={item.after.predicate} /><ProposalField label="Resulting state" value={item.after.state} /><ProposalField label="Authority" value={item.after.authority} /><ProposalField label="Visibility" value={item.after.visibility} /><ProposalField label="Subject ID" value={item.after.subject_entity_id} /><ProposalField label="Object ID" value={item.after.object_entity_id} /><ProposalField label="Confidence" value={item.after.confidence} /><ProposalField label="Conditional" value={item.after.is_conditional} /><ProposalField label="Predicts subject action" value={item.after.predicts_subject_action} /><ProposalField label="Recorded at" value={item.after.recorded_at} /><ProposalField label="Observed at" value={item.after.observed_at} /></>}<ProposalField label="Target ID" value={item.target_id} /></dl></div></label>; })}</div><footer>Approval applies only to checked item IDs in this displayed version. Unchecked siblings remain unapplied.</footer></article>;
}

function ProposalField({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null || value === "") return null;
  const rendered = typeof value === "boolean" ? (value ? "yes" : "no") : String(value);
  return <div><dt>{label}</dt><dd>{rendered}</dd></div>;
}

export default App;





