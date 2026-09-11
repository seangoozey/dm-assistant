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
  run_id?: string;
  session_id?: string;
  entity_id?: string;
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
    case "get_current_campaign_date":
      return { method: "GET", path: "campaign/current-date" };
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
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
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
