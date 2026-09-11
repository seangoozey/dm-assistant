import { JobService } from "windmill-client";

type JobState = "queued" | "running" | "succeeded" | "failed";

interface Snapshot {
  state: JobState;
  progress: number;
  result?: unknown;
  error?: string;
}

function jobError(result: unknown): string {
  if (typeof result === "string") return result;
  if (result && typeof result === "object") {
    const error = (result as { error?: unknown }).error;
    if (typeof error === "string") return error;
    if (error && typeof error === "object") {
      const message = (error as { message?: unknown }).message;
      if (typeof message === "string") return message;
    }
    const message = (result as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return "Windmill job failed";
}

export async function main(job_id: string): Promise<Snapshot> {
  const value = await JobService.getCompletedJobResultMaybe({
    workspace: process.env.WM_WORKSPACE ?? "no_workspace",
    id: job_id,
    getStarted: true,
  });
  if (!value.completed) {
    const progress = await JobService.getJobProgress({
      workspace: process.env.WM_WORKSPACE ?? "no_workspace",
      id: job_id,
    }).catch(() => 0);
    return { state: "running", progress: Math.max(1, progress) };
  }
  if (value.success) {
    const results = value.result && typeof value.result === "object"
      ? (value.result as { results?: Array<{ ok?: boolean; error?: string }> }).results
      : undefined;
    if (results?.length && !results.some((item) => item.ok)) {
      const error = results.map((item) => item.error).filter(Boolean).join("; ")
        || "Every candidate extraction failed";
      return { state: "failed", progress: 100, result: value.result, error };
    }
    return { state: "succeeded", progress: 100, result: value.result };
  }
  return {
    state: "failed",
    progress: 100,
    error: jobError(value.result),
  };
}
