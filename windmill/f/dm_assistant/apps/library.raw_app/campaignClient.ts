export type AnswerMode =
  | "answer"
  | "insufficient_evidence"
  | "conflict"
  | "possible_retcon"
  | "restricted";

export type EvidenceRole = "support" | "context" | "conflict";

export interface RetrievalQuery {
  question: string;
  requester_visibility: {
    role: "dm" | "party" | "character";
    character_id?: string;
  };
}

export interface RetrievedEvidence {
  record_id: string;
  assertion: string;
  citation: string;
  state: string;
  authority: string;
  role: EvidenceRole;
}

export interface RetrievalResult {
  answer_mode: AnswerMode;
  evidence: RetrievedEvidence[];
  citations: string[];
  reasons: string[];
}

export interface ImportRunSummary {
  import_run_id: string;
  root_identifier: string;
  snapshot_at: string;
  status: string;
  admitted_file_count: number;
  candidate_count: number;
  review_count: number;
  outcome_counts: Record<string, number>;
  warning_counts: Record<string, number>;
}

export interface ImportRunPage {
  items: ImportRunSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CandidateEvidence {
  source_revision_id: string;
  source_path: string;
  content_hash: string;
  classification: string;
  section: string;
  start_offset: number;
  end_offset: number;
  excerpt: string;
}

export interface ImportCandidate {
  candidate_id: string;
  source_document_id: string;
  first_seen_import_run_id: string;
  assertion_text: string;
  state: string;
  authority: string;
  visibility: string;
  conditional: boolean;
  predicts_subject_action: boolean;
  evidence_only: boolean;
  status: string;
  review_status: string;
  extractor_version: string;
  created_at: string;
  updated_at: string;
  evidence: CandidateEvidence[];
}

export interface ImportCandidatePage {
  items: ImportCandidate[];
  total: number;
  limit: number;
  offset: number;
}

export interface ImportReviewItem {
  review_id: string;
  kind: string;
  status: string;
  subject_type: string;
  subject_id: string;
  details: Record<string, unknown>;
  opened_by_import_run_id: string;
  source_path?: string;
  classification?: string;
}

export interface ImportReviewPage {
  items: ImportReviewItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface CandidateFilters {
  run_id?: string;
  review_status?: string;
  authority?: string;
  state?: string;
  classification?: string;
  source?: string;
  limit?: number;
  offset?: number;
}

export interface CreateEntityProposalItem {
  mutation_kind: "create_entity";
  candidate_id: string;
  evidence_revision_id: string;
  target_id: string;
  entity_type: string;
  canonical_name: string;
}

export interface CreateClaimProposalItem {
  mutation_kind: "create_claim";
  candidate_id: string;
  evidence_revision_id: string;
  target_id: string;
  subject_entity_id: string;
  predicate: string;
  state: string;
  authority: string;
  visibility: string;
  confidence: string;
  is_conditional: boolean;
  predicts_subject_action: boolean;
  recorded_at: string;
  observed_at?: string;
}

export type CreateProposalItem = CreateEntityProposalItem | CreateClaimProposalItem;

export interface ProposalItem {
  item_id: string;
  sequence: number;
  mutation_kind: "create_entity" | "create_claim";
  target_type: "entity" | "claim";
  target_id: string;
  after: Record<string, unknown>;
  evidence: {
    candidate_id: string;
    source_revision_id: string;
    source_span_id: string;
    candidate_fingerprint: string;
  };
}

export interface CandidateProposalVersion {
  proposal_id: string;
  workflow_session_id: string;
  status: string;
  version_id: string;
  version_number: number;
  content_hash: string;
  supersedes_version_id?: string;
  created_at: string;
  items: ProposalItem[];
}

export interface CandidateProposalApproval {
  proposal_id: string;
  proposal_version_id: string;
  reviewed_version: number;
  content_hash: string;
  approval_id: string;
  change_set_id: string;
  item_ids: string[];
  idempotency_key: string;
  approved_at: string;
  idempotent_replay: boolean;
}

export interface ChangeSetReceipt {
  receipt_id: string;
  change_set_id: string;
  outcome: string;
  applied_item_ids: string[];
  issued_at: string;
  idempotent_replay: boolean;
}

export interface CandidateDispositionResult {
  disposition_id: string;
  candidate_id: string;
  review_status: "deferred" | "rejected";
  reason: string;
  created_at: string;
}

export interface CampaignClient {
  query(request: RetrievalQuery, signal?: AbortSignal): Promise<RetrievalResult>;
  listImportRuns(): Promise<ImportRunPage>;
  listCandidates(filters: CandidateFilters): Promise<ImportCandidatePage>;
  getCandidate(candidateId: string): Promise<ImportCandidate>;
  listReviews(runId?: string): Promise<ImportReviewPage>;
  createProposal(items: CreateProposalItem[]): Promise<CandidateProposalVersion>;
  getProposal(proposalId: string): Promise<CandidateProposalVersion>;
  approveProposal(
    proposal: CandidateProposalVersion,
    itemIds: string[],
    idempotencyKey: string,
  ): Promise<CandidateProposalApproval>;
  dispositionCandidate(
    candidateId: string,
    disposition: "deferred" | "rejected",
    reason: string,
  ): Promise<CandidateDispositionResult>;
  applyApproval(
    proposal: CandidateProposalVersion,
    approval: CandidateProposalApproval,
  ): Promise<ChangeSetReceipt>;
}

export interface ReviewBackendRequest {
  operation:
    | "list_runs"
    | "list_candidates"
    | "get_candidate"
    | "list_reviews"
    | "create_proposal"
    | "get_proposal"
    | "approve_proposal"
    | "disposition_candidate"
    | "apply_approval";
  candidate_id?: string;
  proposal_id?: string;
  change_set_id?: string;
  query?: Record<string, string | number | undefined>;
  body?: unknown;
}

export interface CampaignBackend {
  query_campaign(input: { query: RetrievalQuery }): Promise<RetrievalResult>;
  review_campaign(input: { input: ReviewBackendRequest }): Promise<unknown>;
}

export class CampaignClientError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "CampaignClientError";
  }
}

