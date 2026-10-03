interface ReviewBackendRequest {
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
    | "get_template_vocabulary"
    | "get_link_audit"
    | "get_unpromoted_material"
    | "get_orphaned_claims"
    | "list_brainstorm_sessions"
    | "capture_encounter_document"
    | "get_owner_suggestions"
    | "dispose_claim_owner"
    | "mint_encounter_entity"
    | "get_qualified_entities"
    | "get_exclusive_claims"
    | "reattribute_claim"
    | "get_moved_assertions"
    | "change_template_vocabulary"
    | "get_entity_dossier"
    | "promote_to_dossier"
    | "demote_from_dossier"
    | "set_ai_prompt"
    | "reset_ai_prompt"
    | "discover_claim_overlaps"
    | "reconcile_claims"
    | "get_claim_snapshot"
    | "correct_claim"
    | "replace_claim"
    | "derive_promotion"
    | "approve_promotion";
  candidate_id?: string;
  proposal_id?: string;
  version_number?: number;
  content_hash?: string;
  plan_id?: string;
  document_id?: string;
  path_id?: string;
  change_set_id?: string;
  claim_id?: string;
  entry_id?: string;
  run_id?: string;
  session_id?: string;
    entity_id?: string;
  purpose?: string;
  text?: string;
  limit?: number;
  vocabulary?: string;
  record_id?: string;
  note_id?: string;
  query?: Record<string, string | number | undefined>;
  body?: unknown;
}

type RuntimeGlobal = typeof globalThis & {
  process?: { env?: Record<string, string | undefined> };
};

function configuredCoreUrl(): string {
  const environment = (globalThis as RuntimeGlobal).process?.env;
  return environment?.CAMPAIGN_CORE_URL ?? "http://campaign-core:8000";
}

function required(value: string | undefined, name: string): string {
  if (!value) throw new Error(`${name} is required for this campaign operation`);
  return value;
}

