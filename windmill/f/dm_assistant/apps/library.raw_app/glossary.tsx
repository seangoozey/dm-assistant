import { useEffect, type ReactNode } from "react";

export interface GlossaryEntry {
  term: string;
  short: string;
  definition: string;
  category: string;
}

export const GLOSSARY_CATEGORIES = [
  "The three layers",
  "Records and truth",
  "Identity",
  "Documents and evidence",
  "Organizations and roles",
  "Workflow and audit",
  "Retrieval and the graph",
] as const;

export const TERMS: Record<string, GlossaryEntry> = {
  "three-layers": {
    term: "The three layers", category: "The three layers",
    short: "Canon lives under the hood; written prose becomes canon; every page you see is assembled from canon.",
    definition: "The app separates what is TRUE from what you SEE. Under the hood sit the claims — complete, auditable, never the default view. Written prose (descriptions, session notes, thoughts) is the bridge: you write it because it reads well, and it becomes canon because you wrote it. Everything displayed is assembled by per-kind templates from those two sources — which is why pages can never contradict the record, and why restyling a page never touches truth.",
  },
  "under-the-hood": {
    term: "Records (under the hood)", category: "The three layers",
    short: "The one consistent way to open the audit view: claims, sources, Truth States, provenance, history.",
    definition: "Every entry exposes the same Records control — same icon, same spot, same label everywhere. It opens the under-the-hood view: the Claims with their Truth States and authorities, the Sources (exact passages), supersession history, and where each fact came from. It exists for the moments you verify — retcon checks, conflict review, 'says who?' — and it is always one deliberate click away, on every page, by design.",
  },
  "life-status": {
    term: "Life status", category: "Records and truth",
    short: "The enumerated alive/dead/undead/resurrected/immortal dimension, set by audited decision.",
    definition: "Life status is a structured canon dimension on a character's profile — alive, dead, undead, resurrected, immortal, or unknown — with the date it changed and the claim that established it. It is set through a receipted decision anchored to that claim (an observed death, a resurrection), never inferred from prose. Conflict detection reads the enum: a dead member still holding a roster seat or leadership surfaces for review mechanically. Immortal marks beings that cannot die: any death claim about them is a retcon question “destroyed their form?”, never a status change.",
  },
  claim: {
    term: "Claim", category: "Records and truth",
    short: "The atomic assertion on which truth is built — every Claim has a Truth State.",
    definition: "A Claim is one assertion about the campaign, recorded with its Source (where it came from), its Truth State (where it sits on the canonical spectrum), and its authority and visibility. A Claim without a Truth State should not exist. Everything the system 'knows' is Claims; Sources are their evidence, and Documents just arrange them for reading.",
  },
  "truth-state": {
    term: "Truth State (CTS)", category: "Records and truth",
    short: "Where a Claim sits on the six-state Canonical Truth State spectrum — from Considered (worked through, blocked) to Observed (witnessed at the table).",
    definition: "The CTS spectrum: Considered means 'I worked through this and found a route that precludes it' — parked, not rejected, findable when the blocker clears. Possible means 'available to happen with no known blockers.' Prepared means 'DM material exists but hasn't been encountered' — you can't un-prepare even if the scenario becomes impossible. Intended means 'a stated plan or goal' — pressure, never prediction. Established means 'confirmed fact of the world.' Observed means 'directly witnessed at the table' — highest authority. Any state can promote to Observed (anything can happen in real play). Direct promotion to Established should be avoided — that's Considered's purpose.",
  },
  source: {
    term: "Source", category: "Documents and evidence",
    short: "The port of entry from which information came — carries provenance.",
    definition: "A Source is where information entered the system: an imported file, a direct-input description, a session note, a brainstorm thought. Sources carry provenance — the exact passage a Claim came from stays immutable. Direct Input Sources record where they were entered (Library, Lore, Brainstorm, Session).",
  },
  attribute: {
    term: "Attribute", category: "Identity",
    short: "An Enumerable or Named field on an Entity: location type, status, race, sex, life status.",
    definition: "Attributes are the structured data fields on an Entity — the enumerable values managed through template vocabularies (location types, statuses, races) and named fields (life status, aliases). They are the Entity's descriptive characteristics, distinct from Kind (which is structural classification, not description).",
  },
  kind: {
    term: "Kind", category: "Identity",
    short: "The structural category of an Entity — determines the Template and organizational rules.",
    definition: "Kind is the Entity's classification: NPC, location, faction, item, event, worldbuilding. It determines which Template arranges the Document and which organizational rules apply (only factions have rosters, for example). Kind is NOT descriptive data about the Identity — descriptive characteristics belong to Attributes.",
  },
  identity: {
    term: "Identity", category: "Identity",
    short: "The person, place, thing, or event being defined — the Entity defines it.",
    definition: "The Identity is the real-world referent: the actual character, place, organization, or event in the campaign. The Entity (the assembled collection of Attributes and Claims) is the system's definition OF that Identity. You edit Entities; what you're really defining is Identities.",
  },
  observed: {
    term: "Observed", category: "Records and truth",
    short: "Directly witnessed at the table — the highest authority about what happened.",
    definition: "Something that actually occurred in play. Real-play observation outranks every other authority: lore, plans and preparation all bend to it, and suspected conflicts with it become retcon checks.",
  },
  established: {
    term: "Established", category: "Records and truth",
    short: "Confirmed fact of the world; the default for lore.",
    definition: "A settled fact that was not directly witnessed at the table — typically imported lore or an accepted statement. Established claims are canon but do not outrank observed play.",
  },
  intended: {
    term: "Intended", category: "Records and truth",
    short: "A stated plan or goal — pressure toward an outcome, never a prediction.",
    definition: "Someone (a player, an NPC, a faction) wants this to happen. Intended claims are plot pressure and opportunity. They never predict what a player character will do, and the world is free to answer them with failure.",
  },
  prepared: {
    term: "Prepared", category: "Records and truth",
    short: "DM preparation that exists in the world but has not been encountered yet.",
    definition: "Content staged behind the screen — an ambush, a letter, a room. It is real once the table touches it; until then it can change freely without contradicting anything.",
  },
  possible: {
    term: "Possible", category: "Records and truth",
    short: "Speculation or branching potential — explicitly not fact.",
    definition: "A maybe. Possibilities record what could be true (often with a condition attached) so the campaign can revisit them, but they assert nothing and never graduate to fact without promotion through review.",
  },
  authority: {
    term: "Authority", category: "Records and truth",
    short: "Where a statement's weight comes from; real play outranks lore.",
    definition: "Every claim carries an authority: real play, explicit lore, NPC intention, preparation, or brainstorm. The ladder resolves arguments — what happened at the table beats what a book said, and plans are never outcomes.",
  },
  visibility: {
    term: "Visibility", category: "Records and truth",
    short: "Who may see a record: DM only, the party, or a specific character.",
    definition: "Records are scoped. Most of this archive is DM-only; party-visible records can be shared at the table; character-scoped records belong to one character's knowledge. Retrieval respects this on every query.",
  },
  supersession: {
    term: "Supersession", category: "Records and truth",
    short: "New claims replace old ones by keeping both and linking them — nothing is silently overwritten.",
    definition: "When a fact changes, the old claim is not deleted: it is marked superseded, with the replacing claim and a reason. That is what makes retcon checks possible — the system can always show what was believed before, and what changed it.",
  },
  "canon-by-receipt": {
    term: "Canon by receipt", category: "Records and truth",
    short: "There is no canon-status field; something is canon because an audited action says so.",
    definition: "The system never stores a 'this is canon' flag. A record is canonical because it came through an audited path — a reviewed promotion, an applied change set, a recorded decision — and the receipt for that action can always be shown. If you want to know why something counts, follow its receipt.",
  },
  entity: {
    term: "Entity", category: "Identity",
    short: "An assembled collection of Attributes and Claims that defines an Identity.",
    definition: "An Entity is the assembled data object: the structured collection of Attributes (enumerable/named fields) and Claims (truth-bearing assertions) that together define an Identity. The Entity is what the system stores and edits; the Identity is the real-world thing being defined. Documents display Entities using Templates.",
  },
  alias: {
    term: "Alias", category: "Identity",
    short: "Another name that resolves to the same identity.",
    definition: "'Inquisition' finds the Inquisitors. Aliases make search and linking forgiving without changing the canonical name. An alias never steals a name another identity owns, and declaring one is an audited decision.",
  },
  misspelling: {
    term: "Misspelling", category: "Identity",
    short: "A recognized misspelling: resolves for search, never shown as a name.",
    definition: "Coreferra misspelled still finds Coreferra — but the correction is displayed as a correction, not quietly absorbed. Misspellings keep discovery working while keeping the record of what was actually written.",
  },
  document: {
    term: "Document", category: "Documents and evidence",
    short: "Text preserved as evidence: imported files, captured notes, thoughts — sources, never conclusions.",
    definition: "Documents are the words a human actually wrote, kept immutable with their history. The system files them, links them, and builds views over them — it never treats a document's text as a conclusion. Everything derived from documents is rebuildable.",
  },
  "direct-input": {
    term: "Direct input", category: "Documents and evidence",
    short: "A document authored inside the app, filed with the same evidence treatment as imports.",
    definition: "Session notes and brainstorm thoughts typed into the app become source documents exactly like imported files — marked by their connector so their origin stays visible. The system never authors evidence; it files what you wrote.",
  },
  description: {
    term: "Entity description", category: "Documents and evidence",
    short: "The page a DM writes for a file-less identity — it becomes that entity's document.",
    definition: "Identities created during review start as claims-only records with synthesized pages. Writing a description gives the entity a real document of its own (authored in-app, connector-marked), which becomes its page. Until then the entry carries the dashed 'no page' marker.",
  },
  provenance: {
    term: "Provenance", category: "Documents and evidence",
    short: "The exact passage a claim came from, kept immutable.",
    definition: "Every claim points back to the specific source span that justifies it. That is the trust model: any canonical statement can answer 'says who, where?' with your own words. Provenance is why sources are never rewritten — only superseded.",
  },
  faction: {
    term: "Faction", category: "Organizations and roles",
    short: "An organization whose membership can change and is worth tracking.",
    definition: "Factions carry rosters, roles, and leadership seats — courts, churches, inquisitions, even the party's own name. The test is app-sense, not dictionary-sense: a fixed collection (the four Oracles) or a class concept (a druid circle) belongs in worldbuilding instead.",
  },
  roster: {
    term: "Roster (membership)", category: "Organizations and roles",
    short: "The audited list of who belongs to a faction; every change is a recorded decision.",
    definition: "Membership is explicit. Adding or removing a member leaves a receipted decision, and once a roster exists, derived co-mention lists never re-enter it. Factions without rosters show their co-mentions clearly labeled as associations — nothing to remove.",
  },
  role: {
    term: "Role", category: "Organizations and roles",
    short: "A titled seat within one faction — 'Grand Inquisitor' exists only in the Inquisitors.",
    definition: "Roles are faction-scoped titles with holders. They can be defined before anyone is seated (a vacant seat), assigned from a member's row or the Roles page, and vacated without removing the member. Role history rides the audited supersession chain.",
  },
  leadership: {
    term: "Leadership (★)", category: "Organizations and roles",
    short: "A role with exactly one holder at a time, marked ★.",
    definition: "A leadership seat is unique within its faction. Seating a second holder is refused by name — succession is always two explicit decisions (clear or change the old holder, then seat the new). The ★ appears wherever the seat appears.",
  },
  title: {
    term: "Title (vs. role)", category: "Organizations and roles",
    short: "An honorific attached to a person by an outside authority — an alias, not a faction seat.",
    definition: "'Herald of Arkin, as decreed by the god' belongs to Coreferra: it names her, conferred from outside, with no organization behind it. Titles live as aliases on the person and their conferral as claims — not as roster machinery.",
  },
  "qualified-entity": {
    term: "Qualified Entity", category: "Records and truth",
    short: "The checkable bar every record must clear: asserted, evidenced, owned — nothing outside the machinery.",
    definition: "An Entity is Qualified when its Identity lives entirely through the declared machinery: at least one current claim (a record with no data at all should not exist), clean ownership of what is about it, a correct Kind, and Attributes that are claim-backed, dated, and vocabulary-backed. Descriptions are polish for reading, not qualification — a record with claims and Attributes and no Description is still Qualified. The bar is binary and computed live; the Migration-to-Seeded campaign crosses it once and then the system never holds an unQualified Entity again.",
  },
  candidate: {
    term: "Candidate", category: "Workflow and audit",
    short: "A statement pulled from a document, waiting for review.",
    definition: "Importers and captures produce candidates — potential claims with their evidence attached. Candidates never become canon by themselves; they wait in the review flow until you decide, word by word.",
  },
  "promotion-pipeline": {
    term: "Promotion Pipeline", category: "Workflow and audit",
    short: "One reusable path from working material to claims: Proposal → Candidate → Approve promotion.",
    definition: "Every surface that turns working material into canon — descriptions, lore, brainstorm — uses the same progression. The system derives candidate claims from your text (with defaults filled in), you scan the list and fix only what is wrong, and one Approve promotion action commits the claims and files the document together in a single receipted transaction. Restatements of gathered claims stay references, never second claims; a conflict flag means the system found a KNOWN conflict with its current detectors — an unflagged statement is not guaranteed contradiction-free, so your read of the list is still the real check.",
  },
  proposal: {
    term: "Proposal", category: "Workflow and audit",
    short: "An exact, versioned draft of a canonical change.",
    definition: "A proposal spells out precisely what will change — every coordinate hashed and reviewable. Approving applies exactly what you read, nothing more. Inspecting one item never approves the rest.",
  },
  "change-set": {
    term: "Change set", category: "Workflow and audit",
    short: "Applied changes committed in one auditable, idempotent transaction.",
    definition: "The change set is the system's only door to canonical mutation: one transaction, one receipt, safely replayable. If any part of a change fails, none of it applies.",
  },
  receipt: {
    term: "Receipt", category: "Workflow and audit",
    short: "Proof of an audited action: what it did, when, under which decision.",
    definition: "Every decision and application leaves a receipt — the id you see in confirmation messages. Receipts are how canon-by-receipt works: trust any record exactly as far as its audited trail.",
  },
  derived: {
    term: "Derived vs. audited", category: "Workflow and audit",
    short: "Computed from text (always labeled) versus decided by you (always receipted).",
    definition: "Derived information — co-mention associations, similarity, graph edges — is computed and clearly labeled; it ranks and suggests but never rules. Audited information exists because you made an explicit decision. When the two disagree, the decision wins.",
  },
  suggestion: {
    term: "Evidence vs. suggestion", category: "Retrieval and the graph",
    short: "Evidence carries provenance; suggestions are discovery aids.",
    definition: "Search results separate direct evidence (records with sources) from related discoveries (associations, graph paths). Suggestions earn their place by being useful to consider — never by implying verified fact.",
  },
  "graph-trace": {
    term: "Graph trace", category: "Retrieval and the graph",
    short: "The explained path behind a related result — associations, not verified facts.",
    definition: "Every graph-connected result shows how it was reached: which name matched, which hops connected, which passage supports the link. The trace is inspectable context — 'these were mentioned together' — not a claim that the relationship is canon.",
  },
  "ai-model-profile": {
    term: "AI model profile", category: "Workflow and audit",
    short: "A controlled model configuration for one purpose, activated by receipt.",
    definition: "Each AI purpose — claim extraction, prose writing — has its own set of model profiles and its own active choice. A profile fixes the provider, model, limits, and timeout; activating one files a receipt, exactly like every other audited decision. The extraction model and the prose model are chosen separately on purpose: the model that reads documents well is not presumed to be the model that writes them.",
  },
  "ai-action-wand": {
    term: "AI action (✨ wand)", category: "Workflow and audit",
    short: "The magic-wand icon marks every button that triggers a model call.",
    definition: "Any button that sends a prompt to an AI model — drafting prose, extracting claims, retrying a failed extraction — leads with the wand icon, so AI involvement is visible before you click, not after. Buttons without the wand never call a model: they file, edit, or navigate records on their own. The wand marks the trigger, not the trust: machine output is always marked machine-drafted and waits for your review.",
  },
  "promotion-assistant": {
    term: "Promotion assistant", category: "Workflow and audit",
    short: "Wand-marked AI suggestions inside promotion review — suggestions, never decisions.",
    definition: "The AI helper behind the Suggest action in the Lore workspace (TKT-0137). It reads the draft prose and the considered evidence and returns three kinds of wand-marked suggestions: restatement matches (which reviewed statements already exist as gathered claims), statement ideas (assertions the new record might establish, each with a suggested Truth State and its basis), and a Link pre-sort (evidence that is really about the new record, not merely context). Agreement coloring follows one rule: green means the system and the AI agree, blue means the deterministic system's value alone, orange means an AI suggestion awaiting your decision. Suggestions arrive excluded, carry their model and prompt version for audit, and never auto-include, gate, or commit — Stage 3 has no AI involvement at all.",
  },
  "dossier": {
    term: "Dossier", category: "Records and truth",
    short: "The DM-curated fact cards on an entry page — promoted one claim at a time.",
    definition: "Any record under the hood can be promoted to an entry's Dossier: a promote icon on the record's row files a receipted decision and the fact appears as a card on the page (each card carries a demote icon to return it under the hood). The Dossier is editorial, never automatic — templates decide how a page looks, the DM decides which facts earn a card. Cards render in the established character-dossier style; the full record set always remains in Records.",
  },
  "drafts-tray": {
    term: "Drafts tray", category: "Workflow and audit",
    short: "The floating tray that holds background AI drafts until you claim or discard them.",
    definition: "Drafting never blocks the app: a Draft request runs as a background job and parks in the Drafts tray (a floating control, bottom-right by default). Entries tick elapsed time while running; a finished draft shows its excerpt and support line (model, time, tokens, cited records) with Return to draft — which loads that entry's composer with the prose and its citations mirrored into the selection — and Discard. Failed drafts stay in the tray with their error until dismissed. Where the tray docks (left, right, or hidden) is managed in Settings under Floating trays, alongside the session notes tray.",
  },
};

