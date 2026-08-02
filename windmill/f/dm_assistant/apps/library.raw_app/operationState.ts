import type { JobSnapshot } from "./jobPlatform";

export const PENDING_JOB_KEY = "dm-assistant.pending-job.v1";

export function loadPendingJob(storage: Storage): JobSnapshot | null {
  const serialized = storage.getItem(PENDING_JOB_KEY);
  if (!serialized) return null;
  try {
    const parsed = JSON.parse(serialized) as JobSnapshot;
    if (!parsed.jobId || !["queued", "running", "succeeded", "failed"].includes(parsed.state)) {
      throw new Error("invalid operation state");
    }
    return parsed;
  } catch {
    storage.removeItem(PENDING_JOB_KEY);
    return null;
  }
}

export function savePendingJob(storage: Storage, snapshot: JobSnapshot | null): void {
  if (!snapshot) {
    storage.removeItem(PENDING_JOB_KEY);
    return;
  }
  storage.setItem(PENDING_JOB_KEY, JSON.stringify(snapshot));
}