function route(input: ReviewBackendRequest): { method: "GET" | "POST" | "PUT" | "DELETE"; path: string } {
  switch (input.operation) {
    case "get_ai_configuration":
      return { method: "GET", path: "ai/configuration" };
    case "activate_ai_profile":
      return { method: "POST", path: "ai/configuration/activate" };
    case "draft_prose":
      return { method: "POST", path: "prose/draft" };
    case "derive_promotion":
      return { method: "POST", path: "promotion/derive" };
    case "approve_promotion":
      return { method: "POST", path: "promotion/approve" };
    case "get_entity_graph_neighborhood":
      return { method: "GET", path: `entities/${required(input.entity_id, "entity_id")}/graph-neighborhood` };
    case "get_ai_prompts":
      return { method: "GET", path: "ai/prompts" };
    case "reattribute_claim":
      return { method: "POST", path: `claims/${required(input.claim_id, "claim_id")}/reattribute` };
    case "get_moved_assertions":
      return { method: "GET", path: `entities/${required(input.entity_id, "entity_id")}/moved-assertions` };
    case "get_link_audit":
      return { method: "GET", path: "campaign/link-audit" };
    case "get_unpromoted_material":
      return { method: "GET", path: "campaign/unpromoted-material" };
    case "get_orphaned_claims":
      return { method: "GET", path: "campaign/orphaned-claims" };
    case "list_brainstorm_sessions":
      return { method: "GET", path: "campaign/brainstorm-sessions" };
    case "capture_encounter_document":
      return { method: "POST", path: "capture/encounters" };
    case "get_owner_suggestions":
      return { method: "GET", path: `campaign/owner-suggestions?limit=${input.limit ?? 3}&text=${encodeURIComponent(required(input.text, "text"))}` };
    case "dispose_claim_owner":
      return { method: "POST", path: `claims/${required(input.claim_id, "claim_id")}/owner-disposition` };
    case "mint_encounter_entity":
      return { method: "POST", path: "campaign/encounter-entities" };
    case "get_qualified_entities":
      return { method: "GET", path: "campaign/qualified-entities" };
    case "get_exclusive_claims":
      return { method: "GET", path: "campaign/unqualified-exclusive-claims" };
    case "get_template_vocabulary":
      return { method: "GET", path: `template-vocabularies/${required(input.vocabulary, "vocabulary")}` };
    case "change_template_vocabulary":
      return { method: "POST", path: `template-vocabularies/${required(input.vocabulary, "vocabulary")}` };
    case "get_entity_dossier":
      return { method: "GET", path: `entities/${required(input.entity_id, "entity_id")}/dossier` };
    case "promote_to_dossier":
      return { method: "POST", path: `entities/${required(input.entity_id, "entity_id")}/dossier/${required(input.claim_id, "claim_id")}/promote` };
    case "demote_from_dossier":
      return { method: "POST", path: `entities/${required(input.entity_id, "entity_id")}/dossier/${required(input.claim_id, "claim_id")}/demote` };
    case "set_ai_prompt":
      return { method: "PUT", path: `ai/prompts/${required(input.purpose, "purpose")}` };
    case "reset_ai_prompt":
      return { method: "DELETE", path: `ai/prompts/${required(input.purpose, "purpose")}` };
    case "discover_claim_overlaps":
      return { method: "GET", path: "claims/reconciliation-candidates" };
    case "reconcile_claims":
      return { method: "POST", path: "claims/reconciliations" };
    case "get_claim_snapshot":
      return { method: "GET", path: `claims/${required(input.claim_id, "claim_id")}` };
    case "correct_claim":
      return { method: "POST", path: `claims/${required(input.claim_id, "claim_id")}/corrections` };
    case "replace_claim":
      return { method: "POST", path: `claims/${required(input.claim_id, "claim_id")}/replacements` };
    case "get_taxonomy":
      return { method: "GET", path: "taxonomy" };
    case "search_entities":
      return { method: "GET", path: "entities" };
    case "list_library_entries":
      return { method: "GET", path: "library/entries" };
    case "get_library_entry":
      return { method: "GET", path: `library/entries/${required(input.entry_id, "entry_id")}` };
    case "list_plans":
      return { method: "GET", path: "plans" };
    case "create_plan_proposal":
      return { method: "POST", path: "plans/proposals" };
    case "transition_plan_proposal":
      return { method: "POST", path: `plans/${required(input.plan_id, "plan_id")}/lifecycle-proposals` };
    case "get_plan_proposal":
      return { method: "GET", path: `plans/proposals/${required(input.proposal_id, "proposal_id")}` };
    case "approve_plan_proposal":
      return { method: "POST", path: `plans/proposals/${required(input.proposal_id, "proposal_id")}/approvals` };
    case "list_runs":
      return { method: "GET", path: "imports/runs" };
    case "get_open_brainstorm":
      return { method: "GET", path: "brainstorms/open" };
    case "start_brainstorm":
      return { method: "POST", path: "brainstorms" };
    case "capture_brainstorm_thought":
      return { method: "POST", path: `brainstorms/${required(input.session_id, "session_id")}/thoughts` };
    case "pin_brainstorm_entity":
      return { method: "PUT", path: `brainstorms/${required(input.session_id, "session_id")}/pins/${required(input.entity_id, "entity_id")}` };
    case "unpin_brainstorm_entity":
      return { method: "DELETE", path: `brainstorms/${required(input.session_id, "session_id")}/pins/${required(input.entity_id, "entity_id")}` };
    case "pin_brainstorm_evidence":
      return { method: "PUT", path: `brainstorms/${required(input.session_id, "session_id")}/evidence-pins/${encodeURIComponent(required(input.record_id, "record_id"))}` };
    case "unpin_brainstorm_evidence":
      return { method: "DELETE", path: `brainstorms/${required(input.session_id, "session_id")}/evidence-pins/${encodeURIComponent(required(input.record_id, "record_id"))}` };
    case "close_brainstorm":
      return { method: "POST", path: `brainstorms/${required(input.session_id, "session_id")}/close` };
    case "capture_session_note":
      return { method: "POST", path: "capture/session-notes" };
    case "get_current_campaign_date": return { method: "GET", path: "campaign/current-date" };
    case "set_current_campaign_date": return { method: "PUT", path: "campaign/current-date?requester_role=dm" };
    case "get_campaign_date_history": return { method: "GET", path: `campaign/current-date/history?limit=${input.query?.limit ?? 10}` };
    case "get_session_dating_walk": return { method: "GET", path: "campaign/session-dating" };
    case "set_session_document_date": return { method: "PUT", path: `campaign/session-dating/${required(input.path_id, "path_id")}?requester_role=dm` };
    case "inherit_claim_dates": return { method: "POST", path: "campaign/claim-dates/inherit?requester_role=dm" };
    case "get_undated_claims": return { method: "GET", path: `campaign/undated-claims?limit=${input.query?.limit ?? 50}` };
    case "get_conflict_queue": return { method: "GET", path: "campaign/conflicts" };
    case "decide_conflict": return { method: "POST", path: "campaign/conflicts/decisions?requester_role=dm" };
    case "write_entity_description": return { method: "POST", path: `entities/${required(input.entity_id, "entity_id")}/description?requester_role=dm` };
    case "derive_promotion": return { method: "POST", path: "promotion/derive?requester_role=dm" };
    case "approve_promotion": return { method: "POST", path: "promotion/approve?requester_role=dm" };
    case "get_life_status_proposals": return { method: "GET", path: "campaign/life-status/proposals" };
    case "set_life_status": return { method: "POST", path: `campaign/life-status/${required(input.entity_id, "entity_id")}?requester_role=dm` };
    case "get_dead_seats": return { method: "GET", path: "campaign/dead-seats" };
    case "get_open_session_run":
      return { method: "GET", path: "campaign/session-runs/open" };
    case "open_session_run":
      return { method: "POST", path: "campaign/session-runs/open" };
    case "save_session_run_note":
      return { method: "PUT", path: `campaign/session-runs/${required(input.run_id, "run_id")}/notes/${required(input.note_id, "note_id")}` };
    case "delete_session_run_note":
      return { method: "DELETE", path: `campaign/session-runs/${required(input.run_id, "run_id")}/notes/${required(input.note_id, "note_id")}` };
    case "close_session_run":
      return { method: "POST", path: `campaign/session-runs/${required(input.run_id, "run_id")}/close` };
    case "list_encounter_progress":
      return { method: "GET", path: "campaign/encounters/progress" };
    case "update_encounter_progress":
      return { method: "PUT", path: `campaign/encounters/${required(input.document_id, "document_id")}/progress` };
    case "list_candidates":
      return { method: "GET", path: "imports/candidates" };
    case "get_candidate":
      return {
        method: "GET",
        path: `imports/candidates/${required(input.candidate_id, "candidate_id")}`,
      };
    case "list_reviews":
      return { method: "GET", path: "imports/reviews" };
    case "list_source_documents":
      return { method: "GET", path: "imports/source-documents" };
    case "get_source_document":
      return {
        method: "GET",
        path: `imports/source-documents/${required(input.document_id, "document_id")}`,
      };
    case "get_pc_profile": return { method: "GET", path: `imports/source-documents/${required(input.document_id, "document_id")}/pc-profile` };
    case "update_pc_profile": return { method: "PUT", path: `imports/source-documents/${required(input.document_id, "document_id")}/pc-profile` };
    case "list_identity_gaps": return { method: "GET", path: "identity/gaps" };
    case "add_identity_alias": return { method: "POST", path: "identity/decisions/add-alias" };
    case "create_identity_entity": return { method: "POST", path: "identity/decisions/create-entity" };
    case "mark_identity_role": return { method: "POST", path: "identity/decisions/mark-role" };
    case "dismiss_identity_gap": return { method: "POST", path: "identity/decisions/dismiss" };
    case "revert_identity_decision": return { method: "POST", path: "identity/decisions/revert" };
    case "mark_identity_misspelling": return { method: "POST", path: "identity/decisions/mark-misspelling" };
    case "get_entity_profile": return { method: "GET", path: `entities/${required(input.path_id, "path_id")}/profile` };
    case "update_entity_profile": return { method: "PUT", path: `entities/${required(input.path_id, "path_id")}/profile` };
    case "create_entity_metadata_proposal": return { method: "POST", path: `entities/${required(input.path_id, "path_id")}/metadata-proposals` };
    case "membership_decision": return { method: "POST", path: "identity/decisions/membership" };
    case "role_decision": return { method: "POST", path: "identity/decisions/role" };
    case "define_role_decision": return { method: "POST", path: "identity/decisions/define-role" };
    case "list_faction_roles": return { method: "GET", path: "identity/roles" };
    case "list_role_declarations": return { method: "GET", path: "identity/role-declarations" };
    case "list_recent_decisions": return { method: "GET", path: `identity/decisions/recent?limit=${input.query?.limit ?? 100}` };
    case "approve_entity_metadata_proposal": return { method: "POST", path: `entities/metadata-proposals/${required(input.proposal_id, "proposal_id")}/approvals` };
    case "create_proposal":
      return { method: "POST", path: "imports/proposals" };
    case "revise_proposal":
      return { method: "POST", path: `imports/proposals/${required(input.proposal_id, "proposal_id")}/versions` };
    case "get_proposal":
      return {
        method: "GET",
        path: `imports/proposals/${required(input.proposal_id, "proposal_id")}`,
      };
    case "get_candidate_proposal":
      return { method: "GET", path: `imports/candidates/${required(input.candidate_id, "candidate_id")}/proposal` };
    case "approve_proposal":
      return {
        method: "POST",
        path: `imports/proposals/${required(input.proposal_id, "proposal_id")}/approvals`,
      };
    case "disposition_candidate":
      return {
        method: "POST",
        path: `imports/candidates/${required(input.candidate_id, "candidate_id")}/disposition`,
      };
    case "extract_candidate":
      return {
        method: "POST",
        path: `imports/candidates/${required(input.candidate_id, "candidate_id")}/extraction`,
      };
    case "apply_approval":
      return {
        method: "POST",
        path: `change-sets/${required(input.change_set_id, "change_set_id")}/apply`,
      };
  }
}

