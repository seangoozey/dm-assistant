import { JobService } from "windmill-client";

export async function main(job_id: string): Promise<string> {
  return JobService.cancelQueuedJob({
    workspace: process.env.WM_WORKSPACE ?? "no_workspace",
    id: job_id,
    requestBody: { reason: "Cancelled from DM Assistant" },
  });
}
