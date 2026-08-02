import { describe, expect, it, vi } from "vitest";

import {
  CampaignClientError,
  HttpCampaignClient,
  WindmillCampaignClient,
  type CampaignBackend,
} from "./campaignClient";

describe("HttpCampaignClient", () => {
  it("binds a receiver-sensitive browser fetch to the global object", async () => {
    const request = vi.fn(function (this: unknown) {
      if (this !== globalThis) {
        throw new TypeError("Illegal invocation");
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            answer_mode: "insufficient_evidence",
            evidence: [],
            citations: [],
            reasons: ["unsupported_detail"],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    }) as typeof fetch;
    const client = new HttpCampaignClient("/campaign-core", request);

    const result = await client.query({
      question: "What is unknown?",
      requester_visibility: { role: "dm" },
    });

    expect(result.answer_mode).toBe("insufficient_evidence");
    expect(request).toHaveBeenCalledOnce();
  });

  it("posts a typed DM retrieval query through Campaign Core", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ answer_mode: "answer", evidence: [], citations: [], reasons: ["grounded_answer"] }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = new HttpCampaignClient("/campaign-core/", request);

    const result = await client.query({
      question: "What is established?",
      requester_visibility: { role: "dm" },
    });

    expect(result.answer_mode).toBe("answer");
    expect(request).toHaveBeenCalledWith(
      "/campaign-core/retrieval/query",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "What is established?",
          requester_visibility: { role: "dm" },
        }),
      }),
    );
  });

  it("raises a typed error without fabricating a response", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(new Response("no", { status: 503 }));
    const client = new HttpCampaignClient("/campaign-core", request);

    await expect(
      client.query({ question: "Unknown?", requester_visibility: { role: "dm" } }),
    ).rejects.toEqual(new CampaignClientError("Campaign Core returned 503", 503));
  });

  it("loads every source review page so quarantine totals are not truncated", async () => {
    const firstItems = Array.from({ length: 100 }, (_, index) => ({
      review_id: `review-${index}`,
      kind: "import_warning",
      status: "open",
      subject_type: "source_document",
      subject_id: `source-${index}`,
      details: {},
      opened_by_import_run_id: "run-1",
    }));
    const request = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ items: firstItems, total: 101, limit: 100, offset: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ items: [{ ...firstItems[0], review_id: "review-100" }], total: 101, limit: 100, offset: 100 }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    const client = new HttpCampaignClient("/campaign-core", request);

    const page = await client.listReviews("run-1");

    expect(page.items).toHaveLength(101);
    expect(request).toHaveBeenNthCalledWith(
      2,
      "/campaign-core/imports/reviews?requester_role=dm&run_id=run-1&limit=100&offset=100",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

describe("WindmillCampaignClient", () => {
  it("routes the typed query through the generated backend binding", async () => {
    const query_campaign = vi.fn<CampaignBackend["query_campaign"]>().mockResolvedValue({
      answer_mode: "insufficient_evidence",
      evidence: [],
      citations: [],
      reasons: ["unsupported_detail"],
    });
    const review_campaign = vi.fn<CampaignBackend["review_campaign"]>();
    const client = new WindmillCampaignClient({ query_campaign, review_campaign });
    const query = {
      question: "What is unknown?",
      requester_visibility: { role: "dm" as const },
    };

    const result = await client.query(query);

    expect(result.answer_mode).toBe("insufficient_evidence");
    expect(query_campaign).toHaveBeenCalledWith({ query });
  });

  it("routes exact review and approval commands through the generated binding", async () => {
    const review_campaign = vi
      .fn<CampaignBackend["review_campaign"]>()
      .mockResolvedValueOnce({ items: [], total: 0, limit: 50, offset: 0 })
      .mockResolvedValueOnce({ approval_id: "approval-1" });
    const client = new WindmillCampaignClient({
      query_campaign: vi.fn<CampaignBackend["query_campaign"]>(),
      review_campaign,
    });
    const proposal = {
      proposal_id: "proposal-1",
      workflow_session_id: "workflow-1",
      status: "pending",
      version_id: "version-1",
      version_number: 2,
      content_hash: "a".repeat(64),
      created_at: "2026-08-01T12:00:00Z",
      items: [],
    };

    await client.listCandidates({ review_status: "pending" });
    await client.approveProposal(proposal, ["item-1"], "approval-key");

    expect(review_campaign).toHaveBeenNthCalledWith(1, {
      input: {
        operation: "list_candidates",
        query: { limit: 50, review_status: "pending" },
      },
    });
    expect(review_campaign).toHaveBeenNthCalledWith(2, {
      input: {
        operation: "approve_proposal",
        proposal_id: "proposal-1",
        body: {
          reviewed_version: 2,
          content_hash: "a".repeat(64),
          item_ids: ["item-1"],
          idempotency_key: "approval-key",
        },
      },
    });
  });
});
