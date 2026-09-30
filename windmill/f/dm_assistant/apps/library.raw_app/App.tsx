import { FormEvent, KeyboardEvent as ReactKeyboardEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LogEntry, ToastStack, toast } from "./toasts";
import { getSettings, useSettings } from "./settings";
import { queueForLore, resolveLoreItem, dismissLoreItem, subscribeLoreQueue, resetLoreQueueForTest, saveLoreEvidence, type LoreQueueItem, type LoreSuggestionSet } from "./loreQueue";
import { GlossaryHelpPage, Term, registerGlossaryNavigation } from "./glossary";
import type { CampaignClockChange, CampaignDate, ConflictPair, DeadSeat, LifeStatusProposal, SessionDatingEntry, UndatedClaimEntry } from "./campaignClient";
import { evidenceTitle } from "./evidenceTitle";

import type {
  CampaignClient,
  BrainstormSession,
  AIConfigurationSnapshot,
  AIPurposeInfo,
  EffectivePrompt,
  LinkAuditResult,
  MovedAssertion,
  GraphRelationRow,
  ProseDraftCommand,
  ProseDraftResult,
  VocabularyValue,
  CandidateExtraction,
  CandidateProposalApproval,
  CandidateFilters,
  CandidateProposalVersion,
  CreateProposalItem,
  CreateClaimProposalItem,
  EntityKind,
  EntityKindGuidance,
  EntityIdentity,
  FactionRole,
  IdentityDecisionEntry,
  FactionRoleSummary,
  LibraryEntrySummary,
  RoleDeclarationSummary,
  LibraryMember,
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
  EntityProfile,
  PromotionCandidate,
  UnpromotedAuditResult,
  QualifiedAuditResult,
  ExclusiveClaimsResult,
  EntityDocumentClaims,
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

function ClaimAssertion({ claim, contextName }: { claim: SourceDocumentClaim; contextName?: string }) {
  const compact = claim.assertion_text.replace(/\s+/g, " ").trim();
  const mention = contextName
    && claim.subject_entity_name
    && claim.subject_entity_name.toLocaleLowerCase() !== contextName.toLocaleLowerCase()
    && compact.toLocaleLowerCase().includes(contextName.toLocaleLowerCase());
  const ownerTitle = claim.subject_entity_name
    && contextName
    && claim.subject_entity_name.toLocaleLowerCase() !== contextName.toLocaleLowerCase()
    ? <span className="claim-owner-title">owned by {claim.subject_entity_name}</span>
    : null;
  if (compact.length <= 420) return <>{ownerTitle}<p>{claim.assertion_text}</p></>;
  const sentences = compact.match(/[^.!?]+[.!?]+(?:\s|$)/g) ?? [compact];
  const summary = (() => {
    // A claim owned by another record is on this page because it MENTIONS
    // this record — anchor the clamp on the mention-bearing sentence so the
    // relevance is visible, with ellipses covering omitted sentences.
    if (mention) {
      const lower = contextName!.toLocaleLowerCase();
      const index = sentences.findIndex((s) => s.toLocaleLowerCase().includes(lower));
      if (index >= 0) {
        const pick = sentences[index].trim();
        if (pick.length <= 320) {
          return `${index > 0 ? "… " : ""}${pick}${index < sentences.length - 1 ? " …" : ""}`;
        }
        return `… ${pick.slice(0, 280).replace(/\s+\S*$/, "")}… …`;
      }
    }
    const first = sentences[0]?.trim() ?? compact;
    if (first.length >= 40 && first.length <= 280) return first;
    return `${compact.slice(0, 240).replace(/\s+\S*$/, "")}…`;
  })();
  return <>{ownerTitle}<p>{summary}</p><details className="full-assertion"><summary>Read full canonical assertion</summary><p>{claim.assertion_text}</p></details></>;
}

function RecordIcon({ kind }: { kind: "edit" | "source" | "hide" | "show" | "note" | "unpaged" | "page" | "records" | "dossier" }) {
  if (kind === "dossier") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 3h9l3 3v15H6V3Z" /><path d="m12 8.2 1 2.3 2.5.4-1.8 1.7.4 2.5-2.1-1.1-2.1 1.1.4-2.5-1.8-1.7 2.5-.4L12 8.2Z" /></svg>;
  if (kind === "records") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h13" /><path d="M17 15l3 3-3 3" /></svg>;
  if (kind === "unpaged") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 3h9l3 3v15H6V3Z" strokeDasharray="3 2.6" /><path d="M9.5 11h5M9.5 15h5" strokeDasharray="2 2.4" /></svg>;
  if (kind === "page") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 3h9l3 3v15H6V3Z" /><path d="M9.5 11h5M9.5 15h5" /></svg>;
  if (kind === "edit") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16v4Zm9.5-13.5 4 4" /></svg>;
  if (kind === "source") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 3h9l3 3v15H6V3Z" /><path d="M15 3v4h4M9 11h6M9 15h6" /></svg>;
  if (kind === "hide") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" /><path d="m4 4 16 16" /></svg>;
  if (kind === "note") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 4h14v16H5zM8 8h8M8 12h5" /><path d="M16 14v6M13 17h6" /></svg>;
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" /><circle cx="12" cy="12" r="2.5" /></svg>;
}

interface DraftQueueItem {
  id: string;
  jobId: string;
  entryId: string;
  entryName: string;
  startedAt: number;
  state: "running" | "ready" | "failed";
  result?: ProseDraftResult;
  elapsedSeconds?: string;
  error?: string;
}

function WandIcon() {
  // The AI-action mark: every button that triggers a model call leads with it.
  return <svg aria-hidden="true" className="wand-icon" viewBox="0 0 24 24"><path d="M5 19 17 7" /><path d="m15.5 5.5 3 3L21 6l-3-3-2.5 2.5Z" /><path d="M4 8l1.2-1.2L6.4 8 5.2 9.2 4 8Z" /><path d="M9 3l.9-.9.9.9-.9.9L9 3Z" /><path d="m12.6 21.4.9-.9.9.9-.9.9-.9-.9Z" /></svg>;
}

function EntrySourceDrawer({ sources, fallbackPath }: { sources: LibraryEntrySource[]; fallbackPath?: string }) {
  const [settings] = useSettings();
  const unique = sources.length
    ? Array.from(new Map(sources.map((source) => [source.document_id, source])).values())
    : fallbackPath ? [{ document_id: fallbackPath, path: fallbackPath }] : [];
  if (!unique.length || !settings.recordsVisibility.sources) return null;
  return <details className="source-drawer"><summary>Sources</summary>{unique.map((source) => <code key={source.document_id}>{source.path}</code>)}</details>;
}

function CanonicalClaimSections({ claims, history, onEditClaim, onPromote, dossierPromoted, contextName }: { contextName?: string; claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; onEditClaim?: (claimId: string) => void; onPromote?: (claimId: string) => void; dossierPromoted?: Set<string> }) {
  const [hiddenClaims, setHiddenClaims] = useState<Set<string>>(() => new Set());
  const [visibilitySettings] = useSettings();
  const [showHidden, setShowHidden] = useState(false);
  const groups = [
    { title: "Real-play facts", states: ["observed"] },
    { title: "Established information", states: ["established"] },
    { title: "Plans and preparation", states: ["intended", "prepared"] },
    { title: "Considered", states: ["considered", "possible"] },
  ];
  if (claims.length === 0 && history.length === 0) return null;
  return <section className="entry-claims canonical-record"><header><div><span>Campaign record</span><h2>Current information</h2></div><button aria-label={showHidden ? "Hide hidden records" : "Show hidden records"} disabled={hiddenClaims.size === 0} onClick={() => setShowHidden((value) => !value)} title={hiddenClaims.size === 0 ? "No hidden records" : showHidden ? "Hide hidden" : "Show hidden"} type="button"><RecordIcon kind={showHidden ? "hide" : "show"} /></button></header><div className="record-details-body">{groups.map((group) => {
    const items = claims.filter((claim) => group.states.includes(claim.state) && (showHidden || !hiddenClaims.has(claim.claim_id)));
    return items.length > 0 && <section key={group.title}><h3>{group.title}</h3><div className="canonical-claim-list">{items.map((claim) => { const isHidden = hiddenClaims.has(claim.claim_id); const hasSource = Boolean(claim.source_excerpt || claim.sources?.length); return <article className={isHidden ? "hidden-record" : ""} key={claim.claim_id}><div className="record-card-actions">{onPromote && (dossierPromoted?.has(claim.claim_id)
              ? <span className="on-page-tag" title="Promoted to the Dossier on this entry's page"><RecordIcon kind="dossier" /></span>
              : <button aria-label={`Promote to Dossier: ${claim.assertion_text.slice(0, 40)}`} onClick={() => onPromote(claim.claim_id)} title="Promote to Dossier — show this fact as a card on the entry page" type="button"><RecordIcon kind="dossier" /></button>)}{onEditClaim && <button aria-label="Edit claim" onClick={() => onEditClaim(claim.claim_id)} title="Edit" type="button"><RecordIcon kind="edit" /></button>}<button aria-label="Show source" disabled={!hasSource} title={hasSource ? "Source" : "No source available"} type="button" onClick={(event) => { const details = event.currentTarget.closest("article")?.querySelector("details.record-source") as HTMLDetailsElement | null; if (details) details.open = !details.open; }}><RecordIcon kind="source" /></button><button aria-label={isHidden ? "Restore record" : "Hide record"} onClick={() => setHiddenClaims((current) => { const next = new Set(current); next.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id); return next; })} title={isHidden ? "Restore" : "Hide"} type="button"><RecordIcon kind={isHidden ? "show" : "hide"} /></button></div><ClaimAssertion claim={claim} contextName={contextName} />{claim.conditional && claim.condition_text && <p className="claim-condition"><b>Prerequisite:</b> {claim.condition_text}</p>}{visibilitySettings.recordsVisibility.sources && <details className="record-source"><summary>Provenance</summary>{claim.source_excerpt && <pre>{claim.source_excerpt}</pre>}{claim.sources?.map((source) => <code key={source.document_id}>{source.path}</code>)}</details>}</article>; })}</div></section>;
  })}{history.length > 0 && visibilitySettings.recordsVisibility.earlierVersions && <details className="claim-history"><summary>Earlier versions ({history.length})</summary>{history.map((claim) => <article key={claim.claim_id}><p>{claim.assertion_text}</p><small>{claim.supersession_reason}</small>{claim.sources?.length && visibilitySettings.recordsVisibility.sources ? <details className="record-source"><summary>Provenance</summary>{claim.sources.map((source) => <code key={source.document_id}>{source.path}</code>)}</details> : null}</article>)}</details>}</div></section>;
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
    <details className="records-hood" aria-label="Records (under the hood)"><summary><RecordIcon kind="records" /> Records — claims and sources</summary>
      <CanonicalClaimSections claims={claims} history={history} onEditClaim={onEditClaim} contextName={entry.name} />
      <EntrySourceDrawer fallbackPath={path} sources={sources} />
    </details>
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

function StructuredEntryView({ entry, path, claims, history, sources, onEditClaim, onEdit, onWriteDescription, onReviseDescription, entityTemplate, roster, dossierClaimIds, movedAssertions, onPromoteClaim, onDemoteClaim, onOpenEntryByName, locationTrail }: { entry: ParsedEntry; path: string; claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; sources: LibraryEntrySource[]; onEditClaim?: (claimId: string) => void; onEdit?: () => void; onWriteDescription?: () => void; onReviseDescription?: () => void; entityTemplate?: { aliases: string[]; base_location?: string | null; location_type?: string | null; parent_location?: string | null; roles?: FactionRole[]; race?: string | null; sex?: string | null; player?: string | null; life_status?: EntityProfile["life_status"]; life_status_since?: EntityProfile["life_status_since"] }; roster?: { members: LibraryMember[]; related: string[] }; dossierClaimIds?: Set<string>; movedAssertions?: MovedAssertion[]; onPromoteClaim?: (claimId: string) => void; onDemoteClaim?: (claimId: string) => void; onOpenEntryByName?: (name: string) => void; locationTrail?: string[] }) {
  const label = pathEntryType(path) === "Source" ? (entry.type === "lore" ? "Worldbuilding" : display(entry.type)) : pathEntryType(path);
  // Entity-sourced template fields win over a borrowed document's frontmatter;
  // profile edits must never display stale doc metadata.
  const field = (key: "location_type" | "parent_location") =>
    (entityTemplate && entityTemplate[key]) || entry.metadata.get(key) || null;
  const dossierClaims = (dossierClaimIds && onDemoteClaim)
    ? claims.filter((claim) => dossierClaimIds.has(claim.claim_id))
    : [];
  return <article className={`document-view entry-view ${entry.type}-entry`}>
    <header><b>{label}</b><span>Campaign entry</span><div className="entry-page-actions">{onWriteDescription && <button aria-label={`Write description for ${entry.name}`} onClick={onWriteDescription} title="Write description — give this entry its page" type="button"><RecordIcon kind="unpaged" /></button>}{onReviseDescription && <button aria-label={`Revise description for ${entry.name}`} onClick={onReviseDescription} title="Revise description — edit this entry's authored page" type="button"><RecordIcon kind="page" /></button>}{onEdit && <button aria-label="Edit entry" onClick={onEdit} title="Edit" type="button"><RecordIcon kind="edit" /></button>}</div></header>
    <section className="entry-hero"><h1>{entry.name}</h1>{locationTrail && locationTrail.length > 1 && <nav aria-label="Location hierarchy" className="entry-breadcrumb">{locationTrail.slice(0, -1).map((crumb, index) => <span className="breadcrumb-step" key={`${crumb}-${index}`}>{onOpenEntryByName
      ? <button onClick={() => onOpenEntryByName(crumb)} type="button">{crumb}</button>
      : <span>{crumb}</span>}<span aria-hidden="true" className="breadcrumb-sep">›</span></span>)}<span>{locationTrail[locationTrail.length - 1]}</span></nav>}<dl>{field("location_type") && <div><dt>Location type</dt><dd>{cleanMarkdown(field("location_type")!)}</dd></div>}{entry.metadata.get("status") && <div><dt>Status</dt><dd>{cleanMarkdown(entry.metadata.get("status")!)}</dd></div>}{entityTemplate?.race && <div><dt>Race</dt><dd>{cleanMarkdown(entityTemplate.race)}</dd></div>}{entityTemplate?.sex && <div><dt>Sex</dt><dd>{cleanMarkdown(entityTemplate.sex)}</dd></div>}{entityTemplate?.player && <div><dt>Player</dt><dd>{cleanMarkdown(entityTemplate.player)}</dd></div>}{entityTemplate && entityTemplate.aliases.length > 0 && <div><dt><Term term="alias">Aliases</Term></dt><dd>{entityTemplate.aliases.join(", ")}</dd></div>}{entityTemplate?.base_location && <div><dt>Location</dt><dd>{cleanMarkdown(entityTemplate.base_location)}</dd></div>}{entityTemplate?.life_status && <div><dt><Term term="life-status">Life status</Term></dt><dd>{display(entityTemplate.life_status)}{entityTemplate.life_status_since ? ` (since ${entityTemplate.life_status_since.year}-${String(entityTemplate.life_status_since.month).padStart(2, "0")}-${String(entityTemplate.life_status_since.day).padStart(2, "0")})` : ""}</dd></div>}{entityTemplate?.roles && entityTemplate.roles.length > 0 && <div><dt><Term term="role">Roles</Term></dt><dd>{entityTemplate.roles.map((role) => `${role.name}${role.is_leadership ? " ★" : ""}${role.holder_names.length > 0 ? ` — ${role.holder_names.join(", ")}` : " — vacant"}`).join("; ")}</dd></div>}</dl></section>
    {entry.intro && <section className="entry-summary"><EntryText text={entry.intro} /></section>}
    {dossierClaims.length > 0 && <section aria-label="Dossier" className="character-content character-dossier"><h2>Dossier</h2><div>{dossierClaims.map((claim) => <section className="dossier-fact-card" key={claim.claim_id}>
      <div className="record-card-actions"><button aria-label={`Demote from Dossier: ${claim.assertion_text.slice(0, 40)}`} onClick={() => onDemoteClaim!(claim.claim_id)} title="Demote from Dossier — back under the hood only" type="button"><RecordIcon kind="hide" /></button></div>
      <EntryText text={claim.assertion_text} />
    </section>)}</div></section>}
    {movedAssertions && movedAssertions.length > 0 && <section aria-label="Moved assertions" className="character-content character-dossier"><h2>Moved to new entries</h2><div>{movedAssertions.map((moved) => <section className="dossier-fact-card moved-assertion-tile" key={moved.claim_id}>
      <h3>{moved.assertion_text.slice(0, 80)}{moved.assertion_text.length > 80 ? "…" : ""}</h3>
      <EntryText text={moved.assertion_text.slice(0, 160)} />
      {onOpenEntryByName && <button className="text-button" onClick={() => onOpenEntryByName(moved.new_entity_name)} type="button">→ {moved.new_entity_name}</button>}
    </section>)}</div></section>}
    {entry.sections.filter((section) => section.title.toLocaleLowerCase() !== "sources" && section.title.toLocaleLowerCase() !== "references").length > 0 && <section aria-label="Sections" className="character-content character-dossier"><div>{entry.sections.filter((section) => section.title.toLocaleLowerCase() !== "sources" && section.title.toLocaleLowerCase() !== "references").map((section, index) => <section className={`entry-section-card level-${section.level}`} key={`${section.title}-${index}`}><h3>{section.title}</h3><EntryText text={section.content} /></section>)}</div></section>}
    {roster && (roster.members.length > 0 || roster.related.length > 0) && <section className="entry-section faction-roster" aria-label="Faction roster">
      <h2>{roster.members.length > 0 ? <Term term="roster">Members</Term> : "Appears with"}</h2>
      {roster.members.length > 0 ? <ul className="roster-list">{roster.members.map((member) => <li key={member.member_id}>
        <span className="member-name">{member.name}</span>
        {member.role_title && <span className={member.is_leadership ? "role-chip leadership" : "role-chip"}>{member.role_title}{member.is_leadership ? " ★" : ""}</span>}
      </li>)}</ul> : <div><p className="roles-explainer">Co-mentioned in shared records; not an explicit roster.</p><ul className="roster-list roster-associations">{roster.related.map((name) => <li key={name}><span className="member-name">{name}</span></li>)}</ul></div>}
      {roster.members.length > 0 && <span className="identity-members-legend">★ unique leadership seat</span>}
    </section>}
    <details className="records-hood" aria-label="Records (under the hood)"><summary><RecordIcon kind="records" /> Records — claims and sources</summary>
      <CanonicalClaimSections claims={claims} history={history} onEditClaim={onEditClaim} onPromote={onPromoteClaim} dossierPromoted={dossierClaimIds} contextName={entry.name} />
      <EntrySourceDrawer fallbackPath={path} sources={sources} />
    </details>
  </article>;
}

function SessionNoteEntryView({ note, claims, history, onEditClaim, onEdit }: { note: SourceDocumentContent; claims: SourceDocumentClaim[]; history: SourceDocumentClaimHistory[]; onEditClaim?: (claimId: string) => void; onEdit: () => void }) {
  const campaignDate = note.in_game_date;
  const campaignDateLabel = campaignDate ? `${String(campaignDate.year).padStart(4, "0")}-${String(campaignDate.month).padStart(2, "0")}-${String(campaignDate.day).padStart(2, "0")} CE` : "Not recorded";
  return <article className="document-view entry-view session-note-entry">
    <header><b>Session note</b><span>Actual play</span><div className="entry-page-actions"><button aria-label="Edit session note" onClick={onEdit} title="Create a corrected revision" type="button"><RecordIcon kind="edit" /></button></div></header>
    <section className="entry-hero"><span>Session</span><h1>{note.title ?? "Untitled session"}</h1><dl><div><dt>Played</dt><dd>{note.session_date ?? "Not recorded"}</dd></div><div><dt>Campaign date</dt><dd>{campaignDateLabel}</dd></div></dl></section>
    <details className="records-hood" aria-label="Records (under the hood)"><summary><RecordIcon kind="records" /> Records — claims and sources</summary>
      <section className="entry-section"><h3>Session record</h3>{claims.length > 0 ? <div className="canonical-claim-list">{claims.map((claim) => <article key={claim.claim_id}>{onEditClaim && <div className="record-card-actions"><button aria-label="Edit claim" onClick={() => onEditClaim(claim.claim_id)} title="Edit" type="button"><RecordIcon kind="edit" /></button></div>}<ClaimAssertion claim={claim} /></article>)}</div> : <p>No committed claims yet.</p>}</section>
      <details className="source-drawer"><summary>Original note and provenance</summary><EntryText text={note.content} /><code>{note.path}</code></details>
      {history.length > 0 && <details className="claim-history"><summary>Superseded claim history ({history.length})</summary>{history.map((claim) => <p key={claim.claim_id}>{claim.assertion_text}</p>)}</details>}
    </details>
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

function CharacterDocumentView({ profile, path, sources = [], onEdit, onWriteDescription, dmClaims = [], claimHistory = [], onEditClaim, lifeStatus, dossierClaimIds, onPromoteClaim, onDemoteClaim }: { profile: CharacterDocument; path: string; sources?: LibraryEntrySource[]; onEdit?: () => void; onWriteDescription?: () => void; dmClaims?: SourceDocumentClaim[]; claimHistory?: SourceDocumentClaimHistory[]; onEditClaim?: (claimId: string) => void; lifeStatus?: { status: string | null; since: string | null }; dossierClaimIds?: Set<string>; onPromoteClaim?: (claimId: string) => void; onDemoteClaim?: (claimId: string) => void }) {
  const contextName = profile.name;
  const [hiddenClaims, setHiddenClaims] = useState<Set<string>>(() => new Set());
  const [visibilitySettings] = useSettings();
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
      return <article className={isHidden ? "hidden-record" : ""} key={claim.claim_id}><div className="record-card-actions">{onPromoteClaim && (dossierClaimIds?.has(claim.claim_id)
        ? <span className="on-page-tag" title="Promoted to the Dossier on this entry's page"><RecordIcon kind="dossier" /></span>
        : <button aria-label={`Promote to Dossier: ${claim.assertion_text.slice(0, 40)}`} onClick={() => onPromoteClaim(claim.claim_id)} title="Promote to Dossier — show this fact as a card on the entry page" type="button"><RecordIcon kind="dossier" /></button>)}{onEditClaim && <button aria-label="Edit claim" onClick={() => onEditClaim(claim.claim_id)} title="Edit" type="button"><RecordIcon kind="edit" /></button>}<button aria-label="Show source" disabled={!hasSource} onClick={() => setVisibleSources((current) => { const next = new Set(current); next.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id); return next; })} title={hasSource ? "Source" : "No source available"} type="button"><RecordIcon kind="source" /></button><button aria-label={isHidden ? "Restore record" : "Hide record"} onClick={() => setHiddenClaims((current) => { const next = new Set(current); next.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id); return next; })} title={isHidden ? "Restore" : "Hide"} type="button"><RecordIcon kind={isHidden ? "show" : "hide"} /></button></div><ClaimAssertion claim={claim} contextName={contextName} />{claim.conditional && claim.condition_text && <p className="claim-condition"><b>Prerequisite:</b> {claim.condition_text}</p>}{visibleSources.has(claim.claim_id) && visibilitySettings.recordsVisibility.sources && <div className="record-source">{claim.source_excerpt && normalized(claim.source_excerpt) !== normalized(claim.assertion_text) && <pre>{claim.source_excerpt}</pre>}{claim.sources?.map((source) => <code key={source.document_id}>{source.path}</code>)}</div>}</article>;
    })}</div> : <p className="empty-section">{empty}</p>;
  };
  return <article className="document-view character-document">
    <header><b>{profile.kind === "pc" ? "Player character" : "Non-player character"}</b><span>Campaign character</span><div className="entry-page-actions">{onWriteDescription && <button aria-label={`Write description for ${profile.name}`} onClick={onWriteDescription} title="Write description — give this entry its page" type="button"><RecordIcon kind="unpaged" /></button>}{onEdit && <button aria-label={`Edit ${profile.kind.toUpperCase()} page`} onClick={onEdit} title="Edit" type="button"><RecordIcon kind="edit" /></button>}</div></header>
    <section className="character-profile">
      <div><span>{profile.kind === "pc" ? "Player character" : "Non-player character"}</span><h1>{profile.name}</h1></div>
      <dl>
        {profile.kind === "pc" && <Field label="Player" value={profile.player} />}
        <Field label="Race" value={profile.race} />
        <Field label="Sex" value={profile.sex} />
        <Field label="Status" value={profile.status} />
        {lifeStatus?.status && <div><dt><Term term="life-status">Life status</Term></dt><dd>{display(lifeStatus.status)}{lifeStatus.since ? ` (since ${lifeStatus.since})` : ""}</dd></div>}
      </dl>
    </section>
    <section className="character-content"><h2>Background</h2>{profile.background ? <pre>{profile.background}</pre> : <p className="empty-section">No authoritative background recorded.</p>}</section>
    {(() => {
      const dossierClaims = (dossierClaimIds && onDemoteClaim)
        ? claims.filter((claim) => dossierClaimIds.has(claim.claim_id))
        : [];
      return dossierClaims.length > 0 && <section aria-label="Dossier" className="character-content character-dossier"><h2>Dossier</h2><div>{dossierClaims.map((claim) => <section className="dossier-fact-card" key={claim.claim_id}>
        <div className="record-card-actions"><button aria-label={`Demote from Dossier: ${claim.assertion_text.slice(0, 40)}`} onClick={() => onDemoteClaim!(claim.claim_id)} title="Demote from Dossier — back under the hood only" type="button"><RecordIcon kind="hide" /></button></div>
        <EntryText text={claim.assertion_text} />
      </section>)}</div></section>;
    })()}
    {profile.kind === "npc" && <section className="character-content character-dossier"><h2>Character dossier</h2><div>{(profile.sections ?? []).filter((section) => !["background/history", "background / history", "current status/goals", "current goals", "goals & motivations", "references", "notes"].includes(section.title.toLocaleLowerCase())).map((section) => <section key={section.title}><h3>{section.title}</h3><EntryText text={section.content} /></section>)}</div></section>}
    <details className="records-hood" aria-label="Records (under the hood)"><summary><RecordIcon kind="records" /> Records — claims and sources</summary>
      <button aria-label={showHidden ? "Hide hidden records" : "Show hidden records"} disabled={hiddenClaims.size === 0} onClick={() => setShowHidden((value) => !value)} title={hiddenClaims.size === 0 ? "No hidden records" : showHidden ? "Hide hidden" : "Show hidden"} type="button"><RecordIcon kind={showHidden ? "hide" : "show"} /> {showHidden ? "Hide hidden" : "Show hidden"}</button>
      {profile.kind === "npc" && <section className="character-content"><h3>Known facts</h3><ClaimList projection="lore_fact" empty="None" /></section>}
      <section className="character-content"><h3>Real-play facts</h3><ClaimList projection="real_play" empty="None" /></section>
      {profile.kind === "pc" && <section className="character-content"><h3>Player plans</h3><ClaimList projection="player_plan" empty="None" /></section>}
      {profile.kind === "npc" && <section className="character-content"><h3>NPC plans</h3><ClaimList projection="npc_plan" empty="None" /></section>}
      <EntrySourceDrawer fallbackPath={path} sources={sources} />
    </details>
    <section className="character-content"><h2>DM plans</h2><ClaimList projection="dm_plan" empty="None" /></section>
    {claimHistory.length > 0 && <section className="character-content claim-history"><details><summary>Earlier versions ({claimHistory.length})</summary>{claimHistory.map((claim) => <article key={claim.claim_id}><p>{claim.assertion_text}</p><small>Superseded: {claim.supersession_reason}</small>{claim.source_excerpt && <details><summary>Source evidence</summary><pre>{claim.source_excerpt}</pre></details>}</article>)}</details></section>}
    <EntrySourceDrawer fallbackPath={path} sources={sources} />
  </article>;
}

