import type {
  CandidateProposalApproval,
  CandidateProposalVersion,
  ChangeSetReceipt,
} from "./campaignClient";

export const REVIEW_STATE_KEY = "dm-assistant.review-state.v1";

export type ReviewPhase =
  | "idle"
  | "proposal_pending"
  | "approved"
  | "applied"
  | "rejected"
  | "deferred"
  | "stale"
  | "failed";

export interface PersistedReviewState {
  selectedCandidateId?: string;
  phase: ReviewPhase;
  proposal?: CandidateProposalVersion;
  approval?: CandidateProposalApproval;
  receipt?: ChangeSetReceipt;
  message?: string;
}

const EMPTY_STATE: PersistedReviewState = { phase: "idle" };

export function loadReviewState(storage: Storage): PersistedReviewState {
  const raw = storage.getItem(REVIEW_STATE_KEY);
  if (!raw) return EMPTY_STATE;
  try {
    const parsed = JSON.parse(raw) as PersistedReviewState;
    if (!parsed.phase) return EMPTY_STATE;
    return parsed;
  } catch {
    storage.removeItem(REVIEW_STATE_KEY);
    return EMPTY_STATE;
  }
}

export function saveReviewState(storage: Storage, state: PersistedReviewState): void {
  if (state.phase === "idle" && !state.selectedCandidateId) {
    storage.removeItem(REVIEW_STATE_KEY);
    return;
  }
  storage.setItem(REVIEW_STATE_KEY, JSON.stringify(state));
}