export async function reviewCampaign(
  input: ReviewBackendRequest,
  coreUrl: string,
  request: typeof fetch,
): Promise<unknown> {
  const selected = route(input);
  const endpoint = new URL(selected.path, `${coreUrl.replace(/\/+$/, "")}/`);
  if (endpoint.protocol !== "http:" && endpoint.protocol !== "https:") {
    throw new Error("CAMPAIGN_CORE_URL must be an absolute HTTP(S) URL");
  }
  endpoint.searchParams.set("requester_role", "dm");
  Object.entries(input.query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") endpoint.searchParams.set(key, String(value));
  });

  const response = await request(endpoint, {
    method: selected.method,
    headers: input.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: input.body === undefined ? undefined : JSON.stringify(input.body),
  });
  if (!response.ok) {
    let detail = `Campaign Core returned ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string | Array<{ msg?: string; loc?: string[] }> };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        // FastAPI 422 returns an array of field-level validation errors.
        detail = payload.detail
          .map((error) => `${(error.loc ?? []).join(".")}: ${error.msg ?? "invalid"}`)
          .join("; ");
      }
    } catch {
      // Preserve the status-only failure when no structured error is available.
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function main(input: ReviewBackendRequest): Promise<unknown> {
  return reviewCampaign(input, configuredCoreUrl(), globalThis.fetch.bind(globalThis));
}