function CharacterProfileEditor({ profile, kind, changedFields, preview, onChange, onCancel, onReview, onSave, entityId, lifeStatus, onLifeStatus }: {
  profile: PCProfile;
  kind: "pc" | "npc";
  changedFields: string[];
  preview: boolean;
  onChange: (profile: PCProfile) => void;
  onCancel: () => void;
  onReview: () => void;
  onSave: () => void;
  entityId?: string;
  lifeStatus?: { status: string | null; since: string | null };
  onLifeStatus?: (status: string | null, since: { year: number; month: number; day: number } | null) => void;
}) {
  const label = kind.toUpperCase();
  const [lifeStatusDraft, setLifeStatusDraft] = useState<string | null>(lifeStatus?.status ?? null);
  const [lifeSinceDraft, setLifeSinceDraft] = useState<string>(lifeStatus?.since ?? "");
  const commitLifeStatus = (status: string | null, since: string) => {
    if (!onLifeStatus) return;
    setLifeStatusDraft(status); setLifeSinceDraft(since);
    const match = since.match(/^(\d{1,6})-(\d{1,2})-(\d{1,2})$/);
    if (!status || !match) return;
    onLifeStatus(status, { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) });
  };
  return <article className="document-view pc-editor">
    <header><b>{kind === "pc" ? "Player character" : "Non-player character"}</b><span>Editing version {profile.version}</span></header>
    <section className="character-content">
      <div className="form-grid">
        <label>Name<input aria-label={`${label} name`} value={profile.canonical_name} onChange={(event) => onChange({ ...profile, canonical_name: event.target.value })} /></label>
        {kind === "pc" && <label>Player<input aria-label="PC player" value={profile.player ?? ""} onChange={(event) => onChange({ ...profile, player: event.target.value })} /></label>}
        <label>Race<input aria-label={`${label} race`} value={profile.race ?? ""} onChange={(event) => onChange({ ...profile, race: event.target.value || undefined })} /></label>
        <label>Sex<input aria-label={`${label} sex`} value={profile.sex ?? ""} onChange={(event) => onChange({ ...profile, sex: event.target.value || undefined })} /></label>
        <label>Status<input aria-label={`${label} status`} value={profile.status} onChange={(event) => onChange({ ...profile, status: event.target.value })} /></label>
        {entityId && onLifeStatus && <div className="life-status-field">
          <label>Life status<select aria-label={`${label} life status`} value={lifeStatusDraft ?? ""} onChange={(event) => commitLifeStatus(event.target.value || null, lifeSinceDraft)}>
            <option value="">Not set</option>
            <option value="alive">Alive</option>
            <option value="dead">Dead</option>
            <option value="undead">Undead</option>
            <option value="resurrected">Resurrected</option>
            <option value="immortal">Immortal</option>
            <option value="unknown">Unknown</option>
          </select></label>
          {lifeStatusDraft && <label>Since<input aria-label={`${label} life status since`} placeholder="505-11-05" value={lifeSinceDraft} onChange={(event) => commitLifeStatus(lifeStatusDraft, event.target.value)} /></label>}
        </div>}
        {/* The in-progress (last) segment keeps its trailing space mid-word; its leading space would double the join separator, so it is start-trimmed. */}
        <label>Aliases<input aria-label={`${label} aliases`} value={profile.aliases.join(", ")} onChange={(event) => onChange({ ...profile, aliases: event.target.value.split(",").map((value, index, all) => index < all.length - 1 ? value.trim() : value.trimStart()) })} onBlur={(event) => onChange({ ...profile, aliases: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></label>
      </div>
      <label className="pc-background-field">Background<textarea aria-label={`${label} background`} rows={14} value={profile.background} onChange={(event) => onChange({ ...profile, background: event.target.value })} /></label>
      {preview && <section className="pc-change-preview" aria-label={`${label} profile change review`}><div><h2>Save these changes?</h2><p>{changedFields.length === 1 ? "1 field changed" : `${changedFields.length} fields changed`}: {changedFields.join(", ")}.</p></div><button onClick={onSave} type="button">Save changes</button></section>}
      <div className="step-actions"><button className="text-button" onClick={onCancel} type="button">Cancel</button><button disabled={!profile.canonical_name.trim() || (kind === "pc" && !profile.player?.trim()) || !profile.status.trim() || changedFields.length === 0} onClick={onReview} type="button">Review changes</button></div>
    </section>
  </article>;
}

export function normalizeEntryName(value: string): string {
  return value.toLocaleLowerCase().replace(/['’]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
}

export function selectEntrySource(entry: Pick<LibraryEntrySummary, "canonical_name" | "entity_kind">, sources: { document_id: string; path: string }[], entityNames: string[] = []): { document_id: string; path: string } | undefined {
  if (sources.length === 0) return undefined;
  // TKT-0147: sheets are evidence, never pages — only authored entities/
  // descriptions and (transitionally) location writeups render as pages.
  const preferredRoot = ({ location: "locations/" } as Partial<Record<EntityKind, string>>)[entry.entity_kind];
  const normalizedName = entry.canonical_name.toLocaleLowerCase().replace(/['’]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
  const nameTokens = new Set(normalizedName.split(" ").filter((token) => token.length > 2 && !["the", "of", "and", "for"].includes(token)));
  const stemOf = (source: { path: string }) =>
    source.path.toLocaleLowerCase().split("/").pop()!.replace(/\.md$/, "").replace(/['’]/g, "");
  // Generic words a lore writeup may append to the entity's name
  // ("thanore-history.md" is Thanore's page; "vika-lana-journal.md" is a
  // player handout, so journal/diary/notes stay foreign).
  const FILENAME_GENERIC = new Set(["the", "of", "and", "for", "history", "myth", "lore", "legend"]);
  const distinctive = (tokens: string[]) =>
    tokens.filter((token) => token.length > 2 && !FILENAME_GENERIC.has(token));
  // A document may represent an entity only when its filename uses nothing
  // beyond the entity's own name. Dropping qualifier words is fine
  // ("Monastery of Arkin" -> monastery.md), but a foreign word means sibling
  // subject matter, not this entry's page ("Council of Unity" must not borrow
  // heart-of-unity.md; "Romulus" must not borrow the-wrath-of-romulus.md).
  // An exact filename match always wins when one exists.
  // A filename that is exactly another entity's name belongs to that entity,
  // even when this entity's name contains it ("Council of Unity" must not
  // borrow unity.md — that is the city Unity's page).
  const otherEntityNames = new Set(entityNames.map(normalizeEntryName).filter((name) => name !== normalizedName));
  const exact = sources.filter((source) => stemOf(source).replace(/-/g, " ") === normalizedName);
  if (exact.length > 0) {
    // The authored description page (entities/) IS the entry's page by
    // definition — it outranks an imported document that happens to share
    // the name (Fleurite's locations/ writeup defers to entities/fleurite.md).
    const score = (source: { path: string }) =>
      source.path.toLocaleLowerCase().startsWith("entities/") ? 2
        : (preferredRoot && source.path.toLocaleLowerCase().startsWith(preferredRoot) ? 1 : 0);
    return [...exact].sort((left, right) => score(right) - score(left) || left.path.localeCompare(right.path))[0];
  }
  const stemTokensOf = (source: { path: string }) => distinctive(stemOf(source).split(/[^a-z0-9']+/));
  const named = sources.filter((source) => {
    const stem = stemOf(source).replace(/-/g, " ");
    if (otherEntityNames.has(stem)) return false;
    const stemTokens = stemTokensOf(source);
    return stemTokens.length > 0 && stemTokens.every((token) => nameTokens.has(token));
  });
  if (named.length === 0) return undefined;
  const score = (source: { path: string }) =>
    (source.path.toLocaleLowerCase().startsWith("entities/") ? 3
      : preferredRoot && source.path.toLocaleLowerCase().startsWith(preferredRoot) ? 2 : 0) + stemTokensOf(source).length;
  return [...named].sort((left, right) => score(right) - score(left) || left.path.localeCompare(right.path))[0];
}

// Claim-history rows are exactly the entry's superseded claims; a referenced
// claim appearing there means the page's citation is out of date.
export function supersededReferenceCount(referenced: string[], history: { claim_id: string }[]): number {
  const superseded = new Set(history.map((claim) => claim.claim_id));
  return referenced.filter((id) => superseded.has(id)).length;
}

export function synthesizedEntryDocument(entry: Pick<LibraryEntrySummary, "canonical_name" | "entity_kind" | "aliases"> & { members?: LibraryMember[]; related?: string[] }, profile?: EntityProfile | null): string {
  // Identities without a source file of their own still deserve a proper
  // entry page: kind frontmatter the viewers recognize, a kind-appropriate
  // section heading, and the canonical-name heading the hero renders.
  const section = ({ pc: "Current Status", npc: "Current Status", location: "Established Facts",
    worldbuilding: "Lore", item: "Details", event: "Account",
    rules_element: "Rules" } as Record<string, string>)[entry.entity_kind] ?? "Established Facts";
  // Factions carry no synthesized section heading: nothing can populate it —
  // an empty titled section is a phantom block on the page.
  // Members render from roster data in the template view (TKT-0121), not as
  // markdown — structured data keeps roles/★ even for authored descriptions.
  const memberNames = "";
  const aliases = entry.aliases.length > 0 ? `aliases: ${entry.aliases.join(", ")}\n` : "";
  const profileLine = (key: string, value?: string | null) =>
    value ? `${key}: ${value}\n` : "";
  const profileFrontmatter = [
    profileLine("location_type", profile?.location_type),
    profileLine("status", profile?.status),
    profileLine("parent_location", profile?.parent_location),
    profileLine("base_location", profile?.base_location),
    profileLine("race", profile?.race),
    profileLine("sex", profile?.sex),
    profileLine("player", profile?.player),
  ].join("");
  // The profile summary field is retired (2026-09-21): authored prose lives in
  // Descriptions through the pipeline, never as a canon-side blob.
  const sectionBlock = entry.entity_kind === "faction" ? "" : `\n## ${section}\n`;
  return `---\ntype: ${entry.entity_kind === "worldbuilding" ? "lore" : entry.entity_kind}\n${aliases}${profileFrontmatter}---\n\n# ${entry.canonical_name}\n${sectionBlock}${memberNames}`;
}

function MemberRoleControl({ member, roles, onAssign }: { member: LibraryMember; roles: FactionRole[]; onAssign: (roleName: string | null, isLeadership: boolean) => void }) {
  const [newRoleOpen, setNewRoleOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleLeadership, setNewRoleLeadership] = useState(false);
  const current = member.role_title ?? "";
  return <span className="member-role-control">
    <select aria-label={`Role for ${member.name}`} value={newRoleOpen ? "__new" : current} onChange={(event) => {
      const value = event.target.value;
      if (value === "__new") { setNewRoleOpen(true); setNewRoleName(""); setNewRoleLeadership(false); return; }
      setNewRoleOpen(false);
      if (value !== current) onAssign(value || null, false);
    }}>
      <option value="">No role</option>
      {member.role_title && !roles.some((role) => role.name === member.role_title) && <option value={member.role_title}>{member.role_title} (outside catalog)</option>}
      {roles.map((role) => <option key={role.name} value={role.name}>
        {role.name}{role.is_leadership ? " ★" : ""}{role.holder_names.length > 0 && !role.holder_names.includes(member.name) ? ` (held by ${role.holder_names.join(", ")})` : ""}
      </option>)}
      <option value="__new">New role…</option>
    </select>
    {newRoleOpen && <span className="member-role-new">
      <input aria-label={`New role name for ${member.name}`} placeholder="Role name" value={newRoleName} onChange={(event) => setNewRoleName(event.target.value)} />
      <label className="member-role-leadership"><input checked={newRoleLeadership} onChange={(event) => setNewRoleLeadership(event.target.checked)} type="checkbox" />Leadership ★</label>
      <button className="text-button" disabled={!newRoleName.trim()} onClick={() => { onAssign(newRoleName.trim(), newRoleLeadership); setNewRoleOpen(false); }} type="button">Assign</button>
      <button className="text-button" onClick={() => setNewRoleOpen(false)} type="button">Cancel</button>
    </span>}
  </span>;
}

function EntityProfileEditor({ entry, profile, onChange, onCancel, onSave, message, messageIsError, onKindChange, members, roles, memberSearch, memberResults, onMemberSearch, onAddMember, onRemoveMember, onAssignRole, vocabularies, locationNames }: {
  entry: LibraryEntrySummary; profile: EntityProfile; onChange: (profile: EntityProfile) => void;
  onCancel: () => void; onSave: () => void; message: string; messageIsError?: boolean; onKindChange?: (kind: string) => void;
  members?: LibraryMember[]; roles?: FactionRole[]; memberSearch?: string; memberResults?: EntityIdentity[];
  onMemberSearch?: (value: string) => void; onAddMember?: (member: EntityIdentity) => void;
  onRemoveMember?: (member: LibraryMember) => void; onAssignRole?: (member: LibraryMember, roleName: string | null, isLeadership: boolean) => void;
  vocabularies?: Partial<Record<"location_type" | "status" | "race" | "sex", string[]>>;
  locationNames?: string[];
}) {
  const vocabSelect = (label: string, ariaLabel: string, vocabulary: "location_type" | "status" | "race" | "sex", current: string | null | undefined, apply: (value: string | null) => void) => {
    const offered = (vocabularies?.[vocabulary] ?? []).filter(Boolean);
    const known = current && offered.includes(current);
    return <label>{label}<select aria-label={ariaLabel} value={current ?? ""} onChange={(event) => apply(event.target.value || null)}>
      <option value="">Not set</option>
      {current && !known && <option value={current}>{current} (not in vocabulary)</option>}
      {offered.map((value) => <option key={value} value={value}>{value}</option>)}
    </select></label>;
  };
  const isCharacter = entry.entity_kind === "pc" || entry.entity_kind === "npc";
  const isLocation = entry.entity_kind === "location";
  return <article className="document-view entity-profile-editor" aria-label="Identity profile editor">
    <header><b>{display(entry.entity_kind)} identity</b><span>Editing version {profile.version}</span></header>
    <section className="character-content">
      <b className="identity-section-label">Attributes</b>
      <div className="form-grid">
        <label>Name<input aria-label="Identity name" value={profile.canonical_name} onChange={(event) => onChange({ ...profile, canonical_name: event.target.value })} /></label>
        {entry.entity_kind === "pc" && <label>Player<input aria-label="Identity player" value={profile.player ?? ""} onChange={(event) => onChange({ ...profile, player: event.target.value })} /></label>}
        {isCharacter && vocabSelect("Race", "Identity race", "race", profile.race, (value) => onChange({ ...profile, race: value ?? undefined }))}
        {isCharacter && vocabSelect("Sex", "Identity sex", "sex", profile.sex, (value) => onChange({ ...profile, sex: value ?? undefined }))}
        {isLocation && vocabSelect("Location type", "Identity location type", "location_type", profile.location_type, (value) => onChange({ ...profile, location_type: value }))}
        {isLocation && <label>Parent location<select aria-label="Identity parent location" value={profile.parent_location ?? ""} onChange={(event) => onChange({ ...profile, parent_location: event.target.value || null })}>
          <option value="">Not set</option>
          {(locationNames ?? []).filter((name) => name !== entry.canonical_name).map((name) => <option key={name} value={name}>{name}</option>)}
          {profile.parent_location && !(locationNames ?? []).includes(profile.parent_location) && <option value={profile.parent_location}>{profile.parent_location} (no matching entry)</option>}
        </select></label>}
        {entry.entity_kind === "faction" && <label>Base location<input aria-label="Identity base location" placeholder="Where the faction operates" value={profile.base_location ?? ""} onChange={(event) => onChange({ ...profile, base_location: event.target.value })} /></label>}
        {vocabSelect("Status", "Identity status", "status", profile.status, (value) => onChange({ ...profile, status: value ?? "" }))}
        {isCharacter && <div className="life-status-field">
          <label><Term term="life-status">Life status</Term><select aria-label="Identity life status" value={profile.life_status ?? ""} onChange={(event) => {
            const value = event.target.value || null;
            onChange({ ...profile, life_status: value as typeof profile.life_status, life_status_since: value ? profile.life_status_since : null });
          }}>
            <option value="">Not set</option>
            <option value="alive">Alive</option>
            <option value="dead">Dead</option>
            <option value="undead">Undead</option>
            <option value="resurrected">Resurrected</option>
            <option value="immortal">Immortal</option>
            <option value="unknown">Unknown</option>
          </select></label>
          {profile.life_status && (() => {
            const since = profile.life_status_since;
            const sinceText = since ? `${since.year}-${String(since.month).padStart(2, "0")}-${String(since.day).padStart(2, "0")}` : "";
            return <label>Since<input aria-label="Life status since" placeholder="505-11-05" value={sinceText} onChange={(event) => {
              const match = event.target.value.match(/^(\d{1,6})-(\d{1,2})-(\d{1,2})$/);
              onChange({ ...profile, life_status_since: match ? { calendar_id: "gregorian-ce", year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) } : null });
            }} /></label>;
          })()}
        </div>}
        {onKindChange && <label><Term term="derived">Kind (audited)</Term><select aria-label="Identity kind correction" value={entry.entity_kind} onChange={(event) => { if (event.target.value !== entry.entity_kind) onKindChange(event.target.value); }}><option value={entry.entity_kind}>{display(entry.entity_kind)} (current)</option>{ENTITY_KINDS.filter((kind) => kind.kind !== entry.entity_kind).map((kind) => <option key={kind.kind} value={kind.kind}>{kind.label}</option>)}</select></label>}
        <label>Aliases<input aria-label="Identity aliases" value={profile.aliases.join(", ")} onChange={(event) => onChange({ ...profile, aliases: event.target.value.split(",").map((value, index, all) => index < all.length - 1 ? value.trim() : value.trimStart()) })} onBlur={(event) => onChange({ ...profile, aliases: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></label>
      </div>
      {members !== undefined && onAddMember && onRemoveMember && <div className="identity-members-editor" aria-label="Faction members">
        <b>Members (audited <Term term="roster">roster</Term>)</b>
        <span className="identity-members-legend">★ unique leadership seat</span>
        {members.length === 0 && <p className="roles-explainer">No explicit roster yet. Names this faction appears with in shared records show on the entry page as associations — add a member below to start the audited roster.</p>}
        <ul>{members.map((member) => <li key={member.member_id}>
          <span className="member-name">{member.name}</span>
          {member.role_title && <span className={member.is_leadership ? "role-chip leadership" : "role-chip"}>{member.role_title}{member.is_leadership ? " ★" : ""}</span>}
          {onAssignRole && <MemberRoleControl member={member} roles={roles ?? []} onAssign={(roleName, isLeadership) => onAssignRole(member, roleName, isLeadership)} />}
          <button className="text-button" type="button" onClick={() => onRemoveMember(member)} title="Remove membership">Remove</button>
        </li>)}</ul>
        {onMemberSearch !== undefined && <label>Add member<input aria-label="Search identities to add as member" placeholder="Search identities…" value={memberSearch ?? ""} onChange={(event) => onMemberSearch(event.target.value)} /></label>}
        {(memberResults ?? []).length > 0 && <div className="identity-target-results">{(memberResults ?? []).map((match) => <button key={match.entity_id} type="button" onClick={() => onAddMember(match)}><b>{match.canonical_name}</b><small>{display(match.entity_kind)}</small></button>)}</div>}
      </div>}
      {message && <p role={messageIsError ? "alert" : "status"} className={messageIsError ? "notice error" : undefined}>{message}</p>}
      <div className="step-actions">
        <button className="text-button" onClick={onCancel} type="button">Cancel</button>
        <button className="decision-button" disabled={!profile.canonical_name.trim()} onClick={onSave} type="button">Save identity profile</button>
      </div>
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
      <span>Review extracted claims</span>
      <p>The complete claim text is the record. Subject is required for resolution; predicate and object are optional retrieval indexes.</p>
    </header>
    <div className="extraction-draft-list">{props.drafts.map((draft, index) =>
      <article className={draft.included ? "extraction-draft" : "extraction-draft excluded"} key={draft.extractionId}>
        <label className="include-extraction"><input checked={draft.included} onChange={(event) => update(index, { included: event.target.checked })} type="checkbox" />Include claim {index + 1}</label>
        <label className="assertion-field">Assertion<textarea aria-label={`Extraction ${index + 1} assertion`} value={draft.assertionText} onChange={(event) => update(index, { assertionText: event.target.value })} /></label>
        <label>Principal subject<input aria-label={`Assertion ${index + 1} principal subject`} value={draft.subject} onChange={(event) => update(index, { subject: event.target.value })} /></label>
        <p className={`subject-resolution subject-${draft.subjectResolution}`}>{draft.subjectResolution === "focal_entity" ? "Resolved from the source's focal subject" : draft.subjectResolution === "named_identity" ? "Named identity grounded in the cited source" : draft.subjectResolution === "non_entity" ? "Source-grounded non-entity phrase — choose the principal entity before proposing" : "Unresolved model phrasing — explicitly choose or correct the principal identity"}</p>
        <details className="retrieval-indexes" onToggle={(event) => setOpenIndexes((prior) => { const next = new Set(prior); if (event.currentTarget.open) next.add(index); else next.delete(index); return next; })}>
          <summary>Optional retrieval indexes</summary>
          {openIndexes.has(index) && <div className="form-grid">
            <label>Predicate<input aria-label={`Assertion ${index + 1} index predicate`} value={draft.predicate} onChange={(event) => update(index, { predicate: event.target.value })} /></label>
            <label>Object text<input aria-label={`Assertion ${index + 1} index object`} value={draft.objectEntity} onChange={(event) => update(index, { objectEntity: event.target.value })} /></label>
          </div>}
        </details>
        <blockquote>{draft.supportingExcerpt}</blockquote>
      </article>)}</div>
    <div className="step-actions"><button className="danger-button" onClick={props.onAbandon} type="button">Abandon extraction</button><button className="text-button" onClick={props.onBack} type="button">Back to extraction</button><button disabled={!canContinue} onClick={() => props.onContinue(props.drafts.find((draft) => draft.included)?.subject.trim() ?? "")} type="button">Continue with selected claims</button></div>
  </section>;
}

const MIGRATION_STEPS = [
  "Source", "Claim", "Optional extraction", "Proposal", "Approval", "Application",
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
  const heading = ({ "GM planning": "GM planning", Worldbuilding: "Worldbuilding sources", Session: "Sessions", Handout: "Handouts" } as Record<string, string>)[family] ?? `${family}s`;
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

function FactionRolesPage({ campaignClient, factions, onRefreshLibrary, onOpenFaction }: { campaignClient: CampaignClient; factions: LibraryEntrySummary[]; onRefreshLibrary: () => void; onOpenFaction: (entryId: string) => void }) {
  const [roles, setRoles] = useState<FactionRoleSummary[] | null>(null);
  const [declarations, setDeclarations] = useState<RoleDeclarationSummary[] | null>(null);
  const [linkChoices, setLinkChoices] = useState<Record<string, { factionId: string; leadership: boolean }>>({});
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
      const [roleList, declarationList] = await Promise.all([
        campaignClient.listFactionRoles(),
        campaignClient.listRoleDeclarations().catch(() => [] as RoleDeclarationSummary[]),
      ]);
      setRoles(roleList);
      setDeclarations(declarationList);
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
      toast.push("success", done);
      await loadRoles();
      onRefreshLibrary();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error && error.message ? error.message : "Role decision failed");
      toast.push("error", error instanceof Error && error.message ? error.message : "Role decision failed");
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
      <div className="section-heading"><div><p className="kicker">Identity maintenance</p><h2>Faction Roles</h2></div><p>Every <Term term="role">role</Term> definition across <Term term="faction">factions</Term>, who holds it, and where the vacant seats are. Roles are faction-scoped titles — unique <Term term="leadership">leadership</Term> seats carry the ★.</p></div>
      <div className="identity-toolbar"><button className="secondary-button" disabled={loading || busy} onClick={() => void loadRoles()} type="button">{loading ? "Working…" : "Refresh"}</button></div>
      {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    </section>

    {declarations !== null && declarations.length > 0 && <section className="page-panel" aria-label="Unlinked role declarations">
      <h3>Declared during Identity Review — unlinked</h3>
      <p className="roles-explainer">These role surfaces were marked during review but belong to no faction yet. Link one to define it in that faction's catalog; the leadership ★ marks a unique seat.</p>
      <ul className="role-declaration-list">{declarations.map((declaration) => {
        const choice = linkChoices[declaration.normalized_surface] ?? { factionId: "", leadership: false };
        return <li key={declaration.normalized_surface} className="role-row">
          <span className="role-chip">{declaration.surface}</span>
          <span className="member-role-control">
            <select aria-label={`Link ${declaration.surface} to faction`} value={choice.factionId} onChange={(event) => setLinkChoices((current) => ({ ...current, [declaration.normalized_surface]: { ...choice, factionId: event.target.value } }))}>
              <option value="">Choose a faction…</option>
              {factions.map((faction) => <option key={faction.entry_id} value={faction.entry_id}>{faction.canonical_name}</option>)}
            </select>
            <label className="member-role-leadership"><Term term="leadership">Leadership ★</Term><input aria-label={`Leadership ★ for ${declaration.surface}`} checked={choice.leadership} onChange={(event) => setLinkChoices((current) => ({ ...current, [declaration.normalized_surface]: { ...choice, leadership: event.target.checked } }))} type="checkbox" />Leadership ★</label>
            <button className="text-button" disabled={busy || !choice.factionId} onClick={() => { const factionName = factions.find((faction) => faction.entry_id === choice.factionId)?.canonical_name ?? "the faction"; void decide(() => campaignClient.defineFactionRole(choice.factionId, declaration.surface, choice.leadership), `Linked ${declaration.surface}${choice.leadership ? " ★" : ""} to ${factionName}`).then(() => setLinkChoices((current) => { const next = { ...current }; delete next[declaration.normalized_surface]; return next; })); }} type="button">Link</button>
          </span>
        </li>; })}</ul>
    </section>}

    <section className="page-panel" aria-label="Define a role">
      <h3>Define a role</h3>
      <div className="form-grid">
        <label>Faction<select aria-label="Role faction" value={defineFaction} onChange={(event) => setDefineFaction(event.target.value)}>
          <option value="">Choose a faction…</option>
          {factions.map((faction) => <option key={faction.entry_id} value={faction.entry_id}>{faction.canonical_name}</option>)}
        </select></label>
        <label>Role name<input aria-label="New role definition name" placeholder="Grand Inquisitor" value={defineName} onChange={(event) => setDefineName(event.target.value)} /></label>
        <label className="member-role-leadership"><input checked={defineLeadership} onChange={(event) => setDefineLeadership(event.target.checked)} type="checkbox" /><Term term="leadership">Leadership ★ (unique seat)</Term></label>
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

// Underlying claim UUID from an evidence id — graph-sourced ids carry an
// entity prefix that Core's claim routes do not accept.
function underlyingClaimId(id: string): string | null {
  const graphMatch = id.match(/^graph:[0-9a-f-]+:(.+)$/i);
  const underlying = graphMatch ? graphMatch[1] : id;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(underlying)
    ? underlying
    : null;
}

// Lore workspace evidence: a claim plus the record it belongs to. The owner
// title matters twice — on screen (a Considered reference reads as ABOUT its
// owner, never as a fact of the entry being drafted) and in the prose
// material, where the model needs the same context.
type LoreEvidence = SourceDocumentClaim & { owner_name?: string };

function LoreCreationPage({ campaignClient, jobPlatform, libraryEntries, onOpenEntry, onQueueDraft, pendingDraft, onConsumeDraft, onCreated }: {
  campaignClient: CampaignClient; jobPlatform: JobPlatform;
  libraryEntries: LibraryEntrySummary[];
  onOpenEntry: (entityId: string, name: string) => void;
  onQueueDraft: (command: ProseDraftCommand, entryId: string, entryName: string) => Promise<void>;
  pendingDraft: string | null;
  onConsumeDraft: () => void;
  onCreated: () => void;
}) {
  const [queue, setQueue] = useState<LoreQueueItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<LoreQueueItem | null>(null);
  const [searchResults, setSearchResults] = useState<{ claims: LoreEvidence[]; matches: EntityIdentity[] }>({ claims: [], matches: [] });
  const [linkedClaims, setLinkedClaims] = useState<Set<string>>(() => new Set());
  const [consideredClaims, setConsideredClaims] = useState<Set<string>>(() => new Set());
  const [expandedClaims, setExpandedClaims] = useState<Set<string>>(() => new Set());
  const [linkTarget, setLinkTarget] = useState<string>("");
  const [prose, setProse] = useState("");
  const [chosenKind, setChosenKind] = useState<string>("location");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [draftBusy, setDraftBusy] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [direction, setDirection] = useState("");
  const [searchBusy, setSearchBusy] = useState(false);
  // Promotion review (ADR-0018): Lore has NO unreviewed create path — the
  // Create action derives candidates first and commits through Approve.
  const [promotionRows, setPromotionRows] = useState<PromotionRow[] | null>(null);
  const [promotionText, setPromotionText] = useState("");
  const [promotionKind, setPromotionKind] = useState("");
  const [promotionBusy, setPromotionBusy] = useState(false);
  const [promotionError, setPromotionError] = useState("");
  const promotionKey = useRef<string | null>(null);
  // AI promotion assistant (TKT-0137): wand-marked suggestions — restatement
  // matching, statement ideas, Link pre-sort. Queued as async Windmill work;
  // the set lands in the working item and survives refresh (ADR-0019). Never
  // auto-included: every suggestion is included, edited, or dismissed by the DM.
  const [suggestBusy, setSuggestBusy] = useState(false);
  const [suggestJobId, setSuggestJobId] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<LoreSuggestionSet | null>(null);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(() => new Set());
  const [suggestError, setSuggestError] = useState("");
  const suggestPollTimer = useRef<number | null>(null);
  // Evidence accordion (user ruling 2026-09-21): one branch is ALWAYS open —
  // clicking the open bar leaves it open. Opening Results parks Consider's
  // bar at the panel bottom; opening Consider slides it up under Results;
  // the open branch's list is the scroll area between the bars.
  const [evidencePanel, setEvidencePanel] = useState<"results" | "consider">("results");

  useEffect(() => subscribeLoreQueue(setQueue), []);

  // Auto-save the working file — evidence AND the workspace itself (kind,
  // direction, description). Rule of thumb for workspaces: the user should
  // never have to worry about data loss (user ruling 2026-09-21).
  useEffect(() => {
    if (!selectedItem) return;
    const kept = searchResults.claims.filter(
      (c) => linkedClaims.has(c.claim_id) || consideredClaims.has(c.claim_id));
    saveLoreEvidence(selectedItem.id, {
      claims: kept.map((c) => ({
        claim_id: c.claim_id,
        assertion_text: c.assertion_text,
        state: c.state,
        authority: c.authority,
        source_excerpt: c.source_excerpt,
        owner_name: c.owner_name,
      })),
      linkedClaimIds: [...linkedClaims],
      consideredClaimIds: [...consideredClaims],
      chosenKind,
      direction,
      prose,
      suggestionJobId: suggestJobId ?? undefined,
      suggestion: suggestion ?? undefined,
      dismissedSuggestions: [...dismissedSuggestions],
    });
  }, [selectedItem, linkedClaims, consideredClaims, searchResults.claims, chosenKind, direction, prose, suggestJobId, suggestion, dismissedSuggestions]);

  // Gather evidence for a queued name: claims that mention it, and existing
  // entities that might be what this refers to.
  const gather = useCallback(async (name: string) => {
    if (busy) return;
    setBusy(true);
    setMessageIsError(false);
    setMessage("");
    setEvidencePanel("results");
    try {
      const [claimPage, entityMatches] = await Promise.all([
        campaignClient.listSourceDocuments(),
        campaignClient.searchEntities(name).catch(() => [] as EntityIdentity[]),
      ]);
      const lower = name.toLocaleLowerCase();
      const matching: LoreEvidence[] = [];
      for (const doc of claimPage.items) {
        const full = await campaignClient.getSourceDocument(doc.document_id).catch(() => null);
        if (!full) continue;
        for (const claim of (full.canonical_claims ?? [])) {
          if (claim.assertion_text.toLocaleLowerCase().includes(lower)) {
            matching.push({
              ...claim,
              source_excerpt: claim.source_excerpt ?? undefined,
              // Backward ownership link from Core: whose record this claim is
              // about, so results can be titled and grouped by entity.
              owner_name: claim.subject_entity_name ?? undefined,
            });
          }
        }
      }
      // Gather merges exactly like search: the Considered set survives a
      // re-gather; fresh name matches replace the unconsidered pool (deduped
      // by underlying claim, so a retrieval or graph result already in the
      // working set is not duplicated).
      const underlyingId = (id: string) => {
        const graphMatch = id.match(/^graph:[0-9a-f-]+:(.+)$/i);
        return graphMatch ? graphMatch[1] : id;
      };
      setSearchResults((current) => {
        const kept = current.claims.filter((c) => consideredClaims.has(c.claim_id));
        const seen = new Set(kept.map((c) => underlyingId(c.claim_id)));
        const deduped = matching.slice(0, 30).filter((c) => {
          const id = underlyingId(c.claim_id);
          if (seen.has(id)) return false;
          seen.add(id);
          return true;
        });
        return { claims: [...kept, ...deduped], matches: entityMatches };
      });
    } catch (cause) {
      setMessageIsError(true);
      setMessage(cause instanceof Error ? cause.message : "Evidence gathering failed");
    } finally { setBusy(false); }
  }, [campaignClient, consideredClaims]);

  // Relevance search: the retrieval endpoint ranks by meaning, not just
  // exact text. Results arrive UNCHECKED; un-Considered prior results are
  // cleared so each search is a fresh pool. The graph is consulted for the
  // QUEUED NAME (not the search query) — its structural relations (seats,
  // memberships, parents) are evidence; co-mentions are context, not proof.
  const searchEvidence = useCallback(async () => {
    if (!searchQuery.trim() || searchBusy) return;
    setSearchBusy(true);
    setMessageIsError(false);
    setMessage("");
    // Searching delivers results — open the Results branch automatically.
    setEvidencePanel("results");
    try {
      const query = searchQuery.trim();
      // Graph: consult entities matching BOTH the search query and the queued
      // name. Structural relations (audited seats) are evidence; co-mentions
      // are context, shown as a compact "appears with" note per entity.
      const graphFor = async (name: string): Promise<GraphRelationRow[]> => {
        const matches = await campaignClient.searchEntities(name).catch(() => [] as EntityIdentity[]);
        const canonical = matches.find((m) => m.match_kind === "canonical") ?? matches[0];
        if (!canonical) return [] as GraphRelationRow[];
        return campaignClient.getEntityGraphNeighborhood(canonical.entity_id).catch(() => [] as GraphRelationRow[]);
      };
      const names = [query, selectedItem?.name].filter(Boolean) as string[];
      const [result, ...graphRowSets] = await Promise.all([
        campaignClient.query({ question: query, requester_visibility: { role: "dm" } }),
        ...names.map((n) => graphFor(n)),
      ]);
      // Deduplicate graph rows across all consulted entities.
      const graphSeen = new Set<string>();
      const graphRows: GraphRelationRow[] = [];
      for (const set of graphRowSets) {
        for (const row of set) {
          if (!graphSeen.has(row.text)) { graphSeen.add(row.text); graphRows.push(row); }
        }
      }
      const found: LoreEvidence[] = result.evidence.map((item) => ({
        claim_id: item.record_id,
        assertion_text: item.assertion,
        state: item.state,
        authority: item.authority,
        visibility: "dm_only",
        conditional: false,
        recorded_at: new Date().toISOString(),
        projection: "lore_fact",
        source_excerpt: item.citation,
        owner_name: item.entity_id
          ? libraryEntries.find((entry) => entry.entry_id === item.entity_id)?.canonical_name
          : undefined,
      }));
      // The graph's value is DISCOVERY: it identifies related entities whose
      // CLAIMS are the evidence. Extract entity names from graph rows, fetch
      // their top claims from the library, and present those as evidence
      // items with the graph path noted.
      const relatedNames = new Set<string>();
      for (const row of graphRows) {
        // Structural rows: "X leads Y" / "X is a member of Y" → extract X and Y.
        // Co-mention rows: "Frequently appears with X (N shared documents)" → extract X.
        const text = row.text;
        const structuralMatch = text.match(/^(.+?) (?:leads|is a member of) (.+)$/);
        if (structuralMatch) {
          relatedNames.add(structuralMatch[1].trim());
          relatedNames.add(structuralMatch[2].trim());
        }
        const coMatch = text.match(/Frequently appears with (.+?) \(/);
        if (coMatch) relatedNames.add(coMatch[1].trim());
      }
      // Remove the search subject itself.
      names.forEach((n) => relatedNames.delete(n));
      // Fetch claims from the top related entities (max 5, to keep bounded).
      const relatedEntries = libraryEntries.filter(
        (entry) => relatedNames.has(entry.canonical_name));
      const graphEvidence: LoreEvidence[] = [];
      for (const entry of relatedEntries.slice(0, 5)) {
        try {
          const libEntry = await campaignClient.getLibraryEntry(entry.entry_id);
          // Top 3 claims per related entity, labelled with the graph path.
          for (const claim of (libEntry.claims ?? []).slice(0, 3)) {
            graphEvidence.push({
              claim_id: `graph:${entry.entry_id}:${claim.claim_id}`,
              assertion_text: claim.assertion_text,
              state: claim.state,
              authority: claim.authority,
              visibility: claim.visibility,
              conditional: false,
              recorded_at: claim.recorded_at,
              projection: claim.projection,
              source_excerpt: `via graph → ${entry.canonical_name} (${display(entry.entity_kind)})`,
              owner_name: entry.canonical_name,
            });
          }
        } catch { /* related entity unavailable — skip */ }
      }
      // Keep only Considered prior results; new results arrive unchecked.
      const kept = searchResults.claims.filter((c) => consideredClaims.has(c.claim_id));
      // Deduplicate by the UNDERLYING claim UUID — graph items carry
      // graph:{entityId}:{uuid} wrappers but refer to the same claim as
      // direct retrieval results with the raw UUID.
      const underlyingId = (id: string) => {
        const graphMatch = id.match(/^graph:[0-9a-f-]+:(.+)$/i);
        return graphMatch ? graphMatch[1] : id;
      };
      const seen = new Set(kept.map((c) => underlyingId(c.claim_id)));
      const deduped = [...found, ...graphEvidence].filter((c) => {
        const id = underlyingId(c.claim_id);
        if (seen.has(id)) return false;
        seen.add(id);
        return true;
      });
      const merged = [...kept, ...deduped];
      setSearchResults((current) => ({ ...current, claims: merged }));
      // New results are NOT auto-selected.
      if (found.length === 0 && graphEvidence.length === 0) {
        setMessage(`No evidence found for "${query}" — try a broader term.`);
      }
    } catch (cause) {
      setMessageIsError(true);
      setMessage(cause instanceof Error ? cause.message : "The evidence search failed");
    } finally { setSearchBusy(false); }
  }, [campaignClient, searchQuery, searchBusy, searchResults.claims, consideredClaims, selectedItem, libraryEntries]);

  const pick = (item: LoreQueueItem) => {
    setSelectedItem(item);
    setLinkTarget("");
    setEvidencePanel("results");
    // Restore the whole working file — evidence plus kind, direction, and
    // description — so a refresh (or switching away and back) loses nothing.
    const saved = item.savedEvidence;
    setProse(saved?.prose ?? "");
    setDirection(saved?.direction ?? "");
    setChosenKind(saved?.chosenKind ?? "location");
    // The AI suggestion set rides with the working item (TKT-0137): a queued
    // job resumes polling; landed suggestions stay until reviewed.
    setSuggestJobId(saved?.suggestionJobId ?? null);
    setSuggestion(saved?.suggestion ?? null);
    setDismissedSuggestions(new Set(saved?.dismissedSuggestions ?? []));
    setSuggestError("");
    if (saved && saved.claims.length > 0) {
      const restored = saved.claims.map((c) => ({
        ...c,
        visibility: "dm_only",
        conditional: false,
        recorded_at: new Date().toISOString(),
        projection: "lore_fact" as const,
      }));
      setSearchResults({ claims: restored, matches: [] });
      setLinkedClaims(new Set(saved.linkedClaimIds));
      setConsideredClaims(new Set(saved.consideredClaimIds));
      setExpandedClaims(new Set());
    } else {
      setSearchResults({ claims: [], matches: [] });
      setLinkedClaims(new Set());
      setConsideredClaims(new Set());
      setExpandedClaims(new Set());
    }
  };

  // AI synopsis: draft from the selected evidence using the prose writer.
  const draftSynopsis = async () => {
    if (!selectedItem || draftBusy) return;
    setDraftBusy(true);
    try {
      // Material is the CONSIDERED set (Link implies Consider) — background
      // reference for the draft, each item titled with the record it is
      // actually about so the model never reads a reference as a fact of the
      // subject. With nothing selected, the queued name itself is the seed —
      // no evidence is required to draft.
      const consideredMaterial = searchResults.claims
        .filter((claim) => consideredClaims.has(claim.claim_id))
        .map((claim) => ({
          key: `claim:${claim.claim_id}`,
          kind: "claim" as const,
          text: claim.owner_name ? `[about ${claim.owner_name}] ${claim.assertion_text}` : claim.assertion_text,
          state: claim.state,
        }));
      const material = consideredMaterial.length > 0 ? consideredMaterial : [
        {
          key: `seed:${selectedItem.id}`,
          kind: "claim" as const,
          text: `${selectedItem.name} is a name queued for a new ${display(chosenKind)} entry${selectedItem.context ? ` (noted from ${selectedItem.context})` : ""}.`,
          state: "considered",
        },
      ];
      await onQueueDraft({
        subject: selectedItem.name,
        subject_kind: chosenKind,
        paragraph_limit: 3,
        direction: direction.trim() || undefined,
        material,
        idempotency_key: `lore-draft:${selectedItem.id}:${crypto.randomUUID()}`,
      }, `lore:${selectedItem.id}`, selectedItem.name);
      setMessageIsError(false);
      setMessage(`Draft queued — it will land in the Drafts tray when the model finishes.`);
      toast.push("info", `Lore draft queued for ${selectedItem.name}`);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "The synopsis could not be queued";
      setMessageIsError(true);
      setMessage(detail);
      toast.push("error", detail);
    } finally { setDraftBusy(false); }
  };

  // AI promotion suggestions (TKT-0137): queue the assistant on the seed
  // name, the current prose, and the Considered evidence. Async Windmill
  // work — the result lands in the working item when the model finishes.
  const queueSuggestions = async () => {
    if (!selectedItem || suggestBusy || suggestJobId) return;
    setSuggestBusy(true); setSuggestError("");
    try {
      const consideredMaterial = searchResults.claims
        .filter((claim) => consideredClaims.has(claim.claim_id))
        .map((claim) => ({
          key: claim.claim_id,
          text: claim.owner_name ? `[about ${claim.owner_name}] ${claim.assertion_text}` : claim.assertion_text,
          state: claim.state,
        }));
      const material = consideredMaterial.length > 0 ? consideredMaterial : [
        {
          key: `seed:${selectedItem.id}`,
          text: `${selectedItem.name} is a name queued for a new ${display(chosenKind)} entry${selectedItem.context ? ` (noted from ${selectedItem.context})` : ""}.`,
          state: "considered",
        },
      ];
      const command = {
        surface: "lore",
        subject: selectedItem.name,
        subject_kind: chosenKind,
        prose: prose.trim(),
        material,
        idempotency_key: `promotion-suggest:${selectedItem.id}:${crypto.randomUUID()}`,
      };
      const job = await jobPlatform.startPromotionSuggest(command);
      setSuggestJobId(job.jobId);
      toast.push("info", `Suggestions queued for ${selectedItem.name} — they land here when the model finishes`);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "The suggestion run could not be queued";
      setSuggestError(detail);
      toast.push("error", detail);
    } finally { setSuggestBusy(false); }
  };

  // Poll the queued suggestion job to completion; a refresh resumes from the
  // persisted job id (the working item never loses a queued run).
  useEffect(() => {
    if (!selectedItem || !suggestJobId || suggestion) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const next = await jobPlatform.inspect(suggestJobId);
        if (cancelled) return;
        if (next.state === "succeeded" && next.result && typeof next.result === "object") {
          const result = next.result as LoreSuggestionSet;
          setSuggestion(result);
          setSuggestJobId(null);
          toast.push("success", `Suggestions ready for ${selectedItem.name} — review the wand-marked rows`);
        } else if (next.state === "failed") {
          const error = next.error ?? "The suggestion job failed";
          setSuggestError(error);
          setSuggestJobId(null);
          toast.push("error", `Suggestions failed for ${selectedItem.name} — ${error}`);
        }
      } catch {
        // Transient inspect failures keep polling until the job resolves.
      }
      if (!cancelled) suggestPollTimer.current = window.setTimeout(poll, 2500);
    };
    suggestPollTimer.current = window.setTimeout(poll, 800);
    return () => {
      cancelled = true;
      if (suggestPollTimer.current !== null) window.clearTimeout(suggestPollTimer.current);
    };
  }, [selectedItem, suggestJobId, suggestion, jobPlatform]);

  const dismissSuggestion = (key: string) => {
    setDismissedSuggestions((current) => new Set(current).add(key));
  };

  // Create a new entity + file a description page for it.
  // Handles the "entity already exists" case from partial prior attempts:
  // if an entity with this name exists, file the description on IT instead
  // of failing.
  // Promotion review (mandatory — no bypass): derive candidates from the
  // prose with the Considered set as references, then Approve commits the
  // entity, description, promoted claims, and linked moves in one action.
  const reviewPromotion = async () => {
    if (!selectedItem || !prose.trim() || promotionBusy) return;
    setPromotionBusy(true); setPromotionError("");
    try {
      const derived = await campaignClient.deriveLorePromotion(
        selectedItem.name, chosenKind, prose.trim(),
        [...consideredClaims].map(underlyingClaimId).filter((id): id is string => id !== null));
      setPromotionRows(derived.candidates.map((candidate) => ({ ...candidate, conflictCleared: false })));
      setPromotionText(prose.trim());
      setPromotionKind(chosenKind);
    } catch (error) {
      setPromotionError(error instanceof Error ? error.message : "The promotion review could not be derived");
      toast.push("error", error instanceof Error ? error.message : "Promotion derive failed");
    } finally { setPromotionBusy(false); }
  };

  const commitPromotion = async () => {
    if (!selectedItem || promotionRows === null || promotionBusy) return;
    setPromotionBusy(true); setPromotionError("");
    try {
      promotionKey.current ??= `lore-promotion:${selectedItem.id}:${crypto.randomUUID()}`;
      const linkedIds = [...linkedClaims].map(underlyingClaimId).filter((id): id is string => id !== null);
      const receipt = await campaignClient.approveLorePromotion({
        entity_name: selectedItem.name,
        entity_kind: promotionKind || chosenKind,
        document_text: promotionText,
        statements: promotionRows.map((row) => ({
          span_start: row.span_start, span_end: row.span_end,
          assertion_text: row.assertion_text.trim(), state: row.state,
          included: row.included && row.consequence.kind === "new_claim",
        })),
        referenced_claim_ids: [...consideredClaims].map(underlyingClaimId).filter((id): id is string => id !== null),
        linked_claim_ids: linkedIds,
        idempotency_key: promotionKey.current,
      });
      const parts = [`+${receipt.claims_committed} claim${receipt.claims_committed === 1 ? "" : "s"}`];
      if (receipt.moved_claim_ids.length > 0) parts.push(`${receipt.moved_claim_ids.length} moved`);
      setMessageIsError(false);
      setMessage(`Created ${selectedItem.name} — ${parts.join(", ")} · receipt ${String(receipt.receipt_id ?? receipt.document_id).slice(0, 8)}${receipt.move_errors.length > 0 ? ` (${receipt.move_errors.length} linked assertion${receipt.move_errors.length === 1 ? "" : "s"} stayed put — see the Log)` : ""}`);
      toast.push("success", `Lore created — ${selectedItem.name} (${parts.join(", ")})`);
      resolveLoreItem(selectedItem.id, selectedItem.name);
      setSelectedItem(null);
      setProse("");
      setPromotionRows(null);
      setPromotionText("");
      promotionKey.current = null;
      onCreated();
    } catch (error) {
      setPromotionError(error instanceof Error ? error.message : "The promotion could not be committed");
      toast.push("error", error instanceof Error ? error.message : "Promotion commit failed");
    } finally { setPromotionBusy(false); }
  };


  // Resolve by linking to an existing entity.
  const linkEntry = async () => {
    if (!selectedItem || !linkTarget) return;
    setBusy(true);
    try {
      resolveLoreItem(selectedItem.id, linkTarget);
      setSelectedItem(null);
      setMessageIsError(false);
      setMessage(`Linked "${selectedItem.name}" to ${linkTarget}`);
      toast.push("success", `Lore resolved — ${selectedItem.name} → ${linkTarget}`);
    } finally { setBusy(false); }
  };

  const pending = queue.filter((item) => item.status === "queued");
  const resolved = queue.filter((item) => item.status === "resolved");
  const ENTITY_KIND_OPTIONS = ENTITY_KINDS.filter((k) => !["pc"].includes(k.kind));
  const backToLore = () => { setSelectedItem(null); setProse(""); };
  // Results group by the record each claim is ABOUT (user ruling 2026-09-21);
  // owner-less claims fall into a trailing "No owning record" group. The
  // Considered set groups the same way.
  const resultsClaims = searchResults.claims.filter((c) => !consideredClaims.has(c.claim_id));
  const consideredClaimsList = searchResults.claims.filter((c) => consideredClaims.has(c.claim_id));
  const groupByOwner = (claims: LoreEvidence[]): Array<{ owner: string | null; items: LoreEvidence[] }> => {
    const groups: Array<{ owner: string | null; items: LoreEvidence[] }> = [];
    for (const claim of claims) {
      const owner = claim.owner_name ?? null;
      const group = groups.find((entry) => entry.owner === owner);
      if (group) group.items.push(claim);
      else groups.push({ owner, items: [claim] });
    }
    groups.sort((left, right) => Number(left.owner === null) - Number(right.owner === null));
    return groups;
  };
  const resultsByOwner = groupByOwner(resultsClaims);
  const consideredByOwner = groupByOwner(consideredClaimsList);

  // --- AI suggestion application (TKT-0137) --------------------------------
  const normalizeStatement = (text: string) => text.toLocaleLowerCase().replace(/\s+/g, " ").trim();
  const basisText = (key: string) => {
    const claim = searchResults.claims.find((c) => c.claim_id === key || underlyingClaimId(c.claim_id) === key);
    return claim ? (claim.owner_name ? `[about ${claim.owner_name}] ${claim.assertion_text}` : claim.assertion_text) : key;
  };
  // Restatement annotations keyed by review-row sequence. Agreement coloring
  // follows the placement ruling: green = system mirror + AI agree, blue =
  // system only, orange = AI-only suggestion awaiting the DM's confirmation.
  const aiRestatements: Record<number, { claimId: string | null; materialText: string; agrees: boolean; modelSlug: string }> = {};
  if (suggestion && promotionRows) {
    for (const row of promotionRows) {
      const key = normalizeStatement(row.assertion_text);
      const restatement = suggestion.restatements.find((r) => normalizeStatement(r.statement_text) === key);
      if (!restatement || dismissedSuggestions.has(`restatement:${key}`)) continue;
      const claimId = underlyingClaimId(restatement.material_key);
      const agrees = row.consequence.kind === "reference"
        && row.consequence.claim_id !== null
        && claimId === row.consequence.claim_id;
      aiRestatements[row.sequence] = {
        claimId,
        materialText: basisText(restatement.material_key),
        agrees,
        modelSlug: suggestion.model_slug,
      };
    }
  }
  const visibleStatementSuggestions = suggestion
    ? suggestion.statements.filter((s) => !dismissedSuggestions.has(`statement:${normalizeStatement(s.text)}`))
    : [];
  const linkSuggestionFor = (claimId: string) => suggestion?.links.find((link) =>
    underlyingClaimId(link.material_key) === underlyingClaimId(claimId)
    && !dismissedSuggestions.has(`link:${link.material_key}`));

  // Working an item is its own page — the queue stays behind the Back button,
  // and both columns scroll inside a viewport-height workspace.
  if (selectedItem) return <main className="page-lore lore-working" aria-label="Lore creation workspace page">
    <div className="lore-working-header">
      <button className="text-button" onClick={backToLore} type="button">← Back to Lore</button>
      <p className="kicker">Lore creation</p>
    </div>
    <section className="lore-workspace" aria-label="Lore creation workspace">
      <div className="lore-workspace-main">
        {message && <div className={"notice" + (messageIsError ? " error" : "")} role={messageIsError ? "alert" : "status"} style={{ margin: 0 }}>{message}</div>}
        <h3>Creating: {selectedItem.name}</h3>

        <div className="form-grid">
          <label>Entity kind<select aria-label="Lore entity kind" value={chosenKind} onChange={(event) => setChosenKind(event.target.value)}>
            {ENTITY_KIND_OPTIONS.map((k) => <option key={k.kind} value={k.kind}>{k.label}</option>)}
          </select></label>
        </div>

        {searchResults.matches.length > 0 && <div className="lore-existing-matches">
          <b>Existing entities with this name:</b>
          {searchResults.matches.map((match) => <label key={match.entity_id} className="lore-match-row">
            <input checked={linkTarget === match.canonical_name} onChange={() => setLinkTarget(linkTarget === match.canonical_name ? "" : match.canonical_name)} type="radio" />
            <span>{match.canonical_name} ({display(match.entity_kind)})</span>
          </label>)}
        </div>}

        <label className="pc-background-field session-notes-field lore-direction-field">AI direction (optional — shapes the draft's emphasis)<textarea aria-label="AI direction for the draft" placeholder="e.g. Focus on the statue's significance, the secrecy around it, and what the treasury means to Fleurite's power structure…" rows={3} value={direction} onChange={(event) => setDirection(event.target.value)} /></label>

        <div className="composer-draft-row">
          <button className="secondary-button" disabled={draftBusy || busy} onClick={() => void draftSynopsis()} type="button"><WandIcon />{draftBusy ? "Drafting…" : "Draft synopsis"}</button>
          <button className="secondary-button" disabled={suggestBusy || suggestJobId !== null} onClick={() => void queueSuggestions()} type="button"><WandIcon />{suggestJobId ? "Suggesting…" : "Suggest"}</button>
          <small className="ai-activation-note">Draft synopsis drafts prose from the Considered evidence into the Drafts tray. Suggest runs the promotion assistant: restatement matches, statement ideas, and a Link pre-sort — wand-marked suggestions, never auto-included.</small>
        </div>
        {suggestJobId && <p className="ai-activation-note" role="status">Promotion assistant running for {selectedItem.name} — suggestions land here when the model finishes.</p>}
        {suggestError && <div className="notice error" role="alert" style={{ margin: 0 }}>{suggestError}</div>}
        {suggestion && visibleStatementSuggestions.length > 0 && <section className="lore-suggestions" aria-label="AI-suggested statements">
          <header><span><WandIcon /> AI suggestions</span><h4>Statements {selectedItem.name} might assert</h4>
            <small className="ai-activation-note">suggested by {suggestion.model_slug} · {suggestion.prompt_version} — never auto-included; inserting adds the sentence to your description, where promotion review derives it</small></header>
          {visibleStatementSuggestions.map((s) => <article className="lore-suggestion-row" key={s.text}>
            <p className="lore-evidence-text">{s.text}</p>
            <div className="lore-evidence-header">
              <span className="role-chip ai-suggestion-chip">{display(s.state)}</span>
              <span className="ai-suggestion-basis">based on: {basisText(s.basis_key)}</span>
              <button className="text-button" onClick={() => {
                setProse((current) => current.trim() ? `${current.trim()} ${s.text}` : s.text);
                dismissSuggestion(`statement:${normalizeStatement(s.text)}`);
                toast.push("info", "Inserted — review the promotion again to derive it");
              }} type="button">Insert into description</button>
              <button className="text-button" onClick={() => dismissSuggestion(`statement:${normalizeStatement(s.text)}`)} type="button">Dismiss</button>
            </div>
          </article>)}
        </section>}

        {pendingDraft && <div className="lore-draft-ready notice" role="status">
          <span>AI draft ready for {selectedItem.name}:</span>
          <button className="text-button" onClick={() => { setProse(pendingDraft); onConsumeDraft(); toast.push("info", "Draft inserted — review before creating"); }} type="button">Insert into description</button>
        </div>}
        <label className="pc-background-field session-notes-field">Description (the new entry's page)<textarea aria-label="Lore description" placeholder={`Write ${selectedItem.name}'s page — what it is, why it matters…`} rows={10} value={prose} onChange={(event) => setProse(event.target.value)} /></label>

        {promotionRows !== null && <PromotionReviewList
          entityName={selectedItem.name}
          rows={promotionRows}
          stale={prose.trim() !== promotionText || chosenKind !== promotionKind}
          busy={promotionBusy}
          error={promotionError}
          bundleLabel={`new ${display(promotionKind || chosenKind)}`}
          emptyLabel={`Create ${selectedItem.name}`}
          aiRestatements={Object.keys(aiRestatements).length > 0 ? aiRestatements : undefined}
          onRowChange={(sequence, patch) => setPromotionRows((current) => current?.map((row) => row.sequence === sequence ? { ...row, ...patch } : row) ?? null)}
          onMarkReference={(sequence, claimId, modelSlug) => setPromotionRows((current) => current?.map((row) => row.sequence === sequence
            ? { ...row, consequence: { kind: "reference", claim_id: claimId, label: `restatement — AI-suggested, DM-confirmed (${modelSlug})` } }
            : row) ?? null)}
          onDismissAiNote={(sequence) => {
            const row = promotionRows.find((r) => r.sequence === sequence);
            if (row) dismissSuggestion(`restatement:${normalizeStatement(row.assertion_text)}`);
          }}
          onCommit={() => void commitPromotion()}
          onDismiss={() => { setPromotionRows(null); setPromotionError(""); }}
        />}

        <div className="step-actions">
          {linkTarget
            ? <button disabled={busy} onClick={() => void linkEntry()} type="button">Link to {linkTarget}</button>
            : <button className="decision-button" disabled={busy || promotionBusy || !prose.trim()} onClick={() => void reviewPromotion()} type="button">{promotionBusy ? "Reviewing…" : `Review promotion — create ${selectedItem.name}`}</button>}
        </div>
      </div>

      <aside className="lore-evidence-panel" aria-label="Lore evidence">
        <header><span>Evidence</span><h2>Gathered for {selectedItem.name}</h2>
          <p>Consider keeps a claim as draft background; Link moves it to the new entry when created. Gather scans for the exact name; Search ranks passages by relevance and consults the graph.</p></header>
        <div className="lore-panel-search">
          <input aria-label="Lore evidence search" onChange={(event) => setSearchQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void searchEvidence(); } }} placeholder="treasure, wealth, vault…" value={searchQuery} />
          <button className="secondary-button" disabled={searchBusy || !searchQuery.trim()} onClick={() => void searchEvidence()} type="button">{searchBusy ? "Searching…" : "Search"}</button>
          <button className="text-button" disabled={busy} onClick={() => selectedItem && void gather(selectedItem.name)} type="button">{busy ? "Gathering…" : "Gather by name"}</button>
        </div>
        <button aria-expanded={evidencePanel === "results"} className="lore-panel-bar results-bar" onClick={() => setEvidencePanel("results")} type="button">Results <span>{searchResults.claims.filter((c) => !consideredClaims.has(c.claim_id)).length}</span></button>
        <div aria-hidden={evidencePanel !== "results"} className={"lore-scroll" + (evidencePanel === "results" ? " open" : "")}>
        <div aria-label="Search results" className="lore-panel-section">
          {busy && <p className="empty-section">Gathering…</p>}
          {resultsByOwner.map((group) => <div className="lore-result-group" key={group.owner ?? "__none"}>
            <div className="lore-group-heading"><b>{group.owner ?? "No owning record"}</b><span>{group.items.length} claim{group.items.length === 1 ? "" : "s"}</span></div>
            {group.items.map((claim) => <article className="lore-evidence-item" key={claim.claim_id}>
            <div className="lore-evidence-header">
              <label><input aria-label={"Consider evidence: " + claim.assertion_text.slice(0, 40)} checked={consideredClaims.has(claim.claim_id)} onChange={(event) => {
                const next = new Set(consideredClaims);
                event.target.checked ? next.add(claim.claim_id) : next.delete(claim.claim_id);
                setConsideredClaims(next);
              }} type="checkbox" /> Consider</label>
              <label title="Ownership: this assertion moves from its current owner to the new entity when created" ><input aria-label={"Link evidence (re-attribute): " + claim.assertion_text.slice(0, 40)} checked={linkedClaims.has(claim.claim_id)} onChange={(event) => {
                const next = new Set(linkedClaims);
                if (event.target.checked) {
                  next.add(claim.claim_id);
                  setConsideredClaims((cur) => new Set(cur).add(claim.claim_id));
                } else next.delete(claim.claim_id);
                setLinkedClaims(next);
              }} type="checkbox" /> Link <small className="lore-link-annotation">← moves to this entity</small></label>
              <span className="role-chip">{display(claim.state)}</span>
              <span className="role-chip">{display(claim.authority)}</span>
              {claim.claim_id.startsWith("graph:") && <span className="role-chip graph-chip">graph</span>}
            </div>
            <p className={"lore-evidence-text" + (expandedClaims.has(claim.claim_id) ? "" : " clamped")} onClick={() => setExpandedClaims((cur) => {
              const next = new Set(cur);
              cur.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id);
              return next;
            })}>{claim.assertion_text}</p>
            {claim.source_excerpt && <code className="lore-evidence-source">{claim.source_excerpt}</code>}
          </article>)}
          </div>)}
          {!busy && resultsClaims.length === 0 && <p className="empty-section">No results yet — search for evidence or gather by name.</p>}
        </div>
        </div>
        <button aria-expanded={evidencePanel === "consider"} className="lore-panel-bar consider-bar" onClick={() => setEvidencePanel("consider")} type="button">Consider <span>{consideredClaims.size}</span></button>
        <div aria-hidden={evidencePanel !== "consider"} className={"lore-scroll" + (evidencePanel === "consider" ? " open" : "")}>
        <div aria-label="Considered evidence" className="lore-panel-section">
          {consideredByOwner.map((group) => <div className="lore-result-group" key={group.owner ?? "__none"}>
            <div className="lore-group-heading"><b>{group.owner ?? "No owning record"}</b><span>{group.items.length} claim{group.items.length === 1 ? "" : "s"}</span></div>
            {group.items.map((claim) => <article className="lore-evidence-item" key={claim.claim_id}>
            <div className="lore-evidence-header">
              <label><input aria-label={"Unconsider: " + claim.assertion_text.slice(0, 40)} checked onChange={() => setConsideredClaims((cur) => {
                const next = new Set(cur);
                next.delete(claim.claim_id);
                return next;
              })} type="checkbox" /> Consider</label>
              <label><input aria-label={"Link considered: " + claim.assertion_text.slice(0, 40)} checked={linkedClaims.has(claim.claim_id)} onChange={(event) => {
                const next = new Set(linkedClaims);
                event.target.checked ? next.add(claim.claim_id) : next.delete(claim.claim_id);
                setLinkedClaims(next);
              }} type="checkbox" /> Link</label>
              <span className="role-chip">{display(claim.state)}</span>
              <span className="role-chip">{display(claim.authority)}</span>
              {claim.claim_id.startsWith("graph:") && <span className="role-chip graph-chip">graph</span>}
              {linkSuggestionFor(claim.claim_id) && !linkedClaims.has(claim.claim_id) && <span className="role-chip ai-suggestion-chip"><WandIcon /> Link — {linkSuggestionFor(claim.claim_id)!.reason}</span>}
            </div>
            <p className={"lore-evidence-text" + (expandedClaims.has(claim.claim_id) ? "" : " clamped")} onClick={() => setExpandedClaims((cur) => {
              const next = new Set(cur);
              cur.has(claim.claim_id) ? next.delete(claim.claim_id) : next.add(claim.claim_id);
              return next;
            })}>{claim.assertion_text}</p>
            {claim.source_excerpt && <code className="lore-evidence-source">{claim.source_excerpt}</code>}
          </article>)}
          </div>)}
          {consideredClaims.size === 0 && <p className="empty-section">Nothing considered yet — check Consider on a result to keep it as draft background.</p>}
        </div>
        </div>
      </aside>
    </section>
  </main>;

  return <main className="page-lore">
    <section className="identity-page-header" aria-label="Lore creation">
      <div className="section-heading"><div><p className="kicker">Capture to canon</p><h2>Lore</h2></div>
        <p>Names that need campaign entries. Queue from the Library, gather evidence, review, and create — nothing becomes canon without your explicit action.</p></div>
    </section>

    <section className="page-panel settings-panel" aria-label="Queue a name">
      <h3>Queue a name</h3>
      <QueueForLoreForm onQueued={() => {}} />
    </section>

    {pending.length > 0 && <section className="page-panel" aria-label="Lore queue">
      <h3>Pending ({pending.length})</h3>
      {pending.map((item) => <article key={item.id} className="lore-queue-item">
        <div><b>{item.name}</b>{item.context && <small> · {item.context}</small>}</div>
        <small>{new Date(item.queuedAt).toLocaleDateString()}</small>
        <div className="lore-item-actions">
          <button onClick={() => pick(item)} type="button">Work this</button>
          <button className="text-button" onClick={() => dismissLoreItem(item.id)} type="button">Dismiss</button>
        </div>
      </article>)}
    </section>}

    {message && <div className={"notice" + (messageIsError ? " error" : "")} role={messageIsError ? "alert" : "status"} style={{ margin: "14px 0" }}>{message}</div>}

    {resolved.length > 0 && <details className="lore-resolved-history"><summary>Resolved ({resolved.length})</summary>
      {resolved.map((item) => <p key={item.id}><b>{item.name}</b> → {item.resolvedAs}</p>)}
    </details>}
  </main>;
}

function QueueForLoreForm({ onQueued }: { onQueued: (name: string) => void }) {
  const [name, setName] = useState("");
  const [context, setContext] = useState("");
  const queued = queueForLore;
  return <div className="lore-queue-form">
    <label>Name<input aria-label="Lore queue name" onChange={(event) => setName(event.target.value)} placeholder="Tsunadis" value={name} /></label>
    <label>Context (optional)<input aria-label="Lore queue context" onChange={(event) => setContext(event.target.value)} placeholder="encounters/floor3.md" value={context} /></label>
    <button disabled={!name.trim()} onClick={() => {
      try {
        const item = queued(name, context);
        setName(""); setContext("");
        toast.push("success", `Queued "${item.name}" for Lore`);
        onQueued(item.name);
      } catch (error) {
        toast.push("error", error instanceof Error ? error.message : "Could not queue");
      }
    }} type="button">Queue for Lore</button>
  </div>;
}

function AIModelSettings({ campaignClient }: { campaignClient: CampaignClient }) {
  const [configuration, setConfiguration] = useState<AIConfigurationSnapshot | null>(null);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [busyPurpose, setBusyPurpose] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void campaignClient.getAIConfiguration().then((snapshot) => {
      setConfiguration(snapshot);
      setSelected(snapshot.active_profile_by_purpose);
      setError("");
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "AI configuration unavailable"));
  }, [campaignClient]);

  async function activate(purpose: AIPurposeInfo) {
    const profileKey = selected[purpose.key];
    if (!profileKey || profileKey === configuration?.active_profile_by_purpose[purpose.key]) return;
    setBusyPurpose(purpose.key);
    try {
      await campaignClient.activateAIProfile(profileKey, purpose.key);
      const snapshot = await campaignClient.getAIConfiguration();
      setConfiguration(snapshot);
      setSelected(snapshot.active_profile_by_purpose);
      setError("");
      const profile = snapshot.profiles.find((item) => item.key === profileKey);
      toast.push("success", `${purpose.label} model activated — ${profile?.model_slug ?? profileKey}`);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "AI profile activation failed";
      setError(message);
      toast.push("error", message);
    } finally {
      setBusyPurpose(null);
    }
  }

  return <section className="page-panel settings-panel" aria-label="AI models">
    <h3>AI models</h3>
    <p className="roles-explainer">Each purpose carries its own <Term term="ai-model-profile">AI model profile</Term> — the model that extracts claims is not presumed to be the model that writes prose. Campaign Core owns activation; provider credentials never enter the browser.</p>
    {error && <div className="notice error" role="alert">{error}</div>}
    {!configuration && !error && <p className="empty-section">Loading configuration…</p>}
    {configuration?.purposes.map((purpose) => {
      const purposeProfiles = configuration.profiles.filter((profile) => profile.purpose === purpose.key);
      const activeKey = configuration.active_profile_by_purpose[purpose.key];
      const active = purposeProfiles.find((profile) => profile.key === activeKey) ?? null;
      const selectable = purposeProfiles.filter((profile) => profile.selectable);
      const chosen = selected[purpose.key] ?? "";
      const receipt = configuration.last_activation_by_purpose[purpose.key];
      return <article className="ai-purpose-panel" key={purpose.key} aria-label={`${purpose.label} model`}>
        <header><b>{purpose.label}</b><span>{purpose.description}</span></header>
        {active
          ? <dl>
            <div><dt>Active model</dt><dd>{active.model_slug}</dd></div>
            <div><dt>Provider</dt><dd>{active.provider}</dd></div>
            <div><dt>Reasoning</dt><dd>{active.reasoning_effort ?? "none"}</dd></div>
            <div><dt>Output limit</dt><dd>{active.max_tokens}</dd></div>
            <div><dt>Timeout</dt><dd>{active.timeout_seconds}s</dd></div>
            <div><dt>Retries</dt><dd>{active.retry_limit}</dd></div>
            <div><dt>Suitability</dt><dd>{active.suitability}</dd></div>
          </dl>
          : <p className="empty-section">No {purpose.label.toLowerCase()} model active yet — pick one below and activate it.</p>}
        {purpose.prompt_text && <details className="gathered-claims"><summary>Prompt ({purpose.prompt_version})</summary><pre>{purpose.prompt_text}</pre></details>}
        {receipt && <small className="ai-activation-note">Activated {new Date(receipt.activated_at).toLocaleString()} · receipt {receipt.receipt_id.slice(0, 8)}</small>}
        {selectable.length > 0 && <div className="ai-purpose-select">
          <label>Model<select aria-label={`${purpose.label} model profile`} value={chosen} onChange={(event) => setSelected((current) => ({ ...current, [purpose.key]: event.target.value }))}>
            <option value="">Choose a model…</option>
            {purposeProfiles.map((profile) => <option disabled={!profile.selectable} key={profile.key} value={profile.key}>{profile.model_slug} — {profile.suitability}{profile.selectable ? "" : " (locked)"}</option>)}
          </select></label>
          <button disabled={busyPurpose === purpose.key || !chosen || chosen === activeKey} onClick={() => void activate(purpose)} type="button">{busyPurpose === purpose.key ? "Activating…" : "Activate"}</button>
        </div>}
      </article>;
    })}
    <AIPromptEditors campaignClient={campaignClient} />
  </section>;
}

function AIPromptEditors({ campaignClient }: { campaignClient: CampaignClient }) {
  const [prompts, setPrompts] = useState<EffectivePrompt[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const labels: Record<string, string> = { extraction: "Claim extraction", prose: "Prose writing", promotion: "Promotion assistant" };

  const load = useCallback(async () => {
    try {
      const items = await campaignClient.getAIPrompts();
      setPrompts(items);
      setDrafts(Object.fromEntries(items.map((item) => [item.purpose, item.prompt_text])));
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "AI prompts unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { void load(); }, [load]);

  const save = async (item: EffectivePrompt) => {
    const text = drafts[item.purpose] ?? item.prompt_text;
    if (!text.trim() || text === item.prompt_text) return;
    setBusy(item.purpose);
    try {
      const receipt = await campaignClient.setAIPrompt(item.purpose, text);
      await load();
      toast.push("success", `${labels[item.purpose] ?? item.purpose} prompt saved — ${receipt.version_label} (receipt ${receipt.receipt_id.slice(0, 8)})`);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "The prompt could not be saved";
      setError(detail);
      toast.push("error", detail);
    } finally { setBusy(null); }
  };

  const reset = async (item: EffectivePrompt) => {
    setBusy(item.purpose);
    try {
      await campaignClient.resetAIPrompt(item.purpose);
      await load();
      toast.push("success", `${labels[item.purpose] ?? item.purpose} prompt reset to the built-in default`);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "The prompt could not be reset";
      setError(detail);
      toast.push("error", detail);
    } finally { setBusy(null); }
  };

  if (prompts.length === 0 && !error) return null;
  return <>
    {error && <div className="notice error" role="alert">{error}</div>}
    {prompts.map((item) => {
      const draft = drafts[item.purpose] ?? item.prompt_text;
      return <article className="ai-purpose-panel" key={item.purpose} aria-label={`${labels[item.purpose] ?? item.purpose} prompt`}>
        <header><b>{labels[item.purpose] ?? item.purpose} prompt</b><span>{item.overridden ? `Override active · ${item.version_label}` : `${item.version_label} · built-in`}</span></header>
        <label className="pc-background-field session-notes-field">Prompt<textarea aria-label={`${labels[item.purpose] ?? item.purpose} prompt text`} rows={10} value={draft} onChange={(event) => setDrafts((current) => ({ ...current, [item.purpose]: event.target.value }))} /></label>
        <div className="step-actions">
          <button className="text-button" disabled={!item.overridden || busy === item.purpose} onClick={() => void reset(item)} type="button">Reset to default</button>
          <button disabled={busy === item.purpose || !draft.trim() || draft === item.prompt_text} onClick={() => void save(item)} type="button">{busy === item.purpose ? "Saving…" : "Save override"}</button>
        </div>
        <small className="ai-activation-note">Saving files a receipt and stamps a local version; drafts and extraction runs record which prompt produced them. The structural contract (citations, JSON shape) cannot be edited away.</small>
      </article>;
    })}
  </>;
}

function SettingsPage({ settings, onChange, campaignClient }: { settings: import("./settings").Settings; onChange: (changes: import("./settings").PartialSettings) => void; campaignClient: CampaignClient }) {
  const HIDEABLE = [
    { label: "Migration", note: "Phase 2 — the qualified-entities campaign: drive every record to the bar, then hold it" },
    { label: "Conventions", note: "The UI reference page" },
  ];
  return <main className="page-settings">
    <section className="identity-page-header" aria-label="Settings">
      <div className="section-heading"><div><p className="kicker">Preferences</p><h2>Settings</h2></div>
        <p>DM preferences for how this app behaves. Everything here is stored in your browser and applies immediately — nothing touches campaign truth.</p></div>
    </section>

    <section className="page-panel settings-panel" aria-label="Notifications">
      <h3>Notifications</h3>
      <label className="setting-row"><input checked={settings.toastsEnabled} onChange={(event) => onChange({ toastsEnabled: event.target.checked })} type="checkbox" />
        <span><b>Show toasts</b><small>Transient confirmations in the top-right. Every outcome is still recorded in the Log regardless.</small></span></label>
      <label className="setting-row">Toast duration<input aria-label="Toast duration seconds" max={20} min={2} type="number" value={Math.round(settings.toastDurationMs / 1000)}
        onChange={(event) => { const seconds = Number(event.target.value); if (seconds >= 2 && seconds <= 20) onChange({ toastDurationMs: seconds * 1000 }); }} />
        <small>Seconds before each toast dismisses itself (2–20).</small></label>
    </section>

    <section className="page-panel settings-panel" aria-label="Activity log">
      <h3>Activity log</h3>
      <label className="setting-row"><input checked={settings.logErrorsOnly} onChange={(event) => onChange({ logErrorsOnly: event.target.checked })} type="checkbox" />
        <span><b>Errors only</b><small>The Log page shows just failures and refusals; receipts stay available per surface.</small></span></label>
      <label className="setting-row"><input checked={settings.showLegacyMigration} onChange={(event) => onChange({ showLegacyMigration: event.target.checked })} type="checkbox" />
        <span><b>Phase-1 Migration wizard</b><small>Shelved 2026-09-21 — the Starfall import closed. The legacy workspace (import queue, extraction, session-note review) stays reachable here until session review is re-homed.</small></span></label>
    </section>

    <section className="page-panel settings-panel" aria-label="Records visibility">
      <h3>Records visibility</h3>
      <p className="roles-explainer">Provenance detail is verification machinery, not reading material — both stay available in the audit view when you need them.</p>
      <label className="setting-row"><input checked={settings.recordsVisibility.sources} onChange={(event) => onChange({ recordsVisibility: { ...settings.recordsVisibility, sources: event.target.checked } })} type="checkbox" />
        <span><b>Show sources &amp; provenance</b><small>Source paths and provenance passages on records. The referenced sources live outside the app, so this is off by default.</small></span></label>
      <label className="setting-row"><input checked={settings.recordsVisibility.earlierVersions} onChange={(event) => onChange({ recordsVisibility: { ...settings.recordsVisibility, earlierVersions: event.target.checked } })} type="checkbox" />
        <span><b>Show earlier versions</b><small>Superseded claim history blocks under Records.</small></span></label>
    </section>

    <section className="page-panel settings-panel" aria-label="Navigation">
      <h3>Navigation</h3>
      <p className="roles-explainer">Hide pages you rarely open from the top bar. Hidden pages stay fully reachable — clear the checkbox to bring a page back.</p>
      {HIDEABLE.map((page) => <label className="setting-row" key={page.label}><input checked={!settings.hiddenNavPages.includes(page.label)}
          onChange={(event) => {
            const hidden = event.target.checked
              ? settings.hiddenNavPages.filter((item) => item !== page.label)
              : [...settings.hiddenNavPages, page.label];
            onChange({ hiddenNavPages: hidden });
          }} type="checkbox" />
        <span><b>Show {page.label}</b><small>{page.note}</small></span></label>)}
    </section>

    <section className="page-panel settings-panel" aria-label="Floating trays">
      <h3>Floating trays</h3>
      <p className="roles-explainer">The floating tray array anchors to one bottom edge; launchers sit side by side, open panels tile horizontally without overlapping. Hiding a tray removes its launcher (queue events still toast and log).</p>
      <label className="setting-row">Array anchor<select aria-label="Tray array anchor" value={settings.trayLayout.anchor}
          onChange={(event) => onChange({ trayLayout: { ...settings.trayLayout, anchor: event.target.value as "left" | "right" | "centered" } })}>
          <option value="right">Dock right</option>
          <option value="left">Dock left</option>
          <option value="centered">Centered</option>
        </select></label>
      {([["session", "Session notes", "The table-notes tray"], ["drafts", "Drafts tray", "AI draft holding"], ["search", "Ask-the-archive", "The archive search tray (the topbar magnifier always opens it too)"]] as const).map(([key, label, note]) => <label className="setting-row" key={key}><input checked={settings.trayLayout[key as "session" | "drafts" | "search"]}
          onChange={(event) => onChange({ trayLayout: { ...settings.trayLayout, [key]: event.target.checked } })} type="checkbox" />
        <span><b>Show {label} launcher</b><small>{note}</small></span></label>)}
    </section>

    <AIModelSettings campaignClient={campaignClient} />
    <TemplateVocabularySettings campaignClient={campaignClient} />
  </main>;
}

function TemplateVocabularySettings({ campaignClient }: { campaignClient: CampaignClient }) {
  const VOCABULARY_LABELS: Record<string, string> = {
    location_type: "Location types", status: "Statuses", race: "Races", sex: "Sexes",
  };
  const [values, setValues] = useState<Record<string, VocabularyValue[]>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async (vocabulary: string) => {
    try {
      const items = await campaignClient.getTemplateVocabulary(vocabulary);
      setValues((current) => ({ ...current, [vocabulary]: items }));
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Template vocabularies unavailable");
    }
  }, [campaignClient]);

  useEffect(() => {
    for (const vocabulary of Object.keys(VOCABULARY_LABELS)) void load(vocabulary);
  }, [load]);

  const change = async (vocabulary: string, action: "add" | "retire", value: string) => {
    if (!value.trim()) return;
    const restoring = action === "add" && (values[vocabulary] ?? []).some((item) => item.value === value.trim() && item.retired);
    setBusy(`${vocabulary}:${action}:${value}`);
    try {
      await campaignClient.changeTemplateVocabulary(vocabulary, action, value.trim());
      await load(vocabulary);
      if (action === "add" && !restoring) setDrafts((current) => ({ ...current, [vocabulary]: "" }));
      toast.push("success", action === "add"
        ? restoring
          ? `${VOCABULARY_LABELS[vocabulary]}: "${value.trim()}" restored — offered again (receipt filed)`
          : `${VOCABULARY_LABELS[vocabulary]}: added "${value.trim()}" (receipt filed)`
        : `${VOCABULARY_LABELS[vocabulary]}: "${value.trim()}" retired — it stops being offered but keeps rendering where already set`);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "The vocabulary change could not be filed";
      setError(detail);
      toast.push("error", detail);
    } finally { setBusy(null); }
  };

  return <section className="page-panel settings-panel" aria-label="Template vocabularies">
    <h3>Template vocabularies</h3>
    <p className="roles-explainer">Controlled values for template fields — no more arbitrary text in Location type, Status, Race, or Sex. Adding or retiring a value files a receipt; retired values stop being offered but keep rendering on entries that already carry them. Roles are relations, not a vocabulary — they stay with the roster.</p>
    {error && <div className="notice error" role="alert">{error}</div>}
    {Object.entries(VOCABULARY_LABELS).map(([vocabulary, label]) => <article className="ai-purpose-panel" key={vocabulary} aria-label={label}>
      <header><b>{label}</b><span>{(values[vocabulary] ?? []).filter((item) => !item.retired).length} offered · {(values[vocabulary] ?? []).filter((item) => item.retired).length} retired</span></header>
      <div className="vocabulary-values">
        {(values[vocabulary] ?? []).map((item) => <span key={item.value} className={"vocabulary-chip" + (item.retired ? " retired" : "")}>
          {item.value}
          {!item.retired
            ? <button aria-label={`Retire ${item.value} from ${label}`} className="text-button" disabled={busy !== null} onClick={() => void change(vocabulary, "retire", item.value)} title="Retire — stops being offered, keeps rendering where set" type="button">×</button>
            : <><small>retired</small><button aria-label={`Restore ${item.value} to ${label}`} className="text-button" disabled={busy !== null} onClick={() => void change(vocabulary, "add", item.value)} title="Restore — offer this value again" type="button">↩</button></>}
        </span>)}
      </div>
      <div className="ai-purpose-select">
        <label>Add value<input aria-label={`New ${label.slice(0, -1)} value`} onChange={(event) => setDrafts((current) => ({ ...current, [vocabulary]: event.target.value }))} placeholder="New value…" value={drafts[vocabulary] ?? ""} /></label>
        <button disabled={busy !== null || !(drafts[vocabulary] ?? "").trim()} onClick={() => void change(vocabulary, "add", drafts[vocabulary] ?? "")} type="button">{busy?.startsWith(vocabulary + ":add") ? "Adding…" : "Add"}</button>
      </div>
    </article>)}
  </section>;
}

function ActivityLogPage({ campaignClient }: { campaignClient: CampaignClient }) {
  const [sessionEvents, setSessionEvents] = useState<LogEntry[]>([]);
  const [decisions, setDecisions] = useState<IdentityDecisionEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "errors">("all");
  const [notice, setNotice] = useState("");

  useEffect(() => toast.subscribeLog(setSessionEvents), []);

  const loadDecisions = useCallback(async () => {
    setLoading(true);
    try {
      setDecisions(await campaignClient.listRecentDecisions(100));
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Decisions could not be loaded");
    } finally { setLoading(false); }
  }, [campaignClient]);

  useEffect(() => { if (decisions === null && !loading) void loadDecisions(); }, [decisions === null, loading, loadDecisions]);

  const timeOf = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const decisionSummary = (decision: IdentityDecisionEntry) => {
    const details = (decision.details ?? {}) as Record<string, unknown>;
    const action = typeof details.action === "string" ? details.action : null;
    const parts = [
      action ? display(action) : null,
      typeof details.role_name === "string" ? `role: ${details.role_name}` : null,
      typeof details.member_name === "string" ? `member: ${details.member_name}` : null,
      typeof details.faction_name === "string" ? `faction: ${details.faction_name}` : null,
    ].filter(Boolean);
    return parts.length > 0 ? parts.join(" · ") : null;
  };
  const rows = [
    ...sessionEvents.map((event) => ({
      key: `session-${event.id}`, at: event.at, time: timeOf(event.at),
      kind: event.kind, label: event.kind === "success" ? "Done" : event.kind === "error" ? "Error" : "Notice",
      message: event.message, detail: null as string | null, source: "This session",
    })),
    ...(decisions ?? []).map((decision) => ({
      key: `decision-${decision.decision_id}`, at: decision.decided_at, time: timeOf(decision.decided_at),
      kind: "decision" as const, label: `Decision · ${display(decision.kind)}`,
      message: decision.surface, detail: decisionSummary(decision), source: "Campaign Core audit",
    })),
  ].sort((left, right) => right.at.localeCompare(left.at));
  const settings = getSettings();
  const visible = (filter === "errors" || settings.logErrorsOnly)
    ? rows.filter((row) => row.kind === "error") : rows;

  return <main className="page-log">
    <section className="identity-page-header" aria-label="Activity log">
      <div className="section-heading"><div><p className="kicker">Maintenance</p><h2>Activity Log</h2></div><p>Every outcome plus the durable decision audit from Campaign Core — newest first. Session events are kept in this browser and survive reloads; decisions persist with receipts.</p></div>
      <div className="identity-toolbar">
        <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")} type="button">All</button>
        <button className={filter === "errors" ? "active" : ""} onClick={() => setFilter("errors")} type="button">Errors only</button>
        <button className="secondary-button" disabled={loading} onClick={() => void loadDecisions()} type="button">{loading ? "Working…" : "Refresh"}</button>
      </div>
      {notice && <p role="alert" className="identity-message notice error">{notice}</p>}
    </section>
    <p className="identity-count">Showing {visible.length} event{visible.length === 1 ? "" : "s"} · {sessionEvents.length} this session · {decisions?.length ?? 0} audited decisions</p>
    {visible.length === 0 && <p className="identity-empty">Nothing logged yet.</p>}
    <ul className="log-list" aria-label="Activity events">
      {visible.slice(0, 300).map((row) => <li className={`log-row log-${row.kind}`} key={row.key}>
        <time>{row.time}</time>
        <span className="log-kind">{row.label}</span>
        <span className="log-message">{row.message}{row.detail ? ` — ${row.detail}` : ""}</span>
        <small>{row.source}</small>
      </li>)}
    </ul>
  </main>;
}

// ADR-0018 Promotion Pipeline: the reusable candidate review list. Compact
// scan-able rows — every approvable element at a glance, fixed inline, one
// Approve promotion action (user ruling 2026-09-20). TKT-0137: AI
// restatement suggestions co-display in the row with agreement coloring
// (green = system + AI agree, blue = system, orange = AI suggestion) — the
// DM's pick wins, and suggestions never gate or auto-include.
interface PromotionRow extends PromotionCandidate {
  conflictCleared: boolean;
}

interface AIRestatementNote {
  claimId: string | null;
  materialText: string;
  agrees: boolean;
  modelSlug: string;
}

function PromotionReviewList({ entityName, rows, stale, busy, error, bundleLabel, emptyLabel, aiRestatements, onRowChange, onMarkReference, onDismissAiNote, onCommit, onDismiss }: {
  entityName: string; rows: PromotionRow[]; stale: boolean; busy: boolean; error: string;
  bundleLabel: string; emptyLabel: string;
  aiRestatements?: Record<number, AIRestatementNote>;
  onRowChange: (sequence: number, patch: Partial<PromotionRow>) => void;
  onMarkReference?: (sequence: number, claimId: string, modelSlug: string) => void;
  onDismissAiNote?: (sequence: number) => void;
  onCommit: () => void; onDismiss: () => void;
}) {
  const included = rows.filter((row) => row.included && row.consequence.kind === "new_claim");
  const blocked = included.some((row) => row.conflict && !row.conflictCleared);
  return <section className="promotion-review" aria-label="Promotion review">
    <header>
      <div><span>Promotion review</span><h3>{entityName}</h3></div>
      <p>{rows.length === 0
        ? "No statements found in the prose — filing records the document only."
        : "Scan the list, fix wording or truth state inline, then approve. Restatements of gathered claims stay references — never a second claim."}</p>
    </header>
    {rows.map((row) => {
      const note = aiRestatements?.[row.sequence];
      return <article className={`promotion-row${row.consequence.kind === "reference" ? " reference" : ""}${row.conflict && !row.conflictCleared ? " has-conflict" : ""}`} key={row.sequence}>
      <label className="promotion-include"><input
        aria-label={`${row.included ? "Exclude" : "Include"} statement ${row.sequence}`}
        checked={row.included}
        disabled={row.consequence.kind === "reference" || Boolean(row.conflict && !row.conflictCleared)}
        onChange={(event) => onRowChange(row.sequence, { included: event.target.checked })}
        type="checkbox"
      /></label>
      <div className="promotion-row-main">
        <input
          aria-label={`Statement ${row.sequence} wording`}
          className="promotion-assertion"
          disabled={row.consequence.kind === "reference"}
          value={row.assertion_text}
          onChange={(event) => onRowChange(row.sequence, { assertion_text: event.target.value, conflictCleared: row.conflict ? true : row.conflictCleared })}
        />
        <div className="promotion-row-meta">
          {row.consequence.kind === "new_claim"
            ? <label className="promotion-state"><small>Truth State</small><select
                aria-label={`Statement ${row.sequence} truth state`}
                value={row.state}
                onChange={(event) => onRowChange(row.sequence, { state: event.target.value })}
              >
                <option value="established">Established</option>
                <option value="considered">Considered</option>
                <option value="prepared">Prepared</option>
              </select></label>
            : <span className="promotion-state-fixed">inherits reference</span>}
          <span className={"promotion-consequence" + (row.consequence.kind === "reference" ? (note?.agrees ? " agreement-consensus" : " agreement-system") : "")}>{row.consequence.kind === "new_claim" ? `new claim on ${entityName}` : row.consequence.label}</span>
          <small className="promotion-provenance">from the description prose · statement {row.sequence}</small>
        </div>
        {note && !note.agrees && <div className="promotion-ai-note">
          <WandIcon /> <b>AI suggests this restates gathered evidence</b>
          {note.materialText && <span className="promotion-ai-material"> — “{note.materialText}”</span>}
          <small className="ai-activation-note">suggested by {note.modelSlug}</small>
          <span className="promotion-ai-actions">
            {note.claimId && <button className="text-button" onClick={() => onMarkReference?.(row.sequence, note.claimId!, note.modelSlug)} type="button">Mark as reference</button>}
            <button className="text-button" onClick={() => onDismissAiNote?.(row.sequence)} type="button">Keep as new claim</button>
          </span>
        </div>}
        {row.conflict && !row.conflictCleared && <p className="promotion-conflict" role="alert">
          ⚑ known conflict: “{row.conflict.against_text}” — reword the statement or leave it out
        </p>}
        {row.conflict && row.conflictCleared && <p className="promotion-conflict-cleared">reworded — Campaign Core re-checks on commit</p>}
      </div>
      </article>;
    })}
    {stale && <p className="promotion-stale" role="alert">The prose changed after this review — dismiss and review again.</p>}
    {error && <p className="inline-error" role="alert">{error}</p>}
    <div className="step-actions">
      <button className="text-button" disabled={busy} onClick={onDismiss} type="button">Dismiss review</button>
      <button className="decision-button" disabled={busy || stale || blocked} onClick={onCommit} type="button">
        {busy ? "Committing…" : included.length > 0 ? `Approve promotion · ${included.length} claim${included.length === 1 ? "" : "s"} + ${bundleLabel}` : emptyLabel}
      </button>
    </div>
  </section>;
}

// Description promotion reviews CLAIMS, not prose statements (Sean's ruling
// 2026-09-24): the description is an ordered composition of claims — the
// prose is the reading layer and is never split into claims. Rows are the
// gathered claims in gather order; text edits supersede through the
// receipted correction path; Own marks re-attribute to this entry.
// Description claim-breakpoint review (TKT-0146, ADR-0018 amendment):
// rows derive FROM THE PROSE — `::` marks author intent (marker-only split;
// no markers = one whole-prose row). The unit is the assertion, not the
// sentence: edit / merge-below / split / drop are the regroup ops. The
// prose is the reading layer and never files as claims; the claims promote
// and the document records the ordered collection (Dossier-like).
interface DescriptionClaimRow {
  rowId: string;
  text: string;
  included: boolean;
  state: string;
  // The prose span this group came from — the filed candidate's provenance;
  // regroup ops keep it a non-overlapping range into the original prose.
  spanStart: number;
  spanEnd: number;
}

// Deterministic marker split — the ONLY delimiter when markers are present.
function splitClaimGroups(prose: string): string[] {
  if (prose.includes("::")) {
    return prose.split("::").map((part) => part.trim()).filter(Boolean);
  }
  // No markers: no breaks — one whole-prose row (the author adds breaks).
  const whole = prose.trim();
  return whole ? [whole] : [];
}

function DescriptionClaimReview({ entryName, rows, busy, error, aiNotes, materialTextFor, onRowChange, onExcludeRow, onDismissAiNote, onMerge, onSplit, onRowDrop, onRowMove, onCommit, onDismiss }: {
  entryName: string; rows: DescriptionClaimRow[]; busy: boolean; error: string;
  aiNotes?: Record<string, { systemKey: string | null; aiKey: string | null; agrees: boolean; modelSlug: string }>;
  materialTextFor?: (key: string) => string;
  onRowChange: (rowId: string, patch: Partial<DescriptionClaimRow>) => void;
  onExcludeRow?: (rowId: string) => void;
  onDismissAiNote?: (rowId: string) => void;
  onMerge: (rowId: string) => void;
  onSplit: (rowId: string, caret: number) => void;
  onRowDrop: (rowId: string) => void;
  onRowMove: (rowId: string, direction: -1 | 1) => void;
  onCommit: () => void; onDismiss: () => void;
}) {
  const included = rows.filter((row) => row.included && row.text.trim());
  return <section className="promotion-review" aria-label="Description claim review">
    <header>
      <div><span>Description claims</span><h3>{entryName}</h3></div>
      <p>The claims your prose asserts — one row per `::` group. Shape them here: edit wording, merge glue into the claim above, split a row carrying two assertions, drop what isn't canon. Approve promotes the claims and records this order as the description's collection; the prose stays the reading layer.</p>
    </header>
    {rows.map((row, index) => {
      const note = aiNotes?.[row.rowId];
      const systemText = note?.systemKey && materialTextFor ? materialTextFor(note.systemKey) : null;
      const aiText = note?.aiKey && materialTextFor ? materialTextFor(note.aiKey) : null;
      return <article className={"promotion-row" + (row.included ? "" : " excluded")} key={row.rowId}>
      <label className="promotion-include"><input
        aria-label={`Include claim ${index + 1}`}
        checked={row.included}
        onChange={(event) => onRowChange(row.rowId, { included: event.target.checked })}
        type="checkbox"
      /></label>
      <div className="promotion-row-main">
        <textarea
          aria-label={`Claim ${index + 1} text`}
          className="promotion-assertion"
          rows={Math.max(2, Math.ceil(row.text.length / 90))}
          value={row.text}
          onChange={(event) => onRowChange(row.rowId, { text: event.target.value })}
        ></textarea>
        <div className="promotion-row-meta">
          <label className="promotion-state"><small>Truth State</small><select
            aria-label={`Claim ${index + 1} truth state`}
            value={row.state}
            onChange={(event) => onRowChange(row.rowId, { state: event.target.value })}
          >
            <option value="established">Established</option>
            <option value="considered">Considered</option>
            <option value="prepared">Prepared</option>
          </select></label>
          <span className="promotion-consequence">claim {index + 1} of {rows.length}</span>
          <div className="promotion-row-ops">
            {index > 0 && <button aria-label={`Merge claim ${index + 1} into claim ${index}`} onClick={() => onMerge(row.rowId)} title="Merge into the claim above" type="button">⤒ merge</button>}
            <button aria-label={`Split claim ${index + 1}`} onClick={(event) => {
              const area = (event.currentTarget.closest(".promotion-row")?.querySelector("textarea")) as HTMLTextAreaElement | null;
              onSplit(row.rowId, area?.selectionStart ?? -1);
            }} title="Split at the caret" type="button">⤓ split</button>
            <button aria-label={`Drop claim ${index + 1}`} onClick={() => onRowDrop(row.rowId)} title="Drop this claim" type="button">✕</button>
            {index > 0 && <button aria-label={`Move claim ${index + 1} up`} onClick={() => onRowMove(row.rowId, -1)} title="Move up" type="button">↑</button>}
            {index < rows.length - 1 && <button aria-label={`Move claim ${index + 1} down`} onClick={() => onRowMove(row.rowId, 1)} title="Move down" type="button">↓</button>}
          </div>
        </div>
        {note && (note.agrees || note.systemKey) && <div className={"promotion-ai-note" + (note.agrees ? " consensus" : " system")}>
          {note.agrees
            ? <><WandIcon /> <b>Restatement — system + AI agree</b>{systemText && <span className="promotion-ai-material"> — “{systemText}”</span>}</>
            : <><b>System mirror: restates an existing claim</b>{systemText && <span className="promotion-ai-material"> — “{systemText}”</span>}</>}
          <span className="promotion-ai-actions">
            <button className="text-button" onClick={() => onExcludeRow?.(row.rowId)} type="button">Exclude row</button>
          </span>
        </div>}
        {note?.aiKey && !note.agrees && !note.systemKey && <div className="promotion-ai-note">
          <WandIcon /> <b>AI suggests this restates an existing claim</b>{aiText && <span className="promotion-ai-material"> — “{aiText}”</span>}
          <small className="ai-activation-note">suggested by {note.modelSlug}</small>
          <span className="promotion-ai-actions">
            <button className="text-button" onClick={() => onExcludeRow?.(row.rowId)} type="button">Exclude row</button>
            <button className="text-button" onClick={() => onDismissAiNote?.(row.rowId)} type="button">Keep as new claim</button>
          </span>
        </div>}
        {note?.aiKey && !note.agrees && note.systemKey && <div className="promotion-ai-note">
          <WandIcon /> <b>AI names a different match</b>{aiText && <span className="promotion-ai-material"> — “{aiText}”</span>}
          <small className="ai-activation-note">suggested by {note.modelSlug} — the system's flag stays above; your pick wins</small>
          <span className="promotion-ai-actions">
            <button className="text-button" onClick={() => onDismissAiNote?.(row.rowId)} type="button">Keep as new claim</button>
          </span>
        </div>}
      </div>
      </article>;
    })}
    {error && <p className="inline-error" role="alert">{error}</p>}
    <div className="step-actions">
      <button className="text-button" disabled={busy} onClick={onDismiss} type="button">Dismiss review</button>
      <button className="decision-button" disabled={busy || included.length === 0} onClick={onCommit} type="button">
        {busy ? "Committing…" : `Approve promotion · ${included.length} claim${included.length === 1 ? "" : "s"} + description`}
      </button>
    </div>
  </section>;
}

function DescriptionComposer({ entry, claims, profile, campaignClient, jobPlatform, onClose, onSaved, initialText, documentId, onDirtyChange, onQueueDraft, initialSelected }: {
  entry: LibraryEntry; claims: SourceDocumentClaim[];
  profile: EntityProfile | null; campaignClient: CampaignClient; jobPlatform: JobPlatform; onClose: () => void;
  onSaved: () => Promise<void>; initialText?: string | null; documentId?: string | null;
  onDirtyChange?: (dirty: boolean) => void;
  onQueueDraft?: (command: ProseDraftCommand) => Promise<void>;
  initialSelected?: { claimIds: string[]; relationKeys: string[] } | null;
}) {
  const [text, setText] = useState(initialText ?? "");
  // ADR-0016: the switch guard needs to know the composer holds changes —
  // any prose in a fresh composer, or any edit of the seeded revision text.
  useEffect(() => { onDirtyChange?.(text.trim().length > 0 && text !== (initialText ?? "")); }, [text, initialText, onDirtyChange]);
  // A claimed draft arrives with the citations it actually used — the
  // selection mirrors them so filing records exactly the cited records.
  const [selected, setSelected] = useState<Set<string>>(() => new Set(initialSelected?.claimIds ?? claims.map((claim) => claim.claim_id)));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  // TKT-0120/0127: drafting is fire-and-forget — the request runs as a
  // background Windmill job and lands in the Drafts tray; nothing here blocks.
  const [proseModelActive, setProseModelActive] = useState<boolean | null>(null);
  const [drafting, setDrafting] = useState(false);
  useEffect(() => {
    void campaignClient.getAIConfiguration().then((snapshot) => setProseModelActive(Boolean(snapshot.active_profile_by_purpose.prose))).catch(() => setProseModelActive(null));
  }, [campaignClient]);
  // Two-layer relational gather: the base layer comes from the entry's own
  // canonical data (roster seats, roles, co-mention associations); the graph
  // expansion layer loads on demand from the audited-edge bundle.
  const baseRelations: { key: string; text: string; backing: string }[] = [
    ...(entry.roles ?? []).map((role) => ({
      key: `relation:role:${role.name}`,
      text: `Role ${role.name}${role.is_leadership ? " (unique leadership seat ★)" : ""}${role.holder_names.length > 0 ? ` — held by ${role.holder_names.join(", ")}` : " — vacant"}`,
      backing: "canonical role record",
    })),
    ...(entry.members ?? []).map((member) => ({
      key: `relation:member:${member.name}`,
      text: `${member.name} is a member${member.role_title ? ` (${member.role_title}${member.is_leadership ? " ★" : ""})` : ""}`,
      backing: "audited membership record",
    })),
    ...(entry.related ?? []).slice(0, 8).map((name) => ({
      key: `relation:related:${name}`,
      text: `Appears with ${name}`,
      backing: "derived co-mention association",
    })),
  ];
  const [graphRows, setGraphRows] = useState<{ key: string; text: string; backing: string }[] | null>(null);
  const [graphEnabled, setGraphEnabled] = useState(false);
  const [graphLoading, setGraphLoading] = useState(false);
  // ADR-0018 Promotion Pipeline: on-demand derive (never automatic), prose
  // snapshot for staleness, and one idempotency key held across retries.
  const [promotionRows, setPromotionRows] = useState<DescriptionClaimRow[] | null>(null);
  const [promotionBusy, setPromotionBusy] = useState(false);
  const [promotionError, setPromotionError] = useState("");
  const promotionKey = useRef<string | null>(null);
  // AI promotion assistant (TKT-0137): the dedup check — the deterministic
  // mirror AND the AI's paraphrase judgment over the reviewed rows against
  // this entry's existing claims. Queued async; lands in the working file.
  const [suggestBusy, setSuggestBusy] = useState(false);
  const [suggestJobId, setSuggestJobId] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<LoreSuggestionSet | null>(null);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(() => new Set());
  const [suggestError, setSuggestError] = useState("");
  const suggestPollTimer = useRef<number | null>(null);
  // ADR-0019: the working file — prose AND in-flight review rows — auto-saves
  // continuously per entry; reopening restores both. The user never keeps an
  // external copy out of distrust.
  const workingKey = `dm-assistant.descriptionWork.${entry.entry_id}`;
  const persist = useCallback((work: { prose: string; rows: DescriptionClaimRow[] | null; suggestion?: LoreSuggestionSet | null; suggestionJobId?: string | null; dismissedSuggestions?: string[] }) => {
    try {
      window.localStorage.setItem(workingKey, JSON.stringify({ ...work, savedAt: new Date().toISOString() }));
    } catch { /* storage full or unavailable — the in-editor state continues */ }
  }, [workingKey]);
  const restoreWork = () => {
    const work = restoredWork ? restoredWork() : null;
    if (work?.prose) setText(work.prose);
    if (work?.rows) setPromotionRows(work.rows);
    setSuggestion(work?.suggestion ?? null);
    setSuggestJobId(work?.suggestionJobId ?? null);
    setDismissedSuggestions(new Set(work?.dismissedSuggestions ?? []));
    setRestoredWork(null);
    toast.push("info", "Working file restored — nothing was lost");
  };
  const discardWork = () => {
    setRestoredWork(null);
    try { window.localStorage.removeItem(workingKey); } catch { /* already gone */ }
  };
  const [restoredWork, setRestoredWork] = useState<(() => { prose: string; rows: DescriptionClaimRow[] | null; suggestion?: LoreSuggestionSet | null; suggestionJobId?: string | null; dismissedSuggestions?: string[] } | null) | null>(null);
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(workingKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as { prose?: string; rows?: DescriptionClaimRow[] | null; suggestion?: LoreSuggestionSet | null; suggestionJobId?: string | null; dismissedSuggestions?: string[] };
      if ((parsed.prose ?? "").trim() || (parsed.rows ?? null)) {
        const capture = { prose: parsed.prose ?? "", rows: parsed.rows ?? null, suggestion: parsed.suggestion ?? null, suggestionJobId: parsed.suggestionJobId ?? null, dismissedSuggestions: parsed.dismissedSuggestions ?? [] };
        setRestoredWork(() => () => capture);
      }
    } catch { /* corrupt working file — start fresh */ }
  }, [workingKey]);
  const claimCount = splitClaimGroups(text).length;
  useEffect(() => { persist({ prose: text, rows: promotionRows, suggestion, suggestionJobId: suggestJobId, dismissedSuggestions: [...dismissedSuggestions] }); }, [text, promotionRows, persist, suggestion, suggestJobId, dismissedSuggestions]);
  const relationRows = graphRows === null ? baseRelations : [...baseRelations, ...graphRows];
  const [selectedRelations, setSelectedRelations] = useState<Set<string>>(() => new Set(initialSelected?.relationKeys ?? baseRelations.map((row) => row.key)));

  // Review derives rows FROM THE PROSE via the :: marker split (marker-only;
  // no markers = one whole-prose row). No backend derive call.
  const reviewPromotion = () => {
    if (!text.trim()) return;
    const prose = text;
    const groups = splitClaimGroups(prose);
    // Compute each group's span in the prose (marker split preserves order,
    // so spans are sequential and non-overlapping by construction).
    let cursor = 0;
    const rows = groups.map((group, index) => {
      const at = prose.indexOf(group, cursor);
      const spanStart = at >= 0 ? at : cursor;
      const spanEnd = spanStart + group.length;
      cursor = spanEnd;
      return {
        rowId: `r${index + 1}`,
        text: group,
        included: true,
        state: "established",
        spanStart,
        spanEnd,
      } as DescriptionClaimRow;
    });
    setPromotionRows(rows);
    setPromotionError("");
  };

  // Row ops — the candidate builder's regrouping.
  const rowChange = (rowId: string, patch: Partial<DescriptionClaimRow>) =>
    setPromotionRows((current) => current?.map((row) => row.rowId === rowId ? { ...row, ...patch } : row) ?? null);
  const rowMerge = (rowId: string) =>
    setPromotionRows((current) => {
      if (!current) return null;
      const index = current.findIndex((row) => row.rowId === rowId);
      if (index <= 0) return current;
      const next = [...current];
      next[index - 1] = {
        ...next[index - 1],
        text: `${next[index - 1].text} ${next[index].text}`.trim(),
        spanEnd: next[index].spanEnd,
      };
      next.splice(index, 1);
      return next;
    });
  const rowSplit = (rowId: string, caret: number) =>
    setPromotionRows((current) => {
      if (!current) return null;
      const index = current.findIndex((row) => row.rowId === rowId);
      if (index < 0) return current;
      const row = current[index];
      // Caret split; without a caret, fall back to the first sentence
      // boundary in the back half.
      let at = caret >= 0 && caret < row.text.length ? caret : -1;
      if (at <= 0) {
        const tail = row.text.slice(Math.ceil(row.text.length / 2));
        const sentence = tail.search(/[.!?]\s/);
        at = sentence >= 0 ? Math.ceil(row.text.length / 2) + sentence + 1 : Math.ceil(row.text.length / 2);
      }
      const head = row.text.slice(0, at).trim();
      const rest = row.text.slice(at).trim();
      if (!head || !rest) return current;
      const splitAt = Math.round((head.length / row.text.length) * (row.spanEnd - row.spanStart)) + row.spanStart;
      const next = [...current];
      next.splice(index, 1,
        { ...row, rowId: `${row.rowId}a`, text: head, spanEnd: splitAt },
        { ...row, rowId: `${row.rowId}b`, text: rest, spanStart: splitAt });
      return next;
    });
  const rowDrop = (rowId: string) =>
    setPromotionRows((current) => current?.filter((row) => row.rowId !== rowId) ?? null);
  const rowMove = (rowId: string, direction: -1 | 1) =>
    setPromotionRows((current) => {
      if (!current) return null;
      const index = current.findIndex((row) => row.rowId === rowId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });

  // Dedup check (TKT-0137): the reviewed rows against this entry's existing
  // claims — one async job returns the deterministic mirror AND the AI's
  // paraphrase judgment; the review joins them into the agreement coloring.
  const queueSuggestions = async () => {
    if (promotionRows === null || suggestBusy || suggestJobId) return;
    setSuggestBusy(true); setSuggestError("");
    try {
      const job = await jobPlatform.startPromotionSuggest({
        surface: "description",
        subject: entry.canonical_name,
        subject_kind: entry.entity_kind,
        statements: promotionRows.map((row) => row.text),
        material: claims.map((claim) => ({
          key: claim.claim_id,
          text: cleanImportedAssertion(claim.assertion_text),
          state: claim.state,
        })),
        idempotency_key: `promotion-suggest:${entry.entry_id}:${crypto.randomUUID()}`,
      });
      setSuggestJobId(job.jobId);
      toast.push("info", `Duplicate check queued for ${entry.canonical_name}`);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "The duplicate check could not be queued";
      setSuggestError(detail);
      toast.push("error", detail);
    } finally { setSuggestBusy(false); }
  };
  useEffect(() => {
    if (!suggestJobId || suggestion) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const next = await jobPlatform.inspect(suggestJobId);
        if (cancelled) return;
        if (next.state === "succeeded" && next.result && typeof next.result === "object") {
          setSuggestion(next.result as LoreSuggestionSet);
          setSuggestJobId(null);
          toast.push("success", "Duplicate check ready — review the marked rows");
        } else if (next.state === "failed") {
          const error = next.error ?? "The duplicate check job failed";
          setSuggestError(error);
          setSuggestJobId(null);
          toast.push("error", error);
        }
      } catch {
        // Transient inspect failures keep polling until the job resolves.
      }
      if (!cancelled) suggestPollTimer.current = window.setTimeout(poll, 2500);
    };
    suggestPollTimer.current = window.setTimeout(poll, 800);
    return () => {
      cancelled = true;
      if (suggestPollTimer.current !== null) window.clearTimeout(suggestPollTimer.current);
    };
  }, [suggestJobId, suggestion, jobPlatform]);

  const dismissSuggestion = (key: string) => {
    setDismissedSuggestions((current) => new Set(current).add(key));
  };

  // Join the two opinions per row (matched by normalized row text): the
  // system mirror's flag is deterministic and stays; the AI-only flag can be
  // dismissed. Green = both flag the same claim, blue = system only,
  // orange = AI only.
  const normalizeRow = (value: string) => value.toLocaleLowerCase().replace(/\s+/g, " ").trim();
  const materialTextFor = (key: string) => {
    const claim = claims.find((c) => c.claim_id === key);
    return claim ? cleanImportedAssertion(claim.assertion_text) : key;
  };
  const aiNotes: Record<string, { systemKey: string | null; aiKey: string | null; agrees: boolean; modelSlug: string }> = {};
  if (suggestion && promotionRows) {
    for (const row of promotionRows) {
      const key = normalizeRow(row.text);
      const ai = suggestion.restatements.find((r) => normalizeRow(r.statement_text) === key);
      const system = (suggestion.system_restatements ?? []).find((r) => normalizeRow(r.statement_text) === key);
      if (!ai && !system) continue;
      // Dismissing the AI's call hides only the orange note; the system's
      // own flag is deterministic and stays until the wording changes.
      const aiDismissed = Boolean(ai && dismissedSuggestions.has(`restatement:${key}`));
      if (aiDismissed && !system) continue;
      aiNotes[row.rowId] = {
        systemKey: system?.material_key ?? null,
        aiKey: aiDismissed ? null : (ai?.material_key ?? null),
        agrees: Boolean(ai && system && !aiDismissed && ai.material_key === system.material_key),
        modelSlug: suggestion.model_slug,
      };
    }
  }

  // Commit: claims created from rows through the promotion facade; the
  // document files the FINAL ORDERED claim ids with the prose verbatim
  // (markers retained for revision; render strips them).
  const commitPromotion = async () => {
    if (promotionRows === null || promotionBusy) return;
    const included = promotionRows.filter((row) => row.included && row.text.trim());
    if (included.length === 0) return;
    // Rows restored from an older working file may predate span tracking —
    // re-derive sequential spans against the prose before committing.
    let cursor = 0;
    for (const row of included) {
      if (!Number.isFinite(row.spanStart) || !Number.isFinite(row.spanEnd) || row.spanEnd <= row.spanStart) {
        const at = text.indexOf(row.text.trim().split(/\s+/)[0] ?? "", cursor);
        row.spanStart = at >= 0 ? at : cursor;
        row.spanEnd = Math.min(row.spanStart + row.text.trim().length, text.length || row.spanStart + row.text.trim().length);
      }
      cursor = Math.max(cursor, row.spanEnd);
    }
    setPromotionBusy(true); setPromotionError("");
    try {
      promotionKey.current ??= `promotion:${entry.entry_id}:${crypto.randomUUID()}`;
      const commitKey = promotionKey.current;
      const build = (asRevision: boolean) => campaignClient.approvePromotion({
        surface: "description",
        entity_id: entry.entry_id,
        document_text: text,
        statements: included.map((row, index) => ({
          span_start: row.spanStart, span_end: row.spanEnd,
          assertion_text: row.text.trim(), state: row.state, included: true,
        })),
        referenced_claim_ids: [...selected],
        ...(asRevision && documentId ? { document_id: documentId } : {}),
        idempotency_key: commitKey,
      });
      let receipt;
      try {
        receipt = await build(Boolean(documentId));
      } catch (error) {
        const detail = error instanceof Error ? error.message : "";
        if (documentId && detail.includes("no longer this entity's page path")) {
          receipt = await build(false);
        } else {
          throw error;
        }
      }
      setMessageIsError(false);
      setMessage(receipt.claims_committed > 0
        ? `Approved promotion — ${receipt.claims_committed} claim${receipt.claims_committed === 1 ? "" : "s"} + description filed at ${receipt.path} (receipt ${String(receipt.receipt_id ?? receipt.document_id).slice(0, 8)})`
        : `Description filed at ${receipt.path} (receipt ${receipt.document_id.slice(0, 8)})`);
      toast.push("success", receipt.claims_committed > 0
        ? `Promotion approved — ${entry.canonical_name} +${receipt.claims_committed} claims`
        : `Description filed — ${entry.canonical_name}`);
      setPromotionRows(null);
      promotionKey.current = null;
      try { window.localStorage.removeItem(workingKey); } catch { /* stale working file is harmless */ }
      await onSaved();
    } catch (error) {
      setPromotionError(error instanceof Error ? error.message : "The promotion could not be committed");
      toast.push("error", error instanceof Error ? error.message : "Promotion commit failed");
    } finally { setPromotionBusy(false); }
  };


  const toggleGraphNeighborhood = async (enabled: boolean) => {
    setGraphEnabled(enabled);
    if (!enabled || graphRows !== null || graphLoading) return;
    setGraphLoading(true);
    try {
      const raw = await campaignClient.getEntityGraphNeighborhood(entry.entry_id);
      // Normalize into the relation: key space so selection and citation
      // sync treat both layers uniformly.
      const rows = raw.map((row) => ({ ...row, key: `relation:${row.key}` }));
      setGraphRows(rows);
      setSelectedRelations((current) => {
        const next = new Set(current);
        for (const row of rows.slice(0, 6)) next.add(row.key);
        return next;
      });
    } catch (error) {
      setGraphEnabled(false);
      const detail = error instanceof Error ? error.message : "The graph neighborhood could not be loaded";
      setMessageIsError(true);
      setMessage(detail);
      toast.push("error", detail);
    } finally { setGraphLoading(false); }
  };

  const draft = async () => {
    const claimMaterial = claims.filter((claim) => selected.has(claim.claim_id));
    // The graph layer contributes material only while its panel is enabled.
    const relationMaterial = (graphEnabled ? relationRows : baseRelations)
      .filter((row) => selectedRelations.has(row.key));
    const material = [
      ...claimMaterial.map((claim) => ({ key: `claim:${claim.claim_id}`, kind: "claim", text: cleanImportedAssertion(claim.assertion_text), state: claim.state })),
      ...relationMaterial.map((row) => ({ key: row.key, kind: "relation", text: row.text })),
    ];
    if (material.length === 0 || drafting) return;
    if (!onQueueDraft) return;
    setDrafting(true);
    try {
      await onQueueDraft({
        subject: entry.canonical_name, subject_kind: entry.entity_kind, paragraph_limit: 3,
        material,
        idempotency_key: `prose-draft:${entry.entry_id}:${crypto.randomUUID()}`,
      });
      setMessageIsError(false);
      setMessage(`Draft queued — keep working; it lands in the Drafts tray (bottom-right) when the model finishes. Nothing is blocked while it runs.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "The draft could not be queued";
      setMessageIsError(true);
      setMessage(detail);
      toast.push("error", detail);
    } finally { setDrafting(false); }
  };

  const grouped = [
    { title: "Real-play facts", states: ["observed"] },
    { title: "Established information", states: ["established"] },
    { title: "Plans and preparation", states: ["intended", "prepared"] },
    { title: "Considered", states: ["considered", "possible"] },
  ];

  return <article className="document-view description-composer" aria-label="Description composer">
    <header><b>{display(entry.entity_kind)} description</b><span>{documentId ? `Revising ${entry.canonical_name}'s page` : `Writing ${entry.canonical_name}'s page`}</span></header>
    <section className="character-content">
      <p className="roles-explainer">{documentId
        ? "The revised prose sources as a new revision of the same Source — superseded text stays in revision history (ADR-0015). Draft from selected can propose the revision from the checked records."
        : <>Your prose becomes a Source filed as this entry's page (ADR-0015: authored canon-input). The gathered claims are recorded as <Term term="claim">references</Term> — the description cites the record; it never duplicates it. Write it yourself, or use <b>Draft from selected</b> to have the active prose model propose the page from the checked records — always review a machine draft before filing.</>}</p>
      <label className="pc-background-field session-notes-field">Description<textarea aria-label="Entity description" placeholder={`${documentId ? "Revise" : "Write"} ${entry.canonical_name}'s page — background, character, what matters at the table…`} rows={14} value={text} onChange={(event) => setText(event.target.value)} /></label>
      {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
      {proseModelActive === false
        ? <p className="ai-activation-note">No prose model active — activate one in Settings (AI models) to draft with AI.</p>
        : <div className="composer-draft-row">
          <button className="secondary-button" disabled={drafting || busy || (selected.size === 0 && selectedRelations.size === 0)} onClick={() => void draft()} type="button"><WandIcon />{drafting ? "Drafting…" : "Draft from selected"}</button>
          <small className="ai-activation-note">{selected.size === 0 && selectedRelations.size === 0 ? "Check records in the panels below for the model to draft from" : "The active prose model drafts only from the checked records below — the draft runs in the background and lands in the Drafts tray"}</small>
        </div>}
      <details className={"gathered-claims relations-panel" + (graphEnabled ? " graph-enabled" : "")} open><summary>Gathered relations ({selectedRelations.size} of {(graphEnabled ? relationRows : baseRelations).length} selected)</summary>
        <label className="setting-row graph-toggle"><input checked={graphEnabled} disabled={graphLoading} onChange={(event) => void toggleGraphNeighborhood(event.target.checked)} type="checkbox" />
          <span><b>Include graph neighborhood</b><small>Expansion layer — audited member/leader edges plus ranked co-mentions, capped and labeled <Term term="derived">derived</Term>.</small></span></label>
        <p className="roles-explainer">Structural context for the draft: audited seats and associations, cited to the records behind them.</p>
        {baseRelations.map((row) => <label className="gathered-claim" key={row.key}>
          <input checked={selectedRelations.has(row.key)} onChange={(event) => setSelectedRelations((current) => {
            const next = new Set(current);
            event.target.checked ? next.add(row.key) : next.delete(row.key);
            return next;
          })} type="checkbox" />
          <span>{row.text}<small className="ai-activation-note"> · {row.backing}</small></span>
        </label>)}
        {baseRelations.length === 0 && graphRows === null && <p className="empty-section">No canonical relations for this entry — the graph neighborhood is the expansion layer.</p>}
        {graphRows !== null && <div className={"graph-rows" + (graphEnabled ? "" : " graph-rows-off")}>
          {graphRows.map((row) => <label className="gathered-claim" key={row.key}>
            <input checked={selectedRelations.has(row.key)} disabled={!graphEnabled} onChange={(event) => setSelectedRelations((current) => {
              const next = new Set(current);
              event.target.checked ? next.add(row.key) : next.delete(row.key);
              return next;
            })} type="checkbox" />
            <span>{row.text}<small className="ai-activation-note"> · {row.backing}</small></span>
          </label>)}
        </div>}
        {graphEnabled && graphRows === null && graphLoading && <p className="empty-section">Loading graph neighborhood…</p>}
      </details>
      <details className="gathered-claims" open={claims.length > 0}><summary>Gathered claims ({selected.size} of {claims.length} referenced)</summary>
        <p className="roles-explainer">Selected claims are recorded as the description's references; supersession of a reference later flags the page stale.</p>
        {grouped.map((group) => {
          const items = claims.filter((claim) => group.states.includes(claim.state));
          return items.length > 0 && <section key={group.title}><h4>{group.title}</h4>
            {items.map((claim) => <label className="gathered-claim" key={claim.claim_id}>
              <input checked={selected.has(claim.claim_id)} onChange={(event) => setSelected((current) => {
                const next = new Set(current);
                event.target.checked ? next.add(claim.claim_id) : next.delete(claim.claim_id);
                return next;
              })} type="checkbox" />
              <span>{claim.assertion_text.slice(0, 160)}{claim.assertion_text.length > 160 ? "…" : ""}</span>
            </label>)}
          </section>;
        })}
        {claims.length === 0 && <p className="empty-section">No claims gathered — the description will be this entry's first canon input.</p>}
      </details>
      {promotionRows !== null && claims.length > 0 && <div className="composer-draft-row">
        <button className="secondary-button" disabled={suggestBusy || suggestJobId !== null} onClick={() => void queueSuggestions()} type="button"><WandIcon />{suggestJobId ? "Checking…" : "Check for duplicates"}</button>
        <small className="ai-activation-note">The promotion assistant checks each row against this entry's existing claims — the deterministic mirror and the AI's paraphrase judgment side by side: green when they agree, blue for the system's own flag, orange for an AI-only catch. Nothing is excluded automatically.</small>
      </div>}
      {suggestError && <div className="notice error" role="alert" style={{ margin: 0 }}>{suggestError}</div>}
      {promotionRows !== null && <DescriptionClaimReview
        entryName={entry.canonical_name}
        rows={promotionRows}
        busy={promotionBusy}
        error={promotionError}
        aiNotes={Object.keys(aiNotes).length > 0 ? aiNotes : undefined}
        materialTextFor={materialTextFor}
        onRowChange={rowChange}
        onExcludeRow={(rowId) => rowChange(rowId, { included: false })}
        onDismissAiNote={(rowId) => {
          const row = promotionRows.find((r) => r.rowId === rowId);
          if (row) dismissSuggestion(`restatement:${normalizeRow(row.text)}`);
        }}
        onMerge={rowMerge}
        onSplit={rowSplit}
        onRowDrop={rowDrop}
        onRowMove={rowMove}
        onCommit={() => void commitPromotion()}
        onDismiss={() => { setPromotionRows(null); setPromotionError(""); }}
      />}
      <div className="step-actions">
        <button className="text-button" disabled={busy} onClick={onClose} type="button">Cancel</button>
        <button className="decision-button" disabled={busy || promotionBusy || !text.trim()} onClick={() => void reviewPromotion()} type="button">{promotionBusy ? "Reviewing…" : "Review promotion"}</button>
      </div>
      <div className="composer-draft-row">
        <small className="ai-activation-note">{claimCount === 0
          ? "No claims detected — add :: between assertions in the prose to mark claim breaks."
          : `${claimCount} claim${claimCount === 1 ? "" : "s"} detected — :: marks the breaks; reviewing lets you shape them.`}</small>
      </div>
      {restoredWork ? <div className="lore-draft-ready notice" role="status"><span>Working file found</span><button className="text-button" onClick={restoreWork} type="button">Restore</button><button className="text-button" onClick={discardWork} type="button">Discard</button></div> : null}
    </section>
  </article>;
}

function LifeStatusPanel({ campaignClient }: { campaignClient: CampaignClient }) {
  const [proposals, setProposals] = useState<LifeStatusProposal[] | null>(null);
  const [deadSeats, setDeadSeats] = useState<DeadSeat[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);

  const load = useCallback(async () => {
    try {
      const [items, seats] = await Promise.all([
        campaignClient.getLifeStatusProposals(),
        campaignClient.getDeadSeats().catch(() => [] as DeadSeat[]),
      ]);
      setProposals(items);
      setDeadSeats(seats);
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Life status is unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { if (proposals === null) void load(); }, [proposals === null, load]);

  const confirm = async (proposal: LifeStatusProposal) => {
    const [year, month, day] = proposal.death_date.split("-").map(Number);
    setBusy(proposal.entity_id);
    try {
      await campaignClient.setLifeStatus(
        proposal.entity_id, "dead", { year, month, day },
        proposal.death_claim_id, `life-status:${proposal.entity_id}`);
      setMessageIsError(false);
      setMessage(`Marked ${proposal.entity_name} dead as of ${proposal.death_date} — receipted against the observed claim`);
      toast.push("success", `${proposal.entity_name} marked dead (${proposal.death_date})`);
      await load();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "The status could not be set");
      toast.push("error", error instanceof Error ? error.message : "The status could not be set");
    } finally { setBusy(null); }
  };

  return <section className="page-panel life-status-panel" aria-label="Life status">
    <div className="section-heading"><div><p className="kicker">Campaign maintenance</p><h2>Life status</h2></div>
      <p>An enumerated canon dimension — alive, dead, undead, resurrected — set through audited decisions anchored to the claim that established it. Detectors read the enum; prose never decides.</p></div>
    {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    {proposals === null ? <p className="queue-empty">Loading…</p> : <>
      <p className="identity-count">SHOWING {proposals.length} DEATH PROPOSAL{proposals.length === 1 ? "" : "S"}{deadSeats.length > 0 ? ` · ${deadSeats.length} SEAT${deadSeats.length === 1 ? "" : "S"} HELD BY THE DEAD` : ""}</p>
      {proposals.length === 0 && deadSeats.length === 0 && <p className="identity-empty">No pending status proposals and no seats held by the dead.</p>}
      {proposals.map((proposal) => <article className="conflict-card" key={proposal.entity_id} aria-label={`Death proposal: ${proposal.entity_name}`}>
        <h3>{proposal.entity_name} <small>observed death {proposal.death_date}</small></h3>
        <div className="conflict-sides"><div className="conflict-side conflict-death">
          <span className="log-kind">Backing claim</span>
          <p>{proposal.death_assertion.slice(0, 300)}{proposal.death_assertion.length > 300 ? "…" : ""}</p>
        </div></div>
        <div className="conflict-actions">
          <button className="decision-button" disabled={busy === proposal.entity_id} onClick={() => void confirm(proposal)} type="button">Mark dead</button>
        </div>
      </article>)}
      {deadSeats.length > 0 && <details className="residue-queue" open><summary>Seats held by the dead ({deadSeats.length})</summary>
        <ul>{deadSeats.map((seat) => <li key={`${seat.faction_id}-${seat.member_id}`} className="residue-relevant">
          <span className="log-message">{seat.member_name} — {seat.role_title ?? "member"}{seat.is_leadership ? " ★" : ""} of {seat.faction_name}</span>
          <small> · dead since {seat.life_status_since}</small>
        </li>)}</ul>
      </details>}
    </>}
  </section>;
}

function UnpromotedMaterialPanel({ campaignClient, onOpenEntry, onOpenDocument, onOpenBrainstorm }: {
  campaignClient: CampaignClient;
  onOpenEntry?: (entityId: string, entityName: string) => void;
  onOpenDocument?: (documentId: string, documentPath: string) => void;
  onOpenBrainstorm?: () => void;
}) {
  const [result, setResult] = useState<UnpromotedAuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");

  const run = useCallback(async () => {
    setLoading(true);
    try {
      const audit = await campaignClient.getUnpromotedMaterial();
      setResult(audit);
      setNotice("");
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "The unpromoted-material audit could not run");
    } finally { setLoading(false); }
  }, [campaignClient]);

  const kindLabel: Record<string, string> = {
    empty_shell: "Empty shell — page but no claims",
    pending_capture: "Captured, never reviewed",
    unpromoted_thoughts: "Unpromoted brainstorm thoughts",
  };
  const findings = result?.findings ?? [];

  return <section className="page-panel" aria-label="Unpromoted material">
    <h3>Unpromoted material</h3>
    <p className="roles-explainer">The Promotion Pipeline repair lane: in-app material written but never promoted — entries with a page and no claims, captured statements still pending, brainstorm thoughts left behind. Findings are computed fresh each run; every fix goes through its surface's reviewed door.</p>
    <button className="secondary-button" disabled={loading} onClick={() => void run()} type="button">{loading ? "Auditing…" : result ? "Re-run audit" : "Run audit"}</button>
    {notice && <div className="notice error" role="alert">{notice}</div>}
    {result && <p className="identity-count">{findings.length === 0 ? "No unpromoted material — everything written has been reviewed." : `${findings.length} finding${findings.length === 1 ? "" : "s"} · ${new Date(result.audited_at).toLocaleTimeString()}`}</p>}
    {findings.length > 0 && <div className="source-review-queue">
      {findings.map((finding) => <article key={`${finding.kind}-${finding.entity_id ?? finding.document_id ?? finding.session_id}`} className="unpromoted-finding">
        <span>{kindLabel[finding.kind] ?? finding.kind}{finding.count > 0 ? ` · ${finding.count}` : ""}</span>
        <b>{finding.entity_name}</b>
        <p>{finding.detail}</p>
        <div className="lore-item-actions">
          {finding.kind === "empty_shell" && finding.entity_id && onOpenEntry && <button onClick={() => onOpenEntry(finding.entity_id ?? "", finding.entity_name)} type="button">Open entry — revise its description</button>}
          {finding.kind === "pending_capture" && finding.document_id && onOpenDocument && <button onClick={() => onOpenDocument(finding.document_id!, finding.document_path ?? "")} type="button">Open capture — review statements</button>}
          {finding.kind === "unpromoted_thoughts" && onOpenBrainstorm && <button onClick={onOpenBrainstorm} type="button">Open Brainstorm — promote thoughts</button>}
        </div>
      </article>)}
    </div>}
  </section>;
}

function QualifiedEntitiesPanel({ campaignClient, onOpenEntry, onOpenProfile }: {
  campaignClient: CampaignClient;
  onOpenEntry?: (entityId: string, entityName: string) => void;
  onOpenProfile?: (entityId: string, entityName: string) => void;
}) {
  const [result, setResult] = useState<QualifiedAuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [busyValue, setBusyValue] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    try {
      const audit = await campaignClient.getQualifiedEntities();
      setResult(audit);
      setNotice("");
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "The qualification audit could not run");
    } finally { setLoading(false); }
  }, [campaignClient]);

  // Step 1 (2026-09-22 ruling): document-exclusive claims with checked
  // boxes and one Assign Ownership action per entity.
  const [docClaims, setDocClaims] = useState<ExclusiveClaimsResult | null>(null);
  const [docClaimsLoading, setDocClaimsLoading] = useState(false);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [assigningFor, setAssigningFor] = useState<string | null>(null);

  const gatherDocumentClaims = useCallback(async () => {
    setDocClaimsLoading(true);
    try {
      const result = await campaignClient.getExclusiveClaims();
      setDocClaims(result);
      const nextChecked: Record<string, boolean> = {};
      for (const group of result.groups) for (const claim of group.claims) nextChecked[claim.claim_id] = true;
      setChecked(nextChecked);
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "The document-claims gather could not run");
    } finally { setDocClaimsLoading(false); }
  }, [campaignClient]);

  const assignOwnership = useCallback(async (group: EntityDocumentClaims) => {
    if (assigningFor) return;
    const claimIds = group.claims.filter((claim) => checked[claim.claim_id]);
    if (claimIds.length === 0) return;
    setAssigningFor(group.entity_id);
    let moved = 0;
    const errors: string[] = [];
    for (const claim of claimIds) {
      try {
        await campaignClient.reattributeClaim(claim.claim_id, group.entity_id, "Assign Ownership: " + group.canonical_name + "'s document claims");
        moved += 1;
      } catch (cause) {
        errors.push(cause instanceof Error ? cause.message : String(cause));
      }
    }
    setAssigningFor(null);
    toast.push(moved > 0 ? "success" : "error",
      "Assigned " + moved + " of " + claimIds.length + " claim" + (claimIds.length === 1 ? "" : "s") + " to " + group.canonical_name + (errors.length > 0 ? " — " + errors.length + " failed (see Log)" : ""));
    await gatherDocumentClaims();
    await run();
  }, [campaignClient, checked, assigningFor, gatherDocumentClaims, run]);

  const restoreValue = async (vocabulary: string, value: string) => {
    if (busyValue) return;
    setBusyValue(`${vocabulary}:${value}`);
    try {
      await campaignClient.changeTemplateVocabulary(vocabulary, "add", value);
      toast.push("success", `Vocabulary: "${value}" restored — offered again (receipt filed)`);
      await run();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "The value could not be restored");
    } finally { setBusyValue(null); }
  };

  const groupLabels: Record<string, string> = {
    q1_asserts: "No claims — the record asserts nothing",
    q4_kind: "Kind structure",
    q6_vocabulary: "Retired vocabulary values in use",
  };
  const findings = result?.unqualified ?? [];
  const byCriterion = findings.reduce<Record<string, typeof findings>>((acc, finding) => {
    for (const criterion of finding.criteria) {
      if (criterion.status === "fail") (acc[criterion.criterion] ??= []).push(finding);
    }
    return acc;
  }, {});

  return <section className="page-panel" aria-label="Qualified entities">
    <h3>Qualified entities</h3>
    <p className="roles-explainer">The bar, computed live: every record asserts, is evidenced, is owned — binary, per the standard. Drive the count to zero and the audit holds it there. Pending criteria (orphan ownership, claim-backed attributes) report as pending until their mechanisms land.</p>
    <button className="secondary-button" disabled={loading} onClick={() => void run()} type="button">{loading ? "Auditing…" : result ? "Re-run audit" : "Run audit"}</button>
    {notice && <div className="notice error" role="alert">{notice}</div>}
    {result && <p className="identity-count">{result.qualified_count} of {result.total_entities} qualified · {findings.length} unqualified · {new Date(result.audited_at).toLocaleTimeString()}</p>}
    <div className="qualified-step1" aria-label="Document-exclusive claims">
      <header><div><span>Step 1 — Assign Ownership</span><h4>Claims that live only on the record's document</h4></div>
        <button className="secondary-button" disabled={docClaimsLoading} onClick={() => void gatherDocumentClaims()} type="button">{docClaimsLoading ? "Gathering…" : docClaims ? "Re-gather" : "Gather document claims"}</button></header>
      <p className="roles-explainer">For every unqualified record: the claims evidenced only on the document that represents it — the migration's material whose ownership was never assigned. Checked means included; Assign Ownership re-attributes the checked claims to the record (receipted, provenance untouched).</p>
      {docClaims && <p className="identity-count">{docClaims.entities_with_exclusive_claims} record{docClaims.entities_with_exclusive_claims === 1 ? "" : "s"} · {docClaims.total_claims} exclusive claim{docClaims.total_claims === 1 ? "" : "s"}</p>}
      {docClaims?.groups.map((group) => <details className="qualified-step1-group" key={group.entity_id} open>
        <summary>{group.canonical_name} <small>{group.claims.length} claim{group.claims.length === 1 ? "" : "s"} · {group.document_path}</small></summary>
        {group.claims.map((claim) => <label className="gathered-claim" key={claim.claim_id}>
          <input aria-label={"Include claim for " + group.canonical_name + ": " + claim.assertion_text.slice(0, 40)} checked={Boolean(checked[claim.claim_id])} onChange={(event) => setChecked((current) => ({ ...current, [claim.claim_id]: event.target.checked }))} type="checkbox" />
          <span>{claim.assertion_text}
            <small className="ai-activation-note"> · {claim.owner_name ? "currently owned by " + claim.owner_name : "no owner — initial attribution"} · {display(claim.state)}</small>
          </span>
        </label>)}
        <div className="lore-item-actions">
          <button className="decision-button" disabled={assigningFor !== null || !group.claims.some((claim) => checked[claim.claim_id])} onClick={() => void assignOwnership(group)} type="button">{assigningFor === group.entity_id ? "Assigning…" : "Assign Ownership (" + group.claims.filter((claim) => checked[claim.claim_id]).length + ")"}</button>
        </div>
      </details>)}
    </div>
    {Object.entries(byCriterion).map(([criterion, group]) => <div className="source-review-queue" key={criterion}>
      <header><span>{groupLabels[criterion] ?? criterion}</span><b>{group.length}</b></header>
      {group.map((finding) => <article key={finding.entity_id} className="unpromoted-finding">
        <span>{display(finding.entity_kind ?? "")}</span>
        <b>{finding.canonical_name}</b>
        <p>{finding.criteria.filter((c) => c.status === "fail").map((c) => c.reason).join("; ")}</p>
        <div className="lore-item-actions">
          {criterion === "q6_vocabulary" && finding.criteria.filter((c) => c.status === "fail" && c.vocabulary && c.value).map((c) => (
            <button disabled={busyValue === `${c.vocabulary}:${c.value}`} key={`${c.vocabulary}:${c.value}`} onClick={() => void restoreValue(c.vocabulary!, c.value!)} type="button">Re-activate "{c.value}"</button>
          ))}
          {criterion !== "q6_vocabulary" && onOpenEntry && <button onClick={() => onOpenEntry(finding.entity_id, finding.canonical_name)} type="button">Open entry — write its description</button>}
          {criterion === "q4_kind" && onOpenProfile && <button onClick={() => onOpenProfile(finding.entity_id, finding.canonical_name)} type="button">Fix kind</button>}
        </div>
      </article>)}
    </div>)}
  </section>;
}

function Phase2MigrationsPage({ campaignClient, onOpenEntry, onOpenProfile, onOpenDocument, onOpenBrainstorm }: {
  campaignClient: CampaignClient;
  onOpenEntry: (entityId: string, entityName: string) => void;
  onOpenProfile: (entityId: string, entityName: string) => void;
  onOpenDocument: (documentId: string, documentPath: string) => void;
  onOpenBrainstorm: () => void;
}) {
  return <main className="page-migration2">
    <section className="identity-page-header" aria-label="Phase 2 migrations">
      <div className="section-heading"><div><p className="kicker">Migration phase 2</p><h2>Migrations</h2></div>
        <p>The completion campaign: force every Entity-shaped record through to the Qualified bar — then never hold an unQualified Entity again. Phase 1 (the Starfall import) closed 2026-08-22; its wizard is shelved (Settings).</p></div>
    </section>
    <QualifiedEntitiesPanel campaignClient={campaignClient} onOpenEntry={onOpenEntry} onOpenProfile={onOpenProfile} />
    <UnpromotedMaterialPanel campaignClient={campaignClient} onOpenEntry={onOpenEntry} onOpenDocument={onOpenDocument} onOpenBrainstorm={onOpenBrainstorm} />
  </main>;
}

function LinkAuditPanel({ campaignClient, onOpenEntry }: { campaignClient: CampaignClient; onOpenEntry?: (entityId: string, entityName: string) => void }) {
  const [result, setResult] = useState<LinkAuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");

  const run = useCallback(async () => {
    setLoading(true);
    try {
      const audit = await campaignClient.getLinkAudit();
      setResult(audit);
      setNotice("");
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "The link audit could not run");
    } finally { setLoading(false); }
  }, [campaignClient]);

  const kindLabel: Record<string, string> = {
    wrong_page_borrow: "Wrong-page borrow", zero_affinity: "No page of its own",
  };
  const findings = result?.findings ?? [];
  const byKind = findings.reduce<Record<string, typeof findings>>((acc, f) => {
    (acc[f.kind] ??= []).push(f);
    return acc;
  }, {});

  return <section className="page-panel" aria-label="Link audit">
    <h3>Link audit</h3>
    <p className="roles-explainer">Live traversal of entity↔source links across every claim-evidenced source. Findings are computed fresh each run — nothing is stored, nothing changes. Every fix is your decision.</p>
    <button className="secondary-button" disabled={loading} onClick={() => void run()} type="button">{loading ? "Auditing…" : result ? "Re-run audit" : "Run audit"}</button>
    {notice && <div className="notice error" role="alert">{notice}</div>}
    {result && <p className="identity-count">{findings.length === 0 ? "No findings — all entity↔source links look correct." : `${findings.length} finding${findings.length === 1 ? "" : "s"} across ${Object.keys(byKind).length} categor${Object.keys(byKind).length === 1 ? "y" : "ies"} · ${new Date(result.audited_at).toLocaleTimeString()}`}</p>}
    {Object.entries(byKind).map(([kind, items]) => <div key={kind} className="link-audit-group">
      <h4>{kindLabel[kind] ?? kind} ({items.length})</h4>
      {items.map((finding, index) => <article className="link-audit-finding" key={`${finding.entity_id}-${index}`}>
        <div><b>{finding.entity_name}</b><span className="role-chip">{display(finding.entity_kind)}</span></div>
        <p>{finding.detail}</p>
        {finding.entity_id && onOpenEntry && <button className="text-button" onClick={() => onOpenEntry(finding.entity_id!, finding.entity_name)} type="button">Open {finding.entity_name}</button>}
      </article>)}
    </div>)}
  </section>;
}

function ConflictReviewPanel({ campaignClient }: { campaignClient: CampaignClient }) {
  const [conflicts, setConflicts] = useState<ConflictPair[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);

  const load = useCallback(async () => {
    try {
      setConflicts(await campaignClient.getConflictQueue());
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Conflict queue is unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { if (conflicts === null) void load(); }, [conflicts === null, load]);

  const decide = async (pair: ConflictPair, action: "dismiss" | "supersede") => {
    const reason = action === "dismiss"
      ? `Historical mention kept alongside ${pair.entity_name}'s observed death (${pair.claim_a_date})`
      : `Retired: contradicts the observed death of ${pair.entity_name} on ${pair.claim_a_date}`;
    setBusy(pair.claim_b_id);
    try {
      const result = await campaignClient.decideConflict(pair.claim_a_id, pair.claim_b_id, action, reason);
      setMessageIsError(false);
      setMessage(action === "dismiss"
        ? `Kept both — reviewed ${pair.entity_name} pair (receipt ${result.decision_id.slice(0, 8)})`
        : `Superseded the ${pair.claim_b_date} claim — death of ${pair.entity_name} stands (change set ${(result.change_set_id ?? "").slice(0, 8)})`);
      toast.push("success", action === "dismiss" ? `Conflict reviewed — kept both` : `Claim superseded — ${pair.entity_name}'s death stands`);
      await load();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "The decision failed");
      toast.push("error", error instanceof Error ? error.message : "The decision failed");
    } finally { setBusy(null); }
  };

  return <section className="page-panel conflict-review" aria-label="Conflict review">
    <div className="section-heading"><div><p className="kicker">Campaign maintenance</p><h2>Conflict review</h2></div>
      <p>Mechanical detection: an observed, dated death versus a current claim about the same record dated strictly later. Time keeps historical mentions out; every decision is receipted. <Term term="authority">Authority</Term> is shown on both sides — real play outranks lore.</p></div>
    {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    {conflicts === null ? <p className="queue-empty">Loading…</p> : <>
      <p className="identity-count">SHOWING {conflicts.length} CONFLICT{conflicts.length === 1 ? "" : "S"}</p>
      {conflicts.length === 0 && <p className="identity-empty">No detected conflicts right now. Observed deaths stand clean against dated claims.</p>}
      {conflicts.map((pair) => <article className="conflict-card" key={pair.claim_b_id} aria-label={`Conflict: ${pair.entity_name}`}>
        <h3>{pair.entity_name} <small>death observed {pair.claim_a_date}</small></h3>
        <div className="conflict-sides">
          <div className="conflict-side conflict-death">
            <span className="log-kind">Observed death</span>
            <p>{pair.claim_a_assertion.slice(0, 320)}{pair.claim_a_assertion.length > 320 ? "…" : ""}</p>
          </div>
          <div className="conflict-side conflict-later">
            <span className="log-kind">Later claim · {pair.claim_b_date} · {display(pair.claim_b_authority)}</span>
            <p>{pair.claim_b_assertion.slice(0, 320)}{pair.claim_b_assertion.length > 320 ? "…" : ""}</p>
          </div>
        </div>
        <p className="roles-explainer">If the later claim recounts pre-death events in past tense, keep both. If it asserts {pair.entity_name} operative after death, retire it.</p>
        <div className="conflict-actions">
          <button className="text-button" disabled={busy === pair.claim_b_id} onClick={() => void decide(pair, "dismiss")} type="button">Keep both — historical</button>
          <button className="decision-button" disabled={busy === pair.claim_b_id} onClick={() => void decide(pair, "supersede")} type="button">Retire later claim</button>
        </div>
      </article>)}
    </>}
  </section>;
}

function SessionDatingPanel({ campaignClient }: { campaignClient: CampaignClient }) {
  const [entries, setEntries] = useState<SessionDatingEntry[] | null>(null);
  const [residue, setResidue] = useState<UndatedClaimEntry[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);

  const load = useCallback(async () => {
    try {
      const [walk, undated] = await Promise.all([
        campaignClient.getSessionDatingWalk(),
        campaignClient.getUndatedClaims(20).catch(() => [] as UndatedClaimEntry[]),
      ]);
      setEntries(walk);
      setResidue(undated);
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Session dating is unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { if (entries === null) void load(); }, [entries === null, load]);

  const previousDated = (index: number): SessionDatingEntry | null => {
    for (let prior = index - 1; prior >= 0; prior -= 1) {
      if (entries![prior].year !== null && entries![prior].year !== undefined) return entries![prior];
    }
    return null;
  };

  const save = async (entry: SessionDatingEntry) => {
    const raw = (drafts[entry.document_id] ?? "").trim();
    const match = raw.match(/^(-?\d{1,6})-(\d{1,2})-(\d{1,2})$/);
    if (!match) {
      setMessageIsError(true);
      setMessage(`Enter ${entry.title}'s date as year-month-day, e.g. 505-11-20`);
      return;
    }
    const [, year, month, day] = match;
    setBusy(entry.document_id);
    try {
      const result = await campaignClient.setSessionDate(
        entry.document_id, Number(year), Number(month), Number(day), "reconstructed");
      setMessageIsError(false);
      setMessage(`Dated ${entry.title} to ${year}-${month}-${day} · ${result.claims_stamped} claim${result.claims_stamped === 1 ? "" : "s"} stamped`);
      toast.push("success", `Dated ${entry.title} · ${result.claims_stamped} claims stamped`);
      await load();
      setDrafts((current) => { const next = { ...current }; delete next[entry.document_id]; return next; });
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "The date could not be saved");
      toast.push("error", error instanceof Error ? error.message : "The date could not be saved");
    } finally { setBusy(null); }
  };

  const syncAll = async () => {
    setBusy("inherit");
    try {
      const result = await campaignClient.inheritClaimDates();
      setMessageIsError(false);
      setMessage(`Inheritance sync: ${result.claims_stamped} claim${result.claims_stamped === 1 ? "" : "s"} stamped from dated documents`);
      toast.push("success", `Inheritance: ${result.claims_stamped} claims stamped`);
      await load();
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Inheritance failed");
    } finally { setBusy(null); }
  };

  const datedCount = (entries ?? []).filter((entry) => entry.year !== null && entry.year !== undefined).length;
  const total = entries?.length ?? 0;
  const undatedResidue = residue.length;

  return <section className="page-panel session-dating" aria-label="Session dating walk">
    <div className="section-heading"><div><p className="kicker">Campaign timeline</p><h2>Session dating walk</h2></div>
      <p>Date each session note's in-world day; its claims inherit the date from provenance immediately. Walk in play order — the previous dated session is shown as your anchor.</p></div>
    {message && <p role={messageIsError ? "alert" : "status"} className={"identity-message" + (messageIsError ? " notice error" : "")}>{message}</p>}
    {entries === null ? <p className="queue-empty">Loading…</p> : <>
      <p className="identity-count">SHOWING {datedCount} OF {total} SESSIONS DATED{undatedResidue > 0 ? ` · ${undatedResidue} UNDATED CLAIMS IN RESIDUE` : ""}</p>
      {total === 0 && <p className="identity-empty">No session sources found.</p>}
      <ul className="dating-walk-list">
        {entries.map((entry, index) => {
          const prior = previousDated(index);
          const draft = drafts[entry.document_id] ?? (entry.year ? `${entry.year}-${entry.month}-${entry.day}` : "");
          const goesBackwards = prior !== null && prior.year !== null
            && (Number((drafts[entry.document_id] ?? "").split("-")[0]) || 0) > 0
            && (() => { const m = (drafts[entry.document_id] ?? "").match(/^(-?\d{1,6})-(\d{1,2})-(\d{1,2})$/); if (!m) return false;
              const [y, mo, d] = m.slice(1).map(Number);
              return y < (prior.year ?? 0) || (y === prior.year && (mo < (prior.month ?? 0) || (mo === (prior.month ?? 0) && d < (prior.day ?? 0)))); })();
          return <li className="dating-row" key={entry.document_id}>
            <div className="dating-when">
              <b>{entry.title}</b>
              <small>{entry.session_date ? `played ${entry.session_date}` : entry.path}</small>
              {prior && <small className="dating-anchor">after {prior.year}-{prior.month}-{prior.day}</small>}
            </div>
            <div className="dating-set">
              {entry.dated_by === "capture"
                ? <span className="dating-current">{entry.year}-{entry.month}-{entry.day} <small>capture</small></span>
                : <>
                  <input aria-label={`Campaign date for ${entry.title}`} placeholder="505-11-20" value={draft}
                         onChange={(event) => setDrafts((current) => ({ ...current, [entry.document_id]: event.target.value }))} />
                  <button className="text-button" disabled={busy === entry.document_id}
                          onClick={() => void save(entry)} type="button">{entry.dated_by === "dm" ? "Re-date" : "Date"}</button>
                  {entry.undated_claims > 0 && <small className="dating-claims">{entry.undated_claims} claims waiting</small>}
                </>}
              {goesBackwards && <small className="dating-backwards">before the previous dated session — confirm</small>}
            </div>
          </li>; })}
      </ul>
      <div className="step-actions">
        <button className="secondary-button" disabled={busy !== null} onClick={() => void syncAll()} type="button">
          {busy === "inherit" ? "Syncing…" : "Sync claim dates from dated sources"}</button>
      </div>
      {residue.length > 0 && <details className="residue-queue"><summary>Undated claims ({residue.length} shown) — conflict-ranked</summary>
        <p className="roles-explainer">Present-state claims about entities with dated events surface first: these are the collisions conflict review will care about. Static lore and descriptions surface last or never.</p>
        <ul>{residue.map((claim) => <li key={claim.claim_id} className={claim.conflict_relevant ? "residue-relevant" : ""}>
          <span className="log-message">{claim.assertion}</span>
          {claim.entities.length > 0 && <small> · {claim.entities.join(", ")}</small>}
          {claim.conflict_relevant && <span className="tree-doc-flag">collision risk</span>}
        </li>)}</ul>
      </details>}
    </>}
  </section>;
}

function CampaignClockChip({ campaignClient, onDateChanged }: { campaignClient: CampaignClient; onDateChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<CampaignDate | null | undefined>(undefined);
  const [history, setHistory] = useState<CampaignClockChange[]>([]);
  const [year, setYear] = useState("");
  const [month, setMonth] = useState("");
  const [day, setDay] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [date, changes] = await Promise.all([
        campaignClient.getCurrentCampaignDate().catch(() => null),
        campaignClient.getCampaignDateHistory(5).catch(() => [] as CampaignClockChange[]),
      ]);
      setCurrent(date);
      setHistory(changes);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Campaign clock is unavailable");
    }
  }, [campaignClient]);

  useEffect(() => { if (current === undefined) void load(); }, [current === undefined, load]);

  const applyFields = (date: CampaignDate) => {
    setYear(String(date.year)); setMonth(String(date.month)); setDay(String(date.day));
  };
  useEffect(() => { if (current) applyFields(current); }, [current?.year, current?.month, current?.day]);

  const advance = (days: number) => {
    if (!year || !month || !day) return;
    const base = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
    base.setUTCDate(base.getUTCDate() + days);
    setYear(String(base.getUTCFullYear()));
    setMonth(String(base.getUTCMonth() + 1));
    setDay(String(base.getUTCDate()));
  };

  const save = async () => {
    setBusy(true);
    try {
      const next = await campaignClient.setCurrentCampaignDate(
        { calendar_id: "gregorian-ce", year: Number(year), month: Number(month), day: Number(day) },
        reason.trim() || undefined);
      setCurrent(next);
      setReason("");
      await load();
      onDateChanged();
      toast.push("success", `Campaign date set to ${next.year}-${String(next.month).padStart(2, "0")}-${String(next.day).padStart(2, "0")}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Campaign date could not be set");
      toast.push("error", caught instanceof Error ? caught.message : "Campaign date could not be set");
    } finally { setBusy(false); }
  };

  const valid = Number(year) > 0 && Number(month) >= 1 && Number(month) <= 12 && Number(day) >= 1 && Number(day) <= 31;
  const label = current
    ? `${current.year}-${String(current.month).padStart(2, "0")}-${String(current.day).padStart(2, "0")} CE`
    : "Set campaign date";
  return <div className="campaign-clock">
    <button aria-expanded={open} className="campaign-clock-chip" onClick={() => setOpen((value) => !value)} title="Current in-world date — click to manage" type="button">
      <span className="campaign-clock-kicker">Today</span>{label}
    </button>
    {open && <div className="campaign-clock-panel" role="dialog" aria-label="Campaign clock">
      <b>Campaign clock</b>
      <p className="roles-explainer">The current in-world date. Session captures advance it automatically; set or advance it here between sessions — new dated entries default from it.</p>
      <div className="form-grid">
        <label>Year<input aria-label="Campaign year" inputMode="numeric" value={year} onChange={(event) => setYear(event.target.value)} /></label>
        <label>Month<input aria-label="Campaign month" inputMode="numeric" value={month} onChange={(event) => setMonth(event.target.value)} /></label>
        <label>Day<input aria-label="Campaign day" inputMode="numeric" value={day} onChange={(event) => setDay(event.target.value)} /></label>
      </div>
      <div className="campaign-clock-actions">
        <button className="text-button" onClick={() => advance(1)} type="button">+1 day</button>
        <button className="text-button" onClick={() => advance(7)} type="button">+7 days</button>
        <button className="decision-button" disabled={busy || !valid} onClick={() => void save()} type="button">{busy ? "Saving…" : "Set date"}</button>
      </div>
      <label>Reason (optional)<input aria-label="Campaign date change reason" placeholder="Session end; time skip" value={reason} onChange={(event) => setReason(event.target.value)} /></label>
      {error && <p role="alert" className="notice error">{error}</p>}
      {history.length > 0 && <div className="campaign-clock-history" aria-label="Recent clock changes">
        <span>Recent changes</span>
        {history.map((change, index) => (
          <small key={index}>{change.year}-{String(change.month).padStart(2, "0")}-{String(change.day).padStart(2, "0")}
            {change.reason ? ` — ${change.reason}` : ""} · {new Date(change.changed_at).toLocaleString()}</small>
        ))}
      </div>}
    </div>}
  </div>;
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

export function cleanImportedAssertion(value: string): string {
  return value
    .split(/\r?\n/)
    .filter((line) => !/^\s*Source:\s*\[\[.*\]\]\s*$/i.test(line))
    .filter((line) => !/^\s*#{1,6}\s+/.test(line))
    .filter((line) => !/^\s*These are GM planning notes only\b/i.test(line))
    .map((line) => line.replace(/^\s*-\s+/, "").replaceAll("**", "").trimEnd())
    .join("\n")
    // Real-world date headers are provenance, not campaign truth (TKT-0122):
    // a leading 12/6/25 stays in the source note, never the canonical claim.
    .replace(/^\s*\d{1,2}\/\d{1,2}\/\d{2,4}[\s:.—–-]+/, "")
    .replace(/^\s*\d{4}-\d{2}-\d{2}[\s:.—–-]+/, "")
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
  const [identityMessageIsError, setIdentityMessageIsError] = useState(false);
  const [identityKinds, setIdentityKinds] = useState<Record<string, string>>({});
  const [identityAliasSelection, setIdentityAliasSelection] = useState<Record<string, string[]>>({});
  const [identityRecent, setIdentityRecent] = useState<{ receipt: IdentityDecisionReceipt; done: string }[]>([]);
  const [identityQueueTotal, setIdentityQueueTotal] = useState(0);
  const [entityProfile, setEntityProfile] = useState<EntityProfile | null>(null);
  const [entityProfileDraft, setEntityProfileDraft] = useState<EntityProfile | null>(null);
  const [entityProfileEditing, setEntityProfileEditing] = useState(false);
  const [entityProfileMessage, setEntityProfileMessage] = useState("");
  const [entityProfileMessageIsError, setEntityProfileMessageIsError] = useState(false);
  const [descriptionComposerOpen, setDescriptionComposerOpen] = useState(false);
  // Seeded prose + page document when revising an authored description;
  // null means the composer opens fresh (first write).
  const [revisionDraft, setRevisionDraft] = useState<string | null>(null);
  // A claimed Drafts-tray result also carries the citations it used.
  const [claimSelection, setClaimSelection] = useState<{ claimIds: string[]; relationKeys: string[] } | null>(null);
  const [composerDirty, setComposerDirty] = useState(false);
  // TKT-0127: the Drafts tray — background prose jobs parked until claimed.
  const [draftQueue, setDraftQueue] = useState<DraftQueueItem[]>([]);
  const [draftPenOpen, setDraftPenOpen] = useState(false);
  // TKT-0128: Ask-the-archive lives in the tray array; the topbar magnifier opens it.
  const [searchTrayOpen, setSearchTrayOpen] = useState(false);
  const draftPollTimer = useRef<number | null>(null);
  const [entityProfileBaseline, setEntityProfileBaseline] = useState<string | null>(null);
  const [blockedSwitch, setBlockedSwitch] = useState<{ label: string; proceed: () => void } | null>(null);
  const [identityViewMode, setIdentityViewMode] = useState<"cards" | "compact">("cards");
  const [identityVisibleCount, setIdentityVisibleCount] = useState(20);
  const [identityCanonical, setIdentityCanonical] = useState<Record<string, string>>({});
  const [identityManualAliases, setIdentityManualAliases] = useState<Record<string, string>>({});
  const [identityTargetQuery, setIdentityTargetQuery] = useState<Record<string, string>>({});
  const [identityTargetResults, setIdentityTargetResults] = useState<Record<string, EntityIdentity[]>>({});
  const [memberSearch, setMemberSearch] = useState("");
  const [memberResults, setMemberResults] = useState<EntityIdentity[]>([]);
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
          toast.push("error", error instanceof Error ? error.message : "Extraction job status is unavailable");
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
        toast.push("error", message);
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
        toast.push("error", message);
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
          toast.push("error", error instanceof Error ? error.message : "Extracted candidate could not be refreshed");
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
      toast.push("error", error instanceof Error ? error.message : "Import review is unavailable");
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
      toast.push("error", error instanceof Error ? error.message : "Candidate could not be loaded");
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
      toast.push("info", `${candidateIds.length} failed candidate${candidateIds.length === 1 ? "" : "s"} queued again.`);
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
        message: "Source-backed claim is ready for exact approval.",
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
        ...(provenanceState === "observed" && observedCampaignDate ? (() => { const [year, month, day] = observedCampaignDate.split("-").map(Number); return { observed_at: { calendar_id: "gregorian-ce", year, month, day }, effective_from: { calendar_id: "gregorian-ce", year, month, day } }; })() : {}),
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
      const queue = await campaignClient.getIdentityGaps(200);
      setIdentityGaps(queue.gaps);
      setIdentityQueueTotal(queue.total_candidates);
      // Related surfaces default to selected: merging variants is the common
      // case, and deselecting is the explicit refusal. Kind defaults to the
      // queue's deterministic suggestion; canonical names start from the
      // title-prefix suggestion when one exists.
      setIdentityAliasSelection(Object.fromEntries(queue.gaps.map((gap) => [
        gap.normalized_surface, [...gap.related_surfaces]])));
      setIdentityKinds(Object.fromEntries(queue.gaps
        .filter((gap) => gap.suggested_kind)
        .map((gap) => [gap.normalized_surface, gap.suggested_kind as string])));
      setIdentityCanonical(Object.fromEntries(queue.gaps.map((gap) => [
        gap.normalized_surface, gap.suggested_canonical_name ?? gap.surface])));
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
      setIdentityRecent((current) => [{ receipt, done }, ...current].slice(0, 5));
      await loadIdentityGaps();
      // Identity decisions change the library immediately; refresh it so new
      // entities and aliases appear without a manual page reload.
      campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {});
      const linked = receipt.linked_claims ? ` · ${receipt.linked_claims} claim${receipt.linked_claims === 1 ? "" : "s"} linked` : "";
      setIdentityMessageIsError(false);
      setIdentityMessage(`${done} with receipt ${receipt.decision_id}${linked}`);
      toast.push("success", `${done}${linked}`);
    } catch (error) {
      setIdentityMessageIsError(true);
      setIdentityMessage(error instanceof Error && error.message ? error.message : "Identity decision failed");
      toast.push("error", error instanceof Error && error.message ? error.message : "Identity decision failed");
    } finally {
      setIdentityBusy(false);
    }
  }, [campaignClient, loadIdentityGaps]);

  const undoIdentity = useCallback(async (decisionId: string, done: string) => {
    await decideIdentity(
      () => campaignClient.revertIdentityDecision(decisionId, `identity-revert:${decisionId}:${Date.now()}`),
      `Reverted “${done}”`);
  }, [campaignClient, decideIdentity]);

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

  const sourceBackedLibraryDocuments = useMemo(() => {
    const canonicalPCNames = new Set(libraryEntries.filter((entry) => entry.entity_kind === "pc").map((entry) => entry.canonical_name.trim().toLocaleLowerCase()));
    const canonicalEntryNames = new Set(libraryEntries.map((entry) => normalizeEntryName(entry.canonical_name)));
    return sourceDocuments.filter((doc) => (isSourceBackedEntry(doc) || (
      /^pcs\//i.test(doc.path) && !canonicalPCNames.has((doc.title ?? entryLabel(doc.path)).trim().toLocaleLowerCase())
    )) && !(
      // Session notes are events, not entity pages; everything else whose
      // filename exactly names an entity is hidden behind that entity's entry.
      !/^sessions\//i.test(doc.path)
      && canonicalEntryNames.has(normalizeEntryName(doc.path.split("/").pop()?.replace(/\.md$/, "") ?? ""))
    ));
  }, [libraryEntries, sourceDocuments]);

  const editableSessionDocuments = useMemo(
    () => sourceDocuments.filter((document) => document.document_type === "session_note" && document.capture_mode === "direct_input")
      .sort((left, right) => (right.session_date ?? "").localeCompare(left.session_date ?? "")),
    [sourceDocuments],
  );

  const [helpAnchor, setHelpAnchor] = useState<string | null>(null);
  useEffect(() => {
    registerGlossaryNavigation((term) => { setHelpAnchor(term); setActivePage("help"); });
    return () => registerGlossaryNavigation(null);
  }, []);
  const [activePage, setActivePage] = useState<"documents" | "brainstorm" | "identity" | "roles" | "migration" | "migration-legacy" | "lore" | "tools" | "log" | "help" | "conventions" | "settings">("documents");
  const [appSettings, updateAppSettings] = useSettings();

  const openEntityProfileEditor = useCallback(() => {
    if (!selectedEntry) return;
    const draft = entityProfile ?? {
      entity_id: selectedEntry.entry_id, version: 0,
      canonical_name: selectedEntry.canonical_name, status: null,
      location_type: null, parent_location: null, player: null,
      race: null, sex: null, aliases: [...selectedEntry.aliases], summary: "",
    };
    setEntityProfileDraft(draft);
    setEntityProfileBaseline(JSON.stringify(draft));
    setEntityProfileEditing(true);
  }, [entityProfile, selectedEntry]);

  const correctEntityKind = useCallback(async (kind: string) => {
    if (!selectedEntry) return;
    try {
      const proposal = await campaignClient.proposeEntityKind(selectedEntry.entry_id, kind);
      const approval = await campaignClient.approveEntityMetadataProposal(
        proposal.proposal_id, proposal.item.item_id, proposal.version_number,
        proposal.content_hash);
      await campaignClient.applyApproval(
        { version_number: proposal.version_number, content_hash: proposal.content_hash },
        approval);
      setEntityProfileMessageIsError(false);
      setEntityProfileMessage(`Kind corrected to ${display(kind)} — proposal ${proposal.proposal_id.slice(0, 8)} applied`);
      toast.push("success", `Kind corrected to ${display(kind)} — proposal ${proposal.proposal_id.slice(0, 8)} applied`);
      await loadCanonicalEntry(selectedEntry.entry_id);
      setEntityProfileEditing(false);
      campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {});
    } catch (error) {
      setEntityProfileMessageIsError(true);
      setEntityProfileMessage(error instanceof Error ? error.message : "Kind correction failed");
      toast.push("error", error instanceof Error ? error.message : "Kind correction failed");
    }
  }, [campaignClient, selectedEntry, loadCanonicalEntry]);

  const addFactionMember = useCallback(async (member: EntityIdentity) => {
    if (!selectedEntry) return;
    setMemberSearch("");
    setMemberResults([]);
    // Refusals ("already a member") must be visible here in the editor, not
    // on the Identity page the DM is not looking at.
    try {
      const receipt = await campaignClient.addMembership(selectedEntry.entry_id, member.entity_id);
      setEntityProfileMessageIsError(false);
      setEntityProfileMessage(`Added ${member.canonical_name} to ${selectedEntry.canonical_name} with receipt ${receipt.decision_id.slice(0, 8)}`);
      toast.push("success", `Added ${member.canonical_name} to ${selectedEntry.canonical_name}`);
    } catch (error) {
      setEntityProfileMessageIsError(true);
      setEntityProfileMessage(error instanceof Error && error.message ? error.message : "Membership decision failed");
      toast.push("error", error instanceof Error && error.message ? error.message : "Membership decision failed");
      return;
    }
    campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {});
    // The roster lives on the library entry; reload it so the list updates in place.
    await loadCanonicalEntry(selectedEntry.entry_id);
  }, [campaignClient, selectedEntry, loadCanonicalEntry]);

  const removeFactionMember = useCallback(async (member: LibraryMember) => {
    if (!selectedEntry) return;
    try {
      const receipt = await campaignClient.removeMembership(selectedEntry.entry_id, member.member_id);
      setEntityProfileMessageIsError(false);
      setEntityProfileMessage(`Removed ${member.name} from ${selectedEntry.canonical_name} with receipt ${receipt.decision_id.slice(0, 8)}`);
      toast.push("success", `Removed ${member.name} from ${selectedEntry.canonical_name}`);
    } catch (error) {
      setEntityProfileMessageIsError(true);
      setEntityProfileMessage(error instanceof Error && error.message ? error.message : "Membership decision failed");
      toast.push("error", error instanceof Error && error.message ? error.message : "Membership decision failed");
      return;
    }
    campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {});
    await loadCanonicalEntry(selectedEntry.entry_id);
  }, [campaignClient, selectedEntry, loadCanonicalEntry]);

  const assignFactionRole = useCallback(async (member: LibraryMember, roleName: string | null, isLeadership: boolean) => {
    if (!selectedEntry) return;
    // Core refuses a leadership seat held by another member by name; that
    // refusal surfaces here as an error instead of silently transferring.
    try {
      await campaignClient.assignFactionRole(selectedEntry.entry_id, member.member_id, roleName, isLeadership);
    } catch (error) {
      setEntityProfileMessageIsError(true);
      setEntityProfileMessage(error instanceof Error && error.message ? error.message : "Role decision failed");
      toast.push("error", error instanceof Error && error.message ? error.message : "Role decision failed");
      return;
    }
    await loadCanonicalEntry(selectedEntry.entry_id);
    campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {});
    setEntityProfileMessageIsError(false);
    setEntityProfileMessage(roleName
      ? `Seated ${member.name} as ${roleName}${isLeadership ? " ★" : ""} in ${selectedEntry.canonical_name}`
      : `Cleared ${member.name}'s role in ${selectedEntry.canonical_name}`);
    toast.push("success", roleName
      ? `Seated ${member.name} as ${roleName}${isLeadership ? " ★" : ""} in ${selectedEntry.canonical_name}`
      : `Cleared ${member.name}'s role in ${selectedEntry.canonical_name}`);
  }, [campaignClient, selectedEntry, loadCanonicalEntry]);

  const saveEntityProfile = useCallback(async (): Promise<boolean> => {
    if (!selectedEntry || !entityProfileDraft || !entityProfileDraft.canonical_name.trim()) return false;
    try {
      const receipt = await campaignClient.updateEntityProfile(
        selectedEntry.entry_id,
        { ...entityProfileDraft,
          canonical_name: entityProfileDraft.canonical_name.trim(),
          status: entityProfileDraft.status?.trim() || null,
          location_type: entityProfileDraft.location_type?.trim() || null,
          parent_location: entityProfileDraft.parent_location?.trim() || null,
          base_location: entityProfileDraft.base_location?.trim() || null,
          race: entityProfileDraft.race?.trim() || null,
          sex: entityProfileDraft.sex?.trim() || null,
          player: entityProfileDraft.player?.trim() || null,
          aliases: entityProfileDraft.aliases.map((value) => value.trim()).filter(Boolean),
          summary: entityProfileDraft.summary,
          version: entityProfileDraft.version,
          idempotency_key: `entity-profile:${selectedEntry.entry_id}:${entityProfileDraft.version}:${crypto.randomUUID()}` });
      await loadCanonicalEntry(selectedEntry.entry_id);
      campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {});
      setEntityProfileEditing(false);
      setEntityProfileBaseline(null);
      setEntityProfileMessageIsError(false);
      setEntityProfileMessage(`Saved with receipt ${receipt.receipt_id}` + (receipt.alias_sync ? ` · aliases for ${receipt.alias_sync.entity_name}:` +
        [receipt.alias_sync.applied.length ? ` added ${receipt.alias_sync.applied.join(", ")}` : "",
         receipt.alias_sync.removed.length ? ` removed ${receipt.alias_sync.removed.join(", ")}` : "",
         receipt.alias_sync.skipped_conflicting.length ? ` skipped (owned by another identity): ${receipt.alias_sync.skipped_conflicting.join(", ")}` : ""].filter(Boolean).join(";") : ""));
      toast.push("success", "Identity profile saved");
      return true;
    } catch (error) {
      setEntityProfileMessageIsError(true);
      setEntityProfileMessage(error instanceof Error ? error.message : "Profile could not be saved");
      toast.push("error", error instanceof Error ? error.message : "Profile could not be saved");
      return false;
    }
  }, [campaignClient, entityProfileDraft, selectedEntry, loadCanonicalEntry]);

    useEffect(() => {
    if (activePage === "identity" && identityGaps === null && !identityBusy) {
      void loadIdentityGaps();
    }
  }, [activePage, identityGaps === null, identityBusy, loadIdentityGaps]);
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
  // TKT-0121: the DM-curated Dossier for the selected entry (receipted
  // promote/demote decisions; the page renders promoted current claims).
  const [dossierClaimIds, setDossierClaimIds] = useState<Set<string>>(() => new Set());
  // Assertions that moved away from this entity — shown as Dossier tiles
  // with shortcuts to the new owners.
  const [movedAssertions, setMovedAssertions] = useState<MovedAssertion[]>([]);
  // Location breadcrumb: the full ancestor chain, oldest root first.
  const [locationTrail, setLocationTrail] = useState<string[]>([]);
  const locationTrailMemo = useRef(new Map<string, string[]>());
  // TKT-0129: template vocabularies for the profile editors' selects.
  const [templateVocabularies, setTemplateVocabularies] = useState<Partial<Record<"location_type" | "status" | "race" | "sex", string[]>>>({});
  useEffect(() => {
    const loadVocabulary = async (vocabulary: "location_type" | "status" | "race" | "sex") => {
      try {
        const items = await campaignClient.getTemplateVocabulary(vocabulary);
        setTemplateVocabularies((current) => ({ ...current, [vocabulary]: items.filter((item) => !item.retired).map((item) => item.value) }));
      } catch { /* selects fall back to Not set + current */ }
    };
    for (const vocabulary of ["location_type", "status", "race", "sex"] as const) void loadVocabulary(vocabulary);
  }, [campaignClient]);
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
  const [claimEditBaseline, setClaimEditBaseline] = useState<string | null>(null);
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

  // ADR-0016: one guard for every edit surface. Clean surfaces close
  // silently on switch; any dirty surface blocks the switch until resolved.
  const profileDirty = entityProfileEditing && entityProfileDraft && entityProfileBaseline !== null
    && JSON.stringify(entityProfileDraft) !== entityProfileBaseline;
  const characterDirty = pcEditing && pcDraft && pcProfile
    && JSON.stringify(pcDraft) !== JSON.stringify(pcProfile);
  const claimEditDirty = claimEdit !== null && claimEditBaseline !== null
    && (JSON.stringify({ drafts: claimEditDrafts, reason: claimEditReason }) !== claimEditBaseline);
  const leaveEditorGuard = useCallback((label: string, proceed: () => void) => {
    if (profileDirty || characterDirty || claimEditDirty || composerDirty) {
      setBlockedSwitch({ label, proceed });
      return;
    }
    setEntityProfileEditing(false);
    setEntityProfileDraft(null);
    setEntityProfileBaseline(null);
    setDescriptionComposerOpen(false);
    setRevisionDraft(null); setClaimSelection(null);
    setComposerDirty(false);
    setClaimEdit(null); setClaimEditDrafts([]); setClaimEditBaseline(null); setClaimEditMessage("");
    setPCEditing(false); setPCPreview(false); setPCSaveKey("");
    setBlockedSwitch(null);
    proceed();
  }, [profileDirty, characterDirty, claimEditDirty, composerDirty]);
  const openSourceDocument = useCallback((document: SourceDocument) => {
    leaveEditorGuard(`the ${document.title ?? document.path} source`, () => {
      setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null);
      setSelectedDocumentId(document.document_id);
      void loadDocumentContent(document.document_id, document.path);
    });
  }, [leaveEditorGuard]);

  // TKT-0127: drafting is fire-and-forget. The job runs on a Windmill worker;
  // the result parks in the Drafts tray until claimed or discarded.
  const queueProseDraft = useCallback(async (command: ProseDraftCommand, entryId: string, entryName: string) => {
    const job = await jobPlatform.startProseDraft(command);
    setDraftQueue((queue) => [...queue, {
      id: crypto.randomUUID(), jobId: job.jobId, entryId, entryName,
      startedAt: performance.now(), state: "running",
    }]);
    setDraftPenOpen(true);
    toast.push("info", `Draft queued for ${entryName} — it lands in the Drafts tray when the model finishes`);
  }, [jobPlatform]);

  useEffect(() => {
    const running = draftQueue.filter((item) => item.state === "running");
    if (running.length === 0) return;
    let cancelled = false;
    const poll = async () => {
      for (const item of running) {
        try {
          const next = await jobPlatform.inspect(item.jobId);
          if (cancelled) return;
          if (next.state === "succeeded" && next.result && typeof next.result === "object") {
            const result = next.result as ProseDraftResult;
            const elapsed = ((performance.now() - item.startedAt) / 1000).toFixed(1);
            setDraftQueue((queue) => queue.map((entry) => entry.id === item.id
              ? { ...entry, state: "ready" as const, result, elapsedSeconds: elapsed } : entry));
            toast.push("success", `Draft ready for ${item.entryName} in ${elapsed}s — review it in the Drafts tray`);
          } else if (next.state === "failed") {
            const elapsed = ((performance.now() - item.startedAt) / 1000).toFixed(1);
            const error = next.error ?? "The draft job failed";
            setDraftQueue((queue) => queue.map((entry) => entry.id === item.id
              ? { ...entry, state: "failed" as const, error, elapsedSeconds: elapsed } : entry));
            toast.push("error", `Draft failed for ${item.entryName} after ${elapsed}s — ${error}`);
          }
        } catch {
          // Transient inspect failures keep polling until the job resolves.
        }
      }
      if (!cancelled) draftPollTimer.current = window.setTimeout(poll, 2500);
    };
    draftPollTimer.current = window.setTimeout(poll, 800);
    return () => {
      cancelled = true;
      if (draftPollTimer.current !== null) window.clearTimeout(draftPollTimer.current);
    };
  }, [draftQueue, jobPlatform]);

  const claimDraft = (item: DraftQueueItem) => {
    if (!item.result) return;
    leaveEditorGuard(item.entryName, () => {
      setDraftPenOpen(false);
      setDraftQueue((queue) => queue.filter((entry) => entry.id !== item.id));
      if (item.entryId.startsWith("lore:")) {
        // Lore drafts land back in the Lore creation workspace's prose field.
        setActivePage("lore");
        setRevisionDraft(item.result!.draft_text.replace(/\s*\[\d+\]/g, ""));
        toast.push("info", `Draft ready for ${item.entryName} — paste it into the Lore description field`);
        return;
      }
      setActivePage("documents");
      setSelectedEntryId(item.entryId);
      void loadCanonicalEntry(item.entryId).then(() => {
        // Seed the guarded composer with the finished prose; the selection
        // mirrors the citations the draft actually used.
        setRevisionDraft(item.result!.draft_text.replace(/\s*\[\d+\]/g, ""));
        setClaimSelection({
          claimIds: item.result!.cited_keys.filter((key) => key.startsWith("claim:")).map((key) => key.slice("claim:".length)),
          relationKeys: item.result!.cited_keys.filter((key) => key.startsWith("relation:")),
        });
        setDescriptionComposerOpen(true);
        toast.push("info", `Draft loaded for ${item.entryName} — edit, then file or cancel`);
      });
    });
  };

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
      // The session reviewer lives on the shelved phase-1 workspace (its
      // re-home is queued); the settings flag is required to reach it.
      setActivePage("migration-legacy");
      await loadReviewWorkspace(nextFilters, false);
      await chooseCandidate(receipt.candidate_id);
    } catch (error) {
      setSessionCaptureError(error instanceof Error ? error.message : "Session note could not be captured");
      toast.push("error", error instanceof Error ? error.message : "Session note could not be captured");
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
      const source = selectEntrySource(entry, entry.sources, libraryEntries.map((item) => item.canonical_name));
      let profile: CharacterDocument | null = null;
      if (source) {
        const document = await campaignClient.getSourceDocument(source.document_id);
        profile = characterDocument(document.content);
        if (profile) {
          // Document-backed characters still carry canon dimensions on their
          // entity profile (life status); fetch it alongside the sheet.
          const stored = await campaignClient.getEntityProfile(entry.entry_id).catch(() => null);
          setEntityProfile(stored);
        }
      }
      setEncounterDossier({ entry, profile, path: source?.path ?? "" });
    } catch (error) {
      setEncounterDossierError(error instanceof Error ? error.message : "NPC dossier could not be loaded");
      toast.push("error", error instanceof Error ? error.message : "NPC dossier could not be loaded");
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
      setDocContent("Unable to load source content.");
    } finally {
      setDocLoading(false);
    }
  }

  async function prefillSheetBackground(entry: LibraryEntry) {
  // TKT-0147: the sheet's Background is evidence for a Description — seed
  // the composer with it so candidate promotion (:: flow) can promote it.
  if (revisionDraft !== null) return; // already seeded (draft or revision)
  const sheet = entry.sources.find((source) => /^(npcs|pcs)\//.test(source.path));
  if (!sheet) return;
  try {
    const doc = await campaignClient.getSourceDocument(sheet.document_id);
    const match = doc.content.match(new RegExp("##[ ]+" + "(?:background([ ]*/[ ]*history)?|original biography source)" + "[ ]*\n" + "([\s\S]*?)" + "(?=\n##[ ]|$)", "i"));


    const background = match?.[1]?.trim();
    if (background) setRevisionDraft(background);
  } catch { /* seeding is best-effort; a blank composer remains fine */ }
}

async function loadCanonicalEntry(entryId: string, freshSourceDocuments?: SourceDocument[]) {
    // Same-entry reloads (roster and role operations) stay on screen; only a
    // genuine entry switch swaps the panel for the loading state — and closes
    // transient edit surfaces (ADR-0016: the guard forces resolution for
    // dirty ones before the switch can even reach here).
    const switching = entryId !== selectedEntryId;
    if (switching) {
      setDocLoading(true);
      setDescriptionComposerOpen(false);
      setRevisionDraft(null); setClaimSelection(null);
      setComposerDirty(false);
    }
    setMemberSearch("");
    setMemberResults([]);
    try {
      const entry = await campaignClient.getLibraryEntry(entryId);
      setSelectedEntry(entry);
      setSelectedPlan(null);
      // Every entry page is editable (ADR-0016): the entity profile loads
      // for all kinds, page-backed included — the page's document stays
      // immutable evidence; the entity record is what edits.
      const profile = await campaignClient.getEntityProfile(entry.entry_id).catch(() => null);
      setEntityProfile(profile);
      // Roster operations reload the open editor's entry; the in-progress
      // draft survives those reloads. Switching entries goes through
      // leaveEditorGuard, which closes the editor first.
      if (!entityProfileEditing) setEntityProfileDraft(profile);
      // The authored description page is a page candidate even when no claim
      // links it to the entry yet — without this, a just-filed page loses
      // the page match to an imported doc that shares the name. The fresh
      // list is passed in by post-save reloads (the closure's state is stale
      // until the next render).
      const docs = freshSourceDocuments ?? sourceDocuments;
      const authoredSlug = entry.canonical_name.toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
      const authoredPath = `entities/${authoredSlug}.md`;
      const authoredPage = docs.find((doc) => doc.path === authoredPath);
      const candidates = authoredPage && !entry.sources.some((source) => source.path === authoredPath)
        ? [{ document_id: authoredPage.document_id, path: authoredPath }, ...entry.sources]
        : entry.sources;
      const source = selectEntrySource(entry, candidates, libraryEntries.map((item) => item.canonical_name));
      setDocCanonicalClaims(entry.claims);
      setDocClaimHistory(entry.claim_history ?? []);
      setClaimEdit(null); setClaimEditMessage("");
      campaignClient.getEntityDossier(entry.entry_id)
        .then((view) => setDossierClaimIds(new Set(view.promoted_claim_ids)))
        .catch(() => setDossierClaimIds(new Set()));
      campaignClient.getMovedAssertions(entry.entry_id)
        .then(setMovedAssertions)
        .catch(() => setMovedAssertions([]));
      // Walk the parent-location chain upward for the breadcrumb trail
      // (Myrin › Illisan › Fleurite › Fleurite Castle). Memoized per entry.
      if (entry.entity_kind === "location") {
        const cached = locationTrailMemo.current.get(entry.entry_id);
        if (cached) setLocationTrail(cached);
        else void (async () => {
          const chain: string[] = [entry.canonical_name];
          let parent = profile?.parent_location ?? null;
          const seen = new Set([entry.canonical_name.toLocaleLowerCase()]);
          for (let depth = 0; parent && depth < 6; depth += 1) {
            const cleanParent = cleanMarkdown(parent);
            chain.unshift(cleanParent);
            if (seen.has(cleanParent.toLocaleLowerCase())) break;
            seen.add(cleanParent.toLocaleLowerCase());
            const parentEntry = libraryEntries.find(
              (item) => item.canonical_name.toLocaleLowerCase() === cleanParent.toLocaleLowerCase());
            if (!parentEntry) break;
            try {
              const parentProfile = await campaignClient.getEntityProfile(parentEntry.entry_id).catch(() => null);
              parent = parentProfile?.parent_location ?? null;
            } catch { break; }
          }
          locationTrailMemo.current.set(entry.entry_id, chain);
          setLocationTrail(chain);
        })();
      } else setLocationTrail([]);
      if (source) {
        const result = await campaignClient.getSourceDocument(source.document_id);
        setDocMetadata(result);
        setSelectedDocumentId(source.document_id);
        setDocContent(result.content);
        setDocContentPath(result.path);
        const parsed = characterDocument(result.content);
        if (parsed?.kind === "pc" || parsed?.kind === "npc") {
          const stored = await campaignClient.getPCProfile(source.document_id);
          const initial: PCProfile = stored ?? { document_id: source.document_id, source_revision_id: result.source_revision_id, version: 0, canonical_name: entry.canonical_name, player: parsed.player, race: parsed.race, sex: parsed.sex, status: parsed.status ?? "active", aliases: entry.aliases, background: parsed.background ?? "" };
          setPCProfile(initial); setPCDraft(initial);
        } else { setPCProfile(null); setPCDraft(null); }
      } else {
        setDocMetadata(null);
        setSelectedDocumentId(null);
        setDocContent(synthesizedEntryDocument(entry, profile));
        setDocContentPath("");
        setPCProfile(null); setPCDraft(null);
      }
      setPCEditing(false); setPCPreview(false); setPCSaveKey(""); setPCMessage("");
      return entry;
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
    if (!pcDraft || !pcDraft.canonical_name.trim() || (characterKind === "pc" && !pcDraft.player?.trim())) return false;
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
      toast.push("success", "PC profile saved");
      return true;
    } catch (error) { setPCMessage(error instanceof Error ? error.message : "PC profile could not be saved"); toast.push("error", error instanceof Error ? error.message : "PC profile could not be saved"); return false; }
  }

  const toggleDossier = async (claimId: string, action: "promote" | "demote") => {
    if (!selectedEntry) return;
    try {
      await (action === "promote"
        ? campaignClient.promoteToDossier(selectedEntry.entry_id, claimId)
        : campaignClient.demoteFromDossier(selectedEntry.entry_id, claimId));
      setDossierClaimIds((current) => {
        const next = new Set(current);
        action === "promote" ? next.add(claimId) : next.delete(claimId);
        return next;
      });
      toast.push("success", action === "promote"
        ? "Promoted to Dossier — the fact now shows as a card on the page"
        : "Demoted from Dossier — the fact is back under the hood only");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "The dossier decision could not be filed";
      toast.push("error", detail);
    }
  };

  const openEntryByName = (name: string) => {
    const match = libraryEntries.find((entry) => entry.canonical_name.toLocaleLowerCase() === name.toLocaleLowerCase());
    if (!match) return;
    leaveEditorGuard(match.canonical_name, () => {
      setSelectedEntryId(match.entry_id);
      void loadCanonicalEntry(match.entry_id);
    });
  };

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
      // Baseline for the edit guard (ADR-0016): opening an editor is not a
      // change; switching pages with untouched drafts closes silently.
      setClaimEditBaseline(JSON.stringify({ drafts: [draft], reason: "" }));
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
      toast.push("success", "Claim corrected");
    } catch (error) { setClaimEditMessage(error instanceof Error ? error.message : "Claim correction failed"); toast.push("error", error instanceof Error ? error.message : "Claim correction failed"); }
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
          <button className={activePage === "identity" ? "active" : ""} onClick={() => setActivePage("identity")} type="button">Identity</button>
          <button className={activePage === "roles" ? "active" : ""} onClick={() => setActivePage("roles")} type="button">Roles</button>
          <button className={activePage === "lore" ? "active" : ""} onClick={() => setActivePage("lore")} type="button">Lore</button>
          {!appSettings.hiddenNavPages.includes("Migration") && <button className={activePage === "migration" ? "active" : ""} onClick={() => setActivePage("migration")} type="button">Migration</button>}
          {appSettings.showLegacyMigration && <button className={activePage === "migration-legacy" ? "active" : ""} onClick={() => setActivePage("migration-legacy")} type="button">Migration phase 1</button>}
          <button className={activePage === "tools" ? "active" : ""} onClick={() => setActivePage("tools")} type="button">Tools</button>
          <button className={activePage === "log" ? "active" : ""} onClick={() => setActivePage("log")} type="button">Log</button>
          {!appSettings.hiddenNavPages.includes("Conventions") && <button className={activePage === "conventions" ? "active" : ""} onClick={() => setActivePage("conventions")} type="button">Conventions</button>}
          <button className={activePage === "help" ? "active" : ""} onClick={() => setActivePage("help")} type="button">Help</button>
        </nav>
        <div className="topbar-right">
          <CampaignClockChip campaignClient={campaignClient} onDateChanged={() => { /* capture default refetches per open */ }} />
          <button aria-label="Ask the archive" className="topbar-search" onClick={() => setSearchTrayOpen((open) => !open)} title="Ask the archive" type="button"><SearchIcon /></button>
          <button aria-label="Open settings" className={activePage === "settings" ? "identity active" : "identity"} onClick={() => setActivePage("settings")} title="DM settings" type="button"><span>DM</span><b>Private archive</b></button>
        </div>
      </header>
        <div className={"tray-dock " + appSettings.trayLayout.anchor}>
              <div className="tray-panels">
            {searchTrayOpen && <aside aria-label="Ask the archive" className="table-notes-panel ask-tray">
              <header><div><span>Starfall campaign records</span><h2>Ask the archive</h2></div><div className="table-notes-header-actions"><button aria-label="Close Ask the archive" onClick={() => setSearchTrayOpen(false)} type="button">×</button></div></header>
              <form className="ask-box" onSubmit={ask}>
                <label htmlFor="campaign-question">Campaign question</label>
                <div className="ask-row">
                  <SearchIcon />
                  <textarea id="campaign-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What do the records establish about…" rows={2} />
                  <button disabled={!question.trim() || queryState === "loading"} type="submit">{queryState === "loading" ? "Searching…" : "Search records"}</button>
                </div>
                <div className="ask-meta"><span>Visibility</span><b>Dungeon Master</b><span className="dot" />No creative inference</div>
              </form>
              {queryState === "error" && <div className="notice error"><b>Campaign Core is unavailable.</b><span>{queryError}</span></div>}
              {!result && queryState !== "error" && <div className="empty-state"><div className="empty-glyph"><SearchIcon /></div><div><b>Your evidence will appear here</b><span>Ask a question to inspect canonical records and cited context.</span></div></div>}
              {result && modeCopy && <article className={"answer-card mode-" + result.answer_mode}><header><div><p>{modeCopy.eyebrow}</p><h2>{modeCopy.title}</h2></div><span>{result.evidence.length} evidence item{result.evidence.length === 1 ? "" : "s"}</span></header>{result.evidence.length === 0 ? <p className="no-evidence">No visible authoritative record supports an answer. Nothing was invented.</p> : <div className="evidence-list">{result.evidence.map((item) => <div className="evidence" key={item.record_id}><span className={"role role-" + item.role}>{item.role}</span><p>{item.assertion}</p><dl><div><dt>Authority</dt><dd>{display(item.authority)}</dd></div><div><dt>State</dt><dd>{item.state}</dd></div></dl><cite>{item.citation}</cite></div>)}</div>}<footer>{result.reasons.map(display).join(" · ")}</footer></article>}
            </aside>}
            {draftPenOpen && <aside aria-label="Drafts tray" className="table-notes-panel drafts-pen">
              <header><div><span>Background AI drafts</span><h2>Drafts</h2></div><div className="table-notes-header-actions"><button aria-label="Close Drafts tray" onClick={() => setDraftPenOpen(false)} type="button">×</button></div></header>
              <p className="roles-explainer">Drafts run in the background and park here. Claim one to load it into that entry's composer with its citations mirrored into the selection — edit, then file or cancel; discard drops it. Nothing blocks while a draft runs.</p>
              <div className="table-notes-timeline">
                {draftQueue.length === 0 && <p className="empty-section">No drafts queued.</p>}
                {draftQueue.map((item) => <article key={item.id}><time>{item.state === "running"
                  ? `${((performance.now() - item.startedAt) / 1000).toFixed(0)}s`
                  : `${item.elapsedSeconds ?? ""}s`}</time><div>
                  <span>{item.entryName}</span>
                  {item.state === "running" && <p className="ai-activation-note">Drafting…</p>}
                  {item.state === "failed" && <p className="ai-activation-note" role="alert">{item.error}</p>}
                  {item.state === "ready" && item.result && typeof item.result.draft_text === "string" && <p>{item.result.draft_text.replace(/\s*\[\d+\]/g, "").slice(0, 160)}…</p>}
                  {item.state === "ready" && item.result && <p className="ai-activation-note">machine-drafted · {item.result.model_slug} · {item.elapsedSeconds}s · {item.result.prompt_tokens + item.result.completion_tokens} tokens · cited {item.result.cited_keys.length} record{item.result.cited_keys.length === 1 ? "" : "s"}</p>}
                  <div className="table-note-actions">
                    {item.state === "ready" && <button onClick={() => claimDraft(item)} type="button">Return to draft</button>}
                    <button aria-label={`Discard draft for ${item.entryName}`} className="text-button" onClick={() => setDraftQueue((queue) => queue.filter((entry) => entry.id !== item.id))} type="button">Discard</button>
                  </div>
                </div></article>)}
              </div>
            </aside>}
            {tableNotesOpen && <aside aria-label="Session table notes" className="table-notes-panel">
              <header><div><span>{sessionRun ? `Open session · ${sessionRun.session_date}` : "Session timeline"}</span><h2>Table notes</h2></div><div className="table-notes-header-actions"><button onClick={() => openTableNoteComposer(generalSessionNoteContext())} type="button">+ General note</button><button aria-label="Close table notes" onClick={() => { setTableNotesOpen(false); setTableNoteContext(null); setEditingTableNoteId(null); setTableNoteDraft(""); }} type="button">×</button></div></header>
              {tableNotesSyncError && <div className="notice error" role="alert">Saved in this browser. Durable sync failed: {tableNotesSyncError}</div>}
              {tableNoteContext && <section className="table-note-composer"><span>{tableNoteContext.contextKind === "general" ? "Outside an encounter" : tableNoteContext.encounterName}</span><h3>{tableNoteContext.sectionTitle}</h3><textarea aria-label="Table note" onChange={(event) => setTableNoteDraft(event.target.value)} onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); saveTableNote(); } }} placeholder="What happened at the table?" ref={tableNoteInputRef} rows={4} value={tableNoteDraft} /><div><button className="text-button" onClick={() => { setTableNoteContext(null); setEditingTableNoteId(null); setTableNoteDraft(""); }} type="button">Cancel</button><button disabled={!tableNoteDraft.trim()} onClick={saveTableNote} type="button">{editingTableNoteId ? "Save note" : "Add to timeline"}</button></div><small>Ctrl+Enter saves. Context is retained without changing the claim text.</small></section>}
              {encounterProgress.filter((item) => item.status === "in_progress").length > 0 && <section className="unfinished-encounters" aria-label="Unfinished encounters"><span>Unfinished encounters</span>{encounterProgress.filter((item) => item.status === "in_progress").map((item) => <article key={item.source_document_id}><div><b>{item.encounter_name}</b>{item.resume_section_title && <small>Resume at {item.resume_section_title}</small>}</div><div><button onClick={() => void resumeEncounter(item)} type="button">Resume</button><button onClick={() => void setEncounterLifecycle(item.source_document_id, item.source_path, item.encounter_name, "completed")} type="button">Complete</button><button className="text-button" onClick={() => void setEncounterLifecycle(item.source_document_id, item.source_path, item.encounter_name, "abandoned")} type="button">Abandon</button></div></article>)}</section>}
              <div className="table-notes-timeline">{chronologicalEncounterNotes(encounterNotes).length === 0 ? <p className="empty-section">No table notes yet. Add a general note or use a note icon in an encounter.</p> : chronologicalEncounterNotes(encounterNotes).map((note) => <article key={note.noteId}><time dateTime={note.capturedAt}>{new Date(note.capturedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time><div><span>{note.contextKind === "general" ? "General session note" : `${note.encounterName} · ${note.sectionTitle}`}</span><p>{note.text}</p>{note.contextKind !== "general" && note.sourceDocumentId && <button className="resume-checkpoint" onClick={() => void setEncounterLifecycle(note.sourceDocumentId, note.sourcePath, note.encounterName, "in_progress", { key: note.sectionKey, title: note.sectionTitle })} type="button">Resume here next session</button>}</div><div className="table-note-actions"><button aria-label={`Edit note from ${note.sectionTitle}`} onClick={() => editTableNote(note)} title="Edit note" type="button"><RecordIcon kind="edit" /></button><button aria-label={`Remove note from ${note.sectionTitle}`} onClick={() => void removeTableNote(note)} title="Remove note" type="button">×</button></div></article>)}</div>
              {encounterNotes.length > 0 && <footer><label>Add chronologically to<select aria-label="Session note destination" onChange={(event) => setTableNoteDestination(event.target.value)} value={tableNoteDestination}><option value="new">A new session note</option>{editableSessionDocuments.map((document) => <option key={document.document_id} value={document.document_id}>{document.session_date ? `${document.session_date} — ` : ""}{document.title ?? entryLabel(document.path)}</option>)}</select></label><button onClick={() => void assembleTableNotesIntoSession()} type="button">Continue in session note</button></footer>}
            </aside>}
              </div>
              <div className="tray-launchers">
                {appSettings.trayLayout.search && !searchTrayOpen && <button className="table-notes-launcher" onClick={() => setSearchTrayOpen(true)} type="button"><SearchIcon /><span>Ask</span></button>}
                {appSettings.trayLayout.drafts && !draftPenOpen && draftQueue.length > 0 && (() => {
                  const ready = draftQueue.filter((item) => item.state === "ready").length;
                  const running = draftQueue.filter((item) => item.state === "running").length;
                  return <button className={"table-notes-launcher drafts-launcher" + (ready > 0 ? " has-ready" : "")} onClick={() => setDraftPenOpen(true)} type="button"><WandIcon /><span>Drafts</span>{running > 0 && <b>{running} running</b>}{ready > 0 && <b>{ready} ready</b>}</button>;
                })()}
                {appSettings.trayLayout.session && !tableNotesOpen && (sessionRun || encounterNotes.length > 0) && <button className="table-notes-launcher" onClick={() => setTableNotesOpen(true)} type="button"><RecordIcon kind="note" /><span>Open session</span>{encounterNotes.length > 0 && <b>{encounterNotes.length}</b>}</button>}
              </div>
            </div>

      {activePage === "documents" && (
      <main className="page-documents">
        <div className={`doc-layout ${libraryPanelCollapsed ? "library-collapsed" : ""}`}>
          <button aria-label={libraryPanelCollapsed ? "Expand Library" : "Collapse Library"} className="library-panel-handle" onClick={() => setLibraryPanelCollapsed((value) => !value)} title={libraryPanelCollapsed ? "Expand Library" : "Collapse Library"} type="button">{libraryPanelCollapsed ? "›" : "‹"}</button>
          <aside className={`doc-tree-panel ${libraryPanelCollapsed ? "collapsed" : ""}`} aria-label="Entry library">
            <div className="tree-header library-tree-header"><div><span>{libraryMode === "entries" ? "Campaign library" : "Source files"}</span></div><div className="library-header-actions"><div className="new-session-menu"><button aria-expanded={newSessionMenuOpen} aria-label="New session" className="new-session-note" onClick={() => { if (sessionRunRef.current) setTableNotesOpen(true); else setNewSessionMenuOpen((open) => !open); }} title={sessionRun ? "Open session" : "New session"} type="button">+</button>{newSessionMenuOpen && !sessionRun && <div role="menu"><button onClick={() => void beginLiveSession()} role="menuitem" type="button"><b>Start live session</b><span>Capture events as they happen</span></button><button onClick={() => { setNewSessionMenuOpen(false); void openSessionCapture(); }} role="menuitem" type="button"><b>Write session log directly</b><span>Enter a finished account for review</span></button><button onClick={() => { setNewSessionMenuOpen(false); setActivePage("lore"); }} role="menuitem" type="button"><b>Queue for Lore</b><span>A name that needs a campaign entry</span></button></div>}</div><label className="source-mode-toggle"><span>Source</span><button aria-checked={libraryMode === "sources"} aria-label="Source view" onClick={() => setLibraryMode((mode) => mode === "sources" ? "entries" : "sources")} role="switch" type="button"><i /></button></label></div></div>
            <div className="tree-body">
              {sourceDocuments.length === 0 && reviewLoading && <p className="queue-empty">Loading…</p>}
              {libraryMode === "entries" && libraryEntries.length > 0 && Array.from(new Set(libraryEntries.map((entry) => entry.entity_kind))).map((kind) => {
                const loreDocuments = kind === "worldbuilding"
                  ? sourceBackedLibraryDocuments.filter((document) => pathEntryType(document.path) === "Worldbuilding")
                  : [];
                const entryRows = libraryEntries.filter((entry) => entry.entity_kind === kind).map((entry) => (
                  { key: `entry-${entry.entry_id}`, label: entry.canonical_name, selected: selectedEntryId === entry.entry_id, node: <button className={`tree-doc canonical-entry-link ${selectedEntryId === entry.entry_id ? "selected" : ""}`} key={entry.entry_id} onClick={() => leaveEditorGuard(entry.canonical_name, () => { setSelectedEntryId(entry.entry_id); void loadCanonicalEntry(entry.entry_id); })} type="button"><span className="tree-doc-name">{entry.canonical_name}</span>{unpagedEntryIds.has(entry.entry_id) && <span aria-hidden="true" className="tree-doc-flag" title="No authored page yet — this entry is displayed from its records. Write a description to give it an authored page."><RecordIcon kind="unpaged" /></span>}</button> }));
                const documentRows = loreDocuments.map((document) => (
                  { key: `doc-${document.document_id}`, label: sourceDocumentLabel(document), selected: selectedDocumentId === document.document_id, node: <div className="source-entry-row" key={document.document_id}><button className={`tree-doc canonical-entry-link ${selectedDocumentId === document.document_id ? "selected" : ""}`} onClick={() => openSourceDocument(document)} type="button"><span className="tree-doc-name">{sourceDocumentLabel(document)}</span></button></div> }));
                return <details className="canonical-entry-group" key={kind}><summary>{entryKindLabel(kind)}</summary><div>{[...entryRows, ...documentRows].sort((left, right) => left.label.toLocaleLowerCase().localeCompare(right.label.toLocaleLowerCase())).map((row) => row.node)}</div></details>;
              })}
              {libraryMode === "entries" && libraryPlans.length > 0 && <details className="canonical-entry-group"><summary>Plans</summary><div>{libraryPlans.map((plan) => <button className={`tree-doc canonical-entry-link ${selectedPlan?.id === plan.id ? "selected" : ""}`} key={plan.id} onClick={() => leaveEditorGuard(`the ${plan.canonical_name} plan`, () => { setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(plan); setDocContent(""); })} type="button"><span className="tree-doc-name">{plan.canonical_name}</span></button>)}</div></details>}
              {libraryMode === "entries" && sourceBackedLibraryDocuments.length > 0 && Array.from(new Set(sourceBackedLibraryDocuments.map((document) => pathEntryType(document.path)))).filter((family) => family !== "Worldbuilding").map((family) => <SourceBackedFamily documents={sourceBackedLibraryDocuments.filter((document) => pathEntryType(document.path) === family)} family={family} key={family} onEditSession={(document) => void editSourceSessionDocument(document)} onSelect={openSourceDocument} selectedDocumentId={selectedDocumentId} />)}
              {(libraryMode === "sources" || libraryEntries.length === 0) && <>{libraryMode === "sources" && <p className="tree-explainer">Immutable imported evidence, organized by source path.</p>}{Object.entries(buildDocTree(sourceDocuments)).map(([dir, children]) => (
                <TreeDir key={dir} name={dir} depth={0} children_={children} expanded={expandedDirs} setExpanded={setExpandedDirs} selectedDocumentId={selectedDocumentId} sourceMode={libraryMode === "sources"} onSelect={(docId) => { const doc = sourceDocuments.find((d) => d.document_id === docId); if (doc) { leaveEditorGuard(`the ${doc.title ?? doc.path} document`, () => { setSelectedEntryId(null); setSelectedEntry(null); setSelectedPlan(null); setSelectedDocumentId(docId); void loadDocumentContent(docId, doc.path); }); } }} />
              ))}</>}
            </div>
          </aside>
          <section className={`doc-content-panel ${encounterDossier ? (encounterDossierCollapsed ? "dossier-collapsed" : "dossier-open") : ""}`} aria-label="Source content">
            {blockedSwitch && (() => {
              const dirty = [
                profileDirty ? "identity profile" : null,
                characterDirty ? "character changes" : null,
                claimEditDirty ? "claim correction" : null,
                composerDirty ? "description draft" : null,
              ].filter((item): item is string => item !== null);
              const proceedAfterDiscard = () => {
                const proceed = blockedSwitch.proceed;
                setBlockedSwitch(null);
                setEntityProfileEditing(false); setEntityProfileDraft(entityProfile); setEntityProfileBaseline(null);
                setDescriptionComposerOpen(false); setRevisionDraft(null); setClaimSelection(null); setComposerDirty(false);
                setClaimEdit(null); setClaimEditDrafts([]); setClaimEditBaseline(null); setClaimEditMessage("");
                setPCEditing(false); setPCPreview(false); setPCSaveKey("");
                proceed();
              };
              return <div className="notice error unresolved-edit" role="alert"><b>Unsaved changes.</b><p>Resolve the open {dirty.join(", ")} before opening {blockedSwitch.label}.</p><div className="step-actions">
                <button className="text-button" type="button" onClick={proceedAfterDiscard}>Discard changes</button>
                {profileDirty && <button className="decision-button" type="button" onClick={() => { void (async () => { if (await saveEntityProfile() && !characterDirty && !claimEditDirty && !composerDirty) { const proceed = blockedSwitch.proceed; setBlockedSwitch(null); proceed(); } /* else: the notice recomposes around whatever is still dirty */ })(); }}>Save profile</button>}
                {characterDirty && <button className="decision-button" type="button" onClick={() => { void (async () => { if (await savePCProfile() && !profileDirty && !claimEditDirty && !composerDirty) { const proceed = blockedSwitch.proceed; setBlockedSwitch(null); proceed(); } })(); }}>Save changes</button>}
              </div></div>;
            })()}
            {sessionCaptureOpen && closeoutNotes.length > 0 && <section aria-label="Session closeout context" className="session-closeout-context"><header><div><span>Session context</span><b>{closeoutNotes.length} timeline note{closeoutNotes.length === 1 ? "" : "s"}</b></div><button className="text-button" onClick={() => setTableNotesOpen(true)} type="button">Review timeline</button></header>{closeoutEncounters.length > 0 ? <div>{closeoutEncounters.map((note) => { const progress = encounterProgress.find((item) => item.source_document_id === note.sourceDocumentId); return <article key={note.sourceDocumentId || note.sourcePath}><b>{note.encounterName}</b><span>{progress?.resume_section_title ? `Resume at ${progress.resume_section_title}` : progress?.status === "completed" ? "Completed" : progress?.status === "abandoned" ? "Abandoned" : "No resume point saved"}</span></article>; })}</div> : <p>These notes occurred outside a prepared encounter.</p>}<small>Encounter and resume labels stay with the session run. Only the editable note text becomes source evidence.</small></section>}
            {sessionCaptureOpen ? <article className="document-view session-note-capture"><header><b>{sessionCaptureId ? "Edit session note" : "New session note"}</b><span>{sessionCaptureId ? "Corrected revision" : "Direct input"}</span></header><section className="character-content"><p>Capture manicured notes from actual play. The submitted text is preserved as immutable evidence before review.</p><div className="form-grid"><label>Session date<input aria-label="Session date" type="date" value={sessionCaptureDate} onChange={(event) => setSessionCaptureDate(event.target.value)} /></label><label>Title<input aria-label="Session note title" placeholder="Return to the Monastery" value={sessionCaptureTitle} onChange={(event) => setSessionCaptureTitle(event.target.value)} /></label></div><fieldset className="campaign-date-fields"><legend>In-game date</legend><p>This becomes the default campaign date for the next session note.</p><label>Campaign date (CE)<input aria-label="In-game date" type="date" value={inGameDate} onChange={(event) => setInGameDate(event.target.value)} /></label></fieldset><label className="pc-background-field session-notes-field">Notes<textarea ref={sessionNotesRef} aria-label="Session notes" placeholder="Enter one reviewable event or statement per line. Type @ to link a character or location." rows={18} value={sessionCaptureText} onChange={(event) => updateSessionCaptureText(event.target.value, event.currentTarget)} onKeyDown={handleSessionNotesKeyDown} />{mentionMatches.length > 0 && <div className="mention-suggestions" style={mentionMenuPosition} role="listbox" aria-label="Entity mentions">{mentionMatches.map((entity, index) => <button className={index === mentionHighlight ? "active" : ""} aria-selected={index === mentionHighlight} key={entity.entity_id} onMouseDown={(event) => event.preventDefault()} onClick={() => selectSessionMention(entity)} role="option" type="button"><b>{entity.canonical_name}</b><span>{display(entity.entity_kind)}</span></button>)}</div>}</label>{sessionMentions.length > 0 && <div className="mention-chips" aria-label="Linked records">{sessionMentions.map((entity) => <span key={entity.entity_id}>@{entity.canonical_name}<small>{display(entity.entity_kind)}</small></span>)}</div>}{sessionCaptureError && <div className="notice error" role="alert">{sessionCaptureError}</div>}<div className="step-actions"><button className="text-button" disabled={sessionCaptureBusy} onClick={() => { setSessionCaptureOpen(false); setSessionCaptureTableNoteIds([]); }} type="button">Cancel</button><button disabled={sessionCaptureBusy || !sessionCaptureDate || !inGameDate || !sessionCaptureTitle.trim() || !sessionCaptureText.trim()} onClick={() => void captureSessionNote()} type="button">{sessionCaptureBusy ? "Saving…" : sessionCaptureId ? "Save revision and review" : "Capture and review"}</button></div></section></article>
              : selectedPlan ? <PlanEntryView plan={selectedPlan} /> : docLoading ? <p className="queue-empty">Loading document…</p>
              : docContent ? (docMetadata?.document_type === "session_note" ? <><SessionNoteEntryView note={docMetadata} claims={docCanonicalClaims} history={docClaimHistory} onEditClaim={(claimId) => void beginClaimEdit(claimId)} onEdit={() => editSessionNote(docMetadata)} />{claimEdit && <ClaimReplacementEditor drafts={claimEditDrafts} busy={claimEditBusy} reason={claimEditReason} onChange={setClaimEditDrafts} onReasonChange={setClaimEditReason} onCancel={() => setClaimEdit(null)} onSave={() => void saveClaimCorrection()} />}{claimEditMessage && <div className="notice" role="status">{claimEditMessage}</div>}</> : <>{parseEntry(docContent).type === "encounter" ? <EncounterEntryView entry={parseEntry(docContent)} path={docContentPath} sourceDocumentId={docMetadata?.document_id ?? selectedDocumentId ?? ""} claims={docCanonicalClaims} history={docClaimHistory} sources={selectedEntry?.sources ?? []} npcEntries={libraryEntries.filter((entry) => entry.entity_kind === "npc")} noteCounts={new Map(Array.from(encounterNotes.filter((note) => note.sourceDocumentId === (docMetadata?.document_id ?? selectedDocumentId)).reduce((counts, note) => counts.set(note.sectionKey, (counts.get(note.sectionKey) ?? 0) + 1), new Map<string, number>()).entries()))} onOpenNpc={(npc) => void openEncounterNpcDossier(npc)} onAddNote={openTableNoteComposer} onOpenNotes={() => setTableNotesOpen(true)} onEditClaim={(claimId) => void beginClaimEdit(claimId)} />
                : selectedEntry && entityProfileEditing
                  ? (entityProfileDraft
                    ? <EntityProfileEditor entry={selectedEntry} profile={entityProfileDraft} onChange={setEntityProfileDraft} onCancel={() => { setEntityProfileEditing(false); setEntityProfileDraft(entityProfile); setEntityProfileMessage(""); setEntityProfileMessageIsError(false); }} onSave={() => void saveEntityProfile()} message={entityProfileMessage} messageIsError={entityProfileMessageIsError} onKindChange={(kind) => void correctEntityKind(kind)} members={selectedEntry.entity_kind === "faction" ? (selectedEntry.members ?? []) : undefined} roles={selectedEntry.entity_kind === "faction" ? (selectedEntry.roles ?? []) : undefined} memberSearch={memberSearch} memberResults={memberResults} onMemberSearch={(value) => { setMemberSearch(value); if (value.trim().length > 1) { campaignClient.searchEntities(value.trim()).then(setMemberResults).catch(() => setMemberResults([])); } else { setMemberResults([]); } }} onAddMember={(member) => void addFactionMember(member)} onRemoveMember={(member) => void removeFactionMember(member)} onAssignRole={(member, roleName, isLeadership) => void assignFactionRole(member, roleName, isLeadership)} vocabularies={templateVocabularies} locationNames={libraryEntries.filter((item) => item.entity_kind === "location").map((item) => item.canonical_name)} />
                    : <div className="detail-empty">Identity profile could not be loaded.</div>)
                  : <>{descriptionComposerOpen && selectedEntry && <DescriptionComposer entry={selectedEntry} claims={docCanonicalClaims} profile={entityProfile} campaignClient={campaignClient} jobPlatform={jobPlatform} initialText={revisionDraft} initialSelected={claimSelection} documentId={revisionDraft !== null && docMetadata?.document_type === "entity-description" ? selectedDocumentId : undefined} onDirtyChange={setComposerDirty} onQueueDraft={selectedEntry ? (command) => queueProseDraft(command, selectedEntry.entry_id, selectedEntry.canonical_name) : undefined} onClose={() => { setDescriptionComposerOpen(false); setRevisionDraft(null); setClaimSelection(null); setComposerDirty(false); }} onSaved={async () => { setDescriptionComposerOpen(false); setRevisionDraft(null); setClaimSelection(null); setComposerDirty(false); // The document list must refresh BEFORE the entry reloads — the page
          // matcher needs the just-filed authored page in its candidate pool.
          let fresh: SourceDocument[] | undefined;
          try { const page = await campaignClient.listSourceDocuments(); setSourceDocuments(page.items); fresh = page.items; } catch { /* the entry reload still runs */ }
          await loadCanonicalEntry(selectedEntry.entry_id, fresh);
          campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {}); }} />}{!descriptionComposerOpen && docMetadata?.document_type === "entity-description" && (() => {
                    // Only the stale ALERT renders — the neutral status bar is
                    // gone; revision lives in the header actions instead.
                    const referenced = docMetadata.referenced_claims ?? [];
                    const stale = supersededReferenceCount(referenced, docClaimHistory);
                    if (stale === 0) return null;
                    return <div className="notice error description-page-status" role="alert">
                      <span>{`${stale} of ${referenced.length} referenced record${referenced.length === 1 ? "" : "s"} changed since this page was written — consider revising`}</span>
                      <button className="text-button" onClick={() => { setRevisionDraft(docContent); setDescriptionComposerOpen(true); }} type="button">Revise description</button>
                    </div>;
                  })()}{entityProfileMessage && <div className="notice" role="status">{entityProfileMessage}</div>}
                <StructuredEntryView entry={docMetadata?.document_type === "entity-description" && selectedEntry
                  // An authored page is bare prose: it renders as the ENTRY
                  // (kind + canonical name), not as an untitled source doc.
                  ? { ...parseEntry(docContent), type: selectedEntry.entity_kind, name: selectedEntry.canonical_name, intro: parseEntry(docContent).intro || docContent.trim() }
                  : parseEntry(docContent)} path={docContentPath} claims={docCanonicalClaims} history={docClaimHistory} sources={selectedEntry?.sources ?? []} onEditClaim={(claimId) => void beginClaimEdit(claimId)} onEdit={selectedEntry ? openEntityProfileEditor : undefined} onWriteDescription={selectedEntry && docMetadata?.document_type !== "entity-description" ? () => { setRevisionDraft(null); setClaimSelection(null); void prefillSheetBackground(selectedEntry); setDescriptionComposerOpen(true); } : undefined} entityTemplate={selectedEntry ? { aliases: selectedEntry.aliases, base_location: selectedEntry.entity_kind === "faction" ? (entityProfile?.base_location ?? null) : undefined, location_type: selectedEntry.entity_kind === "location" ? (entityProfile?.location_type ?? null) : undefined, parent_location: selectedEntry.entity_kind === "location" ? (entityProfile?.parent_location ?? null) : undefined, roles: selectedEntry.entity_kind === "faction" ? (selectedEntry.roles ?? []) : undefined, race: entityProfile?.race ?? null, sex: entityProfile?.sex ?? null, player: entityProfile?.player ?? null, life_status: entityProfile?.life_status ?? null, life_status_since: entityProfile?.life_status_since ?? null } : undefined} roster={selectedEntry && selectedEntry.entity_kind === "faction" ? { members: selectedEntry.members ?? [], related: selectedEntry.related ?? [] } : undefined} dossierClaimIds={selectedEntry ? dossierClaimIds : undefined} movedAssertions={movedAssertions.length > 0 ? movedAssertions : undefined} onPromoteClaim={selectedEntry ? (claimId) => void toggleDossier(claimId, "promote") : undefined} onDemoteClaim={selectedEntry ? (claimId) => void toggleDossier(claimId, "demote") : undefined} onOpenEntryByName={openEntryByName} onReviseDescription={selectedEntry && docMetadata?.document_type === "entity-description" ? () => { setRevisionDraft(docContent); setDescriptionComposerOpen(true); } : undefined} locationTrail={locationTrail.length > 0 ? locationTrail : undefined} /></>}{claimEdit && <ClaimReplacementEditor drafts={claimEditDrafts} busy={claimEditBusy} reason={claimEditReason} onChange={setClaimEditDrafts} onReasonChange={setClaimEditReason} onCancel={() => setClaimEdit(null)} onSave={() => void saveClaimCorrection()} />}{claimEditMessage && <div className="notice" role="status">{claimEditMessage}</div>}</>
              ) : <div className="detail-empty">Select an entry from the library.</div>}
            {encounterDossierLoading && <div className="npc-dossier-loading" role="status">Loading NPC dossier…</div>}
            {encounterDossierError && <div className="npc-dossier-error" role="alert">{encounterDossierError}<button onClick={() => setEncounterDossierError("")} type="button">Dismiss</button></div>}
            {encounterDossier && <NpcDossierDrawer dossier={encounterDossier} collapsed={encounterDossierCollapsed} initialScroll={dossierScrollPositions.current.get(encounterDossier.entry.entry_id) ?? 0} onScroll={(position) => dossierScrollPositions.current.set(encounterDossier.entry.entry_id, position)} onToggleCollapsed={() => setEncounterDossierCollapsed((value) => !value)} onClose={() => setEncounterDossier(null)} onOpenFull={() => { const entryId = encounterDossier.entry.entry_id; setEncounterDossier(null); leaveEditorGuard(encounterDossier.entry.canonical_name, () => { setSelectedDocumentId(null); setSelectedPlan(null); setSelectedEntryId(entryId); void loadCanonicalEntry(entryId); }); }} />}
            

          </section>
        </div>

      </main>
      )}

      {activePage === "brainstorm" && <BrainstormWorkspace campaignClient={campaignClient} onReviewProposal={async (created) => {
        const firstCandidateId = created.items[0]?.evidence.candidate_id;
        if (!firstCandidateId) return;
        setReviewState({ selectedCandidateId: firstCandidateId, phase: "proposal_pending", proposal: created, message: "Brainstorm promotion proposal is ready for exact review." });
        setSelectedItemIds(created.items.map((item) => item.item_id));
        setProposalValidated(true);
        setActivePage("migration-legacy");
        await chooseCandidate(firstCandidateId);
      }} />}

      {activePage === "identity" && (
      <main className="page-identity">
        <section className="identity-page-header" aria-label="Identity review">
          <div className="section-heading"><div><p className="kicker">Identity maintenance</p><h2>Identity Review</h2></div><p>Names that recur in current claims but resolve to no identity. Detection is automatic; every decision is yours, recorded, and undoable. Nothing merges automatically.</p></div>
          <div className="identity-toolbar">
            <button className={identityViewMode === "cards" ? "active" : ""} onClick={() => setIdentityViewMode("cards")} type="button">Full entries</button>
            <button className={identityViewMode === "compact" ? "active" : ""} onClick={() => setIdentityViewMode("compact")} type="button">Compact list</button>
            <button className="secondary-button" disabled={identityBusy} onClick={() => void loadIdentityGaps()} type="button">{identityBusy ? "Working…" : "Refresh"}</button>
          </div>
          {identityMessage && <p role={identityMessageIsError ? "alert" : "status"} className={"identity-message" + (identityMessageIsError ? " notice error" : "")}>{identityMessage}</p>}
          {identityRecent.length > 0 && <div className="identity-recent" aria-label="Recent identity decisions">{identityRecent.map(({ receipt, done }) => <span key={receipt.decision_id}>{done} <button className="text-button" disabled={identityBusy || receipt.kind === "revert"} onClick={() => void undoIdentity(receipt.decision_id, done)} type="button">Undo</button></span>)}</div>}
        </section>

        {identityGaps !== null && (<p className="identity-count" data-testid="identity-count">Showing {identityViewMode === "cards" ? Math.min(identityVisibleCount, identityGaps.length) : identityGaps.length} of {identityQueueTotal} unresolved surface{identityQueueTotal === 1 ? "" : "s"}</p>)}
        {identityGaps !== null && identityGaps.length === 0 && <p className="identity-empty">No unresolved surfaces right now.</p>}

        {identityViewMode === "compact" && identityGaps !== null && identityGaps.length > 0 && <div className="identity-compact-list">
        {identityGaps.map((gap) => (
          <article className="identity-compact-row" key={gap.normalized_surface}>
            <b>{gap.surface}</b>
            {gap.suggested_canonical_name && gap.suggested_canonical_name !== gap.surface && <span className="identity-compact-suggestion">appears as “{gap.suggested_canonical_name}” without title</span>}
            <span>{gap.retrieval_demand > 0 && <>{gap.retrieval_demand} lookup misses · </>}{gap.claims_with_phrase} claims · {gap.total_mentions} mentions{gap.role_hint ? " · role-like" : ""}</span>
            <span className="identity-compact-actions">
              {gap.alias_candidates.map((candidate) => <button className="decision-button outline" key={candidate.entity_id} disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.addIdentityAlias(gap.surface, candidate.entity_id, `identity-alias:${gap.normalized_surface}:${candidate.entity_id}:${Date.now()}`), `Aliased “${gap.surface}” to ${candidate.canonical_name}`)} type="button">Alias → {candidate.canonical_name}</button>)}
              <button className="text-button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.createIdentityEntity(identityCanonical[gap.normalized_surface] ?? gap.surface, identityKinds[gap.normalized_surface] ?? gap.suggested_kind ?? "faction", `identity-create:${gap.normalized_surface}:${Date.now()}`, [], []), `Created ${identityCanonical[gap.normalized_surface] ?? gap.surface} as an identity`)} type="button">Create</button>
              <button className="text-button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.markIdentityRole(gap.surface, `identity-role:${gap.normalized_surface}:${Date.now()}`), `Marked “${gap.surface}” as a role or title`)} type="button">Role</button>
              <button className="text-button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.dismissIdentityGap(gap.surface, `identity-dismiss:${gap.normalized_surface}:${Date.now()}`), `Dismissed “${gap.surface}”`)} type="button">Dismiss</button>
            </span>
          </article>
        ))}
        </div>}

        {identityViewMode === "cards" && identityGaps?.slice(0, identityVisibleCount).map((gap) => (
          <article className="identity-gap identity-full" key={gap.normalized_surface}>
            <div className="identity-gap-main">
              <label className="identity-canonical">{gap.suggested_canonical_name && gap.suggested_canonical_name !== gap.surface ? `Canonical name (claims say “${gap.surface}”)` : "Canonical name"}<input aria-label={`Canonical name for ${gap.surface}`} value={identityCanonical[gap.normalized_surface] ?? gap.surface} onChange={(event) => setIdentityCanonical((current) => ({ ...current, [gap.normalized_surface]: event.target.value }))} /></label>
              <span>{gap.retrieval_demand > 0 && <>{gap.retrieval_demand} lookup miss{gap.retrieval_demand === 1 ? "" : "es"} · </>}{gap.claims_with_phrase} claim{gap.claims_with_phrase === 1 ? "" : "s"} · {gap.total_mentions} mention{gap.total_mentions === 1 ? "" : "s"}</span>
            </div>
            {gap.role_hint && <p className="identity-role-hint">Ends like a role or title you have marked before.</p>}
            <details className="identity-evidence-list"><summary>Claims mentioning “{gap.surface}” ({gap.evidence.length} shown)</summary>{gap.evidence.map((item) => <blockquote key={item.claim_id}>“{item.excerpt}”</blockquote>)}</details>
            {gap.related_surfaces.length > 0 && <fieldset className="identity-related"><legend>Merge these related surfaces as aliases?</legend>{gap.related_surfaces.map((surface) => <label key={surface}><input checked={(identityAliasSelection[gap.normalized_surface] ?? []).includes(surface)} onChange={(event) => setIdentityAliasSelection((current) => ({ ...current, [gap.normalized_surface]: event.target.checked ? [...(current[gap.normalized_surface] ?? []), surface] : (current[gap.normalized_surface] ?? []).filter((item) => item !== surface) }))} type="checkbox" />{surface}</label>)}</fieldset>}
            <label className="identity-manual-aliases">Manual aliases (comma-separated)<input aria-label={`Manual aliases for ${gap.surface}`} placeholder="e.g. The Stars, Court of Stars" value={identityManualAliases[gap.normalized_surface] ?? ""} onChange={(event) => setIdentityManualAliases((current) => ({ ...current, [gap.normalized_surface]: event.target.value }))} /></label>
            <div className="identity-target">
              <label>Alias to an existing identity<input aria-label={`Alias target search for ${gap.surface}`} placeholder="Search identities…" value={identityTargetQuery[gap.normalized_surface] ?? ""} onChange={(event) => { const value = event.target.value; setIdentityTargetQuery((current) => ({ ...current, [gap.normalized_surface]: value })); if (value.trim().length > 1) { campaignClient.searchEntities(value.trim()).then((results) => setIdentityTargetResults((current) => ({ ...current, [gap.normalized_surface]: results }))).catch(() => {}); } else { setIdentityTargetResults((current) => ({ ...current, [gap.normalized_surface]: [] })); } }} /></label>
              {(identityTargetResults[gap.normalized_surface] ?? []).length > 0 && <div className="identity-target-results" role="listbox" aria-label={`Alias target matches for ${gap.surface}`}>{(identityTargetResults[gap.normalized_surface] ?? []).map((match) => <span className="identity-target-match" key={match.entity_id} role="option"><button onClick={() => void decideIdentity(() => campaignClient.addIdentityAlias(gap.surface, match.entity_id, `identity-alias:${gap.normalized_surface}:${match.entity_id}:${Date.now()}`), `Aliased “${gap.surface}” to ${match.canonical_name}`)} type="button"><b>{match.canonical_name}</b><small>{display(match.entity_kind)}{match.match_kind === "alias" && match.matched_name ? ` · via ${match.matched_name}` : ""}</small></button><button className="text-button" onClick={() => void decideIdentity(() => campaignClient.markIdentityMisspelling(gap.surface, match.entity_id, `identity-misspelling:${gap.normalized_surface}:${match.entity_id}:${Date.now()}`), `Recorded “${gap.surface}” as a misspelling of ${match.canonical_name}`)} title="Record this surface as a misspelling of the identity — resolvable, never a name" type="button">Misspelling</button></span>)}</div>}
              {gap.alias_candidates.length > 0 && <div className="identity-alias-candidates"><span>Suggested:</span>{gap.alias_candidates.map((candidate) => <span className="identity-target-match" key={candidate.entity_id}><button type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.addIdentityAlias(gap.surface, candidate.entity_id, `identity-alias:${gap.normalized_surface}:${candidate.entity_id}:${Date.now()}`), `Aliased “${gap.surface}” to ${candidate.canonical_name}`)}><b>Alias → {candidate.canonical_name}</b></button><button className="text-button" type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.markIdentityMisspelling(gap.surface, candidate.entity_id, `identity-misspelling:${gap.normalized_surface}:${candidate.entity_id}:${Date.now()}`), `Recorded “${gap.surface}” as a misspelling of ${candidate.canonical_name}`)} title="Record this surface as a misspelling of the identity — resolvable, never a name">Misspelling</button></span>)}</div>}
            </div>
            <div className="identity-actions">
              <label>Kind<select aria-label={`Entity kind for ${gap.surface}`} value={identityKinds[gap.normalized_surface] ?? gap.suggested_kind ?? "faction"} onChange={(event) => setIdentityKinds((current) => ({ ...current, [gap.normalized_surface]: event.target.value }))}>{entityKinds.map((kind) => <option key={kind.kind} value={kind.kind}>{kind.label}</option>)}</select></label>
              <button className="decision-button" type="button" disabled={identityBusy || gap.alias_candidates.some((candidate) => candidate.canonical_name.toLocaleLowerCase() === (identityCanonical[gap.normalized_surface] ?? gap.surface).trim().toLocaleLowerCase())} title={gap.alias_candidates.some((candidate) => candidate.canonical_name.toLocaleLowerCase() === (identityCanonical[gap.normalized_surface] ?? gap.surface).trim().toLocaleLowerCase()) ? "That name already resolves — use the alias action instead" : undefined} onClick={() => { const canonical = (identityCanonical[gap.normalized_surface] ?? gap.surface).trim() || gap.surface; const manual = (identityManualAliases[gap.normalized_surface] ?? "").split(",").map((value) => value.trim()).filter(Boolean); const related = identityAliasSelection[gap.normalized_surface] ?? []; const aliases = [...related]; if (canonical !== gap.surface && !aliases.includes(gap.surface) && !manual.includes(gap.surface)) aliases.unshift(gap.surface); void decideIdentity(() => campaignClient.createIdentityEntity(canonical, identityKinds[gap.normalized_surface] ?? gap.suggested_kind ?? "faction", `identity-create:${gap.normalized_surface}:${Date.now()}`, aliases, manual), `Created ${canonical} as an identity${aliases.length + manual.length ? ` with ${aliases.length + manual.length} alias${aliases.length + manual.length === 1 ? "" : "es"}` : ""}`); }}>{(() => { const aliasCount = (identityAliasSelection[gap.normalized_surface] ?? []).length + (identityManualAliases[gap.normalized_surface] ?? "").split(",").map((value) => value.trim()).filter(Boolean).length; return aliasCount > 0 ? `Create with ${aliasCount} alias${aliasCount === 1 ? "" : "es"}` : "Create entity"; })()}</button>
              <button className="text-button" type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.markIdentityRole(gap.surface, `identity-role:${gap.normalized_surface}:${Date.now()}`), `Marked “${gap.surface}” as a role or title`)}>Mark as role</button>
              <button className="text-button" type="button" disabled={identityBusy} onClick={() => void decideIdentity(() => campaignClient.dismissIdentityGap(gap.surface, `identity-dismiss:${gap.normalized_surface}:${Date.now()}`), `Dismissed “${gap.surface}”`)}>Dismiss</button>
            </div>
          </article>
        ))}
        {identityViewMode === "cards" && identityGaps !== null && identityVisibleCount < identityGaps.length && <button className="secondary-button identity-show-more" onClick={() => setIdentityVisibleCount((count) => count + 20)} type="button">Show 20 more</button>}
      </main>
      )}

      {activePage === "roles" && <FactionRolesPage campaignClient={campaignClient} factions={libraryEntries.filter((entry) => entry.entity_kind === "faction")} onRefreshLibrary={() => campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {})} onOpenFaction={(entryId) => { setActivePage("documents"); leaveEditorGuard(libraryEntries.find((entry) => entry.entry_id === entryId)?.canonical_name ?? "the faction", () => { setSelectedEntryId(entryId); void loadCanonicalEntry(entryId); }); }} />}
      {activePage === "migration" && <Phase2MigrationsPage campaignClient={campaignClient} onOpenEntry={(entityId, entityName) => { leaveEditorGuard(entityName, () => { setActivePage("documents"); setSelectedEntryId(entityId); void loadCanonicalEntry(entityId).then((entry) => { // Open after the load: the entry switch inside loadCanonicalEntry resets the composer surfaces (ADR-0016).
      setRevisionDraft(null); setClaimSelection(null); if (entry) void prefillSheetBackground(entry); setDescriptionComposerOpen(true); }); }); }} onOpenProfile={(entityId, entityName) => { leaveEditorGuard(entityName, () => { setActivePage("documents"); setSelectedEntryId(entityId); void loadCanonicalEntry(entityId).then(() => openEntityProfileEditor()); }); }} onOpenDocument={(documentId, documentPath) => { leaveEditorGuard("the capture", async () => { const nextFilters: CandidateFilters = { status: "active", review_status: "pending", ...(documentPath ? { source: documentPath } : {}) }; setFilters(nextFilters); setActivePage("migration-legacy"); try { const page = await campaignClient.listCandidates(nextFilters); await loadReviewWorkspace(nextFilters, false); if (page.items.length > 0) await chooseCandidate(page.items[0].candidate_id); } catch { /* the workspace still renders; selection can be manual */ } }); }} onOpenBrainstorm={() => { leaveEditorGuard("Brainstorm", () => setActivePage("brainstorm")); }} />}

      {activePage === "migration-legacy" && (
      <main className="page-migration">
        {sessionReviewActive ? <nav aria-label="Session review progress" className="session-review-progress"><b>Review session statements</b><span>{sessionReviewComplete ? "Complete" : `${directPosition} of ${directPending.length} pending`}</span></nav> : <nav aria-label="Migration progress" className="migration-progress">
          {MIGRATION_STEPS.map((label, index) => {
            const step = (index + 1) as MigrationStep;
            return <button aria-current={migrationStep === step ? "step" : undefined} className={migrationStep === step ? "active" : migrationStep > step ? "complete" : ""} disabled={step > migrationStep || proposalBlocksSelection} key={label} onClick={() => setMigrationStep(step)} type="button"><span>{step}</span>{label}</button>;
          })}
        </nav>}{(batchNotice || (!sessionReviewActive && (extractionNotice || extractionJob))) && <div className="batch-notice" role="status"><span>{batchNotice || extractionNotice || "Background extraction running."}</span>{!sessionReviewActive && extractionJob && <small>{display(extractionJob.state)} · {displayedExtractionJob.jobId.slice(0, 12)}</small>}</div>}<div className={`doc-layout ${sessionReviewActive ? "session-review-layout" : ""}`}>
          {!sessionReviewActive && <aside className="doc-tree-panel" aria-label="Source tree">
            <div className="tree-header"><span>Documents</span><b>{sourceDocuments.length} sources</b></div>
            {activeRun && <div className="run-summary-compact" aria-label="Import run summary"><span>{activeRun.admitted_file_count} sources</span><span>{activeRun.candidate_count} candidates</span><span>{activeRun.review_count} reviews</span></div>}
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
                {!extractionPending && (displayedExtractionJob.state === "failed" || ((displayedExtractionJob.result as { results?: Array<{ ok: boolean }> } | undefined)?.results ?? []).some((result) => !result.ok)) && <button className="task-retry" onClick={() => void retryFailedExtraction()} type="button"><WandIcon />Retry failed extraction</button>}
              </article>}
              {extractionTaskError && <div className="task-error" role="alert"><span>{extractionTaskError}</span><button aria-label="Dismiss extraction error" onClick={() => setExtractionTaskError("")} type="button">Dismiss</button></div>}
            </section>
          </aside>}
          <section className="doc-content-panel" aria-label="Migration workspace">
            {sessionReviewComplete ? <section className="session-review-complete" aria-label="Session review complete"><span>Session note complete</span><h2>Every statement has been reviewed.</h2><p>The claims were applied with their original note evidence and campaign date.</p><small>Final receipt {sessionReviewComplete.receiptId}</small><div className="step-actions"><button className="text-button" onClick={() => { setSessionReviewComplete(null); setActivePage("documents"); setSelectedDocumentId(sessionReviewComplete.sourceDocumentId); void loadDocumentContent(sessionReviewComplete.sourceDocumentId, sessionReviewComplete.sourcePath); }} type="button">View session note</button><button onClick={() => { setSessionReviewComplete(null); setActivePage("documents"); void openSessionCapture(); }} type="button">Capture another session note</button></div></section> : migrationStep === 1 ? <div className="detail-empty batch-start"><span>{selectedDocumentId ? "Review one candidate, or prepare every pending candidate in this document." : "Select a source to narrow the queue, then select a candidate."}</span>{selectedDocumentId && candidates.some((candidate) => candidate.review_status === "pending") && <button disabled={batchBusy || extractionPending} onClick={() => void extractPendingSequence()} type="button"><WandIcon />{extractionPending ? "Extraction job running" : batchBusy ? "Queueing sequence…" : "Extract pending candidates"}</button>}</div> : !selected ? <div className="detail-empty">Select a candidate to review.</div> : (
              <div className={`candidate-detail migration-detail ${directSessionReview ? "direct-session-review" : ""}`}>
                {reviewError && <div className="notice error persistent-review-error" role="alert"><b>Claim was not committed.</b><span>{reviewError}</span><button className="text-button" onClick={() => setReviewError("")} type="button">Dismiss</button></div>}
                <header className="candidate-title"><div><span className={`status-pill status-${selected.review_status}`}>{display(selected.review_status)}</span><h3>{selected.assertion_text}</h3></div>{!directSessionReview && <dl><div><dt>State</dt><dd>{display(selected.state)}</dd></div><div><dt>Authority</dt><dd>{display(selected.authority)}</dd></div><div><dt>Visibility</dt><dd>{display(selected.visibility)}</dd></div></dl>}</header>
                {selected.evidence.map((evidence) => directSessionReview ? <details className="source-evidence compact-evidence" key={evidence.source_revision_id}><summary>Evidence details</summary><blockquote>{evidence.excerpt}</blockquote><dl><div><dt>Source</dt><dd>{evidence.source_path}</dd></div><div><dt>Section</dt><dd>{evidence.section}</dd></div><div><dt>Offsets</dt><dd>{evidence.start_offset}–{evidence.end_offset}</dd></div><div><dt>Revision</dt><dd title={evidence.content_hash}>{evidence.content_hash.slice(0, 12)}</dd></div></dl></details> : <article className="source-evidence" key={evidence.source_revision_id}><div><span>Exact source evidence</span><b>{evidence.source_path}</b></div><blockquote>{evidence.excerpt}</blockquote><dl><div><dt>Section</dt><dd>{evidence.section}</dd></div><div><dt>Classification</dt><dd>{display(evidence.classification)}</dd></div><div><dt>Offsets</dt><dd>{evidence.start_offset}–{evidence.end_offset}</dd></div><div><dt>Revision</dt><dd title={evidence.content_hash}>{evidence.content_hash.slice(0, 12)}</dd></div></dl></article>)}
                {[2, 3].includes(migrationStep) && selected.review_status === "pending" && !proposalBelongsToSelected && <section className={`resolution-form ${directSessionReview ? "session-claim-review" : ""}`} aria-label="Provenance-first proposal"><header><span>{directSessionReview ? "Review statement" : "Promote this claim"}</span><p>{directSessionReview ? "Correct the claim if needed, then commit it and continue to the next statement." : "Edit the canonical wording and truth dimensions. The exact imported text remains unchanged below as provenance."}</p></header>{splitClaims ? <section className="split-claim-editor" aria-label="Split claims"><header><span>Split claims</span><p>Each entry will become its own claim with the same source evidence and campaign date.</p></header>{splitClaims.map((claim, index) => <div className="split-claim-row" key={index}><label>Claim {index + 1}<textarea aria-label={`Split claim ${index + 1}`} value={claim} onChange={(event) => setSplitClaims((prior) => prior?.map((value, itemIndex) => itemIndex === index ? event.target.value : value) ?? null)} /></label><button className="text-button" disabled={splitClaims.length <= 1} onClick={() => setSplitClaims((prior) => prior?.filter((_value, itemIndex) => itemIndex !== index) ?? null)} type="button">Remove</button></div>)}<div className="step-actions"><button className="text-button" onClick={() => setSplitClaims((prior) => [...(prior ?? []), ""])} type="button">Add claim</button><button className="text-button" onClick={() => setSplitClaims(null)} type="button">Cancel split</button></div></section> : <label>Canonical assertion<textarea aria-label="Canonical claim" value={provenanceAssertion} onChange={(event) => setProvenanceAssertion(event.target.value)} /></label>}{directSessionReview && !splitClaims && <button className="text-button" onClick={beginClaimSplit} type="button">Split into claims</button>}{directMentions.length > 0 && <div className="candidate-mentions"><span>Related records</span>{directMentions.map((mention) => <b key={mention.entity_id}>@{mention.display_name}</b>)}<small>These records will be linked to every claim; no subject role is inferred.</small></div>}{directSessionReview ? <label>Observed campaign date<input aria-label="Observed campaign date" required type="date" value={observedCampaignDate} onChange={(event) => setObservedCampaignDate(event.target.value)} /></label> : <><div className="form-grid"><label>State<select aria-label="Canonical claim state" value={provenanceState} onChange={(event) => { setProvenanceState(event.target.value); if (event.target.value === "possible") { setConditionEnabled(false); setConditionText(""); } }}><option value="observed">Observed</option><option value="established">Established</option><option value="intended">Intended</option><option value="prepared">Prepared</option><option value="possible">Possible</option><option value="considered">Considered</option></select></label><label>Authority<select aria-label="Canonical claim authority" value={provenanceAuthority} onChange={(event) => setProvenanceAuthority(event.target.value)}><option value="real_play">Real play</option><option value="explicit_lore">Explicit lore</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option><option value="unclassified">Unclassified</option></select></label><label>Visibility<select aria-label="Canonical claim visibility" value={provenanceVisibility} onChange={(event) => setProvenanceVisibility(event.target.value)}><option value="dm_only">DM only</option><option value="party">Party</option><option value="character">Character</option></select></label></div>{provenanceState === "observed" && <label>Observed campaign year<input aria-label="Observed campaign year" required type="number" value={observedAt} onChange={(event) => setObservedAt(event.target.value)} /></label>}{provenanceState !== "possible" && <fieldset><label><input checked={conditionEnabled} onChange={(event) => { setConditionEnabled(event.target.checked); if (!event.target.checked) setConditionText(""); }} type="checkbox" />Has a concrete prerequisite</label></fieldset>}{conditionEnabled && provenanceState !== "possible" && <label>Condition trigger<input aria-label="Condition trigger" placeholder="The concrete event that activates this consequence" value={conditionText} onChange={(event) => setConditionText(event.target.value)} /></label>}</>}<div className="step-actions">{directSessionReview && <button className="text-button" disabled={reviewBusy || !dispositionReason.trim()} onClick={() => void disposition("deferred")} type="button">Skip with reason</button>}<button disabled={reviewBusy || (splitClaims ? !splitClaims.some((claim) => claim.trim()) : !provenanceAssertion.trim()) || (directSessionReview ? !observedCampaignDate : (provenanceState === "observed" && !observedAt)) || (conditionEnabled && provenanceState !== "possible" && !conditionText.trim())} onClick={() => void (directSessionReview ? commitDirectInputClaim() : createProvenanceFirstProposal())} type="button">{directSessionReview ? `Commit ${splitClaims ? splitClaims.filter((claim) => claim.trim()).length : 1} claim${splitClaims && splitClaims.filter((claim) => claim.trim()).length !== 1 ? "s" : ""} and continue` : "Create source-backed proposal"}</button></div>{directSessionReview && <input aria-label="Skip reason" value={dispositionReason} onChange={(event) => setDispositionReason(event.target.value)} placeholder="Reason required only when skipping" />}</section>}
                {migrationStep === 2 && selected.review_status === "pending" && <div className="extraction-actions"><button className="text-button" disabled={extractionPending || proposalBlocksSelection} onClick={() => void runExtraction(selected.candidate_id)} type="button"><WandIcon />{extractionPending ? "Extraction job running" : (selected.extractions && selected.extractions.length > 0 ? "Re-extract this candidate" : "Extract this candidate")}</button>{candidates.filter((candidate) => candidate.review_status === "pending").length > 1 && <button className="text-button" disabled={batchBusy || extractionPending || proposalBlocksSelection} onClick={() => void extractPendingSequence()} type="button"><WandIcon />{`Extract all ${Math.min(50, candidates.filter((candidate) => candidate.review_status === "pending").length)} pending candidates`}</button>}</div>}
                {migrationStep === 3 && selected.extraction_segments && selected.extraction_segments.length > 0 && <section className="extraction-coverage" aria-label="Extraction coverage"><header><span>Source coverage</span><b>{selected.extraction_segments.filter((segment) => segment.disposition !== "unaccounted").length} / {selected.extraction_segments.length} accounted for</b></header>{selected.extraction_segments.some((segment) => segment.disposition !== "extracted") ? <div>{selected.extraction_segments.filter((segment) => segment.disposition !== "extracted").map((segment) => <article key={segment.segment_id}><div><b>{segment.segment_id}</b><span>{display(segment.disposition)}</span></div><p>{segment.text}</p></article>)}</div> : <p>Every source segment is represented by extracted claims.</p>}</section>}
                {!directSessionReview && migrationStep === 3 && extractionDrafts.length > 0 && <AssertionFirstReview drafts={extractionDrafts} setDrafts={setExtractionDrafts} onBack={() => setMigrationStep(2)} onAbandon={abandonExtraction} onContinue={(subject) => void prepareSubjectGroups(subject)} />}
                {!directSessionReview && migrationStep === 3 && extractionDrafts.length > 0 && <section className="extraction-editor" aria-label="Editable extraction review"><header><span>Review extracted claims</span><p>All grounded claims are grouped here. Correct mistakes or exclude a claim, then continue once.</p></header><div className="extraction-draft-list">{extractionDrafts.map((draft, index) => <article className={draft.included ? "extraction-draft" : "extraction-draft excluded"} key={draft.extractionId}><label className="include-extraction"><input checked={draft.included} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, included: event.target.checked } : item))} type="checkbox" />Include claim {index + 1}</label><div className="form-grid"><label>Subject<input aria-label={`Extraction ${index + 1} subject`} value={draft.subject} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, subject: event.target.value } : item))} /></label><label>Predicate<input aria-label={`Extraction ${index + 1} predicate`} value={draft.predicate} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, predicate: event.target.value } : item))} /></label><label>Object<input aria-label={`Extraction ${index + 1} object`} value={draft.objectEntity} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, objectEntity: event.target.value } : item))} /></label><label>State<select aria-label={`Extraction ${index + 1} state`} value={draft.state} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, state: event.target.value } : item))}><option value="observed">Observed</option><option value="established">Established</option><option value="intended">Intended</option><option value="prepared">Prepared</option><option value="possible">Possible</option><option value="considered">Considered</option></select></label><label>Authority<select aria-label={`Extraction ${index + 1} authority`} value={draft.authority} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, authority: event.target.value } : item))}><option value="real_play">Real play</option><option value="explicit_lore">Explicit lore</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option><option value="unclassified">Unclassified</option></select></label><label>Visibility<select aria-label={`Extraction ${index + 1} visibility`} value={draft.visibility} onChange={(event) => setExtractionDrafts((prior) => prior.map((item, itemIndex) => itemIndex === index ? { ...item, visibility: event.target.value } : item))}><option value="dm_only">DM only</option><option value="party">Party</option><option value="character">Character</option></select></label></div></article>)}</div><p className="extraction-note">Object text remains review context; a canonical object relationship requires an explicit entity identity.</p><div className="step-actions"><button className="danger-button" onClick={abandonExtraction} type="button">Abandon extraction</button><button className="text-button" onClick={() => setMigrationStep(2)} type="button">Back to candidate</button><button disabled={!extractionDrafts.some((draft) => draft.included && draft.subject.trim() && draft.predicate.trim())} onClick={() => { const first = extractionDrafts.find((draft) => draft.included); setEntityName(first?.subject.trim() ?? ""); setMigrationStep(4); }} type="button">Continue with selected claims</button></div></section>}
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
                {migrationStep === 5 && proposal && claimCorrection && <section className="resolution-form proposal-correction" aria-label="Correct pending claim"><header><span>New immutable proposal version</span><p>The evidence remains unchanged. Saving replaces no history and invalidates approval of the displayed version.</p></header><label>Claim<textarea aria-label="Corrected claim" value={claimCorrection.assertion_text} onChange={(event) => setClaimCorrection({ ...claimCorrection, assertion_text: event.target.value })} /></label><div className="form-grid"><label>State<select aria-label="Corrected state" value={claimCorrection.state} onChange={(event) => { const state = event.target.value; const authority = ({ observed: "real_play", established: "explicit_lore", intended: "npc_intention", prepared: "preparation", possible: "brainstorm" } as Record<string, string>)[state]; setClaimCorrection({ ...claimCorrection, state, authority }); }}><option value="observed">Observed</option><option value="established">Established</option><option value="intended">Intended</option><option value="prepared">Prepared</option><option value="possible">Possible</option><option value="considered">Considered</option></select></label><label>Authority<select aria-label="Corrected authority" value={claimCorrection.authority} onChange={(event) => setClaimCorrection({ ...claimCorrection, authority: event.target.value })}><option value="real_play">Real play</option><option value="explicit_lore">Explicit lore</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option></select></label><label>Visibility<select aria-label="Corrected visibility" value={claimCorrection.visibility} onChange={(event) => setClaimCorrection({ ...claimCorrection, visibility: event.target.value })}><option value="dm_only">DM only</option><option value="party">Party</option><option value="character">Character</option></select></label></div><fieldset><label><input checked={claimCorrection.is_conditional} onChange={(event) => setClaimCorrection({ ...claimCorrection, is_conditional: event.target.checked })} type="checkbox" />Conditional</label><label><input checked={claimCorrection.predicts_subject_action} onChange={(event) => setClaimCorrection({ ...claimCorrection, predicts_subject_action: event.target.checked })} type="checkbox" />Predicts subject action</label></fieldset><div className="step-actions"><button className="text-button" onClick={() => setClaimCorrection(null)} type="button">Cancel correction</button><button disabled={reviewBusy || !claimCorrection.assertion_text.trim()} onClick={() => void reviseClaimProposal()} type="button">Save as new version</button></div></section>}
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
        <LifeStatusPanel campaignClient={campaignClient} />
        <LinkAuditPanel campaignClient={campaignClient} onOpenEntry={(entityId, entityName) => { leaveEditorGuard(entityName, () => { setActivePage("documents"); setSelectedEntryId(entityId); void loadCanonicalEntry(entityId); }); }} />
        <ConflictReviewPanel campaignClient={campaignClient} />
        <SessionDatingPanel campaignClient={campaignClient} />
        

        {sourceReviews.length > 0 && <section className="operations source-reviews-tool" aria-label="Source reviews"><div className="section-heading"><div><p className="kicker">Import maintenance</p><h2>Source Reviews</h2></div><p>Source-level quarantine and unresolved-reference work lives outside the migration workflow.</p></div><div className="source-review-queue"><header><span>Open source reviews</span><b>{sourceReviews.length} open · {quarantineCount} quarantined</b></header>{sourceReviews.slice(0, 20).map((review) => <article key={review.review_id}><span>{display(review.kind)} · {display(review.classification ?? "unclassified")}</span><b>{review.source_path ?? review.subject_id}</b><p>{reviewSummary(review)}</p></article>)}</div></section>}

        <ClaimReconciliationWorkspace campaignClient={campaignClient} />
        <PlanWorkspace campaignClient={campaignClient} />

        <section className="operations" id="operations"><div className="section-heading"><div><p className="kicker">Infrastructure</p><h2>Operations</h2></div><p>Background work remains visible and recoverable after refresh.</p></div><article className="operation-card"><div className="operation-icon"><PulseIcon /></div><div className="operation-copy"><span>Campaign Core</span><h3>Service health check</h3><p>Runs through the isolated Windmill job adapter. No campaign database credential crosses this boundary.</p>{job && <div className={`job-status status-${job.state}`} role="status"><div><b>{JOB_COPY[job.state]}</b><span>{job.jobId.slice(0, 12)}</span></div><div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div>{job.error && <p>{job.error}</p>}</div>}{jobActionError && <p className="inline-error">Status unavailable: {jobActionError}</p>}</div><button className="secondary-button" disabled={Boolean(isPending)} onClick={startHealthCheck} type="button">{isPending ? "Checking…" : job?.state === "failed" ? "Retry check" : "Run check"}</button></article></section>
      </main>
      )}
      {activePage === "log" && <ActivityLogPage campaignClient={campaignClient} />}
      {activePage === "help" && <GlossaryHelpPage anchor={helpAnchor} />}
      {activePage === "settings" && <SettingsPage settings={appSettings} onChange={updateAppSettings} campaignClient={campaignClient} />}
      {activePage === "lore" && <LoreCreationPage campaignClient={campaignClient} jobPlatform={jobPlatform} libraryEntries={libraryEntries} onOpenEntry={(entityId, name) => { leaveEditorGuard(name, () => { setActivePage("documents"); setSelectedEntryId(entityId); void loadCanonicalEntry(entityId); }); }} onQueueDraft={queueProseDraft} pendingDraft={revisionDraft} onConsumeDraft={() => setRevisionDraft(null)} onCreated={() => { campaignClient.listSourceDocuments().then((page) => setSourceDocuments(page.items)).catch(() => {}); campaignClient.listLibraryEntries().then(setLibraryEntries).catch(() => {}); }} />}
      {activePage === "conventions" && (
      <main className="page-conventions">
        <section className="identity-page-header" aria-label="UI conventions">
          <div className="section-heading"><div><p className="kicker">Reference</p><h2>Conventions</h2></div><p>The design language of this app, rendered live. Every component below names its CSS class so styling can be fixed by name. The written reference is docs/architecture/ui-conventions.md; this page is generated from the same stylesheet.</p></div>
        </section>

        <section className="convention-group" aria-label="Design tokens">
          <h3>Design tokens</h3>
          <div className="convention-swatches">
            <span className="convention-swatch"><i style={{ background: "#292821" }} /><b>Ink #292821</b><small>body text</small></span>
            <span className="convention-swatch"><i style={{ background: "#f2f0e8", border: "1px solid #cbc5b7" }} /><b>Paper #f2f0e8</b><small>page background</small></span>
            <span className="convention-swatch"><i style={{ background: "#fffefa", border: "1px solid #cbc5b7" }} /><b>Card #fffefa</b><small>panels</small></span>
            <span className="convention-swatch"><i style={{ background: "#f0ede4", border: "1px solid #cbc5b7" }} /><b>Panel tint #f0ede4</b><small>queues</small></span>
            <span className="convention-swatch"><i style={{ background: "#82533a" }} /><b>Accent #82533a</b><small>actions, kickers</small></span>
            <span className="convention-swatch"><i style={{ background: "#68412d" }} /><b>Accent hover #68412d</b><small>button hover</small></span>
            <span className="convention-swatch"><i style={{ background: "#7d776c" }} /><b>Muted #7d776c</b><small>descriptions</small></span>
            <span className="convention-swatch"><i style={{ background: "#d6d0c3" }} /><b>Hairline #d6d0c3</b><small>borders</small></span>
          </div>
          <p className="convention-note">Type: <b>Manrope</b> UI · <b>Libre Caslon Display</b> headings &amp; prose · <b>DM Mono</b> uppercase kickers/labels/counts. Kicker pattern: <code>.kicker</code> / mono 8–10px uppercase, letter-spacing .06–.13em.</p>
        </section>

        <section className="convention-group" aria-label="Buttons">
          <h3>Buttons</h3>
          <div className="convention-row">
            <button className="secondary-button" type="button">Primary · .secondary-button / .ask-row button</button>
            <span className="convention-tag">solid #82533a · 6px radius · 11px bold</span>
          </div>
          <div className="convention-row">
            <button className="text-button" type="button">Tertiary · .text-button</button>
            <span className="convention-tag">borderless · muted/accent text</span>
          </div>
          <div className="convention-row">
            <div className="entry-page-actions"><button aria-label="Edit entry" title="Edit" type="button"><RecordIcon kind="edit" /></button><button aria-label="Show hidden records" title="Show hidden" type="button"><RecordIcon kind="show" /></button><button aria-label="Add note" title="Note" type="button"><RecordIcon kind="note" /></button></div>
            <span className="convention-tag">Icon slot · .entry-page-actions / .record-card-actions — the compact upper-right edit/hide/note buttons (28px squares, RecordIcon)</span>
          </div>
          <div className="convention-row">
            <div className="identity-toolbar"><button className="active" type="button">Full entries</button><button type="button">Compact list</button></div>
            <span className="convention-tag">View toggle · .identity-toolbar button (+ .active) — hover fills accent</span>
          </div>
          <div className="convention-row">
            <button className="secondary-button" type="button"><WandIcon />Draft from selected</button>
            <span className="convention-tag">AI action · any button that triggers a model call leads with the wand icon (.wand-icon) — extraction and drafting buttons alike; no wand, no model</span>
          </div>
          <div className="convention-row">
            <button className="decision-button" type="button">Create entity · .decision-button</button>
            <button className="decision-button outline" type="button">Alias → name · .decision-button.outline</button>
            <span className="convention-tag">Commit/confirm actions · solid accent; outline variant for suggestions</span>
          </div>
          <p className="convention-note">No button ever moves or resizes on hover or click — state changes are color-only (fill, border, or darkened accent).</p>
        </section>

        <section className="convention-group" aria-label="Panels and cards">
          <h3>Panels &amp; cards</h3>
          <article className="identity-full">
            <div className="identity-gap-main"><b>Card · .identity-full</b><span>mono meta line · 28c 28m</span></div>
            <p className="identity-role-hint">Role hint · .identity-role-hint (italic, accent)</p>
            <fieldset className="identity-related"><legend>Merge surfaces · .identity-related</legend><label><input type="checkbox" />Related surface</label></fieldset>
          </article>
          <div className="identity-compact-list">
            <article className="identity-compact-row"><b>Queue panel row · .identity-compact-list / .identity-compact-row</b><span>hover #f8f5ec</span><span className="identity-compact-actions"><button type="button">Create</button><button className="text-button" type="button">Dismiss</button></span></article>
            <article className="identity-compact-row"><b>Second row</b><span>hairline separators · #d9d3c6</span></article>
          </div>
          <div className="convention-row"><div className="notice"><b>Notice · .notice</b><span>warm announcement/error surface</span></div></div>
          <p className="identity-empty">Empty state · .identity-empty (serif, muted)</p>
        </section>

        <section className="convention-group" aria-label="Entry page anatomy">
          <h3>Entry pages</h3>
          <article className="document-view entry-view location-entry">
            <header><b>Location</b><span>Campaign entry</span><div className="entry-page-actions"><button aria-label="Edit entry" title="Edit" type="button"><RecordIcon kind="edit" /></button></div></header>
            <section className="entry-hero"><span>location</span><h1>Entry hero · .entry-hero</h1><dl><div><dt>Location type</dt><dd>building</dd></div><div><dt>Status</dt><dd>seat-of-power</dd></div></dl></section>
            <section className="entry-summary"><p>Entry summary · .entry-summary (intro prose)</p></section>
            <div className="entry-sections"><section className="entry-section"><h2>Entry section · .entry-section</h2><p className="entry-text">Two-column section grid; level-2 sections span both columns.</p></section></div>
            <details className="source-drawer"><summary>Source drawer · .source-drawer</summary></details>
          </article>
        </section>

        <section className="convention-group" aria-label="Forms">
          <h3>Forms</h3>
          <div className="form-grid">
            <label>Label + input · .form-grid label<input readOnly value="1px solid #c8bcac · focus #82533a" /></label>
            <label>Select<select><option>Select · native + styled</option></select></label>
            <label>Aliases (comma-separated · trim on blur)<input readOnly value="The Stars, Court of Stars" /></label>
          </div>
          <div className="step-actions"><button className="text-button" type="button">Cancel · left</button><button className="secondary-button" type="button">Save · right</button></div>
          <p className="convention-note">Actions row · .step-actions — Cancel left, primary right. Alias inputs must never trim per keystroke (space-eating bug).</p>
        </section>

        <section className="convention-group" aria-label="Page header rhythm">
          <h3>Page header</h3>
          <p className="convention-note">Kicker → h2 (Libre Caslon 34px) → right-aligned muted description → border-bottom. Widths: wide pages <code>main.page-documents/.page-migration/.page-identity</code> (max 1600px); reading pages bare <code>main</code> (1080px). Count lines are mono uppercase: “SHOWING 20 OF 129 UNRESOLVED SURFACES”.</p>
        </section>
      </main>
      )}

      <ToastStack />
      <footer className="page-footer"><span>Private campaign workspace</span></footer>
    </div>
  );
}

