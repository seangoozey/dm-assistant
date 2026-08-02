interface ReviewBackendRequest {
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

function route(input: ReviewBackendRequest): { method: "GET" | "POST"; path: string } {
  switch (input.operation) {
    case "list_runs":
      return { method: "GET", path: "imports/runs" };
    case "list_candidates":
      return { method: "GET", path: "imports/candidates" };
    case "get_candidate":
      return {
        method: "GET",
        path: `imports/candidates/${required(input.candidate_id, "candidate_id")}`,
      };
    case "list_reviews":
      return { method: "GET", path: "imports/reviews" };
    case "create_proposal":
      return { method: "POST", path: "imports/proposals" };
    case "get_proposal":
      return {
        method: "GET",
        path: `imports/proposals/${required(input.proposal_id, "proposal_id")}`,
      };
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
