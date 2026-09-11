import { describe, expect, it, vi } from "vitest";

import { WindmillJobPlatform, type WindmillBackend } from "./jobPlatform";

describe("WindmillJobPlatform", () => {
  it("contains Windmill calls behind one portable interface", async () => {
    const healthJobId = "019fe949-209f-0980-4374-96fed322a598";
    const extractionJobId = "019fe949-209f-0980-4374-96fed322a599";
    const backend: WindmillBackend = {
      start_health_check: vi.fn().mockResolvedValue(healthJobId),
      start_candidate_extraction: vi.fn().mockResolvedValue(extractionJobId),
      cancel_job: vi.fn().mockResolvedValue("cancelled"),
      inspect_job: vi.fn().mockResolvedValue({
        state: "succeeded",
        progress: 100,
        result: { status: "ok" },
      }),
    };
    const platform = new WindmillJobPlatform(backend);

    expect(await platform.startHealthCheck()).toMatchObject({
      jobId: healthJobId,
      state: "queued",
      progress: 5,
    });
    expect(await platform.startCandidateExtraction(["candidate-1"])).toMatchObject({
      jobId: extractionJobId,
      state: "queued",
    });
    expect(await platform.inspect(healthJobId)).toMatchObject({
      jobId: healthJobId,
      state: "succeeded",
      progress: 100,
    });
    expect(backend.inspect_job).toHaveBeenCalledWith({ job_id: healthJobId });
    await platform.cancel(extractionJobId);
    expect(backend.cancel_job).toHaveBeenCalledWith({ job_id: extractionJobId });
  });

  it("rejects an error string returned in place of a job ID", async () => {
    const platform = new WindmillJobPlatform({
      start_health_check: vi.fn().mockResolvedValue("Failed to deserialize query string"),
      start_candidate_extraction: vi.fn().mockResolvedValue("Failed to deserialize query string"),
      cancel_job: vi.fn(),
      inspect_job: vi.fn(),
    });

    await expect(platform.startCandidateExtraction(["candidate-1"])).rejects.toThrow(
      "Windmill did not return a valid job ID",
    );
  });
});
