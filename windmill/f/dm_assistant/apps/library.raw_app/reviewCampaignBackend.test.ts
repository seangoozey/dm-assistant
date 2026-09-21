import { describe, expect, it, vi } from "vitest";

import { reviewCampaign } from "./backend/review_campaign";

describe("reviewCampaign backend runnable", () => {
  it("allows only the typed route and adds DM visibility", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await reviewCampaign(
      {
        operation: "list_candidates",
        query: { review_status: "pending", source: "sanitized" },
      },
      "http://campaign-core:8000",
      request,
    );

    const endpoint = request.mock.calls[0]?.[0] as URL;
    expect(endpoint.pathname).toBe("/imports/candidates");
    expect(endpoint.searchParams.get("requester_role")).toBe("dm");
    expect(endpoint.searchParams.get("review_status")).toBe("pending");
    expect(endpoint.searchParams.get("source")).toBe("sanitized");
  });

  it("maps the campaign clock operations to their exact routes", async () => {
    const ok = () => new Response(JSON.stringify({ calendar_id: "gregorian-ce", year: 505, month: 11, day: 26 }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    const request = vi.fn<typeof fetch>().mockImplementation(async () => ok());

    await reviewCampaign({ operation: "get_current_campaign_date" }, "http://campaign-core:8000", request);
    await reviewCampaign(
      { operation: "set_current_campaign_date", body: { calendar_id: "gregorian-ce", year: 505, month: 11, day: 26, reason: null } },
      "http://campaign-core:8000", request);
    await reviewCampaign({ operation: "get_campaign_date_history", query: { limit: 5 } }, "http://campaign-core:8000", request);

    const [first, second, third] = request.mock.calls as unknown as Array<[URL, RequestInit]>;
    // Reading the clock must never fall through to the mutating PUT.
    expect([first[1].method, first[0].pathname]).toEqual(["GET", "/campaign/current-date"]);
    expect([second[1].method, second[0].pathname]).toEqual(["PUT", "/campaign/current-date"]);
    expect([third[1].method, third[0].pathname]).toEqual(["GET", "/campaign/current-date/history"]);
    expect(third[0].searchParams.get("limit")).toBe("5");
  });

  it("routes prose drafting through Campaign Core as a DM-gated POST", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ draft_text: "Text [1].", cited_keys: ["claim:k1"], model_slug: "m", prompt_version: "prose/1", prompt_tokens: 1, completion_tokens: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await reviewCampaign(
      { operation: "draft_prose", body: { subject: "Fleurite", subject_kind: "location", paragraph_limit: 3, material: [{ key: "claim:k1", kind: "claim", text: "Text." }], idempotency_key: "t" } },
      "http://campaign-core:8000",
      request,
    );

    const [endpoint, init] = request.mock.calls[0] as unknown as [URL, RequestInit];
    expect([init.method, endpoint.pathname]).toEqual(["POST", "/prose/draft"]);
    expect(endpoint.searchParams.get("requester_role")).toBe("dm");
  });

  it("posts exact approval coordinates and surfaces Core detail", async () => {
    const body = {
      reviewed_version: 2,
      content_hash: "a".repeat(64),
      item_ids: ["item-1"],
      idempotency_key: "approval-1",
    };
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "reviewed proposal version is stale" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      reviewCampaign(
        { operation: "approve_proposal", proposal_id: "proposal-1", body },
        "http://campaign-core:8000",
        request,
      ),
    ).rejects.toThrow("reviewed proposal version is stale");

    expect(request).toHaveBeenCalledWith(
      new URL(
        "http://campaign-core:8000/imports/proposals/proposal-1/approvals?requester_role=dm",
      ),
      expect.objectContaining({ method: "POST", body: JSON.stringify(body) }),
    );
  });

  it("routes plan creation and lifecycle proposals only through Campaign Core", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ proposal_id: "plan-proposal" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await reviewCampaign(
      { operation: "transition_plan_proposal", plan_id: "plan-1", body: {
        plan_id: "plan-1", lifecycle: "failed", supporting_claim_ids: ["claim-1"],
      } },
      "http://campaign-core:8000",
      request,
    );
    const endpoint = request.mock.calls[0]?.[0] as URL;
    expect(endpoint.pathname).toBe("/plans/plan-1/lifecycle-proposals");
    expect(endpoint.searchParams.get("requester_role")).toBe("dm");
  });

  it("routes source document listing to Campaign Core", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 500, offset: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await reviewCampaign(
      { operation: "list_source_documents", query: { limit: 500 } },
      "http://campaign-core:8000",
      request,
    );
    const endpoint = request.mock.calls[0]?.[0] as URL;
    expect(endpoint.pathname).toBe("/imports/source-documents");
    expect(endpoint.searchParams.get("requester_role")).toBe("dm");
    expect(endpoint.searchParams.get("limit")).toBe("500");
  });

  it("routes durable session note writes and deletes", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ deleted: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await reviewCampaign(
      { operation: "delete_session_run_note", run_id: "run-1", note_id: "note-1" },
      "http://campaign-core:8000",
      request,
    );
    const endpoint = request.mock.calls[0]?.[0] as URL;
    expect(endpoint.pathname).toBe("/campaign/session-runs/run-1/notes/note-1");
    expect(request.mock.calls[0]?.[1]).toEqual(expect.objectContaining({ method: "DELETE" }));
  });
});
