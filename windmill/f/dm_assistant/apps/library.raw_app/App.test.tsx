// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type {
  CampaignClient,
  CandidateProposalApproval,
  CandidateProposalVersion,
  ImportCandidate,
} from "./campaignClient";
import type { JobPlatform } from "./jobPlatform";
import { PENDING_JOB_KEY } from "./operationState";
import { REVIEW_STATE_KEY } from "./reviewState";

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

const quietJobs: JobPlatform = {
  startHealthCheck: vi.fn(),
  inspect: vi.fn(),
};

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
      after: { canonical_name: "Sanitized Keeper", entity_type: "location" },
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
        state: "established",
        authority: "explicit_lore",
        visibility: "dm_only",
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
    query: vi.fn(),
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
    createProposal: vi.fn().mockResolvedValue(proposal),
    getProposal: vi.fn().mockResolvedValue(proposal),
    approveProposal: vi.fn().mockResolvedValue(approval),
    dispositionCandidate: vi.fn().mockResolvedValue({
      disposition_id: "92000000-0000-0000-0000-000000000001",
      candidate_id: candidate.candidate_id,
      review_status: "rejected",
      reason: "Not campaign truth",
      created_at: "2026-08-01T12:01:00Z",
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

describe("DM Assistant shell", () => {
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
    render(<App campaignClient={campaignClient} jobPlatform={quietJobs} />);

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
    render(<App campaignClient={campaignClient} jobPlatform={quietJobs} />);

    expect(await screen.findByText("lore/sanitized-keeper.md")).toBeInTheDocument();
    expect(screen.getAllByText(candidate.assertion_text).length).toBeGreaterThan(0);
    expect(screen.getAllByText("A referenced record could not be resolved.")).toHaveLength(2);
    expect(screen.getByText("inbox/sanitized-unknown.md")).toBeInTheDocument();
    expect(screen.getByText("2 open · 1 quarantined")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Canonical name"), {
      target: { value: "Sanitized Keeper" },
    });
    fireEvent.change(screen.getByLabelText("Entity type"), {
      target: { value: "location" },
    });
    fireEvent.change(screen.getByLabelText("Claim predicate"), {
      target: { value: "archive_role" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create exact proposal" }));

    const proposalHeading = await screen.findByText("Version 1");
    const proposalPanel = proposalHeading.closest("article");
    expect(proposalPanel).not.toBeNull();
    const proposalComparison = within(proposalPanel as HTMLElement);
    expect(proposalComparison.getByText("Entity type")).toBeInTheDocument();
    expect(proposalComparison.getByText("location")).toBeInTheDocument();
    expect(proposalComparison.getByText("Predicate")).toBeInTheDocument();
    expect(proposalComparison.getByText("archive_role")).toBeInTheDocument();
    expect(proposalComparison.getByText("Authority")).toBeInTheDocument();
    expect(proposalComparison.getByText("explicit_lore")).toBeInTheDocument();
    expect(proposalComparison.getByText("Visibility")).toBeInTheDocument();
    expect(proposalComparison.getByText("dm_only")).toBeInTheDocument();
    expect(screen.getByText("Pending exact confirmation")).toBeInTheDocument();
    const approvalButton = screen.getByRole("button", { name: "Approve 2 exact items" });
    expect(approvalButton).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Exact approval confirmation"), {
      target: { value: "APPROVE" },
    });
    fireEvent.click(approvalButton);

    expect(await screen.findByText("Approved and ready to apply")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply approved change" }));
    expect(await screen.findByText("Applied with receipt")).toBeInTheDocument();
    expect(screen.getByText("93000000-0000-0000-0000-000000000001")).toBeInTheDocument();

    expect(campaignClient.createProposal).toHaveBeenCalledWith([
      expect.objectContaining({
        mutation_kind: "create_entity",
        candidate_id: candidate.candidate_id,
        evidence_revision_id: candidate.evidence[0].source_revision_id,
        canonical_name: "Sanitized Keeper",
        entity_type: "location",
      }),
      expect.objectContaining({
        mutation_kind: "create_claim",
        candidate_id: candidate.candidate_id,
        predicate: "archive_role",
        state: "established",
        authority: "explicit_lore",
      }),
    ]);
    expect(JSON.parse(window.sessionStorage.getItem(REVIEW_STATE_KEY) ?? "{}")).toMatchObject({
      phase: "applied",
      receipt: { receipt_id: "93000000-0000-0000-0000-000000000001" },
    });
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
    const staleView = render(<App campaignClient={staleClient} jobPlatform={quietJobs} />);
    expect(await screen.findByText("Stale proposal version")).toBeInTheDocument();
    expect(screen.getByText(/changed after the displayed version/)).toBeInTheDocument();
    staleView.unmount();
    window.sessionStorage.clear();

    const rejectClient = makeClient();
    const rejectView = render(<App campaignClient={rejectClient} jobPlatform={quietJobs} />);
    await screen.findByText("lore/sanitized-keeper.md");
    fireEvent.change(screen.getByLabelText("Disposition reason"), {
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
    render(<App campaignClient={failingClient} jobPlatform={quietJobs} />);
    const apply = await screen.findByRole("button", { name: "Apply approved change" });
    fireEvent.click(apply);
    expect(await screen.findByText("Operation failed")).toBeInTheDocument();
    expect(screen.getByText("Atomic application was rejected")).toBeInTheDocument();
  });

  it("applies queue filters through CampaignClient", async () => {
    const campaignClient = makeClient();
    render(<App campaignClient={campaignClient} jobPlatform={quietJobs} />);
    await screen.findByText("lore/sanitized-keeper.md");
    fireEvent.change(screen.getByLabelText("Review status"), { target: { value: "rejected" } });
    fireEvent.change(screen.getByLabelText("Authority filter"), {
      target: { value: "explicit_lore" },
    });
    fireEvent.change(screen.getByLabelText("Source filter"), {
      target: { value: "keeper" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() =>
      expect(campaignClient.listCandidates).toHaveBeenLastCalledWith(
        expect.objectContaining({
          review_status: "rejected",
          authority: "explicit_lore",
          source: "keeper",
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
    render(<App campaignClient={campaignClient} jobPlatform={quietJobs} />);
    await screen.findByText("lore/sanitized-keeper.md");
    fireEvent.change(screen.getByLabelText("Disposition reason"), {
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
    window.sessionStorage.setItem(
      PENDING_JOB_KEY,
      JSON.stringify({
        jobId: "persisted-job-1234",
        state: "running",
        progress: 55,
        updatedAt: "2026-08-01T12:00:00Z",
      }),
    );
    const jobs: JobPlatform = {
      startHealthCheck: vi.fn(),
      inspect: vi.fn().mockResolvedValue({
        jobId: "persisted-job-1234",
        state: "succeeded",
        progress: 100,
        result: { status: "ok" },
        updatedAt: "2026-08-01T12:01:00Z",
      }),
    };
    render(<App campaignClient={makeClient()} jobPlatform={jobs} pollIntervalMs={1} />);

    expect(screen.getByText("Campaign Core check in progress")).toBeInTheDocument();
    await waitFor(() => expect(jobs.inspect).toHaveBeenCalledWith("persisted-job-1234"));
    expect(await screen.findByText("Campaign Core is available")).toBeInTheDocument();
  });

  it("makes a background job start failure visible", async () => {
    const jobs: JobPlatform = {
      startHealthCheck: vi.fn().mockRejectedValue(new Error("No worker is available")),
      inspect: vi.fn(),
    };
    render(<App campaignClient={makeClient()} jobPlatform={jobs} />);
    fireEvent.click(screen.getByRole("button", { name: "Run check" }));
    expect(await screen.findByText(/No worker is available/)).toBeInTheDocument();
  });
});
