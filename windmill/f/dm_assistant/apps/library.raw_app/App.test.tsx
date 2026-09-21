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

afterEach(() => {
  cleanup();
  toast.resetForTest();
  resetSettingsForTest();
  window.sessionStorage.clear();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

function makeQuietJobs(): JobPlatform { return {
  startHealthCheck: vi.fn(),
  cancel: vi.fn(),
  startProseDraft: vi.fn().mockRejectedValue(new Error("drafts are not configured in this test")),
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
  const view = render(<App campaignClient={client} jobPlatform={platform} />);
  fireEvent.click(screen.getByRole("button", { name: "Migration" }));
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

    fireEvent.click(screen.getByRole("button", { name: "New session" }));
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
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "New session" }));
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
    fireEvent.click(screen.getByRole("button", { name: "New session" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Write session log directly/ }));
    fireEvent.change(screen.getByLabelText("Session notes"), { target: { value: "The party met @Tich" } });
    fireEvent.click(await screen.findByRole("option", { name: /Tichon/i }));
    expect(screen.getByLabelText("Session notes")).toHaveValue("The party met @Tichon ");
    expect(screen.getByLabelText("Linked records")).toHaveTextContent("@Tichon");
  });

  it("accepts the highlighted @ mention with Enter and continues after a space", async () => {
    const searchEntities = vi.fn().mockResolvedValue([{ entity_id: "62000000-0000-0000-0000-000000000123", canonical_name: "Tichon", entity_kind: "npc", aliases: [], match_kind: "canonical" }]);
    render(<App campaignClient={makeClient({ searchEntities })} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "New session" }));
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
    expect(await screen.findByRole("heading", { name: "Romulus" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Character dossier" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Physical Appearance" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Abilities & Powers" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit NPC page" }));
    fireEvent.change(await screen.findByLabelText("NPC race"), { target: { value: "High elf" } });
    fireEvent.change(screen.getByLabelText("NPC sex"), { target: { value: "male" } });
    expect(screen.queryByLabelText("PC player")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review changes" }));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(updatePCProfile).toHaveBeenCalledWith(document.document_id, expect.objectContaining({ race: "High elf", sex: "male", player: undefined, idempotency_key: expect.stringMatching(/^character-profile:/) })));
  });

  it("assembles Romulus as one canonical NPC dossier with facts, plans, relationships, history, and all sources", async () => {
    updateSettings({ recordsVisibility: { sources: true, earlierVersions: true } });
    const npcSource = { document_id: "61000000-0000-0000-0000-000000000181", path: "npcs/romulus.md" };
    const bibleSource = { document_id: "61000000-0000-0000-0000-000000000182", path: "gm/campaign-bible.md" };
    const romulus = { entry_id: "62000000-0000-0000-0000-000000000181", canonical_name: "Romulus", entity_kind: "npc" as const, aliases: [], tags: [], current_claim_count: 3, source_count: 2 };
    const claim = (claim_id: string, assertion_text: string, state: string, authority: string, projection: string, sources: typeof npcSource[]) => ({ claim_id, assertion_text, state, authority, visibility: "dm_only", conditional: false, recorded_at: "2026-08-01T00:00:00Z", projection, sources });
    const campaignClient = makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([romulus]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...romulus, claims: [
        claim("63000000-0000-0000-0000-000000000181", "Romulus is the primary antagonist.", "established", "explicit_lore", "lore_fact", [npcSource]),
        claim("63000000-0000-0000-0000-000000000182", "Romulus intends to expand the Inquisition.", "intended", "npc_intention", "npc_plan", [npcSource]),
        claim("63000000-0000-0000-0000-000000000183", "Dariferra may warn the party about Romulus.", "prepared", "preparation", "dm_plan", [bibleSource]),
      ], claim_history: [{ ...claim("63000000-0000-0000-0000-000000000184", "Romulus once lacked a defined plan.", "possible", "brainstorm", "dm_plan", [bibleSource]), superseded_by_claim_id: "63000000-0000-0000-0000-000000000183", supersession_reason: "Replaced by focused preparation." }], sources: [bibleSource, npcSource] }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: npcSource.document_id, source_revision_id: "60000000-0000-0000-0000-000000000181", path: npcSource.path, content: "---\ntype: npc\nstatus: alive\n---\n# Romulus\n\n## Background / History\nRomulus corrupted Fleurite.\n\n## Relationships\nRhetus is his brother.\n\n## Personality\nCold and calculating." }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByText("NPC"));
    fireEvent.click(screen.getByRole("button", { name: "Romulus" }));
    expect(await screen.findByRole("heading", { name: "Known facts" })).toBeInTheDocument();
    expect(screen.getByText("Romulus is the primary antagonist.")).toBeInTheDocument();
    expect(screen.getByText("Romulus intends to expand the Inquisition.")).toBeInTheDocument();
    expect(screen.getByText("Dariferra may warn the party about Romulus.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Relationships" })).toBeInTheDocument();
    expect(screen.getByText("Earlier versions (1)")).toBeInTheDocument();
    expect(screen.getAllByText("gm/campaign-bible.md").length).toBeGreaterThan(0);
    expect(screen.getAllByText("npcs/romulus.md").length).toBeGreaterThan(0);
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

  it("renders a PC profile with intact background and explicit content boundaries", async () => {
    const pcDocument = {
      document_id: "61000000-0000-0000-0000-000000000002",
      path: "pcs/ruhrogue.md",
      classification: "durable_evidence" as const,
      candidate_count: 1,
      extraction_count: 0,
      open_review_count: 1,
      missing_source: false,
    };
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [pcDocument], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({
        document_id: pcDocument.document_id,
        source_revision_id: "60000000-0000-0000-0000-000000000002",
        path: pcDocument.path,
        content: "---\ntype: pc\nplayer: Ryan\nstatus: active\n---\n# Ruhrogue\n\n## Character Details\n- **Player:** Ryan\n- **Race:** Half-elf\n\n## Current Status\nDerived session summary.\n\n## Private GM Notes\nConditional DM direction.\n\n## Original Biography Source\nThe intact player-authored biography.",
      }),
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: /pcs.*1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /ruhrogue\.md/i }));

    expect(await screen.findByRole("heading", { name: "Ruhrogue" })).toBeInTheDocument();
    expect(screen.getByText("Ryan")).toBeInTheDocument();
    expect(screen.getByText("Half-elf")).toBeInTheDocument();
    expect(screen.getByText("Not recorded")).toBeInTheDocument();
    expect(screen.getByText("The intact player-authored biography.")).toBeInTheDocument();
    expect(screen.queryByText(/Current Status summary is derived/)).not.toBeInTheDocument();
    expect(screen.queryByText("Derived session summary.")).not.toBeInTheDocument();
    expect(screen.queryByText("Conditional DM direction.")).not.toBeInTheDocument();
    expect(screen.getAllByText("None")).toHaveLength(3);
    expect(screen.queryByRole("heading", { name: "Facts" })).not.toBeInTheDocument();
  });

  it("corrects a committed DM-plan claim without editing canonical history in place", async () => {
    const document = { document_id: "61000000-0000-0000-0000-000000000003", path: "pcs/coreferra.md", classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const claim = { claim_id: "63000000-0000-0000-0000-000000000003", assertion_text: "Coreferra restores magic. Source: [[gm/notes]]", state: "possible", authority: "brainstorm", visibility: "dm_only", recorded_at: "2026-08-13T00:00:00Z", source_paths: [document.path], snapshot_hash: "a".repeat(64), is_current: true };
    const replaceClaim = vi.fn().mockResolvedValue({ receipt_id: "64000000-0000-0000-0000-000000000003", change_set_id: "65000000-0000-0000-0000-000000000003", original_claim_id: claim.claim_id, replacement_claim_ids: ["66000000-0000-0000-0000-000000000003"], idempotent_replay: false });
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: document.document_id, source_revision_id: "60000000-0000-0000-0000-000000000003", path: document.path, content: "---\ntype: pc\nplayer: Presto\nstatus: active\n---\n# Coreferra\n\n## Original Biography Source\nBiography.", canonical_claims: [{ claim_id: claim.claim_id, assertion_text: claim.assertion_text, state: claim.state, authority: claim.authority, visibility: claim.visibility, conditional: false }] }),
      getClaimSnapshot: vi.fn().mockResolvedValue(claim), replaceClaim,
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: /pcs.*1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /coreferra\.md/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Edit claim" }));
    fireEvent.change(await screen.findByLabelText("Replacement 1 claim"), { target: { value: "Coreferra restores magic." } });
    fireEvent.change(screen.getByLabelText("Claim correction reason"), { target: { value: "Remove provenance markup from assertion text." } });
    fireEvent.click(screen.getByRole("button", { name: "Save replacement claim" }));
    await waitFor(() => expect(replaceClaim).toHaveBeenCalledWith(claim, [expect.objectContaining({ assertion_text: "Coreferra restores magic.", state: "possible", authority: "brainstorm", visibility: "dm_only" })], "Remove provenance markup from assertion text."));
  });

  it("splits a committed claim and requires an observed campaign date", async () => {
    const document = { document_id: "61000000-0000-0000-0000-000000000004", path: "pcs/coreferra.md", classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false };
    const claim = { claim_id: "63000000-0000-0000-0000-000000000004", assertion_text: "Mixed preparation and outcome.", state: "prepared", authority: "preparation", visibility: "dm_only", recorded_at: "2026-08-13T00:00:00Z", source_paths: [document.path], evidence: [], snapshot_hash: "b".repeat(64), is_current: true };
    const replaceClaim = vi.fn().mockResolvedValue({ receipt_id: "64000000-0000-0000-0000-000000000004", change_set_id: "65000000-0000-0000-0000-000000000004", original_claim_id: claim.claim_id, replacement_claim_ids: ["66000000-0000-0000-0000-000000000004", "66000000-0000-0000-0000-000000000005"], idempotent_replay: false });
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: document.document_id, source_revision_id: "60000000-0000-0000-0000-000000000004", path: document.path, content: "---\ntype: pc\nplayer: Presto\nstatus: active\n---\n# Coreferra\n\n## Original Biography Source\nBiography.", canonical_claims: [{ claim_id: claim.claim_id, assertion_text: claim.assertion_text, state: claim.state, authority: claim.authority, visibility: claim.visibility, conditional: false }] }),
      getClaimSnapshot: vi.fn().mockResolvedValue(claim), replaceClaim,
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(await screen.findByRole("button", { name: /pcs.*1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /coreferra\.md/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Edit claim" }));
    fireEvent.click(await screen.findByRole("button", { name: "Split into another claim" }));
    const second = screen.getByText("Replacement 2").closest("fieldset");
    expect(second).not.toBeNull();
    fireEvent.change(within(second!).getByLabelText("Replacement 2 claim"), { target: { value: "The outcome occurred." } });
    fireEvent.change(within(second!).getByLabelText("State"), { target: { value: "observed" } });
    fireEvent.change(screen.getByLabelText("Claim correction reason"), { target: { value: "Separate plan from outcome." } });
    expect(screen.getByRole("button", { name: "Save split claims" })).toBeDisabled();
    expect(screen.getByText("Observed replacements require an observed campaign date.")).toBeInTheDocument();
    const observedDate = second!.querySelectorAll("fieldset.claim-date")[3];
    fireEvent.change(observedDate.querySelector('input[type="number"]')!, { target: { value: "2026" } });
    fireEvent.click(screen.getByRole("button", { name: "Save split claims" }));
    await waitFor(() => expect(replaceClaim).toHaveBeenCalledWith(claim, expect.arrayContaining([expect.objectContaining({ state: "prepared" }), expect.objectContaining({ assertion_text: "The outcome occurred.", state: "observed", observed: { year: 2026 } })]), "Separate plan from outcome."));
  });

  it("reviews and saves an exact PC profile edit with source provenance", async () => {
    const document = {
      document_id: "61000000-0000-0000-0000-000000000002", path: "pcs/ruhrogue.md",
      classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0,
      open_review_count: 0, missing_source: false,
    };
    const updatePCProfile = vi.fn().mockResolvedValue({
      receipt_id: "95000000-0000-0000-0000-000000000001",
      document_id: document.document_id, version: 1, idempotent_replay: false,
    });
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({
        document_id: document.document_id,
        source_revision_id: "60000000-0000-0000-0000-000000000002",
        path: document.path,
        content: "---\ntype: pc\nplayer: Ryan\nstatus: active\n---\n# Ruhrogue\n\n## Original Biography Source\nOld biography.",
      }),
      getPCProfile: vi.fn().mockResolvedValue(null), updatePCProfile,
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: /pcs.*1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /ruhrogue\.md/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Edit PC page" }));
    fireEvent.change(screen.getByLabelText("PC sex"), { target: { value: "male" } });
    fireEvent.change(screen.getByLabelText("PC background"), { target: { value: "Revised biography." } });
    fireEvent.click(screen.getByRole("button", { name: "Review changes" }));

    const confirmation = screen.getByRole("region", { name: "PC profile change review" });
    expect(confirmation).toHaveTextContent("2 fields changed: sex, background");
    expect(confirmation).not.toHaveTextContent("Revised biography.");
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(updatePCProfile).toHaveBeenCalledWith(
      document.document_id,
      expect.objectContaining({
        source_revision_id: "60000000-0000-0000-0000-000000000002",
        version: 0, sex: "male", background: "Revised biography.",
        idempotency_key: expect.stringMatching(/^pc-profile:/),
      }),
    ));
    expect(await screen.findByText(/Saved with receipt 95000000/)).toBeInTheDocument();
  });

  it("accepts aliases with spaces while typing and trims them at save", async () => {
    const document = {
      document_id: "61000000-0000-0000-0000-000000000003", path: "pcs/coreferra.md",
      classification: "durable_evidence" as const, candidate_count: 0, extraction_count: 0,
      open_review_count: 0, missing_source: false,
    };
    const updatePCProfile = vi.fn().mockResolvedValue({
      receipt_id: "95000000-0000-0000-0000-000000000002",
      document_id: document.document_id, version: 1, idempotent_replay: false,
    });
    const campaignClient = makeClient({
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [document], total: 1, limit: 500, offset: 0 }),
      getSourceDocument: vi.fn().mockResolvedValue({
        document_id: document.document_id,
        source_revision_id: "60000000-0000-0000-0000-000000000003",
        path: document.path,
        content: "---\ntype: pc\nplayer: Presto\nstatus: active\n---\n# Coreferra\n\n## Original Biography Source\nBiography.",
      }),
      getPCProfile: vi.fn().mockResolvedValue(null), updatePCProfile,
    });
    render(<App campaignClient={campaignClient} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: /pcs.*1/i }));
    fireEvent.click(await screen.findByRole("button", { name: /coreferra\.md/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Edit PC page" }));
    const aliases = screen.getByLabelText("PC aliases");
    fireEvent.change(aliases, { target: { value: "The " } });
    expect(aliases).toHaveValue("The ");
    fireEvent.blur(aliases);
    expect(aliases).toHaveValue("The");
    fireEvent.change(aliases, { target: { value: "The Grand Inquisitor, The Shadow" } });
    expect(aliases).toHaveValue("The Grand Inquisitor, The Shadow");
    fireEvent.click(screen.getByRole("button", { name: "Review changes" }));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(updatePCProfile).toHaveBeenCalledWith(
      document.document_id,
      expect.objectContaining({ aliases: ["The Grand Inquisitor", "The Shadow"] }),
    ));
  });

  it("shows complete plan coordinates before exact approval and application", async () => {
    const planProposal = {
      proposal_id: "a1000000-0000-0000-0000-000000000001",
      workflow_session_id: "a2000000-0000-0000-0000-000000000001",
      status: "pending",
      version_id: "a3000000-0000-0000-0000-000000000001",
      version_number: 1,
      content_hash: "d".repeat(64),
      created_at: "2026-08-02T12:00:00Z",
      item: {
        item_id: "a4000000-0000-0000-0000-000000000001",
        mutation_kind: "create_plan" as const,
        target_id: "a5000000-0000-0000-0000-000000000001",
        after: {
          record_type: "plan", plan_kind: "campaign_direction", plan_kind_version: 1,
          canonical_name: "Sanitized arc pressure", lifecycle: "active",
          knowledge_boundary: "dm_direction", visibility: "dm_only",
          evidence_source_span_ids: [], related_plan_ids: [],
        },
      },
    };
    const planApproval = { ...approval, proposal_id: planProposal.proposal_id,
      proposal_version_id: planProposal.version_id, item_ids: [planProposal.item.item_id] };
    const campaignClient = makeClient({
      createPlanProposal: vi.fn().mockResolvedValue(planProposal),
      approvePlanProposal: vi.fn().mockResolvedValue(planApproval),
    });
    renderTools(campaignClient);
    fireEvent.click(screen.getByRole("button", { name: "Ask the archive" }));
    fireEvent.change(screen.getByLabelText("Plan name"), { target: { value: "Sanitized arc pressure" } });
    fireEvent.change(screen.getByLabelText("Plan summary"), { target: { value: "Develop pressure without prescribing a PC response." } });
    fireEvent.click(screen.getByRole("button", { name: "Create exact plan proposal" }));
    expect(await screen.findByText((_, element) =>
      element?.tagName === "PRE" && Boolean(element.textContent?.includes("dm_direction")),
    )).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve and apply exact plan proposal" }));
    expect(await screen.findByText(/Applied with receipt/)).toBeInTheDocument();
  });

  it("renders a grounded CampaignClient response with citation and authority", async () => {
    const campaignClient = makeClient({
      query: vi.fn().mockResolvedValue({
        answer_mode: "answer",
        evidence: [
          {
            record_id: "claim-1",
            assertion: "Jace bears the copied signature.",
            citation: "sessions/sanitized.md#Warden signature",
            state: "observed",
            authority: "real_play",
            role: "support",
          },
        ],
        citations: ["sessions/sanitized.md#Warden signature"],
        reasons: ["grounded_answer"],
      }),
    });
    renderTools(campaignClient);
    fireEvent.click(screen.getByRole("button", { name: "Ask the archive" }));

    fireEvent.change(screen.getByLabelText("Campaign question"), {
      target: { value: "What signature does Jace bear?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search records" }));

    expect(await screen.findByText("The archive supports this")).toBeInTheDocument();
    expect(screen.getByText("Jace bears the copied signature.")).toBeInTheDocument();
    expect(screen.getByText("sessions/sanitized.md#Warden signature")).toBeInTheDocument();
    expect(campaignClient.query).toHaveBeenCalledWith(
      expect.objectContaining({ requester_visibility: { role: "dm" } }),
    );
  });

  it("reviews exact evidence, confirms one version, applies, and persists its receipt", async () => {
    const campaignClient = makeClient();
    renderApp(campaignClient);

    fireEvent.click(await screen.findByRole("button", { name: /The sanitized archive names a careful keeper/ }));
    expect(await screen.findByText("lore/sanitized-keeper.md")).toBeInTheDocument();
    expect(screen.getAllByText(candidate.assertion_text).length).toBeGreaterThan(0);
    expect(screen.queryByText("inbox/sanitized-unknown.md")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tools" }));
    expect(await screen.findByRole("region", { name: "Source reviews" })).toBeInTheDocument();
    expect(screen.getByText("inbox/sanitized-unknown.md")).toBeInTheDocument();
    expect(screen.getByText("2 open · 1 quarantined")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Migration" }));
    expect(screen.getAllByText((_content, element) => Boolean(element?.textContent?.includes("17 sources") && element?.classList?.contains("run-summary-compact"))).length).toBeGreaterThan(0);
    expect(screen.getAllByText((_content, element) => Boolean(element?.textContent?.includes("15 candidates") && element?.classList?.contains("run-summary-compact"))).length).toBeGreaterThan(0);

    expect(screen.getByLabelText("Editable extraction review")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Extraction 1 predicate"), { target: { value: "guards" } });
    fireEvent.change(screen.getByLabelText("Extraction 1 state"), { target: { value: "prepared" } });
    fireEvent.change(screen.getByLabelText("Extraction 1 authority"), { target: { value: "preparation" } });
    fireEvent.change(screen.getByLabelText("Extraction 1 visibility"), { target: { value: "party" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Continue with selected claims" }).at(-1)!);
    fireEvent.change(screen.getByRole("textbox", { name: "Canonical name" }), {
      target: { value: "Sanitized Keeper" },
    });
    fireEvent.change(screen.getByLabelText("Entity kind"), {
      target: { value: "location" },
    });
    expect(screen.getByText("A place at any geographic scale.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add tags (optional)" }));
    fireEvent.click(screen.getByLabelText("deity"));
    expect(screen.getByRole("button", { name: "Remove deity tag" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create grouped proposal" }));

    await waitFor(() => expect(campaignClient.createProposal).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({
        mutation_kind: "create_claim",
        state: "prepared",
        authority: "preparation",
        visibility: "party",
      })]),
    ));

    const proposalHeading = await screen.findByText("Version 1");
    const proposalPanel = proposalHeading.closest("article");
    expect(proposalPanel).not.toBeNull();
    const proposalComparison = within(proposalPanel as HTMLElement);
    expect(proposalComparison.getByText("Entity kind")).toBeInTheDocument();
    expect(proposalComparison.getByText("location")).toBeInTheDocument();
    expect(proposalComparison.getByText("Predicate")).toBeInTheDocument();
    expect(proposalComparison.getByText("archive_role")).toBeInTheDocument();
    expect(proposalComparison.getByText("Authority")).toBeInTheDocument();
    expect(proposalComparison.getByText("preparation")).toBeInTheDocument();
    expect(proposalComparison.getByText("Visibility")).toBeInTheDocument();
    expect(proposalComparison.getByText("party")).toBeInTheDocument();
    expect(screen.getByText("Ready for approval")).toBeInTheDocument();
    const approvalButton = screen.getByRole("button", { name: "Approve and apply 2 exact items" });
    expect(approvalButton).toBeEnabled();
    fireEvent.click(approvalButton);

    expect(await screen.findByText("Applied with receipt")).toBeInTheDocument();
    expect(screen.getByText("93000000-0000-0000-0000-000000000001")).toBeInTheDocument();

    expect(campaignClient.createProposal).toHaveBeenCalledWith([
      expect.objectContaining({
        mutation_kind: "create_entity",
        candidate_id: candidate.candidate_id,
        evidence_revision_id: candidate.evidence[0].source_revision_id,
        canonical_name: "Sanitized Keeper",
        entity_kind: "location",
        tags: ["deity"],
      }),
      expect.objectContaining({
        mutation_kind: "create_claim",
        candidate_id: candidate.candidate_id,
        candidate_extraction_id: candidate.extractions?.[0].extraction_id,
        predicate: "guards",
        state: "prepared",
        authority: "preparation",
        visibility: "party",
      }),
    ]);
    expect(JSON.parse(window.sessionStorage.getItem(REVIEW_STATE_KEY) ?? "{}")).toMatchObject({
      phase: "applied",
      receipt: { receipt_id: "93000000-0000-0000-0000-000000000001" },
    });
  });

  it("creates a provenance-first proposal without SPO or AI extraction", async () => {
    const campaignClient = makeClient();
    renderApp(campaignClient);

    fireEvent.click(await screen.findByRole("button", { name: /The sanitized archive names a careful keeper/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Create source-backed proposal" }));

    await waitFor(() => expect(campaignClient.createProposal).toHaveBeenCalledTimes(1));
    expect(campaignClient.createProposal).toHaveBeenCalledWith([
      expect.objectContaining({
        mutation_kind: "create_claim",
        candidate_id: candidate.candidate_id,
        evidence_revision_id: candidate.evidence[0].source_revision_id,
        assertion_text: candidate.assertion_text,
        state: candidate.state,
        authority: candidate.authority,
        visibility: candidate.visibility,
      }),
    ]);
    const createdItem = vi.mocked(campaignClient.createProposal).mock.calls[0][0][0];
    expect(createdItem).not.toHaveProperty("subject_entity_id");
    expect(createdItem).not.toHaveProperty("predicate");
    expect(screen.getByText("Source-backed claim is ready for exact approval.")).toBeInTheDocument();
  });

  it("prefills a direct session claim date and commits the confirmed claim in one action", async () => {
    const directCandidate: ImportCandidate = {
      ...candidate,
      assertion_text: "Coreferra became the Herald of Arkin.",
      state: "observed",
      authority: "real_play",
      extractor_version: "direct-input/session-note-v2",
      extractions: [],
      evidence: [{
        ...candidate.evidence[0],
        excerpt: "@Coreferra became the Herald of Arkin.",
        in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 },
        mentions: [{ entity_id: "62000000-0000-0000-0000-000000000124", display_name: "Coreferra", start_offset: 0, end_offset: 11 }],
      }],
    };
    const listLibraryEntries = vi.fn().mockResolvedValue([]);
    const campaignClient = makeClient({
      getCandidate: vi.fn().mockResolvedValue(directCandidate),
      listCandidates: vi.fn().mockResolvedValue({ items: [directCandidate], total: 1, limit: 100, offset: 0 }),
      listLibraryEntries,
    });
    renderApp(campaignClient);
    const candidateButton = await screen.findByRole("button", { name: /Coreferra became the Herald/ });
    await waitFor(() => expect(candidateButton).toBeEnabled());
    fireEvent.click(candidateButton);
    expect(await screen.findByLabelText("Canonical claim")).toHaveValue("Coreferra became the Herald of Arkin.");
    expect(screen.getByLabelText("Observed campaign date")).toHaveValue("0505-07-12");
    expect(screen.getByText("@Coreferra")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Commit .*claim.* and continue/ }));
    await waitFor(() => expect(campaignClient.applyApproval).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(listLibraryEntries).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("heading", { name: "Every statement has been reviewed." })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View session note" })).toBeInTheDocument();
    expect(screen.queryByText("1 of 0 pending")).not.toBeInTheDocument();
    expect(campaignClient.createProposal).toHaveBeenCalledWith([expect.objectContaining({
      assertion_text: "Coreferra became the Herald of Arkin.",
      observed_at: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 },
      related_entity_ids: ["62000000-0000-0000-0000-000000000124"],
    })]);
  });

  it("resumes an existing direct-note proposal after a failed application", async () => {
    const directCandidate: ImportCandidate = {
      ...candidate, state: "observed", authority: "real_play", extractor_version: "direct-input/session-note-v2",
      extractions: [], evidence: [{ ...candidate.evidence[0], in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 } }],
    };
    const createProposal = vi.fn().mockRejectedValue(new Error("Campaign Core returned 409 Conflict"));
    const getCandidateProposal = vi.fn().mockResolvedValue(proposal);
    const campaignClient = makeClient({
      createProposal, getCandidateProposal,
      getCandidate: vi.fn().mockResolvedValue(directCandidate),
      listCandidates: vi.fn().mockResolvedValue({ items: [directCandidate], total: 1, limit: 100, offset: 0 }),
    });
    renderApp(campaignClient);
    const candidateButton = await screen.findByRole("button", { name: /The sanitized archive names/ });
    await waitFor(() => expect(candidateButton).toBeEnabled());
    fireEvent.click(candidateButton);
    fireEvent.click(await screen.findByRole("button", { name: /Commit .*claim.* and continue/ }));
    await waitFor(() => expect(campaignClient.applyApproval).toHaveBeenCalledTimes(1));
    expect(getCandidateProposal).toHaveBeenCalledWith(directCandidate.candidate_id);
  });

  it("advances after skipping a direct session statement with an audit reason", async () => {
    const first: ImportCandidate = { ...candidate, assertion_text: "A table aside was not campaign truth.", state: "observed", authority: "real_play", extractor_version: "direct-input/session-note-v3", extractions: [] };
    const second: ImportCandidate = { ...first, candidate_id: "50000000-0000-0000-0000-000000000002", assertion_text: "The party entered the camp." };
    const dispositionCandidate = vi.fn().mockResolvedValue({ disposition_id: "92000000-0000-0000-0000-000000000002", candidate_id: first.candidate_id, review_status: "deferred", reason: "Table chatter", created_at: "2026-08-23T12:00:00Z" });
    const campaignClient = makeClient({
      dispositionCandidate,
      listCandidates: vi.fn().mockResolvedValue({ items: [first, second], total: 2, limit: 100, offset: 0 }),
      getCandidate: vi.fn().mockImplementation(async (id: string) => id === second.candidate_id ? second : first),
    });
    renderApp(campaignClient);
    const firstButton = await screen.findByRole("button", { name: /A table aside/ });
    await waitFor(() => expect(firstButton).toBeEnabled());
    fireEvent.click(firstButton);
    await screen.findByLabelText("Canonical claim");
    fireEvent.change(screen.getByLabelText("Skip reason"), { target: { value: "Table chatter" } });
    fireEvent.click(screen.getByRole("button", { name: "Skip with reason" }));
    expect(await screen.findByLabelText("Canonical claim")).toHaveValue("The party entered the camp.");
    expect(dispositionCandidate).toHaveBeenCalledWith(first.candidate_id, "deferred", "Table chatter");
  });

  it("revises a recovered proposal when the current direct-review draft changed", async () => {
    const directCandidate: ImportCandidate = { ...candidate, state: "observed", authority: "real_play", extractor_version: "direct-input/session-note-v3", extractions: [], evidence: [{ ...candidate.evidence[0], in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 } }] };
    const revised = { ...proposal, version_number: 2, version_id: "70000000-0000-0000-0000-000000000099", content_hash: "d".repeat(64), items: proposal.items.map((item) => item.mutation_kind === "create_claim" ? { ...item, after: { ...item.after, assertion_text: "Corrected session truth." } } : item) };
    const reviseProposal = vi.fn().mockResolvedValue(revised);
    const campaignClient = makeClient({
      createProposal: vi.fn().mockRejectedValue(new Error("Campaign Core returned 409 Conflict")),
      getCandidateProposal: vi.fn().mockResolvedValue(proposal), reviseProposal,
      getProposal: vi.fn().mockResolvedValue(revised),
      getCandidate: vi.fn().mockResolvedValue(directCandidate),
      listCandidates: vi.fn().mockResolvedValue({ items: [directCandidate], total: 1, limit: 100, offset: 0 }),
    });
    renderApp(campaignClient);
    fireEvent.click(await screen.findByRole("button", { name: /The sanitized archive names/ }));
    fireEvent.change(await screen.findByLabelText("Canonical claim"), { target: { value: "Corrected session truth." } });
    fireEvent.click(screen.getByRole("button", { name: /Commit .*claim.* and continue/ }));
    await waitFor(() => expect(reviseProposal).toHaveBeenCalledTimes(1));
  });

  it("splits one direct session statement into separately persisted claims", async () => {
    const directCandidate: ImportCandidate = {
      ...candidate,
      assertion_text: "The party agreed to persuade Tichon. Aris permitted them to move the carpet.",
      state: "observed", authority: "real_play", extractor_version: "direct-input/session-note-v2",
      extractions: [], evidence: [{ ...candidate.evidence[0], in_game_date: { calendar_id: "gregorian-ce", year: 505, month: 7, day: 12 }, mentions: [
        { entity_id: "62000000-0000-0000-0000-000000000201", display_name: "Tichon", start_offset: 29, end_offset: 36 },
        { entity_id: "62000000-0000-0000-0000-000000000202", display_name: "Aris", start_offset: 38, end_offset: 43 },
      ] }],
    };
    const campaignClient = makeClient({
      getCandidate: vi.fn().mockResolvedValue(directCandidate),
      listCandidates: vi.fn().mockResolvedValue({ items: [directCandidate], total: 1, limit: 100, offset: 0 }),
    });
    renderApp(campaignClient);
    fireEvent.click(await screen.findByRole("button", { name: /The party agreed to persuade/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Split into claims" }));
    expect(screen.getByLabelText("Split claim 1")).toHaveValue("The party agreed to persuade Tichon.");
    expect(screen.getByLabelText("Split claim 2")).toHaveValue("Aris permitted them to move the carpet.");
    fireEvent.click(screen.getByRole("button", { name: "Add claim" }));
    fireEvent.change(screen.getByLabelText("Split claim 3"), { target: { value: "The permission applied before the meeting." } });
    fireEvent.click(screen.getByRole("button", { name: "Commit 3 claims and continue" }));
    await waitFor(() => expect(campaignClient.createProposal).toHaveBeenCalledTimes(1));
    const items = vi.mocked(campaignClient.createProposal).mock.calls[0][0];
    expect(items).toHaveLength(3);
    expect(items.map((item) => "assertion_text" in item ? item.assertion_text : "")).toEqual([
      "The party agreed to persuade Tichon.",
      "Aris permitted them to move the carpet.",
      "The permission applied before the meeting.",
    ]);
    expect(items.map((item) => "related_entity_ids" in item ? item.related_entity_ids : [])).toEqual([
      ["62000000-0000-0000-0000-000000000201"],
      ["62000000-0000-0000-0000-000000000202"],
      [],
    ]);
  });

  it("abandons extracted assertions without rejecting the source candidate", async () => {
    const campaignClient = makeClient();
    renderApp(campaignClient);
    fireEvent.click(await screen.findByRole("button", { name: /The sanitized archive names/ }));
    const abandonButtons = await screen.findAllByRole("button", { name: "Abandon extraction" });
    fireEvent.click(abandonButtons[0]);
    expect(await screen.findByText("Extraction abandoned. The source-backed candidate remains available.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Assertion-first extraction review")).not.toBeInTheDocument();
    expect(campaignClient.dispositionCandidate).not.toHaveBeenCalled();
  });

  it("does not treat planning guidance as conditional without an explicit prerequisite", async () => {
    const planningCandidate: ImportCandidate = {
      ...candidate,
      assertion_text: "- The tattoo should remain longer-term foreshadowing.\n\n### Campaign-Sculpting Direction\n\nThese are GM planning notes only — not concrete outcomes or guarantees.\n\nSource: [[gm/brainstorming/tattoo]]",
      state: "prepared",
      authority: "preparation",
      conditional: true,
      extractions: [],
    };
    const campaignClient = makeClient({
      listCandidates: vi.fn().mockResolvedValue({ items: [planningCandidate], total: 1, limit: 50, offset: 0 }),
      getCandidate: vi.fn().mockResolvedValue(planningCandidate),
    });
    renderApp(campaignClient);

    const planningButton = await screen.findByRole("button", { name: /longer-term foreshadowing/ });
    await waitFor(() => expect(planningButton).toBeEnabled());
    fireEvent.click(planningButton);
    expect(await screen.findByLabelText("Canonical claim")).toHaveValue("The tattoo should remain longer-term foreshadowing.");
    const prerequisite = await screen.findByRole("checkbox", { name: "Has a concrete prerequisite" });
    expect(prerequisite).not.toBeChecked();
    expect(screen.queryByLabelText("Condition trigger")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create source-backed proposal" }));

    await waitFor(() => expect(campaignClient.createProposal).toHaveBeenCalledWith([
      expect.objectContaining({ is_conditional: false }),
    ]));
  });

  it("corrects a pending claim by creating a new immutable proposal version", async () => {
    const corrected = {
      ...proposal, version_number: 2,
      version_id: "70000000-0000-0000-0000-000000000002",
      content_hash: "b".repeat(64), supersedes_version_id: proposal.version_id,
      items: proposal.items.map((item, index) => ({ ...item, item_id: `71000000-0000-0000-0000-00000000000${index + 2}`, after: {
        ...item.after, assertion_text: "Ruhrogue may help unite Myrin against Starfall.",
        state: "possible", authority: "brainstorm", is_conditional: false,
      } })),
    };
    const reviseProposal = vi.fn().mockResolvedValue(corrected);
    const campaignClient = makeClient({ reviseProposal });
    renderApp(campaignClient);
    fireEvent.click(await screen.findByRole("button", { name: /The sanitized archive names a careful keeper/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Create source-backed proposal" }));
    fireEvent.click(await screen.findByRole("button", { name: "Correct claim before approval" }));
    fireEvent.change(screen.getByLabelText("Corrected claim"), { target: { value: "Ruhrogue may help unite Myrin against Starfall." } });
    fireEvent.change(screen.getByLabelText("Corrected state"), { target: { value: "possible" } });
    expect(screen.queryByRole("button", { name: /Approve and apply/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save as new version" }));

    await waitFor(() => expect(reviseProposal).toHaveBeenCalledWith(
      proposal.proposal_id,
      expect.arrayContaining([expect.objectContaining({
        assertion_text: "Ruhrogue may help unite Myrin against Starfall.",
        state: "possible", authority: "brainstorm", is_conditional: false,
        evidence_revision_id: candidate.evidence[0].source_revision_id,
      })]),
    ));
    expect(await screen.findByText("Correction saved as immutable version 2.")).toBeInTheDocument();
    expect(screen.getByText("Version 2")).toBeInTheDocument();
  });

  it("allows a proposed candidate to recover its durable proposal after document navigation", async () => {
    const proposedCandidate = { ...candidate, review_status: "proposed" };
    window.sessionStorage.setItem(REVIEW_STATE_KEY, JSON.stringify({
      selectedCandidateId: candidate.candidate_id, phase: "proposal_pending", proposal,
    }));
    const getCandidateProposal = vi.fn().mockResolvedValue(proposal);
    const campaignClient = makeClient({
      listCandidates: vi.fn().mockResolvedValue({ items: [proposedCandidate], total: 1, limit: 50, offset: 0 }),
      getCandidate: vi.fn().mockResolvedValue(proposedCandidate), getCandidateProposal,
    });
    renderApp(campaignClient);
    fireEvent.click(await screen.findByRole("button", { name: /lore.*1/i }));
    const document = await screen.findByRole("button", { name: /sanitized-keeper\.md/i });
    fireEvent.click(document);
    const proposed = await screen.findByRole("button", { name: /explicit lore.*proposed/i });
    expect(proposed).toBeEnabled();
    fireEvent.click(proposed);
    await waitFor(() => expect(getCandidateProposal).toHaveBeenCalledWith(candidate.candidate_id));
    expect(await screen.findByText("Recovered immutable proposal version 1.")).toBeInTheDocument();
  });

  it("renders successful extraction results without requiring a refresh", async () => {
    const staleCandidate = { ...candidate, extractions: [] };
    const campaignClient = makeClient({
      getCandidate: vi.fn().mockResolvedValueOnce(staleCandidate).mockResolvedValue(candidate),
      extractCandidate: vi.fn().mockResolvedValue({
        candidate_id: candidate.candidate_id,
        extracted: candidate.extractions,
        extractor_version: "extraction/1",
        error: null,
      }),
    });
    renderApp(campaignClient);

    expect(screen.queryByRole("button", { name: "Extract this candidate" })).not.toBeInTheDocument();
    fireEvent.click(
      await screen.findByRole("button", {
        name: /The sanitized archive names a careful keeper/,
      }),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Extract this candidate" }));

    expect(await screen.findByLabelText("Editable extraction review")).toBeInTheDocument();
    expect(screen.getByLabelText("Extraction coverage")).toHaveTextContent("2 / 2 accounted for");
    expect(screen.getByLabelText("Extraction coverage")).toHaveTextContent("context only");
    expect(screen.getAllByRole("status").some((status) => status.textContent?.includes("1 candidate extracted."))).toBe(true);
    const backgroundTasks = screen.getByLabelText("Background tasks");
    expect(backgroundTasks).toHaveTextContent("0 active");
    expect(backgroundTasks).toHaveTextContent("succeeded");
    expect(backgroundTasks).toHaveTextContent("1 completed · 0 failed");
    expect(screen.getByDisplayValue("the archive").getAttribute("aria-label")).toBe("Extraction 1 object");
    expect(screen.queryByRole("button", { name: "Review this extraction" })).not.toBeInTheDocument();
  });

  it("keeps the same page-level monitor visible after re-extraction advances", async () => {
    const campaignClient = makeClient({
      extractCandidate: vi.fn().mockResolvedValue({
        candidate_id: candidate.candidate_id,
        extracted: candidate.extractions,
        extractor_version: "extraction/1",
        error: null,
      }),
    });
    renderApp(campaignClient);
    fireEvent.click(await screen.findByRole("button", { name: /The sanitized archive names a careful keeper/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Back to candidate" }));
    fireEvent.click(screen.getByRole("button", { name: "Re-extract this candidate" }));

    expect(await screen.findByLabelText("Editable extraction review")).toBeInTheDocument();
    expect(screen.getAllByRole("status").some((status) => status.textContent?.includes("1 candidate extracted."))).toBe(true);
  });

  it("retries a failed extraction directly from Background Tasks", async () => {
    window.sessionStorage.setItem(LAST_EXTRACTION_JOB_KEY, JSON.stringify({
      jobId: "019feef3-396e-7041-4e4c-426270f42ce1",
      state: "failed",
      progress: 100,
      error: "provider output was truncated",
      totalItems: 1,
      candidateIds: [candidate.candidate_id],
      updatedAt: "2026-08-10T20:00:00Z",
    }));
    const jobs = makeQuietJobs();
    renderApp(makeClient(), jobs);

    fireEvent.click(screen.getByRole("button", { name: "Retry failed extraction" }));

    await waitFor(() => expect(jobs.startCandidateExtraction).toHaveBeenCalledWith([candidate.candidate_id]));
    expect(screen.getByLabelText("Background tasks")).toHaveTextContent("queued");
  });

  it("retries only failed candidates from a partially successful task", async () => {
    const failedCandidateId = "50000000-0000-0000-0000-000000000002";
    window.sessionStorage.setItem(LAST_EXTRACTION_JOB_KEY, JSON.stringify({
      jobId: "019feef3-396e-7041-4e4c-426270f42ce1",
      state: "succeeded",
      progress: 100,
      result: { results: [
        { candidate_id: candidate.candidate_id, ok: true },
        { candidate_id: failedCandidateId, ok: false, error: "provider failed" },
      ] },
      totalItems: 2,
      candidateIds: [candidate.candidate_id, failedCandidateId],
      updatedAt: "2026-08-10T20:00:00Z",
    }));
    const jobs = makeQuietJobs();
    renderApp(makeClient(), jobs);

    fireEvent.click(screen.getByRole("button", { name: "Retry failed extraction" }));

    await waitFor(() => expect(jobs.startCandidateExtraction).toHaveBeenCalledWith([failedCandidateId]));
  });

  it("clears stale candidate actions when a document starts a new workflow", async () => {
    const campaignClient = makeClient();
    renderApp(campaignClient);
    fireEvent.click(
      await screen.findByRole("button", {
        name: /The sanitized archive names a careful keeper/,
      }),
    );
    expect(await screen.findByLabelText("Editable extraction review")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back to candidate" }));
    expect(screen.getByRole("button", { name: "Re-extract this candidate" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /lore/ })[0]);
    fireEvent.click(await screen.findByRole("button", { name: /sanitized-keeper\.md/ }));

    expect(await screen.findByText("Review one candidate, or prepare every pending candidate in this document.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Extract pending candidates" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Re-extract this candidate" })).not.toBeInTheDocument();
  });

  it("makes reject disposition, stale refresh, and apply failure explicit", async () => {
    const staleProposal = { ...proposal, version_number: 2, content_hash: "d".repeat(64) };
    window.sessionStorage.setItem(
      REVIEW_STATE_KEY,
      JSON.stringify({
        selectedCandidateId: candidate.candidate_id,
        phase: "approved",
        proposal,
        approval,
      }),
    );
    const staleClient = makeClient({ getProposal: vi.fn().mockResolvedValue(staleProposal) });
    const staleView = renderApp(staleClient);
    expect(await screen.findByText("Stale proposal version")).toBeInTheDocument();
    expect(screen.getByText(/changed after the displayed version/)).toBeInTheDocument();
    staleView.unmount();
    window.sessionStorage.clear();

    const rejectClient = makeClient();
    const rejectView = renderApp(rejectClient);
    const rejectCandidate = await screen.findByRole("button", {
      name: /The sanitized archive names a careful keeper/,
    });
    await waitFor(() => expect(rejectCandidate).toBeEnabled());
    fireEvent.click(rejectCandidate);
    fireEvent.click(await screen.findByRole("button", { name: "Back to candidate" }));
    fireEvent.change(await screen.findByLabelText("Disposition reason"), {
      target: { value: "Not campaign truth" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(await screen.findByText("Candidate rejected")).toBeInTheDocument();
    expect(rejectClient.dispositionCandidate).toHaveBeenCalledWith(
      candidate.candidate_id,
      "rejected",
      "Not campaign truth",
    );
    rejectView.unmount();
    window.sessionStorage.clear();

    window.sessionStorage.setItem(
      REVIEW_STATE_KEY,
      JSON.stringify({
        selectedCandidateId: candidate.candidate_id,
        phase: "approved",
        proposal,
        approval,
      }),
    );
    const failingClient = makeClient({
      applyApproval: vi.fn().mockRejectedValue(new Error("Atomic application was rejected")),
    });
    renderApp(failingClient);
    const apply = await screen.findByRole("button", { name: "Apply approved change" });
    fireEvent.click(apply);
    expect(await screen.findByText("Approved and ready to apply")).toBeInTheDocument();
    expect(screen.getByText("Application failed: Atomic application was rejected")).toBeInTheDocument();
  });

  it("keeps a restored proposal locked until confirmation succeeds and offers retry", async () => {
    window.sessionStorage.setItem(
      REVIEW_STATE_KEY,
      JSON.stringify({
        selectedCandidateId: candidate.candidate_id,
        phase: "proposal_pending",
        proposal,
      }),
    );
    const getProposal = vi.fn()
      .mockRejectedValueOnce(new Error("Campaign Core temporarily unavailable"))
      .mockResolvedValueOnce(proposal);
    renderApp(makeClient({ getProposal }));

    expect(await screen.findByText("Confirmation failed.")).toBeInTheDocument();
    expect(screen.getAllByText("Campaign Core temporarily unavailable")).toHaveLength(1);
    expect(screen.getByRole("button", { name: /Approve and apply/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Retry confirmation" }));

    await waitFor(() => expect(getProposal).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("button", { name: /Approve and apply/ })).toBeEnabled());
    expect(screen.queryByText("Confirmation failed.")).not.toBeInTheDocument();
  });

  it("applies queue filters through CampaignClient", async () => {
    const campaignClient = makeClient();
    renderApp(campaignClient);
    await screen.findByRole("button", {
      name: /The sanitized archive names a careful keeper/,
    });
    fireEvent.change(screen.getByLabelText("Review status"), { target: { value: "rejected" } });

    await waitFor(() =>
      expect(campaignClient.listCandidates).toHaveBeenLastCalledWith(
        expect.objectContaining({
          review_status: "rejected",
        }),
      ),
    );
  });

  it("records a required reason when a candidate is deferred", async () => {
    const campaignClient = makeClient({
      dispositionCandidate: vi.fn().mockResolvedValue({
        disposition_id: "92000000-0000-0000-0000-000000000002",
        candidate_id: candidate.candidate_id,
        review_status: "deferred",
        reason: "Needs session-note comparison",
        created_at: "2026-08-01T12:01:00Z",
      }),
    });
    renderApp(campaignClient);
    const deferredCandidate = await screen.findByRole("button", {
      name: /The sanitized archive names a careful keeper/,
    });
    await waitFor(() => expect(deferredCandidate).toBeEnabled());
    fireEvent.click(deferredCandidate);
    fireEvent.click(await screen.findByRole("button", { name: "Back to candidate" }));
    fireEvent.change(await screen.findByLabelText("Disposition reason"), {
      target: { value: "Needs session-note comparison" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Defer" }));

    expect(await screen.findByText("Candidate deferred")).toBeInTheDocument();
    expect(campaignClient.dispositionCandidate).toHaveBeenCalledWith(
      candidate.candidate_id,
      "deferred",
      "Needs session-note comparison",
    );
    expect(JSON.parse(window.sessionStorage.getItem(REVIEW_STATE_KEY) ?? "{}")).toMatchObject({
      phase: "deferred",
      message: "Needs session-note comparison",
    });
  });

  it("resumes a persisted pending job after refresh instead of discarding it", async () => {
    const persistedJobId = "019fe949-209f-0980-4374-96fed322a597";
    window.sessionStorage.setItem(
      PENDING_JOB_KEY,
      JSON.stringify({
        jobId: persistedJobId,
        state: "running",
        progress: 55,
        updatedAt: "2026-08-01T12:00:00Z",
      }),
    );
    const jobs: JobPlatform = {
      startHealthCheck: vi.fn(),
      cancel: vi.fn(),
      startProseDraft: vi.fn(),
      startCandidateExtraction: vi.fn(),
      inspect: vi.fn().mockResolvedValue({
        jobId: persistedJobId,
        state: "succeeded",
        progress: 100,
        result: { status: "ok" },
        updatedAt: "2026-08-01T12:01:00Z",
      }),
    };
    render(<App campaignClient={makeClient()} jobPlatform={jobs} pollIntervalMs={1} />);
    fireEvent.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByText("Campaign Core check in progress")).toBeInTheDocument();
    await waitFor(() => expect(jobs.inspect).toHaveBeenCalledWith(persistedJobId));
    expect(await screen.findByText("Campaign Core is available")).toBeInTheDocument();
  });

  it("makes a background job start failure visible", async () => {
    const jobs: JobPlatform = {
      startHealthCheck: vi.fn().mockRejectedValue(new Error("No worker is available")),
      cancel: vi.fn(),
      startProseDraft: vi.fn(),
      startCandidateExtraction: vi.fn(),
      inspect: vi.fn(),
    };
    renderTools(makeClient(), jobs);
    fireEvent.click(screen.getByRole("button", { name: "Run check" }));
    expect(await screen.findByText(/No worker is available/)).toBeInTheDocument();
  });

  it("keeps AI model configuration out of Tools (it lives in Settings)", async () => {
    renderTools(makeClient(), makeQuietJobs());
    expect(screen.getByRole("button", { name: "Ask the archive" })).toBeInTheDocument();
    expect(screen.queryByText("AI model")).toBeNull();
    expect(screen.queryByRole("button", { name: "Activate profile" })).toBeNull();
  });

  it("manages per-purpose AI model profiles in Settings", async () => {
    const extractionProfile = {
      key: "deepseek-chat", purpose: "extraction", provider: "openrouter",
      model_slug: "deepseek/deepseek-chat", description: "Proven non-reasoning extraction profile.",
      reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1,
      selectable: true, suitability: "recommended",
    };
    const candidateProfile = {
      key: "mistral-candidate", purpose: "extraction", provider: "openrouter",
      model_slug: "mistralai/mistral-small", description: "Candidate under evaluation.",
      reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1,
      selectable: true, suitability: "candidate",
    };
    const activateAIProfile = vi.fn().mockResolvedValue({
      receipt_id: "94000000-0000-0000-0000-000000000002", purpose: "extraction",
      profile_key: "mistral-candidate", prompt_version: "extraction/8",
      activated_at: "2026-09-16T12:00:00Z",
    });
    render(<App campaignClient={makeClient({
      getAIConfiguration: vi.fn().mockResolvedValue({
        purposes: [
          { key: "extraction", label: "Claim extraction", description: "Proposes candidate claims.", prompt_version: "extraction/8", prompt_text: "Extract grounded claims." },
          { key: "prose", label: "Prose writing", description: "Drafts prose from selected material.", prompt_version: null, prompt_text: null },
        ],
        profiles: [
          extractionProfile,
          candidateProfile,
          {
            key: "deepseek-v4-flash", purpose: "prose", provider: "openrouter",
            model_slug: "deepseek/deepseek-v4-flash-0731", description: "First prose pick: cheap, fast, non-reasoning flash tier.",
            reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1,
            selectable: true, suitability: "candidate",
          },
        ],
        active_profile_by_purpose: { extraction: "deepseek-chat" },
        last_activation_by_purpose: {},
      }),
      activateAIProfile,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    const extractionPanel = await screen.findByRole("article", { name: "Claim extraction model" });
    expect(within(extractionPanel).getByText("deepseek/deepseek-chat")).toBeInTheDocument();
    expect(within(extractionPanel).getByText(/Prompt \(extraction\/8\)/)).toBeInTheDocument();
    // The prose purpose is visible with its candidate listed but not yet active.
    const prosePanel = screen.getByRole("article", { name: "Prose writing model" });
    expect(within(prosePanel).getByText(/No prose writing model active yet/)).toBeInTheDocument();
    expect(within(prosePanel).getByRole("option", { name: /deepseek\/deepseek-v4-flash-0731/ })).toBeInTheDocument();
    // Switching the extraction model activates through Core with the purpose.
    fireEvent.change(within(extractionPanel).getByRole("combobox", { name: "Claim extraction model profile" }), { target: { value: "mistral-candidate" } });
    fireEvent.click(within(extractionPanel).getByRole("button", { name: "Activate" }));
    await waitFor(() => expect(activateAIProfile).toHaveBeenCalledWith("mistral-candidate", "extraction"));
    expect(await screen.findByText(/Claim extraction model activated/)).toBeInTheDocument();
  });

  it("reviews and applies an overlapping claim decision with an audit reason", async () => {
    const snapshot = (id: string, assertion: string, recorded: string) => ({
      claim_id: id, assertion_text: assertion, state: "possible", authority: "brainstorm",
      visibility: "dm_only", recorded_at: recorded, source_paths: ["pcs/example.md"],
      snapshot_hash: id.replaceAll("-", "").padEnd(64, "a").slice(0, 64), is_current: true,
    });
    const overlap = {
      superseding: snapshot("63000000-0000-0000-0000-000000000001", "The hero may unite the nations.", "2026-08-13T06:00:00Z"),
      superseded: snapshot("63000000-0000-0000-0000-000000000002", "The hero might unite all nations.", "2026-08-12T06:00:00Z"),
      similarity: 0.88,
    };
    const reconcileClaims = vi.fn().mockResolvedValue({
      receipt_id: "64000000-0000-0000-0000-000000000001",
      change_set_id: "65000000-0000-0000-0000-000000000001",
      decision: "supersede",
      idempotent_replay: false,
    });
    renderTools(makeClient({ discoverClaimOverlaps: vi.fn().mockResolvedValue([overlap]), reconcileClaims }));

    fireEvent.click(await screen.findByRole("button", { name: /88% similar/ }));
    expect(screen.getByText("Newer claim")).toBeInTheDocument();
    expect(screen.getByText("Earlier claim")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Reconciliation reason"), { target: { value: "Reviewed duplicate" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));

    await waitFor(() => expect(reconcileClaims).toHaveBeenCalledWith(overlap, "supersede", "Reviewed duplicate"));
  });

  it("preserves a brainstorm thought and refreshes grounded continuity evidence", async () => {
    const openSession: BrainstormSession = {
      session_id: "66000000-0000-0000-0000-000000000001",
      title: "Northern archive",
      status: "open",
      started_at: "2026-08-30T12:00:00Z",
      thoughts: [],
      pins: [],
    };
    const capturedSession: BrainstormSession = {
      ...openSession,
      thoughts: [{
        thought_id: "67000000-0000-0000-0000-000000000001",
        sequence: 1,
        text: "The keeper might move the archive north.",
        source_document_id: "68000000-0000-0000-0000-000000000001",
        source_revision_id: "69000000-0000-0000-0000-000000000001",
        candidate_id: "6a000000-0000-0000-0000-000000000001",
        captured_at: "2026-08-30T12:01:00Z",
        mentions: [],
        evidence: {
          answer_mode: "answer",
          reasons: ["grounded_answer"],
          citations: ["lore/archive.md"],
          evidence: [{
            record_id: "6b000000-0000-0000-0000-000000000001",
            assertion: "The archive is currently housed beneath the old observatory.",
            citation: "lore/archive.md",
            state: "established",
            authority: "explicit_lore",
            role: "support",
          }],
        },
      }],
    };
    const startBrainstorm = vi.fn().mockResolvedValue(openSession);
    const captureBrainstormThought = vi.fn().mockResolvedValue(capturedSession);
    render(<App campaignClient={makeClient({ startBrainstorm, captureBrainstormThought })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Brainstorm" }));
    fireEvent.change(await screen.findByLabelText("Brainstorm title"), { target: { value: "Northern archive" } });
    fireEvent.click(screen.getByRole("button", { name: "Start brainstorm" }));
    fireEvent.change(await screen.findByLabelText("Next thought"), { target: { value: capturedSession.thoughts[0].text } });
    fireEvent.click(screen.getByRole("button", { name: "Preserve thought" }));

    expect(await screen.findByText(capturedSession.thoughts[0].text)).toBeInTheDocument();
    expect(screen.getByText("The archive is currently housed beneath the old observatory.")).toBeInTheDocument();
    expect(captureBrainstormThought).toHaveBeenCalledWith(openSession.session_id, capturedSession.thoughts[0].text, []);
  });

  it("completes a Brainstorm mention at the caret and submits its stable identity", async () => {
    const entity = { entity_id: "6c000000-0000-0000-0000-000000000001", canonical_name: "Malygos", entity_kind: "npc" as const, match_kind: "alias" as const, matched_name: "The Azure" };
    const openSession: BrainstormSession = { session_id: "6d000000-0000-0000-0000-000000000001", title: "Names", status: "open", started_at: "2026-09-05T12:00:00Z", thoughts: [], pins: [] };
    const captureBrainstormThought = vi.fn().mockResolvedValue(openSession);
    render(<App campaignClient={makeClient({ getOpenBrainstorm: vi.fn().mockResolvedValue(openSession), searchEntities: vi.fn().mockResolvedValue([entity]), captureBrainstormThought })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Brainstorm" }));
    const input = await screen.findByLabelText("Next thought");
    fireEvent.change(input, { target: { value: "Ask @Mal", selectionStart: 8 } });
    expect(await screen.findByRole("option", { name: /Malygos/ })).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => expect(input).toHaveValue("Ask @Malygos "));
    fireEvent.click(screen.getByRole("button", { name: "Preserve thought" }));

    await waitFor(() => expect(captureBrainstormThought).toHaveBeenCalledWith(
      openSession.session_id,
      "Ask @Malygos ",
      [{ entity_id: entity.entity_id, display_name: "Malygos", start_offset: 4, end_offset: 12 }],
    ));
  });

  it("searches, pins, and opens a dossier without losing the Brainstorm draft", async () => {
    const summary = { entry_id: "6e000000-0000-0000-0000-000000000001", canonical_name: "Malygos", entity_kind: "npc" as const, aliases: ["The Azure"], tags: ["deity"], current_claim_count: 1, source_count: 1 };
    const openSession: BrainstormSession = { session_id: "6f000000-0000-0000-0000-000000000001", title: "Context", status: "open", started_at: "2026-09-05T12:00:00Z", thoughts: [], pins: [] };
    const pinnedSession: BrainstormSession = { ...openSession, pins: [{ entity_id: summary.entry_id, canonical_name: summary.canonical_name, entity_kind: summary.entity_kind, position: 1, pinned_at: "2026-09-05T12:01:00Z" }] };
    const pinBrainstormEntity = vi.fn().mockResolvedValue(pinnedSession);
    const dossier = { ...summary, claims: [{ claim_id: "70000000-0000-0000-0000-000000000001", assertion_text: "Malygos intends to end mortality on Myrin.", state: "intended", authority: "npc_intention", visibility: "dm_only", recorded_at: "2026-09-05T12:00:00Z", source_paths: ["lore/malygos.md"], sources: [{ document_id: "71000000-0000-0000-0000-000000000001", path: "lore/malygos.md" }] }], claim_history: [], sources: [{ document_id: "71000000-0000-0000-0000-000000000001", path: "lore/malygos.md" }] };
    render(<App campaignClient={makeClient({ getOpenBrainstorm: vi.fn().mockResolvedValue(openSession), listLibraryEntries: vi.fn().mockResolvedValue([summary]), pinBrainstormEntity, getLibraryEntry: vi.fn().mockResolvedValue(dossier) })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Brainstorm" }));
    const thoughtInput = await screen.findByLabelText("Next thought");
    fireEvent.change(thoughtInput, { target: { value: "Keep this unfinished thought." } });
    fireEvent.change(screen.getByLabelText("Search campaign during brainstorm"), { target: { value: "Azure" } });
    fireEvent.click(screen.getByRole("button", { name: "Pin Malygos" }));
    await waitFor(() => expect(pinBrainstormEntity).toHaveBeenCalledWith(openSession.session_id, summary.entry_id));
    const pinnedContext = screen.getByText("Pinned context").closest("section");
    expect(pinnedContext).not.toBeNull();
    expect(within(pinnedContext!).getByRole("button", { name: "Unpin Malygos" })).toBeInTheDocument();
    fireEvent.click(within(pinnedContext!).getByRole("button", { name: /Malygos npc/ }));
    expect(await screen.findByText("Malygos intends to end mortality on Myrin.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close brainstorm dossier" }));
    expect(thoughtInput).toHaveValue("Keep this unfinished thought.");
  });

  it("shows a highlighted bounded canonical excerpt that expands to the full assertion", async () => {
    const romulus = { entry_id: "72000000-0000-0000-0000-000000000001", canonical_name: "Romulus", entity_kind: "npc" as const, aliases: [], tags: [], current_claim_count: 1, source_count: 1 };
    const openSession: BrainstormSession = { session_id: "73000000-0000-0000-0000-000000000001", title: "Countermove", status: "open", started_at: "2026-09-05T12:00:00Z", thoughts: [], pins: [] };
    const assertion = `Ruling Fleurite from the shadows of the throne. ${"Earlier status material. ".repeat(35)}Romulus commanded Ishi'go'dan to fly east to Mythis Minor and destroy the castle at Tsunadis, opening the way for cultists summoning Ragga'na'ken.`;
    const query = vi.fn().mockResolvedValue({
      answer_mode: "answer",
      evidence: [{ record_id: "74000000-0000-0000-0000-000000000001", assertion, citation: "npcs/Romulus.md#Current Status/Goals", state: "intended", authority: "npc_intention", role: "support" }],
      citations: ["npcs/Romulus.md#Current Status/Goals"], reasons: ["grounded_answer"],
    });
    const pinBrainstormEvidence = vi.fn().mockResolvedValue(openSession);
    render(<App campaignClient={makeClient({ getOpenBrainstorm: vi.fn().mockResolvedValue(openSession), listLibraryEntries: vi.fn().mockResolvedValue([romulus]), query, pinBrainstormEvidence })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Brainstorm" }));
    fireEvent.change(await screen.findByLabelText("Search campaign during brainstorm"), { target: { value: "Tsunadis" } });

    const directCategory = await screen.findByText("Direct matches");
    expect(directCategory.closest("details")).not.toHaveAttribute("open");
    fireEvent.click(directCategory);
    const result = await screen.findByRole("button", { name: /Expand canonical result/ });
    expect(within(result).getByText("Tsunadis", { selector: "mark" })).toBeInTheDocument();
    expect(result).not.toHaveTextContent("Ruling Fleurite from the shadows");
    expect(query).toHaveBeenCalledWith({ question: "Tsunadis", requester_visibility: { role: "dm" } }, expect.any(AbortSignal));
    fireEvent.click(screen.getByRole("button", { name: /Pin search evidence/ }));
    await waitFor(() => expect(pinBrainstormEvidence).toHaveBeenCalledWith(openSession.session_id, "74000000-0000-0000-0000-000000000001", "Tsunadis"));
    fireEvent.click(result);
    expect(screen.getByRole("button", { name: /Collapse canonical result/ })).toHaveTextContent("Ruling Fleurite from the shadows");
  });

  it("keeps graph context and its explanation when ten lexical matches compete", async () => {
    const openSession: BrainstormSession = { session_id: "73000000-0000-0000-0000-000000000001", title: "Graph context", status: "open", started_at: "2026-09-05T12:00:00Z", thoughts: [], pins: [] };
    const query = vi.fn().mockResolvedValue({
      answer_mode: "answer",
      evidence: [
        ...Array.from({ length: 10 }, (_, index) => ({ record_id: `lexical-${index}`, assertion: `Tsunadis lexical result ${index}`, citation: `encounters/${index}`, state: "established", authority: "explicit_lore", role: "support" })),
        { record_id: "graph-context", assertion: "The castle stands on Mythis Minor.", citation: "lore/islands", state: "established", authority: "explicit_lore", role: "context", graph_trace: ["Matched graph entity: Tsunadis", "Connected through: Tsunadis — located on → Mythis Minor"] },
      ],
      citations: [], reasons: [],
    });
    render(<App campaignClient={makeClient({ getOpenBrainstorm: vi.fn().mockResolvedValue(openSession), query })} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "Brainstorm" }));
    fireEvent.change(await screen.findByLabelText("Search campaign during brainstorm"), { target: { value: "Tsunadis" } });
    const relatedCategory = await screen.findByText("Related discoveries");
    expect(relatedCategory.closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("Direct matches").closest("details")).not.toHaveAttribute("open");
    fireEvent.click(relatedCategory);
    expect(screen.getByText("Direct matches").closest("details")).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("Direct matches"));
    expect(screen.getAllByRole("button", { name: /Expand search card/ })).toHaveLength(11);
    expect(screen.queryByText("Why these graph results appeared")).not.toBeInTheDocument();
    expect(screen.getByText("Tsunadis — located on → Mythis Minor")).toBeVisible();
    expect(screen.getByText("The castle stands on Mythis Minor.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Expand canonical result/ })).toHaveLength(11);
  });

  it("pins suggested evidence even when it has no owning entity", async () => {
    const recordId = "75000000-0000-0000-0000-000000000001";
    const assertion = "The Inflection Point is waiting for the final two leylines.";
    const openSession: BrainstormSession = {
      session_id: "76000000-0000-0000-0000-000000000001", title: "Countermove", status: "open", started_at: "2026-09-05T12:00:00Z", pins: [], thoughts: [{
        thought_id: "77000000-0000-0000-0000-000000000001", sequence: 1, text: "Romulus makes his final push.",
        source_document_id: "78000000-0000-0000-0000-000000000001", source_revision_id: "79000000-0000-0000-0000-000000000001",
        candidate_id: "7a000000-0000-0000-0000-000000000001", captured_at: "2026-09-05T12:01:00Z", mentions: [],
        evidence: { answer_mode: "answer", reasons: ["grounded_answer"], citations: ["gm/campaign-bible.md#Romulus"], evidence: [{ record_id: recordId, assertion, citation: "gm/campaign-bible.md#Romulus", state: "established", authority: "explicit_lore", role: "support" }] },
      }],
    };
    const pinnedSession: BrainstormSession = { ...openSession, evidence_pins: [{ record_id: recordId, assertion, citation: "gm/campaign-bible.md#Romulus", position: 1, pinned_at: "2026-09-05T12:02:00Z" }] };
    const pinBrainstormEvidence = vi.fn().mockResolvedValue(pinnedSession);
    render(<App campaignClient={makeClient({ getOpenBrainstorm: vi.fn().mockResolvedValue(openSession), pinBrainstormEvidence })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Brainstorm" }));
    fireEvent.click(await screen.findByRole("button", { name: "Pin suggested evidence" }));
    await waitFor(() => expect(pinBrainstormEvidence).toHaveBeenCalledWith(openSession.session_id, recordId));
    expect(screen.getByRole("button", { name: "Unpin suggested evidence" })).toBeInTheDocument();
  });

  it("opens the Identity page, shows counts, and records a create decision with manual alias and edited name", async () => {
    const gap = {
      surface: "White Cloaks", normalized_surface: "white cloaks",
      claims_with_phrase: 3, total_mentions: 4, retrieval_demand: 2,
      role_hint: false, suggested_canonical_name: "White Cloak Order", suggested_kind: "faction",
      related_surfaces: [],
      evidence: [{ claim_id: "97000000-0000-0000-0000-000000000001", excerpt: "Members of the White Cloaks collect tolls." }],
      alias_candidates: [],
    };
    const getIdentityGaps = vi.fn().mockResolvedValueOnce({ gaps: [gap], total_candidates: 129 })
      .mockResolvedValue({ gaps: [], total_candidates: 0 });
    const createIdentityEntity = vi.fn().mockResolvedValue({
      decision_id: "96000000-0000-0000-0000-00000000000a", kind: "create_entity",
      surface: "White Cloak Order", linked_claims: 3, idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({ getIdentityGaps, createIdentityEntity })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Identity" }));
    expect(await screen.findByText("Showing 1 of 129 unresolved surfaces")).toBeInTheDocument();
    expect((screen.getByLabelText("Canonical name for White Cloaks") as HTMLInputElement).value).toBe("White Cloak Order");
    expect(screen.getByText(/3 claims · 4 mentions/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Manual aliases for White Cloaks"), { target: { value: "The Cloaks" } });
    expect(screen.getByRole("button", { name: "Create with 1 alias" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Canonical name for White Cloaks"), { target: { value: "White Cloak Order" } });
    fireEvent.click(screen.getByRole("button", { name: "Create with 1 alias" }));
    await waitFor(() => expect(createIdentityEntity).toHaveBeenCalledWith(
      "White Cloak Order", "faction", expect.stringMatching(/^identity-create:/),
      ["White Cloaks"], ["The Cloaks"]));
    expect(await screen.findByText(/Created White Cloak Order as an identity with 2 aliases with receipt 96000000/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("No unresolved surfaces right now.")).toBeInTheDocument());
  });

  it("renders the conventions reference page with named components", async () => {
    render(<App campaignClient={makeClient()} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "Conventions" }));
    expect(await screen.findByRole("heading", { name: "Conventions" })).toBeInTheDocument();
    for (const label of ["Design tokens", "Buttons", "Panels & cards", "Entry pages", "Forms"]) {
      expect(screen.getByRole("heading", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText(/\.identity-full/)).toBeInTheDocument();
    expect(screen.getByText(/\.entry-page-actions/)).toBeInTheDocument();
    expect(screen.getByText(/\.secondary-button/)).toBeInTheDocument();
  });

  it("edits a queue-created location identity profile", async () => {
    const entry = {
      entry_id: "a1000000-0000-0000-0000-0000000000f1", canonical_name: "Far Realm",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      current_claim_count: 12, source_count: 0,
    };
    const savedProfile = {
      entity_id: entry.entry_id, version: 1, canonical_name: "Far Realm",
      status: "sealed", location_type: "planar region", parent_location: "Cosmology",
      player: null, race: null, sex: null, aliases: ["the Far Realm"], summary: "It presses.",
    };
    const getEntityProfile = vi.fn()
      .mockResolvedValueOnce(null)                      // first load: no profile
      .mockResolvedValueOnce(savedProfile);             // reload after save
    const updateEntityProfile = vi.fn().mockResolvedValue({
      receipt_id: "a2000000-0000-0000-0000-0000000000f2", entity_id: entry.entry_id,
      version: 1, idempotent_replay: false,
      alias_sync: { entity_name: "Far Realm", applied: ["the Far Realm"], removed: [], skipped_conflicting: [] },
    });
    const getLibraryEntry = vi.fn().mockResolvedValue({
      ...entry, claims: [], claim_history: [], sources: [],
    });
    const getIdentityGaps = vi.fn().mockResolvedValue({ gaps: [], total_candidates: 0 });
    const cosmology = { ...entry, entry_id: "a1000000-0000-0000-0000-0000000000c9", canonical_name: "Cosmology" };
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entry, cosmology]),
      getLibraryEntry, getEntityProfile, updateEntityProfile, getIdentityGaps,
      getTemplateVocabulary: vi.fn((vocabulary: string) => Promise.resolve(
        vocabulary === "location_type" ? [{ vocabulary, value: "planar region", retired: false }, { vocabulary, value: "region", retired: false }]
        : vocabulary === "status" ? [{ vocabulary, value: "sealed", retired: false }, { vocabulary, value: "active", retired: false }]
        : [])),
    })} jobPlatform={makeQuietJobs()} />);

    const entryButton = await screen.findByRole("button", { name: "Far Realm" });
    fireEvent.click(entryButton);
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(entry.entry_id));
    fireEvent.click(await screen.findByRole("button", { name: "Edit entry" }));
    // Vocabulary selects: values come from the template vocabulary, not free text.
    fireEvent.change(screen.getByLabelText("Identity location type"), { target: { value: "planar region" } });
    fireEvent.change(screen.getByLabelText("Identity status"), { target: { value: "sealed" } });
    // Parent location is an entity reference — picked from location entries.
    fireEvent.change(screen.getByLabelText("Identity parent location"), { target: { value: "Cosmology" } });
    fireEvent.change(screen.getByLabelText("Identity aliases"), { target: { value: "the Far Realm" } });
    fireEvent.click(screen.getByRole("button", { name: "Save identity profile" }));
    await waitFor(() => expect(updateEntityProfile).toHaveBeenCalledWith(
      entry.entry_id, expect.objectContaining({
        location_type: "planar region", status: "sealed", parent_location: "Cosmology",
        aliases: ["the Far Realm"], version: 0,
      })));
    expect(await screen.findByText(/Saved with receipt a2000000/)).toBeInTheDocument();
    expect(await screen.findByText(/added the Far Realm/)).toBeInTheDocument();
    // After save, the entry re-renders with the profile's hero fields.
    expect(await screen.findByText("planar region")).toBeInTheDocument();
  });

  it("shows faction members and corrects kind through the audited path", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Carpet Rollers",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [
        { member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Ruhrogue", role_title: null, is_leadership: false },
        { member_id: "b1000000-0000-0000-0000-0000000000m2", name: "Coreferra", role_title: null, is_leadership: false },
      ], current_claim_count: 9, source_count: 0,
    };
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 2, canonical_name: "Carpet Rollers",
      status: "active", base_location: "The manor in Unity", aliases: [], summary: "",
    });
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...faction, claims: [], claim_history: [], sources: [] });
    const proposeEntityKind = vi.fn().mockResolvedValue({
      proposal_id: "b2000000-0000-0000-0000-0000000000f2", version_number: 1,
      content_hash: "c".repeat(64), item: { item_id: "b3000000-0000-0000-0000-0000000000f3", target_id: faction.entry_id, before: {}, after: {} },
    });
    const approveEntityMetadataProposal = vi.fn().mockResolvedValue({ approval_id: "b4000000-0000-0000-0000-0000000000f4",
      proposal_id: "b2000000-0000-0000-0000-0000000000f2", proposal_version_id: "v1",
      reviewed_version: 1, content_hash: "c".repeat(64), item_ids: ["b3000000-0000-0000-0000-0000000000f3"],
      change_set_id: "b5000000-0000-0000-0000-0000000000f5", idempotency_key: "k", approved_at: "t", idempotent_replay: false });
    const applyApproval = vi.fn().mockResolvedValue({ receipt_id: "b6000000-0000-0000-0000-0000000000f6" });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, proposeEntityKind, approveEntityMetadataProposal, applyApproval,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Carpet Rollers" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    expect(await screen.findByText(/Ruhrogue/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    fireEvent.change(screen.getByLabelText("Identity kind correction"), { target: { value: "worldbuilding" } });
    await waitFor(() => expect(proposeEntityKind).toHaveBeenCalledWith(faction.entry_id, "worldbuilding"));
    await waitFor(() => expect(approveEntityMetadataProposal).toHaveBeenCalledWith(
      "b2000000-0000-0000-0000-0000000000f2", "b3000000-0000-0000-0000-0000000000f3", 1, "c".repeat(64)));
    await waitFor(() => expect(applyApproval).toHaveBeenCalled());
    expect((await screen.findAllByText(/Kind corrected to worldbuilding/)).length).toBeGreaterThan(0);
  });

  it("refreshes the faction roster in place after removing a member", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-0000000000f1", canonical_name: "Carpet Rollers",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [
        { member_id: "b1000000-0000-0000-0000-0000000000m1", name: "Ruhrogue", role_title: null, is_leadership: false },
        { member_id: "b1000000-0000-0000-0000-0000000000m2", name: "Coreferra", role_title: null, is_leadership: false },
      ], current_claim_count: 9, source_count: 0,
    };
    const memberRow = (name: string, index: number, role_title: string | null = null, is_leadership = false) => ({ member_id: `b1000000-0000-0000-0000-0000000000m${index + 1}`, name, role_title, is_leadership });
    const entryWithRoster = (members: string[]) => ({ ...faction, members: members.map((name, index) => memberRow(name, index)), claims: [], claim_history: [], sources: [] });
    const getLibraryEntry = vi.fn()
      .mockResolvedValueOnce(entryWithRoster(["Ruhrogue", "Coreferra"]))
      .mockResolvedValue(entryWithRoster(["Ruhrogue"]));
    const getEntityProfile = vi.fn().mockResolvedValue({
      entity_id: faction.entry_id, version: 2, canonical_name: "Carpet Rollers",
      status: "active", base_location: "The manor in Unity", aliases: [], summary: "",
    });
    const removeMembership = vi.fn().mockResolvedValue({
      decision_id: "b7000000-0000-0000-0000-0000000000f7", kind: "membership",
      surface: "Carpet Rollers", idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry, getEntityProfile, removeMembership,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Carpet Rollers" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    expect(screen.getAllByTitle("Remove membership")).toHaveLength(2);
    fireEvent.click(screen.getAllByTitle("Remove membership")[1]);
    await waitFor(() => expect(removeMembership).toHaveBeenCalledWith(
      faction.entry_id, "b1000000-0000-0000-0000-0000000000m2"));
    // The roster reloads in place: no loading flash, editor stays open.
    expect(screen.queryByText("Loading source…")).not.toBeInTheDocument();
    expect(getLibraryEntry).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.getAllByTitle("Remove membership")).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Save identity profile" })).toBeInTheDocument();
    expect(screen.getAllByText(/Removed Coreferra from Carpet Rollers/).length).toBeGreaterThan(0);
  });

  it("merges session events and audited decisions on the Log page, newest first", async () => {
    const decisions = [
      { decision_id: "c1000000-0000-0000-0000-0000000000d1", kind: "membership", surface: "Eustice in Inquisitors",
        decided_at: "2026-09-13T20:05:00Z", details: { action: "assign_role", role_name: "Grand Inquisitor", member_name: "Eustice" } },
      { decision_id: "c1000000-0000-0000-0000-0000000000d2", kind: "create_entity", surface: "Inquisitors",
        decided_at: "2026-09-13T20:01:00Z", details: null },
    ];
    const listRecentDecisions = vi.fn().mockResolvedValue(decisions);
    render(<App campaignClient={makeClient({ listRecentDecisions })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Log" }));
    // Audited decisions render with their structured summary and source.
    expect(await screen.findByText(/Eustice in Inquisitors/)).toBeInTheDocument();
    expect(screen.getByText(/assign role · role: Grand Inquisitor · member: Eustice/i)).toBeInTheDocument();
    expect(screen.getAllByText("Campaign Core audit").length).toBeGreaterThan(0);
    // Session events join the stream from the shared bus, newest first.
    fireEvent.click(screen.getByRole("button", { name: "Identity" }));
    fireEvent.click(screen.getByRole("button", { name: "Log" }));
    expect(screen.getByText(/audited decisions/)).toBeInTheDocument();
    // Errors filter narrows to failures only.
    fireEvent.click(screen.getByRole("button", { name: "Errors only" }));
    expect(screen.queryByText(/Eustice in Inquisitors/)).not.toBeInTheDocument();
  });

  it("writes a description that files as the entry's page and takes claims under the hood", async () => {
    const entity = {
      entry_id: "e1000000-0000-0000-0000-000000000001", canonical_name: "Ruh",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 0,
    };
    const claims = [
      { claim_id: "c1000000-0000-0000-0000-000000000001", assertion_text: "Ruh kept watch after the fall.", state: "observed", authority: "real_play", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "real_play", sources: [] },
      { claim_id: "c1000000-0000-0000-0000-000000000002", assertion_text: "Ruh speaks rarely.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact", sources: [] },
    ];
    const writeEntityDescription = vi.fn().mockResolvedValue({
      entity_id: entity.entry_id, document_id: "d1000000-0000-0000-0000-000000000003",
      revision_id: "r1000000-0000-0000-0000-000000000004", path: "entities/ruh.md", idempotent_replay: false });
    const getLibraryEntry = vi.fn()
      .mockResolvedValueOnce({ ...entity, claims, claim_history: [], sources: [] })
      .mockResolvedValue({ ...entity, claims, claim_history: [], sources: [] });
    const getEntityProfile = vi.fn().mockResolvedValue(null);
    const content = ["---", "type: entity-description", "---", "", "# Ruh", "", "A quiet presence.", "", "## Background", "", "Kept watch."].join("\n");
    const getSourceDocument = vi.fn().mockResolvedValue({
      document_id: "d1000000-0000-0000-0000-000000000003",
      source_revision_id: "r1000000-0000-0000-0000-000000000004",
      path: "entities/ruh.md", content, canonical_claims: [], claim_history: [] });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry, getEntityProfile, getSourceDocument, writeEntityDescription,
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Ruh" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(entity.entry_id));
    const hood = screen.getAllByText(/Records —/)[0].closest("details.records-hood");
    expect(hood).not.toBeNull();
    expect(hood!.querySelector(".canonical-claim-list")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Write description for Ruh" }));
    fireEvent.change(await screen.findByLabelText("Entity description"), { target: { value: "A quiet presence at the camp's edge." } });
    fireEvent.click(screen.getByRole("button", { name: "File description" }));
    await waitFor(() => expect(writeEntityDescription).toHaveBeenCalledWith(
      entity.entry_id, "A quiet presence at the camp's edge.",
      ["c1000000-0000-0000-0000-000000000001", "c1000000-0000-0000-0000-000000000002"],
      expect.stringMatching(/^entity-description:/), undefined));
    expect(await screen.findByText(/Description filed — Ruh has its page/)).toBeInTheDocument();
  });
  it("flags a stale authored page and revises it as a new revision of the same document", async () => {
    const entity = {
      entry_id: "e3000000-0000-0000-0000-000000000001", canonical_name: "Ruh",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 1,
    };
    const claim = (id: string, text: string) => ({
      claim_id: id, assertion_text: text, state: "observed", authority: "real_play",
      visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z",
      projection: "real_play" as const, sources: [],
    });
    const claims = [
      claim("c3000000-0000-0000-0000-000000000001", "Ruh kept watch after the fall."),
      claim("c3000000-0000-0000-0000-000000000002", "Ruh speaks rarely."),
    ];
    const claimHistory = [{
      ...claims[0],
      superseded_by_claim_id: "c3000000-0000-0000-0000-000000000009",
      supersession_reason: "corrected at the table",
    }];
    const pageContent = "# Ruh\n\nA quiet presence at the camp's edge.";
    const writeEntityDescription = vi.fn().mockResolvedValue({
      entity_id: entity.entry_id, document_id: "d3000000-0000-0000-0000-000000000003",
      revision_id: "r3000000-0000-0000-0000-000000000005", path: "entities/ruh.md", idempotent_replay: false });
    const getSourceDocument = vi.fn().mockResolvedValue({
      document_id: "d3000000-0000-0000-0000-000000000003",
      source_revision_id: "r3000000-0000-0000-0000-000000000004",
      path: "entities/ruh.md", content: pageContent,
      document_type: "entity-description",
      referenced_claims: ["c3000000-0000-0000-0000-000000000001", "c3000000-0000-0000-0000-000000000002"],
      canonical_claims: [], claim_history: claimHistory });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...entity, claims, claim_history: claimHistory, sources: [{ document_id: "d3000000-0000-0000-0000-000000000003", path: "entities/ruh.md" }] }),
      getEntityProfile: vi.fn().mockResolvedValue(null),
      getSourceDocument, writeEntityDescription,
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Ruh" }));
    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("1 of 2 referenced records changed");
    fireEvent.click(within(banner).getByRole("button", { name: "Revise description" }));
    const textarea = await screen.findByLabelText("Entity description");
    expect(textarea).toHaveValue(pageContent);
    fireEvent.click(screen.getByRole("button", { name: "File description" }));
    await waitFor(() => expect(writeEntityDescription).toHaveBeenCalledWith(
      entity.entry_id, pageContent,
      ["c3000000-0000-0000-0000-000000000001", "c3000000-0000-0000-0000-000000000002"],
      expect.stringMatching(/^entity-description:/),
      "d3000000-0000-0000-0000-000000000003"));
    expect(await screen.findByText(/Description revised — Ruh/)).toBeInTheDocument();
  });
  it("runs drafting as a background job through the drafts pen and claims the result", async () => {
    const entity = {
      entry_id: "e6000000-0000-0000-0000-000000000001", canonical_name: "Fleurite",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 2, source_count: 0,
    };
    const claims = [
      { claim_id: "c6000000-0000-0000-0000-000000000001", assertion_text: "Fleurite is a region and city-state within Illisan.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
      { claim_id: "c6000000-0000-0000-0000-000000000002", assertion_text: "The walled settlement is the only survivor in the region.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
    ];
    const proseJobId = "019fe949-209f-0980-4374-96fed322a59b";
    const startProseDraft = vi.fn().mockResolvedValue({ jobId: proseJobId, state: "queued", progress: 5, updatedAt: "2026-09-17T12:00:00Z" });
    const inspect = vi.fn().mockResolvedValue({
      jobId: proseJobId, state: "succeeded", progress: 100,
      result: {
        draft_text: "Fleurite is a region and city-state within Illisan [1].",
        cited_keys: ["claim:c6000000-0000-0000-0000-000000000001"],
        model_slug: "deepseek/deepseek-v4-flash-0731", prompt_version: "prose/3",
        prompt_tokens: 120, completion_tokens: 340,
      },
      updatedAt: "2026-09-17T12:00:20Z",
    });
    const jobs: JobPlatform = { ...makeQuietJobs(), startProseDraft, inspect };
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...entity, claims, claim_history: [], sources: [] }),
      getAIConfiguration: vi.fn().mockResolvedValue({
        purposes: [
          { key: "extraction", label: "Claim extraction", description: "Proposes claims.", prompt_version: "extraction/8", prompt_text: "Extract." },
          { key: "prose", label: "Prose writing", description: "Drafts prose.", prompt_version: null, prompt_text: null },
        ],
        profiles: [{ key: "deepseek-v4-flash", purpose: "prose", provider: "openrouter", model_slug: "deepseek/deepseek-v4-flash-0731", description: "First prose pick.", reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1, selectable: true, suitability: "candidate" }],
        active_profile_by_purpose: { extraction: "deepseek-chat", prose: "deepseek-v4-flash" },
        last_activation_by_purpose: {},
      }),
    })} jobPlatform={jobs} />);

    fireEvent.click(await screen.findByRole("button", { name: "Fleurite" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Fleurite" }));
    fireEvent.click(await screen.findByRole("button", { name: "Draft from selected" }));
    // The composer is released immediately — the job runs in the background.
    await waitFor(() => expect(startProseDraft).toHaveBeenCalledWith(expect.objectContaining({
      subject: "Fleurite",
      subject_kind: "location",
      material: [
        { key: "claim:c6000000-0000-0000-0000-000000000001", kind: "claim", text: "Fleurite is a region and city-state within Illisan.", state: "established" },
        { key: "claim:c6000000-0000-0000-0000-000000000002", kind: "claim", text: "The walled settlement is the only survivor in the region.", state: "established" },
      ],
    })), { timeout: 4000 });
    expect(await screen.findAllByText(/Draft queued/).then((found) => found.length > 0)).toBe(true);
    // The pen holds the finished draft with its support line.
    expect(await screen.findByRole("button", { name: "Return to draft" }, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByText(/machine-drafted · deepseek\/deepseek-v4-flash-0731/)).toBeInTheDocument();
    // Claiming loads the prose into the guarded composer, markers stripped,
    // with the citations mirrored into the claim selection (1 of 2, not all).
    fireEvent.click(screen.getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByLabelText("Entity description", {}, { timeout: 4000 })).toHaveValue(
      "Fleurite is a region and city-state within Illisan.");
    expect(screen.getByText("Gathered claims (1 of 2 referenced)")).toBeInTheDocument();
  });
  it("files a claimed draft on an imported-paged entry as a NEW page, not a revision of the imported doc", async () => {
    const paged = {
      entry_id: "ea000000-0000-0000-0000-000000000001", canonical_name: "Bastok",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 1,
    };
    const claims = [
      { claim_id: "ca000000-0000-0000-0000-000000000001", assertion_text: "Bastok trades ore.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
    ];
    const proseJobId = "019fe949-209f-0980-4374-96fed322a59f";
    const startProseDraft = vi.fn().mockResolvedValue({ jobId: proseJobId, state: "queued", progress: 5, updatedAt: "2026-09-18T12:00:00Z" });
    const inspect = vi.fn().mockResolvedValue({
      jobId: proseJobId, state: "succeeded", progress: 100,
      result: {
        draft_text: "Bastok trades ore [1].",
        cited_keys: ["claim:ca000000-0000-0000-0000-000000000001"],
        model_slug: "deepseek/deepseek-v4-flash-0731", prompt_version: "prose/3",
        prompt_tokens: 80, completion_tokens: 150,
      },
      updatedAt: "2026-09-18T12:00:12Z",
    });
    // The authored page joins the document list only once it is filed.
    let authoredFiled = false;
    const writeEntityDescription = vi.fn(async (...args: unknown[]) => {
      const receipt = await Promise.resolve({
        entity_id: paged.entry_id, document_id: "da000000-0000-0000-0000-000000000003",
        revision_id: "ra000000-0000-0000-0000-000000000004", path: "entities/bastok.md", idempotent_replay: false,
      });
      authoredFiled = true;
      void args;
      return receipt;
    });
    const jobs: JobPlatform = { ...makeQuietJobs(), startProseDraft, inspect };
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([paged]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...paged, claims, claim_history: [], sources: [{ document_id: "da000000-0000-0000-0000-000000000002", path: "locations/bastok.md" }] }),
      getSourceDocument: vi.fn((documentId: string) => Promise.resolve(documentId === "da000000-0000-0000-0000-000000000003"
        ? { document_id: "da000000-0000-0000-0000-000000000003", source_revision_id: "ra000000-0000-0000-0000-000000000006", path: "entities/bastok.md", content: "Bastok trades ore and always has.", document_type: "entity-description", referenced_claims: ["ca000000-0000-0000-0000-000000000001"], canonical_claims: [], claim_history: [] }
        : { document_id: "da000000-0000-0000-0000-000000000002",
        source_revision_id: "ra000000-0000-0000-0000-000000000005",
        path: "locations/bastok.md",
        content: "---\ntype: location\n---\n\n# Bastok\n\nA trade city.", canonical_claims: [], claim_history: [] })),
      getAIConfiguration: vi.fn().mockResolvedValue({
        purposes: [
          { key: "extraction", label: "Claim extraction", description: "Proposes claims.", prompt_version: "extraction/8", prompt_text: "Extract." },
          { key: "prose", label: "Prose writing", description: "Drafts prose.", prompt_version: null, prompt_text: null },
        ],
        profiles: [{ key: "deepseek-v4-flash", purpose: "prose", provider: "openrouter", model_slug: "deepseek/deepseek-v4-flash-0731", description: "First prose pick.", reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1, selectable: true, suitability: "candidate" }],
        active_profile_by_purpose: { extraction: "deepseek-chat", prose: "deepseek-v4-flash" },
        last_activation_by_purpose: {},
      }),
      writeEntityDescription,
      listSourceDocuments: vi.fn(() => Promise.resolve(authoredFiled
        ? { items: [
          { document_id: "da000000-0000-0000-0000-000000000003", path: "entities/bastok.md", classification: "durable_evidence", candidate_count: 0, extraction_count: 0, open_review_count: 0, missing_source: false },
        ], total: 1, limit: 500, offset: 0 }
        : { items: [], total: 0, limit: 500, offset: 0 })),
    })} jobPlatform={jobs} />);

    fireEvent.click(await screen.findByRole("button", { name: "Bastok" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Bastok" }));
    fireEvent.click(await screen.findByRole("button", { name: "Draft from selected" }));
    fireEvent.click(await screen.findByRole("button", { name: "Return to draft" }, { timeout: 4000 }));
    fireEvent.click(await screen.findByRole("button", { name: "File description" }));
    await waitFor(() => expect(writeEntityDescription).toHaveBeenCalled());
    // The imported page document is NOT the revision target — the claimed
    // draft files fresh (no document id), beside the imported evidence.
    const call = writeEntityDescription.mock.calls[0];
    expect(call[4]).toBeUndefined();
    expect(await screen.findByText(/Description filed — Bastok has its page/)).toBeInTheDocument();
    // The authored page becomes the entry's page: prose rendered under the
    // canonical name and kind, the authored-page banner with its Revise
    // action, and no write-description button (the page exists).
    expect(await screen.findByText("Bastok trades ore and always has.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bastok" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revise description for Bastok" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Write description for Bastok" })).toBeNull();
  });
  it("manages floating trays from Settings — sides move, hidden trays show no launcher", async () => {
    const entity = {
      entry_id: "e9000000-0000-0000-0000-000000000001", canonical_name: "Ruh",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 0,
    };
    const claims = [
      { claim_id: "c9000000-0000-0000-0000-000000000001", assertion_text: "Ruh kept watch.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
    ];
    const startProseDraft = vi.fn().mockResolvedValue({ jobId: "019fe949-209f-0980-4374-96fed322a59e", state: "queued", progress: 5, updatedAt: "2026-09-17T12:00:00Z" });
    // Keep the prose job running — this test exercises the launcher, not the result.
    const inspect = vi.fn().mockResolvedValue({ jobId: "019fe949-209f-0980-4374-96fed322a59e", state: "running", progress: 40, updatedAt: "2026-09-17T12:00:02Z" });
    const jobs: JobPlatform = { ...makeQuietJobs(), startProseDraft, inspect };
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...entity, claims, claim_history: [], sources: [] }),
      getAIConfiguration: vi.fn().mockResolvedValue({
        purposes: [
          { key: "extraction", label: "Claim extraction", description: "Proposes claims.", prompt_version: "extraction/8", prompt_text: "Extract." },
          { key: "prose", label: "Prose writing", description: "Drafts prose.", prompt_version: null, prompt_text: null },
        ],
        profiles: [{ key: "deepseek-v4-flash", purpose: "prose", provider: "openrouter", model_slug: "deepseek/deepseek-v4-flash-0731", description: "First prose pick.", reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1, selectable: true, suitability: "candidate" }],
        active_profile_by_purpose: { extraction: "deepseek-chat", prose: "deepseek-v4-flash" },
        last_activation_by_purpose: {},
      }),
    })} jobPlatform={jobs} />);

    // Queue a draft so the Drafts tray launcher exists (the array anchors right by default).
    fireEvent.click(await screen.findByRole("button", { name: "Ruh" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Ruh" }));
    fireEvent.click(await screen.findByRole("button", { name: "Draft from selected" }));
    await waitFor(() => expect(startProseDraft).toHaveBeenCalled(), { timeout: 4000 });
    // Queueing opens the tray; close it so its launcher is the surface under test.
    fireEvent.click(screen.getByRole("button", { name: "Close Drafts tray" }));
    const launcher = await screen.findByRole("button", { name: /^Drafts/ });
    expect(launcher.closest(".tray-dock")).toHaveClass("right");
    // The manager moves the ARRAY to the left anchor; hiding a tray drops its launcher.
    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    fireEvent.change(await screen.findByLabelText("Tray array anchor"), { target: { value: "left" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Library" })[0]);
    await waitFor(() => expect(screen.getByRole("button", { name: /^Drafts/ }).closest(".tray-dock")).toHaveClass("left"));
    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Show Drafts tray launcher/ }));
    fireEvent.click(screen.getAllByRole("button", { name: "Library" })[0]);
    await waitFor(() => expect(screen.queryByRole("button", { name: /^Drafts/ })).toBeNull());
  });
  it("queues a name for Lore, gathers evidence, and creates the entry", async () => {
    const createIdentityEntity = vi.fn().mockResolvedValue({
      decision_id: "99000000-0000-0000-0000-000000000001",
      kind: "create_entity",
      surface: "Tsunadis",
      entity_id: "99000000-0000-0000-0000-000000000002",
      linked_claims: 0,
      idempotent_replay: false,
    });
    const writeEntityDescription = vi.fn().mockResolvedValue({
      entity_id: "99000000-0000-0000-0000-000000000002",
      document_id: "99000000-0000-0000-0000-000000000003",
      revision_id: "99000000-0000-0000-0000-000000000004",
      path: "entities/tsunadis.md", idempotent_replay: false,
    });
    render(<App campaignClient={makeClient({
      createIdentityEntity, writeEntityDescription,
      searchEntities: vi.fn().mockResolvedValue([]),
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Lore" }));
    // Queue a name
    fireEvent.change(await screen.findByLabelText("Lore queue name"), { target: { value: "Tsunadis" } });
    fireEvent.click(screen.getByRole("button", { name: "Queue for Lore" }));
    expect(await screen.findByText("Tsunadis")).toBeInTheDocument();
    // Pick it up
    fireEvent.click(screen.getByRole("button", { name: "Work this" }));
    expect(await screen.findByText(/Creating: Tsunadis/)).toBeInTheDocument();
    expect(await screen.findByText(/No claims mention this name yet/)).toBeInTheDocument();
    // Write the description and create
    fireEvent.change(screen.getByLabelText("Lore description"), { target: { value: "A coastal city on the Shandriz Channel." } });
    fireEvent.click(screen.getByRole("button", { name: /Create Tsunadis as location/ }));
    await waitFor(() => expect(createIdentityEntity).toHaveBeenCalledWith("Tsunadis", "location", expect.stringMatching(/^lore-create:/)));
    await waitFor(() => expect(writeEntityDescription).toHaveBeenCalled());
    expect(await screen.findByText(/Created Tsunadis as a location/)).toBeInTheDocument();
  });
  it("runs the link audit from Tools and navigates to findings", async () => {
    const entity = {
      entry_id: "ed000000-0000-0000-0000-000000000001", canonical_name: "Romulus",
      entity_kind: "npc" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 5, source_count: 2,
    };
    const getLinkAudit = vi.fn().mockResolvedValue({
      audited_at: "2026-09-19T12:00:00Z",
      findings: [
        { kind: "wrong_page_borrow", entity_id: entity.entry_id, entity_name: "Romulus", entity_kind: "npc", document_id: "dd000000-0000-0000-0000-000000000002", document_path: "lore/the-wrath-of-romulus.md", detail: "'lore/the-wrath-of-romulus.md' carries tokens belonging to other entities: The Wrath of Romulus" },
      ],
    });
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...entity, claims: [], claim_history: [], sources: [] });
    render(<App campaignClient={makeClient({
      getLinkAudit,
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(screen.getByRole("button", { name: "Tools" }));
    fireEvent.click(screen.getByRole("button", { name: "Run audit" }));
    await waitFor(() => expect(getLinkAudit).toHaveBeenCalled());
    expect(await screen.findByText(/1 finding/)).toBeInTheDocument();
    expect(screen.getByText(/the-wrath-of-romulus/)).toBeInTheDocument();
    // Navigate to the finding's entity.
    fireEvent.click(screen.getByRole("button", { name: "Open Romulus" }));
    await waitFor(() => expect(getLibraryEntry).toHaveBeenCalledWith(entity.entry_id));
  });
  it("opens Ask-the-archive from the topbar magnifier as a tray, off the Tools page", async () => {
    render(<App campaignClient={makeClient()} jobPlatform={makeQuietJobs()} />);
    fireEvent.click(screen.getByRole("button", { name: "Tools" }));
    // The hero is gone from the page body; the magnifier opens the tray.
    expect(screen.queryByRole("heading", { name: /Ask the archive/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Ask the archive" }));
    expect(await screen.findByLabelText("Campaign question")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close Ask the archive" }));
    await waitFor(() => expect(screen.queryByLabelText("Campaign question")).toBeNull());
  });
  it("gathers relations in two layers and drafts from claims plus selected relations", async () => {
    const faction = {
      entry_id: "e8000000-0000-0000-0000-000000000001", canonical_name: "Fleurite Exiles",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [{ member_id: "m1", name: "Jace Valamacke", role_title: "Leader of the Rebellion", is_leadership: true }],
      related: ["Goodman's City"], current_claim_count: 1, source_count: 0,
    };
    const claims = [
      { claim_id: "c8000000-0000-0000-0000-000000000001", assertion_text: "The Exiles camp outside the walls.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
    ];
    const getEntityGraphNeighborhood = vi.fn().mockResolvedValue([
      { key: "graph:0", text: "Ruh is a member of the White Cloaks", backing: "audited membership record" },
      { key: "graph:1", text: "Frequently appears with Peter le Fleur (4 shared documents)", backing: "derived co-mention association" },
    ]);
    const startProseDraft = vi.fn().mockResolvedValue({ jobId: "019fe949-209f-0980-4374-96fed322a59d", state: "queued", progress: 5, updatedAt: "2026-09-17T12:00:00Z" });
    const jobs: JobPlatform = { ...makeQuietJobs(), startProseDraft };
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry: vi.fn().mockResolvedValue({
        ...faction, claims, claim_history: [], sources: [],
        roles: [{ name: "Leader of the Rebellion", is_leadership: true, holder_names: ["Jace Valamacke"] }],
      }),
      getAIConfiguration: vi.fn().mockResolvedValue({
        purposes: [
          { key: "extraction", label: "Claim extraction", description: "Proposes claims.", prompt_version: "extraction/8", prompt_text: "Extract." },
          { key: "prose", label: "Prose writing", description: "Drafts prose.", prompt_version: null, prompt_text: null },
        ],
        profiles: [{ key: "deepseek-v4-flash", purpose: "prose", provider: "openrouter", model_slug: "deepseek/deepseek-v4-flash-0731", description: "First prose pick.", reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1, selectable: true, suitability: "candidate" }],
        active_profile_by_purpose: { extraction: "deepseek-chat", prose: "deepseek-v4-flash" },
        last_activation_by_purpose: {},
      }),
      getEntityGraphNeighborhood,
    })} jobPlatform={jobs} />);

    fireEvent.click(await screen.findByRole("button", { name: "Fleurite Exiles" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Fleurite Exiles" }));
    // Base layer: canonical roles/members show as selectable relation rows,
    // and the relations panel is present for every entry (grey, graph off).
    expect(await screen.findByText(/Role Leader of the Rebellion \(unique leadership seat ★\)/)).toBeInTheDocument();
    expect(screen.getByText(/Jace Valamacke is a member/)).toBeInTheDocument();
    const panel = screen.getByText(/Gathered relations/).closest("details.relations-panel") as HTMLElement;
    expect(panel).not.toHaveClass("graph-enabled");
    // Expansion layer: the checkbox enables the panel and loads the
    // neighborhood, which arrives pre-selected.
    fireEvent.click(within(panel).getByRole("checkbox", { name: /Include graph neighborhood/ }));
    await waitFor(() => expect(getEntityGraphNeighborhood).toHaveBeenCalledWith(faction.entry_id));
    expect(panel).toHaveClass("graph-enabled");
    expect(await screen.findByText(/Ruh is a member of the White Cloaks/)).toBeInTheDocument();
    // Drafting queues both layers as background job material.
    fireEvent.click(screen.getByRole("button", { name: "Draft from selected" }));
    await waitFor(() => expect(startProseDraft).toHaveBeenCalledWith(expect.objectContaining({
      material: expect.arrayContaining([
        expect.objectContaining({ kind: "claim", text: "The Exiles camp outside the walls." }),
        expect.objectContaining({ kind: "relation", key: "relation:role:Leader of the Rebellion" }),
        expect.objectContaining({ kind: "relation", key: "relation:graph:0" }),
      ]),
    })));
    // AI actions carry the wand mark.
    expect(screen.getByRole("button", { name: "Draft from selected" }).querySelector("svg.wand-icon")).not.toBeNull();
  });
  it("keeps a failed draft job in the pen and records it in the toast and persisted log", async () => {
    const entity = {
      entry_id: "e7000000-0000-0000-0000-000000000001", canonical_name: "Ruh",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 0,
    };
    const claims = [
      { claim_id: "c7000000-0000-0000-0000-000000000001", assertion_text: "Ruh kept watch.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] },
    ];
    const proseJobId = "019fe949-209f-0980-4374-96fed322a59c";
    const startProseDraft = vi.fn().mockResolvedValue({ jobId: proseJobId, state: "queued", progress: 5, updatedAt: "2026-09-17T12:00:00Z" });
    const inspect = vi.fn().mockResolvedValue({
      jobId: proseJobId, state: "failed", progress: 0,
      error: "Campaign Core rejected the draft: the model could not satisfy the drafting contract",
      updatedAt: "2026-09-17T12:00:09Z",
    });
    const jobs: JobPlatform = { ...makeQuietJobs(), startProseDraft, inspect };
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([entity]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...entity, claims, claim_history: [], sources: [] }),
      getAIConfiguration: vi.fn().mockResolvedValue({
        purposes: [
          { key: "extraction", label: "Claim extraction", description: "Proposes claims.", prompt_version: "extraction/8", prompt_text: "Extract." },
          { key: "prose", label: "Prose writing", description: "Drafts prose.", prompt_version: null, prompt_text: null },
        ],
        profiles: [{ key: "deepseek-v4-flash", purpose: "prose", provider: "openrouter", model_slug: "deepseek/deepseek-v4-flash-0731", description: "First prose pick.", reasoning_effort: null, max_tokens: 8192, timeout_seconds: 90, retry_limit: 1, selectable: true, suitability: "candidate" }],
        active_profile_by_purpose: { extraction: "deepseek-chat", prose: "deepseek-v4-flash" },
        last_activation_by_purpose: {},
      }),
    })} jobPlatform={jobs} />);

    fireEvent.click(await screen.findByRole("button", { name: "Ruh" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Ruh" }));
    fireEvent.click(await screen.findByRole("button", { name: "Draft from selected" }));
    // The failed job stays in the pen with its error until dismissed.
    expect(await screen.findAllByText(/could not satisfy the drafting contract/, {}, { timeout: 4000 }).then((found) => found.length > 0)).toBe(true);
    expect(screen.getByRole("button", { name: "Discard draft for Ruh" })).toBeInTheDocument();
    // The bus records the failure — toast now, log persistently.
    await waitFor(() => expect(toast.logEntries().some((entry) => entry.kind === "error" && entry.message.includes("Draft failed for Ruh"))).toBe(true));
    expect(JSON.parse(globalThis.localStorage.getItem("dm-assistant.sessionLog") ?? "[]")
      .some((entry: { kind: string; message: string }) => entry.kind === "error" && entry.message.includes("Draft failed for Ruh"))).toBe(true);
  });
  it("gives page-backed entries edit and write-description affordances (ADR-0016)", async () => {
    const paged = {
      entry_id: "e4000000-0000-0000-0000-000000000001", canonical_name: "Bastok",
      entity_kind: "location" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 1, source_count: 1,
    };
    const claims = [{ claim_id: "c4000000-0000-0000-0000-000000000001", assertion_text: "Bastok trades ore.", state: "established", authority: "explicit_lore", visibility: "dm_only", conditional: false, recorded_at: "2026-01-01T00:00:00Z", projection: "lore_fact" as const, sources: [] }];
    const getLibraryEntry = vi.fn().mockResolvedValue({ ...paged, claims, claim_history: [], sources: [{ document_id: "d4000000-0000-0000-0000-000000000002", path: "locations/bastok.md" }] });
    const getSourceDocument = vi.fn().mockResolvedValue({
      document_id: "d4000000-0000-0000-0000-000000000002",
      source_revision_id: "r4000000-0000-0000-0000-000000000003",
      path: "locations/bastok.md",
      content: "---\ntype: location\n---\n\n# Bastok\n\nA trade city.", canonical_claims: [], claim_history: [] });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([paged]),
      getLibraryEntry, getSourceDocument,
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Bastok" }));
    // The imported page backs the entry, but the entity record is editable…
    expect(await screen.findByRole("button", { name: "Edit entry" })).toBeInTheDocument();
    // …and the authored page can be written beside the imported evidence.
    expect(screen.getByRole("button", { name: "Write description for Bastok" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit entry" }));
    expect(await screen.findByRole("article", { name: "Identity profile editor" })).toBeInTheDocument();
  });
  it("closes a clean composer on entry switch and blocks the switch while a draft is dirty (ADR-0016)", async () => {
    const ruh = { entry_id: "e5000000-0000-0000-0000-000000000001", canonical_name: "Ruh", entity_kind: "location" as const, aliases: [], misspellings: [], tags: [], members: [], current_claim_count: 1, source_count: 0 };
    const bastok = { entry_id: "e5000000-0000-0000-0000-000000000002", canonical_name: "Bastok", entity_kind: "location" as const, aliases: [], misspellings: [], tags: [], members: [], current_claim_count: 1, source_count: 0 };
    const getLibraryEntry = vi.fn((id: string) => Promise.resolve(
      id === ruh.entry_id
        ? { ...ruh, claims: [], claim_history: [], sources: [] }
        : { ...bastok, claims: [], claim_history: [], sources: [] }));
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([ruh, bastok]),
      getLibraryEntry,
      listSourceDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 500, offset: 0 }),
    })} jobPlatform={makeQuietJobs()} />);

    // Clean composer: switching entries closes it without asking.
    fireEvent.click(await screen.findByRole("button", { name: "Ruh" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Ruh" }));
    fireEvent.change(await screen.findByLabelText("Entity description"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Bastok" }));
    await waitFor(() => expect(screen.queryByLabelText("Entity description")).toBeNull());

    // Dirty composer: the switch is blocked until the draft is resolved.
    fireEvent.click(screen.getByRole("button", { name: "Ruh" }));
    fireEvent.click(await screen.findByRole("button", { name: "Write description for Ruh" }));
    fireEvent.change(await screen.findByLabelText("Entity description"), { target: { value: "A quiet presence." } });
    fireEvent.click(screen.getByRole("button", { name: "Bastok" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/description draft/);
    expect(screen.getByLabelText("Entity description")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Discard changes" }));
    await waitFor(() => expect(screen.queryByLabelText("Entity description")).toBeNull());
    expect(await screen.findByRole("heading", { name: "Bastok" })).toBeInTheDocument();
  });
  it("sets life status from the character editor dropdown for continued backfill", async () => {
    const npc = {
      entry_id: "a1000000-0000-0000-0000-000000000010", canonical_name: "Goodman",
      entity_kind: "npc" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 3, source_count: 1,
    };
    const profile = { entity_id: npc.entry_id, version: 1, canonical_name: "Goodman",
      status: "active", base_location: null, aliases: [], summary: "",
      life_status: null, life_status_since: null, life_status_claim_id: null };
    const getEntityProfile = vi.fn().mockResolvedValue(profile);
    const updateEntityProfile = vi.fn().mockResolvedValue({ receipt_id: "r1000000-0000-0000-0000-000000000011", entity_id: npc.entry_id, version: 2, idempotent_replay: false });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([npc]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...npc, claims: [], claim_history: [], sources: [] }),
      getEntityProfile, updateEntityProfile,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Goodman" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(npc.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit NPC page" }));
    // Choose resurrected and give the since date; save carries the audited write.
    fireEvent.change(screen.getByLabelText("Identity life status"), { target: { value: "resurrected" } });
    fireEvent.change(screen.getByLabelText("Life status since"), { target: { value: "505-11-11" } });
    fireEvent.click(screen.getByRole("button", { name: "Save identity profile" }));
    await waitFor(() => expect(updateEntityProfile).toHaveBeenCalledWith(
      npc.entry_id, expect.objectContaining({ life_status: "resurrected",
        life_status_since: { calendar_id: "gregorian-ce", year: 505, month: 11, day: 11 } })));
    expect(await screen.findByText(/Saved with receipt r1000000/)).toBeInTheDocument();
  });

  it("renders the faction roster as structured template blocks", async () => {
    const faction = {
      entry_id: "b1000000-0000-0000-0000-000000000030", canonical_name: "Inquisitors",
      entity_kind: "faction" as const, aliases: [], misspellings: [], tags: [],
      members: [
        { member_id: "b1000000-0000-0000-0000-000000000031", name: "Eustice", role_title: "Inquisitor", is_leadership: false },
        { member_id: "b1000000-0000-0000-0000-000000000032", name: "Romulus", role_title: "Grand Inquisitor", is_leadership: true },
      ], related: [], current_claim_count: 2, source_count: 0,
    };
    const getEntityProfile = vi.fn().mockResolvedValue(null);
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([faction]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...faction, roles: [], claims: [], claim_history: [], sources: [] }),
      getEntityProfile,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Inquisitors" }));
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(faction.entry_id));
    const rosterSection = await screen.findByLabelText("Faction roster");
    expect(rosterSection).toHaveTextContent("Eustice");
    expect(rosterSection).toHaveTextContent("Romulus");
    expect(rosterSection).toHaveTextContent("Grand Inquisitor ★");
    expect(screen.getByText(/★ unique leadership seat/)).toBeInTheDocument();
    expect(screen.getByText(/Records — claims and sources/)).toBeInTheDocument();
  });

  it("sets life status on a sheet-backed npc through the character editor", async () => {
    const npc = {
      entry_id: "a1000000-0000-0000-0000-000000000020", canonical_name: "Romulus",
      entity_kind: "npc" as const, aliases: [], misspellings: [], tags: [],
      members: [], current_claim_count: 5, source_count: 1,
    };
    const sheet = "---\ntype: npc\nname: Romulus\nstatus: active\n---\n\n# Romulus\n\n## Background\n\nPatience and knives.";
    const entityProfile = { entity_id: npc.entry_id, version: 1, canonical_name: "Romulus",
      status: "active", base_location: null, aliases: [], summary: "",
      life_status: null, life_status_since: null, life_status_claim_id: null };
    const getEntityProfile = vi.fn().mockResolvedValue(entityProfile);
    const setLifeStatus = vi.fn().mockResolvedValue({ receipt_id: "r2000000-0000-0000-0000-000000000021", version: 2, idempotent_replay: false });
    render(<App campaignClient={makeClient({
      listLibraryEntries: vi.fn().mockResolvedValue([npc]),
      getLibraryEntry: vi.fn().mockResolvedValue({ ...npc, claims: [], claim_history: [],
        sources: [{ document_id: "d2000000-0000-0000-0000-000000000022", path: "npcs/romulus.md" }] }),
      getSourceDocument: vi.fn().mockResolvedValue({ document_id: "d2000000-0000-0000-0000-000000000022",
        source_revision_id: "s2000000-0000-0000-0000-000000000023", path: "npcs/romulus.md",
        content: sheet, canonical_claims: [], claim_history: [] }),
      getPCProfile: vi.fn().mockResolvedValue({ document_id: "d2000000-0000-0000-0000-000000000022",
        source_revision_id: "s2000000-0000-0000-0000-000000000023", version: 1, canonical_name: "Romulus",
        status: "active", aliases: [], background: "" }),
      getEntityProfile, setLifeStatus,
    })} jobPlatform={makeQuietJobs()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Romulus" }));
    // The sheet-backed hero shows Life status once the profile loads.
    await waitFor(() => expect(getEntityProfile).toHaveBeenCalledWith(npc.entry_id));
    fireEvent.click(screen.getByRole("button", { name: "Edit NPC page" }));
    fireEvent.change(screen.getByLabelText("NPC life status"), { target: { value: "undead" } });
    fireEvent.change(screen.getByLabelText("NPC life status since"), { target: { value: "505-11-11" } });
    await waitFor(() => expect(setLifeStatus).toHaveBeenCalledWith(
      npc.entry_id, "undead", { year: 505, month: 11, day: 11 }, null, expect.stringMatching(/^life-status:/)));
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

