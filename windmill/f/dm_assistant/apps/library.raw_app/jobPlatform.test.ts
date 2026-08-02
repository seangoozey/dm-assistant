import { describe, expect, it, vi } from "vitest";

import { WindmillJobPlatform, type WindmillBackend } from "./jobPlatform";

describe("WindmillJobPlatform", () => {
  it("contains Windmill calls behind one portable interface", async () => {
    const backend: WindmillBackend = {
      start_health_check: vi.fn().mockResolvedValue("job-123456789"),
      inspect_job: vi.fn().mockResolvedValue({
        state: "succeeded",
        progress: 100,
        result: { status: "ok" },
      }),
    };
    const platform = new WindmillJobPlatform(backend);

    expect(await platform.startHealthCheck()).toMatchObject({
      jobId: "job-123456789",
      state: "queued",
      progress: 5,
    });
    expect(await platform.inspect("job-123456789")).toMatchObject({
      jobId: "job-123456789",
      state: "succeeded",
      progress: 100,
    });
    expect(backend.inspect_job).toHaveBeenCalledWith({ job_id: "job-123456789" });
  });
});
