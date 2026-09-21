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
  entity_kinds?: EntityKind[];
  tags?: string[];
}

export type EntityKind =
  | "npc"
  | "pc"
  | "location"
  | "faction"
  | "item"
  | "event"
  | "worldbuilding"
  | "rules_element";

export interface EntityKindGuidance {
  kind: EntityKind;
  label: string;
  description: string;
}

export interface TaxonomySnapshot {
  entity_kinds: EntityKindGuidance[];
  plan_kinds?: PlanKindGuidance[];
  tags: string[];
}

export interface EntityIdentity {
  entity_id: string;
  canonical_name: string;
  entity_kind: EntityKind;
  match_kind?: "canonical" | "alias" | "partial";
  matched_name?: string;
}

export interface LibraryEntrySource { document_id: string; path: string; }
export interface LibraryMember {
  member_id: string; name: string; role_title: string | null; is_leadership: boolean;
}
export interface FactionRole {
  name: string; is_leadership: boolean; holder_names: string[];
}
export interface FactionRoleSummary {
  faction_id: string; faction_name: string; name: string; is_leadership: boolean;
  holders: { id: string; name: string }[];
}
export interface RoleDeclarationSummary {
  surface: string; normalized_surface: string;
}
export interface IdentityDecisionEntry {
  decision_id: string; kind: string; surface: string; decided_at: string; details?: Record<string, unknown> | null;
}
export interface LibraryEntrySummary {
  entry_id: string; canonical_name: string; entity_kind: EntityKind; aliases: string[]; misspellings?: string[]; tags: string[]; members?: LibraryMember[]; related?: string[];
  current_claim_count: number; source_count: number;
}
export interface LibraryEntryClaim extends Omit<SourceDocumentClaim, "source_excerpt"> { sources: LibraryEntrySource[]; }
export interface LibraryEntry extends LibraryEntrySummary { claims: LibraryEntryClaim[]; claim_history: SourceDocumentClaimHistory[]; sources: LibraryEntrySource[]; roles?: FactionRole[]; }

export type PlanKind = "campaign_direction" | "in_world_plan" | "player_plan";
export type PlanLifecycle = "active" | "completed" | "failed" | "abandoned" | "superseded";

export interface PlanKindGuidance { kind: PlanKind; label: string; description: string; }
export interface PlanRecord {
  id: string; record_type: "plan"; plan_kind: PlanKind; plan_kind_version: number;
  canonical_name: string; summary: string; objective?: string; mechanism?: string;
  intended_outcome?: string; lifecycle: PlanLifecycle; knowledge_boundary: string;
  visibility: string; owner_record_id?: string; owner_kind?: string; owner_name?: string;
  player_attribution?: string; communicated_at?: string;
  evidence_source_span_ids: string[]; related_plan_ids: string[]; supporting_claim_ids: string[];
}

export interface CreatePlanInput {
  target_id: string; plan_kind: PlanKind; canonical_name: string; summary: string;
  objective?: string; mechanism?: string; intended_outcome?: string; visibility?: string;
  owner_record_id?: string; player_attribution?: string; communicated_at?: string;
  evidence_source_span_ids: string[]; related_plan_ids: string[];
}

export interface PlanProposalVersion {
  proposal_id: string; workflow_session_id: string; status: string; version_id: string;
  version_number: number; content_hash: string; created_at: string;
  item: { item_id: string; mutation_kind: "create_plan" | "transition_plan";
    target_id: string; before?: Record<string, unknown>; after: Record<string, unknown> };
}

export interface RetrievedEvidence {
  graph_trace?: string[];
  graph_sources?: { record_id: string; assertion: string; citation: string; state: string }[];
  record_id: string;
  assertion: string;
  citation: string;
  state: string;
  authority: string;
  role: EvidenceRole;
  entity_id?: string;
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
  in_game_date?: CampaignDate;
  mentions?: DirectInputMention[];
}

export interface CandidateExtraction {
  extraction_id: string;
  subject: string;
  subject_resolution?: "focal_entity" | "named_identity" | "non_entity" | "unresolved";
  predicate: string | null;
  object_entity: string | null;
  assertion_text: string;
  supporting_excerpt: string;
  state: string;
  authority: string;
  visibility: string;
  confidence: string;
  extractor_version: string;
  source_segment_ids?: string[];
}

export interface CandidateExtractionSegment {
  segment_id: string;
  text: string;
  start_offset: number;
  end_offset: number;
  disposition: "extracted" | "context_only" | "duplicate" | "non_assertive" | "unaccounted";
  claim_indexes: number[];
}

export interface CandidateExtractionResult {
  candidate_id: string;
  extracted: CandidateExtraction[];
  extractor_version: string;
  error: string | null;
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
  condition_text?: string;
  condition_reference_type?: "claim" | "event" | "plan" | "entity";
  condition_reference_id?: string;
  evidence_only: boolean;
  status: string;
  review_status: string;
  extractor_version: string;
  created_at: string;
  updated_at: string;
  evidence: CandidateEvidence[];
  extractions?: CandidateExtraction[];
  extraction_segments?: CandidateExtractionSegment[];
}