function queryString(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export class HttpCampaignClient implements CampaignClient {
  private readonly request: typeof fetch;

  constructor(
    private readonly baseUrl = "/campaign-core",
    request: typeof fetch = globalThis.fetch,
  ) {
    this.request = request.bind(globalThis);
  }

  private async core<T>(
    path: string,
    method: "GET" | "POST" = "GET",
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    let response: Response;
    try {
      response = await this.request(`${this.baseUrl.replace(/\/$/, "")}${path}`, {
        method,
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (error) {
      throw new CampaignClientError(
        error instanceof Error ? error.message : "Campaign Core could not be reached",
      );
    }
    if (!response.ok) {
      let detail = `Campaign Core returned ${response.status}`;
      try {
        const payload = (await response.json()) as { detail?: string };
        if (payload.detail) detail = payload.detail;
      } catch {
        // Keep the status-only error when the response has no structured body.
      }
      throw new CampaignClientError(detail, response.status);
    }
    return (await response.json()) as T;
  }

  query(query: RetrievalQuery, signal?: AbortSignal): Promise<RetrievalResult> {
    return this.core("/retrieval/query", "POST", query, signal);
  }

  listImportRuns(): Promise<ImportRunPage> {
    return this.core("/imports/runs?requester_role=dm&limit=20");
  }

  listCandidates(filters: CandidateFilters): Promise<ImportCandidatePage> {
    return this.core(
      `/imports/candidates${queryString({ requester_role: "dm", limit: 50, ...filters })}`,
    );
  }

  getCandidate(candidateId: string): Promise<ImportCandidate> {
    return this.core(`/imports/candidates/${candidateId}?requester_role=dm`);
  }

  async listReviews(runId?: string): Promise<ImportReviewPage> {
    const items: ImportReviewItem[] = [];
    let total = 0;
    do {
      const page = await this.core<ImportReviewPage>(
        `/imports/reviews${queryString({
          requester_role: "dm",
          run_id: runId,
          limit: 100,
          offset: items.length,
        })}`,
      );
      total = page.total;
      items.push(...page.items);
      if (page.items.length === 0) break;
    } while (items.length < total);
    return { items, total, limit: items.length, offset: 0 };
  }

  createProposal(items: CreateProposalItem[]): Promise<CandidateProposalVersion> {
    return this.core("/imports/proposals?requester_role=dm", "POST", { items });
  }

  getProposal(proposalId: string): Promise<CandidateProposalVersion> {
    return this.core(`/imports/proposals/${proposalId}?requester_role=dm`);
  }

  approveProposal(
    proposal: CandidateProposalVersion,
    itemIds: string[],
    idempotencyKey: string,
  ): Promise<CandidateProposalApproval> {
    return this.core(
      `/imports/proposals/${proposal.proposal_id}/approvals?requester_role=dm`,
      "POST",
      {
        reviewed_version: proposal.version_number,
        content_hash: proposal.content_hash,
        item_ids: itemIds,
        idempotency_key: idempotencyKey,
      },
    );
  }

  dispositionCandidate(
    candidateId: string,
    disposition: "deferred" | "rejected",
    reason: string,
  ): Promise<CandidateDispositionResult> {
    return this.core(
      `/imports/candidates/${candidateId}/disposition?requester_role=dm`,
      "POST",
      { disposition, reason },
    );
  }

  applyApproval(
    proposal: CandidateProposalVersion,
    approval: CandidateProposalApproval,
  ): Promise<ChangeSetReceipt> {
    return this.core(`/change-sets/${approval.change_set_id}/apply`, "POST", {
      reviewed_version: proposal.version_number,
      approval_id: approval.approval_id,
      content_hash: proposal.content_hash,
    });
  }
}

export class WindmillCampaignClient implements CampaignClient {
  constructor(private readonly backend: CampaignBackend) {}

  async query(query: RetrievalQuery, signal?: AbortSignal): Promise<RetrievalResult> {
    if (signal?.aborted) throw new DOMException("The request was aborted", "AbortError");
    return this.backend.query_campaign({ query });
  }

  private async review<T>(input: ReviewBackendRequest): Promise<T> {
    return (await this.backend.review_campaign({ input })) as T;
  }

  listImportRuns(): Promise<ImportRunPage> {
    return this.review({ operation: "list_runs" });
  }

  listCandidates(filters: CandidateFilters): Promise<ImportCandidatePage> {
    return this.review({ operation: "list_candidates", query: { limit: 50, ...filters } });
  }

  getCandidate(candidateId: string): Promise<ImportCandidate> {
    return this.review({ operation: "get_candidate", candidate_id: candidateId });
  }

  async listReviews(runId?: string): Promise<ImportReviewPage> {
    const items: ImportReviewItem[] = [];
    let total = 0;
    do {
      const page = await this.review<ImportReviewPage>({
        operation: "list_reviews",
        query: { run_id: runId, limit: 100, offset: items.length },
      });
      total = page.total;
      items.push(...page.items);
      if (page.items.length === 0) break;
    } while (items.length < total);
    return { items, total, limit: items.length, offset: 0 };
  }

  createProposal(items: CreateProposalItem[]): Promise<CandidateProposalVersion> {
    return this.review({ operation: "create_proposal", body: { items } });
  }

  getProposal(proposalId: string): Promise<CandidateProposalVersion> {
    return this.review({ operation: "get_proposal", proposal_id: proposalId });
  }

  approveProposal(
    proposal: CandidateProposalVersion,
    itemIds: string[],
    idempotencyKey: string,
  ): Promise<CandidateProposalApproval> {
    return this.review({
      operation: "approve_proposal",
      proposal_id: proposal.proposal_id,
      body: {
        reviewed_version: proposal.version_number,
        content_hash: proposal.content_hash,
        item_ids: itemIds,
        idempotency_key: idempotencyKey,
      },
    });
  }

  dispositionCandidate(
    candidateId: string,
    disposition: "deferred" | "rejected",
    reason: string,
  ): Promise<CandidateDispositionResult> {
    return this.review({
      operation: "disposition_candidate",
      candidate_id: candidateId,
      body: { disposition, reason },
    });
  }

  applyApproval(
    proposal: CandidateProposalVersion,
    approval: CandidateProposalApproval,
  ): Promise<ChangeSetReceipt> {
    return this.review({
      operation: "apply_approval",
      change_set_id: approval.change_set_id,
      body: {
        reviewed_version: proposal.version_number,
        approval_id: approval.approval_id,
        content_hash: proposal.content_hash,
      },
    });
  }
}
