interface RetrievalQuery {
  question: string;
  requester_visibility: {
    role: "dm" | "party" | "character";
    character_id?: string;
  };
}

interface RetrievalResult {
  answer_mode: "answer" | "insufficient_evidence" | "conflict" | "possible_retcon" | "restricted";
  evidence: Array<{
    record_id: string;
    assertion: string;
    citation: string;
    state: string;
    authority: string;
    role: "support" | "context" | "conflict";
  }>;
  citations: string[];
  reasons: string[];
}

type RuntimeGlobal = typeof globalThis & {
  process?: { env?: Record<string, string | undefined> };
};

function configuredCoreUrl(): string {
  const environment = (globalThis as RuntimeGlobal).process?.env;
  return environment?.CAMPAIGN_CORE_URL ?? "http://campaign-core:8000";
}

export async function queryCampaign(
  query: RetrievalQuery,
  coreUrl: string,
  request: typeof fetch,
): Promise<RetrievalResult> {
  const endpoint = new URL("retrieval/query", `${coreUrl.replace(/\/+$/, "")}/`);
  if (endpoint.protocol !== "http:" && endpoint.protocol !== "https:") {
    throw new Error("CAMPAIGN_CORE_URL must be an absolute HTTP(S) URL");
  }

  const response = await request(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(query),
  });
  if (!response.ok) {
    throw new Error(`Campaign Core returned ${response.status}`);
  }
  return (await response.json()) as RetrievalResult;
}

export async function main(query: RetrievalQuery): Promise<RetrievalResult> {
  return queryCampaign(query, configuredCoreUrl(), globalThis.fetch.bind(globalThis));
}
