import * as wmill from "windmill-client";

type JobState = "queued" | "running" | "succeeded" | "failed";

interface Snapshot {
  state: JobState;
  progress: number;
  result?: unknown;
  error?: string;
}

export async function main(job_id: string): Promise<Snapshot> {
  const value = (await wmill.getResultMaybe(job_id)) as {
    started?: boolean;
    completed?: boolean;
    success?: boolean;
    result?: unknown;
  };
  if (!value.started) return { state: "queued", progress: 10 };
  if (!value.completed) return { state: "running", progress: 55 };
  if (value.success) return { state: "succeeded", progress: 100, result: value.result };
  return {
    state: "failed",
    progress: 100,
    error: typeof value.result === "string" ? value.result : "Windmill job failed",
  };
}