export interface ImportCandidatePage {
  items: ImportCandidate[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceDocument {
  document_id: string;
  path: string;
  classification: string;
  candidate_count: number;
  extraction_count: number;
  open_review_count: number;
  missing_source: boolean;
  document_type?: string;
  title?: string;
  session_date?: string;
  capture_mode?: string;
}

export interface SourceDocumentPage {
  items: SourceDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceDocumentContent {
  document_id: string;
  path: string;
  source_revision_id: string;
  content: string;
  document_type?: string;
  title?: string;
  session_date?: string;
  in_game_date?: CampaignDate;
  capture_mode?: string;
  capture_id?: string;
  mentions?: DirectInputMention[];
  referenced_claims?: string[];
  canonical_claims?: SourceDocumentClaim[];
  claim_history?: SourceDocumentClaimHistory[];
}

export type ClaimProjection = "real_play" | "player_plan" | "npc_plan" | "dm_plan" | "lore_fact";
export interface SourceDocumentClaim { claim_id: string; assertion_text: string; state: string; authority: string; visibility: string; conditional: boolean; condition_text?: string; recorded_at: string; projection: ClaimProjection; source_excerpt?: string; sources?: LibraryEntrySource[]; }
export interface SourceDocumentClaimHistory extends SourceDocumentClaim { superseded_by_claim_id: string; supersession_reason: string; }

export interface PCProfile { document_id: string; source_revision_id: string; version: number; canonical_name: string; player?: string; race?: string; sex?: string; status: string; aliases: string[]; background: string; }
export interface ProfileAliasSync { entity_id: string; entity_name: string; applied: string[]; removed: string[]; skipped_conflicting: string[]; }
export interface PCProfileReceipt { receipt_id: string; document_id: string; version: number; idempotent_replay: boolean; alias_sync?: ProfileAliasSync; }
export interface IdentityGapEvidence { claim_id: string; excerpt: string; }
export interface IdentityGapAliasCandidate { entity_id: string; canonical_name: string; entity_kind?: string | null; }
export interface IdentityGap { surface: string; normalized_surface: string; claims_with_phrase: number; total_mentions: number; retrieval_demand: number; role_hint: boolean; suggested_canonical_name?: string | null; suggested_kind?: string | null; related_surfaces: string[]; evidence: IdentityGapEvidence[]; alias_candidates: IdentityGapAliasCandidate[]; }
export interface IdentityGapQueue { gaps: IdentityGap[]; total_candidates: number; }
export interface IdentityDecisionReceipt { decision_id: string; kind: string; surface: string; entity_id?: string; linked_claims?: number; idempotent_replay: boolean; }
export interface EntityProfile { entity_id: string; version: number; canonical_name: string; status?: string | null; location_type?: string | null; parent_location?: string | null; base_location?: string | null; player?: string | null; race?: string | null; sex?: string | null; aliases: string[]; summary: string; life_status?: "alive" | "dead" | "undead" | "resurrected" | "immortal" | "unknown" | null; life_status_since?: { calendar_id: string; year: number; month: number; day: number } | null; life_status_claim_id?: string | null; }
export interface EntityProfileAliasSync { entity_name: string; applied: string[]; removed: string[]; skipped_conflicting: string[]; }
export interface EntityProfileReceipt { receipt_id: string; entity_id: string; version: number; idempotent_replay: boolean; alias_sync?: EntityProfileAliasSync | null; }
export interface EntityKindProposalVersion { proposal_id: string; workflow_session_id: string; status: string; version_id: string; version_number: number; content_hash: string; created_at: string; item: { item_id: string; target_id: string; before: Record<string, unknown>; after: Record<string, unknown> }; }
export interface CampaignDate { calendar_id: string; year: number; month: number; day: number; }
export interface SessionDatingEntry {
  document_id: string; path: string; title: string; session_date?: string | null;
  year?: number | null; month?: number | null; day?: number | null;
  undated_claims: number; dated_by?: "dm" | "capture" | null;
}
export interface UndatedClaimEntry {
  claim_id: string; assertion: string; entities: string[]; conflict_relevant: boolean;
}
export interface SessionDateResult { claims_stamped: number; claims_evidenced: number; }
export interface InheritResult { overlay_dated_documents: number; frontmatter_dated_documents: number; claims_stamped: number; }
export interface ConflictPair {
  entity_name: string;
  claim_a_id: string; claim_a_assertion: string; claim_a_date: string;
  claim_b_id: string; claim_b_assertion: string; claim_b_date: string;
  claim_b_authority: string; claim_b_state: string;
}
export interface ConflictDecisionResult {
  decision_id: string; change_set_id?: string | null; idempotent_replay: boolean;
}
export interface EntityDescriptionReceipt {
  entity_id: string; document_id: string; revision_id: string; path: string; idempotent_replay: boolean;
}
export interface ProseMaterialItem { key: string; kind: string; text: string; state?: string | null; }
export interface ProseDraftCommand { subject: string; subject_kind: string; paragraph_limit: number; direction?: string | null; material: ProseMaterialItem[]; idempotency_key: string; }
export interface ProseDraftResult { draft_text: string; cited_keys: string[]; model_slug: string; prompt_version: string; prompt_tokens: number; completion_tokens: number; }
export interface GraphRelationRow { key: string; text: string; backing: string; }
export interface EffectivePrompt { purpose: string; prompt_text: string; version_label: string; overridden: boolean; updated_at: string | null; }
export interface PromptOverrideReceipt { receipt_id: string; purpose: string; action: string; version_label: string; changed_at: string; }
export interface DossierView { entity_id: string; promoted_claim_ids: string[]; }
export interface VocabularyValue { vocabulary: string; value: string; retired: boolean; }
export interface VocabularyChangeReceipt { receipt_id: string; vocabulary: string; action: string; value: string; changed_at: string; }
export interface ReattributionReceipt { receipt_id: string; claim_id: string; old_entity_id: string; new_entity_id: string; moved_at: string; }
export interface MovedAssertion { claim_id: string; assertion_text: string; state: string; new_entity_id: string; new_entity_name: string; moved_at: string; reason: string; }
export interface LinkFinding { kind: string; entity_id: string | null; entity_name: string; entity_kind: string; document_id: string | null; document_path: string | null; detail: string; }
export interface LinkAuditResult { audited_at: string; findings: LinkFinding[]; }
export interface DossierDecisionReceipt { receipt_id: string; entity_id: string; claim_id: string; action: string; decided_at: string; }
export interface LifeStatusProposal {
  entity_id: string; entity_name: string; death_claim_id: string;
  death_assertion: string; death_date: string; current_status?: string | null;
}
export interface DeadSeat {
  member_name: string; faction_name: string; role_title?: string | null;
  is_leadership: boolean; life_status_since: string;
  member_id: string; faction_id: string;
}
export interface LifeStatusReceipt {
  receipt_id: string; version: number; idempotent_replay: boolean;
}
export interface CampaignClockChange {
  calendar_id: string; year: number; month: number; day: number;
  reason?: string | null; changed_by: string; changed_at: string;
}
export interface DirectInputMention { entity_id: string; display_name: string; start_offset: number; end_offset: number; }
export interface SessionNoteCaptureInput { session_date: string; in_game_date: CampaignDate; title: string; text: string; visibility: "dm_only" | "party" | "character"; mentions: DirectInputMention[]; idempotency_key: string; capture_id?: string; }
export interface SessionNoteCaptureReceipt { capture_id: string; source_document_id: string; source_revision_id: string; candidate_id: string; candidate_ids: string[]; idempotent_replay: boolean; }
export interface BrainstormPin { entity_id: string; canonical_name: string; entity_kind: EntityKind; position: number; pinned_at: string; }
export interface BrainstormEvidencePin { record_id: string; assertion: string; citation: string; entity_id?: string; position: number; pinned_at: string; }
export interface BrainstormThought { thought_id: string; sequence: number; text: string; source_document_id: string; source_revision_id: string; candidate_id: string; captured_at: string; evidence: RetrievalResult; mentions: DirectInputMention[]; }
export interface BrainstormSession { session_id: string; title: string; status: "open" | "closed"; started_at: string; closed_at?: string; proposal_id?: string;
  version_number?: number;
  content_hash?: string; thoughts: BrainstormThought[]; pins: BrainstormPin[]; evidence_pins?: BrainstormEvidencePin[]; }
export interface SessionRunNote { note_id: string; run_id: string; source_document_id?: string; source_path: string; context_kind: "general" | "encounter"; encounter_name?: string; section_key?: string; section_title?: string; text: string; captured_at: string; updated_at: string; }
export interface SessionRunEncounter { source_document_id?: string; source_path: string; encounter_name: string; first_activity_at: string; last_activity_at: string; last_section_key?: string; last_section_title?: string; note_count: number; }
export type EncounterLifecycle = "not_started" | "in_progress" | "completed" | "abandoned";
export interface EncounterProgress { source_document_id: string; source_path: string; encounter_name: string; status: EncounterLifecycle; resume_section_key?: string; resume_section_title?: string; last_session_run_id?: string; updated_at: string; }
export interface UpdateEncounterProgressInput { source_document_id: string; source_path: string; encounter_name: string; status: EncounterLifecycle; resume_section_key?: string; resume_section_title?: string; session_run_id?: string; }
export interface SessionRun { run_id: string; status: "open" | "closed"; session_date: string; in_game_date?: CampaignDate; title: string; captured_source_document_id?: string; capture_id?: string; created_at: string; updated_at: string; closed_at?: string; notes: SessionRunNote[]; encounters: SessionRunEncounter[]; }
export interface OpenSessionRunInput { session_date: string; in_game_date?: CampaignDate; title: string; }
export interface SaveSessionRunNoteInput { note_id: string; source_document_id?: string; source_path: string; context_kind?: "general" | "encounter"; encounter_name?: string; section_key?: string; section_title?: string; text: string; captured_at: string; }

export interface ClaimEvidenceSnapshot { source_span_id: string; source_path: string; section_path: string; start_offset: number; end_offset: number; evidence_role: string; }
export interface ClaimDateParts { year: number; month?: number; day?: number; }
export interface ClaimSnapshot { claim_id: string; assertion_text: string; state: string; authority: string; visibility: string; recorded_at: string; condition_text?: string; effective_from?: ClaimDateParts; effective_until?: ClaimDateParts; expected?: ClaimDateParts; observed?: ClaimDateParts; source_paths: string[]; evidence: ClaimEvidenceSnapshot[]; snapshot_hash: string; is_current: boolean; }
export interface ClaimReplacementDraft { assertion_text: string; state: string; authority: string; visibility: string; condition_text?: string; effective_from?: ClaimDateParts; effective_until?: ClaimDateParts; expected?: ClaimDateParts; observed?: ClaimDateParts; }
export interface ClaimOverlap { superseding: ClaimSnapshot; superseded: ClaimSnapshot; similarity: number; }
export type ReconciliationDecision = "retain_both" | "duplicate" | "supersede";
export interface ClaimReconciliationReceipt { receipt_id: string; change_set_id: string; decision: ReconciliationDecision; idempotent_replay: boolean; }
export interface ClaimCorrectionReceipt { receipt_id: string; change_set_id: string; original_claim_id: string; replacement_claim_id: string; idempotent_replay: boolean; }
export interface ClaimReplacementReceipt { receipt_id: string; change_set_id: string; original_claim_id: string; replacement_claim_ids: string[]; idempotent_replay: boolean; }

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
  status?: string;
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
  entity_kind: EntityKind;
  canonical_name: string;
  tags: string[];
}

export interface CreateClaimProposalItem {
  mutation_kind: "create_claim";
  candidate_id: string;
  candidate_extraction_id?: string;
  evidence_revision_id: string;
  target_id: string;
  subject_entity_id?: string;
  related_entity_ids?: string[];
  assertion_text?: string;
  predicate?: string;
  state: string;
  authority: string;
  visibility: string;
  confidence: string;
  is_conditional: boolean;
  predicts_subject_action: boolean;
  recorded_at: string;
  observed_at?: { calendar_id: string; year?: number; month?: number; day?: number };
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
  getAIConfiguration(): Promise<AIConfigurationSnapshot>;
  activateAIProfile(profileKey: string, purpose: string): Promise<AIActivationReceipt>;
  getAIPrompts(): Promise<EffectivePrompt[]>;
  getEntityDossier(entityId: string): Promise<DossierView>;
  getTemplateVocabulary(vocabulary: string): Promise<VocabularyValue[]>;
  getLinkAudit(): Promise<LinkAuditResult>;
  reattributeClaim(claimId: string, newEntityId: string, reason: string): Promise<ReattributionReceipt>;
  getMovedAssertions(entityId: string): Promise<MovedAssertion[]>;
  changeTemplateVocabulary(vocabulary: string, action: "add" | "retire", value: string): Promise<VocabularyChangeReceipt>;
  promoteToDossier(entityId: string, claimId: string): Promise<DossierDecisionReceipt>;
  demoteFromDossier(entityId: string, claimId: string): Promise<DossierDecisionReceipt>;
  setAIPrompt(purpose: string, promptText: string): Promise<PromptOverrideReceipt>;
  resetAIPrompt(purpose: string): Promise<PromptOverrideReceipt>;
  getTaxonomy(): Promise<TaxonomySnapshot>;
  searchEntities(canonicalName: string): Promise<EntityIdentity[]>;
  listLibraryEntries(): Promise<LibraryEntrySummary[]>;
  getLibraryEntry(entryId: string): Promise<LibraryEntry>;
  listPlans(planKind?: PlanKind, lifecycle?: PlanLifecycle): Promise<PlanRecord[]>;
  createPlanProposal(input: CreatePlanInput): Promise<PlanProposalVersion>;
  transitionPlanProposal(planId: string, lifecycle: PlanLifecycle, supportingClaimIds: string[]): Promise<PlanProposalVersion>;
  getPlanProposal(proposalId: string): Promise<PlanProposalVersion>;
  approvePlanProposal(proposal: PlanProposalVersion, idempotencyKey: string): Promise<CandidateProposalApproval>;
  query(request: RetrievalQuery, signal?: AbortSignal): Promise<RetrievalResult>;
  listImportRuns(): Promise<ImportRunPage>;
  getOpenBrainstorm(): Promise<BrainstormSession | null>;
  startBrainstorm(title: string): Promise<BrainstormSession>;
  captureBrainstormThought(sessionId: string, text: string, mentions?: DirectInputMention[]): Promise<BrainstormSession>;
  pinBrainstormEntity(sessionId: string, entityId: string): Promise<BrainstormSession>;
  unpinBrainstormEntity(sessionId: string, entityId: string): Promise<BrainstormSession>;
  pinBrainstormEvidence(sessionId: string, recordId: string, searchQuery?: string): Promise<BrainstormSession>;
  unpinBrainstormEvidence(sessionId: string, recordId: string): Promise<BrainstormSession>;
  closeBrainstorm(sessionId: string, proposalId: string): Promise<BrainstormSession>;
  captureSessionNote(input: SessionNoteCaptureInput): Promise<SessionNoteCaptureReceipt>;
  getCurrentCampaignDate(): Promise<CampaignDate | null>;
  setCurrentCampaignDate(date: CampaignDate, reason?: string): Promise<CampaignDate>;
  getCampaignDateHistory(limit?: number): Promise<CampaignClockChange[]>;
  getSessionDatingWalk(): Promise<SessionDatingEntry[]>;
  setSessionDate(documentId: string, year: number, month: number, day: number, reason?: string): Promise<SessionDateResult>;
  inheritClaimDates(): Promise<InheritResult>;
  getUndatedClaims(limit?: number): Promise<UndatedClaimEntry[]>;
  getConflictQueue(): Promise<ConflictPair[]>;
  decideConflict(claimAId: string, claimBId: string, action: "dismiss" | "supersede", reason: string): Promise<ConflictDecisionResult>;
  writeEntityDescription(entityId: string, text: string, referencedClaimIds: string[], idempotencyKey: string, documentId?: string | null): Promise<EntityDescriptionReceipt>;
  draftProse(command: ProseDraftCommand): Promise<ProseDraftResult>;
  getEntityGraphNeighborhood(entityId: string): Promise<GraphRelationRow[]>;
  getLifeStatusProposals(): Promise<LifeStatusProposal[]>;
  setLifeStatus(entityId: string, status: string, since: { year: number; month: number; day: number }, claimId: string | null, idempotencyKey: string): Promise<LifeStatusReceipt>;
  getDeadSeats(): Promise<DeadSeat[]>;
  getOpenSessionRun(): Promise<SessionRun | null>;
  openSessionRun(input: OpenSessionRunInput): Promise<SessionRun>;
  saveSessionRunNote(runId: string, note: SaveSessionRunNoteInput): Promise<SessionRunNote>;
  deleteSessionRunNote(runId: string, noteId: string): Promise<void>;
  closeSessionRun(runId: string, sourceDocumentId: string, captureId: string): Promise<SessionRun>;
  listEncounterProgress(): Promise<EncounterProgress[]>;
  updateEncounterProgress(input: UpdateEncounterProgressInput): Promise<EncounterProgress>;
  listCandidates(filters: CandidateFilters): Promise<ImportCandidatePage>;
  getCandidate(candidateId: string): Promise<ImportCandidate>;
  listReviews(runId?: string): Promise<ImportReviewPage>;
  listSourceDocuments(): Promise<SourceDocumentPage>;
  getSourceDocument(documentId: string): Promise<SourceDocumentContent>;
  getPCProfile(documentId: string): Promise<PCProfile | null>;
  updatePCProfile(documentId: string, profile: Omit<PCProfile, "document_id"> & { idempotency_key: string }): Promise<PCProfileReceipt>;
  getIdentityGaps(limit?: number): Promise<IdentityGapQueue>;
  addIdentityAlias(surface: string, entityId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt>;
  createIdentityEntity(surface: string, entityKind: string, idempotencyKey: string, aliasSurfaces?: string[], manualAliases?: string[]): Promise<IdentityDecisionReceipt>;
  markIdentityRole(surface: string, idempotencyKey: string): Promise<IdentityDecisionReceipt>;
  dismissIdentityGap(surface: string, idempotencyKey: string): Promise<IdentityDecisionReceipt>;
  revertIdentityDecision(decisionId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt>;
  markIdentityMisspelling(surface: string, entityId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt>;
  getEntityProfile(entityId: string): Promise<EntityProfile | null>;
  updateEntityProfile(entityId: string, profile: Omit<EntityProfile, "entity_id"> & { idempotency_key: string }): Promise<EntityProfileReceipt>;
  proposeEntityKind(entityId: string, entityKind: string): Promise<EntityKindProposalVersion>;
  addMembership(factionId: string, memberId: string, roleTitle?: string): Promise<IdentityDecisionReceipt>;
  removeMembership(factionId: string, memberId: string): Promise<IdentityDecisionReceipt>;
  assignFactionRole(factionId: string, memberId: string, roleName: string | null, isLeadership: boolean): Promise<IdentityDecisionReceipt>;
  defineFactionRole(factionId: string, roleName: string, isLeadership: boolean): Promise<IdentityDecisionReceipt>;
  listFactionRoles(): Promise<FactionRoleSummary[]>;
  listRoleDeclarations(): Promise<RoleDeclarationSummary[]>;
  listRecentDecisions(limit?: number): Promise<IdentityDecisionEntry[]>;
  approveEntityMetadataProposal(proposalId: string, itemId: string, versionNumber: number, contentHash: string): Promise<CandidateProposalApproval>;
  discoverClaimOverlaps(): Promise<ClaimOverlap[]>;
  reconcileClaims(overlap: ClaimOverlap, decision: ReconciliationDecision, reason: string): Promise<ClaimReconciliationReceipt>;
  getClaimSnapshot(claimId: string): Promise<ClaimSnapshot>;
  correctClaim(claim: ClaimSnapshot, assertionText: string, reason: string): Promise<ClaimCorrectionReceipt>;
  replaceClaim(claim: ClaimSnapshot, replacements: ClaimReplacementDraft[], reason: string): Promise<ClaimReplacementReceipt>;
  createProposal(items: CreateProposalItem[], workflowSessionId?: string): Promise<CandidateProposalVersion>;
  reviseProposal(proposalId: string, items: CreateProposalItem[]): Promise<CandidateProposalVersion>;
  getProposal(proposalId: string): Promise<CandidateProposalVersion>;
  getCandidateProposal(candidateId: string): Promise<CandidateProposalVersion>;
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
  extractCandidate(candidateId: string): Promise<CandidateExtractionResult>;
  applyApproval(
    proposal: Pick<CandidateProposalVersion | PlanProposalVersion, "version_number" | "content_hash">,
    approval: CandidateProposalApproval,
  ): Promise<ChangeSetReceipt>;
}

export interface AIModelProfile { key: string; purpose: string; provider: string; model_slug: string; description: string; reasoning_effort: string | null; max_tokens: number; timeout_seconds: number; retry_limit: number; selectable: boolean; suitability: string; }
export interface AIPurposeInfo { key: string; label: string; description: string; prompt_version: string | null; prompt_text: string | null; }
export interface AIActivationReceipt { receipt_id: string; purpose: string; profile_key: string; prompt_version: string; activated_at: string; }
export interface AIConfigurationSnapshot { purposes: AIPurposeInfo[]; profiles: AIModelProfile[]; active_profile_by_purpose: Record<string, string>; last_activation_by_purpose: Record<string, AIActivationReceipt>; }

export interface ReviewBackendRequest {
  operation:
    | "get_taxonomy"
    | "search_entities"
    | "list_library_entries"
    | "get_library_entry"
    | "list_plans"
    | "create_plan_proposal"
    | "transition_plan_proposal"
    | "get_plan_proposal"
    | "approve_plan_proposal"
    | "list_runs"
    | "get_open_brainstorm"
    | "start_brainstorm"
    | "capture_brainstorm_thought"
    | "pin_brainstorm_entity"
    | "unpin_brainstorm_entity"
    | "pin_brainstorm_evidence"
    | "unpin_brainstorm_evidence"
    | "close_brainstorm"
    | "capture_session_note"
    | "get_current_campaign_date"
    | "set_current_campaign_date"
    | "get_campaign_date_history"
    | "get_session_dating_walk"
    | "set_session_document_date"
    | "inherit_claim_dates"
    | "get_undated_claims"
    | "get_conflict_queue"
    | "decide_conflict"
    | "write_entity_description"
    | "get_life_status_proposals"
    | "set_life_status"
    | "get_dead_seats"
    | "get_open_session_run"
    | "open_session_run"
    | "save_session_run_note"
    | "delete_session_run_note"
    | "close_session_run"
    | "list_encounter_progress"
    | "update_encounter_progress"
    | "list_candidates"
    | "get_candidate"
    | "list_reviews"
    | "list_source_documents"
    | "get_source_document"
    | "get_pc_profile"
    | "update_pc_profile"
    | "list_identity_gaps"
    | "add_identity_alias"
    | "create_identity_entity"
    | "mark_identity_role"
    | "dismiss_identity_gap"
    | "revert_identity_decision"
    | "mark_identity_misspelling"
    | "get_entity_profile"
    | "update_entity_profile"
    | "create_entity_metadata_proposal"
    | "membership_decision"
    | "role_decision"
    | "define_role_decision"
    | "list_faction_roles"
    | "list_role_declarations"
    | "list_recent_decisions"
    | "approve_entity_metadata_proposal"
    | "create_proposal"
    | "revise_proposal"
    | "get_proposal"
    | "get_candidate_proposal"
    | "approve_proposal"
    | "disposition_candidate"
    | "extract_candidate"
    | "apply_approval"
    | "get_ai_configuration"
    | "activate_ai_profile"
    | "draft_prose"
    | "get_entity_graph_neighborhood"
    | "get_ai_prompts"
    | "get_entity_dossier"
    | "get_template_vocabulary"
    | "get_link_audit"
    | "reattribute_claim"
    | "get_moved_assertions"
    | "change_template_vocabulary"
    | "promote_to_dossier"
    | "demote_from_dossier"
    | "set_ai_prompt"
    | "reset_ai_prompt"
    | "discover_claim_overlaps"
    | "reconcile_claims"
    | "get_claim_snapshot"
    | "correct_claim"
    | "replace_claim";
  candidate_id?: string;
  proposal_id?: string;
  plan_id?: string;
  document_id?: string;
  change_set_id?: string;
  claim_id?: string;
  entry_id?: string;
  path_id?: string;
  run_id?: string;
  session_id?: string;
  entity_id?: string;
  purpose?: string;
  vocabulary?: string;
  record_id?: string;
  note_id?: string;
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
    method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
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

  getTaxonomy(): Promise<TaxonomySnapshot> {
    return this.core("/taxonomy?requester_role=dm");
  }
  getAIConfiguration(): Promise<AIConfigurationSnapshot> { return this.core("/ai/configuration?requester_role=dm"); }
  activateAIProfile(profileKey: string, purpose: string): Promise<AIActivationReceipt> { return this.core("/ai/configuration/activate?requester_role=dm", "POST", { profile_key: profileKey, purpose }); }
  getAIPrompts(): Promise<EffectivePrompt[]> { return this.core("/ai/prompts?requester_role=dm"); }
  getEntityDossier(entityId: string): Promise<DossierView> { return this.core(`/entities/${entityId}/dossier?requester_role=dm`); }
  getTemplateVocabulary(vocabulary: string): Promise<VocabularyValue[]> { return this.core(`/template-vocabularies/${vocabulary}?requester_role=dm`); }
  getLinkAudit(): Promise<LinkAuditResult> { return this.core("/campaign/link-audit?requester_role=dm"); }
  reattributeClaim(claimId: string, newEntityId: string, reason: string): Promise<ReattributionReceipt> { return this.core(`/claims/${claimId}/reattribute?requester_role=dm`, "POST", { claim_id: claimId, new_entity_id: newEntityId, reason }); }
  getMovedAssertions(entityId: string): Promise<MovedAssertion[]> { return this.core(`/entities/${entityId}/moved-assertions?requester_role=dm`); }
  changeTemplateVocabulary(vocabulary: string, action: "add" | "retire", value: string): Promise<VocabularyChangeReceipt> { return this.core(`/template-vocabularies/${vocabulary}?requester_role=dm`, "POST", { action, value }); }
  promoteToDossier(entityId: string, claimId: string): Promise<DossierDecisionReceipt> { return this.core(`/entities/${entityId}/dossier/${claimId}/promote?requester_role=dm`, "POST"); }
  demoteFromDossier(entityId: string, claimId: string): Promise<DossierDecisionReceipt> { return this.core(`/entities/${entityId}/dossier/${claimId}/demote?requester_role=dm`, "POST"); }
  setAIPrompt(purpose: string, promptText: string): Promise<PromptOverrideReceipt> { return this.core(`/ai/prompts/${purpose}?requester_role=dm`, "PUT", { purpose, prompt_text: promptText }); }
  resetAIPrompt(purpose: string): Promise<PromptOverrideReceipt> { return this.core(`/ai/prompts/${purpose}?requester_role=dm`, "DELETE"); }

  searchEntities(canonicalName: string): Promise<EntityIdentity[]> {
    return this.core(`/entities${queryString({ canonical_name: canonicalName, requester_role: "dm" })}`, "GET");
  }
  listLibraryEntries(): Promise<LibraryEntrySummary[]> { return this.core("/library/entries?requester_role=dm"); }
  getLibraryEntry(entryId: string): Promise<LibraryEntry> { return this.core(`/library/entries/${entryId}?requester_role=dm`); }

  listPlans(planKind?: PlanKind, lifecycle?: PlanLifecycle): Promise<PlanRecord[]> {
    return this.core(`/plans${queryString({ requester_role: "dm", plan_kind: planKind, lifecycle })}`);
  }

  createPlanProposal(input: CreatePlanInput): Promise<PlanProposalVersion> {
    return this.core("/plans/proposals?requester_role=dm", "POST", input);
  }

  transitionPlanProposal(planId: string, lifecycle: PlanLifecycle, supportingClaimIds: string[]): Promise<PlanProposalVersion> {
    return this.core(`/plans/${planId}/lifecycle-proposals?requester_role=dm`, "POST", {
      plan_id: planId, lifecycle, supporting_claim_ids: supportingClaimIds,
    });
  }

  getPlanProposal(proposalId: string): Promise<PlanProposalVersion> {
    return this.core(`/plans/proposals/${proposalId}?requester_role=dm`);
  }

  approvePlanProposal(proposal: PlanProposalVersion, idempotencyKey: string): Promise<CandidateProposalApproval> {
    return this.core(`/plans/proposals/${proposal.proposal_id}/approvals?requester_role=dm`, "POST", {
      reviewed_version: proposal.version_number, content_hash: proposal.content_hash,
      item_ids: [proposal.item.item_id], idempotency_key: idempotencyKey,
    });
  }

  query(query: RetrievalQuery, signal?: AbortSignal): Promise<RetrievalResult> {
    return this.core("/retrieval/query", "POST", query, signal);
  }

  listImportRuns(): Promise<ImportRunPage> {
    return this.core("/imports/runs?requester_role=dm&limit=20");
  }
  getOpenBrainstorm(): Promise<BrainstormSession | null> { return this.core("/brainstorms/open?requester_role=dm"); }
  startBrainstorm(title: string): Promise<BrainstormSession> { return this.core("/brainstorms?requester_role=dm", "POST", { title, idempotency_key: `brainstorm-start-${crypto.randomUUID()}` }); }
  captureBrainstormThought(sessionId: string, text: string, mentions: DirectInputMention[] = []): Promise<BrainstormSession> { return this.core(`/brainstorms/${sessionId}/thoughts?requester_role=dm`, "POST", { text, mentions, idempotency_key: `brainstorm-thought-${crypto.randomUUID()}` }); }
  pinBrainstormEntity(sessionId: string, entityId: string): Promise<BrainstormSession> { return this.core(`/brainstorms/${sessionId}/pins/${entityId}?requester_role=dm`, "PUT"); }
  unpinBrainstormEntity(sessionId: string, entityId: string): Promise<BrainstormSession> { return this.core(`/brainstorms/${sessionId}/pins/${entityId}?requester_role=dm`, "DELETE"); }
  pinBrainstormEvidence(sessionId: string, recordId: string, searchQuery?: string): Promise<BrainstormSession> { return this.core(`/brainstorms/${sessionId}/evidence-pins/${encodeURIComponent(recordId)}${queryString({ requester_role: "dm", search_query: searchQuery })}`, "PUT"); }
  unpinBrainstormEvidence(sessionId: string, recordId: string): Promise<BrainstormSession> { return this.core(`/brainstorms/${sessionId}/evidence-pins/${encodeURIComponent(recordId)}?requester_role=dm`, "DELETE"); }
  closeBrainstorm(sessionId: string, proposalId: string): Promise<BrainstormSession> { return this.core(`/brainstorms/${sessionId}/close?requester_role=dm`, "POST", { proposal_id: proposalId }); }
  captureSessionNote(input: SessionNoteCaptureInput): Promise<SessionNoteCaptureReceipt> { return this.core("/capture/session-notes", "POST", input); }
  getCurrentCampaignDate(): Promise<CampaignDate | null> { return this.core("/campaign/current-date"); }
  setCurrentCampaignDate(date: CampaignDate, reason?: string): Promise<CampaignDate> { return this.core("/campaign/current-date?requester_role=dm", "PUT", { calendar_id: date.calendar_id, year: date.year, month: date.month, day: date.day, reason: reason ?? null }); }
  getCampaignDateHistory(limit?: number): Promise<CampaignClockChange[]> { return this.core(`/campaign/current-date/history?limit=${limit ?? 10}`); }
  getSessionDatingWalk(): Promise<SessionDatingEntry[]> { return this.core("/campaign/session-dating"); }
  setSessionDate(documentId: string, year: number, month: number, day: number, reason?: string): Promise<SessionDateResult> { return this.core(`/campaign/session-dating/${documentId}?requester_role=dm`, "PUT", { year, month, day, reason: reason ?? null }); }
  inheritClaimDates(): Promise<InheritResult> { return this.core("/campaign/claim-dates/inherit?requester_role=dm", "POST"); }
  getUndatedClaims(limit?: number): Promise<UndatedClaimEntry[]> { return this.core(`/campaign/undated-claims?limit=${limit ?? 50}`); }
  getConflictQueue(): Promise<ConflictPair[]> { return this.core("/campaign/conflicts"); }
  decideConflict(claimAId: string, claimBId: string, action: "dismiss" | "supersede", reason: string): Promise<ConflictDecisionResult> { return this.core("/campaign/conflicts/decisions?requester_role=dm", "POST", { claim_a_id: claimAId, claim_b_id: claimBId, action, reason }); }
  writeEntityDescription(entityId: string, text: string, referencedClaimIds: string[], idempotencyKey: string, documentId?: string | null): Promise<EntityDescriptionReceipt> { return this.core(`/entities/${entityId}/description?requester_role=dm`, "POST", { entity_id: entityId, text, referenced_claim_ids: referencedClaimIds, idempotency_key: idempotencyKey, ...(documentId ? { document_id: documentId } : {}) }); }
  draftProse(command: ProseDraftCommand): Promise<ProseDraftResult> { return this.core("/prose/draft?requester_role=dm", "POST", command); }
  getEntityGraphNeighborhood(entityId: string): Promise<GraphRelationRow[]> { return this.core(`/entities/${entityId}/graph-neighborhood?requester_role=dm`); }
  getLifeStatusProposals(): Promise<LifeStatusProposal[]> { return this.core("/campaign/life-status/proposals"); }
  setLifeStatus(entityId: string, status: string, since: { year: number; month: number; day: number }, claimId: string | null, idempotencyKey: string): Promise<LifeStatusReceipt> { return this.core(`/campaign/life-status/${entityId}?requester_role=dm`, "POST", { status, since_year: since.year, since_month: since.month, since_day: since.day, claim_id: claimId ?? null, idempotency_key: idempotencyKey }); }
  getDeadSeats(): Promise<DeadSeat[]> { return this.core("/campaign/dead-seats"); }
  getOpenSessionRun(): Promise<SessionRun | null> { return this.core("/campaign/session-runs/open?requester_role=dm"); }
  openSessionRun(input: OpenSessionRunInput): Promise<SessionRun> { return this.core("/campaign/session-runs/open?requester_role=dm", "POST", input); }
  saveSessionRunNote(runId: string, note: SaveSessionRunNoteInput): Promise<SessionRunNote> { return this.core(`/campaign/session-runs/${runId}/notes/${note.note_id}?requester_role=dm`, "PUT", note); }
  async deleteSessionRunNote(runId: string, noteId: string): Promise<void> { await this.core(`/campaign/session-runs/${runId}/notes/${noteId}?requester_role=dm`, "DELETE"); }
  closeSessionRun(runId: string, sourceDocumentId: string, captureId: string): Promise<SessionRun> { return this.core(`/campaign/session-runs/${runId}/close?requester_role=dm`, "POST", { captured_source_document_id: sourceDocumentId, capture_id: captureId }); }
  listEncounterProgress(): Promise<EncounterProgress[]> { return this.core("/campaign/encounters/progress?requester_role=dm"); }
  updateEncounterProgress(input: UpdateEncounterProgressInput): Promise<EncounterProgress> { return this.core(`/campaign/encounters/${input.source_document_id}/progress?requester_role=dm`, "PUT", input); }

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

  listSourceDocuments(): Promise<SourceDocumentPage> {
    return this.core(`/imports/source-documents?requester_role=dm&limit=500`);
  }

  getSourceDocument(documentId: string): Promise<SourceDocumentContent> {
    return this.core(`/imports/source-documents/${documentId}?requester_role=dm`);
  }
  getPCProfile(documentId: string): Promise<PCProfile | null> { return this.core(`/imports/source-documents/${documentId}/pc-profile?requester_role=dm`); }
  updatePCProfile(documentId: string, profile: Omit<PCProfile, "document_id"> & { idempotency_key: string }): Promise<PCProfileReceipt> { return this.core(`/imports/source-documents/${documentId}/pc-profile?requester_role=dm`, "PUT", profile); }
  getIdentityGaps(limit = 50): Promise<IdentityGapQueue> { return this.core(`/identity/gaps?requester_role=dm&limit=${limit}`); }
  addIdentityAlias(surface: string, entityId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/add-alias?requester_role=dm", "POST", { surface, entity_id: entityId, idempotency_key: idempotencyKey }); }
  createIdentityEntity(surface: string, entityKind: string, idempotencyKey: string, aliasSurfaces: string[] = [], manualAliases: string[] = []): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/create-entity?requester_role=dm", "POST", { surface, entity_kind: entityKind, alias_surfaces: aliasSurfaces, manual_aliases: manualAliases, idempotency_key: idempotencyKey }); }
  markIdentityRole(surface: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/mark-role?requester_role=dm", "POST", { surface, idempotency_key: idempotencyKey }); }
  dismissIdentityGap(surface: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/dismiss?requester_role=dm", "POST", { surface, idempotency_key: idempotencyKey }); }
  revertIdentityDecision(decisionId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/revert?requester_role=dm", "POST", { decision_id: decisionId, idempotency_key: idempotencyKey }); }
  markIdentityMisspelling(surface: string, entityId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/mark-misspelling?requester_role=dm", "POST", { surface, entity_id: entityId, idempotency_key: idempotencyKey }); }
  getEntityProfile(entityId: string): Promise<EntityProfile | null> { return this.core(`/entities/${entityId}/profile?requester_role=dm`); }
  updateEntityProfile(entityId: string, profile: Omit<EntityProfile, "entity_id"> & { idempotency_key: string }): Promise<EntityProfileReceipt> { return this.core(`/entities/${entityId}/profile?requester_role=dm`, "PUT", profile); }
  proposeEntityKind(entityId: string, entityKind: string): Promise<EntityKindProposalVersion> { return this.core(`/entities/${entityId}/metadata-proposals?requester_role=dm`, "POST", { entity_kind: entityKind, tags: [] }); }
  addMembership(factionId: string, memberId: string, roleTitle?: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/membership?requester_role=dm", "POST", { faction_id: factionId, member_id: memberId, add: true, role_title: roleTitle ?? null, idempotency_key: `membership-add:${factionId}:${memberId}:${Date.now()}` }); }
  removeMembership(factionId: string, memberId: string): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/membership?requester_role=dm", "POST", { faction_id: factionId, member_id: memberId, add: false, idempotency_key: `membership-remove:${factionId}:${memberId}:${Date.now()}` }); }
  assignFactionRole(factionId: string, memberId: string, roleName: string | null, isLeadership: boolean): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/role?requester_role=dm", "POST", { faction_id: factionId, member_id: memberId, role_name: roleName, is_leadership: roleName ? isLeadership : false, idempotency_key: `role-${roleName ? "assign" : "clear"}:${factionId}:${memberId}:${Date.now()}` }); }
  defineFactionRole(factionId: string, roleName: string, isLeadership: boolean): Promise<IdentityDecisionReceipt> { return this.core("/identity/decisions/define-role?requester_role=dm", "POST", { faction_id: factionId, role_name: roleName, is_leadership: isLeadership, idempotency_key: `role-define:${factionId}:${roleName.toLocaleLowerCase()}:${Date.now()}` }); }
  listFactionRoles(): Promise<FactionRoleSummary[]> { return this.core("/identity/roles"); }
  listRoleDeclarations(): Promise<RoleDeclarationSummary[]> { return this.core("/identity/role-declarations"); }
  listRecentDecisions(limit?: number): Promise<IdentityDecisionEntry[]> { return this.core(`/identity/decisions/recent?limit=${limit ?? 100}`); }
  approveEntityMetadataProposal(proposalId: string, itemId: string, versionNumber: number, contentHash: string): Promise<CandidateProposalApproval> { return this.core(`/entities/metadata-proposals/${proposalId}/approvals?requester_role=dm`, "POST", { reviewed_version: versionNumber, content_hash: contentHash, item_ids: [itemId], idempotency_key: `entity-kind-approval:${proposalId}:${versionNumber}` }); }
  discoverClaimOverlaps(): Promise<ClaimOverlap[]> { return this.core("/claims/reconciliation-candidates?requester_role=dm&limit=100"); }
  reconcileClaims(overlap: ClaimOverlap, decision: ReconciliationDecision, reason: string): Promise<ClaimReconciliationReceipt> {
    return this.core("/claims/reconciliations?requester_role=dm", "POST", {
      superseding_claim_id: overlap.superseding.claim_id, superseded_claim_id: overlap.superseded.claim_id,
      superseding_snapshot_hash: overlap.superseding.snapshot_hash, superseded_snapshot_hash: overlap.superseded.snapshot_hash,
      decision, reason, idempotency_key: `claim-reconciliation-${overlap.superseding.claim_id}-${overlap.superseded.claim_id}-${crypto.randomUUID()}`,
    });
  }
  getClaimSnapshot(claimId: string): Promise<ClaimSnapshot> { return this.core(`/claims/${claimId}?requester_role=dm`); }
  correctClaim(claim: ClaimSnapshot, assertionText: string, reason: string): Promise<ClaimCorrectionReceipt> {
    return this.core(`/claims/${claim.claim_id}/corrections?requester_role=dm`, "POST", {
      claim_id: claim.claim_id, snapshot_hash: claim.snapshot_hash, assertion_text: assertionText,
      reason, idempotency_key: `claim-correction-${claim.claim_id}-${crypto.randomUUID()}`,
    });
  }
  replaceClaim(claim: ClaimSnapshot, replacements: ClaimReplacementDraft[], reason: string): Promise<ClaimReplacementReceipt> {
    return this.core(`/claims/${claim.claim_id}/replacements?requester_role=dm`, "POST", {
      claim_id: claim.claim_id, snapshot_hash: claim.snapshot_hash, replacements, reason,
      idempotency_key: `claim-replacement-${claim.claim_id}-${crypto.randomUUID()}`,
    });
  }

  createProposal(items: CreateProposalItem[], workflowSessionId?: string): Promise<CandidateProposalVersion> {
    return this.core("/imports/proposals?requester_role=dm", "POST", { items, workflow_session_id: workflowSessionId });
  }

  reviseProposal(proposalId: string, items: CreateProposalItem[]): Promise<CandidateProposalVersion> {
    return this.core(`/imports/proposals/${proposalId}/versions?requester_role=dm`, "POST", { items });
  }

  getProposal(proposalId: string): Promise<CandidateProposalVersion> {
    return this.core(`/imports/proposals/${proposalId}?requester_role=dm`);
  }

  getCandidateProposal(candidateId: string): Promise<CandidateProposalVersion> {
    return this.core(`/imports/candidates/${candidateId}/proposal?requester_role=dm`);
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

  extractCandidate(candidateId: string): Promise<CandidateExtractionResult> {
    return this.core(`/imports/candidates/${candidateId}/extraction?requester_role=dm`, "POST");
  }

  applyApproval(
    proposal: Pick<CandidateProposalVersion | PlanProposalVersion, "version_number" | "content_hash">,
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

  getTaxonomy(): Promise<TaxonomySnapshot> {
    return this.review({ operation: "get_taxonomy" });
  }
  getAIConfiguration(): Promise<AIConfigurationSnapshot> { return this.review({ operation: "get_ai_configuration" }); }
  activateAIProfile(profileKey: string, purpose: string): Promise<AIActivationReceipt> { return this.review({ operation: "activate_ai_profile", body: { profile_key: profileKey, purpose } }); }
  getAIPrompts(): Promise<EffectivePrompt[]> { return this.review({ operation: "get_ai_prompts" }); }
  getEntityDossier(entityId: string): Promise<DossierView> { return this.review({ operation: "get_entity_dossier", entity_id: entityId }); }
  getTemplateVocabulary(vocabulary: string): Promise<VocabularyValue[]> { return this.review({ operation: "get_template_vocabulary", vocabulary }); }
  getLinkAudit(): Promise<LinkAuditResult> { return this.review({ operation: "get_link_audit" }); }
  reattributeClaim(claimId: string, newEntityId: string, reason: string): Promise<ReattributionReceipt> { return this.review({ operation: "reattribute_claim", claim_id: claimId, body: { claim_id: claimId, new_entity_id: newEntityId, reason } }); }
  getMovedAssertions(entityId: string): Promise<MovedAssertion[]> { return this.review({ operation: "get_moved_assertions", entity_id: entityId }); }
  changeTemplateVocabulary(vocabulary: string, action: "add" | "retire", value: string): Promise<VocabularyChangeReceipt> { return this.review({ operation: "change_template_vocabulary", vocabulary, body: { action, value } }); }
  promoteToDossier(entityId: string, claimId: string): Promise<DossierDecisionReceipt> { return this.review({ operation: "promote_to_dossier", entity_id: entityId, claim_id: claimId }); }
  demoteFromDossier(entityId: string, claimId: string): Promise<DossierDecisionReceipt> { return this.review({ operation: "demote_from_dossier", entity_id: entityId, claim_id: claimId }); }
  setAIPrompt(purpose: string, promptText: string): Promise<PromptOverrideReceipt> { return this.review({ operation: "set_ai_prompt", purpose, body: { purpose, prompt_text: promptText } }); }
  resetAIPrompt(purpose: string): Promise<PromptOverrideReceipt> { return this.review({ operation: "reset_ai_prompt", purpose }); }

  searchEntities(canonicalName: string): Promise<EntityIdentity[]> {
    return this.review({ operation: "search_entities", query: { canonical_name: canonicalName } });
  }
  listLibraryEntries(): Promise<LibraryEntrySummary[]> { return this.review<LibraryEntrySummary[]>({ operation: "list_library_entries" }); }
  getLibraryEntry(entryId: string): Promise<LibraryEntry> { return this.review<LibraryEntry>({ operation: "get_library_entry", entry_id: entryId }); }

  listPlans(planKind?: PlanKind, lifecycle?: PlanLifecycle): Promise<PlanRecord[]> {
    return this.review({ operation: "list_plans", query: { plan_kind: planKind, lifecycle } });
  }

  createPlanProposal(input: CreatePlanInput): Promise<PlanProposalVersion> {
    return this.review({ operation: "create_plan_proposal", body: input });
  }

  transitionPlanProposal(planId: string, lifecycle: PlanLifecycle, supportingClaimIds: string[]): Promise<PlanProposalVersion> {
    return this.review({ operation: "transition_plan_proposal", plan_id: planId,
      body: { plan_id: planId, lifecycle, supporting_claim_ids: supportingClaimIds } });
  }

  getPlanProposal(proposalId: string): Promise<PlanProposalVersion> {
    return this.review({ operation: "get_plan_proposal", proposal_id: proposalId });
  }

  approvePlanProposal(proposal: PlanProposalVersion, idempotencyKey: string): Promise<CandidateProposalApproval> {
    return this.review({
      operation: "approve_plan_proposal", proposal_id: proposal.proposal_id,
      body: { reviewed_version: proposal.version_number, content_hash: proposal.content_hash,
        item_ids: [proposal.item.item_id], idempotency_key: idempotencyKey },
    });
  }

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
  getOpenBrainstorm(): Promise<BrainstormSession | null> { return this.review({ operation: "get_open_brainstorm" }); }
  startBrainstorm(title: string): Promise<BrainstormSession> { return this.review({ operation: "start_brainstorm", body: { title, idempotency_key: `brainstorm-start-${crypto.randomUUID()}` } }); }
  captureBrainstormThought(sessionId: string, text: string, mentions: DirectInputMention[] = []): Promise<BrainstormSession> { return this.review({ operation: "capture_brainstorm_thought", session_id: sessionId, body: { text, mentions, idempotency_key: `brainstorm-thought-${crypto.randomUUID()}` } }); }
  pinBrainstormEntity(sessionId: string, entityId: string): Promise<BrainstormSession> { return this.review({ operation: "pin_brainstorm_entity", session_id: sessionId, entity_id: entityId }); }
  unpinBrainstormEntity(sessionId: string, entityId: string): Promise<BrainstormSession> { return this.review({ operation: "unpin_brainstorm_entity", session_id: sessionId, entity_id: entityId }); }
  pinBrainstormEvidence(sessionId: string, recordId: string, searchQuery?: string): Promise<BrainstormSession> { return this.review({ operation: "pin_brainstorm_evidence", session_id: sessionId, record_id: recordId, query: { search_query: searchQuery } }); }
  unpinBrainstormEvidence(sessionId: string, recordId: string): Promise<BrainstormSession> { return this.review({ operation: "unpin_brainstorm_evidence", session_id: sessionId, record_id: recordId }); }
  closeBrainstorm(sessionId: string, proposalId: string): Promise<BrainstormSession> { return this.review({ operation: "close_brainstorm", session_id: sessionId, body: { proposal_id: proposalId } }); }
  captureSessionNote(input: SessionNoteCaptureInput): Promise<SessionNoteCaptureReceipt> { return this.review({ operation: "capture_session_note", body: input }); }
  getCurrentCampaignDate(): Promise<CampaignDate | null> { return this.review({ operation: "get_current_campaign_date" }); }
  setCurrentCampaignDate(date: CampaignDate, reason?: string): Promise<CampaignDate> { return this.review({ operation: "set_current_campaign_date", body: { calendar_id: date.calendar_id, year: date.year, month: date.month, day: date.day, reason: reason ?? null } }); }
  getCampaignDateHistory(limit?: number): Promise<CampaignClockChange[]> { return this.review<CampaignClockChange[]>({ operation: "get_campaign_date_history", query: { limit } }); }
  getSessionDatingWalk(): Promise<SessionDatingEntry[]> { return this.review<SessionDatingEntry[]>({ operation: "get_session_dating_walk" }); }
  setSessionDate(documentId: string, year: number, month: number, day: number, reason?: string): Promise<SessionDateResult> { return this.review<SessionDateResult>({ operation: "set_session_document_date", path_id: documentId, body: { year, month, day, reason: reason ?? null } }); }
  inheritClaimDates(): Promise<InheritResult> { return this.review<InheritResult>({ operation: "inherit_claim_dates" }); }
  getUndatedClaims(limit?: number): Promise<UndatedClaimEntry[]> { return this.review<UndatedClaimEntry[]>({ operation: "get_undated_claims", query: { limit } }); }
  getConflictQueue(): Promise<ConflictPair[]> { return this.review<ConflictPair[]>({ operation: "get_conflict_queue" }); }
  decideConflict(claimAId: string, claimBId: string, action: "dismiss" | "supersede", reason: string): Promise<ConflictDecisionResult> { return this.review<ConflictDecisionResult>({ operation: "decide_conflict", body: { claim_a_id: claimAId, claim_b_id: claimBId, action, reason } }); }
  writeEntityDescription(entityId: string, text: string, referencedClaimIds: string[], idempotencyKey: string, documentId?: string | null): Promise<EntityDescriptionReceipt> { return this.review<EntityDescriptionReceipt>({ operation: "write_entity_description", entity_id: entityId, body: { entity_id: entityId, text, referenced_claim_ids: referencedClaimIds, idempotency_key: idempotencyKey, ...(documentId ? { document_id: documentId } : {}) } }); }
  draftProse(command: ProseDraftCommand): Promise<ProseDraftResult> { return this.review<ProseDraftResult>({ operation: "draft_prose", body: command }); }
  getEntityGraphNeighborhood(entityId: string): Promise<GraphRelationRow[]> { return this.review<GraphRelationRow[]>({ operation: "get_entity_graph_neighborhood", entity_id: entityId }); }
  getLifeStatusProposals(): Promise<LifeStatusProposal[]> { return this.review<LifeStatusProposal[]>({ operation: "get_life_status_proposals" }); }
  setLifeStatus(entityId: string, status: string, since: { year: number; month: number; day: number }, claimId: string | null, idempotencyKey: string): Promise<LifeStatusReceipt> { return this.review<LifeStatusReceipt>({ operation: "set_life_status", entity_id: entityId, body: { status, since_year: since.year, since_month: since.month, since_day: since.day, claim_id: claimId, idempotency_key: idempotencyKey } }); }
  getDeadSeats(): Promise<DeadSeat[]> { return this.review<DeadSeat[]>({ operation: "get_dead_seats" }); }
  getOpenSessionRun(): Promise<SessionRun | null> { return this.review({ operation: "get_open_session_run" }); }
  openSessionRun(input: OpenSessionRunInput): Promise<SessionRun> { return this.review({ operation: "open_session_run", body: input }); }
  saveSessionRunNote(runId: string, note: SaveSessionRunNoteInput): Promise<SessionRunNote> { return this.review({ operation: "save_session_run_note", run_id: runId, note_id: note.note_id, body: note }); }
  async deleteSessionRunNote(runId: string, noteId: string): Promise<void> { await this.review({ operation: "delete_session_run_note", run_id: runId, note_id: noteId }); }
  closeSessionRun(runId: string, sourceDocumentId: string, captureId: string): Promise<SessionRun> { return this.review({ operation: "close_session_run", run_id: runId, body: { captured_source_document_id: sourceDocumentId, capture_id: captureId } }); }
  listEncounterProgress(): Promise<EncounterProgress[]> { return this.review({ operation: "list_encounter_progress" }); }
  updateEncounterProgress(input: UpdateEncounterProgressInput): Promise<EncounterProgress> { return this.review({ operation: "update_encounter_progress", document_id: input.source_document_id, body: input }); }

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

  listSourceDocuments(): Promise<SourceDocumentPage> {
    return this.review({ operation: "list_source_documents", query: { limit: 500 } });
  }

  getSourceDocument(documentId: string): Promise<SourceDocumentContent> {
    return this.review({ operation: "get_source_document", document_id: documentId });
  }
  getPCProfile(documentId: string): Promise<PCProfile | null> { return this.review({ operation: "get_pc_profile", document_id: documentId }); }
  updatePCProfile(documentId: string, profile: Omit<PCProfile, "document_id"> & { idempotency_key: string }): Promise<PCProfileReceipt> { return this.review({ operation: "update_pc_profile", document_id: documentId, body: profile }); }
  getIdentityGaps(limit = 50): Promise<IdentityGapQueue> { return this.review({ operation: "list_identity_gaps", query: { limit } }); }
  addIdentityAlias(surface: string, entityId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "add_identity_alias", body: { surface, entity_id: entityId, idempotency_key: idempotencyKey } }); }
  createIdentityEntity(surface: string, entityKind: string, idempotencyKey: string, aliasSurfaces: string[] = [], manualAliases: string[] = []): Promise<IdentityDecisionReceipt> { return this.review({ operation: "create_identity_entity", body: { surface, entity_kind: entityKind, alias_surfaces: aliasSurfaces, manual_aliases: manualAliases, idempotency_key: idempotencyKey } }); }
  markIdentityRole(surface: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "mark_identity_role", body: { surface, idempotency_key: idempotencyKey } }); }
  dismissIdentityGap(surface: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "dismiss_identity_gap", body: { surface, idempotency_key: idempotencyKey } }); }
  revertIdentityDecision(decisionId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "revert_identity_decision", body: { decision_id: decisionId, idempotency_key: idempotencyKey } }); }
  markIdentityMisspelling(surface: string, entityId: string, idempotencyKey: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "mark_identity_misspelling", body: { surface, entity_id: entityId, idempotency_key: idempotencyKey } }); }
  getEntityProfile(entityId: string): Promise<EntityProfile | null> { return this.review({ operation: "get_entity_profile", path_id: entityId }); }
  updateEntityProfile(entityId: string, profile: Omit<EntityProfile, "entity_id"> & { idempotency_key: string }): Promise<EntityProfileReceipt> { return this.review({ operation: "update_entity_profile", path_id: entityId, body: profile }); }
  proposeEntityKind(entityId: string, entityKind: string): Promise<EntityKindProposalVersion> { return this.review({ operation: "create_entity_metadata_proposal", path_id: entityId, body: { entity_kind: entityKind, tags: [] } }); }
  addMembership(factionId: string, memberId: string, roleTitle?: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "membership_decision", body: { faction_id: factionId, member_id: memberId, add: true, role_title: roleTitle ?? null, idempotency_key: `membership-add:${factionId}:${memberId}:${Date.now()}` } }); }
  removeMembership(factionId: string, memberId: string): Promise<IdentityDecisionReceipt> { return this.review({ operation: "membership_decision", body: { faction_id: factionId, member_id: memberId, add: false, idempotency_key: `membership-remove:${factionId}:${memberId}:${Date.now()}` } }); }
  assignFactionRole(factionId: string, memberId: string, roleName: string | null, isLeadership: boolean): Promise<IdentityDecisionReceipt> { return this.review({ operation: "role_decision", body: { faction_id: factionId, member_id: memberId, role_name: roleName, is_leadership: roleName ? isLeadership : false, idempotency_key: `role-${roleName ? "assign" : "clear"}:${factionId}:${memberId}:${Date.now()}` } }); }
  defineFactionRole(factionId: string, roleName: string, isLeadership: boolean): Promise<IdentityDecisionReceipt> { return this.review({ operation: "define_role_decision", body: { faction_id: factionId, role_name: roleName, is_leadership: isLeadership, idempotency_key: `role-define:${factionId}:${roleName.toLocaleLowerCase()}:${Date.now()}` } }); }
  listFactionRoles(): Promise<FactionRoleSummary[]> { return this.review<FactionRoleSummary[]>({ operation: "list_faction_roles" }); }
  listRoleDeclarations(): Promise<RoleDeclarationSummary[]> { return this.review<RoleDeclarationSummary[]>({ operation: "list_role_declarations" }); }
  listRecentDecisions(limit?: number): Promise<IdentityDecisionEntry[]> { return this.review<IdentityDecisionEntry[]>({ operation: "list_recent_decisions", query: { limit } }); }
  approveEntityMetadataProposal(proposalId: string, itemId: string, versionNumber: number, contentHash: string): Promise<CandidateProposalApproval> { return this.review({ operation: "approve_entity_metadata_proposal", proposal_id: proposalId, body: { reviewed_version: versionNumber, content_hash: contentHash, item_ids: [itemId], idempotency_key: `entity-kind-approval:${proposalId}:${versionNumber}` } }); }
  discoverClaimOverlaps(): Promise<ClaimOverlap[]> { return this.review({ operation: "discover_claim_overlaps" }); }
  reconcileClaims(overlap: ClaimOverlap, decision: ReconciliationDecision, reason: string): Promise<ClaimReconciliationReceipt> {
    return this.review({ operation: "reconcile_claims", body: {
      superseding_claim_id: overlap.superseding.claim_id, superseded_claim_id: overlap.superseded.claim_id,
      superseding_snapshot_hash: overlap.superseding.snapshot_hash, superseded_snapshot_hash: overlap.superseded.snapshot_hash,
      decision, reason, idempotency_key: `claim-reconciliation-${overlap.superseding.claim_id}-${overlap.superseded.claim_id}-${crypto.randomUUID()}`,
    } });
  }
  getClaimSnapshot(claimId: string): Promise<ClaimSnapshot> { return this.review({ operation: "get_claim_snapshot", claim_id: claimId }); }
  correctClaim(claim: ClaimSnapshot, assertionText: string, reason: string): Promise<ClaimCorrectionReceipt> {
    return this.review({ operation: "correct_claim", claim_id: claim.claim_id, body: {
      claim_id: claim.claim_id, snapshot_hash: claim.snapshot_hash, assertion_text: assertionText,
      reason, idempotency_key: `claim-correction-${claim.claim_id}-${crypto.randomUUID()}`,
    } });
  }
  replaceClaim(claim: ClaimSnapshot, replacements: ClaimReplacementDraft[], reason: string): Promise<ClaimReplacementReceipt> {
    return this.review({ operation: "replace_claim", claim_id: claim.claim_id, body: {
      claim_id: claim.claim_id, snapshot_hash: claim.snapshot_hash, replacements, reason,
      idempotency_key: `claim-replacement-${claim.claim_id}-${crypto.randomUUID()}`,
    } });
  }

  createProposal(items: CreateProposalItem[], workflowSessionId?: string): Promise<CandidateProposalVersion> {
    return this.review({ operation: "create_proposal", body: { items, workflow_session_id: workflowSessionId } });
  }

  reviseProposal(proposalId: string, items: CreateProposalItem[]): Promise<CandidateProposalVersion> {
    return this.review({ operation: "revise_proposal", proposal_id: proposalId, body: { items } });
  }

  getProposal(proposalId: string): Promise<CandidateProposalVersion> {
    return this.review({ operation: "get_proposal", proposal_id: proposalId });
  }

  getCandidateProposal(candidateId: string): Promise<CandidateProposalVersion> {
    return this.review({ operation: "get_candidate_proposal", candidate_id: candidateId });
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

  extractCandidate(candidateId: string): Promise<CandidateExtractionResult> {
    return this.review({ operation: "extract_candidate", candidate_id: candidateId });
  }

  applyApproval(
    proposal: Pick<CandidateProposalVersion | PlanProposalVersion, "version_number" | "content_hash">,
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
