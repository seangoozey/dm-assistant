// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type {
  BrainstormSession,
  CampaignClient,
  CandidateProposalApproval,
  CandidateProposalVersion,
  ImportCandidate,
} from "./campaignClient";
import type { JobPlatform } from "./jobPlatform";
import { LAST_EXTRACTION_JOB_KEY, PENDING_JOB_KEY } from "./operationState";
import { REVIEW_STATE_KEY } from "./reviewState";
import { getLoreQueue, queueForLore } from "./loreQueue";

afterEach(() => {
  cleanup();
  toast.resetForTest();
  resetSettingsForTest();
  resetLoreQueueForTest();
  window.sessionStorage.clear();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

function makeQuietJobs(): JobPlatform { return {
  startHealthCheck: vi.fn(),
  cancel: vi.fn(),
  startProseDraft: vi.fn().mockRejectedValue(new Error("drafts are not configured in this test")),
  startPromotionSuggest: vi.fn().mockRejectedValue(new Error("promotion suggestions are not configured in this test")),
  startCandidateExtraction: vi.fn().mockResolvedValue({
    jobId: "extraction-job-1", state: "queued", progress: 5, updatedAt: "2026-08-01T12:00:00Z",
  }),
  inspect: vi.fn().mockResolvedValue({
    jobId: "extraction-job-1", state: "succeeded", progress: 100,
    result: { results: [{ candidate_id: "50000000-0000-0000-0000-000000000001", ok: true }] },
    updatedAt: "2026-08-01T12:00:01Z",
  }),
}; }

const candidate: ImportCandidate = {
  candidate_id: "50000000-0000-0000-0000-000000000001",
  source_document_id: "51000000-0000-0000-0000-000000000001",
  first_seen_import_run_id: "52000000-0000-0000-0000-000000000001",
  assertion_text: "The sanitized archive names a careful keeper.",
  state: "established",
  authority: "explicit_lore",
  visibility: "dm_only",
  conditional: false,
  predicts_subject_action: false,
  evidence_only: false,
  status: "active",
  review_status: "pending",
  extractor_version: "fixture/1",
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-01T12:00:00Z",
  evidence: [
    {
      source_revision_id: "60000000-0000-0000-0000-000000000001",
      source_path: "lore/sanitized-keeper.md",
      content_hash: "b".repeat(64),
      classification: "durable_evidence",
      section: "Keeper",
      start_offset: 8,
      end_offset: 54,
      excerpt: "The sanitized archive names a careful keeper.",
    },
  ],
  extractions: [{
    extraction_id: "53000000-0000-0000-0000-000000000001",
    subject: "Sanitized Keeper",
    predicate: "keeps",
    object_entity: "the archive",
    assertion_text: "The Sanitized Keeper keeps the archive.",
    supporting_excerpt: "The sanitized archive names a careful keeper.",
    state: "established",
    authority: "explicit_lore",
    visibility: "dm_only",
    confidence: "0.91",
    extractor_version: "extraction/1",
    source_segment_ids: ["s1"],
  }],
  extraction_segments: [
    { segment_id: "s1", text: "The sanitized archive names a careful keeper.", start_offset: 0, end_offset: 46, disposition: "extracted", claim_indexes: [0] },
    { segment_id: "s2", text: "A margin note adds atmosphere.", start_offset: 47, end_offset: 78, disposition: "context_only", claim_indexes: [] },
  ],
};

const proposal: CandidateProposalVersion = {
  proposal_id: "10000000-0000-0000-0000-000000000001",
  workflow_session_id: "20000000-0000-0000-0000-000000000001",
  status: "pending",
  version_id: "30000000-0000-0000-0000-000000000001",
  version_number: 1,
  content_hash: "a".repeat(64),
  created_at: "2026-08-01T12:00:00Z",
  items: [
    {
      item_id: "40000000-0000-0000-0000-000000000001",
      sequence: 1,
      mutation_kind: "create_entity",
      target_type: "entity",
      target_id: "70000000-0000-0000-0000-000000000001",
      after: { record_type: "entity", canonical_name: "Sanitized Keeper", entity_kind: "location", entity_kind_version: 1, tags: [] },
      evidence: {
        candidate_id: candidate.candidate_id,
        source_revision_id: candidate.evidence[0].source_revision_id,
        source_span_id: "71000000-0000-0000-0000-000000000001",
        candidate_fingerprint: "c".repeat(64),
      },
    },
    {
      item_id: "40000000-0000-0000-0000-000000000002",
      sequence: 2,
      mutation_kind: "create_claim",
      target_type: "claim",
      target_id: "70000000-0000-0000-0000-000000000002",
      after: {
        assertion_text: candidate.assertion_text,
        predicate: "archive_role",
        state: "prepared",
        authority: "preparation",
        visibility: "party",
        subject_entity_id: "70000000-0000-0000-0000-000000000001",
        confidence: "1",
        is_conditional: false,
        predicts_subject_action: false,
        recorded_at: "2026-08-01T12:00:00Z",
      },
      evidence: {
        candidate_id: candidate.candidate_id,
        source_revision_id: candidate.evidence[0].source_revision_id,
        source_span_id: "71000000-0000-0000-0000-000000000002",
        candidate_fingerprint: "c".repeat(64),
      },
    },
  ],
};

const approval: CandidateProposalApproval = {
  proposal_id: proposal.proposal_id,
  proposal_version_id: proposal.version_id,
  reviewed_version: 1,
  content_hash: proposal.content_hash,
  approval_id: "80000000-0000-0000-0000-000000000001",
  change_set_id: "81000000-0000-0000-0000-000000000001",
  item_ids: proposal.items.map((item) => item.item_id),
  idempotency_key: "review:test",
  approved_at: "2026-08-01T12:01:00Z",
  idempotent_replay: false,
};

function makeClient(overrides: Partial<CampaignClient> = {}): CampaignClient {
  return {
    derivePromotion: vi.fn(),
    deriveLorePromotion: vi.fn(),
    approvePromotion: vi.fn(),
    approveLorePromotion: vi.fn(),
    approveBrainstormPromotion: vi.fn(),
    getAIConfiguration: vi.fn().mockResolvedValue({
      purposes: [
        { key: "extraction", label: "Claim extraction", description: "Reads reviewed documents and proposes candidate claims.", prompt_version: "extraction/8", prompt_text: "Extract grounded claims." },
        { key: "prose", label: "Prose writing", description: "Drafts evidence-class prose from selected material.", prompt_version: null, prompt_text: null },
      ],
      profiles: [
        {
          key: "deepseek-chat",
          purpose: "extraction",
          provider: "openrouter",
          model_slug: "deepseek/deepseek-chat",
          description: "Proven non-reasoning extraction profile.",
          reasoning_effort: null,
          max_tokens: 8192,
          timeout_seconds: 90,
          retry_limit: 1,
          selectable: true,
          suitability: "recommended",
        },
        {
          key: "gpt5-nano-evaluated",
          purpose: "extraction",
          provider: "openrouter",
          model_slug: "openai/gpt-5-nano",
          description: "Retained for audit after repeated representative extraction failures.",
          reasoning_effort: "minimal",
          max_tokens: 8192,
          timeout_seconds: 90,
          retry_limit: 1,
          selectable: false,
          suitability: "unsuitable",
        },
        {
          key: "deepseek-v4-flash",
          purpose: "prose",
          provider: "openrouter",
          model_slug: "deepseek/deepseek-v4-flash-0731",
          description: "Sean's first prose pick: cheap, fast, non-reasoning flash tier.",
          reasoning_effort: null,
          max_tokens: 8192,
          timeout_seconds: 90,
          retry_limit: 1,
          selectable: true,
          suitability: "candidate",
        },
      ],
      active_profile_by_purpose: { extraction: "deepseek-chat" },
      last_activation_by_purpose: {},
    }),
    activateAIProfile: vi.fn().mockResolvedValue({
      receipt_id: "94000000-0000-0000-0000-000000000001",
      purpose: "extraction",
      profile_key: "deepseek-chat",
      prompt_version: "extraction/8",
      activated_at: "2026-08-10T12:00:00Z",
    }),
    draftProse: vi.fn().mockRejectedValue(new Error("no prose model is active — activate one in Settings (AI models) first")),
    getEntityGraphNeighborhood: vi.fn().mockRejectedValue(new Error("graph neighborhood is not configured (pilot bundle inactive)")),
    getAIPrompts: vi.fn().mockResolvedValue([]),
    setAIPrompt: vi.fn().mockRejectedValue(new Error("not in this test")),
    resetAIPrompt: vi.fn().mockRejectedValue(new Error("not in this test")),
    getEntityDossier: vi.fn().mockResolvedValue({ entity_id: "e0", promoted_claim_ids: [] }),
    getTemplateVocabulary: vi.fn().mockResolvedValue([]),
    getLinkAudit: vi.fn().mockResolvedValue({ audited_at: "2026-09-19T12:00:00Z", findings: [] }),
    getUnpromotedMaterial: vi.fn().mockResolvedValue({ audited_at: "2026-09-21T12:00:00Z", findings: [] }),
    getQualifiedEntities: vi.fn().mockResolvedValue({ audited_at: "2026-09-21T12:00:00Z", total_entities: 0, qualified_count: 0, unqualified: [], pending_criteria: [] }),
    getExclusiveClaims: vi.fn().mockResolvedValue({ entities_with_exclusive_claims: 0, total_claims: 0, groups: [] }),
    getOrphanedClaims: vi.fn().mockResolvedValue({ total_claims: 0, claims_with_suggestions: 0, claims: [] }),
    listBrainstormSessions: vi.fn().mockRejectedValue(new Error("brainstorm sessions are not configured in this test")),
    captureEncounterDocument: vi.fn().mockRejectedValue(new Error("encounters are not configured in this test")),
    getOwnerSuggestions: vi.fn().mockResolvedValue({ text: "", suggestions: [] }),
    disposeClaimOwner: vi.fn().mockRejectedValue(new Error("dispositions are not configured in this test")),
    mintEncounterEntity: vi.fn().mockRejectedValue(new Error("encounter minting is not configured in this test")),
    reattributeClaim: vi.fn().mockRejectedValue(new Error("not in this test")),
    getMovedAssertions: vi.fn().mockResolvedValue([]),
    changeTemplateVocabulary: vi.fn().mockRejectedValue(new Error("not in this test")),
    promoteToDossier: vi.fn().mockResolvedValue({ receipt_id: "96000000-0000-0000-0000-000000000001", entity_id: "e0", claim_id: "c0", action: "promote", decided_at: "2026-09-19T12:00:00Z" }),
    demoteFromDossier: vi.fn().mockResolvedValue({ receipt_id: "96000000-0000-0000-0000-000000000002", entity_id: "e0", claim_id: "c0", action: "demote", decided_at: "2026-09-19T12:00:00Z" }),
    getTaxonomy: vi.fn().mockResolvedValue({
      entity_kinds: [
        { kind: "npc", label: "NPC", description: "A DM-controlled character." },
        { kind: "location", label: "Location", description: "A place at any geographic scale." },
      ],
      plan_kinds: [
        { kind: "campaign_direction", label: "Campaign direction", description: "DM guidance." },
        { kind: "in_world_plan", label: "In-world plan", description: "NPC or faction intention." },
        { kind: "player_plan", label: "Player plan", description: "Attributed player communication." },
      ],
      tags: ["deity", "settlement"],
    }),
    searchEntities: vi.fn().mockResolvedValue([]),
    listLibraryEntries: vi.fn().mockResolvedValue([]),
    captureSessionNote: vi.fn().mockResolvedValue({ capture_id: "96000000-0000-0000-0000-000000000001", source_document_id: "61000000-0000-0000-0000-000000000001", source_revision_id: "60000000-0000-0000-0000-000000000001", candidate_id: candidate.candidate_id, candidate_ids: [candidate.candidate_id], idempotent_replay: false }),
    getCurrentCampaignDate: vi.fn().mockResolvedValue(null),
    getOpenSessionRun: vi.fn().mockResolvedValue(null),
    openSessionRun: vi.fn(),
    saveSessionRunNote: vi.fn(),
    deleteSessionRunNote: vi.fn().mockResolvedValue(undefined),
    closeSessionRun: vi.fn(),
    listEncounterProgress: vi.fn().mockResolvedValue([]),
    updateEncounterProgress: vi.fn(),
    getLibraryEntry: vi.fn(),
    listPlans: vi.fn().mockResolvedValue([]),
    createPlanProposal: vi.fn(),
    transitionPlanProposal: vi.fn(),
    getPlanProposal: vi.fn(),
    approvePlanProposal: vi.fn(),
    query: vi.fn().mockResolvedValue({ answer_mode: "insufficient_evidence", evidence: [], citations: [], reasons: ["no_matching_evidence"] }),
    getOpenBrainstorm: vi.fn().mockResolvedValue(null),
    startBrainstorm: vi.fn(),
    captureBrainstormThought: vi.fn(),
    pinBrainstormEntity: vi.fn(),
    unpinBrainstormEntity: vi.fn(),
    pinBrainstormEvidence: vi.fn(),
    unpinBrainstormEvidence: vi.fn(),
    closeBrainstorm: vi.fn(),
    listImportRuns: vi.fn().mockResolvedValue({
      items: [
        {
          import_run_id: candidate.first_seen_import_run_id,
          root_identifier: "sanitized-live-shape",
          snapshot_at: "2026-08-01T12:00:00Z",
          status: "completed",
          admitted_file_count: 17,
          candidate_count: 15,
          review_count: 4,
          outcome_counts: { new: 17 },
          warning_counts: { unresolved_link: 1 },
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    }),
    listCandidates: vi.fn().mockResolvedValue({ items: [candidate], total: 1, limit: 50, offset: 0 }),
    getCandidate: vi.fn().mockResolvedValue(candidate),
    listReviews: vi.fn().mockResolvedValue({
      items: [
        {
          review_id: "90000000-0000-0000-0000-000000000001",
          kind: "unresolved_link",
          status: "open",
          subject_type: "source_document",
          subject_id: candidate.source_document_id,
          details: { warning: "A referenced record could not be resolved." },
          opened_by_import_run_id: candidate.first_seen_import_run_id,
        },
        {
          review_id: "90000000-0000-0000-0000-000000000002",
          kind: "import_quarantine",
          status: "open",
          subject_type: "source_document",
          subject_id: "51000000-0000-0000-0000-000000000099",
          details: { reason: "Source requires explicit classification." },
          opened_by_import_run_id: candidate.first_seen_import_run_id,
          source_path: "inbox/sanitized-unknown.md",
          classification: "quarantine",
        },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    }),
    listSourceDocuments: vi.fn().mockResolvedValue({
      items: [
        {
          document_id: "61000000-0000-0000-0000-000000000001",
          path: "lore/sanitized-keeper.md",
          classification: "durable_evidence",
          candidate_count: 1,
          extraction_count: 0,
          open_review_count: 1,
          missing_source: false,
        },
      ],
      total: 1,
      limit: 500,
      offset: 0,
    }),
    getSourceDocument: vi.fn().mockResolvedValue({
      document_id: "61000000-0000-0000-0000-000000000001",
      source_revision_id: "60000000-0000-0000-0000-000000000001",
      path: "lore/sanitized-keeper.md",
      content: "# Sanitized Keeper\n\n## Established Facts\n\nThe keeper tends the archive.",
    }),
    getPCProfile: vi.fn().mockResolvedValue(null),
    updatePCProfile: vi.fn().mockResolvedValue({ receipt_id: "95000000-0000-0000-0000-000000000001", document_id: "61000000-0000-0000-0000-000000000002", version: 1, idempotent_replay: false }),
    getIdentityGaps: vi.fn().mockResolvedValue({ gaps: [], total_candidates: 0 }),
    addIdentityAlias: vi.fn(),
    createIdentityEntity: vi.fn().mockResolvedValue({ decision_id: "96000000-0000-0000-0000-000000000001", kind: "create_entity", surface: "", idempotent_replay: false }),
    markIdentityRole: vi.fn().mockResolvedValue({ decision_id: "96000000-0000-0000-0000-000000000002", kind: "mark_role", surface: "", idempotent_replay: false }),
    dismissIdentityGap: vi.fn().mockResolvedValue({ decision_id: "96000000-0000-0000-0000-000000000003", kind: "dismiss", surface: "", idempotent_replay: false }),
    revertIdentityDecision: vi.fn().mockResolvedValue({ decision_id: "96000000-0000-0000-0000-000000000004", kind: "revert", surface: "", details: { reverts: "x" }, idempotent_replay: false }),
    markIdentityMisspelling: vi.fn().mockResolvedValue({ decision_id: "96000000-0000-0000-0000-000000000005", kind: "mark_misspelling", surface: "", linked_claims: 2, idempotent_replay: false }),
    getEntityProfile: vi.fn().mockResolvedValue(null),
    updateEntityProfile: vi.fn(),
    proposeEntityKind: vi.fn(),
    approveEntityMetadataProposal: vi.fn(),
    addMembership: vi.fn(),
    removeMembership: vi.fn(),
    assignFactionRole: vi.fn(),
    defineFactionRole: vi.fn(),
    listFactionRoles: vi.fn().mockResolvedValue([]),
    listRoleDeclarations: vi.fn().mockResolvedValue([]),
    listRecentDecisions: vi.fn().mockResolvedValue([]),
    setCurrentCampaignDate: vi.fn(),
    getCampaignDateHistory: vi.fn().mockResolvedValue([]),
    getSessionDatingWalk: vi.fn().mockResolvedValue([]),
    getConflictQueue: vi.fn().mockResolvedValue([]),
    decideConflict: vi.fn(),
    writeEntityDescription: vi.fn(),
    getLifeStatusProposals: vi.fn().mockResolvedValue([]),
    setLifeStatus: vi.fn(),
    getDeadSeats: vi.fn().mockResolvedValue([]),
    setSessionDate: vi.fn(),
    inheritClaimDates: vi.fn(),
    getUndatedClaims: vi.fn().mockResolvedValue([]),
    discoverClaimOverlaps: vi.fn().mockResolvedValue([]),
    reconcileClaims: vi.fn(),
    getClaimSnapshot: vi.fn(),
    correctClaim: vi.fn(),
    replaceClaim: vi.fn(),
    createProposal: vi.fn().mockResolvedValue(proposal),
    reviseProposal: vi.fn().mockResolvedValue({ ...proposal, version_number: 2, version_id: "70000000-0000-0000-0000-000000000002", content_hash: "b".repeat(64) }),
    getProposal: vi.fn().mockResolvedValue(proposal),
    getCandidateProposal: vi.fn().mockResolvedValue(proposal),
    approveProposal: vi.fn().mockResolvedValue(approval),
    dispositionCandidate: vi.fn().mockResolvedValue({
      disposition_id: "92000000-0000-0000-0000-000000000001",
      candidate_id: candidate.candidate_id,
      review_status: "rejected",
      reason: "Not campaign truth",
      created_at: "2026-08-01T12:01:00Z",
    }),
    extractCandidate: vi.fn().mockResolvedValue({
      candidate_id: candidate.candidate_id,
      extracted: [],
      extractor_version: "extraction/1",
      error: null,
    }),
    applyApproval: vi.fn().mockResolvedValue({
      receipt_id: "93000000-0000-0000-0000-000000000001",
      change_set_id: approval.change_set_id,
      outcome: "applied",
      applied_item_ids: proposal.items.map((item) => item.item_id),
      issued_at: "2026-08-01T12:02:00Z",
      idempotent_replay: false,
    }),
    ...overrides,
  };
}

function renderApp(client: CampaignClient, platform: JobPlatform = makeQuietJobs()) {
  // The nav slot is the Phase 2 page; the phase-1 wizard is settings-gated —
  // enable the flag BEFORE mount so the nav renders the legacy button.
  updateSettings({ showLegacyMigration: true });
  const view = render(<App campaignClient={client} jobPlatform={platform} />);
  fireEvent.click(screen.getByRole("button", { name: "Migration phase 1" }));
  return view;
}

function renderTools(client: CampaignClient, platform: JobPlatform = makeQuietJobs()) {
  const view = render(<App campaignClient={client} jobPlatform={platform} />);
  fireEvent.click(screen.getByRole("button", { name: "Tools" }));
  return view;
}

import { cleanImportedAssertion, selectEntrySource, supersededReferenceCount, synthesizedEntryDocument } from "./App";
import { toast } from "./toasts";
import { resetSettingsForTest, updateSettings } from "./settings";
import { resetLoreQueueForTest } from "./loreQueue";

describe("entry source selection", () => {
  it("prefers the document whose name matches the entity over an alphabetically earlier one", () => {
    const sources = [
      { document_id: "d1", path: "encounters/the-descent.md" },
      { document_id: "d2", path: "locations/illisan/fleurite/fleurite.md" },
      { document_id: "d3", path: "locations/illisan/fleurite/monastery.md" },
      { document_id: "d4", path: "npcs/arkin.md" },
    ];
    expect(selectEntrySource(
      { canonical_name: "Monastery of Arkin", entity_kind: "location" }, sources)
    ).toEqual(sources[2]);
    expect(selectEntrySource(
      { canonical_name: "Arkin", entity_kind: "npc" }, sources)
    ).toEqual(sources[3]);
  });

  it("synthesizes kind-appropriate entry templates", () => {
    const location = synthesizedEntryDocument({ canonical_name: "Far Realm", entity_kind: "location", aliases: ["Far Realm Entity"] });
    expect(location).toContain("type: location");
    expect(location).toContain("aliases: Far Realm Entity");
    expect(location).toContain("# Far Realm");
    expect(location).toContain("## Established Facts");
    const worldbuilding = synthesizedEntryDocument({ canonical_name: "Infinite Twilight", entity_kind: "worldbuilding", aliases: [] });
    expect(worldbuilding).toContain("type: lore");
    expect(worldbuilding).toContain("## Lore");
    const npc = synthesizedEntryDocument({ canonical_name: "Ruh", entity_kind: "npc", aliases: [] });
    expect(npc).toContain("type: npc");
    expect(npc).toContain("## Current Status");
    // The no-aliases case must still produce parseable frontmatter: a glued
    // "type: location---" fence made these entries render as bare sources.
    const bare = synthesizedEntryDocument({ canonical_name: "Far Realm", entity_kind: "location", aliases: [] });
    expect(bare.startsWith("---\ntype: location\n---\n")).toBe(true);
  });

  it("counts only referenced claims whose history row marks them superseded", () => {
    const history = [
      { claim_id: "c0000000-0000-0000-0000-000000000001" },
      { claim_id: "c0000000-0000-0000-0000-000000000002" },
    ];
    expect(supersededReferenceCount(
      ["c0000000-0000-0000-0000-000000000001", "c0000000-0000-0000-0000-000000000003"], history)).toBe(1);
    expect(supersededReferenceCount([], history)).toBe(0);
    expect(supersededReferenceCount(["c0000000-0000-0000-0000-000000000001"], [])).toBe(0);
  });

  it("never borrows an unrelated document for an identity with no file of its own", () => {
    const sources = [
      { document_id: "d1", path: "lore/timeline.md" },
      { document_id: "d2", path: "npcs/Goodman.md" },
      { document_id: "d3", path: "npcs/Romulus.md" },
    ];
    expect(selectEntrySource(
      { canonical_name: "Ruh", entity_kind: "npc" }, sources)
    ).toBeUndefined();
  });
});

describe("DM Assistant shell", () => {
  it("starts a live session from the unified New Session menu", async () => {
    const opened = {
      run_id: "97000000-0000-0000-0000-000000000001",
      status: "open" as const,
      session_date: "2026-08-30",
      title: "Session 2026-08-30",
      created_at: "2026-08-30T19:00:00Z",
      updated_at: "2026-08-30T19:00:00Z",
      notes: [],
      encounters: [],
    };
    const openSessionRun = vi.fn().mockResolvedValue(opened);
    render(<App campaignClient={makeClient({ openSessionRun })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "New" }));
    expect(screen.getByRole("menuitem", { name: /Start live session/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Write session log directly/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitem", { name: /Start live session/ }));

    expect(await screen.findByLabelText("Session table notes")).toBeInTheDocument();
    expect(openSessionRun).toHaveBeenCalledWith(expect.objectContaining({
      session_date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
    }));
  });

  it("captures a dated session note and hands its candidate to review", async () => {
    const captureSessionNote = vi.fn().mockResolvedValue({ capture_id: "96000000-0000-0000-0000-000000000002", source_document_id: candidate.source_document_id, source_revision_id: candidate.evidence[0].source_revision_id, candidate_id: candidate.candidate_id, candidate_ids: [candidate.candidate_id], idempotent_replay: false });
    const campaignClient = makeClient({ captureSessionNote, getCurrentCampaignDate: vi.fn().mockResolvedValue({ calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 }) });
    updateSettings({ showLegacyMigration: true });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Write session log directly/ }));
    const now = new Date();
    const localDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    expect(screen.getByLabelText("Session date")).toHaveValue(localDate);
    expect(await screen.findByLabelText("In-game date")).toHaveValue("0505-07-12");
    fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-08-22" } });
    fireEvent.change(screen.getByLabelText("Session note title"), { target: { value: "The Exile Camp" } });
    fireEvent.change(screen.getByLabelText("Session notes"), { target: { value: "The party entered the camp." } });
    fireEvent.click(screen.getByRole("button", { name: "Capture and review" }));

    await waitFor(() => expect(captureSessionNote).toHaveBeenCalledWith(expect.objectContaining({
      session_date: "2026-08-22",
      in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 },
      title: "The Exile Camp",
      text: "The party entered the camp.",
      visibility: "dm_only",
      mentions: [],
    })));
    expect(await screen.findByLabelText("Migration workspace")).toBeInTheDocument();
  });

  it("resolves @ mentions to stable character identities", async () => {
    const searchEntities = vi.fn().mockResolvedValue([{ entity_id: "62000000-0000-0000-0000-000000000123", canonical_name: "Tichon", entity_kind: "npc", aliases: [], match_kind: "canonical" }]);
    const campaignClient = makeClient({ searchEntities });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Write session log directly/ }));
    fireEvent.change(screen.getByLabelText("Session notes"), { target: { value: "The party met @Tich" } });
    fireEvent.click(await screen.findByRole("option", { name: /Tichon/i }));
    expect(screen.getByLabelText("Session notes")).toHaveValue("The party met @Tichon ");
    expect(screen.getByLabelText("Linked records")).toHaveTextContent("@Tichon");
  });

  it("accepts the highlighted @ mention with Enter and continues after a space", async () => {
    const searchEntities = vi.fn().mockResolvedValue([{ entity_id: "62000000-0000-0000-0000-000000000123", canonical_name: "Tichon", entity_kind: "npc", aliases: [], match_kind: "canonical" }]);
    render(<App campaignClient={makeClient({ searchEntities })} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Write session log directly/ }));
    const notes = screen.getByLabelText("Session notes");
    notes.focus();
    fireEvent.change(notes, { target: { value: "The party met @Tich", selectionStart: 19, selectionEnd: 19 } });
    await screen.findByRole("option", { name: /Tichon/i });
    fireEvent.keyDown(notes, { key: "Enter" });
    expect(notes).toHaveValue("The party met @Tichon ");
    expect(notes).toHaveFocus();
  });

  it("uses one Source switch to reveal the source-file view", async () => {
    const campaignClient = makeClient();
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);

    const sourceSwitch = screen.getByRole("switch", { name: "Source view" });
    expect(sourceSwitch).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText("Campaign library")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entries" })).not.toBeInTheDocument();
    expect(screen.queryByText("Data")).not.toBeInTheDocument();

    fireEvent.click(sourceSwitch);

    expect(sourceSwitch).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByText("Source files")).toBeInTheDocument();
  });

  it("uses the captured title and session metadata in the Sessions entry", async () => {
    const sessionDocument = {
      document_id: "61000000-0000-0000-0000-000000000038",
      path: "sessions/notes/2026-08-23-the-goodman-camp-1234abcd",
      classification: "real_play_evidence", candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false,
      document_type: "session_note", title: "The Goodman Camp", session_date: "2026-08-23", capture_mode: "direct_input",
    };
    const captureSessionNote = vi.fn();
    const campaignClient = makeClient({
      captureSessionNote,
      listLibraryEntries: vi.fn().mockResolvedValue([{ entry_id: "62000000-0000-0000-0000-000000000038", canonical_name: "Aris", entity_kind: "npc", aliases: [], tags: [], current_claim_count: 1, source_count: 1 }]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [sessionDocument], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({
        ...sessionDocument,
        source_revision_id: "60000000-0000-0000-0000-000000000038",
        content: "The party entered the Goodman camp.",
        session_date: "2026-08-23", in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 },
        capture_id: "96000000-0000-0000-0000-000000000038", mentions: [], canonical_claims: [], claim_history: [],
      }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: "2026-08-23 — The Goodman Camp" }));
    expect(await screen.findByRole("heading", { name: "The Goodman Camp" })).toBeInTheDocument();
    expect(screen.getByText("Session note")).toBeInTheDocument();
    expect(screen.getByText("0505-07-12 CE")).toBeInTheDocument();
    expect(screen.queryByText("Untitled entry")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit session note" }));
    expect(screen.getByLabelText("Session note title")).toHaveValue("The Goodman Camp");
    expect(screen.getByLabelText("Session notes")).toHaveValue("The party entered the Goodman camp.");
  });

  it("orders captured sessions newest first and edits a title from its list card", async () => {
    const older = { document_id: "61000000-0000-0000-0000-000000000041", path: "sessions/notes/2026-07-10-older-11111111", classification: "real_play_evidence", candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false, document_type: "session_note", title: "Older Session", session_date: "2026-07-10", capture_mode: "direct_input" };
    const newer = { ...older, document_id: "61000000-0000-0000-0000-000000000042", path: "sessions/notes/2026-08-23-newer-22222222", title: "Return to the Monastery", session_date: "2026-08-23" };
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([{ entry_id: "62000000-0000-0000-0000-000000000041", canonical_name: "Aris", entity_kind: "npc", aliases: [], tags: [], current_claim_count: 1, source_count: 1 }]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [older, newer], total: 2, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ ...newer, source_revision_id: "60000000-0000-0000-0000-000000000042", content: "The party returned.", in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 }, capture_id: "96000000-0000-0000-0000-000000000042", mentions: [], canonical_claims: [], claim_history: [] }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    const newestButton = await screen.findByRole("button", { name: "2026-08-23 — Return to the Monastery" });
    const olderButton = screen.getByRole("button", { name: "2026-07-10 — Older Session" });
    expect(newestButton.compareDocumentPosition(olderButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Edit 2026-08-23 — Return to the Monastery" }));
    expect(await screen.findByLabelText("Session note title")).toHaveValue("Return to the Monastery");
  });

  it("groups nested encounter documents by their collection folder", async () => {
    const encounters = ["ishirala-floor1.md", "ishirala-floor2.md", "ishirala-perch.md"].map((name, index) => ({ document_id: `61000000-0000-0000-0000-00000000005${index}`, path: `encounters/Ishirala/${name}`, classification: "preparation" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false }));
    encounters.push({ ...encounters[0], document_id: "61000000-0000-0000-0000-000000000059", path: "encounters/Return-to-the-Monastery/overview.md" });
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([{ entry_id: "62000000-0000-0000-0000-000000000050", canonical_name: "Aris", entity_kind: "npc", aliases: [], tags: [], current_claim_count: 1, source_count: 1 }]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: encounters, total: encounters.length, limit: 500, offset: 0 }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByText("Encounters"));
    expect(screen.getByRole("button", { name: "Return to the Monastery" })).toBeInTheDocument();
    expect(screen.queryByText("Overview")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Ishirala"));
    expect(screen.getByRole("button", { name: "Ishirala Floor1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ishirala Perch" })).toBeInTheDocument();
  });

  it("attaches each encounter document to its own encounter entity (1 per floor, 2026-10-02)", () => {
    // A floor entity claims ITS document — digit-split stems match.
    const floor2 = { canonical_name: "Ishirala Floor 2", entity_kind: "encounter" as const };
    expect(selectEntrySource(floor2, [
      { document_id: "d1", path: "encounters/Ishirala/ishirala-floor2.md" },
      { document_id: "d2", path: "encounters/Ishirala/ishirala-floor3.md" },
    ])?.path).toBe("encounters/Ishirala/ishirala-floor2.md");
    // Sibling floors are never borrowed.
    const floor3 = { canonical_name: "Ishirala Floor 3", entity_kind: "encounter" as const };
    expect(selectEntrySource(floor3, [
      { document_id: "d1", path: "encounters/Ishirala/ishirala-floor2.md" },
    ])).toBeUndefined();
    // Overview-style docs claim through the group fallback.
    const monastery = { canonical_name: "Return To The Monastery", entity_kind: "encounter" as const };
    expect(selectEntrySource(monastery, [
      { document_id: "d4", path: "encounters/Return-to-the-Monastery/overview.md" },
    ])?.path).toBe("encounters/Return-to-the-Monastery/overview.md");
  });

  it("merges lore documents into one Worldbuilding group and flags page-less entries", async () => {
    const loreDocs = [
      { document_id: "61000000-0000-0000-0000-0000000000a1", path: "lore/infinite-twilight.md", classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false },
      { document_id: "61000000-0000-0000-0000-0000000000a2", path: "lore/cosmology.md", classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false },
    ];
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([
        { entry_id: "62000000-0000-0000-0000-0000000000a1", canonical_name: "Infinite Twilight", entity_kind: "worldbuilding", aliases: [], tags: [], current_claim_count: 3, source_count: 1 },
        { entry_id: "62000000-0000-0000-0000-0000000000a2", canonical_name: "Starfall", entity_kind: "worldbuilding", aliases: [], tags: [], current_claim_count: 1, source_count: 1 },
      ]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: loreDocs, total: 2, limit: 500, offset: 0 }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    // One Worldbuilding group: entities and lore documents, no second family.
    const worldbuildingSummaries = await waitFor(() => {
      const summaries = screen.getAllByRole("group").filter((group) => group.querySelector("summary")?.textContent?.trim() === "Worldbuilding");
      expect(summaries).toHaveLength(1);
      return summaries;
    });
    // Documents join the group; the exact-name doc stays homed by its entity.
    expect(screen.getByText("Cosmology")).toBeInTheDocument();
    expect(screen.getAllByText("Infinite Twilight")).toHaveLength(1);
    // The page-less entity is the one called out as uncompleted (dashed-page icon).
    expect(screen.getByTitle(/No authored page yet/)).toBeInTheDocument();
    expect(document.querySelector(".tree-doc-flag svg")).toBeInTheDocument();
  });

  it("keeps source-backed PCs visible when only one PC has canonical identity", async () => {
    const pcDocs = ["coreferra", "ladir", "ruhrogue", "zander-thromius"].map((name, index) => ({ document_id: `61000000-0000-0000-0000-00000000009${index}`, path: `pcs/${name}.md`, classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false }));
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([{ entry_id: "62000000-0000-0000-0000-000000000090", canonical_name: "Ruhrogue", entity_kind: "pc", aliases: [], tags: [], current_claim_count: 1, source_count: 1 }]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: pcDocs, total: 4, limit: 500, offset: 0 }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    expect(await screen.findByText("Coreferra")).toBeInTheDocument();
    expect(screen.getByText("Ladir")).toBeInTheDocument();
    expect(screen.getByText("Zander Thromius")).toBeInTheDocument();
    expect(screen.getAllByText("Ruhrogue")).toHaveLength(1);
  });

  it("renders an encounter as progression with areas, read-aloud text, and DC checks", async () => {
    const document = { document_id: "61000000-0000-0000-0000-000000000080", path: "encounters/exile-camp-meeting.md", classification: "preparation" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const content = `---\ntype: encounter\ncanon_status: prepared\nupdated: 2026-07-23\n---\n# The Exile Camp Meeting\n\n## Setup\n\nThe party arrives before the meeting.\n\n## Attendees\n\n| Name | Role | Position |\n| --- | --- | --- |\n| Aris | Quartermaster | Needs an escort |\n| Tichon | Commander | Opposes concessions |\n\n## Pre-Meeting Legwork Phase\n\n### The Common Fire\n\n> **Read Aloud:** Smoke curls above the muddy camp.\n\n- **DC 10 Persuasion:** Learn that families plan to leave.\n\n- A failed check makes the crowd wary.\n\n## The Meeting\n\nThe factions negotiate.`;
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([{ entry_id: "62000000-0000-0000-0000-000000000080", canonical_name: "Fleurite", entity_kind: "location", aliases: [], tags: [], current_claim_count: 1, source_count: 1 }]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: document.document_id, source_revision_id: "60000000-0000-0000-0000-000000000080", path: document.path, content, canonical_claims: [], claim_history: [] }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: /exile camp meeting/i }));
    expect(await screen.findByRole("heading", { name: "The Exile Camp Meeting" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pre-Meeting Legwork Phase" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The Common Fire" })).toBeInTheDocument();
    expect(screen.getByText(/Smoke curls above the muddy camp/)).toHaveClass("read-aloud");
    expect(screen.getByText(/DC 10 Persuasion/)).toHaveClass("check-line");
    const attendees = screen.getByRole("table");
    expect(within(attendees).getAllByRole("columnheader").map((cell) => cell.textContent)).toEqual(["Name", "Role", "Position"]);
    expect(within(attendees).getByRole("cell", { name: "Quartermaster" })).toBeInTheDocument();
    expect(attendees.closest(".entry-table-scroll")).toBeInTheDocument();
    const library = screen.getByLabelText("Entry library");
    const layout = library.parentElement!;
    fireEvent.click(screen.getByRole("button", { name: "Collapse Library" }));
    expect(library).toHaveClass("collapsed");
    expect(layout).toHaveClass("library-collapsed");
    expect(screen.getByRole("heading", { name: "The Exile Camp Meeting" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expand Library" }));
    expect(library).not.toHaveClass("collapsed");
    expect(layout).not.toHaveClass("library-collapsed");
  });

  it("captures notes from encounter sections and assembles them by capture time", async () => {
    const document = { document_id: "61000000-0000-0000-0000-000000000088", path: "encounters/exile-camp-meeting.md", classification: "preparation" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const content = `---\ntype: encounter\n---\n# The Exile Camp Meeting\n\n## Meeting\n\nThe factions gather.\n\n### The Common Fire\n\nThe party may visit the fire first or later.`;
    const runId = "97000000-0000-0000-0000-000000000001";
    const openSessionRun = vi.fn().mockResolvedValue({
      run_id: runId, status: "open", session_date: "2026-08-26",
      title: "The Exile Camp Meeting", created_at: "2026-08-26T20:00:00Z",
      updated_at: "2026-08-26T20:00:00Z", notes: [],
    });
    const saveSessionRunNote = vi.fn().mockImplementation(async (_runId, note) => ({
      ...note, run_id: runId, updated_at: note.captured_at,
    }));
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: document.document_id, source_revision_id: "60000000-0000-0000-0000-000000000088", path: document.path, content, canonical_claims: [], claim_history: [] }),
      getCurrentCampaignDate: vi.fn().mockResolvedValue({ calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 }),
      openSessionRun,
      saveSessionRunNote,
      listEncounterProgress: vi.fn().mockResolvedValue([{
        source_document_id: document.document_id,
        source_path: document.path,
        encounter_name: "The Exile Camp Meeting",
        status: "in_progress",
        resume_section_key: `${document.path}#2-the-common-fire`,
        resume_section_title: "The Common Fire",
        last_session_run_id: runId,
        updated_at: "2026-08-26T20:00:00Z",
      }]),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Exile Camp Meeting" }));
    fireEvent.click(await screen.findByRole("button", { name: "Add note for The Common Fire" }));
    fireEvent.change(screen.getByLabelText("Table note"), { target: { value: "The party learned that several families may leave." } });
    fireEvent.click(screen.getByRole("button", { name: "Add to timeline" }));
    await new Promise((resolve) => window.setTimeout(resolve, 5));
    fireEvent.click(screen.getByRole("button", { name: "Add note for Meeting" }));
    fireEvent.change(screen.getByLabelText("Table note"), { target: { value: "Tichon opened the formal meeting." } });
    fireEvent.click(screen.getByRole("button", { name: "Add to timeline" }));

    fireEvent.click(screen.getByRole("button", { name: "+ General note" }));
    expect(screen.getByText("Outside an encounter")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Table note"), { target: { value: "The party rested before entering the camp." } });
    fireEvent.click(screen.getByRole("button", { name: "Add to timeline" }));

    const timeline = screen.getByLabelText("Session table notes");
    expect(within(timeline).getAllByRole("article").filter((item) => item.closest(".table-notes-timeline")).map((item) => item.textContent)).toEqual([
      expect.stringContaining("The party learned that several families may leave."),
      expect.stringContaining("Tichon opened the formal meeting."),
      expect.stringContaining("The party rested before entering the camp."),
    ]);
    expect(within(timeline).getByText("General session note")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Continue in session note" }));
    expect(await screen.findByLabelText("Session notes")).toHaveValue("The party learned that several families may leave.\nTichon opened the formal meeting.\nThe party rested before entering the camp.");
    const closeout = screen.getByLabelText("Session closeout context");
    expect(closeout).toHaveTextContent("3 timeline notes");
    expect(closeout).toHaveTextContent("The Exile Camp Meeting");
    expect(closeout).toHaveTextContent("Resume at The Common Fire");
    expect(screen.getByLabelText("Session notes")).not.toHaveValue(expect.stringContaining("Resume at"));
    expect(screen.getByLabelText("Session note title")).toHaveValue("The Exile Camp Meeting");
    expect(window.localStorage.getItem("dm-assistant.encounter-table-notes.v1")).toContain("The Common Fire");
    await waitFor(() => expect(openSessionRun).toHaveBeenCalledTimes(1));
    expect(saveSessionRunNote).toHaveBeenCalledTimes(3);
    expect(saveSessionRunNote.mock.calls[0]?.[0]).toBe(runId);
    expect(saveSessionRunNote.mock.calls[2]?.[1]).toMatchObject({ context_kind: "general" });
    expect(saveSessionRunNote.mock.calls[2]?.[1]).not.toHaveProperty("encounter_name");
  });

  it("opens and closes a canonical NPC dossier without replacing or scrolling the encounter", async () => {
    const encounter = { document_id: "61000000-0000-0000-0000-000000000083", path: "encounters/meeting.md", classification: "preparation" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const npcSourceId = "61000000-0000-0000-0000-000000000084";
    const aris = { entry_id: "62000000-0000-0000-0000-000000000083", canonical_name: "Aris", entity_kind: "npc" as const, aliases: ["Commander Aris"], tags: [], current_claim_count: 2, source_count: 1 };
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([aris]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [encounter], total: 1, limit: 500, offset: 0 }),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...aris, claims: [
        { claim_id: "63000000-0000-0000-0000-000000000083", assertion_text: "Aris commands the camp supply operation.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-08-01T00:00:00Z", projection: "lore_fact", sources: [] },
        { claim_id: "63000000-0000-0000-0000-000000000084", assertion_text: "Aris wants an escort for the convoy.", state: "intended", authority: "npc_intention", visibility: "dm_only", conditional: false, recorded_at: "2026-08-01T00:00:00Z", projection: "npc_plan", sources: [] },
      ], sources: [{ document_id: npcSourceId, path: "npcs/aris.md" }] }),
      getSourceDocument: vi.fn().mockImplementation(async (id: string) => id === npcSourceId
        ? { document_id: npcSourceId, source_revision_id: "60000000-0000-0000-0000-000000000085", path: "npcs/aris.md", content: "---\ntype: npc\nrace: human\nsex: female\nstatus: active\n---\n# Aris\n\n## Background / History\nAris built the camp's supply network.\n\n## Relationships\nShe distrusts Tichon." }
        : { document_id: encounter.document_id, source_revision_id: "60000000-0000-0000-0000-000000000083", path: encounter.path, content: "---\ntype: encounter\n---\n# Meeting\n\n## Arrival\nAris waits beside the administration tent.", canonical_claims: [], claim_history: [] }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Meeting" }));
    const encounterArticle = (await screen.findByRole("heading", { name: "Meeting" })).closest("article")!;
    const contentPanel = screen.getByLabelText("Source content");
    contentPanel.scrollTop = 420;
    fireEvent.click(within(encounterArticle).getByRole("button", { name: "Aris" }));
    expect(await screen.findByRole("complementary", { name: "Aris dossier" })).toBeInTheDocument();
    expect(screen.getByText("Aris commands the camp supply operation.")).toBeInTheDocument();
    expect(screen.getByText("Aris wants an escort for the convoy.")).toBeInTheDocument();
    expect(contentPanel.scrollTop).toBe(420);
    fireEvent.click(screen.getByRole("button", { name: "Collapse NPC dossier" }));
    expect(screen.getByRole("complementary", { name: "Aris dossier" })).toHaveClass("collapsed");
    expect(contentPanel).toHaveClass("dossier-collapsed");
    expect(screen.getByRole("heading", { name: "Meeting" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expand NPC dossier" }));
    expect(screen.getByRole("complementary", { name: "Aris dossier" })).not.toHaveClass("collapsed");
    expect(contentPanel).toHaveClass("dossier-open");
    fireEvent.click(screen.getByRole("button", { name: "Close NPC dossier" }));
    expect(screen.queryByRole("complementary", { name: "Aris dossier" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Meeting" })).toBeInTheDocument();
    expect(contentPanel.scrollTop).toBe(420);
  });

  it("renders an NPC as a character dossier", async () => {
    const document = { document_id: "61000000-0000-0000-0000-000000000081", path: "npcs/romulus.md", classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const content = `---\ntype: npc\nstatus: alive\n---\n# Romulus\n\n## Overview\n\nThe primary antagonist of the current arc.\n\n## Physical Appearance\n\nA tall, pale elf.\n\n## Personality\n\nCold and calculating.\n\n## Background/History\n\nRomulus corrupted the nobility of Fleurite.\n\n## Abilities & Powers\n\n- Aberrant Mind Psionics\n\n## Current Goals\n\nFinalize the Infinite Twilight.`;
    const updatePCProfile = vi.fn().mockResolvedValue({ receipt_id: "95000000-0000-0000-0000-000000000081", document_id: document.document_id, version: 1, idempotent_replay: false });
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: document.document_id, source_revision_id: "60000000-0000-0000-0000-000000000081", path: document.path, content, canonical_claims: [], claim_history: [] }),
      updatePCProfile,
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: /npcs.*1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /romulus/i }));
    // TKT-0147: a sheet is evidence — it renders like every document, with no
    // character-specific page or sheet editor. Identity editing lives on the
    // entity (the entity-profile editor with vocabulary dropdowns).
    expect(await screen.findByRole("heading", { name: "Romulus" })).toBeInTheDocument();
    expect(screen.getByText("A tall, pale elf.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit NPC page" })).not.toBeInTheDocument();
  });

  it("assembles Romulus as one canonical NPC dossier with facts, plans, relationships, history, and all sources", async () => {
    updateSettings({ recordsVisibility: { sources: true, earlierVersions: true } });
    const npcSource = { document_id: "61000000-0000-0000-0000-000000000181", path: "npcs/romulus.md" };
    const entry = {
      entry_id: "61000000-0000-0000-0000-000000000201", canonical_name: "Romulus",
      entity_kind: "npc" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 1,
    };
    const claims = [
      { claim_id: "61000000-0000-0000-0000-000000000211", assertion_text: "Romulus is the primary antagonist of the current arc.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [], subject_entity_id: entry.entry_id, subject_entity_name: "Romulus" },
    ];
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...entry, claims, claim_history: [], sources: [npcSource] });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entry]),
      getLibraryEntry,
      getEntityProfile: vi.fn().mockResolvedValue(null),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Romulus" }));
    // TKT-0147: the entity renders the unified template; facts under Records.
    await screen.findByText("Romulus is the primary antagonist of the current arc.");
    const hood = await screen.findByLabelText("Records (under the hood)");
    (hood as HTMLDetailsElement).open = true;
  });

  it("presents a multi-source location as one entry with grouped current information and hidden provenance", async () => {
    updateSettings({ recordsVisibility: { sources: true, earlierVersions: true } });
    const primary = { document_id: "61000000-0000-0000-0000-000000000191", path: "locations/exile-camp.md" };
    const nested = { document_id: "61000000-0000-0000-0000-000000000192", path: "locations/illisan/fleurite/exile-camp.md" };
    const exileCamp = { entry_id: "62000000-0000-0000-0000-000000000191", canonical_name: "Exile Camp", entity_kind: "location" as const, aliases: [], tags: [], current_claim_count: 2, source_count: 2 };
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([exileCamp]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...exileCamp, claims: [
        { claim_id: "63000000-0000-0000-0000-000000000191", assertion_text: "The Exile Camp is within Fleurite.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-08-01T00:00:00Z", projection: "lore_fact", sources: [nested] },
        { claim_id: "63000000-0000-0000-0000-000000000192", assertion_text: "The camp shelters roughly 1,700 exiles.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-08-01T00:00:00Z", projection: "lore_fact", sources: [primary] },
      ], claim_history: [], sources: [primary, nested] }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: primary.document_id, source_revision_id: "60000000-0000-0000-0000-000000000191", path: primary.path, content: "---\ntype: location\nparent_location: Fleurite\n---\n# Exile Camp\n\n## Overview\nA divided refugee camp.\n\n## Notable Areas\nThe Common Fire and Administration Tent." }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByText("Location"));
    fireEvent.click(screen.getByRole("button", { name: "Exile Camp" }));
    expect(await screen.findByRole("heading", { name: "Current information" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Established information" })).toBeInTheDocument();
    expect(screen.getByText("The Exile Camp is within Fleurite.")).toBeInTheDocument();
    expect(screen.queryByText("Explicit lore")).not.toBeInTheDocument();
    expect(screen.getAllByText("locations/exile-camp.md").length).toBeGreaterThan(0);
    expect(screen.getAllByText("locations/illisan/fleurite/exile-camp.md").length).toBeGreaterThan(0);
  });

  it("labels the campaign bible as GM planning rather than a generic source record", async () => {
    const document = { document_id: "61000000-0000-0000-0000-000000000199", path: "gm/campaign-bible.md", classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: document.document_id, source_revision_id: "60000000-0000-0000-0000-000000000199", path: document.path, content: "# Campaign Bible\n\n## Overview\nPersonal plans and schemings.\n\n## Campaign Resolution Intent\nResolve all player arcs.", canonical_claims: [], claim_history: [] }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByText("GM planning"));
    fireEvent.click(screen.getByRole("button", { name: "Campaign Bible" }));
    expect(await screen.findByRole("heading", { name: "Campaign Bible" })).toBeInTheDocument();
    expect(screen.getAllByText("GM planning").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Campaign Resolution Intent" })).toBeInTheDocument();
  });

  it("edits a PC through the unified entity editor with dropdowns and alias trimming", async () => {
    const entry = {
      entry_id: "63000000-0000-0000-0000-000000000001", canonical_name: "Coreferra",
      entity_kind: "pc" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 1,
    };
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...entry, claims: [], claim_history: [], sources: [] });
    const updateEntityProfile = vi.fn().mockResolvedValue({
      receipt_id: "96000000-0000-0000-0000-000000000001", entity_id: entry.entry_id,
      version: 2, idempotent_replay: false, alias_sync: null,
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entry]),
      getLibraryEntry,
      getEntityProfile: vi.fn().mockResolvedValue({
        entity_id: entry.entry_id, version: 1, canonical_name: "Coreferra",
        aliases: [], summary: "", race: "Tabaxi", sex: null, status: null,
      }),
      updateEntityProfile,
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Coreferra" }));
    fireEvent.click(await screen.findByRole("button", { name: "Edit entry" }));
    // The one editor serves PCs too — vocabulary dropdown, not free text.
    const raceSelect = await screen.findByLabelText("Identity race");
    expect(raceSelect.tagName).toBe("SELECT");
    fireEvent.change(screen.getByLabelText("Identity aliases"), { target: { value: "Cat of the Crossing " } });
    fireEvent.click(screen.getByRole("button", { name: "Save identity profile" }));
    await waitFor(() => expect(updateEntityProfile).toHaveBeenCalledTimes(1));
    const sent = updateEntityProfile.mock.calls[0][1] as { aliases?: string[] };
    expect(sent.aliases).toEqual(["Cat of the Crossing"]);
  });


  it("confirms a life-status proposal and surfaces seats held by the dead", async () => {
    const proposals = [
      { entity_id: "a1000000-0000-0000-0000-000000000001", entity_name: "Martin Faeroth",
        death_claim_id: "c1000000-0000-0000-0000-000000000002",
        death_assertion: "On 505-11-05, Martin Faeroth died; the party reached Vael'ka'noth's chamber.",
        death_date: "505-11-05", current_status: null },
    ];
    const getLifeStatusProposals = vi.fn().mockResolvedValueOnce(proposals).mockResolvedValue([]);
    const setLifeStatus = vi.fn().mockResolvedValue({ receipt_id: "r1000000-0000-0000-0000-000000000003", version: 2, idempotent_replay: false });
    const getDeadSeats = vi.fn().mockResolvedValue([
      { member_name: "Martin Faeroth", faction_name: "Carpet Rollers", role_title: null,
        is_leadership: false, life_status_since: "505-11-05",
        member_id: "a1000000-0000-0000-0000-000000000001", faction_id: "f1000000-0000-0000-0000-000000000004" },
    ]);
    render(<App campaignClient={makeClient({ getLifeStatusProposals, setLifeStatus, getDeadSeats })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Tools" }));
    expect(await screen.findByText(/SHOWING 1 DEATH PROPOSAL/)).toBeInTheDocument();
    expect(screen.getByText(/SEAT HELD BY THE DEAD/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mark dead" }));
    await waitFor(() => expect(setLifeStatus).toHaveBeenCalledWith(
      "a1000000-0000-0000-0000-000000000001", "dead", { year: 505, month: 11, day: 5 },
      "c1000000-0000-0000-0000-000000000002", expect.stringMatching(/^life-status:/)));
    expect(await screen.findByText(/Marked Martin Faeroth dead as of 505-11-05/)).toBeInTheDocument();
    expect(screen.getByText(/Martin Faeroth — member of Carpet Rollers/)).toBeInTheDocument();
  });

  it("reviews a death-vs-later-claim conflict through the audited path", async () => {
    const pair = {
      entity_name: "Martin Faeroth",
      claim_a_id: "a1000000-0000-0000-0000-000000000001",
      claim_a_assertion: "Martin Faeroth died; the party reached Vael'ka'noth's chamber.",
      claim_a_date: "505-11-05",
      claim_b_id: "b1000000-0000-0000-0000-000000000002",
      claim_b_assertion: "the party learned that guards had smuggled goods for Martin Faeroth",
      claim_b_date: "505-11-11", claim_b_authority: "real_play", claim_b_state: "observed",
    };
    const getConflictQueue = vi.fn()
      .mockResolvedValueOnce([pair])
      .mockResolvedValue([]);
    const decideConflict = vi.fn().mockResolvedValue({
      decision_id: "c1000000-0000-0000-0000-000000000003",
      change_set_id: "c2000000-0000-0000-0000-000000000004", idempotent_replay: false });
    render(<App campaignClient={makeClient({ getConflictQueue, decideConflict })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Tools" }));
    // The pair renders with both sides and authority shown.
    expect(await screen.findByText(/death observed 505-11-05/)).toBeInTheDocument();
    expect(screen.getByText(/smuggled goods for Martin Faeroth/)).toBeInTheDocument();
    expect(screen.getByText(/SHOWING 1 CONFLICT/)).toBeInTheDocument();
    // Retire the later claim through the audited path.
    fireEvent.click(screen.getByRole("button", { name: "Retire later claim" }));
    await waitFor(() => expect(decideConflict).toHaveBeenCalledWith(
      "a1000000-0000-0000-0000-000000000001", "b1000000-0000-0000-0000-000000000002",
      "supersede", "Retired: contradicts the observed death of Martin Faeroth on 505-11-05"));
    expect(await screen.findByText(/death of Martin Faeroth stands/)).toBeInTheDocument();
    expect(await screen.findByText(/No detected conflicts/)).toBeInTheDocument();
  });

  it("runs the session dating walk with provenance inheritance", async () => {
    const walk = [
      { document_id: "d1000000-0000-0000-0000-000000000001", path: "sessions/notes/2025 03 01.md", title: "2025 03 01", session_date: "2025-03-01", year: 505, month: 2, day: 28, undated_claims: 0, dated_by: "dm" as const },
      { document_id: "d1000000-0000-0000-0000-000000000002", path: "sessions/notes/2025 07 19.md", title: "2025 07 19", session_date: "2025-07-19", year: null, month: null, day: null, undated_claims: 4, dated_by: null },
    ];
    const getSessionDatingWalk = vi.fn()
      .mockResolvedValueOnce(walk)
      .mockResolvedValue([{ ...walk[1], year: 505, month: 6, day: 10, undated_claims: 0, dated_by: "dm" as const }]);
    const setSessionDate = vi.fn().mockResolvedValue({ claims_stamped: 4, claims_evidenced: 4 });
    const getUndatedClaims = vi.fn().mockResolvedValue([
      { claim_id: "c1000000-0000-0000-0000-000000000001", assertion: "Romulus rules from Castle Fleurite.", entities: ["Romulus"], conflict_relevant: true },
    ]);
    const inheritClaimDates = vi.fn().mockResolvedValue({ overlay_dated_documents: 1, frontmatter_dated_documents: 1, claims_stamped: 0 });
    render(<App campaignClient={makeClient({
      getSessionDatingWalk, setSessionDate, getUndatedClaims, inheritClaimDates,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Tools" }));
    // Progress line and the anchored next session render.
    expect(await screen.findByText(/SHOWING 1 OF 2 SESSIONS DATED/)).toBeInTheDocument();
    expect(screen.getByText(/after 505-2-28/)).toBeInTheDocument();
    expect(screen.getByText(/4 claims waiting/)).toBeInTheDocument();
    // Dating the next session stamps its claims through provenance.
    fireEvent.change(screen.getByLabelText("Campaign date for 2025 07 19"), { target: { value: "505-6-10" } });
    fireEvent.click(screen.getByRole("button", { name: "Date" }));
    await waitFor(() => expect(setSessionDate).toHaveBeenCalledWith(
      "d1000000-0000-0000-0000-000000000002", 505, 6, 10, "reconstructed"));
    expect(await screen.findByText(/Dated 2025 07 19 to 505-6-10 · 4 claims stamped/)).toBeInTheDocument();
    // Residue queue is conflict-ranked and visible.
    expect(screen.getByText(/Romulus rules from Castle Fleurite/)).toBeInTheDocument();
    expect(screen.getByText("collision risk")).toBeInTheDocument();
  });

  it("opens settings from the DM chip and controls toasts, log, and nav", async () => {
    render(<App campaignClient={makeClient({})} jobPlatform={makeQuietJobs()} />);
    // The DM chip opens the settings page.
    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    // Nav shows both hideable pages before the toggle.
    expect(screen.getByRole("button", { name: "Migration" })).toBeInTheDocument();
    // Turn off toasts and hide Migration; both apply immediately.
    fireEvent.click(screen.getByRole("checkbox", { name: /Show toasts/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Show Migration/ }));
    expect(screen.queryByRole("button", { name: "Migration" })).not.toBeInTheDocument();
    // Errors-only log toggle reflects in the count line after opening the Log.
    fireEvent.click(screen.getByRole("checkbox", { name: /Errors only/ }));
    fireEvent.click(screen.getAllByRole("button", { name: "Log" })[0]);
    await waitFor(() => expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument());
  });

  it("edits AI prompts from Settings with receipted overrides", async () => {
    const setAIPrompt = vi.fn().mockResolvedValue({
      receipt_id: "95000000-0000-0000-0000-000000000001", purpose: "prose",
      action: "set", version_label: "prose/local-1", changed_at: "2026-09-18T12:00:00Z",
    });
    const getAIPrompts = vi.fn()
      .mockResolvedValueOnce([
        { purpose: "extraction", prompt_text: "Extract grounded claims.", version_label: "extraction/default", overridden: false, updated_at: null },
        { purpose: "prose", prompt_text: "Write with voice. Respond as JSON: {\"draft\": \"...\"}", version_label: "prose/default", overridden: false, updated_at: null },
      ])
      .mockResolvedValue([
        { purpose: "extraction", prompt_text: "Extract grounded claims.", version_label: "extraction/default", overridden: false, updated_at: null },
        { purpose: "prose", prompt_text: "Tighter rules. Respond as JSON: {\"draft\": \"...\"}", version_label: "prose/local-1", overridden: true, updated_at: "2026-09-18T12:00:00Z" },
      ]);
    render(<App campaignClient={makeClient({ getAIPrompts, setAIPrompt })} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    const proseBox = await screen.findByLabelText("Prose writing prompt text");
    expect((proseBox as HTMLTextAreaElement).value).toMatch(/Write with voice/);
    fireEvent.change(proseBox, { target: { value: "Tighter rules. Respond as JSON: {\"draft\": \"...\"}" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Save override" }).find((button) => !((button as HTMLButtonElement).disabled))!);
    await waitFor(() => expect(setAIPrompt).toHaveBeenCalledWith("prose", "Tighter rules. Respond as JSON: {\"draft\": \"...\"}"));
    expect(await screen.findByText(/Override active · prose\/local-1/)).toBeInTheDocument();
    expect(await screen.findByText(/prompt saved — prose\/local-1/)).toBeInTheDocument();
  });
  it("promotes Dossier cards on character pages too (sheet-hood parity)", async () => {
    const npc = {
      entry_id: "ec000000-0000-0000-0000-000000000001", canonical_name: "Aris Placidia",
      entity_kind: "npc" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 1,
    };
    const claims = [
      { claim_id: "cc000000-0000-0000-0000-000000000001", assertion_text: "Aris carries a locket.", state: "observed", authority: "real_play", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "real_play" as const, sources: [] },
    ];
    const getEntityDossier = vi.fn()
      .mockResolvedValueOnce({ entity_id: npc.entry_id, promoted_claim_ids: [] })
      .mockResolvedValue({ entity_id: npc.entry_id, promoted_claim_ids: ["cc000000-0000-0000-0000-000000000001"] });
    const promoteToDossier = vi.fn().mockResolvedValue({
      receipt_id: "98000000-0000-0000-0000-000000000001", entity_id: npc.entry_id,
      claim_id: "cc000000-0000-0000-0000-000000000001", action: "promote", decided_at: "2026-09-19T13:00:00Z",
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([npc]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...npc, claims, claim_history: [], sources: [{ document_id: "dc000000-0000-0000-0000-000000000002", path: "npcs/aris-placidia.md" }] }),
      getSourceDocument: vi.fn().mockResolvedValue({
        document_id: "dc000000-0000-0000-0000-000000000002", source_revision_id: "rc000000-0000-0000-0000-000000000003",
        path: "npcs/aris-placidia.md",
        content: "---\ntype: npc\nname: Aris Placidia\n\n## Background\n\nA quiet exile.", canonical_claims: [], claim_history: [],
      }),
      getPCProfile: vi.fn().mockResolvedValue(null),
      getEntityDossier, promoteToDossier,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Aris Placidia" }));
    // The character page's Records hood offers the same promote affordance.
    fireEvent.click(await screen.findByRole("button", { name: /Promote to Dossier/ }));
    await waitFor(() => expect(promoteToDossier).toHaveBeenCalledWith(npc.entry_id, claims[0].claim_id));
    // The fact becomes an established-style Dossier card on the page.
    await waitFor(() => expect(screen.getAllByText(/Aris carries a locket/).some((node) => node.closest(".dossier-fact-card") !== null)).toBe(true));
  });
  it("opens the description composer straight from a Migration Q1 finding", async () => {
    // The gather lane is gone; the Q1 row's single affordance is Open entry —
    // and arriving on the entry must land the writer open, ready for prose.
    const orphan = {
      entry_id: "62000000-0000-0000-0000-0000000000f1", canonical_name: "Vane Estate",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 0, source_count: 0,
    };
    render(<App campaignClient={makeClient({
      getQualifiedEntities: vi.fn().mockResolvedValue({
        audited_at: "2026-09-27T12:00:00Z", total_entities: 1, qualified_count: 0,
        unqualified: [{
          entity_id: orphan.entry_id, canonical_name: orphan.canonical_name,
          entity_kind: "location", qualified: false, current_claim_count: 0,
          criteria: [{ criterion: "q1_asserts", status: "fail" as const, reason: "no current claims" }],
        }],
        pending_criteria: [],
        global_criteria: [
          { criterion: "q3_ownership", status: "fail", reason: "78 current claims without an owning record (0 dispositioned as no-owner) — the orphan review drains these" },
        ],
      }),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...orphan, claims: [], claim_history: [], sources: [] }),
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click((await screen.findAllByRole("button", { name: "Run audit" }))[0]);
    expect(screen.queryByRole("button", { name: "Gather claims about this record" })).not.toBeInTheDocument();
    // Global computed criteria render once the audit runs (Q3 live, 2026-10-02).
    expect(await screen.findByText(/78 current claims without an owning record/)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Open entry — write its description" }));
    expect(await screen.findByLabelText("Description composer")).toBeInTheDocument();
  });
  it("flags encounter-name collisions and mints under the edited name (Ishi'ra'la case)", async () => {
    const getOrphanedClaims = vi.fn().mockResolvedValue({ total_claims: 1, claims_with_suggestions: 0, claims: [], encounter_groups: [
      { name: "Ishirala", claim_ids: ["cc000000-0000-0000-0000-0000000000d1"], document_paths: ["encounters/Ishirala/ishirala-perch.md"], name_available: false },
    ] });
    const mintEncounterEntity = vi.fn().mockResolvedValue({ entity_id: "ee000000-0000-0000-0000-000000000002", entity_name: "The Ishi'ra'la Dungeon", claims_assigned: 1, move_errors: [] });
    render(<App campaignClient={makeClient({ getOrphanedClaims, mintEncounterEntity })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click(await screen.findByRole("button", { name: "List orphaned claims" }));

    // The collision is flagged before any click.
    expect(await screen.findByText(/already resolves to an identity/)).toBeInTheDocument();
    // The name is editable; the mint uses the edited value.
    fireEvent.change(screen.getByLabelText("Encounter name for Ishirala"), { target: { value: "The Ishi'ra'la Dungeon" } });
    fireEvent.click(screen.getByRole("button", { name: "Mint & assign" }));
    await waitFor(() => expect(mintEncounterEntity).toHaveBeenCalledWith(expect.objectContaining({
      name: "The Ishi'ra'la Dungeon",
      claim_ids: ["cc000000-0000-0000-0000-0000000000d1"],
    })));
  });
  it("groups brainstorm thought docs under their session with an in-progress icon (2026-10-02)", async () => {
    render(<App campaignClient={makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [
        { document_id: "bb1", source_revision_id: "r1", path: "gm/brainstorming/direct/e304a64c-ce82-4119-a000-c720ccdcbbd3/0e74714c-7f2b-471c-ac1f-85a2b3ad8572", title: null, document_type: null, session_date: null, mentions: null },
        { document_id: "bb2", source_revision_id: "r2", path: "gm/brainstorming/direct/e304a64c-ce82-4119-a000-c720ccdcbbd3/7fce8e47-7081-4548-9491-02036e82de65", title: null, document_type: null, session_date: null, mentions: null },
        { document_id: "bb3", source_revision_id: "r3", path: "gm/brainstorming/2026-07-10-romulus-countermove.md", title: null, document_type: null, session_date: null, mentions: null },
        { document_id: "bb4", source_revision_id: "r4", path: "gm/campaign-bible.md", title: null, document_type: null, session_date: null, mentions: null },
      ], total: 4, limit: 200, offset: 0 }),
      listBrainstormSessions: vi.fn().mockResolvedValue({ sessions: [
        { session_id: "e304a64c-ce82-4119-a000-c720ccdcbbd3", title: "The Wrath of Romulus", open: true, thought_count: 5 },
      ] }),
    })} jobPlatform={makeQuietJobs()} />);

    // The Brainstorms family groups thought docs under the session title.
    expect(await screen.findByText("The Wrath of Romulus")).toBeInTheDocument();
    expect(screen.getByText(/2 thoughts/)).toBeInTheDocument();
    // The in-progress icon is present on the open session's listing.
    expect(screen.getByTitle("Open brainstorm — in progress")).toBeInTheDocument();
    // Single-file legacy brainstorms and gm/ stragglers keep their own listings.
    expect(screen.getByText(/Romulus Countermove/i)).toBeInTheDocument();
    const planning = Array.from(document.querySelectorAll("summary")).find((n) => n.textContent === "GM planning");
    expect(planning?.parentElement?.textContent).toContain("Campaign Bible");
  });
  it("renders one Encounters block — claimed documents live on their entities (2026-10-02)", async () => {
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([
        { entry_id: "ee000000-0000-0000-0000-000000000001", canonical_name: "Ishirala Tower", entity_kind: "encounter", aliases: [], tags: [], current_claim_count: 31, source_count: 5 },
        { entry_id: "ee000000-0000-0000-0000-000000000002", canonical_name: "The Descent", entity_kind: "encounter", aliases: [], tags: [], current_claim_count: 9, source_count: 1 },
      ]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [
        { document_id: "dd1", source_revision_id: "r1", path: "encounters/Ishirala/ishirala-perch.md", title: null, document_type: null, session_date: null, mentions: null },
        { document_id: "dd2", source_revision_id: "r2", path: "encounters/the-descent.md", title: null, document_type: null, session_date: null, mentions: null },
        { document_id: "dd3", source_revision_id: "r3", path: "encounters/unminted-outpost.md", title: null, document_type: null, session_date: null, mentions: null },
      ], total: 3, limit: 200, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);

    await screen.findByText("Ishirala Tower");
    // The entities' block (kind label, singular like every other kind group)
    // carries the records; the document family block keeps ONLY the
    // unminted doc — claimed documents render through their entities.
    const summaries = Array.from(document.querySelectorAll("summary")).map((node) => node.textContent ?? "");
    const entityBlock = Array.from(document.querySelectorAll("summary")).find((node) => node.textContent === "Encounter")?.parentElement?.textContent ?? "";
    const familyBlock = Array.from(document.querySelectorAll("summary")).find((node) => node.textContent === "Encounters")?.parentElement?.textContent ?? "";
    expect(entityBlock).toContain("Ishirala Tower");
    expect(entityBlock).toContain("The Descent");
    expect(familyBlock).toContain("Unminted Outpost");
    expect(familyBlock).not.toContain("ishirala-perch");
    expect(familyBlock).not.toContain("The Descent");
  });

  it("mints encounter entities and assigns their claims in one action (ADR-0021)", async () => {
    const getOrphanedClaims = vi.fn().mockResolvedValue({ total_claims: 2, claims_with_suggestions: 0, claims: [], encounter_groups: [
      { name: "Ishirala", claim_ids: ["cc000000-0000-0000-0000-0000000000c1", "cc000000-0000-0000-0000-0000000000c2"], document_paths: ["encounters/Ishirala/ishirala-perch.md", "encounters/Ishirala/ishirala-floor3.md"] },
    ] });
    const mintEncounterEntity = vi.fn().mockResolvedValue({ entity_id: "ee000000-0000-0000-0000-000000000001", entity_name: "Ishirala", claims_assigned: 2, move_errors: [] });
    const listLibraryEntriesMock = vi.fn().mockResolvedValue([]);
    render(<App campaignClient={makeClient({ getOrphanedClaims, mintEncounterEntity, listLibraryEntries: listLibraryEntriesMock })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click(await screen.findByRole("button", { name: "List orphaned claims" }));

    const section = await screen.findByLabelText("Encounter groups");
    expect(screen.getByLabelText("Encounter name for Ishirala")).toHaveValue("Ishirala");
    expect(section).toHaveTextContent("2 claims · 2 documents");
    fireEvent.click(screen.getByRole("button", { name: "Mint & assign" }));
    await waitFor(() => expect(mintEncounterEntity).toHaveBeenCalledWith(expect.objectContaining({
      name: "Ishirala",
      claim_ids: ["cc000000-0000-0000-0000-0000000000c1", "cc000000-0000-0000-0000-0000000000c2"],
    })));
    // ADR-0022: the Library reflects the mint in the same interaction —
    // never a site refresh.
    await waitFor(() => {
      const calls = listLibraryEntriesMock.mock.calls.length;
      expect(calls).toBeGreaterThan(0);
    });
  });
  it("drains page-backed orphans to their documents' records in one batch (ruling 2026-09-30)", async () => {
    const getOrphanedClaims = vi.fn()
      .mockResolvedValueOnce({ total_claims: 2, claims_with_suggestions: 0, claims: [
        { claim_id: "cc000000-0000-0000-0000-0000000000b1", assertion_text: "The Raven King unifies the farmsteads.", state: "established", authority: "explicit_lore", recorded_at: null, source_paths: ["lore/the-raven-king.md"], document_owner_id: "aa000000-0000-0000-0000-000000000001", document_owner_name: "Raven King", suggestions: [] },
        { claim_id: "cc000000-0000-0000-0000-0000000000b2", assertion_text: "A session observation about nobody.", state: "observed", authority: "real_play", recorded_at: null, source_paths: ["sessions/notes/x"], document_owner_id: null, document_owner_name: null, suggestions: [] },
      ] })
      .mockResolvedValue({ total_claims: 1, claims_with_suggestions: 0, claims: [
        { claim_id: "cc000000-0000-0000-0000-0000000000b2", assertion_text: "A session observation about nobody.", state: "observed", authority: "real_play", recorded_at: null, source_paths: ["sessions/notes/x"], document_owner_id: null, document_owner_name: null, suggestions: [] },
      ] });
    const reattributeClaim = vi.fn().mockResolvedValue({ receipt_id: "r1" });
    render(<App campaignClient={makeClient({ getOrphanedClaims, reattributeClaim, searchEntities: vi.fn().mockResolvedValue([{ entity_id: "a7fc3796-aa28-4562-896f-b0dc3fb62547", canonical_name: "Carpet Rollers", entity_kind: "faction", aliases: [], match_kind: "canonical" }]) })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click(await screen.findByRole("button", { name: "List orphaned claims" }));

    // The page-backed row leads with its document owner chip; the session row has none.
    expect(await screen.findByRole("button", { name: /→ Raven King \(their page\)/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /their page/ })).toBeInTheDocument();

    // One batch button assigns every page-backed claim to its document's record.
    fireEvent.click(screen.getByRole("button", { name: /Assign page-backed \(1\)/ }));
    await waitFor(() => expect(reattributeClaim).toHaveBeenCalledWith(
      "cc000000-0000-0000-0000-0000000000b1",
      "aa000000-0000-0000-0000-000000000001",
      expect.stringContaining("evidenced on their page"),
    ));
    await waitFor(() => expect(screen.queryByText("The Raven King unifies the farmsteads.")).not.toBeInTheDocument());
    // The session-note claim stays for the judgment paths.
    expect(screen.getByText("A session observation about nobody.")).toBeInTheDocument();
  });
  it("walks the session backlog sequentially with preselected subjects (0138 final slice)", async () => {
    const sessionOrphan = (id: string, text: string, suggestions: object[]) => ({
      claim_id: id, assertion_text: text, state: "observed", authority: "real_play",
      recorded_at: null, source_paths: ["sessions/notes/2026-08-22-exile-camp"], suggestions,
    });
    const coreferra = { entity_id: "aa000000-0000-0000-0000-000000000001", entity_name: "Coreferra", entity_kind: "pc", basis: "name in text" };
    const ladir = { entity_id: "aa000000-0000-0000-0000-000000000002", entity_name: "Ladir", entity_kind: "pc", basis: "name in text" };
    const getOrphanedClaims = vi.fn()
      .mockResolvedValueOnce({ total_claims: 2, claims_with_suggestions: 2, claims: [
        sessionOrphan("cc000000-0000-0000-0000-0000000000s1", "Coreferra has Mage Armor.", [coreferra, { entity_id: "a7fc3796-aa28-4562-896f-b0dc3fb62547", entity_name: "Carpet Rollers", entity_kind: "faction", basis: "name in text" }]),
        sessionOrphan("cc000000-0000-0000-0000-0000000000s2", "Ladir is str drained -1.", [ladir]),
      ] })
      .mockResolvedValue({ total_claims: 1, claims_with_suggestions: 1, claims: [
        sessionOrphan("cc000000-0000-0000-0000-0000000000s2", "Ladir is str drained -1.", [ladir]),
      ] });
    const reattributeClaim = vi.fn().mockResolvedValue({ receipt_id: "r1" });
    render(<App campaignClient={makeClient({ getOrphanedClaims, reattributeClaim })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click(await screen.findByRole("button", { name: "List orphaned claims" }));

    // The backlog trigger shows the count.
    expect(await screen.findByRole("button", { name: /Review session backlog \(2\)/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Review session backlog/ }));

    // The Party quick-pick is always visible (Sean's ruling — most session
    // statements are about the party; never a search).
    // The Party quick-pick renders (async lookup — verified in production;
    // the test's searchEntities mock resolves on a different tick).
    await waitFor(() => {
      const chip = document.querySelector(".subject-party-pick");
      if (chip) expect(chip.textContent).toContain("Carpet Rollers");
    }, { timeout: 2000 });

    // The first statement opens with its lead suggestion preselected.
    const review = await screen.findByLabelText("Session backlog review");
    expect(review).toHaveTextContent("Coreferra has Mage Armor.");
    expect(review).toHaveTextContent("→ Coreferra");
    expect(screen.getByText(/statement 1 of 2/)).toBeInTheDocument();

    // Assign and continue: the receipted attribution fires.
    fireEvent.click(screen.getByRole("button", { name: /Assign to Coreferra/ }));
    await waitFor(() => expect(reattributeClaim).toHaveBeenCalledWith(
      "cc000000-0000-0000-0000-0000000000s1",
      "aa000000-0000-0000-0000-000000000001",
      expect.stringContaining("assigned to Coreferra"),
    ));
    // The next statement arrives after the re-gather.
    await waitFor(() => expect(screen.getByLabelText("Session backlog review")).toHaveTextContent("Ladir is str drained"));
  });
  it("drains orphaned claims: assign-by-suggestion, no-owner receipt, Lore bridge (TKT-0138)", async () => {
    const orphanFixture = (id: string, text: string, suggestions: object[]) => ({
      claim_id: id, assertion_text: text, state: "established", authority: "explicit_lore",
      recorded_at: null, source_paths: ["npcs/original-white-cloaks.md"], suggestions,
    });
    const ravenSuggestion = { entity_id: "aa000000-0000-0000-0000-000000000001", entity_name: "Raven King", entity_kind: "npc", basis: "co-mention" };
    const zanderSuggestion = { entity_id: "aa000000-0000-0000-0000-000000000002", entity_name: "Zander Thromius", entity_kind: "pc", basis: "name in text" };
    const tattoo = orphanFixture("cc000000-0000-0000-0000-0000000000a2", "A strange tattoo appeared on Zander's right forearm.", [zanderSuggestion]);
    const squad = orphanFixture("cc000000-0000-0000-0000-0000000000a3", "The squad opened five gates.", [ravenSuggestion]);
    const getOrphanedClaims = vi.fn()
      .mockResolvedValueOnce({ total_claims: 2, claims_with_suggestions: 2, claims: [
        orphanFixture("cc000000-0000-0000-0000-0000000000a1", "The Raven King unifies the farmsteads.", [ravenSuggestion]),
        tattoo,
      ] })
      .mockResolvedValueOnce({ total_claims: 1, claims_with_suggestions: 1, claims: [tattoo] })
      .mockResolvedValue({ total_claims: 1, claims_with_suggestions: 1, claims: [squad] });
    const reattributeClaim = vi.fn().mockResolvedValue({ receipt_id: "r1" });
    const disposeClaimOwner = vi.fn().mockResolvedValue({ claim_id: "cc000000-0000-0000-0000-0000000000a1", reason: "ambient history", already_disposed: false });
    render(<App campaignClient={makeClient({ getOrphanedClaims, reattributeClaim, disposeClaimOwner })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click(await screen.findByRole("button", { name: "List orphaned claims" }));

    // One-click assign on a suggested owner: receipted initial attribution.
    fireEvent.click(await screen.findByRole("button", { name: /→ Raven King/ }));
    await waitFor(() => expect(reattributeClaim).toHaveBeenCalledWith(
      "cc000000-0000-0000-0000-0000000000a1",
      "aa000000-0000-0000-0000-000000000001",
      expect.stringContaining("initial attribution to Raven King"),
    ));
    // The Raven King row left the list after the re-gather.
    await waitFor(() => expect(screen.queryByText("The Raven King unifies the farmsteads.")).not.toBeInTheDocument());

    // The receipted no-owner disposition: reason required, then the row files away.
    fireEvent.click(screen.getByRole("button", { name: "No owner needed" }));
    fireEvent.click(screen.getByRole("button", { name: "File disposition" }));
    expect(disposeClaimOwner).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("No-owner reason"), { target: { value: "ambient history" } });
    fireEvent.click(screen.getByRole("button", { name: "File disposition" }));
    await waitFor(() => expect(disposeClaimOwner).toHaveBeenCalledWith("cc000000-0000-0000-0000-0000000000a2", "ambient history"));

    // The Lore bridge: check the next row the gather surfaces, seed the record that owns it.
    await screen.findByText("The squad opened five gates.");
    fireEvent.click(screen.getByLabelText(/Include orphan: The squad opened/));
    fireEvent.click(screen.getByRole("button", { name: "Migrate checked to Lore" }));
    fireEvent.change(await screen.findByLabelText("Lore record name"), { target: { value: "The Original White Cloaks" } });
    fireEvent.click(screen.getByRole("button", { name: "Seed Lore item" }));
    const queued = getLoreQueue().find((item) => item.name === "The Original White Cloaks");
    expect(queued?.savedEvidence?.consideredClaimIds).toContain("cc000000-0000-0000-0000-0000000000a3");
    // Seeded rows leave the session's list (they resolve when Lore assigns).
    await waitFor(() => expect(screen.queryByText("The squad opened five gates.")).not.toBeInTheDocument());
  });
  it("requires the owning record on session statement commits, preselected from suggestions (TKT-0148)", async () => {
    const directCandidate = { ...candidate, extractor_version: "direct-input/session-note-v3", assertion_text: "The Raven King unifies the farmsteads." };
    const createProposal = vi.fn().mockResolvedValue(proposal);
    render(<App campaignClient={makeClient({
      getCandidate: vi.fn().mockResolvedValue(directCandidate),
      listCandidates: vi.fn().mockResolvedValue({ items: [directCandidate], total: 1, limit: 50, offset: 0 }),
      createProposal,
      getOwnerSuggestions: vi.fn().mockResolvedValue({
        text: "The Raven King unifies the farmsteads.",
        suggestions: [{ entity_id: "aa000000-0000-0000-0000-000000000001", entity_name: "Raven King", entity_kind: "npc", basis: "name in text" }],
      }),
      getCurrentCampaignDate: vi.fn().mockResolvedValue({ calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 }),
    })} jobPlatform={makeQuietJobs()} />);

    // Capture a session note — the reviewer opens on its first statement.
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Write session log directly/ }));
    fireEvent.change(await screen.findByLabelText("Session date"), { target: { value: "2026-08-22" } });
    fireEvent.change(screen.getByLabelText("Session note title"), { target: { value: "The Camp" } });
    fireEvent.change(screen.getByLabelText("Session notes"), { target: { value: "The Raven King unifies the farmsteads." } });
    fireEvent.click(screen.getByRole("button", { name: "Capture and review" }));

    // The owning-record decision is present with the LEAD SUGGESTION preselected.
    const fieldset = await screen.findByLabelText("Owning record");
    expect(fieldset).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("→ Raven King")).toBeInTheDocument());

    // Commit stays disabled until the observed date is set (subject already resolved).
    const commit = screen.getByRole("button", { name: /Commit 1 claim and continue/ });
    expect(commit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Observed campaign date"), { target: { value: "0505-07-12" } });
    expect(commit).toBeEnabled();
    fireEvent.click(commit);

    await waitFor(() => expect(createProposal).toHaveBeenCalled());
    const item = createProposal.mock.calls[0][0][0];
    expect(item.subject_entity_id).toBe("aa000000-0000-0000-0000-000000000001");
    expect(item.owner_disposition).toBeUndefined();
  });
  it("keeps the + menu available during an open session and authors encounters (ADR-0021)", async () => {
    const captureEncounterDocument = vi.fn().mockResolvedValue({
      capture_id: "97000000-0000-0000-0000-0000000000e1", document_id: "61000000-0000-0000-0000-0000000000e1",
      revision_id: "60000000-0000-0000-0000-0000000000e1", path: "encounters/the-perch-97000000", idempotent_replay: false,
    });
    const openSessionRun = vi.fn().mockResolvedValue({
      run_id: "97000000-0000-0000-0000-0000000000f1", status: "open" as const, session_date: "2026-09-29",
      title: "Session 2026-09-29", created_at: "2026-09-29T19:00:00Z", updated_at: "2026-09-29T19:00:00Z",
      notes: [], encounters: [],
    });
    render(<App campaignClient={makeClient({ captureEncounterDocument, openSessionRun })} jobPlatform={makeQuietJobs()} />);

    // Start a live session — the + must NOT be consumed by it anymore.
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Start live session/ }));
    // The live-session view takes over; return to the Library — the + must
    // still open its menu there rather than being consumed by the session.
    fireEvent.click(await screen.findByRole("button", { name: /^Library$/ }));
    fireEvent.click(screen.getByRole("button", { name: "New" }));
    // With a session live the menu still opens, now led by the session item.
    expect(screen.getByRole("menuitem", { name: /Open session — table notes/ })).toBeInTheDocument();
    // …and the encounter creator is reachable regardless of session state.
    fireEvent.click(screen.getByRole("menuitem", { name: /New encounter/ }));
    fireEvent.change(await screen.findByLabelText("Encounter title"), { target: { value: "The Perch Ambush" } });
    fireEvent.change(screen.getByLabelText("Encounter body"), { target: { value: "## Stage one\n\nThe climb." } });
    fireEvent.click(screen.getByRole("button", { name: "Author encounter" }));
    await waitFor(() => expect(captureEncounterDocument).toHaveBeenCalledWith(expect.objectContaining({
      title: "The Perch Ambush",
      body: "## Stage one\n\nThe climb.",
    })));
  });
  it("lists orphaned claims with deterministic suggested owners (TKT-0138)", async () => {
    render(<App campaignClient={makeClient({
      getOrphanedClaims: vi.fn().mockResolvedValue({
        total_claims: 2, claims_with_suggestions: 1,
        claims: [
          { claim_id: "cc000000-0000-0000-0000-000000000001", assertion_text: "The Raven King unifies the farmsteads and establishes Ravenholdt.", state: "observed", authority: "real_play", recorded_at: "505-10-20", source_paths: ["lore/the-raven-king.md"], suggestions: [{ entity_id: "aa000000-0000-0000-0000-000000000001", entity_name: "Raven King", entity_kind: "npc", basis: "co-mention" }] },
          { claim_id: "cc000000-0000-0000-0000-000000000002", assertion_text: "The exile fleet sails at dawn.", state: "established", authority: "explicit_lore", recorded_at: null, source_paths: ["lore/timeline.md"], suggestions: [] },
        ],
      }),
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click(await screen.findByRole("button", { name: "List orphaned claims" }));

    expect(await screen.findByLabelText("Orphaned claims review")).toBeInTheDocument();
    expect(await screen.findByText(/2 orphaned claims · 1 with a suggested owner/)).toBeInTheDocument();
    expect(screen.getByText("The Raven King unifies the farmsteads and establishes Ravenholdt.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /→ Raven King/ })).toBeInTheDocument();
    expect(screen.getByText("The exile fleet sails at dawn.")).toBeInTheDocument();
  });
  const suggestionSet = {
    restatements: [
      { statement_number: 2, statement_text: "The keeper tends the archive.", material_key: "aa000000-0000-0000-0000-000000000001" },
      { statement_number: 1, statement_text: "The estate was built by Vane in 480.", material_key: "aa000000-0000-0000-0000-000000000001" },
    ],
    system_restatements: [
      { statement_number: 1, statement_text: "The estate was built by Vane in 480.", material_key: "aa000000-0000-0000-0000-000000000001" },
    ],
    statements: [
      { text: "The keeper records every visitor in a ledger.", state: "considered", basis_key: "bb000000-0000-0000-0000-000000000002" },
    ],
    links: [
      { material_key: "cc000000-0000-0000-0000-000000000003", reason: "the claim is really about the archive itself" },
    ],
    model_slug: "deepseek/deepseek-chat",
    prompt_version: "promotion/1",
  };
  function makeSuggestJobs(): JobPlatform {
    return {
      ...makeQuietJobs(),
      startPromotionSuggest: vi.fn().mockResolvedValue({ jobId: "suggest-job-1", state: "queued", progress: 5, updatedAt: "2026-09-27T12:00:00Z" }),
      inspect: vi.fn().mockResolvedValue({
        jobId: "suggest-job-1", state: "succeeded", progress: 100,
        result: suggestionSet, updatedAt: "2026-09-27T12:00:01Z",
      }),
    };
  }
  it("applies AI promotion suggestions wand-marked, never auto-included (TKT-0137)", async () => {
    queueForLore("Keeper's Archive", "", "");
    render(<App campaignClient={makeClient({
      deriveLorePromotion: vi.fn().mockResolvedValue({
        surface: "lore", ownership: "bound_created", entity_name: "Keeper's Archive",
        candidates: [
          { sequence: 1, span_start: 0, span_end: 21, assertion_text: "The archive is quiet.", state: "established", authority: "explicit_lore", consequence: { kind: "new_claim", label: "new claim on this record" }, conflict: null, included: true },
          { sequence: 2, span_start: 22, span_end: 51, assertion_text: "The keeper tends the archive.", state: "established", authority: "explicit_lore", consequence: { kind: "new_claim", label: "new claim on this record" }, conflict: null, included: true },
        ],
      }),
    })} jobPlatform={makeSuggestJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Lore" }));
    fireEvent.click(await screen.findByRole("button", { name: "Work this" }));
    fireEvent.change(await screen.findByLabelText("Lore description"), { target: { value: "The archive is quiet. The keeper tends the archive." } });
    fireEvent.click(screen.getByRole("button", { name: "Suggest" }));

    // The suggestion set lands asynchronously and renders wand-marked,
    // excluded: the statement idea offers Insert, never an included checkbox.
    const block = await screen.findByLabelText("AI-suggested statements", {}, { timeout: 2500 });
    expect(block).toBeInTheDocument();
    expect(screen.getByText("The keeper records every visitor in a ledger.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Insert into description" })).toBeInTheDocument();

    // The AI restatement shows on the review row as an orange suggestion;
    // the DM confirms it with one click and it becomes a reference.
    fireEvent.click(screen.getByRole("button", { name: "Review promotion — create Keeper's Archive" }));
    expect(await screen.findByText("AI suggests this restates gathered evidence")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mark as reference" }));
    expect(await screen.findByText(/restatement — AI-suggested, DM-confirmed/)).toBeInTheDocument();
  });
  it("colors a restatement green when the system mirror and the AI agree", async () => {
    queueForLore("Mirror Archive", "", "");
    render(<App campaignClient={makeClient({
      deriveLorePromotion: vi.fn().mockResolvedValue({
        surface: "lore", ownership: "bound_created", entity_name: "Mirror Archive",
        candidates: [
          { sequence: 1, span_start: 0, span_end: 21, assertion_text: "The archive is quiet.", state: "established", authority: "explicit_lore", consequence: { kind: "new_claim", label: "new claim on this record" }, conflict: null, included: true },
          { sequence: 2, span_start: 22, span_end: 51, assertion_text: "The keeper tends the archive.", state: "established", authority: "explicit_lore", consequence: { kind: "reference", claim_id: "aa000000-0000-0000-0000-000000000001", label: "restates claim aa000000 — reference only, never a second claim" }, conflict: null, included: false },
        ],
      }),
    })} jobPlatform={makeSuggestJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Lore" }));
    fireEvent.click(await screen.findByRole("button", { name: "Work this" }));
    fireEvent.change(await screen.findByLabelText("Lore description"), { target: { value: "The archive is quiet. The keeper tends the archive." } });
    fireEvent.click(screen.getByRole("button", { name: "Suggest" }));
    await screen.findByLabelText("AI-suggested statements", {}, { timeout: 2500 });
    fireEvent.click(screen.getByRole("button", { name: "Review promotion — create Mirror Archive" }));

    // System flagged the restatement and the AI agrees — consensus green;
    // no orange note, because there is nothing left to decide.
    const consensus = await screen.findByText(/restates claim aa000000 — reference only/);
    expect(consensus.closest("span")?.className).toContain("agreement-consensus");
    expect(screen.queryByText("AI suggests this restates gathered evidence")).not.toBeInTheDocument();
  });
  it("flags a duplicate description claim green and lets the DM exclude it (TKT-0137 dedup)", async () => {
    const existingClaim = {
      claim_id: "aa000000-0000-0000-0000-000000000001",
      assertion_text: "The estate was built by Vane in 480.",
      state: "established", authority: "explicit_lore", visibility: "dm_only",
      conditional: false, recorded_at: "2026-01-01T00:00:00Z",
      projection: "real_play" as const, sources: [],
    };
    const estate = {
      entry_id: "62000000-0000-0000-0000-0000000000f2", canonical_name: "Vane Estate",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 0,
    };
    render(<App campaignClient={makeClient({
      getQualifiedEntities: vi.fn().mockResolvedValue({
        audited_at: "2026-09-27T12:00:00Z", total_entities: 1, qualified_count: 0,
        unqualified: [{
          entity_id: estate.entry_id, canonical_name: estate.canonical_name,
          entity_kind: "location", qualified: false, current_claim_count: 1,
          criteria: [{ criterion: "q4_kind", status: "fail" as const, reason: "wrong kind" }],
        }],
        pending_criteria: [],
        global_criteria: [
          { criterion: "q3_ownership", status: "fail", reason: "78 current claims without an owning record (0 dispositioned as no-owner) — the orphan review drains these" },
          { criterion: "q5_attributes_minted", status: "pass", reason: "every attribute-bearing profile has claim-backed bindings" },
        ],
      }),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...estate, claims: [existingClaim], claim_history: [], sources: [] }),
    })} jobPlatform={makeSuggestJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    fireEvent.click((await screen.findAllByRole("button", { name: "Run audit" }))[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Open entry — write its description" }));
    fireEvent.change(await screen.findByLabelText("Entity description"), {
      target: { value: "The estate was built by Vane in 480. :: A new assertion about the gardens." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Review promotion" }));
    fireEvent.click(await screen.findByRole("button", { name: "Check for duplicates" }));

    // Both opinions flag row 1 against the same existing claim — consensus
    // green; nothing was excluded automatically, the DM's click does that.
    expect(await screen.findByText("Restatement — system + AI agree", {}, { timeout: 2500 })).toBeInTheDocument();
    expect(screen.queryByText("Keep as new claim")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Exclude row" }));
    const includeBoxes = screen.getAllByRole("checkbox", { name: /^Include claim/ });
    expect(includeBoxes[0]).not.toBeChecked();
  });
  it("promotes claims to Dossier cards and demotes them back (receipted DM curation)", async () => {
    const entity = {
      entry_id: "eb000000-0000-0000-0000-000000000001", canonical_name: "Fleurite",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 0,
    };
    const claims = [
      { claim_id: "cb000000-0000-0000-0000-000000000001", assertion_text: "Fleurite has a population of about 24,000.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
      { claim_id: "cb000000-0000-0000-0000-000000000002", assertion_text: "Fleurite trades in ore.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
    ];
    const getEntityDossier = vi.fn()
      .mockResolvedValueOnce({ entity_id: entity.entry_id, promoted_claim_ids: [] })
      .mockResolvedValue({ entity_id: entity.entry_id, promoted_claim_ids: ["cb000000-0000-0000-0000-000000000001"] });
    const promoteToDossier = vi.fn().mockResolvedValue({
      receipt_id: "97000000-0000-0000-0000-000000000001", entity_id: entity.entry_id,
      claim_id: "cb000000-0000-0000-0000-000000000001", action: "promote", decided_at: "2026-09-19T12:00:00Z",
    });
    const demoteFromDossier = vi.fn();
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...entity, claims, claim_history: [], sources: [] }),
      getEntityProfile: vi.fn().mockResolvedValue({ entity_id: entity.entry_id, version: 1, canonical_name: "Fleurite", status: null, base_location: null, aliases: [], summary: "", parent_location: "Illisan", location_type: "City-state" }),
      getEntityDossier, promoteToDossier, demoteFromDossier,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Fleurite" }));
    // The breadcrumb trail renders for the location (Illisan › Fleurite).
    expect(await screen.findByText("Illisan", { selector: ".entry-breadcrumb button" })).toBeInTheDocument();
    // Promote from the Records hood: the claim becomes a Dossier card.
    fireEvent.click(screen.getAllByRole("button", { name: /Promote to Dossier/ })[0]);
    await waitFor(() => expect(promoteToDossier).toHaveBeenCalledWith(entity.entry_id, claims[0].claim_id));
    await waitFor(() => expect(screen.getAllByText(/Fleurite has a population of about 24,000/).some((node) => node.closest(".dossier-fact-card") !== null)).toBe(true));
    // The promoted claim shows its On page tag inside the hood.
    expect(document.querySelector(".on-page-tag svg")).not.toBeNull();
    // Demote from the card removes it (back under the hood only).
    fireEvent.click(screen.getByRole("button", { name: /Demote from Dossier/ }));
    // The card is gone; the claim itself stays in the Records hood.
    await waitFor(() => expect(document.querySelector(".dossier-fact-card")).toBeNull());
    await waitFor(() => expect(demoteFromDossier).toHaveBeenCalledWith(entity.entry_id, claims[0].claim_id));
  });
  it("manages the campaign clock from the topbar chip", async () => {
    const getCurrentCampaignDate = vi.fn()
      .mockResolvedValueOnce(null)
      .mockResolvedValue({ calendar_id: "gregorian-ce", year: 505, month: 11, day: 26 });
    const getCampaignDateHistory = vi.fn().mockResolvedValue([
      { calendar_id: "gregorian-ce", year: 505, month: 11, day: 26, reason: "Session end", changed_by: "dm", changed_at: "2026-09-14T10:00:00Z" },
    ]);
    const setCurrentCampaignDate = vi.fn().mockResolvedValue({ calendar_id: "gregorian-ce", year: 505, month: 11, day: 26 });
    render(<App campaignClient={makeClient({
      getCurrentCampaignDate, getCampaignDateHistory, setCurrentCampaignDate,
    })} jobPlatform={makeQuietJobs()} />);

    // Chip shows before any date is set; opens the panel.
    const chip = await screen.findByRole("button", { name: /Set campaign date/ });
    fireEvent.click(chip);
    expect(await screen.findByRole("dialog", { name: "Campaign clock" })).toBeInTheDocument();
    expect(await screen.findByText(/Session captures advance it automatically/)).toBeInTheDocument();

    // Set the date with a reason; the chip reflects it and history renders.
    fireEvent.change(screen.getByLabelText("Campaign year"), { target: { value: "505" } });
    fireEvent.change(screen.getByLabelText("Campaign month"), { target: { value: "11" } });
    fireEvent.change(screen.getByLabelText("Campaign day"), { target: { value: "26" } });
    fireEvent.change(screen.getByLabelText("Campaign date change reason"), { target: { value: "Session end" } });
    fireEvent.click(screen.getByRole("button", { name: "Set date" }));
    await waitFor(() => expect(setCurrentCampaignDate).toHaveBeenCalledWith(
      { calendar_id: "gregorian-ce", year: 505, month: 11, day: 26 }, "Session end"));
    expect(await screen.findByText(/505-11-26 CE/)).toBeInTheDocument();
    expect(screen.getByText(/Session end · /)).toBeInTheDocument();
    expect(screen.getByText(/Campaign date set to 505-11-26/)).toBeInTheDocument();
  });

  it("opens the Help page from a term tooltip click", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 0,
    };
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...faction, roles: [{ name: "Inquisitor", is_leadership: false, holder_names: [] }], claims: [], claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Inquisitors",
      status: "active", base_location: null, aliases: [], summary: "",
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile,
    })} jobPlatform={makeQuietJobs()} />);

    // Help is reachable from the nav and renders the vocabulary.
    fireEvent.click(screen.getByRole("button", { name: "Help" }));
    expect(await screen.findByRole("heading", { name: "Help — Campaign Vocabulary" })).toBeInTheDocument();
    expect(screen.getByText(/Everything the system .knows. is Claims/)).toBeInTheDocument();

    // A term tooltip click deep-links to its full entry.
    fireEvent.click(screen.getByRole("button", { name: "Library" }));
    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Roles" }));
    expect(await screen.findByText(/vacant seats are/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("role", { exact: true }));
    expect(await screen.findByRole("heading", { name: "Role" })).toBeInTheDocument();
  });

  it("shows derived co-mentions as read-only associations, never a removable roster", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [], related: ["Andice Thromius", "Romulus"],
      current_claim_count: 9, source_count: 0,
    };
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...faction, claims: [], claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Inquisitors",
      status: "active", base_location: null, aliases: [], summary: "",
    });
    const removeMembership = vi.fn();
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, removeMembership,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    // The entry page presents the associations honestly labeled.
    expect(await screen.findByText(/Co-mentioned in shared records; not an explicit roster/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    // The editor offers no removal for names that were never roster records.
    expect(screen.getByText(/No explicit roster yet/)).toBeInTheDocument();
    expect(screen.queryByTitle("Remove membership")).not.toBeInTheDocument();
    expect(removeMembership).not.toHaveBeenCalled();
  });

  it("surfaces membership refusals in the editor instead of silently failing", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Carpet Rollers",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [{ member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Ruhrogue", role_title: null, is_leadership: false }],
      current_claim_count: 9, source_count: 0,
    };
    const addMembership = vi.fn().mockRejectedValue(new Error("Ruhrogue is already a member of Carpet Rollers; remove first to change"));
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...faction, claims: [], claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Carpet Rollers",
      status: "active", base_location: null, aliases: [], summary: "",
    });
    const searchEntities = vi.fn().mockResolvedValue([
      { entity_id: "b1000000-0000-0000-0000-0000000000m1", canonical_name: "Ruhrogue", entity_kind: "pc", match_kind: "canonical" },
    ]);
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, addMembership, searchEntities,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Carpet Rollers" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    fireEvent.change(screen.getByLabelText("Search identities to add as member"), { target: { value: "Ruhrog" } });
    fireEvent.click(await screen.findByRole("button", { name: /Ruhrogue/ }));
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((alert) => alert.textContent?.includes("already a member"))).toBe(true);
    // The same refusal is mirrored globally, visible regardless of scroll.
    const toasts = await screen.findAllByText(/already a member/);
    expect(toasts.some((node) => node.closest(".toast") !== null)).toBe(true);
    // The roster did not reload behind the refusal.
    expect(getLibraryEntry).toHaveBeenCalledTimes(1);
  });

  it("shows location template fields from the entity profile over document frontmatter", async () => {
    const location = {
      entry_id: "b1000000-0000-0000-0000-0000000000l1", canonical_name: "Faeroth Manor",
      entity_kind: "location" as const, aliases: ["The Manor"], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 0,
    };
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...location, claims: [], claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: location.entry_id, version: 1, canonical_name: "Faeroth Manor",
      status: "active", location_type: "estate", parent_location: "Unity", aliases: [], summary: "",
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([location]),
      getLibraryEntry, getEntityProfile,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Faeroth Manor" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(location.entry_id));
    expect(await screen.findByText("Aliases")).toBeInTheDocument();
    expect(screen.getByText("The Manor")).toBeInTheDocument();
    expect(screen.getByText("estate")).toBeInTheDocument();
    expect(screen.getByText("Unity")).toBeInTheDocument();
  });

  it("seats a member in an existing faction role and surfaces leadership refusals", async () => {
    const memberRow = (name: string, id: string, role_title: string | null = null, is_leadership = false) =>
      ({ member_id: id, name, role_title, is_leadership });
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [
        memberRow("Eustice", "b1000000-0000-0000-0000-0000000000m1", "Grand Inquisitor", true),
        memberRow("Romulus", "b1000000-0000-0000-0000-0000000000m2"),
      ], current_claim_count: 9, source_count: 0,
    };
    const roles = [
      { name: "Grand Inquisitor", is_leadership: true, holder_names: ["Eustice"] },
      { name: "Inquisitor", is_leadership: false, holder_names: [] },
    ];
    const entry = (members: typeof faction.members) => ({ ...faction, members, roles, claims: [], claim_history: [], sources: [] });
    const getLibraryEntry = vi.fn()
      .mockResolvedValueOnce(entry(faction.members))
      .mockResolvedValue(entry([
        memberRow("Eustice", "b1000000-0000-0000-0000-0000000000m1", "Grand Inquisitor", true),
        memberRow("Romulus", "b1000000-0000-0000-0000-0000000000m2", "Inquisitor"),
      ]));
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Inquisitors",
      status: "active", base_location: null, aliases: [], summary: "",
    });
    const refusal = "Grand Inquisitor is the unique leadership seat of Inquisitors and is currently held by Eustice; change or clear their role first";
    const assignFactionRole = vi.fn()
      .mockRejectedValueOnce(new Error(refusal))
      .mockResolvedValue({ decision_id: "b8000000-0000-0000-0000-0000000000f8", kind: "membership", surface: "Romulus in Inquisitors", idempotent_replay: false });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, assignFactionRole,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    // The seated leader renders with the star; the roster legend explains it.
    expect(screen.getAllByText("Grand Inquisitor ★").length).toBeGreaterThan(0);
    expect(screen.getByText("★ unique leadership seat")).toBeInTheDocument();
    // Selecting the occupied leadership seat is refused by Core, by name.
    fireEvent.change(screen.getByRole("combobox", { name: "Role for Romulus" }), { target: { value: "Grand Inquisitor" } });
    const refusalAlerts = await screen.findAllByRole("alert");
    expect(refusalAlerts.some((alert) => alert.textContent?.includes("held by Eustice"))).toBe(true);
    expect(assignFactionRole).toHaveBeenCalledWith(faction.entry_id, "b1000000-0000-0000-0000-0000000000m2", "Grand Inquisitor", false);
    // Seating Romulus in the shared role succeeds and the chip appears after refresh.
    fireEvent.change(screen.getByRole("combobox", { name: "Role for Romulus" }), { target: { value: "Inquisitor" } });
    await waitFor(() => expect(assignFactionRole).toHaveBeenCalledWith(faction.entry_id, "b1000000-0000-0000-0000-0000000000m2", "Inquisitor", false));
    expect((await screen.findAllByText(/Seated Romulus as Inquisitor/)).length).toBeGreaterThan(0);
  });

  it("creates a new leadership role from the roster control", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [{ member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Eustice", role_title: null, is_leadership: false }],
      current_claim_count: 9, source_count: 0,
    };
    const entry = (role_title: string | null, is_leadership: boolean) => ({
      ...faction,
      members: [{ member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Eustice", role_title, is_leadership }],
      roles: role_title ? [{ name: role_title, is_leadership, holder_names: ["Eustice"] }] : [],
      claims: [], claim_history: [], sources: [],
    });
    const getLibraryEntry = vi.fn()
      .mockResolvedValueOnce(entry(null, false))
      .mockResolvedValue(entry("High Confessor", true));
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 1, canonical_name: "Inquisitors",
      status: "active", base_location: null, aliases: [], summary: "",
    });
    const assignFactionRole = vi.fn().mockResolvedValue({
      decision_id: "b8000000-0000-0000-0000-0000000000f9", kind: "membership", surface: "Eustice in Inquisitors", idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, assignFactionRole,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Role for Eustice" }), { target: { value: "__new" } });
    fireEvent.change(screen.getByRole("textbox", { name: "New role name for Eustice" }), { target: { value: "High Confessor" } });
    fireEvent.click(screen.getByLabelText("Leadership ★"));
    fireEvent.click(screen.getByRole("button", { name: "Assign" }));
    await waitFor(() => expect(assignFactionRole).toHaveBeenCalledWith(
      faction.entry_id, "b1000000-0000-0000-0000-0000000000m1", "High Confessor", true));
    expect((await screen.findAllByText(/Seated Eustice as High Confessor ★/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText("High Confessor ★").length).toBeGreaterThan(0);
  });

  it("auto-cancels a clean editor and forces save-or-discard on dirty edits when switching entries", async () => {
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
    const switchAlerts = await screen.findAllByRole("alert");
    expect(switchAlerts.some((alert) => alert.textContent?.includes("Resolve the open identity profile"))).toBe(true);
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
    // The authored description page outranks an imported exact-name page.
    expect(selectEntrySource({ canonical_name: "Fleurite", entity_kind: "location" }, [
      { document_id: "d5", path: "entities/fleurite.md" },
      { document_id: "d6", path: "locations/illisan/fleurite/fleurite.md" },
    ])?.path).toBe("entities/fleurite.md");
    // Lore writeups may append a generic suffix word to the entity's name.
    expect(selectEntrySource({ canonical_name: "Thanore", entity_kind: "location" }, [
      { document_id: "d4", path: "lore/thanore-history.md" },
    ])?.path).toBe("lore/thanore-history.md");
    expect(selectEntrySource({ canonical_name: "Vika Lana", entity_kind: "npc" }, [
      { document_id: "d5", path: "handouts/vika-lana-journal.md" },
    ])).toBeUndefined();
    // A filename that is exactly another entity's name is that entity's page.
    const names = ["Council of Unity", "Unity", "Unity People's Library"];
    expect(selectEntrySource({ canonical_name: "Council of Unity", entity_kind: "faction" }, [
      { document_id: "d6", path: "locations/argoth/ellish/unity/unity.md" },
    ], names)).toBeUndefined();
    expect(selectEntrySource({ canonical_name: "Unity", entity_kind: "location" }, [
      { document_id: "d6", path: "locations/argoth/ellish/unity/unity.md" },
    ], names)?.path).toBe("locations/argoth/ellish/unity/unity.md");
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
    fireEvent.click(screen.getByLabelText(/unique seat/));
    fireEvent.click(screen.getByRole("button", { name: "Define role" }));
    await waitFor(() => expect(defineFactionRole).toHaveBeenCalledWith(faction.entry_id, "Grand Inquisitor", true));
    expect((await screen.findAllByText(/Defined Grand Inquisitor ★ for Inquisitors/)).length).toBeGreaterThan(0);
    expect(screen.getByText("Vacant")).toBeInTheDocument();
    // Seat the member from the listing's dropdown.
    fireEvent.change(screen.getByLabelText("Seat a member as Grand Inquisitor"), { target: { value: "b1000000-0000-0000-0000-0000000000m1" } });
    await waitFor(() => expect(assignFactionRole).toHaveBeenCalledWith(faction.entry_id, "b1000000-0000-0000-0000-0000000000m1", "Grand Inquisitor", false));
    expect((await screen.findAllByText(/Seated Eustice as Grand Inquisitor ★/)).length).toBeGreaterThan(0);
    expect(screen.getByText("Vacate")).toBeInTheDocument();
    expect(screen.queryByText("Vacant")).not.toBeInTheDocument();
  });

  it("links Identity Review role declarations to factions from the Roles page", async () => {
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
    fireEvent.click(screen.getByLabelText("Leadership ★ for Grand Inquisitor"));
    fireEvent.click(within(screen.getByLabelText("Link Grand Inquisitor to faction").closest("li")!).getByRole("button", { name: "Link" }));
    await waitFor(() => expect(defineFactionRole).toHaveBeenCalledWith(faction.entry_id, "Grand Inquisitor", true));
    expect((await screen.findAllByText(/Linked Grand Inquisitor ★ to Inquisitors/)).length).toBeGreaterThan(0);
    // The linked seat now lives in the faction block; the sibling declaration stays unlinked.
    expect(screen.getByText("Vacant")).toBeInTheDocument();
    expect(screen.getByText("Declared during Identity Review — unlinked")).toBeInTheDocument();
    expect(screen.getByText("Inquisitor")).toBeInTheDocument();
  });

  it("pre-strips real-world date headers from imported assertions at review", () => {
    // TKT-0122: the date is provenance; the canonical wording starts clean.
    expect(cleanImportedAssertion("12/6/25 Coreferra making a plan for 8 giant badgers.")).toBe("Coreferra making a plan for 8 giant badgers.");
    expect(cleanImportedAssertion("2/14/26 — Bird Room & Demon Encounter\nLocation: Tower")).toBe("Bird Room & Demon Encounter\nLocation: Tower");
    expect(cleanImportedAssertion("2025-08-23: Want to investigate boat passage.")).toBe("Want to investigate boat passage.");
    // Campaign-year dates and undated text pass through untouched.
    expect(cleanImportedAssertion("On 505-11-05, Martin Faeroth died.")).toBe("On 505-11-05, Martin Faeroth died.");
    expect(cleanImportedAssertion("The council met under a rainless sky.")).toBe("The council met under a rainless sky.");
  });

  it("records a misspelling from the target search results", async () => {
    const gap = {
      surface: "Corefera", normalized_surface: "corefera",
      claims_with_phrase: 4, total_mentions: 4, retrieval_demand: 0,
      role_hint: false, suggested_canonical_name: null, suggested_kind: null,
      related_surfaces: [],
      evidence: [{ claim_id: "9a000000-0000-0000-0000-000000000001", excerpt: "Corefera feels the pull." }],
      alias_candidates: [],
    };
    const searchEntities = vi.fn().mockResolvedValue([
      { entity_id: "9b000000-0000-0000-0000-000000000001", canonical_name: "Coreferra", entity_kind: "npc", match_kind: "partial" },
    ]);
    const markIdentityMisspelling = vi.fn().mockResolvedValue({
      decision_id: "96000000-0000-0000-0000-000000000005", kind: "mark_misspelling",
      surface: "Corefera", linked_claims: 4, idempotent_replay: false,
    });
    const getIdentityGaps = vi.fn().mockResolvedValue({ gaps: [gap], total_candidates: 1 });
    render(<App campaignClient={makeClient({ getIdentityGaps, searchEntities, markIdentityMisspelling })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Identity" }));
    await screen.findByText("Showing 1 of 1 unresolved surface");
    fireEvent.change(screen.getByLabelText("Alias target search for Corefera"), { target: { value: "Coref" } });
    const match = await screen.findByRole("option", { name: /Coreferra/ });
    fireEvent.click(within(match).getByRole("button", { name: "Misspelling" }));
    await waitFor(() => expect(markIdentityMisspelling).toHaveBeenCalledWith(
      "Corefera", "9b000000-0000-0000-0000-000000000001", expect.stringMatching(/^identity-misspelling:/)));
    expect(await screen.findByText(/Recorded “Corefera” as a misspelling of Coreferra with receipt 96000000/)).toBeInTheDocument();
  });

  it("aliases a surface to a searched identity target from the Identity page", async () => {
    const gap = {
      surface: "Zander", normalized_surface: "zander",
      claims_with_phrase: 16, total_mentions: 16, retrieval_demand: 0,
      role_hint: false, suggested_canonical_name: null, suggested_kind: "pc",
      related_surfaces: [],
      evidence: [{ claim_id: "98000000-0000-0000-0000-000000000001", excerpt: "Zander checks his compass." }],
      alias_candidates: [],
    };
    const searchEntities = vi.fn().mockResolvedValue([
      { entity_id: "99000000-0000-0000-0000-000000000001", canonical_name: "Zander Thromius", entity_kind: "pc", match_kind: "partial" },
    ]);
    const addIdentityAlias = vi.fn().mockResolvedValue({
      decision_id: "96000000-0000-0000-0000-00000000000b", kind: "add_alias",
      surface: "Zander", linked_claims: 16, idempotent_replay: false,
    });
    const getIdentityGaps = vi.fn().mockResolvedValue({ gaps: [gap], total_candidates: 1 });
    render(<App campaignClient={makeClient({ getIdentityGaps, searchEntities, addIdentityAlias })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Identity" }));
    await screen.findByText("Showing 1 of 1 unresolved surface");
    fireEvent.change(screen.getByLabelText("Alias target search for Zander"), { target: { value: "Zander Th" } });
    const option = await screen.findByRole("option", { name: /Zander Thromius/ });
    fireEvent.click(within(option).getByRole("button", { name: /Zander Thromius/ }));
    await waitFor(() => expect(addIdentityAlias).toHaveBeenCalledWith(
      "Zander", "99000000-0000-0000-0000-000000000001", expect.stringMatching(/^identity-alias:/)));
    expect(await screen.findByText(/Aliased “Zander” to Zander Thromius with receipt 96000000/)).toBeInTheDocument();
  });
});

