import { describe, expect, it, vi } from "vitest";

import { queryCampaign } from "./backend/query_campaign";

const query = {
  question: "What is established?",
  requester_visibility: { role: "dm" as const },
};

describe("queryCampaign backend runnable", () => {
  it("posts the typed query to the absolute internal Campaign Core URL", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
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

    const result = await queryCampaign(query, "http://campaign-core:8000", request);

    expect(result.answer_mode).toBe("insufficient_evidence");
    expect(request).toHaveBeenCalledWith(
      new URL("http://campaign-core:8000/retrieval/query"),
      expect.objectContaining({ method: "POST", body: JSON.stringify(query) }),
    );
  });

  it("surfaces Campaign Core failures", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(new Response("no", { status: 503 }));

    await expect(queryCampaign(query, "http://campaign-core:8000", request)).rejects.toThrow(
      "Campaign Core returned 503",
    );
  });
});
