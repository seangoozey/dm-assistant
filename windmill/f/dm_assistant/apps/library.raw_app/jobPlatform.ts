export type JobState = "queued" | "running" | "succeeded" | "failed";

export interface JobSnapshot {
  jobId: string;
  state: JobState;
  progress: number;
  result?: unknown;
  error?: string;
  updatedAt: string;
}

export interface JobPlatform {
  startHealthCheck(): Promise<JobSnapshot>;
  inspect(jobId: string): Promise<JobSnapshot>;
}

export interface WindmillBackend {
  start_health_check(input: Record<string, never>): Promise<string>;
  inspect_job(input: { job_id: string }): Promise<{
    state: JobState;
    progress: number;
    result?: unknown;
    error?: string;
  }>;
}

export class WindmillJobPlatform implements JobPlatform {
  constructor(private readonly backend: WindmillBackend) {}

  async startHealthCheck(): Promise<JobSnapshot> {
    const jobId = await this.backend.start_health_check({});
    return {
      jobId,
      state: "queued",
      progress: 5,
      updatedAt: new Date().toISOString(),
    };
  }

  async inspect(jobId: string): Promise<JobSnapshot> {
    const snapshot = await this.backend.inspect_job({ job_id: jobId });
    return { jobId, ...snapshot, updatedAt: new Date().toISOString() };
  }
}
