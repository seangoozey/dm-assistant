export type JobState = "queued" | "running" | "succeeded" | "failed";

export interface JobSnapshot {
  jobId: string;
  state: JobState;
  progress: number;
  result?: unknown;
  error?: string;
  totalItems?: number;
  candidateIds?: string[];
  updatedAt: string;
}

export interface JobPlatform {
  startHealthCheck(): Promise<JobSnapshot>;
  startCandidateExtraction(candidateIds: string[]): Promise<JobSnapshot>;
  startProseDraft(command: unknown): Promise<JobSnapshot>;
  inspect(jobId: string): Promise<JobSnapshot>;
  cancel(jobId: string): Promise<void>;
}

export interface WindmillBackend {
  start_health_check(input: Record<string, never>): Promise<string>;
  start_candidate_extraction(input: { candidate_ids: string[] }): Promise<string>;
  start_prose_draft(input: { command: unknown }): Promise<string>;
  inspect_job(input: { job_id: string }): Promise<{
    state: JobState;
    progress: number;
    result?: unknown;
    error?: string;
  }>;
  cancel_job(input: { job_id: string }): Promise<string>;
}

export function requireJobId(value: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`Windmill did not return a valid job ID: ${value}`);
  }
  return value;
}

export class WindmillJobPlatform implements JobPlatform {
  constructor(private readonly backend: WindmillBackend) {}

  async startHealthCheck(): Promise<JobSnapshot> {
    const jobId = requireJobId(await this.backend.start_health_check({}));
    return {
      jobId,
      state: "queued",
      progress: 5,
      updatedAt: new Date().toISOString(),
    };
  }

  async startCandidateExtraction(candidateIds: string[]): Promise<JobSnapshot> {
    const jobId = requireJobId(await this.backend.start_candidate_extraction({ candidate_ids: candidateIds }));
    return { jobId, state: "queued", progress: 5, totalItems: candidateIds.length, candidateIds, updatedAt: new Date().toISOString() };
  }

  async startProseDraft(command: unknown): Promise<JobSnapshot> {
    const jobId = requireJobId(await this.backend.start_prose_draft({ command }));
    return { jobId, state: "queued", progress: 5, updatedAt: new Date().toISOString() };
  }

  async inspect(jobId: string): Promise<JobSnapshot> {
    const snapshot = await this.backend.inspect_job({ job_id: jobId });
    return { jobId, ...snapshot, updatedAt: new Date().toISOString() };
  }

  async cancel(jobId: string): Promise<void> {
    await this.backend.cancel_job({ job_id: requireJobId(jobId) });
  }
}
