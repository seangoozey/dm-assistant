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
  window.sessionStorage.clear();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

function makeQuietJobs(): JobPlatform { return {
  startHealthCheck: vi.fn(),
  cancel: vi.fn(),
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
      profiles: [
        {
          key: "deepseek-chat",
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
      ],
      active_profile_key: "deepseek-chat",
      prompt_version: "extraction/7",
      prompt_text: "Extract grounded claims.",
      last_activation: null,
    }),
    activateAIProfile: vi.fn().mockResolvedValue({
      receipt_id: "94000000-0000-0000-0000-000000000001",
      profile_key: "deepseek-chat",
      prompt_version: "extraction/7",
      activated_at: "2026-08-10T12:00:00Z",
    }),
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
    const contentPanel = screen.getByLabelText("Document content");
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
    expect(screen.getByText("gm/campaign-bible.md")).toBeInTheDocument();
    expect(screen.getByText("npcs/romulus.md")).toBeInTheDocument();
  });

  it("presents a multi-source location as one entry with grouped current information and hidden provenance", async () => {
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
    fireEvent.change(await screen.findByLabelText("Replacement 1 assertion"), { target: { value: "Coreferra restores magic." } });
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
    fireEvent.change(within(second!).getByLabelText("Replacement 2 assertion"), { target: { value: "The outcome occurred." } });
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
    expect(screen.getAllByText((_content, element) => Boolean(element?.textContent?.includes("17 files") && element?.classList?.contains("run-summary-compact"))).length).toBeGreaterThan(0);
    expect(screen.getAllByText((_content, element) => Boolean(element?.textContent?.includes("15 candidates") && element?.classList?.contains("run-summary-compact"))).length).toBeGreaterThan(0);

    expect(screen.getByLabelText("Editable extraction review")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Extraction 1 predicate"), { target: { value: "guards" } });
    fireEvent.change(screen.getByLabelText("Extraction 1 state"), { target: { value: "prepared" } });
    fireEvent.change(screen.getByLabelText("Extraction 1 authority"), { target: { value: "preparation" } });
    fireEvent.change(screen.getByLabelText("Extraction 1 visibility"), { target: { value: "party" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue with selected claims" }));
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
    expect(screen.getByText("Source-backed assertion is ready for exact approval.")).toBeInTheDocument();
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
    expect(await screen.findByLabelText("Canonical assertion")).toHaveValue("Coreferra became the Herald of Arkin.");
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
    await screen.findByLabelText("Canonical assertion");
    fireEvent.change(screen.getByLabelText("Skip reason"), { target: { value: "Table chatter" } });
    fireEvent.click(screen.getByRole("button", { name: "Skip with reason" }));
    expect(await screen.findByLabelText("Canonical assertion")).toHaveValue("The party entered the camp.");
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
    fireEvent.change(await screen.findByLabelText("Canonical assertion"), { target: { value: "Corrected session truth." } });
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
    expect(await screen.findByLabelText("Canonical assertion")).toHaveValue("The tattoo should remain longer-term foreshadowing.");
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
    fireEvent.change(screen.getByLabelText("Corrected assertion"), { target: { value: "Ruhrogue may help unite Myrin against Starfall." } });
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
    expect(screen.getByRole("status")).toHaveTextContent("1 candidate extracted.");
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
    expect(screen.getByRole("status")).toHaveTextContent("1 candidate extracted.");
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
      startCandidateExtraction: vi.fn(),
      inspect: vi.fn(),
    };
    renderTools(makeClient(), jobs);
    fireEvent.click(screen.getByRole("button", { name: "Run check" }));
    expect(await screen.findByText(/No worker is available/)).toBeInTheDocument();
  });

  it("shows the controlled AI extraction profile and prompt", async () => {
    const campaignClient = makeClient();
    renderTools(campaignClient, makeQuietJobs());

    expect(await screen.findByText("AI model")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /deepseek\/deepseek-chat/ })).toBeInTheDocument();
    expect(screen.getByText("extraction/7")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activate profile" })).toBeDisabled();
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
});

