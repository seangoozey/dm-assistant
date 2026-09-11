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