type OpenHandler = (term: string) => void;
let openHandler: OpenHandler | null = null;

/** Registered by the app shell so any <Term> can deep-link into Help. */
export function registerGlossaryNavigation(handler: OpenHandler | null): void {
  openHandler = handler;
}

export function Term({ term, children }: { term: string; children?: ReactNode }) {
  const entry = TERMS[term];
  if (!entry) {
    return <span className="term term-unknown" title={`Missing glossary entry: ${term}`}>{children ?? term}</span>;
  }
  return <span className="term" onClick={() => openHandler?.(term)} tabIndex={0}>
    {children ?? entry.term}
    <span className="term-tip" role="tooltip"><b>{entry.term}</b>{entry.short}<small>Click for the full definition in Help</small></span>
  </span>;
}

export function GlossaryHelpPage({ anchor }: { anchor: string | null }) {
  useEffect(() => {
    if (!anchor) return;
    const element = document.getElementById(`glossary-${anchor}`);
    if (element) {
      // jsdom does not implement scrollIntoView; the anchor flash still applies.
      if (typeof element.scrollIntoView === "function") element.scrollIntoView({ block: "center" });
      element.classList.add("glossary-flash");
      const timer = setTimeout(() => element.classList.remove("glossary-flash"), 2400);
      return () => clearTimeout(timer);
    }
  }, [anchor]);
  return <main className="page-help">
    <section className="identity-page-header" aria-label="Help">
      <div className="section-heading"><div><p className="kicker">Reference</p><h2>Help — Campaign Vocabulary</h2></div><p>What the app's words mean, in DM language: what each thing is, what it's for, and how the system uses it. Terms marked in text with a dotted underline show their short definition on hover and open their full entry here on click.</p></div>
    </section>
    {GLOSSARY_CATEGORIES.map((category) => {
      const entries = Object.entries(TERMS).filter(([, entry]) => entry.category === category);
      if (entries.length === 0) return null;
      return <section className="page-panel glossary-group" key={category} aria-label={category}>
        <h3>{category}</h3>
        {entries.map(([key, entry]) => <article className="glossary-entry" id={`glossary-${key}`} key={key}>
          <h4>{entry.term}</h4>
          <p>{entry.definition}</p>
        </article>)}
      </section>;
    })}
  </main>;
}
