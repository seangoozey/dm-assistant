import { requireJobId, type JobSnapshot } from "./jobPlatform";

export const PENDING_JOB_KEY = "dm-assistant.pending-job.v1";
export const EXTRACTION_JOB_KEY = "dm-assistant.extraction-job.v1";
export const LAST_EXTRACTION_JOB_KEY = "dm-assistant.last-extraction-job.v1";
export const EXTRACTION_ERROR_KEY = "dm-assistant.extraction-error.v1";

export function loadPendingJob(storage: Storage, key = PENDING_JOB_KEY): JobSnapshot | null {
  const serialized = storage.getItem(key);
  if (!serialized) return null;
  try {
    const parsed = JSON.parse(serialized) as JobSnapshot;
    requireJobId(parsed.jobId);
    if (!["queued", "running", "succeeded", "failed"].includes(parsed.state)) {
      throw new Error("invalid operation state");
    }
    return parsed;
  } catch {
    storage.removeItem(key);
    return null;
  }
}

export function savePendingJob(storage: Storage, snapshot: JobSnapshot | null, key = PENDING_JOB_KEY): void {
  if (!snapshot) {
    storage.removeItem(key);
    return;
  }
  storage.setItem(key, JSON.stringify(snapshot));
}