interface BrainstormNewRecord {
  key: string;
  name: string;
  kind: string;
}

interface BrainstormPromotionDraft {
  included: boolean;
  assertion: string;
  // Subject resolution is load-bearing (ADR-0018 free surfaces): an existing
  // record id, a shared new-record key ("new:r1"), or "" while unresolved.
  // "__new__" opens this row's new-record editor and assigns the next key.
  subjectEntityId: string;
  state: "established" | "intended" | "prepared" | "possible" | "considered";
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
  // Records this promotion will create: keyed once, shareable across drafts.
  const [newRecords, setNewRecords] = useState<BrainstormNewRecord[]>([]);
  const [proposal, setProposal] = useState<CandidateProposalVersion | null>(null);
  const [linkedEntities, setLinkedEntities] = useState<EntityIdentity[]>([]);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionMatches, setMentionMatches] = useState<EntityIdentity[]>([]);
  const [mentionHighlight, setMentionHighlight] = useState(0);
  const [mentionPosition, setMentionPosition] = useState({ left: 12, top: 44 });
  const [search, setSearch] = useState("");
  const [contentEvidence, setContentEvidence] = useState<RetrievalResult["evidence"]>([]);
  const [priorThoughts, setPriorThoughts] = useState<{ text: string; sessionTitle: string; sequence: number }[]>([]);
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
        // CTS default for brainstorm promotion: Considered (ADR-0017 spectrum).
        if (!next[item.candidate_id]) next[item.candidate_id] = { included: false, assertion: item.text.trim(), subjectEntityId: "", state: "considered" };
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
      setPriorThoughts([]);
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
            setContentSearchError(searchError instanceof Error ? searchError.message : "Claim search failed");
          }
        })
        .finally(() => { if (!cancelled) setContentSearchLoading(false); });
      // Search prior brainstorm thoughts (closed sessions) alongside Claims.
      void campaignClient.listSourceDocuments()
        .then(async (page) => {
          if (cancelled) return;
          const brainstormDocs = page.items.filter(
            (doc) => doc.path?.startsWith("gm/brainstorming/direct/"));
          const terms = brainstormSearchTerms(question).map((t) => t);
          if (terms.length === 0) return;
          const matches: { text: string; sessionTitle: string; sequence: number }[] = [];
          for (const doc of brainstormDocs.slice(0, 40)) {
            try {
              const full = await campaignClient.getSourceDocument(doc.document_id);
              const content = full.content ?? "";
              const lower = content.toLocaleLowerCase();
              if (terms.some((term) => lower.includes(term))) {
                matches.push({
                  text: content.length > 300 ? content.slice(0, 300) + "…" : content,
                  sessionTitle: doc.title ?? doc.path?.split("/")[3] ?? "prior session",
                  sequence: 0,
                });
              }
            } catch { /* individual brainstorm doc unavailable — skip */ }
            if (matches.length >= 5) break;
          }
          if (!cancelled) setPriorThoughts(matches);
        })
        .catch(() => { if (!cancelled) setPriorThoughts([]); });
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

  // One-action promotion (ADR-0018): the drafts ARE the reviewed candidates —
  // subjects resolved per row (existing or new records minted in the same
  // commit), states chosen, wording edited. Approve commits everything.
  async function commitPromotion() {
    if (!session) return;
    const selected = session.thoughts.filter((item) => drafts[item.candidate_id]?.included);
    if (!selected.length || selected.some((item) => !drafts[item.candidate_id]?.subjectEntityId)) return;
    setBusy(true); setError("");
    try {
      const promotionKey = `brainstorm-promotion:${session.session_id}:${crypto.randomUUID()}`;
      const receipt = await campaignClient.approveBrainstormPromotion({
        document_text: "brainstorm",
        workflow_session_id: session.session_id,
        statements: selected.map((item) => {
          const draft = drafts[item.candidate_id];
          const newRecord = newRecords.find((record) => `new:${record.key}` === draft.subjectEntityId);
          return {
            span_start: 0, span_end: draft.assertion.trim().length,
            assertion_text: draft.assertion.trim(), state: draft.state, included: true,
            subject: newRecord
              ? { new_record: newRecord.key, name: newRecord.name, entity_kind: newRecord.kind }
              : { entity_id: draft.subjectEntityId },
            candidate_id: item.candidate_id,
            evidence_revision_id: item.source_revision_id,
          };
        }),
        idempotency_key: promotionKey,
      });
      toast.push("success", `Promotion approved — ${receipt.claims_committed} claim${receipt.claims_committed === 1 ? "" : "s"}${receipt.created_entity_ids && receipt.created_entity_ids.length > 0 ? ` + ${receipt.created_entity_ids.length} new record${receipt.created_entity_ids.length === 1 ? "" : "s"}` : ""}`);
      setSession(await campaignClient.closeBrainstorm(session.session_id, receipt.proposal_id ?? ""));
    } catch (promotionError) {
      setError(promotionError instanceof Error ? promotionError.message : "The promotion could not be committed");
      toast.push("error", promotionError instanceof Error ? promotionError.message : "Promotion commit failed");
    } finally { setBusy(false); }
  }

  const latest = session?.thoughts.at(-1);
  const supporting = latest?.evidence.evidence.filter((item) => item.role === "support") ?? [];
  const suggestions = supporting.filter((item) => !(session?.evidence_pins ?? []).some((pin) => pin.record_id === item.record_id));
  const contradictions = latest?.evidence.evidence.filter((item) => item.role === "conflict") ?? [];
  const selectedDrafts = Object.values(drafts).filter((draft) => draft.included);
  const proposalReady = selectedDrafts.length > 0 && selectedDrafts.every((draft) => draft.assertion.trim() && draft.subjectEntityId
    && (draft.subjectEntityId.startsWith("new:")
      ? Boolean(newRecords.find((record) => `new:${record.key}` === draft.subjectEntityId)?.name.trim())
      : true));
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

  if (!session) return <main className="brainstorm-page"><section className="brainstorm-start"><span>Working ideas</span><h1>Start a brainstorm</h1><p>Capture working ideas freely. Thoughts here are Sources — they become Claims with Truth States through reviewed promotion.</p><label>Working title<input aria-label="Brainstorm title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What are you exploring?" /></label><button disabled={busy || !title.trim()} onClick={() => void start()} type="button">Start brainstorm</button>{error && <div className="notice error" role="alert">{error}</div>}</section></main>;

  return (
    <main className="brainstorm-page">
      <header className="brainstorm-heading">
        <div><span>Brainstorm · {session.status}</span><h1>{session.title}</h1><p>Every thought is preserved as a DM-only Source.</p></div>
        {session.thoughts.length > 0 && <b>{session.thoughts.length} thought{session.thoughts.length === 1 ? "" : "s"}</b>}
      </header>
      {error && <div className="notice error" role="alert">{error}</div>}
      <div className="brainstorm-grid">
        <section className="brainstorm-capture" aria-label="Brainstorm thoughts">
          <div className="brainstorm-timeline">
            {session.thoughts.length === 0
              ? <p className="brainstorm-empty">Start with a possibility, question, connection, or consequence you want to explore.</p>
              : session.thoughts.map((item) => <article key={item.thought_id}><span>{item.sequence}</span><p>{item.text}</p><small>Source (not yet parsed into Claims)</small></article>)}
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
            <header><div><span>Optional conclusion</span><h2>Prepare exact promotion</h2></div><p>Select only conclusions you want to consider for promotion. Assign the record each claim is about.</p></header>
            {session.thoughts.map((item) => {
              const draft = drafts[item.candidate_id];
              if (!draft) return null;
              return <article className={draft.included ? "selected" : ""} key={item.candidate_id}>
                <label className="brainstorm-include"><input checked={draft.included} disabled={Boolean(proposal)} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, included: event.target.checked } }))} type="checkbox" />Promote thought {item.sequence}</label>
                {draft.included && <><label>Exact claim<textarea aria-label={`Brainstorm claim ${item.sequence}`} value={draft.assertion} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, assertion: event.target.value } }))} /></label><div><label>Affected record<select aria-label={`Brainstorm target ${item.sequence}`} value={draft.subjectEntityId} onChange={(event) => {
                  const value = event.target.value;
                  if (value === "__new__") {
                    const key = `r${newRecords.length + 1}`;
                    setNewRecords((current) => [...current, { key, name: "", kind: "npc" }]);
                    setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, subjectEntityId: `new:${key}` } }));
                  } else {
                    setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, subjectEntityId: value } }));
                  }
                }}><option value="">Choose a campaign record…</option>{entries.map((entry) => <option key={entry.entry_id} value={entry.entry_id}>{entry.canonical_name} · {display(entry.entity_kind)}</option>)}{newRecords.map((record) => <option key={record.key} value={`new:${record.key}`}>{record.name.trim() ? `${record.name} (new · ${display(record.kind)})` : `New record ${record.key} (unfinished)`}</option>)}<option value="__new__">➕ Create new record…</option></select></label><label>Truth coordinate<select aria-label={`Brainstorm state ${item.sequence}`} value={draft.state} onChange={(event) => setDrafts((current) => ({ ...current, [item.candidate_id]: { ...draft, state: event.target.value as BrainstormPromotionDraft["state"] } }))}><option value="established">Established lore</option><option value="intended">NPC or faction intention</option><option value="prepared">Prepared material</option><option value="possible">Possible</option><option value="considered">Considered</option></select></label></div>{(() => {
                  const record = newRecords.find((candidate) => `new:${candidate.key}` === draft.subjectEntityId);
                  if (!record) return null;
                  return <div className="brainstorm-new-record form-grid">
                    <label>New record name<input aria-label={`New record name ${record.key}`} placeholder="Vault Guild" value={record.name} onChange={(event) => setNewRecords((current) => current.map((candidate) => candidate.key === record.key ? { ...candidate, name: event.target.value } : candidate))} /></label>
                    <label>Kind<select aria-label={`New record kind ${record.key}`} value={record.kind} onChange={(event) => setNewRecords((current) => current.map((candidate) => candidate.key === record.key ? { ...candidate, kind: event.target.value } : candidate))}>{ENTITY_KINDS.filter((kind) => kind.kind !== "pc").map((kind) => <option key={kind.kind} value={kind.kind}>{kind.label}</option>)}</select></label>
                    <small className="ai-activation-note">Minted by this promotion — other thoughts can share it from the record list.</small>
                  </div>;
                })()}</>}
              </article>;
            })}
            {proposal ? <div className="brainstorm-proposal-ready"><b>Immutable proposal version {proposal.version_number} is ready.</b><span>No claim has been approved or applied.</span><button onClick={() => void onReviewProposal(proposal)} type="button">Review exact proposal</button></div> : session.status === "open" && session.thoughts.length > 0 && <button className="decision-button" disabled={busy || !proposalReady} onClick={() => void commitPromotion()} type="button">{busy ? "Committing…" : `Approve promotion · ${selectedDrafts.length} claim${selectedDrafts.length === 1 ? "" : "s"}${newRecords.filter((record) => record.name.trim()).length > 0 ? ` + ${newRecords.filter((record) => record.name.trim()).length} new record${newRecords.filter((record) => record.name.trim()).length === 1 ? "" : "s"}` : ""}`}</button>}
          </section>
        </section>
        <aside className="brainstorm-evidence" aria-label="Grounded continuity evidence">
          <header><span>Continuity panel</span><h2>{latest ? `After thought ${latest.sequence}` : "Campaign context"}</h2><p>Search and pin records without leaving your thought. Nothing here changes established truth without review.</p></header>
          <label className="brainstorm-search"><SearchIcon /><input aria-label="Search campaign during brainstorm" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search names, aliases, tags, or campaign facts…" /></label>
          {searchResults.length > 0 && <section className="brainstorm-search-results"><h3>Records</h3>{searchResults.map((entry) => { const pinned = session.pins.some((pin) => pin.entity_id === entry.entry_id); return <article className="brainstorm-context-card" key={entry.entry_id}><button className="brainstorm-card-main" onClick={() => void openDossier(entry.entry_id)} type="button"><b>{entry.canonical_name}</b><span>{display(entry.entity_kind)}{entry.aliases.length ? ` · ${entry.aliases.join(", ")}` : ""}</span></button><button aria-label={`${pinned ? "Unpin" : "Pin"} ${entry.canonical_name}`} className={pinned ? "pin active" : "pin"} disabled={busy || session.status !== "open"} onClick={() => void togglePin(entry.entry_id)} title={pinned ? "Remove from Brainstorm context" : "Keep in Brainstorm context"} type="button"><PinIcon /></button></article>; })}</section>}
          {contentSearchLoading && <p className="brainstorm-search-status" role="status">Searching canonical content…</p>}
          {contentSearchError && <p className="inline-error" role="alert">Content search failed: {contentSearchError}</p>}
{contentSearchGroups.map(([heading, results]) => results.length > 0 && <section className="brainstorm-content-results" key={heading}><details className="brainstorm-search-category"><summary>{heading}<span>{results.length}</span></summary>{results.map((item) => { const owner = item.entity_id ? entries.find((entry) => entry.entry_id === item.entity_id) : undefined; const ownerName = owner?.canonical_name ?? "canonical record"; const pinned = (session.evidence_pins ?? []).some((pin) => pin.record_id === item.record_id); const expanded = expandedEvidence.has(item.record_id); const excerpt = brainstormEvidenceExcerpt(item.assertion, contentSearchTerms, expanded); return <article className={`brainstorm-canon-card brainstorm-search-card${expanded ? " expanded" : ""}`} key={`search-${item.record_id}`}><div className="brainstorm-search-title" title={`${evidenceTitle(item.citation, entries)}\n${item.citation}`}>{evidenceTitle(item.citation, entries)}</div><button aria-expanded={expanded} aria-label={`${expanded ? "Collapse" : "Expand"} canonical result from ${item.citation}`} className="brainstorm-result-main" onClick={() => setExpandedEvidence((current) => { const next = new Set(current); if (next.has(item.record_id)) next.delete(item.record_id); else next.add(item.record_id); return next; })} type="button"><p>{highlightBrainstormTerms(excerpt, contentSearchTerms)}</p>{heading === "Related discoveries" && <div className="brainstorm-connection"><strong>Connected through</strong>{item.graph_trace?.filter((step) => step.startsWith("Connected through:")).map((step, index) => <span key={index}>{step.replace("Connected through: ", "")}</span>)}<small>Associated names · not an event claim</small></div>}<cite>{item.citation}</cite><span>{expanded ? "Show excerpt" : "Show full text"}</span></button>{heading === "Related discoveries" && Boolean(item.graph_sources?.length) && <details className="brainstorm-connection-sources"><summary>Read connection context</summary>{item.graph_sources!.map((source) => <section key={source.record_id}><p>{source.assertion}</p><cite>{source.citation}</cite></section>)}</details>}<div className="brainstorm-card-actions"><button aria-label={`${expanded ? "Collapse" : "Expand"} search card from ${item.citation}`} aria-expanded={expanded} onClick={() => setExpandedEvidence((current) => { const next = new Set(current); if (next.has(item.record_id)) next.delete(item.record_id); else next.add(item.record_id); return next; })} title={expanded ? "Collapse text" : "Expand full text"} type="button">{expanded ? "−" : "⤢"}</button>{item.entity_id && <button aria-label={`Open ${ownerName}`} onClick={() => void openDossier(item.entity_id!)} title={`Open ${ownerName} dossier`} type="button">↗</button>}<button aria-label={`${pinned ? "Unpin" : "Pin"} search evidence from ${item.citation}`} className={pinned ? "pin active" : "pin"} disabled={busy || session.status !== "open"} onClick={() => void toggleEvidencePin(item.record_id, search)} title={pinned ? "Remove from Brainstorm context" : "Keep in Brainstorm context"} type="button"><PinIcon /></button></div></article>; })}</details></section>)}
          {priorThoughts.length > 0 && <section className="brainstorm-content-results" aria-label="Prior brainstorm thinking"><details className="brainstorm-search-category"><summary>Prior brainstorm thinking<span>{priorThoughts.length}</span></summary>{priorThoughts.map((thought, index) => <article className="brainstorm-canon-card" key={`prior-${index}`}><div className="brainstorm-search-title">{thought.sessionTitle}</div><p>{thought.text}</p><cite>Source — brainstorm thought, not a Claim</cite></article>)}</details></section>}
          {dossierLoading && <p className="brainstorm-empty">Opening campaign record…</p>}
          {dossier && <section className="brainstorm-dossier" aria-label="Brainstorm record dossier"><header><div><span>{display(dossier.entity_kind)}</span><h3>{dossier.canonical_name}</h3></div><button aria-label="Close brainstorm dossier" onClick={() => setDossier(null)} type="button">×</button></header>{dossier.aliases.length > 0 && <p><b>Also known as:</b> {dossier.aliases.join(", ")}</p>}{(dossier.misspellings ?? []).length > 0 && <p><b>Recorded misspellings:</b> {(dossier.misspellings ?? []).join(", ")}</p>}<div>{dossier.claims.length ? dossier.claims.map((claim) => <article key={claim.claim_id}><p>{claim.assertion_text}</p></article>) : <p className="brainstorm-empty">No current claims are recorded.</p>}</div></section>}
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
      <label>Claim<textarea aria-label={`Replacement ${index + 1} claim`} rows={5} value={draft.assertion_text} onChange={(event) => update(index, { assertion_text: event.target.value })} /></label>
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
        <form className="resolution-form" onSubmit={proposePlan}><header><span>New stable plan</span><p>Creation remains at the Considered state until its exact proposal is approved and applied.</p></header><div className="form-grid"><label>Plan kind<select aria-label="Plan kind" value={kind} onChange={(event) => setKind(event.target.value as PlanKind)}>{(kinds.length ? kinds : [{ kind: "campaign_direction", label: "Campaign direction", description: "DM guidance" }, { kind: "in_world_plan", label: "In-world plan", description: "NPC or faction intention" }, { kind: "player_plan", label: "Player plan", description: "Attributed player communication" }]).map((item) => <option key={item.kind} value={item.kind}>{item.label}</option>)}</select></label><label>Canonical name<input aria-label="Plan name" required value={name} onChange={(event) => setName(event.target.value)} /></label></div><p className="kind-guidance">{kinds.find((item) => item.kind === kind)?.description}</p><label>Summary<textarea aria-label="Plan summary" required value={summary} onChange={(event) => setSummary(event.target.value)} /></label>{kind !== "campaign_direction" && <label>Owner record ID<input aria-label="Plan owner record ID" required value={ownerId} onChange={(event) => setOwnerId(event.target.value)} /></label>}{kind === "player_plan" && <div className="form-grid"><label>Player attribution<input aria-label="Player attribution" required value={attribution} onChange={(event) => setAttribution(event.target.value)} /></label><label>Communicated at<input aria-label="Communicated at" required type="datetime-local" value={communicatedAt} onChange={(event) => setCommunicatedAt(event.target.value)} /></label></div>}<label>Evidence source-span IDs<input aria-label="Plan evidence IDs" placeholder="Comma-separated; required for player plans" value={evidenceIds} onChange={(event) => setEvidenceIds(event.target.value)} /></label><label>Related plan IDs<input aria-label="Related plan IDs" placeholder="Comma-separated" value={relatedIds} onChange={(event) => setRelatedIds(event.target.value)} /></label><button disabled={busy || !name.trim() || !summary.trim()} type="submit">Create exact plan proposal</button></form>
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



